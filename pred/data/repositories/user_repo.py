"""
사용자 데이터 Repository

기존 users, user_profiles 테이블에서 데이터를 조회합니다.
"""

from typing import Any, Dict, List, Optional

from data.repositories.base import ReadOnlyRepository
from core.database import Database
from core.logging import get_logger

logger = get_logger(__name__)


class UserRepository(ReadOnlyRepository):
    """사용자 데이터 Repository

    기존 Django users 테이블 읽기 전용 접근
    """

    @property
    def table_name(self) -> str:
        return "users"

    async def get_user_with_profile(
        self,
        user_id: int,
    ) -> Optional[Dict[str, Any]]:
        """사용자 정보 (프로필 포함) 조회

        Args:
            user_id: 사용자 ID

        Returns:
            사용자 정보 딕셔너리
        """
        query = """
            SELECT u.id, u.email, u.username, u.role, u.is_active,
                   u.last_login, u.date_joined,
                   up.gender, up.date_of_birth, up.timezone, up.language
            FROM users u
            LEFT JOIN user_profiles up ON u.id = up.user_id
            WHERE u.id = $1 AND u.is_active = true
        """

        record = await self.db.fetch_one(query, user_id)
        return self._record_to_dict(record) if record else None

    async def get_users_by_ids(
        self,
        user_ids: List[int],
    ) -> List[Dict[str, Any]]:
        """여러 사용자 조회

        Args:
            user_ids: 사용자 ID 목록

        Returns:
            사용자 목록
        """
        if not user_ids:
            return []

        query = """
            SELECT u.id, u.email, u.username, u.role, u.is_active,
                   u.last_login, u.date_joined
            FROM users u
            WHERE u.id = ANY($1) AND u.is_active = true
        """

        records = await self.db.fetch_all(query, user_ids)
        return self._records_to_list(records)

    async def get_active_users_count(self) -> int:
        """활성 사용자 수 조회

        Returns:
            활성 사용자 수
        """
        query = "SELECT COUNT(*) FROM users WHERE is_active = true"
        count = await self.db.fetch_val(query)
        return count or 0


