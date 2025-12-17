"""
Instacart 데이터 Repository

Instacart 데이터셋 기반의 cold start 추천을 위한 데이터 접근.
핵심: 32M 주문 데이터 대신 pre-aggregated 168개 시간 패턴 사용
"""

from typing import Any, Dict, List, Optional

from data.repositories.base import ReadOnlyRepository, WritableRepository
from core.database import Database
from core.logging import get_logger

logger = get_logger(__name__)


class InstacartTimePatternRepository(ReadOnlyRepository):
    """시간대별 인기 상품 패턴 Repository

    핵심 최적화: 32M 주문 레코드 대신 168개(24시간 × 7요일) 패턴 사용
    """

    @property
    def table_name(self) -> str:
        return "pred_instacart_time_pattern"

    async def get_patterns_by_time(
        self,
        day_of_week: int,
        hour_of_day: int,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """특정 시간대 인기 상품 패턴 조회

        Args:
            day_of_week: 요일 (0=월요일, 6=일요일)
            hour_of_day: 시간 (0-23)
            limit: 조회 개수

        Returns:
            시간대 인기 상품 패턴 목록
        """
        query = """
            SELECT department_id, aisle_id, top_product_ids,
                   order_count, reorder_rate, avg_cart_position,
                   updated_at
            FROM pred_instacart_time_pattern
            WHERE day_of_week = $1 AND hour_of_day = $2
            ORDER BY order_count DESC
            LIMIT $3
        """

        records = await self.db.fetch_all(query, day_of_week, hour_of_day, limit)
        return self._records_to_list(records)

    async def get_patterns_by_time_range(
        self,
        day_of_week: int,
        start_hour: int,
        end_hour: int,
    ) -> List[Dict[str, Any]]:
        """시간 범위별 패턴 조회 (예: 오전 6시-12시)

        Args:
            day_of_week: 요일
            start_hour: 시작 시간
            end_hour: 종료 시간

        Returns:
            시간 범위 내 패턴 목록
        """
        query = """
            SELECT department_id, aisle_id, top_product_ids,
                   SUM(order_count) AS total_orders,
                   AVG(reorder_rate) AS avg_reorder_rate,
                   AVG(avg_cart_position) AS avg_position
            FROM pred_instacart_time_pattern
            WHERE day_of_week = $1
              AND hour_of_day >= $2
              AND hour_of_day < $3
            GROUP BY department_id, aisle_id, top_product_ids
            ORDER BY total_orders DESC
        """

        records = await self.db.fetch_all(
            query, day_of_week, start_hour, end_hour
        )
        return self._records_to_list(records)

    async def get_time_context_patterns(
        self,
        time_context: str,
        is_weekend: bool,
    ) -> List[Dict[str, Any]]:
        """시간 컨텍스트별 패턴 조회

        Args:
            time_context: 'morning', 'lunch', 'dinner', 'night'
            is_weekend: 주말 여부

        Returns:
            컨텍스트별 패턴 목록
        """
        # 시간 컨텍스트 매핑
        time_ranges = {
            "morning": (6, 11),
            "lunch": (11, 14),
            "dinner": (17, 21),
            "night": (21, 6),
        }

        start_hour, end_hour = time_ranges.get(time_context, (6, 22))

        # 주말/주중 요일 설정
        if is_weekend:
            days = [5, 6]  # 토, 일
        else:
            days = [0, 1, 2, 3, 4]  # 월-금

        query = """
            SELECT department_id, aisle_id, top_product_ids,
                   SUM(order_count) AS total_orders,
                   AVG(reorder_rate) AS avg_reorder_rate
            FROM pred_instacart_time_pattern
            WHERE day_of_week = ANY($1)
              AND (
                  (hour_of_day >= $2 AND hour_of_day < $3)
                  OR ($2 > $3 AND (hour_of_day >= $2 OR hour_of_day < $3))
              )
            GROUP BY department_id, aisle_id, top_product_ids
            ORDER BY total_orders DESC
            LIMIT 50
        """

        records = await self.db.fetch_all(query, days, start_hour, end_hour)
        return self._records_to_list(records)


class InstacartCategoryMappingRepository(ReadOnlyRepository):
    """Instacart-SelF 카테고리 매핑 Repository

    Instacart 카테고리를 SelF 카테고리로 매핑
    """

    @property
    def table_name(self) -> str:
        return "pred_instacart_category_mapping"

    async def get_self_category_id(
        self,
        instacart_aisle_id: int,
    ) -> Optional[int]:
        """Instacart aisle ID → SelF category ID 변환

        Args:
            instacart_aisle_id: Instacart aisle ID

        Returns:
            SelF category ID
        """
        query = """
            SELECT self_category_id
            FROM pred_instacart_category_mapping
            WHERE instacart_aisle_id = $1
        """

        return await self.db.fetch_val(query, instacart_aisle_id)

    async def get_all_mappings(self) -> Dict[int, int]:
        """전체 카테고리 매핑 조회

        Returns:
            {instacart_aisle_id: self_category_id} 딕셔너리
        """
        query = """
            SELECT instacart_aisle_id, self_category_id
            FROM pred_instacart_category_mapping
        """

        records = await self.db.fetch_all(query)
        return {r["instacart_aisle_id"]: r["self_category_id"] for r in records}

    async def get_instacart_categories_for_self(
        self,
        self_category_id: int,
    ) -> List[int]:
        """SelF 카테고리에 매핑된 Instacart aisle 목록

        Args:
            self_category_id: SelF 카테고리 ID

        Returns:
            매핑된 Instacart aisle ID 목록
        """
        query = """
            SELECT instacart_aisle_id
            FROM pred_instacart_category_mapping
            WHERE self_category_id = $1
        """

        records = await self.db.fetch_all(query, self_category_id)
        return [r["instacart_aisle_id"] for r in records]


class InstacartProductMappingRepository(ReadOnlyRepository):
    """Instacart-SelF 상품 매핑 Repository"""

    @property
    def table_name(self) -> str:
        return "pred_product_mapping"

    async def get_self_products_for_instacart(
        self,
        instacart_product_ids: List[int],
    ) -> Dict[int, int]:
        """Instacart 상품 → SelF 상품 변환

        Args:
            instacart_product_ids: Instacart 상품 ID 목록

        Returns:
            {instacart_product_id: self_product_id} 딕셔너리
        """
        if not instacart_product_ids:
            return {}

        query = """
            SELECT instacart_product_id, self_product_id
            FROM pred_product_mapping
            WHERE instacart_product_id = ANY($1)
              AND self_product_id IS NOT NULL
        """

        records = await self.db.fetch_all(query, instacart_product_ids)
        return {r["instacart_product_id"]: r["self_product_id"] for r in records}

    async def get_similar_self_products(
        self,
        instacart_product_id: int,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Instacart 상품과 유사한 SelF 상품 조회

        매핑이 없는 경우 같은 aisle의 상품을 추천

        Args:
            instacart_product_id: Instacart 상품 ID
            limit: 조회 개수

        Returns:
            유사 SelF 상품 목록
        """
        # 먼저 직접 매핑 확인
        direct_query = """
            SELECT self_product_id
            FROM pred_product_mapping
            WHERE instacart_product_id = $1
              AND self_product_id IS NOT NULL
        """
        direct_result = await self.db.fetch_val(direct_query, instacart_product_id)

        if direct_result:
            # 직접 매핑이 있으면 해당 상품 반환
            query = """
                SELECT p.id AS product_id, p.name, p.price, p.category_id
                FROM products p
                WHERE p.id = $1 AND p.status = 'active'
            """
            record = await self.db.fetch_one(query, direct_result)
            return [dict(record)] if record else []

        # 없으면 같은 aisle의 상품 찾기
        similar_query = """
            WITH instacart_info AS (
                SELECT aisle_id FROM pred_instacart_products
                WHERE id = $1
            ),
            mapped_category AS (
                SELECT icm.self_category_id
                FROM pred_instacart_category_mapping icm
                JOIN instacart_info ii ON icm.instacart_aisle_id = ii.aisle_id
            )
            SELECT p.id AS product_id, p.name, p.price, p.category_id,
                   ps.order_event_count
            FROM products p
            JOIN product_stats ps ON p.id = ps.product_id
            WHERE p.category_id = (SELECT self_category_id FROM mapped_category)
              AND p.status = 'active'
            ORDER BY ps.order_event_count DESC
            LIMIT $2
        """

        records = await self.db.fetch_all(similar_query, instacart_product_id, limit)
        return self._records_to_list(records)


class InstacartItemSimilarityRepository(ReadOnlyRepository):
    """아이템 유사도 Repository

    pre-computed item-item similarity 조회
    """

    @property
    def table_name(self) -> str:
        return "pred_item_similarity"

    async def get_similar_items(
        self,
        product_id: int,
        similarity_type: str = "copurchase",
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """유사 아이템 조회

        Args:
            product_id: 상품 ID
            similarity_type: 'copurchase', 'embedding', 'category'
            limit: 조회 개수

        Returns:
            유사 아이템 목록
        """
        query = """
            SELECT pis.similar_product_id, pis.similarity_score,
                   pis.similarity_type, pis.co_occurrence_count,
                   p.name, p.price, p.category_id
            FROM pred_item_similarity pis
            JOIN products p ON pis.similar_product_id = p.id
            WHERE pis.product_id = $1
              AND pis.similarity_type = $2
              AND p.status = 'active'
            ORDER BY pis.similarity_score DESC
            LIMIT $3
        """

        records = await self.db.fetch_all(
            query, product_id, similarity_type, limit
        )
        return self._records_to_list(records)

    async def get_frequently_bought_together(
        self,
        product_ids: List[int],
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """함께 구매되는 상품 조회

        Args:
            product_ids: 기준 상품 ID 목록
            limit: 조회 개수

        Returns:
            함께 구매되는 상품 목록
        """
        if not product_ids:
            return []

        query = """
            SELECT pis.similar_product_id AS product_id,
                   SUM(pis.co_occurrence_count) AS total_co_occurrence,
                   AVG(pis.similarity_score) AS avg_similarity,
                   p.name, p.price, p.category_id
            FROM pred_item_similarity pis
            JOIN products p ON pis.similar_product_id = p.id
            WHERE pis.product_id = ANY($1)
              AND pis.similarity_type = 'copurchase'
              AND pis.similar_product_id != ALL($1)
              AND p.status = 'active'
            GROUP BY pis.similar_product_id, p.name, p.price, p.category_id
            ORDER BY total_co_occurrence DESC, avg_similarity DESC
            LIMIT $2
        """

        records = await self.db.fetch_all(query, product_ids, limit)
        return self._records_to_list(records)

    async def get_cart_based_recommendations(
        self,
        cart_product_ids: List[int],
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """장바구니 기반 추천 (함께 구매 확률 높은 상품)

        Args:
            cart_product_ids: 장바구니 상품 ID 목록
            limit: 조회 개수

        Returns:
            추천 상품 목록
        """
        if not cart_product_ids:
            return []

        query = """
            WITH cart_similarities AS (
                SELECT pis.similar_product_id,
                       SUM(pis.similarity_score * pis.co_occurrence_count) AS weighted_score,
                       COUNT(*) AS match_count
                FROM pred_item_similarity pis
                WHERE pis.product_id = ANY($1)
                  AND pis.similarity_type = 'copurchase'
                  AND pis.similar_product_id != ALL($1)
                GROUP BY pis.similar_product_id
            )
            SELECT cs.similar_product_id AS product_id,
                   cs.weighted_score,
                   cs.match_count,
                   p.name, p.price, p.category_id
            FROM cart_similarities cs
            JOIN products p ON cs.similar_product_id = p.id
            WHERE p.status = 'active'
            ORDER BY cs.match_count DESC, cs.weighted_score DESC
            LIMIT $2
        """

        records = await self.db.fetch_all(query, cart_product_ids, limit)
        return self._records_to_list(records)
