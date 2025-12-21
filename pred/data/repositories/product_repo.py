"""
상품 데이터 Repository

기존 products 테이블에서 데이터를 조회합니다.
"""

from typing import Any, Dict, List, Optional

from data.repositories.base import ReadOnlyRepository
from core.database import Database
from core.logging import get_logger

logger = get_logger(__name__)


class ProductRepository(ReadOnlyRepository):
    """상품 데이터 Repository

    기존 Django products 테이블 읽기 전용 접근
    """

    @property
    def table_name(self) -> str:
        return "products"

    async def get_active_products(
        self,
        category_id: Optional[int] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """활성 상품 목록 조회

        Args:
            category_id: 카테고리 ID (선택적)
            limit: 조회 개수
            offset: 시작 위치

        Returns:
            상품 목록
        """
        query = """
            SELECT p.id, p.name, p.slug, p.price, p.original_price,
                   p.category_id, p.seller_id, p.status, p.product_type,
                   p.unit, p.created_at
            FROM products p
            WHERE p.status = 'active'
        """
        params = []

        if category_id:
            query += " AND p.category_id = $1"
            params.append(category_id)

        query += f" ORDER BY p.created_at DESC LIMIT ${len(params)+1} OFFSET ${len(params)+2}"
        params.extend([limit, offset])

        records = await self.db.fetch_all(query, *params)
        return self._records_to_list(records)

    async def get_products_by_ids(
        self,
        product_ids: List[int],
        active_only: bool = True,
    ) -> List[Dict[str, Any]]:
        """상품 ID 목록으로 조회

        Args:
            product_ids: 상품 ID 목록
            active_only: 활성 상품만 조회 여부

        Returns:
            상품 목록
        """
        if not product_ids:
            return []

        query = """
            SELECT p.id, p.name, p.slug, p.price, p.original_price,
                   p.category_id, p.seller_id, p.status, p.product_type,
                   p.unit, p.created_at
            FROM products p
            WHERE p.id = ANY($1)
        """
        if active_only:
            query += " AND p.status = 'active'"

        query += " ORDER BY p.created_at DESC"

        records = await self.db.fetch_all(query, product_ids)
        return self._records_to_list(records)

    async def get_popular_products_by_categories(
        self,
        category_ids: List[int],
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """카테고리별 인기 상품 조회

        Args:
            category_ids: 카테고리 ID 목록
            limit: 조회 개수

        Returns:
            인기 상품 목록
        """
        if not category_ids:
            return []

        query = """
            SELECT p.id, p.name, p.slug, p.price, p.original_price,
                   p.category_id, p.seller_id, p.status,
                   ps.view_count, ps.order_event_count, ps.average_rating
            FROM products p
            JOIN product_stats ps ON p.id = ps.product_id
            WHERE p.category_id = ANY($1)
              AND p.status = 'active'
            ORDER BY ps.order_event_count DESC, ps.view_count DESC
            LIMIT $2
        """

        records = await self.db.fetch_all(query, category_ids, limit)
        return self._records_to_list(records)

    async def get_product_with_stats(
        self,
        product_id: int,
    ) -> Optional[Dict[str, Any]]:
        """상품 상세 정보 (통계 포함) 조회

        Args:
            product_id: 상품 ID

        Returns:
            상품 상세 정보
        """
        query = """
            SELECT p.id, p.name, p.slug, p.price, p.original_price,
                   p.category_id, p.seller_id, p.status, p.product_type,
                   p.unit, p.created_at,
                   ps.view_count, ps.cart_event_count, ps.order_event_count,
                   ps.wishlist_count, ps.review_count, ps.average_rating,
                   c.name AS category_name
            FROM products p
            LEFT JOIN product_stats ps ON p.id = ps.product_id
            LEFT JOIN categories c ON p.category_id = c.id
            WHERE p.id = $1
        """

        record = await self.db.fetch_one(query, product_id)
        return self._record_to_dict(record) if record else None

    async def search_products(
        self,
        query_text: str,
        category_id: Optional[int] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """상품 검색

        Args:
            query_text: 검색어
            category_id: 카테고리 ID (선택적)
            limit: 조회 개수

        Returns:
            검색 결과
        """
        query = """
            SELECT p.id, p.name, p.slug, p.price, p.original_price,
                   p.category_id, p.status,
                   ps.view_count, ps.order_event_count
            FROM products p
            LEFT JOIN product_stats ps ON p.id = ps.product_id
            WHERE p.status = 'active'
              AND (p.name ILIKE $1 OR p.slug ILIKE $1)
        """
        params = [f"%{query_text}%"]

        if category_id:
            query += " AND p.category_id = $2"
            params.append(category_id)

        query += f" ORDER BY ps.order_event_count DESC NULLS LAST LIMIT ${len(params)+1}"
        params.append(limit)

        records = await self.db.fetch_all(query, *params)
        return self._records_to_list(records)

    async def get_category_products_count(
        self,
        category_id: int,
    ) -> int:
        """카테고리별 활성 상품 수 조회

        Args:
            category_id: 카테고리 ID

        Returns:
            상품 수
        """
        query = """
            SELECT COUNT(*) FROM products
            WHERE category_id = $1 AND status = 'active'
        """
        count = await self.db.fetch_val(query, category_id)
        return count or 0


class ProductStatsRepository(ReadOnlyRepository):
    """상품 통계 Repository"""

    @property
    def table_name(self) -> str:
        return "product_stats"

    async def get_top_products_by_metric(
        self,
        metric: str,
        category_id: Optional[int] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """특정 지표 기준 상위 상품 조회

        Args:
            metric: 정렬 기준 (view_count, order_event_count, average_rating)
            category_id: 카테고리 ID (선택적)
            limit: 조회 개수

        Returns:
            상위 상품 목록
        """
        # SQL Injection 방지를 위한 화이트리스트
        allowed_metrics = [
            'view_count', 'order_event_count', 'cart_event_count',
            'wishlist_count', 'average_rating', 'review_count'
        ]
        if metric not in allowed_metrics:
            metric = 'order_event_count'

        query = f"""
            SELECT ps.product_id, ps.{metric}, ps.view_count,
                   ps.order_event_count, ps.average_rating,
                   p.name, p.price, p.category_id
            FROM product_stats ps
            JOIN products p ON ps.product_id = p.id
            WHERE p.status = 'active'
        """
        params = []

        if category_id:
            query += " AND p.category_id = $1"
            params.append(category_id)

        query += f" ORDER BY ps.{metric} DESC NULLS LAST LIMIT ${len(params)+1}"
        params.append(limit)

        records = await self.db.fetch_all(query, *params)
        return self._records_to_list(records)