class UserInteractionRepository(ReadOnlyRepository):
    """사용자 상호작용 데이터 Repository

    장바구니, 위시리스트, 주문 등 사용자 행동 데이터 조회
    """

    @property
    def table_name(self) -> str:
        return "user_product_stats"

    async def get_user_interaction_count(
        self,
        user_id: int,
    ) -> Dict[str, int]:
        """사용자 상호작용 횟수 조회 (cold/lukewarm/warm 분류용)

        Args:
            user_id: 사용자 ID

        Returns:
            상호작용 횟수 딕셔너리
        """
        query = """
            SELECT
                COALESCE(SUM(view_count), 0) AS total_views,
                COALESCE(SUM(cart_event_count), 0) AS total_carts,
                COALESCE(SUM(order_event_count), 0) AS total_orders,
                COUNT(*) AS interacted_products
            FROM user_product_stats
            WHERE user_id = $1
        """

        record = await self.db.fetch_one(query, user_id)
        if record:
            return {
                "total_views": record["total_views"],
                "total_carts": record["total_carts"],
                "total_orders": record["total_orders"],
                "interacted_products": record["interacted_products"],
            }
        return {
            "total_views": 0,
            "total_carts": 0,
            "total_orders": 0,
            "interacted_products": 0,
        }

    async def get_user_recent_interactions(
        self,
        user_id: int,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """최근 상호작용한 상품 조회

        Args:
            user_id: 사용자 ID
            limit: 조회 개수

        Returns:
            최근 상호작용 상품 목록
        """
        query = """
            SELECT ups.product_id, ups.view_count, ups.cart_event_count,
                   ups.order_event_count, ups.last_interacted_at,
                   p.name, p.price, p.category_id
            FROM user_product_stats ups
            JOIN products p ON ups.product_id = p.id
            WHERE ups.user_id = $1 AND p.status = 'active'
            ORDER BY ups.last_interacted_at DESC
            LIMIT $2
        """

        records = await self.db.fetch_all(query, user_id, limit)
        return self._records_to_list(records)

    async def get_user_ordered_products(
        self,
        user_id: int,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """사용자가 주문한 상품 목록 조회

        Args:
            user_id: 사용자 ID
            limit: 조회 개수

        Returns:
            주문한 상품 목록
        """
        query = """
            SELECT DISTINCT oi.product_id, p.name, p.price, p.category_id,
                   p.seller_id, MAX(o.created_at) AS last_ordered_at
            FROM orders o
            JOIN order_items oi ON o.id = oi.order_id
            JOIN products p ON oi.product_id = p.id
            WHERE o.user_id = $1
              AND o.status NOT IN ('cancelled', 'refunded')
            GROUP BY oi.product_id, p.name, p.price, p.category_id, p.seller_id
            ORDER BY last_ordered_at DESC
            LIMIT $2
        """

        records = await self.db.fetch_all(query, user_id, limit)
        return self._records_to_list(records)

    async def get_user_cart_items(
        self,
        user_id: int,
    ) -> List[Dict[str, Any]]:
        """사용자 장바구니 상품 조회

        Args:
            user_id: 사용자 ID

        Returns:
            장바구니 상품 목록
        """
        query = """
            SELECT c.product_id, c.quantity, c.created_at,
                   p.name, p.price, p.category_id, p.seller_id, p.status
            FROM carts c
            JOIN products p ON c.product_id = p.id
            WHERE c.user_id = $1
            ORDER BY c.created_at DESC
        """

        records = await self.db.fetch_all(query, user_id)
        return self._records_to_list(records)

    async def get_user_wishlist(
        self,
        user_id: int,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """사용자 위시리스트 조회

        Args:
            user_id: 사용자 ID
            limit: 조회 개수

        Returns:
            위시리스트 상품 목록
        """
        query = """
            SELECT w.product_id, w.created_at,
                   p.name, p.price, p.category_id, p.seller_id, p.status
            FROM wishlists w
            JOIN products p ON w.product_id = p.id
            WHERE w.user_id = $1
            ORDER BY w.created_at DESC
            LIMIT $2
        """

        records = await self.db.fetch_all(query, user_id, limit)
        return self._records_to_list(records)

    async def get_user_preferred_categories(
        self,
        user_id: int,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """사용자 선호 카테고리 조회 (주문/장바구니/조회 기반)

        Args:
            user_id: 사용자 ID
            limit: 조회 개수

        Returns:
            선호 카테고리 목록 (점수 내림차순)
        """
        query = """
            WITH category_scores AS (
                SELECT p.category_id,
                       SUM(
                           ups.order_event_count * 5 +
                           ups.cart_event_count * 3 +
                           ups.view_count * 1
                       ) AS score
                FROM user_product_stats ups
                JOIN products p ON ups.product_id = p.id
                WHERE ups.user_id = $1 AND p.category_id IS NOT NULL
                GROUP BY p.category_id
            )
            SELECT cs.category_id, cs.score, c.name AS category_name
            FROM category_scores cs
            JOIN categories c ON cs.category_id = c.id
            ORDER BY cs.score DESC
            LIMIT $2
        """

        records = await self.db.fetch_all(query, user_id, limit)
        return self._records_to_list(records)

    async def get_user_followed_sellers(
        self,
        user_id: int,
    ) -> List[Dict[str, Any]]:
        """사용자가 팔로우한 판매자 조회

        Args:
            user_id: 사용자 ID

        Returns:
            팔로우한 판매자 목록
        """
        query = """
            SELECT sf.seller_id, sf.created_at AS followed_at,
                   s.brand_name, s.logo_url
            FROM seller_follows sf
            JOIN sellers s ON sf.seller_id = s.id
            WHERE sf.user_id = $1
            ORDER BY sf.created_at DESC
        """

        records = await self.db.fetch_all(query, user_id)
        return self._records_to_list(records)
