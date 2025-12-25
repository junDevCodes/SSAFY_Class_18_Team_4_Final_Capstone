"""
SelF Pred API - ML 기반 추천 서버

장바구니 상품 기반 레시피 추천 및 상품 추천 API를 제공합니다.
"""

import asyncio
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from core.config import settings
from core.database import db
from core.logging import get_logger
from ml.model_loader import model_loader
from ml.base import RecommendationContext

logger = get_logger(__name__)

# 전역 모델 인스턴스 및 동시성 제어 Lock
_recipe_model = None
_self_personalized_model = None
_continuous_trainer = None
_price_scout_service = None
_airscout_model = None  # AIRScout Cold Start 보조 모델

# 싱글톤 초기화용 Lock (Race Condition 방지)
_recipe_model_lock = asyncio.Lock()
_personalized_model_lock = asyncio.Lock()
_price_scout_lock = asyncio.Lock()
_continuous_trainer_lock = asyncio.Lock()
_airscout_model_lock = asyncio.Lock()  # AIRScout 모델 Lock

# 연속 학습 모드 설정 (환경변수로 제어)
# CONTINUOUS_TRAINING_MODE: "aggressive" | "scheduled" | "disabled"
CONTINUOUS_TRAINING_MODE = os.getenv("CONTINUOUS_TRAINING_MODE", "aggressive")


async def get_recipe_model():
    """RecipePickleModel 싱글톤 인스턴스 반환

    Double-checked locking 패턴으로 Race Condition 방지
    """
    global _recipe_model

    # 빠른 경로: 이미 초기화된 경우
    if _recipe_model is not None:
        return _recipe_model

    # 느린 경로: Lock 획득 후 초기화
    async with _recipe_model_lock:
        # Double-check: Lock 획득 사이에 다른 코루틴이 초기화했을 수 있음
        if _recipe_model is None:
            from ml.models.recipe_pickle_model import RecipePickleModel
            model = RecipePickleModel(db=db)
            await model.initialize()
            _recipe_model = model  # 완전히 초기화된 후에만 전역 변수에 할당
            logger.info("RecipePickleModel 초기화 완료")

    return _recipe_model


async def get_self_personalized_model():
    """SelfPersonalizedModel 싱글톤 인스턴스 반환

    ALS 32차원 기반 개인화 추천 모델
    - 하이브리드: CBF 0.7 + CF 0.3
    - 식료품 특화: 재구매 허용

    Double-checked locking 패턴으로 Race Condition 방지
    """
    global _self_personalized_model

    # 빠른 경로: 이미 초기화된 경우
    if _self_personalized_model is not None:
        return _self_personalized_model

    # 느린 경로: Lock 획득 후 초기화
    async with _personalized_model_lock:
        if _self_personalized_model is None:
            from ml.models.self_personalized import SelfPersonalizedModel
            model = SelfPersonalizedModel(db=db)
            await model.initialize()
            _self_personalized_model = model
            logger.info("SelfPersonalizedModel 초기화 완료")

    return _self_personalized_model


async def get_price_scout_service():
    """PriceScoutService 싱글톤 인스턴스 반환

    self_price_analyzer_v1.pkl 모델 기반 가성비 상품 추천 서비스
    - PriceScout 점수 계산 (검증된 로직)
    - 가격 하락 상품 우선 추천
    - ABNORMAL 상품 제외

    Double-checked locking 패턴으로 Race Condition 방지
    """
    global _price_scout_service

    # 빠른 경로: 이미 초기화된 경우
    if _price_scout_service is not None:
        return _price_scout_service

    # 느린 경로: Lock 획득 후 초기화
    async with _price_scout_lock:
        if _price_scout_service is None:
            from ml.models.price_scout import PriceScoutService
            service = PriceScoutService(db=db)
            await service.initialize()
            _price_scout_service = service
            logger.info("PriceScoutService 초기화 완료")

    return _price_scout_service


async def get_airscout_model():
    """AIRScoutModel 싱글톤 인스턴스 반환

    Cold Start 사용자를 위한 semantic 유사도 기반 보조 추천 모델
    - ko-sroberta-multitask (768D RoBERTa) 기반
    - Sigmoid 스케줄에 따라 개인화로 점진 전환
    - 독립 모델 아님 (항상 기존 모델의 보조 가중치로만 작동)

    Double-checked locking 패턴으로 Race Condition 방지
    """
    global _airscout_model

    # 빠른 경로: 이미 초기화된 경우
    if _airscout_model is not None:
        return _airscout_model

    # 느린 경로: Lock 획득 후 초기화
    async with _airscout_model_lock:
        if _airscout_model is None:
            from ml.models.airscout_model import AIRScoutModel
            model = await AIRScoutModel.get_instance(db=db)
            _airscout_model = model
            logger.info("AIRScoutModel 초기화 완료")

    return _airscout_model


async def get_continuous_trainer():
    """ContinuousTrainer 싱글톤 인스턴스 반환

    적극적 연속 학습 시스템:
    - 학습 완료 → 검증 → 배포 → 즉시 다음 학습
    - Model Validation Gate로 품질 보장

    Double-checked locking 패턴으로 Race Condition 방지
    """
    global _continuous_trainer

    # 빠른 경로: 이미 초기화된 경우
    if _continuous_trainer is not None:
        return _continuous_trainer

    # 느린 경로: Lock 획득 후 초기화
    async with _continuous_trainer_lock:
        if _continuous_trainer is None:
            from ml.continuous_trainer import get_continuous_trainer as _get_ct
            trainer = _get_ct(db)

            # 학습 완료 콜백: 모델 리로드 트리거
            async def on_training_complete(metrics):
                logger.info(
                    f"연속 학습 사이클 #{metrics.cycle_id} 배포 완료",
                    extra={
                        "n_users": metrics.n_users,
                        "user_coverage": metrics.user_coverage,
                        "duration_seconds": metrics.duration_seconds,
                    }
                )
                # Hot Reload 트리거 (파일 변경 감지)
                # model_loader의 check_and_reload_models가 자동으로 감지

            trainer.set_training_complete_callback(on_training_complete)

            # 검증 실패 콜백: 경고 로깅
            async def on_validation_failed(metrics):
                logger.warning(
                    f"연속 학습 사이클 #{metrics.cycle_id} 검증 실패",
                    extra={
                        "result": metrics.validation_result.value,
                        "error": metrics.error_message,
                    }
                )

            trainer.set_validation_failed_callback(on_validation_failed)
            _continuous_trainer = trainer

    return _continuous_trainer


