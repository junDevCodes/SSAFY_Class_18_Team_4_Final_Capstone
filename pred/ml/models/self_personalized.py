"""
SelF Personalized 추천 모델

상호작용 이력이 있는 사용자를 위한 개인화 추천

모드:
1. Pickle 모드: 사전 학습된 임베딩/유사도 행렬 사용 (프로덕션)
2. DB 모드: 실시간 DB 쿼리 기반 추천 (폴백/개발)
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
    - Pickle 모드: 사전 학습된 SVD 임베딩 활용 (프로덕션)
    - DB 모드: 실시간 쿼리 기반 추천 (폴백)
    - 사용자 상호작용 이력 기반 개인화
    - 협업 필터링 (유사 사용자 기반)
    - Cold start용 인기 상품 캐시 활용
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
        """모델 초기화 - pickle 모델 로드 시도"""
        # Pickle 모델 로드 시도
        self._pickle_model = model_loader.get_model("self_personalized")

        if self._pickle_model:
            self._use_pickle = True
            logger.info(
                "Pickle 모델 로드 완료 (self_personalized)",
                extra={"version": self.model_version}
            )
        else:
            self._use_pickle = False
            logger.info("Pickle 모델 없음, DB 폴백 모드로 동작")

        self._initialized = True

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
            # Pickle 추천 실패 시 DB 폴백
            logger.info("Pickle 추천 결과 없음, DB 폴백 사용")

        # DB 기반 추천 (폴백)
        return await self._recommend_with_db(context, limit)

    async def _recommend_with_pickle(
        self,
        context: RecommendationContext,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """Pickle 모델 기반 추천 (임베딩 유사도)

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

        # Warm/Lukewarm user: 임베딩 유사도 기반
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

    async def _recommend_personalized_pickle(
        self,
        context: RecommendationContext,
        limit: int,
        components: Dict,
    ) -> List[Dict[str, Any]]:
        """개인화 추천 (Pickle 기반 임베딩 유사도)

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

        # 내부 필드 제거
        for product in selected:
            product.pop("_score", None)
            product.pop("_source", None)

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
