"""
AIRScout 보조 추천 모델

Cold Start 사용자를 위한 semantic 유사도 기반 보조 점수 제공
- 독립 모델 아님 (항상 기존 모델의 보조 가중치로만 작동)
- SelfPersonalizedModel, RecipePickleModel에서 호출
- Sigmoid 스케줄에 따라 개인화로 점진 전환
"""

import asyncio
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from ml.base import HybridModel, RecommendationContext, RecommendationResult
from ml.embeddings.airscout_encoder import AIRScoutEncoder
from ml.utils.weight_scheduler import AIRScoutWeightScheduler
from core.database import Database
from core.cache import CacheManager
from core.logging import get_logger

logger = get_logger(__name__)

# 환경변수 기반 비활성화 지원
ENABLE_AIRSCOUT_BOOST = os.getenv("ENABLE_AIRSCOUT_BOOST", "true").lower() == "true"


class AIRScoutModel(HybridModel):
    """AIRScout 보조 추천 모델 (싱글톤)

    핵심 특징:
    - 768D RoBERTa (ko-sroberta-multitask) 기반 semantic 유사도
    - Cold Start 사용자 보조 점수 제공
    - Sigmoid 스케줄에 따라 개인화로 점진 전환
    - 하이브리드 스코어: 0.7*semantic + 0.3*user_score

    주의:
    - 이 모델은 독립 추천을 수행하지 않음
    - recommend() 호출 시 빈 결과 반환 (보조 역할만)
    - compute_boost_scores() 메서드를 통해 기존 모델 점수에 가산점 제공

    사용법:
        airscout = await AIRScoutModel.get_instance(db)
        boost_scores = await airscout.compute_boost_scores(
            context=context,
            product_texts=["상품1", "상품2"],
            user_score=None,
        )
    """

    # 전역 싱글톤
    _instance: Optional["AIRScoutModel"] = None
    _init_lock = asyncio.Lock()

    def __init__(
        self,
        db: Database,
        cache: Optional[CacheManager] = None,
        model_dir: Optional[Path] = None,
    ):
        super().__init__(db, cache)

        # 기본 모델 디렉토리 (pred/models/AIRScout_model/hf_model_jhgan/)
        if model_dir is None:
            base = Path(__file__).parent.parent.parent / "models" / "AIRScout_model"
            # hf_model_* 디렉토리 자동 검색
            if base.exists():
                for child in base.iterdir():
                    if child.is_dir() and (child / "config.json").exists():
                        model_dir = child
                        break
            if model_dir is None:
                model_dir = base

        self.model_dir = model_dir
        self._encoder: Optional[AIRScoutEncoder] = None
        self._scheduler: Optional[AIRScoutWeightScheduler] = None
        self._ranking_config: Dict[str, Any] = {}
        self._model_version = "unknown"

    @property
    def model_name(self) -> str:
        return "airscout"

    @property
    def model_version(self) -> str:
        return self._model_version

    @classmethod
    async def get_instance(
        cls,
        db: Database,
        cache: Optional[CacheManager] = None,
    ) -> "AIRScoutModel":
        """싱글톤 인스턴스 반환 (Double-checked Locking)

        Args:
            db: 데이터베이스 인스턴스
            cache: 캐시 매니저 (선택적)

        Returns:
            초기화된 AIRScoutModel 인스턴스
        """
        if cls._instance is not None and cls._instance._initialized:
            return cls._instance

        async with cls._init_lock:
            if cls._instance is None or not cls._instance._initialized:
                cls._instance = cls(db, cache)
                await cls._instance.initialize()

        return cls._instance

    async def initialize(self) -> None:
        """모델 초기화"""
        if self._initialized:
            return

        # 1. ranking_config.json 로드
        config_path = self.model_dir.parent / "ranking_config.json"
        if not config_path.exists() and self.model_dir.exists():
            config_path = self.model_dir / "ranking_config.json"

        if config_path.exists():
            self._ranking_config = json.loads(config_path.read_text(encoding="utf-8"))
            self._model_version = self._ranking_config.get(
                "model_name", "jhgan/ko-sroberta-multitask"
            )
            logger.info(f"ranking_config.json 로드 완료: {config_path}")
        else:
            logger.warning(f"ranking_config.json 없음, 기본값 사용: {config_path}")
            self._ranking_config = {
                "personal_schedule": {"type": "sigmoid", "t0": 21, "k": 0.2},
                "airscout_formula": "0.7*semantic + 0.3*user_score",
                "normalize_user_score": True,
            }
            self._model_version = "jhgan/ko-sroberta-multitask"

        # 2. 가중치 스케줄러 초기화
        self._scheduler = AIRScoutWeightScheduler(self._ranking_config)

        # 3. 텍스트 인코더 초기화
        self._encoder = await AIRScoutEncoder.get_instance(self.model_dir)

        self._initialized = True
        logger.info(
            "AIRScoutModel 초기화 완료",
            extra={
                "model_dir": str(self.model_dir),
                "model_version": self._model_version,
                "enabled": ENABLE_AIRSCOUT_BOOST,
            }
        )

    async def _recommend(
        self,
        context: RecommendationContext,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """추천 로직 (보조 모델이므로 빈 결과 반환)

        AIRScout은 독립 추천을 수행하지 않습니다.
        compute_boost_scores() 메서드를 통해 기존 모델에 가산점을 제공합니다.

        Args:
            context: 추천 컨텍스트
            limit: 추천 개수

        Returns:
            빈 리스트 (보조 모델이므로)
        """
        logger.debug("AIRScoutModel._recommend 호출됨 (보조 모델이므로 빈 결과 반환)")
        return []

    async def compute_boost_scores(
        self,
        context: RecommendationContext,
        product_texts: List[str],
        user_score: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """보조 점수 계산 (기존 모델 점수에 가산)

        user_type 기반 가중치 계산:
        - warm: 즉시 0 반환 (ALS 임베딩 존재, AIRScout 불필요)
        - lukewarm: 0.5 가중치로 부스트 적용
        - cold: Sigmoid 스케줄에 따라 점진적 전환

        Args:
            context: 추천 컨텍스트 (user_type 필수)
            product_texts: 상품명 또는 설명 텍스트 목록 (N개)
            user_score: 튜토리얼 기반 사용자 선호도 점수 (N개), 없으면 0으로 처리

        Returns:
            (N,) 형태의 하이브리드 부스트 점수 [0, 1]
        """
        # 비활성화 시 0 반환
        if not ENABLE_AIRSCOUT_BOOST:
            return np.zeros(len(product_texts))

        if not self._initialized:
            await self.initialize()

        if not product_texts:
            return np.array([])

        # 1. 비회원 판단 (user_id=0 또는 None)
        is_guest = context.user_id is None or context.user_id == 0

        # 2. user_type 기반 가중치 계산 (Primary 기준)
        user_type = context.user_type or "cold"

        # warm 사용자는 즉시 스킵 (ALS 임베딩 존재), 비회원은 무조건 적용
        if not self._scheduler.should_apply_airscout_by_type(user_type, is_guest):
            logger.debug(
                f"AIRScout 스킵 (user_type={user_type})",
                extra={"user_id": context.user_id, "user_type": user_type}
            )
            return np.zeros(len(product_texts))

        # cold일 때만 days_since_signup 조회 (Sigmoid 보조)
        # 비회원은 days_since_signup 조회 불필요 (항상 100%)
        days_since_signup = 0
        if user_type == "cold" and not is_guest:
            days_since_signup = await self._get_days_since_signup(context.user_id)

        w_airscout, w_personal = self._scheduler.get_weights_by_user_type(
            user_type, days_since_signup, is_guest
        )

        # 가중치가 너무 작으면 스킵 (효율성)
        if w_airscout < 0.05:
            logger.debug(
                f"AIRScout 스킵 (w_airscout={w_airscout:.3f} < 0.05)",
                extra={"user_id": context.user_id, "user_type": user_type}
            )
            return np.zeros(len(product_texts))

        # 2. Semantic 점수 계산
        # 대표 쿼리 텍스트 생성 (장바구니 상품명 또는 기본 쿼리)
        if context.cart_product_ids:
            query_text = await self._build_query_from_cart(context.cart_product_ids)
        else:
            query_text = "장보기 추천 상품"

        query_embedding = self._encoder.encode([query_text])[0]
        product_embeddings = self._encoder.encode(product_texts)

        semantic_scores = self._encoder.compute_similarity(
            query_embedding, product_embeddings
        )

        # 3. 하이브리드 점수 계산
        sem_weight, user_weight = self._scheduler.get_hybrid_formula_weights()

        if user_score is None:
            user_score = np.zeros(len(product_texts))
        else:
            user_score = np.asarray(user_score, dtype=float)
            # 정규화 (ranking_config에 normalize_user_score: true)
            if self._ranking_config.get("normalize_user_score", True):
                score_max = user_score.max() if len(user_score) > 0 else 1.0
                if score_max > 0:
                    user_score = user_score / score_max

        hybrid_score = sem_weight * semantic_scores + user_weight * user_score

        # 4. AIRScout 가중치 적용
        boost_scores = w_airscout * hybrid_score

        logger.debug(
            f"AIRScout 부스트 점수 계산 완료",
            extra={
                "user_id": context.user_id,
                "user_type": user_type,
                "is_guest": is_guest,
                "days_since_signup": days_since_signup,
                "w_airscout": round(w_airscout, 3),
                "w_personal": round(w_personal, 3),
                "mean_semantic": round(float(semantic_scores.mean()), 3) if len(semantic_scores) > 0 else 0,
                "mean_boost": round(float(boost_scores.mean()), 3) if len(boost_scores) > 0 else 0,
                "product_count": len(product_texts),
            }
        )

        return boost_scores

    async def compute_recipe_semantic_scores(
        self,
        query_text: str,
        recipe_texts: List[str],
    ) -> np.ndarray:
        """레시피 semantic 유사도 점수 계산

        Args:
            query_text: 검색 쿼리 (예: "삼겹살 깻잎 볶음")
            recipe_texts: 레시피명 + 설명 텍스트 목록

        Returns:
            (N,) 형태의 semantic 유사도 점수 [0, 1]
        """
        if not self._initialized:
            await self.initialize()

        if not recipe_texts:
            return np.array([])

        query_embedding = self._encoder.encode([query_text])[0]
        recipe_embeddings = self._encoder.encode(recipe_texts)

        scores = self._encoder.compute_similarity(query_embedding, recipe_embeddings)

        logger.debug(
            f"레시피 semantic 점수 계산 완료",
            extra={
                "query": query_text[:50],
                "recipe_count": len(recipe_texts),
                "mean_score": round(float(scores.mean()), 3) if len(scores) > 0 else 0,
            }
        )

        return scores

    async def _get_days_since_signup(self, user_id: int) -> int:
        """사용자 가입 후 경과일 조회

        Args:
            user_id: 사용자 ID

        Returns:
            가입 후 경과일 (조회 실패 시 0 반환 = 최대 AIRScout 가중치)
        """
        try:
            query = """
                SELECT EXTRACT(DAY FROM NOW() - date_joined)::INT AS days
                FROM users
                WHERE id = $1
            """
            result = await self.db.fetch_one(query, user_id)

            if result and result["days"] is not None:
                return max(0, result["days"])

        except Exception as e:
            logger.warning(f"사용자 가입일 조회 실패: {e}")

        return 0  # 기본값: Cold 상태로 처리

    async def _build_query_from_cart(self, cart_product_ids: List[int]) -> str:
        """장바구니 상품명으로 쿼리 텍스트 생성

        Args:
            cart_product_ids: 장바구니 상품 ID 목록

        Returns:
            상품명을 결합한 쿼리 텍스트
        """
        if not cart_product_ids:
            return "장보기 추천 상품"

        try:
            placeholders = ", ".join(f"${i+1}" for i in range(len(cart_product_ids[:5])))
            query = f"""
                SELECT name FROM products
                WHERE id IN ({placeholders})
                LIMIT 5
            """
            records = await self.db.fetch_all(query, *cart_product_ids[:5])
            names = [r["name"] for r in records if r.get("name")]

            if names:
                return " ".join(names)

        except Exception as e:
            logger.warning(f"장바구니 상품명 조회 실패: {e}")

        return "장보기 추천 상품"

    def get_current_weights(self, days_since_signup: int) -> Dict[str, float]:
        """현재 가중치 상태 반환 (디버깅/모니터링용)

        Args:
            days_since_signup: 가입 후 경과일

        Returns:
            가중치 상태 딕셔너리
        """
        w_airscout, w_personal = self._scheduler.get_weights(days_since_signup)
        return {
            "days_since_signup": days_since_signup,
            "w_airscout": round(w_airscout, 4),
            "w_personal": round(w_personal, 4),
            "schedule_type": self._scheduler.schedule_type,
            "t0": self._scheduler.t0,
            "k": self._scheduler.k,
            "enabled": ENABLE_AIRSCOUT_BOOST,
        }

    def get_status(self) -> Dict[str, Any]:
        """모델 상태 반환

        Returns:
            모델 상태 딕셔너리
        """
        return {
            "model_name": self.model_name,
            "model_version": self.model_version,
            "initialized": self._initialized,
            "enabled": ENABLE_AIRSCOUT_BOOST,
            "model_dir": str(self.model_dir),
            "scheduler_config": self._scheduler.get_status() if self._scheduler else None,
            "encoder_initialized": self._encoder.is_initialized if self._encoder else False,
        }