async def _on_model_reload(model_name: str):
    """모델 리로드 콜백 (Atomic Swap 패턴)

    모델 파일이 변경되면 새 인스턴스를 생성하고 초기화 완료 후 교체합니다.
    이를 통해 초기화 중에도 기존 모델로 추천 서비스를 계속 제공할 수 있습니다.
    """
    global _self_personalized_model, _recipe_model, _airscout_model

    if model_name.startswith("self_personalized"):
        logger.info("SelfPersonalizedModel 재초기화 시작 (Atomic Swap)")

        # 1단계: 새 인스턴스 생성 및 완전 초기화 (기존 인스턴스는 유지)
        from ml.models.self_personalized import SelfPersonalizedModel
        new_model = SelfPersonalizedModel(db=db)

        try:
            await new_model.initialize()

            # 2단계: 초기화 성공 후 Atomic Swap (Lock 보호 하에 참조만 교체)
            async with _personalized_model_lock:
                old_model = _self_personalized_model
                _self_personalized_model = new_model

            logger.info("SelfPersonalizedModel 재초기화 완료 (Atomic Swap 성공)")

            # 3단계: 이전 모델 정리 (필요 시 리소스 해제)
            del old_model

        except Exception as e:
            logger.error(
                f"SelfPersonalizedModel 재초기화 실패, 기존 모델 유지: {e}",
                exc_info=True
            )

    elif model_name.startswith("recipe"):
        logger.info("RecipePickleModel 재초기화 시작 (Atomic Swap)")

        from ml.models.recipe_pickle_model import RecipePickleModel
        new_model = RecipePickleModel(db=db)

        try:
            await new_model.initialize()

            async with _recipe_model_lock:
                old_model = _recipe_model
                _recipe_model = new_model

            logger.info("RecipePickleModel 재초기화 완료 (Atomic Swap 성공)")
            del old_model

        except Exception as e:
            logger.error(
                f"RecipePickleModel 재초기화 실패, 기존 모델 유지: {e}",
                exc_info=True
            )

    elif model_name.startswith("airscout") or model_name.startswith("AIRScout"):
        logger.info("AIRScoutModel 재초기화 시작 (Atomic Swap)")

        from ml.models.airscout_model import AIRScoutModel

        try:
            # AIRScoutModel은 내부적으로 싱글톤을 관리하므로 _instance를 리셋 후 재생성
            AIRScoutModel._instance = None
            new_model = await AIRScoutModel.get_instance(db=db)

            async with _airscout_model_lock:
                old_model = _airscout_model
                _airscout_model = new_model

            logger.info("AIRScoutModel 재초기화 완료 (Atomic Swap 성공)")
            del old_model

        except Exception as e:
            logger.error(
                f"AIRScoutModel 재초기화 실패, 기존 모델 유지: {e}",
                exc_info=True
            )


async def classify_user(user_id: int) -> str:
    """사용자 타입 분류

    상호작용 이력 기반으로 사용자를 분류합니다.
    - guest: 비회원 (user_id=0 또는 None)
    - cold: 신규 사용자 (상호작용 거의 없음)
    - lukewarm: 탐색 중인 사용자 (조회 활발, 구매 적음)
    - warm: 활성 사용자 (구매 이력 있음)

    Args:
        user_id: 사용자 ID (0 또는 None이면 비회원)

    Returns:
        사용자 타입 ('guest', 'cold', 'lukewarm', 'warm')
    """
    # 비회원 처리: user_id=0 또는 None
    if user_id is None or user_id == 0:
        return "guest"

    try:
        stats = await db.fetch_one(
            """
            SELECT
                COALESCE(SUM(order_event_count), 0) as order_count,
                COALESCE(SUM(cart_event_count), 0) as cart_count,
                COALESCE(SUM(view_count), 0) as view_count
            FROM user_product_stats
            WHERE user_id = $1
            """,
            user_id,
        )

        if not stats:
            return "cold"

        order_count = stats["order_count"] or 0
        cart_count = stats["cart_count"] or 0
        view_count = stats["view_count"] or 0

        # 구매 이력 1회 이상 -> warm
        if order_count >= 1:
            return "warm"
        # 장바구니 3회 이상 -> warm
        if cart_count >= 3:
            return "warm"
        # 조회 10회 이상 + 장바구니 1회 이상 -> lukewarm
        if view_count >= 10 and cart_count >= 1:
            return "lukewarm"

        return "cold"

    except Exception as e:
        logger.warning(f"사용자 분류 실패, cold로 처리: {e}")
        return "cold"


