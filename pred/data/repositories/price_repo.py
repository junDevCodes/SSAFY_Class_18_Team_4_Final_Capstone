"""
가격 데이터 Repository

상품 가격 이력 및 이상치 탐지용 데이터를 조회합니다.
PriceAnomaly 추천 모델에서 사용됩니다.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from data.repositories.base import ReadOnlyRepository
from core.database import Database
from core.logging import get_logger

logger = get_logger(__name__)


class PriceHistoryRepository(ReadOnlyRepository):
    """가격 이력 Repository

    product_price_histories 테이블 읽기 전용 접근
    """

    @property
    def table_name(self) -> str:
        return "product_price_histories"

    async def get_current_prices(
        self,
        product_ids: List[int],
    ) -> Dict[int, Dict[str, Any]]:
        """상품들의 현재 가격 조회

        Args:
            product_ids: 상품 ID 목록

        Returns:
            {product_id: {price, original_price, ...}} 형태의 딕셔너리
        """
        if not product_ids:
            return {}

        query = """
            SELECT pph.product_id, pph.price, pph.original_price,
                   pph.previous_price, pph.price_change, pph.price_change_rate,
                   pph.recorded_at
            FROM product_price_histories pph
            WHERE pph.product_id = ANY($1)
              AND pph.is_current = true
        """

        records = await self.db.fetch_all(query, product_ids)
        return {r["product_id"]: dict(r) for r in records}

    async def get_price_history(
        self,
        product_id: int,
        days: int = 30,
    ) -> List[Dict[str, Any]]:
        """상품의 가격 변동 이력 조회

        Args:
            product_id: 상품 ID
            days: 조회할 일수

        Returns:
            가격 이력 목록 (시간순)
        """
        since = datetime.now() - timedelta(days=days)

        query = """
            SELECT price, original_price, previous_price,
                   price_change, price_change_rate, recorded_at, source
            FROM product_price_histories
            WHERE product_id = $1 AND recorded_at >= $2
            ORDER BY recorded_at ASC
        """

        records = await self.db.fetch_all(query, product_id, since)
        return self._records_to_list(records)

    async def get_price_dropped_products(
        self,
        min_drop_rate: float = 10.0,
        category_id: Optional[int] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """가격 하락 상품 조회 (할인 상품 찾기)

        Args:
            min_drop_rate: 최소 하락률 (%)
            category_id: 카테고리 ID (선택적)
            limit: 조회 개수

        Returns:
            가격 하락 상품 목록
        """
        query = """
            SELECT pph.product_id, pph.price, pph.previous_price,
                   pph.price_change, pph.price_change_rate, pph.recorded_at,
                   p.name, p.category_id, p.seller_id
            FROM product_price_histories pph
            JOIN products p ON pph.product_id = p.id
            WHERE pph.is_current = true
              AND pph.price_change_rate < -$1
              AND p.status = 'active'
        """
        params = [min_drop_rate]

        if category_id:
            query += " AND p.category_id = $2"
            params.append(category_id)

        query += f" ORDER BY pph.price_change_rate ASC LIMIT ${len(params)+1}"
        params.append(limit)

        records = await self.db.fetch_all(query, *params)
        return self._records_to_list(records)

    async def get_price_statistics(
        self,
        product_id: int,
        days: int = 90,
    ) -> Dict[str, Any]:
        """상품 가격 통계 조회 (이상치 탐지용)

        Args:
            product_id: 상품 ID
            days: 통계 계산 기간 (일)

        Returns:
            가격 통계 딕셔너리
        """
        since = datetime.now() - timedelta(days=days)

        query = """
            SELECT
                MIN(price) AS min_price,
                MAX(price) AS max_price,
                AVG(price) AS avg_price,
                STDDEV(price) AS stddev_price,
                COUNT(*) AS record_count,
                MIN(recorded_at) AS first_recorded,
                MAX(recorded_at) AS last_recorded
            FROM product_price_histories
            WHERE product_id = $1 AND recorded_at >= $2
        """

        record = await self.db.fetch_one(query, product_id, since)
        if record:
            return dict(record)
        return {
            "min_price": None,
            "max_price": None,
            "avg_price": None,
            "stddev_price": None,
            "record_count": 0,
            "first_recorded": None,
            "last_recorded": None,
        }

    async def get_category_price_anomalies(
        self,
        category_id: int,
        z_threshold: float = 2.0,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """카테고리 내 가격 이상치 상품 조회

        Z-score 기반으로 카테고리 평균 가격 대비 이상치 탐지

        Args:
            category_id: 카테고리 ID
            z_threshold: Z-score 임계값 (기본 2.0 = 95% 신뢰구간)
            limit: 조회 개수

        Returns:
            가격 이상치 상품 목록
        """
        query = """
            WITH category_stats AS (
                SELECT AVG(p.price) AS avg_price,
                       STDDEV(p.price) AS stddev_price
                FROM products p
                WHERE p.category_id = $1 AND p.status = 'active'
            ),
            product_z_scores AS (
                SELECT p.id AS product_id, p.name, p.price,
                       p.original_price, p.seller_id,
                       (p.price - cs.avg_price) / NULLIF(cs.stddev_price, 0) AS z_score,
                       cs.avg_price AS category_avg_price
                FROM products p, category_stats cs
                WHERE p.category_id = $1 AND p.status = 'active'
            )
            SELECT product_id, name, price, original_price, seller_id,
                   z_score, category_avg_price,
                   CASE WHEN z_score < 0 THEN 'below_average' ELSE 'above_average' END AS anomaly_type
            FROM product_z_scores
            WHERE ABS(z_score) >= $2
            ORDER BY ABS(z_score) DESC
            LIMIT $3
        """

        records = await self.db.fetch_all(query, category_id, z_threshold, limit)
        return self._records_to_list(records)

    async def get_recent_price_changes(
        self,
        hours: int = 24,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """최근 가격 변동 상품 조회

        Args:
            hours: 조회할 시간 범위
            limit: 조회 개수

        Returns:
            최근 가격 변동 상품 목록
        """
        since = datetime.now() - timedelta(hours=hours)

        query = """
            SELECT pph.product_id, pph.price, pph.previous_price,
                   pph.price_change, pph.price_change_rate, pph.recorded_at,
                   p.name, p.category_id, p.seller_id
            FROM product_price_histories pph
            JOIN products p ON pph.product_id = p.id
            WHERE pph.recorded_at >= $1
              AND pph.previous_price IS NOT NULL
              AND p.status = 'active'
            ORDER BY pph.recorded_at DESC
            LIMIT $2
        """

        records = await self.db.fetch_all(query, since, limit)
        return self._records_to_list(records)


class PriceAnomalyCacheRepository(ReadOnlyRepository):
    """가격 이상치 캐시 Repository

    배치로 계산된 가격 이상치 캐시 조회
    """

    @property
    def table_name(self) -> str:
        return "pred_price_anomaly_cache"

    async def get_anomaly_products(
        self,
        category_id: Optional[int] = None,
        anomaly_type: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """캐시된 이상치 상품 조회

        Args:
            category_id: 카테고리 ID (선택적)
            anomaly_type: 이상치 유형 ('price_drop', 'price_surge', 'below_market')
            limit: 조회 개수

        Returns:
            이상치 상품 목록
        """
        query = """
            SELECT pac.product_id, pac.anomaly_type, pac.anomaly_score,
                   pac.current_price, pac.reference_price, pac.category_avg_price,
                   pac.z_score, pac.calculated_at, pac.expires_at,
                   p.name, p.category_id, p.seller_id
            FROM pred_price_anomaly_cache pac
            JOIN products p ON pac.product_id = p.id
            WHERE pac.expires_at > NOW()
              AND p.status = 'active'
        """
        params = []

        if category_id:
            query += f" AND p.category_id = ${len(params)+1}"
            params.append(category_id)

        if anomaly_type:
            query += f" AND pac.anomaly_type = ${len(params)+1}"
            params.append(anomaly_type)

        query += f" ORDER BY pac.anomaly_score DESC LIMIT ${len(params)+1}"
        params.append(limit)

        records = await self.db.fetch_all(query, *params)
        return self._records_to_list(records)

    async def get_best_deals(
        self,
        category_ids: Optional[List[int]] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """최고 할인 상품 조회 (가격 이상치 기반)

        Args:
            category_ids: 카테고리 ID 목록 (선택적)
            limit: 조회 개수

        Returns:
            최고 할인 상품 목록
        """
        query = """
            SELECT pac.product_id, pac.anomaly_score,
                   pac.current_price, pac.reference_price,
                   (pac.reference_price - pac.current_price) AS savings,
                   ROUND((1 - pac.current_price::DECIMAL / NULLIF(pac.reference_price, 0)) * 100, 1) AS discount_rate,
                   pac.calculated_at,
                   p.name, p.category_id, p.seller_id
            FROM pred_price_anomaly_cache pac
            JOIN products p ON pac.product_id = p.id
            WHERE pac.expires_at > NOW()
              AND pac.anomaly_type = 'price_drop'
              AND p.status = 'active'
              AND pac.reference_price > pac.current_price
        """
        params = []

        if category_ids:
            query += f" AND p.category_id = ANY(${len(params)+1})"
            params.append(category_ids)

        query += f" ORDER BY discount_rate DESC LIMIT ${len(params)+1}"
        params.append(limit)

        records = await self.db.fetch_all(query, *params)
        return self._records_to_list(records)
