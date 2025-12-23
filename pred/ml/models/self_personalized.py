"""
SelF Personalized 추천 모델

상호작용 이력이 있는 사용자를 위한 개인화 추천

모드:
1. Pickle 모드 v2: ALS 32차원 + 하이브리드 추천 (프로덕션 권장)
   - Kaggle 최상위 수준 알고리즘 (Hu et al., 2008)
   - 메모리 효율: SVD 128D 대비 ~75% 절감
   - 식료품 특화: filter_already_liked_items=False

2. Pickle 모드 v1: SVD 128차원 임베딩 (레거시)

3. DB 모드: 실시간 DB 쿼리 기반 추천 (폴백/개발)

학술적 근거:
- Hu, Y., Koren, Y., & Volinsky, C. (2008). IEEE ICDM
- Netflix Prize (2009)
- 하이브리드 가중치: CBF 0.7 + CF 0.3 (동적 조정)
"""

from typing import Any, Dict, List, Optional, Tuple
import asyncio

import numpy as np

from ml.base import HybridModel, RecommendationContext
from ml.model_loader import model_loader
from ml.utils.numpy_compat import load_numpy_compatible
from data.repositories.user_repo import UserInteractionRepository
from data.repositories.product_repo import ProductRepository, ProductStatsRepository
from data.repositories.instacart_repo import InstacartItemSimilarityRepository
from data.repositories.cache_repo import EmbeddingCacheRepository, UserEmbeddingRepository
from core.database import Database
from core.cache import CacheManager
from core.logging import get_logger

logger = get_logger(__name__)


