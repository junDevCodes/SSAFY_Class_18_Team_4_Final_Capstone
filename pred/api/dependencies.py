"""
API 의존성 주입

FastAPI 의존성 주입을 위한 함수들
"""

from datetime import datetime
from typing import Optional

from fastapi import Request

from core.database import Database
from core.cache import CacheManager
from core.orchestrator import RecommendationOrchestrator
from core.config import settings
from core.logging import get_logger
from api.schemas import TimeContext

logger = get_logger(__name__)

# 전역 인스턴스 (애플리케이션 시작 시 초기화)
_db: Optional[Database] = None
_cache: Optional[CacheManager] = None
_orchestrator: Optional[RecommendationOrchestrator] = None


async def init_dependencies():
    """의존성 초기화 (애플리케이션 시작 시 호출)"""
    global _db, _cache, _orchestrator

    logger.info("init_dependencies 시작")

    # 데이터베이스 연결 (Database 클래스는 settings에서 설정 읽음)
    _db = Database()
    await _db.connect()
    logger.info("DB 연결 완료")

    # 캐시 연결 (CacheManager 클래스는 settings에서 설정 읽음)
    _cache = CacheManager()
    await _cache.connect()
    logger.info("캐시 연결 완료")

    # Pickle 모델 로드 (중요! 모델 클래스 초기화 전에 실행)
    logger.info("Pickle 모델 로딩 시작")
    from ml.model_loader import model_loader
    await model_loader.load_all_models()
    logger.info(f"로드된 Pickle 모델: {model_loader.loaded_models}")

    # ML 모델 인스턴스 초기화
    logger.info("ML 모델 초기화 시작")
    from ml.models.self_personalized import SelfPersonalizedModel
    from ml.models.price_anomaly import PriceAnomalyModel
    from ml.models.instacart_cold_start import InstacartColdStartModel
    from ml.models.recipe_pickle_model import RecipePickleModel

    self_model = None
    price_model = None
    instacart_model = None
    recipe_model = None

    # SelF Personalized 모델 (개인화 추천)
    try:
        self_model = SelfPersonalizedModel(_db, _cache)
        await self_model.initialize()  # pickle 모델 로드
        logger.info(f"SelfPersonalized 모델 초기화 완료 (pickle: {self_model._use_pickle})")
    except Exception as e:
        logger.warning(f"SelfPersonalized 모델 초기화 실패: {e}", exc_info=True)

    # Price Anomaly 모델 (할인/가격 이상치)
    try:
        price_model = PriceAnomalyModel(_db, _cache)
        await price_model.initialize()  # pickle 모델 로드
        logger.info(f"PriceAnomaly 모델 초기화 완료 (pickle: {price_model._use_pickle})")
    except Exception as e:
        logger.warning(f"PriceAnomaly 모델 초기화 실패: {e}", exc_info=True)

    # Instacart Cold Start 모델 (비로그인/신규 사용자)
    try:
        instacart_model = InstacartColdStartModel(_db, _cache)
        # InstacartColdStartModel은 __init__에서 pickle 로드
        has_pickle = instacart_model._pickle_model is not None
        logger.info(f"InstacartColdStart 모델 초기화 완료 (pickle: {has_pickle})")
    except Exception as e:
        logger.warning(f"InstacartColdStart 모델 초기화 실패: {e}", exc_info=True)

    # Recipe Gap-Filling 모델 (레시피 재료 추천)
    try:
        recipe_model = RecipePickleModel(_db, _cache)
        await recipe_model.initialize()
        logger.info(f"RecipeGapFilling 모델 초기화 완료 (pickle: {recipe_model._use_pickle})")
    except Exception as e:
        logger.warning(f"RecipeGapFilling 모델 초기화 실패: {e}", exc_info=True)

    logger.info(
        f"모델 상태 - self: {self_model is not None}, "
        f"price: {price_model is not None}, "
        f"instacart: {instacart_model is not None}, "
        f"recipe: {recipe_model is not None}"
    )

    # 오케스트레이터 초기화 (모든 ML 모델 포함)
    _orchestrator = RecommendationOrchestrator(
        db=_db,
        cache=_cache,
        self_model=self_model,
        price_model=price_model,
        instacart_model=instacart_model,
        recipe_model=recipe_model,
    )

    logger.info(f"오케스트레이터 모델 상태: {list(_orchestrator.models.keys())}")


async def close_dependencies():
    """의존성 정리 (애플리케이션 종료 시 호출)"""
    global _db, _cache, _orchestrator

    if _db:
        await _db.disconnect()
        _db = None

    if _cache:
        await _cache.disconnect()
        _cache = None

    _orchestrator = None


def get_db() -> Database:
    """데이터베이스 인스턴스 반환"""
    if _db is None:
        raise RuntimeError("데이터베이스가 초기화되지 않았습니다")
    return _db


def get_cache() -> CacheManager:
    """캐시 매니저 인스턴스 반환"""
    if _cache is None:
        raise RuntimeError("캐시가 초기화되지 않았습니다")
    return _cache


def get_orchestrator() -> RecommendationOrchestrator:
    """오케스트레이터 인스턴스 반환"""
    if _orchestrator is None:
        raise RuntimeError("오케스트레이터가 초기화되지 않았습니다")
    return _orchestrator


def get_time_context() -> TimeContext:
    """현재 시간 기반 컨텍스트 결정

    Returns:
        TimeContext: 현재 시간대 컨텍스트
    """
    now = datetime.now()
    hour = now.hour

    if 6 <= hour < 11:
        return TimeContext.MORNING
    elif 11 <= hour < 14:
        return TimeContext.LUNCH
    elif 17 <= hour < 21:
        return TimeContext.DINNER
    elif 21 <= hour or hour < 6:
        return TimeContext.NIGHT
    else:
        return TimeContext.DEFAULT


def get_is_weekend() -> bool:
    """주말 여부 확인

    Returns:
        bool: 주말이면 True
    """
    return datetime.now().weekday() >= 5


def get_day_of_week() -> int:
    """요일 반환 (0=월요일)

    Returns:
        int: 요일 (0-6)
    """
    return datetime.now().weekday()


def get_hour_of_day() -> int:
    """시간 반환 (0-23)

    Returns:
        int: 현재 시간
    """
    return datetime.now().hour