async def _get_user_interaction_count(user_id: int) -> int:
    """사용자 총 상호작용 횟수 조회

    동적 하이브리드 가중치 계산에 사용됩니다.

    Args:
        user_id: 사용자 ID

    Returns:
        총 상호작용 횟수 (order + cart + view)
    """
    try:
        result = await db.fetch_one(
            """
            SELECT COALESCE(SUM(order_event_count + cart_event_count + view_count), 0) AS total
            FROM user_product_stats
            WHERE user_id = $1
            """,
            user_id,
        )
        return int(result["total"]) if result else 0
    except Exception as e:
        logger.warning(f"상호작용 횟수 조회 실패: {e}")
        return 0


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 라이프사이클 관리

    Startup: DB 연결, 모델 로드, 파일 모니터링 시작, 연속 학습 시작
    Shutdown: 연속 학습 중지, 파일 모니터링 중지, DB 연결 종료

    학습 모드 (CONTINUOUS_TRAINING_MODE 환경변수):
    - "aggressive": 적극적 연속 학습 (학습 완료 → 검증 → 배포 → 즉시 다음 학습)
    - "scheduled": 스케줄 기반 학습 (매일 새벽 3시)
    - "disabled": 학습 비활성화 (수동 트리거만)
    """
    global _continuous_trainer

    # Startup
    print("\n" + "=" * 60)
    print("[SelF Pred] 서버 시작 중...")
    print("=" * 60)
    logger.info(
        "서버 시작 - DB 연결 및 모델 로드 중...",
        extra={"training_mode": CONTINUOUS_TRAINING_MODE}
    )
    try:
        print("[DB] 연결 중...")
        await db.connect()
        print("[DB] ✓ 연결 완료")

        # 런타임 모델이 없으면 베이스 모델에서 복사 또는 초기 학습
        # ⚠️ 중요: 모델 로드 전에 먼저 수행해야 runtime에서만 로드됨
        import shutil
        model_loader.runtime_dir.mkdir(parents=True, exist_ok=True)
        runtime_model_path = model_loader.runtime_dir / "self_personalized_v2.pkl"
        base_model_path = model_loader.base_dir / "self_personalized_v2.pkl"

        if not runtime_model_path.exists():
            # 베이스 모델이 있으면 복사 (Atomic Copy 패턴)
            if base_model_path.exists():
                print("[Model] 베이스 모델을 런타임으로 복사 중...")
                logger.info("베이스 모델을 런타임 디렉토리로 복사")
                # 임시 파일에 먼저 복사 후 rename (원자적 이동)
                temp_path = runtime_model_path.with_suffix(".pkl.tmp")
                shutil.copy2(base_model_path, temp_path)
                temp_path.replace(runtime_model_path)
                print("[Model] ✓ 베이스 모델 복사 완료")
            else:
                # 베이스 모델도 없으면 초기 학습 실행
                print("[Training] 모델 파일 없음 - 초기 학습 실행...")
                logger.warning("모델 파일 없음 - 초기 학습 실행 (블로킹)")
                from ml.trainer import get_trainer
                trainer = get_trainer(db)
                success = await trainer.train_and_save("self_personalized_v2")
                if success:
                    print("[Training] ✓ 초기 학습 완료")
                    logger.info("초기 학습 완료")
                else:
                    print("[Training] ✗ 초기 학습 실패 - 폴백 모드")
                    logger.error("초기 학습 실패 - 폴백 모드로 시작")

        # 모든 모델 로드 (runtime 디렉토리에 파일이 있는 상태에서 수행)
        await model_loader.load_all_models()

        # 레시피 모델 미리 초기화
        print("[RecipeModel] 초기화 중...")
        await get_recipe_model()
        print("[RecipeModel] ✓ 초기화 완료")

        # 개인화 모델 미리 초기화
        print("[SelfPersonalizedModel] 초기화 중...")
        await get_self_personalized_model()
        print("[SelfPersonalizedModel] ✓ 초기화 완료")

        # AIRScout 보조 모델 초기화 (Cold Start 사용자용)
        print("[AIRScoutModel] 초기화 중...")
        airscout = await get_airscout_model()
        airscout_status = airscout.get_status()
        print(f"[AIRScoutModel] ✓ 초기화 완료")
        print(f"  - 모델: {airscout_status.get('model_version', 'unknown')}")
        print(f"  - 활성화: {airscout_status.get('enabled', False)}")
        print(f"  - 인코더: {'로드됨' if airscout_status.get('encoder_initialized', False) else '미로드'}")

        # 모델 리로드 콜백 등록 및 파일 모니터링 시작
        model_loader.register_reload_callback(_on_model_reload)
        await model_loader.start_file_monitor()

        # 학습 모드에 따른 처리
        if CONTINUOUS_TRAINING_MODE == "aggressive":
            # 적극적 연속 학습 시작
            print(f"[Training] 모드: aggressive (연속 학습)")
            logger.info("적극적 연속 학습 모드 활성화")
            ct = await get_continuous_trainer()
            await ct.start()

        elif CONTINUOUS_TRAINING_MODE == "scheduled":
            # 스케줄 기반 학습 (매일 새벽 3시)
            print(f"[Training] 모드: scheduled (매일 03:00)")
            logger.info("스케줄 기반 학습 모드 활성화 (매일 03:00)")
            asyncio.create_task(_scheduled_training_loop())

        else:
            print(f"[Training] 모드: disabled (수동 트리거만)")
            logger.info("학습 비활성화 - 수동 트리거만 가능")

        print("=" * 60)
        print("[SelF Pred] ✓ 서버 시작 완료!")
        print(f"  - 포트: {settings.port}")
        print(f"  - 로드된 모델: {model_loader.loaded_models}")
        print("=" * 60 + "\n")
        logger.info("서버 시작 완료")
    except Exception as e:
        logger.error(f"서버 시작 실패: {e}")
        raise

    yield

    # Shutdown
    logger.info("서버 종료 중...")

    # 연속 학습 중지
    if _continuous_trainer is not None:
        await _continuous_trainer.stop()

    await model_loader.stop_file_monitor()
    await db.disconnect()
    logger.info("서버 종료 완료")


async def _scheduled_training_loop():
    """매일 새벽 3시에 모델 재학습 스케줄러

    Docker 환경에서 백그라운드로 실행됩니다.
    """
    from ml.trainer import get_trainer

    while True:
        try:
            # 다음 새벽 3시까지 대기 시간 계산
            now = datetime.now()
            next_3am = now.replace(hour=3, minute=0, second=0, microsecond=0)
            if now.hour >= 3:
                # 오늘 3시가 지났으면 내일 3시
                next_3am = next_3am.replace(day=now.day + 1)

            wait_seconds = (next_3am - now).total_seconds()
            logger.info(
                f"다음 배치 학습까지 대기",
                extra={
                    "next_training": next_3am.isoformat(),
                    "wait_hours": round(wait_seconds / 3600, 1),
                }
            )

            await asyncio.sleep(wait_seconds)

            # 학습 실행
            logger.info("스케줄된 배치 학습 시작 (새벽 3시)")
            trainer = get_trainer(db)
            success = await trainer.train_and_save("self_personalized_v2")

            if success:
                logger.info("스케줄된 배치 학습 완료")
            else:
                logger.error("스케줄된 배치 학습 실패")

        except asyncio.CancelledError:
            logger.info("배치 학습 스케줄러 종료")
            break
        except Exception as e:
            logger.error(f"배치 학습 스케줄러 오류: {e}")
            # 오류 발생 시 1시간 후 재시도
            await asyncio.sleep(3600)


app = FastAPI(
    title="SelF Pred API",
    version="1.0.0",
    description="장바구니 기반 레시피 추천 및 상품 추천 API",
    lifespan=lifespan,
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== Pydantic 모델 ====================

class CartRecommendationRequest(BaseModel):
    """장바구니 추천 요청"""
    product_ids: List[int] = Field(..., description="장바구니 상품 ID 목록")
    limit: int = Field(default=20, ge=1, le=50, description="추천 상품 개수 (최대 50)")


class RecommendedProduct(BaseModel):
    """추천 상품 정보"""
    product_id: int = Field(..., description="상품 ID")
    name: str = Field(..., description="상품명")
    slug: str = Field(..., description="상품 slug")
    price: int = Field(..., description="가격")
    original_price: Optional[int] = Field(None, description="원가")
    main_image: Optional[str] = Field(None, description="대표 이미지 URL")
    order_count: int = Field(default=0, description="주문 수")
    ingredient: str = Field(default="", description="이 상품이 커버하는 재료")


class CartRecommendationResponse(BaseModel):
    """장바구니 추천 응답"""
    products: List[RecommendedProduct] = Field(default_factory=list, description="추천 상품 목록")
    cart_ingredients: List[str] = Field(default_factory=list, description="장바구니에서 인식된 재료")
    model_version: str = Field(default="v2", description="사용된 모델 버전")
    total_count: int = Field(default=0, description="추천 상품 개수")


# ==================== 개인화 추천 Pydantic 모델 ====================

class PersonalizedRecommendationRequest(BaseModel):
    """개인화 추천 요청

    로그인 사용자를 위한 ALS 기반 개인화 추천 요청
    """
    user_id: int = Field(..., description="사용자 ID")
    limit: int = Field(default=8, ge=1, le=50, description="추천 상품 개수 (기본 8, 최대 50)")
    page_type: str = Field(default="home", description="페이지 타입 (home, category, product_detail)")
    category_id: Optional[int] = Field(None, description="카테고리 ID (선택적)")
    cart_product_ids: List[int] = Field(default_factory=list, description="장바구니 상품 ID (제외용)")


class PersonalizedProduct(BaseModel):
    """개인화 추천 상품 정보

    ALS 32차원 모델 기반 추천 상품
    """
    product_id: int = Field(..., description="상품 ID")
    name: str = Field(..., description="상품명")
    slug: str = Field(default="", description="상품 slug")
    price: int = Field(..., description="가격")
    original_price: Optional[int] = Field(None, description="원가")
    main_image: Optional[str] = Field(None, description="대표 이미지 URL")
    category_id: Optional[int] = Field(None, description="카테고리 ID")
    category_name: Optional[str] = Field(None, description="카테고리명")
    order_count: int = Field(default=0, description="주문 수")
    view_count: int = Field(default=0, description="조회 수")
    average_rating: float = Field(default=0.0, description="평균 평점")
    wishlist_count: int = Field(default=0, description="찜 수")
    recommendation_score: float = Field(default=0.0, description="추천 점수 (0-100)")
    recommendation_source: str = Field(default="", description="추천 소스 (pickle_als_v2, pickle_popular 등)")


class PersonalizedRecommendationResponse(BaseModel):
    """개인화 추천 응답

    ALS 32차원 + 하이브리드 추천 결과
    """
    products: List[PersonalizedProduct] = Field(default_factory=list, description="추천 상품 목록")
    user_type: str = Field(default="cold", description="사용자 유형 (cold/lukewarm/warm)")
    model_version: str = Field(default="v2", description="모델 버전")
    total_count: int = Field(default=0, description="추천 상품 개수")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="추가 메타데이터")


# ==================== 타임세일 (PriceScout) Pydantic 모델 ====================


class TimeDealProduct(BaseModel):
    """타임세일 가성비 상품 정보

    self_price_analyzer_v1.pkl 모델 기반 가성비 상품
    - PriceScout 점수로 정렬
    - 가격 하락 상품 우선 노출
    """
    product_id: int = Field(..., description="상품 ID")
    name: str = Field(..., description="상품명")
    slug: str = Field(default="", description="상품 slug")
    price: int = Field(..., description="현재 가격")
    original_price: Optional[int] = Field(None, description="원가")
    previous_price: Optional[int] = Field(None, description="이전 가격 (가격 이력 기반)")
    main_image: Optional[str] = Field(None, description="대표 이미지 URL")
    category_id: Optional[int] = Field(None, description="카테고리 ID")
    category_name: Optional[str] = Field(None, description="카테고리명")
    order_count: int = Field(default=0, description="주문 수")
    view_count: int = Field(default=0, description="조회 수")
    average_rating: float = Field(default=0.0, description="평균 평점")
    # 모델 추천 관련 필드
    price_change_rate: float = Field(..., description="가격 변동률 (%)")
    price_status: str = Field(..., description="가격 상태 (SUPER_SALE, DISCOUNT, STABLE, INCREASE)")
    score_boost: float = Field(default=1.0, description="상태별 점수 가중치")
    final_score: float = Field(..., description="최종 가성비 점수 (모델 추천순)")
    savings: int = Field(default=0, description="절감액 (원)")
    is_lowest_ever: bool = Field(default=False, description="역대 최저가 여부")


class TimeDealResponse(BaseModel):
    """타임세일 응답

    PriceScout 점수 기반 가성비 상품 목록
    """
    products: List[TimeDealProduct] = Field(default_factory=list, description="가성비 상품 목록")
    model_version: str = Field(default="v1", description="사용된 모델 버전")
    total_count: int = Field(default=0, description="상품 개수")


# ==================== 가격 히스토리 Pydantic 모델 ====================


class PriceHistoryPoint(BaseModel):
    """가격 히스토리 데이터 포인트"""
    recorded_at: str = Field(..., description="기록 시각 (ISO 8601)")
    price: int = Field(..., description="가격")
    previous_price: Optional[int] = Field(None, description="이전 가격")
    price_change: Optional[int] = Field(None, description="가격 변동량")
    price_change_rate: Optional[float] = Field(None, description="가격 변동률 (%)")


class PriceStatistics(BaseModel):
    """가격 통계"""
    current_price: int = Field(..., description="현재 가격")
    min_price: int = Field(..., description="최저가")
    max_price: int = Field(..., description="최고가")
    avg_price: float = Field(..., description="평균가")
    price_change_from_avg: float = Field(..., description="평균가 대비 변동률 (%)")
    is_lowest_ever: bool = Field(default=False, description="역대 최저가 여부")
    total_records: int = Field(default=0, description="기록 수")


class PriceHistoryResponse(BaseModel):
    """가격 히스토리 응답"""
    product_id: int = Field(..., description="상품 ID")
    product_name: str = Field(..., description="상품명")
    history: List[PriceHistoryPoint] = Field(default_factory=list, description="가격 이력")
    statistics: Optional[PriceStatistics] = Field(None, description="가격 통계")


# ==================== API 엔드포인트 ====================

@app.get("/")
def read_root():
    """루트 경로 응답"""
    return {
        "message": "SelF Pred API",
        "status": "running",
        "version": "1.0.0",
    }


@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    # DB 연결 상태 확인
    db_healthy = await db.health_check()
    model_loaded = model_loader.is_loaded

    # AIRScout 모델 상태 확인
    airscout_status = None
    if _airscout_model is not None:
        airscout_status = {
            "initialized": _airscout_model._initialized,
            "enabled": _airscout_model.get_status().get("enabled", False),
            "model_version": _airscout_model.model_version,
        }

    status = "healthy" if db_healthy and model_loaded else "degraded"

    return {
        "status": status,
        "db": "connected" if db_healthy else "disconnected",
        "models": "loaded" if model_loaded else "not_loaded",
        "loaded_models": model_loader.loaded_models,
        "airscout": airscout_status,
    }


@app.get("/api/time-deal-products", response_model=TimeDealResponse)
async def get_time_deal_products(
    limit: int = Query(default=10, ge=1, le=50, description="조회할 상품 수 (기본 10, 최대 50)"),
    category_id: Optional[int] = Query(default=None, description="카테고리 ID (선택적)"),
):
    """타임세일 가성비 상품 API

    self_price_analyzer_v1.pkl 모델과 PriceScout 점수 기반으로
    가성비 상품을 추천합니다.

    - **인증 불필요**: 회원/비회원 모두 사용 가능
    - **정렬 기준**: PriceScout 점수 내림차순
    - **필터링**: 가격 하락 상품만, ABNORMAL 상품 제외
    - **폴백**: 가격 하락 상품 부족 시 할인 상품(original_price > price)으로 대체

    가격 상태 분류:
    - SUPER_SALE (< -10%): 특가 할인
    - DISCOUNT (-10% ~ -2%): 일반 할인
    - STABLE (-2% ~ +2%): 안정적
    - INCREASE (+2% ~ +20%): 소폭 상승

    Args:
        limit: 조회할 상품 수 (기본 10, 최대 50)
        category_id: 카테고리 ID (선택적 필터)

    Returns:
        가성비 상품 목록 (PriceScout 점수 내림차순)
    """
    try:
        service = await get_price_scout_service()
        products = await service.get_value_products(
            limit=limit,
            category_id=category_id,
        )

        return TimeDealResponse(
            products=[TimeDealProduct(**p) for p in products],
            model_version=service.model_version,
            total_count=len(products),
        )

    except Exception as e:
        logger.error(f"타임세일 상품 조회 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"타임세일 상품 조회 중 오류가 발생했습니다: {str(e)}",
        )


@app.get("/api/price-history/{product_id}", response_model=PriceHistoryResponse)
async def get_price_history(
    product_id: int,
    days: int = Query(default=30, ge=7, le=365, description="조회 기간 (일)"),
):
    """상품 가격 히스토리 API

    상품의 가격 변동 이력을 조회합니다.
    폴센트(Pollcent) 스타일의 가격 추적 그래프용 데이터를 제공합니다.

    - **인증 불필요**: 회원/비회원 모두 사용 가능
    - **기간 설정**: 7일 ~ 365일 (기본 30일)

    Args:
        product_id: 상품 ID
        days: 조회 기간 (기본 30일)

    Returns:
        가격 이력 및 통계 정보
    """
    try:
        # 상품 정보 조회
        product_query = """
            SELECT id, name, price FROM products WHERE id = $1 AND status = 'active'
        """
        product_record = await db.fetch_one(product_query, product_id)

        if not product_record:
            raise HTTPException(
                status_code=404,
                detail=f"상품을 찾을 수 없습니다: {product_id}",
            )

        current_price = product_record["price"]
        product_name = product_record["name"]

        # 가격 히스토리 조회
        history_query = """
            SELECT
                recorded_at,
                price,
                previous_price,
                price_change,
                price_change_rate
            FROM product_price_histories
            WHERE product_id = $1
              AND recorded_at >= NOW() - INTERVAL '{days} days'
            ORDER BY recorded_at ASC
        """.replace("{days}", str(days))

        history_records = await db.fetch_all(history_query, product_id)

        # 통계 계산
        statistics_query = """
            SELECT
                MIN(price) as min_price,
                MAX(price) as max_price,
                AVG(price) as avg_price,
                COUNT(*) as total_records
            FROM product_price_histories
            WHERE product_id = $1
        """
        stats_record = await db.fetch_one(statistics_query, product_id)

        # 응답 구성
        history_points = []
        for record in history_records:
            history_points.append(PriceHistoryPoint(
                recorded_at=record["recorded_at"].isoformat(),
                price=record["price"],
                previous_price=record["previous_price"],
                price_change=record["price_change"],
                price_change_rate=float(record["price_change_rate"]) if record["price_change_rate"] else None,
            ))

        # 통계 구성
        statistics = None
        if stats_record and stats_record["total_records"] > 0:
            min_price = stats_record["min_price"]
            max_price = stats_record["max_price"]
            avg_price = float(stats_record["avg_price"])
            total_records = stats_record["total_records"]

            # 평균가 대비 변동률 계산
            if avg_price > 0:
                price_change_from_avg = ((current_price - avg_price) / avg_price) * 100
            else:
                price_change_from_avg = 0.0

            # 역대 최저가 여부
            is_lowest_ever = current_price <= min_price

            statistics = PriceStatistics(
                current_price=current_price,
                min_price=min_price,
                max_price=max_price,
                avg_price=round(avg_price, 0),
                price_change_from_avg=round(price_change_from_avg, 2),
                is_lowest_ever=is_lowest_ever,
                total_records=total_records,
            )

        return PriceHistoryResponse(
            product_id=product_id,
            product_name=product_name,
            history=history_points,
            statistics=statistics,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"가격 히스토리 조회 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"가격 히스토리 조회 중 오류가 발생했습니다: {str(e)}",
        )


@app.post("/api/cart-recommendations", response_model=CartRecommendationResponse)
async def cart_recommendations(request: CartRecommendationRequest):
    """장바구니 기반 상품 추천 API

    장바구니에 담긴 상품들의 재료를 분석하여
    레시피 Gap Filling 모델로 추천 상품을 반환합니다.

    - **인증 불필요**: 회원/비회원 모두 사용 가능
    - **parsed_ingredients 활용**: 상품의 main_ingredient 필드 우선 사용

    Args:
        request: 장바구니 상품 ID 목록 및 추천 개수

    Returns:
        추천 상품 목록, 인식된 재료, 모델 버전
    """
    # 빈 장바구니 처리
    if not request.product_ids:
        return CartRecommendationResponse(
            products=[],
            cart_ingredients=[],
            model_version="v2",
            total_count=0,
        )

    try:
        model = await get_recipe_model()
        result = await model.get_simple_cart_recommendations(
            cart_product_ids=request.product_ids,
            limit=request.limit,
        )

        # 응답 변환
        products = [
            RecommendedProduct(
                product_id=p.get("product_id"),
                name=p.get("name", ""),
                slug=p.get("slug", ""),
                price=p.get("price", 0),
                original_price=p.get("original_price"),
                main_image=p.get("main_image"),
                order_count=p.get("order_count", 0),
                ingredient=p.get("ingredient", ""),
            )
            for p in result.get("products", [])
        ]

        return CartRecommendationResponse(
            products=products,
            cart_ingredients=result.get("cart_ingredients", []),
            model_version=result.get("model_version", "v2"),
            total_count=len(products),
        )

    except Exception as e:
        logger.error(f"장바구니 추천 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"추천 처리 중 오류가 발생했습니다: {str(e)}",
        )


@app.post("/api/personalized-recommendations", response_model=PersonalizedRecommendationResponse)
async def personalized_recommendations(request: PersonalizedRecommendationRequest):
    """개인화 추천 API

    로그인 사용자를 위한 개인화 추천을 제공합니다.

    - **인증 필수**: user_id 필수
    - **ALS 32차원 모델**: self_personalized_v2.pkl 사용
    - **장바구니 제외**: cart_product_ids에 있는 상품은 추천에서 제외
    - **항상 8개 반환**: 부족하면 인기 상품으로 채움

    Args:
        request: 사용자 ID, 추천 개수, 페이지 타입, 장바구니 상품 ID

    Returns:
        개인화 추천 상품 목록, 사용자 타입, 모델 버전
    """
    try:
        # 사용자 타입 분류
        user_type = await classify_user(request.user_id)
        exclude_ids = set(request.cart_product_ids)  # 장바구니 상품 제외

        # ALS 32차원 개인화 모델 사용
        model = await get_self_personalized_model()

        # 사용자 상호작용 횟수 조회 (동적 하이브리드 가중치용)
        interaction_count = await _get_user_interaction_count(request.user_id)

        # RecommendationContext 생성
        context = RecommendationContext(
            user_id=request.user_id,
            user_type=user_type,
            category_id=request.category_id,
            cart_product_ids=list(exclude_ids),
            page_type=request.page_type,
            interaction_count=interaction_count,
        )

        # 개인화 모델로 추천 받기
        result = await model.recommend(context, request.limit)
        model_products = result.products  # RecommendationResult에서 products 추출
        logger.info(
            f"[DEBUG] ALS 모델 추천 결과: {len(model_products)}건, "
            f"sources={[p.get('recommendation_source', 'unknown') for p in model_products[:3]]}, "
            f"confidence={result.confidence:.2f}"
        )

        # 장바구니 상품 제외
        personalized_products = [
            p for p in model_products
            if p.get("product_id") not in exclude_ids
        ][:request.limit]

        # 현재까지 추천된 상품 ID 추적
        recommended_ids = set(p["product_id"] for p in personalized_products)
        exclude_ids.update(recommended_ids)

        # 부족하면 인기 상품으로 채움 (항상 8개 보장)
        remaining = request.limit - len(personalized_products)
        if remaining > 0:
            popular_products = await _get_popular_products(
                exclude_ids=exclude_ids,
                limit=remaining,
            )
            personalized_products.extend(popular_products)

        # 상품 상세 정보 조회 (이미지, 카테고리명 등)
        product_ids = [p["product_id"] for p in personalized_products]
        product_details = await _fetch_product_details(product_ids)

        # 응답 변환
        products = []
        for p in personalized_products:
            pid = p["product_id"]
            detail = product_details.get(pid, {})
            products.append(
                PersonalizedProduct(
                    product_id=pid,
                    name=p.get("name", ""),
                    slug=detail.get("slug", ""),
                    price=p.get("price", 0),
                    original_price=p.get("original_price"),
                    main_image=detail.get("main_image"),
                    category_id=p.get("category_id"),
                    category_name=detail.get("category_name"),
                    order_count=p.get("order_count", 0),
                    view_count=detail.get("view_count", 0),
                    average_rating=float(detail.get("average_rating", 0)),
                    wishlist_count=detail.get("wishlist_count", 0),
                    recommendation_score=float(p.get("recommendation_score", 0)),
                    recommendation_source=p.get("recommendation_source", ""),
                )
            )

        # 추천 소스별 개수 집계
        source_counts = {}
        for p in products:
            source = p.recommendation_source or "unknown"
            source_counts[source] = source_counts.get(source, 0) + 1

        logger.info(
            "개인화 추천 완료",
            extra={
                "user_id": request.user_id,
                "user_type": user_type,
                "source_counts": source_counts,
                "result_count": len(products),
            }
        )

        return PersonalizedRecommendationResponse(
            products=products,
            user_type=user_type,
            model_version=model.model_version,
            total_count=len(products),
            metadata={
                "page_type": request.page_type,
                "cart_excluded": len(request.cart_product_ids),
                "source_counts": source_counts,
            },
        )

    except Exception as e:
        logger.error(f"개인화 추천 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"추천 처리 중 오류가 발생했습니다: {str(e)}",
        )


async def _get_personalized_by_user_stats(
    user_id: int,
    exclude_ids: set,
    limit: int,
) -> List[Dict[str, Any]]:
    """user_product_stats 기반 개인화 추천

    가중치 계산:
    - order_event_count: 10점
    - cart_event_count: 5점
    - view_count: 0.1점
    - 시간 감쇠: 10분 100%, 1시간 95%, 6시간 90%, 12시간 85%, 24시간 80%,
                2일 70%, 3일 60%, 4일 50%, 5일 40%, 7일 30%, 14일 20%, 이후 10%

    같은 카테고리의 다른 인기 상품을 추천

    Args:
        user_id: 사용자 ID
        exclude_ids: 제외할 상품 ID (장바구니 상품 등)
        limit: 추천 개수

    Returns:
        추천 상품 목록
    """
    # 사용자 관심 카테고리 추출 (가중치 + 시간 감쇠 적용)
    interest_query = """
        WITH user_interests AS (
            SELECT
                ups.product_id,
                p.category_id,
                ups.order_event_count,
                ups.cart_event_count,
                ups.view_count,
                ups.last_interacted_at,
                -- 시간 감쇠 계산: 세밀한 시간 기반 감쇠
                CASE
                    WHEN ups.last_interacted_at >= NOW() - INTERVAL '10 minutes' THEN 1.0
                    WHEN ups.last_interacted_at >= NOW() - INTERVAL '1 hour' THEN 0.95
                    WHEN ups.last_interacted_at >= NOW() - INTERVAL '6 hours' THEN 0.9
                    WHEN ups.last_interacted_at >= NOW() - INTERVAL '12 hours' THEN 0.85
                    WHEN ups.last_interacted_at >= NOW() - INTERVAL '24 hours' THEN 0.8
                    WHEN ups.last_interacted_at >= NOW() - INTERVAL '2 days' THEN 0.7
                    WHEN ups.last_interacted_at >= NOW() - INTERVAL '3 days' THEN 0.6
                    WHEN ups.last_interacted_at >= NOW() - INTERVAL '4 days' THEN 0.5
                    WHEN ups.last_interacted_at >= NOW() - INTERVAL '5 days' THEN 0.4
                    WHEN ups.last_interacted_at >= NOW() - INTERVAL '7 days' THEN 0.3
                    WHEN ups.last_interacted_at >= NOW() - INTERVAL '14 days' THEN 0.2
                    ELSE 0.1
                END AS time_decay,
                -- 가중치 점수: order * 10 + cart * 5 + view * 0.1
                (COALESCE(ups.order_event_count, 0) * 10 +
                 COALESCE(ups.cart_event_count, 0) * 5 +
                 COALESCE(ups.view_count, 0) * 0.1) AS base_score
            FROM user_product_stats ups
            JOIN products p ON ups.product_id = p.id
            WHERE ups.user_id = $1
              AND p.status = 'active'
        ),
        category_scores AS (
            -- 카테고리별 가중 점수 합산 (시간 감쇠 적용)
            SELECT
                category_id,
                SUM(base_score * time_decay) AS weighted_score,
                MAX(last_interacted_at) AS last_interaction
            FROM user_interests
            WHERE category_id IS NOT NULL
            GROUP BY category_id
            HAVING SUM(base_score * time_decay) > 0
            ORDER BY SUM(base_score * time_decay) DESC
            LIMIT 5
        )
        SELECT category_id, weighted_score
        FROM category_scores
        ORDER BY weighted_score DESC
    """

    try:
        category_records = await db.fetch_all(interest_query, user_id)

        if not category_records:
            return []

        # 관심 카테고리 ID 추출
        interested_category_ids = [r["category_id"] for r in category_records]

        # 해당 카테고리의 인기 상품 조회 (사용자가 이미 본 상품 및 장바구니 상품 제외)
        exclude_list = list(exclude_ids) if exclude_ids else [-1]

        products_query = """
            WITH user_seen_products AS (
                -- 사용자가 이미 상호작용한 상품
                SELECT product_id
                FROM user_product_stats
                WHERE user_id = $1
            ),
            category_popular AS (
                SELECT
                    p.id AS product_id,
                    p.name,
                    p.price,
                    p.original_price,
                    p.category_id,
                    COALESCE(ps.order_event_count, 0) AS order_count,
                    COALESCE(ps.view_count, 0) AS view_count,
                    COALESCE(ps.average_rating, 0) AS average_rating,
                    -- 카테고리 가중치 (첫 번째 관심 카테고리가 가장 높음)
                    CASE
                        WHEN p.category_id = $3 THEN 1.0
                        WHEN p.category_id = ANY($2) THEN 0.7
                        ELSE 0.3
                    END AS category_weight,
                    -- 인기도 점수
                    (COALESCE(ps.order_event_count, 0) * 5 + COALESCE(ps.view_count, 0)) AS popularity_score
                FROM products p
                LEFT JOIN product_stats ps ON p.id = ps.product_id
                WHERE p.category_id = ANY($2)
                  AND p.status = 'active'
                  AND p.id != ALL($4)  -- 장바구니 상품 제외
                  AND p.id NOT IN (SELECT product_id FROM user_seen_products)  -- 이미 본 상품 제외
            )
            SELECT
                product_id, name, price, original_price, category_id,
                order_count, view_count, average_rating,
                (popularity_score * category_weight) AS final_score
            FROM category_popular
            ORDER BY final_score DESC
            LIMIT $5
        """

        # 첫 번째 관심 카테고리
        top_category = interested_category_ids[0] if interested_category_ids else None

        records = await db.fetch_all(
            products_query,
            user_id,
            interested_category_ids,
            top_category,
            exclude_list,
            limit,
        )

        products = []
        for r in records:
            products.append({
                "product_id": r["product_id"],
                "name": r["name"],
                "price": r["price"],
                "original_price": r["original_price"],
                "category_id": r["category_id"],
                "order_count": r["order_count"],
                "view_count": r["view_count"],
                "average_rating": r["average_rating"],
                "recommendation_score": min(100, float(r["final_score"]) / 10),  # 0-100 범위로 정규화
                "recommendation_source": "personalized",
            })

        return products

    except Exception as e:
        logger.warning(f"user_product_stats 기반 추천 실패: {e}")
        return []


async def _get_popular_products(
    exclude_ids: set,
    limit: int,
) -> List[Dict[str, Any]]:
    """전체 인기 상품 조회 (폴백)

    장바구니 상품 및 이미 추천된 상품 제외

    Args:
        exclude_ids: 제외할 상품 ID
        limit: 조회 개수

    Returns:
        인기 상품 목록
    """
    exclude_list = list(exclude_ids) if exclude_ids else [-1]

    query = """
        SELECT
            p.id AS product_id,
            p.name,
            p.price,
            p.original_price,
            p.category_id,
            COALESCE(ps.order_event_count, 0) AS order_count,
            COALESCE(ps.view_count, 0) AS view_count,
            COALESCE(ps.average_rating, 0) AS average_rating
        FROM products p
        LEFT JOIN product_stats ps ON p.id = ps.product_id
        WHERE p.status = 'active'
          AND p.id != ALL($1)
        ORDER BY
            COALESCE(ps.order_event_count, 0) DESC,
            COALESCE(ps.view_count, 0) DESC
        LIMIT $2
    """

    try:
        records = await db.fetch_all(query, exclude_list, limit)

        products = []
        for r in records:
            products.append({
                "product_id": r["product_id"],
                "name": r["name"],
                "price": r["price"],
                "original_price": r["original_price"],
                "category_id": r["category_id"],
                "order_count": r["order_count"],
                "view_count": r["view_count"],
                "average_rating": r["average_rating"],
                "recommendation_score": 50.0,  # 기본 점수
                "recommendation_source": "popular",
            })

        return products

    except Exception as e:
        logger.error(f"인기 상품 조회 실패: {e}")
        return []


async def _fetch_product_details(product_ids: List[int]) -> Dict[int, Dict[str, Any]]:
    """상품 상세 정보 조회 (이미지, 카테고리명 등)

    Args:
        product_ids: 상품 ID 목록

    Returns:
        상품 ID → 상세 정보 맵
    """
    if not product_ids:
        return {}

    placeholders = ", ".join(f"${i+1}" for i in range(len(product_ids)))
    query = f"""
        SELECT
            p.id AS product_id,
            p.slug,
            (SELECT pi.image_url FROM product_images pi
             WHERE pi.product_id = p.id
             ORDER BY pi.display_order ASC LIMIT 1) AS main_image,
            c.name AS category_name,
            COALESCE(ps.view_count, 0) AS view_count,
            COALESCE(ps.average_rating, 0) AS average_rating,
            COALESCE(ps.wishlist_count, 0) AS wishlist_count
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
        LEFT JOIN product_stats ps ON p.id = ps.product_id
        WHERE p.id IN ({placeholders})
    """

    try:
        records = await db.fetch_all(query, *product_ids)
        return {r["product_id"]: dict(r) for r in records}
    except Exception as e:
        logger.warning(f"상품 상세 정보 조회 실패: {e}")
        return {}


@app.post("/api/recommend")
async def recommend_products():
    """추천 로직 자리 - 추후 구현 (레거시 호환)"""
    # TODO: 추가 추천 로직 구현
    return {"status": "pending"}


@app.post("/api/predict-price")
async def predict_price():
    """가격 예측 로직 자리 - 추후 구현"""
    # TODO: 가격 예측 로직 추가
    return {"status": "pending"}


# ==================== 관리자 API ====================


@app.get("/api/admin/model-status")
async def get_model_status():
    """모델 로더 상태 조회

    Returns:
        로드된 모델 목록, 모니터링 상태, 버전 정보 등
    """
    return model_loader.get_status()


@app.post("/api/admin/reload-model/{model_name}")
async def admin_reload_model(model_name: str):
    """특정 모델 수동 리로드

    Args:
        model_name: 리로드할 모델 이름 (예: self_personalized_v2)

    Returns:
        리로드 결과
    """
    success = await model_loader.reload_model(model_name)
    if success:
        return {
            "status": "success",
            "message": f"모델 '{model_name}' 리로드 완료",
            "model_info": model_loader.get_status().get("models", {}).get(model_name),
        }
    else:
        raise HTTPException(
            status_code=404,
            detail=f"모델 '{model_name}'을(를) 찾을 수 없거나 리로드 실패",
        )


@app.post("/api/admin/reload-all-models")
async def admin_reload_all_models():
    """모든 모델 강제 리로드

    Returns:
        리로드된 모델 목록
    """
    reloaded = await model_loader.reload_all_models()
    return {
        "status": "success",
        "reloaded_models": reloaded,
        "total_count": len(reloaded),
    }


@app.post("/api/admin/backup-model/{model_name}")
async def admin_backup_model(model_name: str):
    """모델 백업 생성

    Args:
        model_name: 백업할 모델 이름

    Returns:
        백업 파일 경로
    """
    backup_path = model_loader.backup_model(model_name)
    if backup_path:
        return {
            "status": "success",
            "backup_path": str(backup_path),
        }
    else:
        raise HTTPException(
            status_code=404,
            detail=f"모델 '{model_name}'을(를) 백업할 수 없습니다",
        )


@app.get("/api/admin/backups/{model_name}")
async def admin_list_backups(model_name: str):
    """모델 백업 목록 조회

    Args:
        model_name: 모델 이름

    Returns:
        백업 파일 목록 (최신순)
    """
    backups = model_loader.list_backups(model_name)
    return {
        "model_name": model_name,
        "backups": [
            {
                "path": str(p),
                "filename": p.name,
                "size_mb": round(p.stat().st_size / (1024 * 1024), 2),
                "created_at": p.stat().st_mtime,
            }
            for p in backups
        ],
        "total_count": len(backups),
    }


@app.post("/api/admin/train-model")
async def admin_train_model(background: bool = True):
    """모델 학습 트리거

    Args:
        background: True면 백그라운드 학습, False면 동기 학습

    Returns:
        학습 시작/완료 상태
    """
    from ml.trainer import get_trainer

    trainer = get_trainer(db)

    if trainer.is_training:
        return {
            "status": "already_training",
            "message": "이미 학습이 진행 중입니다",
        }

    if background:
        await trainer.train_in_background("self_personalized_v2")
        return {
            "status": "started",
            "message": "백그라운드 학습이 시작되었습니다",
        }
    else:
        success = await trainer.train_and_save("self_personalized_v2")
        return {
            "status": "success" if success else "failed",
            "message": "학습 완료" if success else "학습 실패",
        }


@app.get("/api/admin/trainer-status")
async def admin_trainer_status():
    """학습기 상태 조회

    Returns:
        학습 진행 여부, 마지막 학습 시간, 하이퍼파라미터
    """
    from ml.trainer import get_trainer

    trainer = get_trainer(db)
    return trainer.get_status()


# ==================== 연속 학습 관리 API ====================


@app.get("/api/admin/continuous-training/status")
async def get_continuous_training_status():
    """연속 학습 시스템 상태 조회

    Returns:
        연속 학습 상태, 사이클 수, 성공률, 최근 히스토리
    """
    if CONTINUOUS_TRAINING_MODE != "aggressive":
        return {
            "mode": CONTINUOUS_TRAINING_MODE,
            "message": "연속 학습 모드가 비활성화되어 있습니다",
            "enabled": False,
        }

    ct = await get_continuous_trainer()
    status = ct.get_status()
    metrics = ct.get_metrics_summary()

    return {
        "mode": CONTINUOUS_TRAINING_MODE,
        "enabled": True,
        **status,
        "metrics_summary": metrics,
    }


@app.post("/api/admin/continuous-training/start")
async def start_continuous_training():
    """연속 학습 시작

    Returns:
        시작 결과
    """
    ct = await get_continuous_trainer()

    if ct.is_running:
        return {
            "status": "already_running",
            "message": "연속 학습이 이미 실행 중입니다",
        }

    await ct.start()
    return {
        "status": "started",
        "message": "연속 학습이 시작되었습니다",
    }


@app.post("/api/admin/continuous-training/stop")
async def stop_continuous_training():
    """연속 학습 중지

    Returns:
        중지 결과
    """
    ct = await get_continuous_trainer()

    if not ct.is_running:
        return {
            "status": "not_running",
            "message": "연속 학습이 실행 중이 아닙니다",
        }

    await ct.stop()
    return {
        "status": "stopped",
        "message": "연속 학습이 중지되었습니다",
    }


@app.post("/api/admin/continuous-training/pause")
async def pause_continuous_training():
    """연속 학습 일시 중지

    Returns:
        일시 중지 결과
    """
    ct = await get_continuous_trainer()
    await ct.pause()
    return {
        "status": "paused",
        "message": "연속 학습이 일시 중지되었습니다",
        "state": ct.state.value,
    }


@app.post("/api/admin/continuous-training/resume")
async def resume_continuous_training():
    """연속 학습 재개

    Returns:
        재개 결과
    """
    ct = await get_continuous_trainer()
    await ct.resume()
    return {
        "status": "resumed",
        "message": "연속 학습이 재개되었습니다",
        "state": ct.state.value,
    }


@app.get("/api/admin/continuous-training/metrics")
async def get_continuous_training_metrics():
    """연속 학습 메트릭 요약

    Returns:
        총 사이클 수, 성공률, 평균 학습 시간, 평균 커버리지
    """
    if CONTINUOUS_TRAINING_MODE != "aggressive":
        return {
            "mode": CONTINUOUS_TRAINING_MODE,
            "enabled": False,
        }

    ct = await get_continuous_trainer()
    return {
        "mode": CONTINUOUS_TRAINING_MODE,
        "enabled": True,
        "cycle_count": ct.cycle_count,
        **ct.get_metrics_summary(),
    }


@app.get("/api/admin/continuous-training/history")
async def get_continuous_training_history(limit: int = 20):
    """연속 학습 히스토리 조회

    Args:
        limit: 조회할 최대 개수 (기본 20)

    Returns:
        최근 학습 사이클 히스토리
    """
    if CONTINUOUS_TRAINING_MODE != "aggressive":
        return {
            "mode": CONTINUOUS_TRAINING_MODE,
            "enabled": False,
            "history": [],
        }

    ct = await get_continuous_trainer()
    status = ct.get_status()

    return {
        "mode": CONTINUOUS_TRAINING_MODE,
        "enabled": True,
        "total_cycles": ct.cycle_count,
        "history": status.get("recent_history", [])[-limit:],
    }