class SelfPersonalizedModel(HybridModel):
    """SelF 개인화 추천 모델

    핵심 특징:
    - Pickle 모드 v2: ALS 32차원 + 하이브리드 (프로덕션 권장)
    - Pickle 모드 v1: SVD 128차원 (레거시)
    - DB 모드: 실시간 쿼리 기반 추천 (폴백)
    - 동적 하이브리드 가중치 (Netflix Prize 기반)
    - 식료품 특화: 재구매 허용 (filter_already_liked_items=False)
    - Cold start용 인기 상품 캐시 활용

    v2 업그레이드 (2024):
    - ALS 32차원 협업 필터링
    - Confidence Weighting (α=15.0)
    - 하이브리드 가중치: CBF 0.7 + CF 0.3
    - 메모리 효율: 기존 대비 ~75% 절감
    """

    def __init__(
        self,
        db: Database,
        cache: Optional[CacheManager] = None,
    ):
        super().__init__(db, cache)
        self.user_repo = UserInteractionRepository(db)
        self.product_repo = ProductRepository(db)
        self.product_stats_repo = ProductStatsRepository(db)
        self.item_similarity_repo = InstacartItemSimilarityRepository(db)
        self.embedding_repo = EmbeddingCacheRepository(db)
        self.user_embedding_repo = UserEmbeddingRepository(db)

        # Pickle 모델 데이터 (initialize에서 로드)
        self._pickle_model = None
        self._use_pickle = False

    @property
    def model_name(self) -> str:
        return "self_personalized"

    @property
    def model_version(self) -> str:
        if self._pickle_model:
            return self._pickle_model.get("version", "1.0.0")
        return "1.0.0"

    async def initialize(self) -> None:
        """모델 초기화 - pickle 모델 로드 및 임베딩 상태 검증"""
        # Pickle 모델 로드 시도
        self._pickle_model = model_loader.get_model("self_personalized")

        if self._pickle_model:
            self._use_pickle = True
            is_v2 = self._is_pickle_v2()
            algorithm = self._pickle_model.get("algorithm", "SVD")
            metadata = self._pickle_model.get("metadata", {})

            logger.info(
                "Pickle 모델 로드 완료 (self_personalized)",
                extra={
                    "version": self.model_version,
                    "algorithm": algorithm,
                    "is_v2": is_v2,
                    "n_users": metadata.get("n_users", "N/A"),
                    "n_items": metadata.get("n_items", "N/A"),
                    "factors": metadata.get("factors", "N/A"),
                }
            )

            if is_v2:
                hyperparams = self._pickle_model.get("hyperparameters", {})
                logger.info(
                    "v2 하이퍼파라미터 로드",
                    extra={
                        "alpha": hyperparams.get("alpha", 15.0),
                        "cbf_weight": hyperparams.get("cbf_weight", 0.7),
                        "cf_weight": hyperparams.get("cf_weight", 0.3),
                        "filter_already_liked": hyperparams.get("filter_already_liked_items", False),
                    }
                )

            # 임베딩 상태 검증
            await self._validate_model_embeddings()
        else:
            self._use_pickle = False
            logger.warning(
                "Pickle 모델 없음, DB 폴백 모드로 동작",
                extra={"action_required": "모델 재학습 필요"}
            )

        self._initialized = True

    async def _validate_model_embeddings(self) -> None:
        """모델 임베딩 상태 검증

        시작 시 Pickle 모델의 사용자 임베딩과 DB 활성 사용자를 비교하여
        누락된 임베딩이 있으면 경고 로깅

        검증 항목:
        1. 모델에 user_embeddings 존재 여부
        2. DB 활성 사용자 vs 모델 user_id_to_idx 비교
        3. 누락 사용자 수 및 비율 경고
        """
        if not self._pickle_model:
            return

        components = self._pickle_model.get("components", {})

        # 1. 기본 임베딩 데이터 존재 여부 확인
        user_embeddings_raw = components.get("user_embeddings")
        product_embeddings_raw = components.get("product_embeddings")
        user_id_to_idx = components.get("user_id_to_idx", {})
        idx_to_product_id = components.get("idx_to_product_id", {})

        if user_embeddings_raw is None:
            logger.error(
                "모델에 user_embeddings 없음 - 개인화 추천 불가",
                extra={"action_required": "모델 재학습 필요"}
            )
            return

        if product_embeddings_raw is None:
            logger.error(
                "모델에 product_embeddings 없음 - 개인화 추천 불가",
                extra={"action_required": "모델 재학습 필요"}
            )
            return

        model_user_ids = set(user_id_to_idx.keys())
        model_product_ids = set(idx_to_product_id.values())

        logger.info(
            "모델 임베딩 통계",
            extra={
                "model_users": len(model_user_ids),
                "model_products": len(model_product_ids),
            }
        )

        # 2. DB 활성 사용자와 비교
        try:
            # 상호작용이 있는 활성 사용자 조회
            active_users_query = """
                SELECT DISTINCT user_id,
                       SUM(order_event_count + cart_event_count + view_count) AS total_interactions
                FROM user_product_stats
                GROUP BY user_id
                HAVING SUM(order_event_count + cart_event_count + view_count) > 0
            """
            active_users_records = await self.db.fetch_all(active_users_query)
            db_active_user_ids = {r["user_id"] for r in active_users_records}

            # 누락된 사용자 (DB에는 있지만 모델에 없음)
            missing_users = db_active_user_ids - model_user_ids
            coverage_ratio = (
                (len(db_active_user_ids) - len(missing_users)) / len(db_active_user_ids) * 100
                if db_active_user_ids else 0
            )

            if missing_users:
                # 상호작용 수가 많은 상위 누락 사용자 식별
                missing_with_stats = [
                    (r["user_id"], r["total_interactions"])
                    for r in active_users_records
                    if r["user_id"] in missing_users
                ]
                missing_with_stats.sort(key=lambda x: x[1], reverse=True)
                top_missing = missing_with_stats[:10]

                logger.warning(
                    "모델에 임베딩 누락된 활성 사용자 발견",
                    extra={
                        "db_active_users": len(db_active_user_ids),
                        "model_users": len(model_user_ids),
                        "missing_users": len(missing_users),
                        "coverage_percent": round(coverage_ratio, 1),
                        "top_missing_users": [
                            {"user_id": uid, "interactions": int(cnt)}
                            for uid, cnt in top_missing
                        ],
                        "action_required": "모델 재학습으로 새 사용자 임베딩 생성 필요",
                    }
                )
            else:
                logger.info(
                    "모델 사용자 임베딩 커버리지 정상",
                    extra={
                        "db_active_users": len(db_active_user_ids),
                        "model_users": len(model_user_ids),
                        "coverage_percent": 100.0,
                    }
                )

            # 3. 활성 상품과 비교
            active_products_query = """
                SELECT id FROM products WHERE status = 'active'
            """
            active_products_records = await self.db.fetch_all(active_products_query)
            db_active_product_ids = {r["id"] for r in active_products_records}

            missing_products = db_active_product_ids - model_product_ids
            product_coverage = (
                (len(db_active_product_ids) - len(missing_products)) / len(db_active_product_ids) * 100
                if db_active_product_ids else 0
            )

            if len(missing_products) > 10:  # 10개 이상 누락 시 경고
                logger.warning(
                    "모델에 임베딩 누락된 활성 상품 발견",
                    extra={
                        "db_active_products": len(db_active_product_ids),
                        "model_products": len(model_product_ids),
                        "missing_products": len(missing_products),
                        "coverage_percent": round(product_coverage, 1),
                        "action_required": "새 상품 추가 후 모델 재학습 필요",
                    }
                )
            else:
                logger.info(
                    "모델 상품 임베딩 커버리지 정상",
                    extra={
                        "db_active_products": len(db_active_product_ids),
                        "model_products": len(model_product_ids),
                        "coverage_percent": round(product_coverage, 1),
                    }
                )

        except Exception as e:
            logger.error(
                "임베딩 상태 검증 중 오류",
                extra={"error": str(e)}
            )

    async def _recommend(
        self,
        context: RecommendationContext,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """개인화 추천 로직

        Args:
            context: 추천 컨텍스트
            limit: 추천 개수

        Returns:
            추천 상품 목록
        """
        # Pickle 모델이 있으면 임베딩 기반 추천 우선
        if self._use_pickle and self._pickle_model:
            products = await self._recommend_with_pickle(context, limit)
            if products:
                return products
            # Pickle 추천 실패 시 user_product_stats 기반 폴백
            logger.info("Pickle 추천 결과 없음, user_product_stats 기반 폴백 사용")

        # user_product_stats 기반 추천 (폴백) - pred_* 테이블 없이 동작
        return await self._recommend_with_user_stats(context, limit)

    def _is_pickle_v2(self) -> bool:
        """Pickle v2 포맷 여부 확인

        v2 특징:
        - version: "2.0.0" 이상
        - algorithm: "ALS"
        - hyperparameters에 factors, alpha 등 포함
        """
        if not self._pickle_model:
            return False

        version = self._pickle_model.get("version", "1.0.0")
        algorithm = self._pickle_model.get("algorithm", "SVD")

        # 버전 2.x.x 이상이거나 ALS 알고리즘이면 v2
        try:
            major = int(version.split(".")[0])
            return major >= 2 or algorithm == "ALS"
        except (ValueError, IndexError):
            return algorithm == "ALS"

    def _load_embedding_from_bytes(self, data: Any) -> np.ndarray:
        """bytes 또는 dict 형태 임베딩 데이터를 numpy 배열로 변환

        v2 Pickle 포맷은 메모리 효율을 위해 bytes로 저장됨

        Args:
            data: bytes, dict, 또는 numpy 배열

        Returns:
            numpy 배열
        """
        if isinstance(data, np.ndarray):
            return data

        def _resolve_dtype(value: Any) -> np.dtype:
            """pickle 메타데이터 기반 dtype 복원"""
            if value is None:
                return np.dtype(np.float32)
            try:
                return np.dtype(value)
            except (TypeError, ValueError):
                return np.dtype(np.float32)

        def _infer_v2_shape(flat_size: int) -> Optional[Tuple[int, int]]:
            """v2 Pickle 메타데이터 기반 shape 추정"""
            if not self._pickle_model or not self._is_pickle_v2():
                return None

            metadata = self._pickle_model.get("metadata", {}) or {}
            hyperparams = self._pickle_model.get("hyperparameters", {}) or {}

            factors = metadata.get("factors") or hyperparams.get("factors")
            n_users = metadata.get("n_users")
            n_items = metadata.get("n_items")

            if not isinstance(factors, int) or factors <= 0:
                return None

            if isinstance(n_users, int) and flat_size == n_users * factors:
                return (n_users, factors)

            if isinstance(n_items, int) and flat_size == n_items * factors:
                return (n_items, factors)

            return None

        def _reshape_if_possible(arr: np.ndarray, target_shape: Optional[Tuple[int, int]]) -> np.ndarray:
            """가능한 경우에만 reshape 적용"""
            if not target_shape:
                return arr
            try:
                return arr.reshape(target_shape)
            except ValueError:
                logger.warning(
                    "임베딩 shape 복원 실패",
                    extra={"target_shape": target_shape, "actual_size": int(arr.size)},
                )
                return arr

        if isinstance(data, (bytes, bytearray, memoryview)):
            metadata_dtype = None
            if self._pickle_model:
                metadata_dtype = (self._pickle_model.get("metadata", {}) or {}).get("dtype")

            arr = np.frombuffer(data, dtype=_resolve_dtype(metadata_dtype)).copy()
            inferred_shape = _infer_v2_shape(int(arr.size))
            return _reshape_if_possible(arr, inferred_shape)

        if isinstance(data, dict):
            # {'data': bytes, 'shape': tuple} 형식
            raw_data = data.get("data")
            shape = data.get("shape")
            if raw_data is not None:
                dtype_value = data.get("dtype")
                if dtype_value is None and self._pickle_model:
                    dtype_value = (self._pickle_model.get("metadata", {}) or {}).get("dtype")

                dtype = _resolve_dtype(dtype_value)
                arr = np.frombuffer(raw_data, dtype=dtype).copy()
                target_shape = shape or _infer_v2_shape(int(arr.size))
                return _reshape_if_possible(arr, target_shape)

        # 폴백: load_numpy_compatible 사용
        return load_numpy_compatible(data)

    async def _recommend_with_pickle(
        self,
        context: RecommendationContext,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """Pickle 모델 기반 추천 (임베딩 유사도)

        v1: SVD 128차원, 코사인 유사도
        v2: ALS 32차원, 내적 (dot product), 하이브리드 가중치

        Args:
            context: 추천 컨텍스트
            limit: 추천 개수

        Returns:
            추천 상품 목록
        """
        components = self._pickle_model.get("components", {})

        # Cold user: 사전 계산된 인기 상품
        if context.user_type == "cold":
            return await self._recommend_cold_pickle(context, limit, components)

        # v2면 ALS 기반 추천 사용
        if self._is_pickle_v2():
            return await self._recommend_personalized_pickle_v2(context, limit, components)

        # v1 (레거시): SVD 코사인 유사도 기반
        return await self._recommend_personalized_pickle(context, limit, components)

    async def _recommend_cold_pickle(
        self,
        context: RecommendationContext,
        limit: int,
        components: Dict,
    ) -> List[Dict[str, Any]]:
        """Cold user 추천 (Pickle 기반)

        사전 계산된 카테고리별/전체 인기 상품 활용

        Args:
            context: 추천 컨텍스트
            limit: 조회 개수
            components: pickle 컴포넌트

        Returns:
            추천 상품 목록
        """
        # 카테고리 지정 시 카테고리별 인기 상품
        if context.category_id:
            # 키 이름 호환성: category_popular_products 또는 category_popular
            category_popular = components.get("category_popular_products") or components.get("category_popular", {})
            product_ids = category_popular.get(context.category_id, [])[:limit]
        else:
            # 전체 인기 상품 (키 이름 호환성)
            product_ids = components.get("global_popular_products") or components.get("global_popular", [])
            product_ids = product_ids[:limit]

        if not product_ids:
            return []

        # DB에서 상품 정보 조회
        products = await self._fetch_products_by_ids(product_ids)

        for product in products:
            product["recommendation_score"] = 50.0  # 기본 점수
            product["recommendation_source"] = "pickle_popular"

        return products

    def _get_dynamic_hybrid_weights(self, n_interactions: int) -> Tuple[float, float]:
        """동적 하이브리드 가중치 계산 (Netflix Prize 기반)

        상호작용 수에 따라 CBF/CF 가중치를 동적으로 조정
        - Cold user: CBF 100%
        - Power user: CF 70%

        Args:
            n_interactions: 사용자 상호작용 수

        Returns:
            (cbf_weight, cf_weight) 튜플
        """
        # 임계값 기반 가중치 (notebooks/utils/personalization/hybrid_recommender.py와 동일)
        thresholds = [
            (0, 1.0, 0.0),    # Cold Start
            (5, 0.8, 0.2),    # Cold Start
            (10, 0.7, 0.3),   # Warm Start
            (30, 0.5, 0.5),   # Active
            (100, 0.3, 0.7),  # Power User
        ]

        cbf_weight, cf_weight = 0.7, 0.3  # 기본값

        for threshold, cbf_w, cf_w in thresholds:
            if n_interactions >= threshold:
                cbf_weight, cf_weight = cbf_w, cf_w

        return cbf_weight, cf_weight

    async def _get_realtime_activity_boost(
        self,
        user_id: int,
        idx_to_product_id: Dict[int, int],
    ) -> Dict[int, float]:
        """실시간 활동 기반 부스트 점수 계산

        모델 학습 이후 발생한 사용자 활동을 반영하여
        해당 상품 및 관련 카테고리 상품에 가산점을 부여합니다.

        Args:
            user_id: 사용자 ID
            idx_to_product_id: 인덱스 → 상품 ID 매핑

        Returns:
            {product_idx: boost_score} 딕셔너리
        """
        try:
            # 최근 24시간 내 활동 조회 (실시간 반영)
            query = """
                SELECT ups.product_id, p.category_id,
                       ups.order_event_count,
                       ups.cart_event_count,
                       ups.view_count,
                       ups.last_interacted_at
                FROM user_product_stats ups
                JOIN products p ON ups.product_id = p.id
                WHERE ups.user_id = $1
                  AND ups.last_interacted_at > NOW() - INTERVAL '24 hours'
                  AND p.status = 'active'
                ORDER BY ups.last_interacted_at DESC
                LIMIT 50
            """

            records = await self.db.fetch_all(query, user_id)

            if not records:
                return {}

            # 상품 ID → 인덱스 역매핑
            product_id_to_idx = {pid: idx for idx, pid in idx_to_product_id.items()}

            boost_scores: Dict[int, float] = {}
            recent_categories = set()

            for r in records:
                product_id = r["product_id"]
                category_id = r["category_id"]

                # 가중치 계산 (order > cart > view)
                score = (
                    r["order_event_count"] * 10.0 +
                    r["cart_event_count"] * 5.0 +
                    r["view_count"] * 0.5
                )

                # 해당 상품에 부스트
                if product_id in product_id_to_idx:
                    idx = product_id_to_idx[product_id]
                    boost_scores[idx] = boost_scores.get(idx, 0) + score

                # 카테고리 수집
                if category_id:
                    recent_categories.add(category_id)

            # 최근 활동 카테고리의 다른 상품에도 약한 부스트 (카테고리 친화도)
            if recent_categories:
                category_boost_query = """
                    SELECT p.id AS product_id
                    FROM products p
                    LEFT JOIN product_stats ps ON p.id = ps.product_id
                    WHERE p.category_id = ANY($1)
                      AND p.status = 'active'
                    ORDER BY COALESCE(ps.order_event_count, 0) DESC
                    LIMIT 30
                """
                category_records = await self.db.fetch_all(
                    category_boost_query, list(recent_categories)
                )

                for r in category_records:
                    product_id = r["product_id"]
                    if product_id in product_id_to_idx:
                        idx = product_id_to_idx[product_id]
                        # 카테고리 부스트는 직접 활동보다 약하게
                        if idx not in boost_scores:
                            boost_scores[idx] = 1.0  # 기본 카테고리 부스트

            return boost_scores

        except Exception as e:
            logger.warning(f"실시간 활동 부스트 계산 실패: {e}")
            return {}

    async def _recommend_personalized_pickle_v2(
        self,
        context: RecommendationContext,
        limit: int,
        components: Dict,
    ) -> List[Dict[str, Any]]:
        """v2 개인화 추천 (ALS 32차원 + 하이브리드)

        Kaggle 최상위 수준 알고리즘 (Hu et al., 2008)
        - ALS 내적 (dot product) 사용 (코사인 유사도 X)
        - 동적 하이브리드 가중치
        - 식료품 특화: 재구매 허용 (filter_already_liked_items=False)

        Args:
            context: 추천 컨텍스트
            limit: 조회 개수
            components: pickle 컴포넌트

        Returns:
            추천 상품 목록
        """
        user_embeddings_raw = components.get("user_embeddings")
        product_embeddings_raw = components.get("product_embeddings")
        user_id_to_idx = components.get("user_id_to_idx", {})
        idx_to_product_id = components.get("idx_to_product_id", {})

        if user_embeddings_raw is None or product_embeddings_raw is None:
            logger.warning("v2 임베딩 데이터 없음")
            return await self._recommend_cold_pickle(context, limit, components)

        # bytes 형태 임베딩 로드 (v2 포맷)
        user_embeddings = self._load_embedding_from_bytes(user_embeddings_raw)
        product_embeddings = self._load_embedding_from_bytes(product_embeddings_raw)

        # shape 미복원/불일치 방어: 잘못된 점수 계산으로 추천 왜곡되는 것을 방지
        if user_embeddings.ndim != 2 or product_embeddings.ndim != 2:
            logger.warning(
                "v2 임베딩 차원 복원 실패, cold 추천으로 폴백",
                extra={
                    "user_ndim": int(getattr(user_embeddings, "ndim", -1)),
                    "product_ndim": int(getattr(product_embeddings, "ndim", -1)),
                },
            )
            return await self._recommend_cold_pickle(context, limit, components)

        if user_embeddings.shape[1] != product_embeddings.shape[1]:
            logger.warning(
                "v2 임베딩 차원 불일치, cold 추천으로 폴백",
                extra={
                    "user_shape": tuple(user_embeddings.shape),
                    "product_shape": tuple(product_embeddings.shape),
                },
            )
            return await self._recommend_cold_pickle(context, limit, components)

        # 사용자 인덱스 조회
        user_idx = user_id_to_idx.get(context.user_id)

        if user_idx is None:
            logger.debug(f"v2: 사용자 임베딩 없음 (user_id={context.user_id}), cold 추천 사용")
            return await self._recommend_cold_pickle(context, limit, components)

        if not isinstance(user_idx, int) or user_idx < 0 or user_idx >= user_embeddings.shape[0]:
            logger.warning(
                "v2 사용자 인덱스 범위 오류, cold 추천으로 폴백",
                extra={"user_id": context.user_id, "user_idx": user_idx, "n_users": int(user_embeddings.shape[0])},
            )
            return await self._recommend_cold_pickle(context, limit, components)

        # 사용자 임베딩
        user_vec = user_embeddings[user_idx]

        # ALS: 내적 (dot product) 사용 - 코사인 유사도가 아님!
        # ALS는 이미 정규화된 latent factor를 학습하므로 내적이 적절
        als_scores = np.dot(product_embeddings, user_vec)

        # ===== 실시간 활동 반영 (하이브리드 점수 결합) =====
        # 모델 학습 이후 발생한 실시간 활동을 반영
        realtime_boost = await self._get_realtime_activity_boost(
            context.user_id, idx_to_product_id
        )

        # 하이브리드 점수: ALS 점수 + 실시간 활동 부스트
        # 실시간 활동이 있는 상품에 가산점 부여
        scores = als_scores.copy()
        if realtime_boost:
            max_als = np.max(als_scores) if len(als_scores) > 0 else 1.0
            for product_idx, boost in realtime_boost.items():
                if 0 <= product_idx < len(scores):
                    # 부스트는 최대 ALS 점수의 30%까지
                    scores[product_idx] += min(boost, max_als * 0.3)

        # 식료품 특화: 재구매 허용 (filter_already_liked_items=False)
        # 기존에 구매한 상품도 추천에 포함 (식료품은 반복 구매가 일반적)
        # 단, 선택적으로 최근 구매 상품에 약간의 페널티 적용 가능
        hyperparams = self._pickle_model.get("hyperparameters", {})
        filter_already_liked = hyperparams.get("filter_already_liked_items", False)

        if filter_already_liked:
            user_matrix = components.get("user_product_matrix")
            if user_matrix is not None:
                try:
                    purchased = user_matrix[user_idx].toarray().flatten()
                    scores[purchased > 0] = -np.inf
                except Exception:
                    pass

        # Top-K 추출 (여유분 확보)
        top_indices = np.argsort(scores)[::-1][:limit * 2]
        product_ids = []
        product_scores = {}

        for idx in top_indices:
            pid = idx_to_product_id.get(int(idx))
            if pid is not None:
                product_ids.append(pid)
                product_scores[pid] = float(scores[idx])

            if len(product_ids) >= limit:
                break

        if not product_ids:
            return await self._recommend_cold_pickle(context, limit, components)

        # DB에서 상품 정보 조회
        products = await self._fetch_products_by_ids(product_ids)

        # 동적 하이브리드 가중치 적용 (로깅용)
        n_interactions = context.interaction_count or 0
        cbf_weight, cf_weight = self._get_dynamic_hybrid_weights(n_interactions)

        # 점수 정규화 및 메타데이터 추가
        max_score = max(product_scores.values()) if product_scores else 1.0
        min_score = min(product_scores.values()) if product_scores else 0.0
        score_range = max_score - min_score if max_score != min_score else 1.0

        for product in products:
            pid = product.get("product_id")
            raw_score = product_scores.get(pid, 0)
            # 0-100 범위로 정규화
            normalized_score = ((raw_score - min_score) / score_range) * 100
            product["recommendation_score"] = round(normalized_score, 2)
            product["recommendation_source"] = "pickle_als_v2"
            product["hybrid_weights"] = {"cbf": cbf_weight, "cf": cf_weight}

        return products

    async def _recommend_personalized_pickle(
        self,
        context: RecommendationContext,
        limit: int,
        components: Dict,
    ) -> List[Dict[str, Any]]:
        """v1 개인화 추천 (SVD 128차원 코사인 유사도) - 레거시

        Args:
            context: 추천 컨텍스트
            limit: 조회 개수
            components: pickle 컴포넌트

        Returns:
            추천 상품 목록
        """
        user_embeddings_raw = components.get("user_embeddings")
        product_embeddings_raw = components.get("product_embeddings")
        user_id_to_idx = components.get("user_id_to_idx", {})
        idx_to_product_id = components.get("idx_to_product_id", {})

        if user_embeddings_raw is None or product_embeddings_raw is None:
            logger.warning("임베딩 데이터 없음")
            return await self._recommend_cold_pickle(context, limit, components)

        # numpy 버전 호환 형식 처리
        user_embeddings = load_numpy_compatible(user_embeddings_raw)
        product_embeddings = load_numpy_compatible(product_embeddings_raw)

        # 사용자 인덱스 조회
        user_idx = user_id_to_idx.get(context.user_id)

        if user_idx is None:
            # 사용자 임베딩 없으면 cold start
            logger.debug(f"사용자 임베딩 없음 (user_id={context.user_id}), cold 추천 사용")
            return await self._recommend_cold_pickle(context, limit, components)

        # 사용자 임베딩
        user_vec = user_embeddings[user_idx]

        # 모든 상품과의 유사도 계산 (코사인 유사도)
        product_norms = np.linalg.norm(product_embeddings, axis=1)
        user_norm = np.linalg.norm(user_vec)

        # 0으로 나누기 방지
        product_norms = np.where(product_norms == 0, 1e-8, product_norms)

        scores = np.dot(product_embeddings, user_vec) / (product_norms * user_norm + 1e-8)

        # 이미 상호작용한 상품 제외
        user_matrix = components.get("user_product_matrix")
        if user_matrix is not None:
            try:
                purchased = user_matrix[user_idx].toarray().flatten()
                scores[purchased > 0] = -np.inf
            except Exception:
                pass  # 행렬 접근 실패 시 무시

        # Top-K 추출
        top_indices = np.argsort(scores)[::-1][:limit * 2]  # 여유분 확보
        product_ids = []
        product_scores = {}

        for idx in top_indices:
            pid = idx_to_product_id.get(int(idx))
            if pid is not None:
                product_ids.append(pid)
                product_scores[pid] = float(scores[idx])

            if len(product_ids) >= limit:
                break

        if not product_ids:
            return await self._recommend_cold_pickle(context, limit, components)

        # DB에서 상품 정보 조회
        products = await self._fetch_products_by_ids(product_ids)

        # 점수 추가
        for product in products:
            pid = product.get("product_id")
            product["recommendation_score"] = round(product_scores.get(pid, 0) * 100, 2)
            product["recommendation_source"] = "pickle_embedding"

        return products

    async def _fetch_products_by_ids(
        self,
        product_ids: List[int],
    ) -> List[Dict[str, Any]]:
        """상품 ID로 상품 정보 조회

        Args:
            product_ids: 상품 ID 목록

        Returns:
            상품 정보 목록
        """
        if not product_ids:
            return []

        placeholders = ", ".join(f"${i+1}" for i in range(len(product_ids)))
        query = f"""
            SELECT p.id AS product_id, p.name, p.price, p.original_price,
                   p.category_id, p.seller_id,
                   COALESCE(ps.order_event_count, 0) AS order_count
            FROM products p
            LEFT JOIN product_stats ps ON p.id = ps.product_id
            WHERE p.id IN ({placeholders})
              AND p.status = 'active'
        """

        records = await self.db.fetch_all(query, *product_ids)

        # 원래 순서 유지
        product_map = {r["product_id"]: dict(r) for r in records}
        return [product_map[pid] for pid in product_ids if pid in product_map]

    async def _recommend_with_user_stats(
        self,
        context: RecommendationContext,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """user_product_stats 기반 추천 (폴백)

        Pickle 모델에 사용자 임베딩이 없을 때 사용.
        pred_* 테이블 없이 Django 테이블만으로 동작.

        전략:
        1. 사용자의 관심 카테고리 추출 (order > cart > view 가중치)
        2. 해당 카테고리의 인기 상품 추천 (사용자가 이미 본 상품 제외)
        3. 부족하면 전체 인기 상품으로 보충

        Args:
            context: 추천 컨텍스트
            limit: 추천 개수

        Returns:
            추천 상품 목록
        """
        user_id = context.user_id
        exclude_ids = context.cart_product_ids or []

        # 1. 사용자 관심 카테고리 추출
        interest_query = """
            SELECT p.category_id,
                   SUM(ups.order_event_count * 10 +
                       ups.cart_event_count * 2 +
                       ups.view_count * 0.1) AS score
            FROM user_product_stats ups
            JOIN products p ON ups.product_id = p.id
            WHERE ups.user_id = $1
              AND p.category_id IS NOT NULL
              AND p.status = 'active'
            GROUP BY p.category_id
            HAVING SUM(ups.order_event_count * 10 +
                       ups.cart_event_count * 2 +
                       ups.view_count * 0.1) > 0
            ORDER BY score DESC
            LIMIT 5
        """

        try:
            category_records = await self.db.fetch_all(interest_query, user_id)
        except Exception as e:
            logger.warning(f"관심 카테고리 조회 실패: {e}")
            category_records = []

        products = []

        if category_records:
            # 2. 관심 카테고리의 인기 상품 추천
            category_ids = [r["category_id"] for r in category_records]

            # 사용자가 이미 상호작용한 상품 조회
            seen_query = """
                SELECT product_id FROM user_product_stats WHERE user_id = $1
            """
            seen_records = await self.db.fetch_all(seen_query, user_id)
            seen_ids = set(r["product_id"] for r in seen_records)
            all_exclude = list(seen_ids | set(exclude_ids)) or [-1]

            products_query = """
                SELECT p.id AS product_id, p.name, p.price, p.original_price,
                       p.category_id, p.seller_id,
                       COALESCE(ps.order_event_count, 0) AS order_count,
                       COALESCE(ps.view_count, 0) AS view_count,
                       COALESCE(ps.average_rating, 0) AS average_rating
                FROM products p
                LEFT JOIN product_stats ps ON p.id = ps.product_id
                WHERE p.category_id = ANY($1)
                  AND p.status = 'active'
                  AND p.id != ALL($2)
                ORDER BY COALESCE(ps.order_event_count, 0) DESC,
                         COALESCE(ps.view_count, 0) DESC
                LIMIT $3
            """

            try:
                records = await self.db.fetch_all(
                    products_query, category_ids, all_exclude, limit
                )
                for r in records:
                    product = dict(r)
                    product["recommendation_score"] = 70.0  # 카테고리 기반
                    product["recommendation_source"] = "user_stats_category"
                    products.append(product)
            except Exception as e:
                logger.warning(f"카테고리 인기 상품 조회 실패: {e}")

        # 3. 부족하면 전체 인기 상품으로 보충
        remaining = limit - len(products)
        if remaining > 0:
            existing_ids = [p["product_id"] for p in products]
            all_exclude = list(set(exclude_ids) | set(existing_ids)) or [-1]

            popular_query = """
                SELECT p.id AS product_id, p.name, p.price, p.original_price,
                       p.category_id, p.seller_id,
                       COALESCE(ps.order_event_count, 0) AS order_count,
                       COALESCE(ps.view_count, 0) AS view_count,
                       COALESCE(ps.average_rating, 0) AS average_rating
                FROM products p
                LEFT JOIN product_stats ps ON p.id = ps.product_id
                WHERE p.status = 'active'
                  AND p.id != ALL($1)
                ORDER BY COALESCE(ps.order_event_count, 0) DESC,
                         COALESCE(ps.view_count, 0) DESC
                LIMIT $2
            """

            try:
                records = await self.db.fetch_all(popular_query, all_exclude, remaining)
                for r in records:
                    product = dict(r)
                    product["recommendation_score"] = 50.0  # 인기 상품
                    product["recommendation_source"] = "user_stats_popular"
                    products.append(product)
            except Exception as e:
                logger.warning(f"전체 인기 상품 조회 실패: {e}")

        logger.info(
            "user_product_stats 폴백 추천 완료",
            extra={
                "user_id": user_id,
                "category_count": len(category_records) if category_records else 0,
                "result_count": len(products),
            }
        )

        return products

    async def _recommend_with_db(
        self,
        context: RecommendationContext,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """DB 기반 추천 (폴백)

        Args:
            context: 추천 컨텍스트
            limit: 추천 개수

        Returns:
            추천 상품 목록
        """
        # 다중 추천 전략 병렬 실행
        tasks = [
            self._get_interaction_based_recommendations(context, limit),
            self._get_embedding_based_recommendations(context, limit),
            self._get_collaborative_recommendations(context, limit),
        ]

        # 장바구니가 있으면 장바구니 기반 추천 추가
        if context.cart_product_ids:
            tasks.append(
                self._get_cart_completion_recommendations(context, limit)
            )

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 결과 취합
        all_products = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(
                    "추천 전략 실패",
                    extra={"strategy_index": i, "error": str(result)},
                )
                continue
            all_products.extend(result)

        # 최종 랭킹 및 다양성 보장
        ranked_products = self._rank_and_diversify(
            all_products, context, limit
        )

        return ranked_products

    async def _get_interaction_based_recommendations(
        self,
        context: RecommendationContext,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """상호작용 기반 추천

        최근 본 상품, 구매한 상품의 유사 상품 추천
        외부 데이터가 없으면 같은 카테고리 인기 상품으로 폴백

        Args:
            context: 추천 컨텍스트
            limit: 조회 개수

        Returns:
            추천 상품 목록
        """
        # 최근 상호작용 상품 조회
        recent_interactions = await self.user_repo.get_user_recent_interactions(
            user_id=context.user_id,
            limit=20,
        )

        if not recent_interactions:
            # 상호작용이 없으면 인기 상품 반환
            return await self._get_popular_products_fallback(limit)

        # 최근 상호작용 상품 ID 추출
        recent_product_ids = [p["product_id"] for p in recent_interactions]

        # 외부 유사도 데이터 시도
        try:
            similar_products = await self.item_similarity_repo.get_frequently_bought_together(
                product_ids=recent_product_ids[:10],
                limit=limit,
            )
        except Exception as e:
            logger.warning(f"유사 상품 조회 실패, 폴백 사용: {e}")
            similar_products = []

        # 유사 상품이 없으면 카테고리 기반 폴백
        if not similar_products:
            return await self._get_category_based_fallback(
                recent_interactions, recent_product_ids, limit
            )

        # 이미 상호작용한 상품 제외
        filtered_products = [
            p for p in similar_products
            if p.get("product_id") not in recent_product_ids
        ]

        for product in filtered_products:
            product["_score"] = product.get("avg_similarity", 0) * 100
            product["_source"] = "interaction_similarity"

        return filtered_products

    async def _get_category_based_fallback(
        self,
        recent_interactions: List[Dict[str, Any]],
        exclude_ids: List[int],
        limit: int,
    ) -> List[Dict[str, Any]]:
        """카테고리 기반 폴백 추천

        사용자가 관심 보인 카테고리의 인기 상품 추천

        Args:
            recent_interactions: 최근 상호작용 정보
            exclude_ids: 제외할 상품 ID
            limit: 조회 개수

        Returns:
            추천 상품 목록
        """
        # 사용자가 상호작용한 카테고리 추출
        category_ids = list(set(
            p.get("category_id") for p in recent_interactions
            if p.get("category_id")
        ))

        if not category_ids:
            return await self._get_popular_products_fallback(limit)

        # 해당 카테고리의 인기 상품 조회 (SelF 자체 데이터 사용)
        query = """
            SELECT p.id AS product_id, p.name, p.price, p.category_id,
                   p.seller_id,
                   COALESCE(ps.order_event_count, 0) AS order_count,
                   COALESCE(ps.view_count, 0) AS view_count,
                   COALESCE(ps.average_rating, 0) AS average_rating
            FROM products p
            LEFT JOIN product_stats ps ON p.id = ps.product_id
            WHERE p.category_id = ANY($1)
              AND p.id != ALL($2)
              AND p.status = 'active'
            ORDER BY COALESCE(ps.order_event_count, 0) DESC,
                     COALESCE(ps.view_count, 0) DESC
            LIMIT $3
        """

        records = await self.db.fetch_all(query, category_ids, exclude_ids, limit)
        products = []
        for record in records:
            product = dict(record)
            # 점수 계산: 주문 * 5 + 조회 * 1
            product["_score"] = product.get("order_count", 0) * 5 + product.get("view_count", 0)
            product["_source"] = "category_popularity"
            products.append(product)

        return products

    async def _get_popular_products_fallback(
        self,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """전체 인기 상품 폴백

        모든 카테고리에서 인기 상품 추천

        Args:
            limit: 조회 개수

        Returns:
            인기 상품 목록
        """
        query = """
            SELECT p.id AS product_id, p.name, p.price, p.category_id,
                   p.seller_id,
                   COALESCE(ps.order_event_count, 0) AS order_count,
                   COALESCE(ps.view_count, 0) AS view_count,
                   COALESCE(ps.average_rating, 0) AS average_rating
            FROM products p
            LEFT JOIN product_stats ps ON p.id = ps.product_id
            WHERE p.status = 'active'
            ORDER BY COALESCE(ps.order_event_count, 0) DESC,
                     COALESCE(ps.view_count, 0) DESC
            LIMIT $1
        """

        records = await self.db.fetch_all(query, limit)
        products = []
        for record in records:
            product = dict(record)
            product["_score"] = product.get("order_count", 0) * 5 + product.get("view_count", 0)
            product["_source"] = "global_popularity"
            products.append(product)

        return products

    async def _get_embedding_based_recommendations(
        self,
        context: RecommendationContext,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """임베딩 기반 추천

        사용자 임베딩과 상품 임베딩의 유사도 기반 추천
        임베딩 데이터가 없으면 빈 목록 반환 (다른 전략이 커버)

        Args:
            context: 추천 컨텍스트
            limit: 조회 개수

        Returns:
            추천 상품 목록
        """
        try:
            # 사용자 임베딩 조회
            user_embedding = await self.user_embedding_repo.get_user_embedding(
                user_id=context.user_id
            )

            if not user_embedding or not user_embedding.get("embedding_vector"):
                # 임베딩이 없으면 빈 목록 (다른 전략이 보완)
                return []

            # 최근 상호작용 상품 (제외용)
            recent_interactions = await self.user_repo.get_user_recent_interactions(
                user_id=context.user_id,
                limit=50,
            )
            exclude_ids = [p["product_id"] for p in recent_interactions]

            # 임베딩 유사도 기반 상품 검색
            similar_products = await self.embedding_repo.find_similar_products_by_embedding(
                embedding_vector=user_embedding["embedding_vector"],
                limit=limit,
                exclude_product_ids=exclude_ids,
            )

            for product in similar_products:
                product["_score"] = product.get("similarity", 0) * 100
                product["_source"] = "embedding_similarity"

            return similar_products
        except Exception as e:
            logger.warning(f"임베딩 기반 추천 실패: {e}")
            return []

    async def _get_collaborative_recommendations(
        self,
        context: RecommendationContext,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """협업 필터링 기반 추천

        유사 사용자가 구매한 상품 추천
        유사 사용자 데이터가 없으면 같은 상품을 본 다른 사용자 기반 추천

        Args:
            context: 추천 컨텍스트
            limit: 조회 개수

        Returns:
            추천 상품 목록
        """
        try:
            # 유사 사용자 찾기 (임베딩 기반)
            similar_users = await self.user_embedding_repo.find_similar_users(
                user_id=context.user_id,
                limit=10,
            )
        except Exception as e:
            logger.warning(f"유사 사용자 검색 실패: {e}")
            similar_users = []

        # 임베딩 기반 유사 사용자가 없으면 상호작용 기반 폴백
        if not similar_users:
            return await self._get_collaborative_fallback(context, limit)

        # 현재 사용자가 상호작용한 상품 (제외용)
        my_interactions = await self.user_repo.get_user_recent_interactions(
            user_id=context.user_id,
            limit=100,
        )
        my_product_ids = set(p["product_id"] for p in my_interactions)

        # 유사 사용자들의 상품 수집
        products_from_similar_users = {}

        for sim_user in similar_users[:5]:  # 상위 5명만 사용
            sim_user_id = sim_user["user_id"]
            similarity = sim_user.get("similarity", 0.5)

            # 유사 사용자의 주문 상품
            sim_user_products = await self.user_repo.get_user_ordered_products(
                user_id=sim_user_id,
                limit=20,
            )

            for product in sim_user_products:
                pid = product.get("product_id")
                if pid and pid not in my_product_ids:
                    if pid not in products_from_similar_users:
                        products_from_similar_users[pid] = {
                            **product,
                            "_score": 0,
                            "_source": "collaborative",
                        }
                    # 유사도 가중치 적용
                    products_from_similar_users[pid]["_score"] += similarity * 10

        result = list(products_from_similar_users.values())
        result.sort(key=lambda x: x["_score"], reverse=True)

        return result[:limit]

    async def _get_collaborative_fallback(
        self,
        context: RecommendationContext,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """협업 필터링 폴백 - 같은 상품을 본/구매한 사용자들의 다른 관심 상품

        Args:
            context: 추천 컨텍스트
            limit: 조회 개수

        Returns:
            추천 상품 목록
        """
        # 현재 사용자가 상호작용한 상품 조회
        my_interactions = await self.user_repo.get_user_recent_interactions(
            user_id=context.user_id,
            limit=10,
        )

        if not my_interactions:
            return []

        my_product_ids = [p["product_id"] for p in my_interactions]

        # 같은 상품과 상호작용한 다른 사용자들이 관심 가진 상품 조회
        query = """
            WITH similar_users AS (
                -- 같은 상품과 상호작용한 다른 사용자
                SELECT DISTINCT user_id
                FROM user_product_stats
                WHERE product_id = ANY($1)
                  AND user_id != $2
                LIMIT 50
            ),
            other_products AS (
                -- 유사 사용자들의 다른 관심 상품
                SELECT ups.product_id,
                       SUM(ups.order_event_count * 5 + ups.cart_event_count * 3 + ups.view_count) AS score,
                       COUNT(DISTINCT ups.user_id) AS user_count
                FROM user_product_stats ups
                JOIN similar_users su ON ups.user_id = su.user_id
                WHERE ups.product_id != ALL($1)
                GROUP BY ups.product_id
                HAVING COUNT(DISTINCT ups.user_id) >= 2
            )
            SELECT op.product_id, op.score, op.user_count,
                   p.name, p.price, p.category_id, p.seller_id
            FROM other_products op
            JOIN products p ON op.product_id = p.id
            WHERE p.status = 'active'
            ORDER BY op.user_count DESC, op.score DESC
            LIMIT $3
        """

        try:
            records = await self.db.fetch_all(query, my_product_ids, context.user_id, limit)
            products = []
            for record in records:
                product = dict(record)
                product["_score"] = product.get("score", 0) * product.get("user_count", 1)
                product["_source"] = "collaborative_fallback"
                products.append(product)
            return products
        except Exception as e:
            logger.warning(f"협업 필터링 폴백 실패: {e}")
            return []

    async def _get_cart_completion_recommendations(
        self,
        context: RecommendationContext,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """장바구니 완성 추천

        장바구니 상품과 함께 자주 구매되는 상품 추천

        Args:
            context: 추천 컨텍스트
            limit: 조회 개수

        Returns:
            추천 상품 목록
        """
        products = await self.item_similarity_repo.get_cart_based_recommendations(
            cart_product_ids=context.cart_product_ids,
            limit=limit,
        )

        for product in products:
            product["_score"] = product.get("weighted_score", 0) * 1.5
            product["_source"] = "cart_completion"

        return products

    def _rank_and_diversify(
        self,
        products: List[Dict[str, Any]],
        context: RecommendationContext,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """최종 랭킹 및 다양성 보장

        MMR (Maximal Marginal Relevance) 기반 다양성 보장

        Args:
            products: 후보 상품 목록
            context: 추천 컨텍스트
            limit: 최종 개수

        Returns:
            랭킹 및 다양화된 상품 목록
        """
        if not products:
            return []

        # 중복 제거
        seen_ids = set()
        unique_products = []
        for product in products:
            pid = product.get("product_id") or product.get("id")
            if pid and pid not in seen_ids:
                seen_ids.add(pid)
                unique_products.append(product)

        # 점수 기준 정렬
        unique_products.sort(key=lambda x: x.get("_score", 0), reverse=True)

        # MMR 기반 다양성 보장
        lambda_param = 0.7  # 관련성 vs 다양성 균형
        selected = []
        remaining = unique_products.copy()

        while len(selected) < limit and remaining:
            if not selected:
                # 첫 번째는 최고 점수 상품
                selected.append(remaining.pop(0))
                continue

            # MMR 점수 계산
            best_idx = 0
            best_mmr = float("-inf")

            selected_categories = set(
                p.get("category_id") for p in selected if p.get("category_id")
            )

            for i, product in enumerate(remaining):
                relevance = product.get("_score", 0)

                # 다양성: 이미 선택된 카테고리와의 거리
                diversity = 1.0
                if product.get("category_id") in selected_categories:
                    diversity = 0.5  # 같은 카테고리는 페널티

                mmr = lambda_param * relevance + (1 - lambda_param) * diversity * 100

                if mmr > best_mmr:
                    best_mmr = mmr
                    best_idx = i

            selected.append(remaining.pop(best_idx))

        # 내부 필드 → recommendation_source로 변환 후 제거
        for product in selected:
            product.pop("_score", None)
            # _source가 있으면 recommendation_source로 변환
            source = product.pop("_source", None)
            if source and "recommendation_source" not in product:
                product["recommendation_source"] = f"db_{source}"

        return selected

    def _calculate_confidence(
        self,
        context: RecommendationContext,
        products: List[Dict[str, Any]],
    ) -> float:
        """개인화 신뢰도 계산

        Args:
            context: 추천 컨텍스트
            products: 추천 상품 목록

        Returns:
            신뢰도 (0.0 ~ 1.0)
        """
        if not products:
            return 0.0

        # 사용자 유형에 따른 기본 신뢰도
        base_confidence = {
            "warm": 0.9,
            "lukewarm": 0.7,
            "cold": 0.4,
        }.get(context.user_type, 0.5)

        # 결과 개수에 따른 조정
        result_ratio = min(1.0, len(products) / 10.0)

        return base_confidence * result_ratio
