"""
Instacart Cold Start 추천 모델

신규/비로그인 사용자를 위한 시간대별 인기 상품 추천
Instacart 데이터셋의 32M 주문 데이터를 168개 시간 패턴으로 사전 집계하여 사용

Pickle 하이브리드 패턴:
- Pickle 모델이 로드되면 사전 집계된 time_patterns와 category_mapping 사용
- Pickle 모델이 없으면 DB Repository로 fallback
"""

from typing import Any, Dict, List, Optional

from ml.base import ColdStartModel, RecommendationContext
from data.repositories.instacart_repo import (
    InstacartTimePatternRepository,
    InstacartCategoryMappingRepository,
    InstacartItemSimilarityRepository,
)
from data.repositories.product_repo import ProductRepository
from core.database import Database
from core.cache import CacheManager
from core.logging import get_logger
from ml.model_loader import model_loader

logger = get_logger(__name__)


class InstacartColdStartModel(ColdStartModel):
    """Instacart 기반 Cold Start 추천 모델

    핵심 특징:
    - 32M Instacart 주문 데이터를 168개 시간 패턴으로 사전 집계
    - 시간대(morning/lunch/dinner/night) + 요일(주중/주말) 기반 추천
    - Instacart 카테고리 → SelF 카테고리 매핑 활용
    - 실시간 쿼리 대신 pre-aggregated 데이터로 빠른 응답

    Pickle 하이브리드 패턴:
    - Pickle 모델이 로드되면 time_patterns, category_mapping 사용
    - Pickle 모델이 없으면 DB Repository로 fallback
    """

    def __init__(
        self,
        db: Database,
        cache: Optional[CacheManager] = None,
    ):
        super().__init__(db, cache)
        self.time_pattern_repo = InstacartTimePatternRepository(db)
        self.category_mapping_repo = InstacartCategoryMappingRepository(db)
        self.item_similarity_repo = InstacartItemSimilarityRepository(db)
        self.product_repo = ProductRepository(db)

        # Pickle 모델 로드 시도
        self._pickle_model = model_loader.get_model("instacart_cold_start")
        if self._pickle_model:
            logger.info("Instacart Cold Start: Pickle 모델 로드됨")
        else:
            logger.info("Instacart Cold Start: DB fallback 모드")

    @property
    def model_name(self) -> str:
        return "instacart_cold_start"

    @property
    def model_version(self) -> str:
        return "1.0.0"

    async def _recommend(
        self,
        context: RecommendationContext,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """Cold Start 추천 로직

        Pickle 모델이 있으면 사전 집계된 시간 패턴 사용,
        없으면 DB Repository로 fallback

        Args:
            context: 추천 컨텍스트
            limit: 추천 개수

        Returns:
            추천 상품 목록
        """
        # Pickle 모델이 로드되어 있으면 Pickle 기반 추천
        if self._pickle_model:
            return await self._recommend_with_pickle(context, limit)

        # DB fallback 모드
        return await self._recommend_with_db(context, limit)

    async def _recommend_with_pickle(
        self,
        context: RecommendationContext,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """Pickle 모델 기반 Cold Start 추천

        time_patterns에서 현재 시간대의 top_aisles를 조회하고
        category_mapping을 통해 SelF 카테고리로 변환하여 상품 추천

        Pickle-only 모드: DB 쿼리 실패 시 graceful하게 처리

        Args:
            context: 추천 컨텍스트
            limit: 추천 개수

        Returns:
            추천 상품 목록
        """
        components = self._pickle_model.get("components", {})
        time_patterns = components.get("time_patterns", {})
        category_mapping = components.get("category_mapping", {})
        global_popular_aisles = components.get("global_popular_aisles", [])

        products = []

        # 1. 시간대별 패턴 기반 추천 (Pickle)
        try:
            time_based = await self._get_time_based_pickle(
                context, time_patterns, category_mapping, limit * 2
            )
            products.extend(time_based)
        except Exception as e:
            logger.warning(f"시간대별 Pickle 추천 실패 (무시하고 계속): {e}")

        # 2. 시간대 패턴이 부족하면 전역 인기 aisle 사용
        if len(products) < limit:
            try:
                global_based = await self._get_global_popular_pickle(
                    global_popular_aisles, category_mapping, limit
                )
                products.extend(global_based)
            except Exception as e:
                logger.warning(f"전역 인기 Pickle 추천 실패 (무시하고 계속): {e}")

        # 3. 카테고리 컨텍스트가 있으면 해당 카테고리 인기 상품 추가 (DB - optional)
        if context.category_id:
            try:
                category_based = await self._get_category_recommendations(
                    context.category_id, limit
                )
                products.extend(category_based)
            except Exception as e:
                logger.warning(f"카테고리 추천 DB 쿼리 실패 (무시하고 계속): {e}")

        # 4. 장바구니가 있으면 함께 구매하는 상품 추가 (DB - optional)
        # 주의: pred_item_similarity 테이블이 없을 수 있음
        if context.cart_product_ids:
            try:
                cart_based = await self._get_cart_based_recommendations(
                    context.cart_product_ids, limit
                )
                products.extend(cart_based)
            except Exception as e:
                logger.warning(f"장바구니 기반 추천 DB 쿼리 실패 (무시하고 계속): {e}")

        # 중복 제거 및 점수 기반 정렬
        unique_products = self._deduplicate_and_rank(products)

        return unique_products[:limit]

    async def _get_time_based_pickle(
        self,
        context: RecommendationContext,
        time_patterns: Dict,
        category_mapping: Dict,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """Pickle에서 시간대별 인기 상품 추천

        Args:
            context: 추천 컨텍스트
            time_patterns: {(day_of_week, hour_of_day): {..., 'top_aisles': [...]}}
            category_mapping: {instacart_aisle_id: self_category_id}
            limit: 조회 개수

        Returns:
            시간대별 인기 상품 목록
        """
        # 현재 시간 패턴 조회
        pattern_key = (context.day_of_week, context.hour_of_day)
        pattern = time_patterns.get(pattern_key, {})

        if not pattern:
            # 가장 가까운 시간대 패턴 찾기
            for offset in range(1, 4):
                for delta in [offset, -offset]:
                    new_hour = (context.hour_of_day + delta) % 24
                    alt_key = (context.day_of_week, new_hour)
                    if alt_key in time_patterns:
                        pattern = time_patterns[alt_key]
                        break
                if pattern:
                    break

        if not pattern:
            return []

        # top_aisles에서 SelF 카테고리 추출
        top_aisles = pattern.get("top_aisles", [])
        self_category_ids = set()
        aisle_scores = {}

        for aisle_info in top_aisles:
            aisle_id = aisle_info.get("aisle_id")
            if aisle_id and aisle_id in category_mapping:
                self_category_id = category_mapping[aisle_id]
                self_category_ids.add(self_category_id)
                # aisle의 order_count를 점수로 저장
                aisle_scores[self_category_id] = aisle_info.get("order_count", 0)

        if not self_category_ids:
            return []

        # SelF 카테고리의 인기 상품 조회 (DB)
        products = await self.product_repo.get_popular_products_by_categories(
            category_ids=list(self_category_ids),
            limit=limit,
        )

        # 점수 추가
        for product in products:
            cat_id = product.get("category_id")
            base_score = product.get("order_event_count", 0)
            time_bonus = aisle_scores.get(cat_id, 0)
            product["_score"] = base_score + time_bonus * 0.1
            product["_source"] = "pickle_time_pattern"

        return products

    async def _get_global_popular_pickle(
        self,
        global_popular_aisles: List[int],
        category_mapping: Dict,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """Pickle에서 전역 인기 aisle 기반 추천

        Args:
            global_popular_aisles: [aisle_id, ...]
            category_mapping: {instacart_aisle_id: self_category_id}
            limit: 조회 개수

        Returns:
            전역 인기 상품 목록
        """
        # 전역 인기 aisle → SelF 카테고리
        self_category_ids = []
        for aisle_id in global_popular_aisles[:20]:  # 상위 20개 aisle만
            if aisle_id in category_mapping:
                cat_id = category_mapping[aisle_id]
                if cat_id not in self_category_ids:
                    self_category_ids.append(cat_id)

        if not self_category_ids:
            return []

        # SelF 카테고리의 인기 상품 조회 (DB)
        products = await self.product_repo.get_popular_products_by_categories(
            category_ids=self_category_ids[:10],  # 상위 10개 카테고리
            limit=limit,
        )

        for product in products:
            product["_score"] = product.get("order_event_count", 0) * 0.8
            product["_source"] = "pickle_global_popular"

        return products

    async def _recommend_with_db(
        self,
        context: RecommendationContext,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """DB Repository 기반 Cold Start 추천 (fallback)

        DB 테이블이 없을 수 있으므로 각 쿼리마다 예외 처리

        Args:
            context: 추천 컨텍스트
            limit: 추천 개수

        Returns:
            추천 상품 목록
        """
        products = []

        # 1. 시간대별 패턴 기반 추천
        try:
            time_based = await self._get_time_based_recommendations(
                context, limit * 2  # 후처리를 위해 더 많이 가져옴
            )
            products.extend(time_based)
        except Exception as e:
            logger.warning(f"시간대별 DB 추천 실패 (무시하고 계속): {e}")

        # 2. 카테고리 컨텍스트가 있으면 해당 카테고리 인기 상품 추가
        if context.category_id:
            try:
                category_based = await self._get_category_recommendations(
                    context.category_id, limit
                )
                products.extend(category_based)
            except Exception as e:
                logger.warning(f"카테고리 DB 추천 실패 (무시하고 계속): {e}")

        # 3. 장바구니가 있으면 함께 구매하는 상품 추가
        if context.cart_product_ids:
            try:
                cart_based = await self._get_cart_based_recommendations(
                    context.cart_product_ids, limit
                )
                products.extend(cart_based)
            except Exception as e:
                logger.warning(f"장바구니 기반 DB 추천 실패 (무시하고 계속): {e}")

        # 중복 제거 및 점수 기반 정렬
        unique_products = self._deduplicate_and_rank(products)

        return unique_products[:limit]

    async def _get_time_based_recommendations(
        self,
        context: RecommendationContext,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """시간대별 인기 상품 추천

        Args:
            context: 추천 컨텍스트
            limit: 조회 개수

        Returns:
            시간대별 인기 상품 목록
        """
        # 시간 컨텍스트에 따른 패턴 조회
        patterns = await self.time_pattern_repo.get_time_context_patterns(
            time_context=context.time_context,
            is_weekend=context.is_weekend,
        )

        if not patterns:
            # 패턴이 없으면 현재 시간 기준으로 조회
            patterns = await self.time_pattern_repo.get_patterns_by_time(
                day_of_week=context.day_of_week,
                hour_of_day=context.hour_of_day,
                limit=limit,
            )

        # 카테고리 매핑 로드
        category_mappings = await self.category_mapping_repo.get_all_mappings()

        # Instacart 패턴에서 SelF 상품 ID 추출
        self_category_ids = set()
        for pattern in patterns:
            instacart_aisle = pattern.get("aisle_id")
            if instacart_aisle and instacart_aisle in category_mappings:
                self_category_ids.add(category_mappings[instacart_aisle])

        if not self_category_ids:
            return []

        # SelF 카테고리의 인기 상품 조회
        products = await self.product_repo.get_popular_products_by_categories(
            category_ids=list(self_category_ids),
            limit=limit,
        )

        # 점수 추가 (시간대 패턴 order_count 기반)
        pattern_scores = {
            p.get("aisle_id"): p.get("total_orders", p.get("order_count", 0))
            for p in patterns
        }

        for product in products:
            # 카테고리 기반 점수 계산
            base_score = product.get("order_event_count", 0)
            time_bonus = sum(
                pattern_scores.get(aid, 0)
                for aid, cid in category_mappings.items()
                if cid == product.get("category_id")
            )
            product["_score"] = base_score + time_bonus * 0.1
            product["_source"] = "time_pattern"

        return products

    async def _get_category_recommendations(
        self,
        category_id: int,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """카테고리 인기 상품 추천

        Args:
            category_id: 카테고리 ID
            limit: 조회 개수

        Returns:
            카테고리 인기 상품 목록
        """
        products = await self.product_repo.get_popular_products_by_categories(
            category_ids=[category_id],
            limit=limit,
        )

        for product in products:
            product["_score"] = product.get("order_event_count", 0) * 1.5  # 카테고리 가중치
            product["_source"] = "category"

        return products

    async def _get_cart_based_recommendations(
        self,
        cart_product_ids: List[int],
        limit: int,
    ) -> List[Dict[str, Any]]:
        """장바구니 기반 함께 구매하는 상품 추천

        Args:
            cart_product_ids: 장바구니 상품 ID 목록
            limit: 조회 개수

        Returns:
            함께 구매하는 상품 목록
        """
        products = await self.item_similarity_repo.get_cart_based_recommendations(
            cart_product_ids=cart_product_ids,
            limit=limit,
        )

        for product in products:
            product["_score"] = product.get("weighted_score", 0) * 2.0  # 장바구니 가중치
            product["_source"] = "cart_similarity"

        return products

    def _deduplicate_and_rank(
        self,
        products: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """중복 제거 및 점수 기반 정렬

        Args:
            products: 상품 목록 (중복 가능)

        Returns:
            중복 제거 및 정렬된 상품 목록
        """
        seen_ids = set()
        unique_products = []

        for product in products:
            product_id = product.get("product_id") or product.get("id")
            if product_id and product_id not in seen_ids:
                seen_ids.add(product_id)
                unique_products.append(product)

        # 점수 기반 정렬
        unique_products.sort(key=lambda x: x.get("_score", 0), reverse=True)

        # 내부 점수 필드 제거
        for product in unique_products:
            product.pop("_score", None)
            product.pop("_source", None)

        return unique_products

    def _calculate_confidence(
        self,
        context: RecommendationContext,
        products: List[Dict[str, Any]],
    ) -> float:
        """Cold Start 신뢰도 계산

        Cold Start는 개인화가 없으므로 기본 신뢰도는 낮게 설정

        Args:
            context: 추천 컨텍스트
            products: 추천 상품 목록

        Returns:
            신뢰도 (0.0 ~ 1.0)
        """
        if not products:
            return 0.0

        base_confidence = 0.5  # Cold Start 기본 신뢰도

        # 장바구니가 있으면 신뢰도 증가
        if context.cart_product_ids:
            base_confidence += 0.2

        # 카테고리 컨텍스트가 있으면 신뢰도 증가
        if context.category_id:
            base_confidence += 0.1

        # 결과 개수에 따른 조정
        result_ratio = min(1.0, len(products) / 10.0)
        base_confidence *= result_ratio

        return min(1.0, base_confidence)
