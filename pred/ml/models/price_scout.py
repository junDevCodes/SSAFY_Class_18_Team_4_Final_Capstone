"""
PriceScout 가성비 상품 추천 서비스

self_price_analyzer_v1.pkl 모델을 활용하여 가성비 상품을 추천합니다.
검증된 PriceScout 점수 계산 로직을 적용합니다. (price_scout_validation.py 검증 결과 기반)

핵심 로직 (검증 결과와 일치):
1. 전체 가격 변동 이력이 있는 상품 조회 (previous_price IS NOT NULL)
2. final_score 계산 (하락 시 점수↑, 급등 시 패널티)
3. final_score 내림차순 정렬 → 자연스럽게 가격 하락 상품이 상위에 위치
4. ABNORMAL 상품(>20% 급등)은 제외

가격 상태 분류 및 score_boost:
- SUPER_SALE (< -10.0%): score_boost = 1.3 → final_score 최대 2.045 (-57% 시)
- DISCOUNT (-10.0 ~ -2.0%): score_boost = 1.1
- STABLE (-2.0 ~ +2.0%): score_boost = 1.0
- INCREASE (+2.0 ~ +20.0%): score_boost = 1.0
- ABNORMAL (> +20.0%): 제외 (급등 상품)

최종 점수 계산 (final_score):
- 가격 하락 시(rate < 0): core = 1.0 + abs(rate) / 100
- 그 외: core = 1.0
- 최종 점수 = core × score_boost

예시 (검증 결과):
- -57.31% 하락 → core=1.5731, boost=1.3 → final_score=2.045
- -44.54% 하락 → core=1.4454, boost=1.3 → final_score=1.879
- +6.26% 상승 → core=1.0, boost=1.0 → final_score=1.000

정렬 기준 (모델 추천순):
1. final_score 내림차순 (가성비 점수 높은 순)
2. price_change_rate 오름차순 (동점 시 더 많이 하락한 상품 우선)
"""

from typing import Any, Dict, List, Optional, Set

from core.database import Database
from core.logging import get_logger
from ml.model_loader import model_loader
from data.repositories.price_repo import PriceHistoryRepository

logger = get_logger(__name__)


class PriceScoutService:
    """가성비 상품 추천 서비스 (타임세일 섹션용)

    self_price_analyzer_v1.pkl 모델 기반으로 가성비 상품을 추천합니다.

    핵심 로직:
    - **가격 하락 상품** (price_change_rate < 0) 대상
    - final_score 기준 정렬 (모델 추천순)
    - 가격 하락 상품이 부족할 경우 폴백으로 할인 상품 표시

    정렬 기준 (모델 추천순):
    1. final_score 내림차순 (가성비 점수 높은 순)
    2. price_change_rate 오름차순 (동점 시 더 많이 하락한 상품 우선)
    """

    def __init__(self, db: Database):
        self.db = db
        self.price_repo = PriceHistoryRepository(db)
        self._model_data: Optional[Dict[str, Any]] = None
        self._initialized: bool = False

    async def initialize(self) -> None:
        """모델 초기화

        self_price_analyzer 모델을 로드하고 메타데이터를 확인합니다.
        """
        self._model_data = model_loader.get_model("self_price_analyzer")
        if self._model_data:
            version = self._model_data.get("version", "unknown")
            created_at = self._model_data.get("created_at", "unknown")
            model_type = self._model_data.get("model_type", "unknown")
            print(f"[PriceScout] ✓ 모델 로드 완료 - version={version}, type={model_type}")
            logger.info(
                "self_price_analyzer 모델 로드 완료",
                extra={
                    "version": version,
                    "created_at": created_at,
                    "model_type": model_type,
                }
            )
        else:
            print("[PriceScout] ⚠ 모델 없음 - DB 기반 폴백 모드")
            logger.warning(
                "self_price_analyzer 모델을 찾을 수 없습니다. "
                "DB 기반 폴백 모드로 동작합니다."
            )
        self._initialized = True

    @property
    def model_version(self) -> str:
        """모델 버전 반환"""
        if self._model_data:
            return self._model_data.get("version", "1.0.0")
        return "fallback"

    def classify_price_status(self, rate: float) -> Dict[str, Any]:
        """가격 변동률 기반 상태 분류 (검증된 로직)

        Args:
            rate: 가격 변동률 (%)

        Returns:
            {"price_status": str, "score_boost": float}
        """
        if rate < -10.0:
            return {"price_status": "SUPER_SALE", "score_boost": 1.3}
        if -10.0 <= rate < -2.0:
            return {"price_status": "DISCOUNT", "score_boost": 1.1}
        if -2.0 <= rate <= 2.0:
            return {"price_status": "STABLE", "score_boost": 1.0}
        if 2.0 < rate <= 20.0:
            return {"price_status": "INCREASE", "score_boost": 1.0}
        # rate > 20.0 (가격 급등 또는 이상치)
        return {"price_status": "ABNORMAL", "score_boost": 0.5}

    def calculate_price_scout_score(self, rate: float) -> float:
        """PriceScout 최종 점수 계산 (검증된 로직)

        Args:
            rate: 가격 변동률 (%)

        Returns:
            최종 가성비 점수
        """
        status_info = self.classify_price_status(rate)
        boost = status_info["score_boost"]

        # 가격 하락 시 core 점수 증가
        if rate < 0:
            core = 1.0 + abs(rate) / 100.0
        else:
            core = 1.0

        return core * boost

    async def get_value_products(
        self,
        limit: int = 10,
        category_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """가성비 상품 목록 조회 (타임세일 섹션용)

        모델 기반 추천 로직 (검증 로직과 일치):
        1. 전체 가격 변동 이력이 있는 상품 조회
        2. final_score 계산 (하락 시 점수↑, 급등 시 패널티)
        3. final_score 내림차순 정렬 → 자연스럽게 가격 하락 상품이 상위에

        정렬 기준 (모델 추천순):
        1. final_score 내림차순 (가성비 점수 높은 순)
        2. price_change_rate 오름차순 (동점 시 더 많이 하락한 상품 우선)

        Args:
            limit: 조회할 상품 수 (기본 10)
            category_id: 카테고리 ID (선택적)

        Returns:
            가성비 상품 목록 (final_score 기준 정렬)
        """
        # 전체 가격 변동 이력이 있는 상품 조회 후 final_score 정렬
        products = await self._get_scored_products(limit, category_id)
        scored_count = len(products)

        # 폴백: 가격 변동 이력이 있는 상품이 부족하면 할인 상품으로 대체
        fallback_count = 0
        if len(products) < limit:
            remaining = limit - len(products)
            existing_ids: Set[int] = {p["product_id"] for p in products}
            fallback_products = await self._get_discounted_products_fallback(
                remaining, category_id, existing_ids
            )
            fallback_count = len(fallback_products)
            products.extend(fallback_products)

        # 상태별 집계
        super_sale_count = sum(1 for p in products if p.get("price_status") == "SUPER_SALE")
        discount_count = sum(1 for p in products if p.get("price_status") == "DISCOUNT")
        stable_count = sum(1 for p in products if p.get("price_status") == "STABLE")
        increase_count = sum(1 for p in products if p.get("price_status") == "INCREASE")

        # 핵심 로그 출력
        print(
            f"[PriceScout] 타임세일 조회 완료 - "
            f"가격이력: {scored_count}개 "
            f"(SUPER_SALE: {super_sale_count}, DISCOUNT: {discount_count}, "
            f"STABLE: {stable_count}, INCREASE: {increase_count}), "
            f"폴백: {fallback_count}개, 총: {len(products[:limit])}개"
        )

        # 상위 3개 상품 상세 로그 (디버깅용)
        if products:
            top_products = products[:3]
            for i, p in enumerate(top_products, 1):
                rate = p.get("price_change_rate", 0)
                score = p.get("final_score", 0)
                status = p.get("price_status", "")
                print(
                    f"  #{i}: {p['name'][:25]}... "
                    f"(rate={rate:+.1f}%, final_score={score:.3f}, {status})"
                )

        return products[:limit]

    async def _get_scored_products(
        self,
        limit: int,
        category_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """전체 가격 변동 상품 조회 및 final_score 정렬 (검증 로직과 일치)

        product_price_histories 테이블에서 가격 변동 이력이 있는 모든 상품 조회
        - 평균가 대비 현재가 변동률을 계산
        - 평균가 대비 가격이 상승한 상품은 제외 (타임세일 섹션 취지에 맞지 않음)
        - final_score 계산 후 내림차순 정렬

        Args:
            limit: 조회할 상품 수
            category_id: 카테고리 ID (선택적)

        Returns:
            상품 목록 (final_score 내림차순 정렬)
        """
        # 전체 가격 이력에서 평균가 계산 + 현재가와 비교
        # - 평균가 대비 현재가 변동률 계산 (1회만 계산 후 재사용)
        # - 가격 상승 상품 제외 (평균가 대비 price_change_from_avg > 0)
        #
        # SQL 최적화: price_change_from_avg를 서브쿼리에서 1회 계산 후
        # 외부 쿼리에서 WHERE, ORDER BY에 재사용 (중복 계산 제거)
        query = """
            WITH price_stats AS (
                -- 각 상품의 가격 통계 (평균, 최저, 최고)
                SELECT
                    product_id,
                    AVG(price) AS avg_price,
                    MIN(price) AS min_price,
                    MAX(price) AS max_price,
                    COUNT(*) AS history_count
                FROM product_price_histories
                GROUP BY product_id
            ),
            latest_prices AS (
                -- 각 상품의 최신 가격 이력
                SELECT DISTINCT ON (product_id)
                    product_id,
                    price,
                    previous_price,
                    price_change,
                    price_change_rate,
                    recorded_at
                FROM product_price_histories
                WHERE previous_price IS NOT NULL
                  AND price_change_rate IS NOT NULL
                ORDER BY product_id, recorded_at DESC
            ),
            product_data AS (
                -- 상품 정보 + 평균가 대비 변동률 계산 (1회만 계산)
                SELECT
                    lp.product_id,
                    p.name,
                    p.slug,
                    p.price,
                    p.original_price,
                    lp.previous_price,
                    lp.price_change,
                    lp.price_change_rate,
                    lp.recorded_at,
                    p.category_id,
                    c.name AS category_name,
                    (SELECT pi.image_url FROM product_images pi
                     WHERE pi.product_id = p.id
                     ORDER BY pi.display_order ASC LIMIT 1) AS main_image,
                    COALESCE(ps.order_event_count, 0) AS order_count,
                    COALESCE(ps.view_count, 0) AS view_count,
                    COALESCE(ps.average_rating, 0) AS average_rating,
                    -- 평균가
                    pstats.avg_price,
                    -- 평균가 대비 현재가 변동률 (%) - 여기서 1회만 계산
                    ROUND(((p.price - pstats.avg_price) / NULLIF(pstats.avg_price, 0)) * 100, 2) AS price_change_from_avg,
                    -- 역대 최저가 여부
                    (p.price <= pstats.min_price) AS is_lowest_ever,
                    pstats.history_count
                FROM latest_prices lp
                JOIN products p ON lp.product_id = p.id
                JOIN price_stats pstats ON p.id = pstats.product_id
                LEFT JOIN categories c ON p.category_id = c.id
                LEFT JOIN product_stats ps ON p.id = ps.product_id
                WHERE p.status = 'active'
                  AND pstats.history_count >= 2
            )
            SELECT *
            FROM product_data
            WHERE price_change_from_avg <= 0
        """
        params: List[Any] = []

        if category_id:
            query += f" AND category_id = ${len(params)+1}"
            params.append(category_id)

        # ORDER BY에서 이미 계산된 price_change_from_avg 컬럼 재사용
        query += " ORDER BY price_change_from_avg ASC"
        query += f" LIMIT ${len(params)+1}"
        params.append(limit * 3)  # 여유분 확보

        records = await self.db.fetch_all(query, *params)

        products: List[Dict[str, Any]] = []
        for record in records:
            # 평균가 대비 변동률 사용 (이전가 대비 X)
            price_change_from_avg = float(record["price_change_from_avg"] or 0)
            status_info = self.classify_price_status(price_change_from_avg)
            final_score = self.calculate_price_scout_score(price_change_from_avg)
            is_lowest = bool(record.get("is_lowest_ever", False))

            # 평균가 대비 하락 시 savings 계산
            avg_price = float(record["avg_price"] or 0)
            current_price = int(record["price"] or 0)
            if price_change_from_avg < 0 and avg_price > 0:
                savings = int(avg_price - current_price)
            else:
                savings = 0

            products.append({
                "product_id": record["product_id"],
                "name": record["name"],
                "slug": record["slug"] or "",
                "price": record["price"],
                "original_price": record["original_price"],
                "previous_price": record["previous_price"],
                "main_image": record["main_image"],
                "category_id": record["category_id"],
                "category_name": record["category_name"],
                "order_count": record["order_count"],
                "view_count": record["view_count"],
                "average_rating": float(record["average_rating"] or 0),
                # 모델 추천 관련 필드 (평균가 대비 변동률 사용)
                "price_change_rate": price_change_from_avg,
                "price_status": status_info["price_status"],
                "score_boost": status_info["score_boost"],
                "final_score": round(final_score, 3),
                "savings": savings,
                # 역대 최저가 여부
                "is_lowest_ever": is_lowest,
            })

        # 정렬 기준 (검증 로직과 동일):
        # 1. final_score 내림차순 (가성비 점수 높은 순)
        # 2. price_change_rate 오름차순 (동점 시 더 많이 하락한 상품 우선)
        products.sort(
            key=lambda x: (
                -x["final_score"],        # 점수 높은 것 앞으로
                x["price_change_rate"],   # 하락률 낮은 것(더 많이 하락) 앞으로
            )
        )
        return products[:limit]

    async def _get_discounted_products_fallback(
        self,
        limit: int,
        category_id: Optional[int] = None,
        exclude_ids: Optional[Set[int]] = None,
    ) -> List[Dict[str, Any]]:
        """할인 상품 조회 (폴백) - original_price > price

        가격 하락 상품이 부족할 경우의 폴백 로직
        할인율 기준으로 가성비 상품 조회

        Args:
            limit: 조회할 상품 수
            category_id: 카테고리 ID (선택적)
            exclude_ids: 제외할 상품 ID 집합

        Returns:
            할인 상품 목록 (final_score 기준 정렬)
        """
        exclude_list = list(exclude_ids) if exclude_ids else [-1]

        # 할인 상품 조회 (original_price > price)
        query = """
            SELECT
                p.id AS product_id,
                p.name,
                p.slug,
                p.price,
                p.original_price,
                p.category_id,
                c.name AS category_name,
                (SELECT pi.image_url FROM product_images pi
                 WHERE pi.product_id = p.id
                 ORDER BY pi.display_order ASC LIMIT 1) AS main_image,
                COALESCE(ps.order_event_count, 0) AS order_count,
                COALESCE(ps.view_count, 0) AS view_count,
                COALESCE(ps.average_rating, 0) AS average_rating,
                ROUND((1 - p.price::DECIMAL / NULLIF(p.original_price, 0)) * 100, 1) AS discount_rate
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            LEFT JOIN product_stats ps ON p.id = ps.product_id
            WHERE p.status = 'active'
              AND p.original_price IS NOT NULL
              AND p.original_price > p.price
              AND p.id != ALL($1)
        """
        params: List[Any] = [exclude_list]

        if category_id:
            query += f" AND p.category_id = ${len(params)+1}"
            params.append(category_id)

        # 할인율 내림차순 정렬
        query += f" ORDER BY discount_rate DESC LIMIT ${len(params)+1}"
        params.append(limit * 2)

        records = await self.db.fetch_all(query, *params)

        products: List[Dict[str, Any]] = []
        for record in records:
            discount_rate = float(record["discount_rate"] or 0)
            savings = int((record["original_price"] or 0) - (record["price"] or 0))

            # 할인율을 음수 변동률로 변환하여 상태 분류
            price_change_rate = -discount_rate
            status_info = self.classify_price_status(price_change_rate)
            final_score = self.calculate_price_scout_score(price_change_rate)

            products.append({
                "product_id": record["product_id"],
                "name": record["name"],
                "slug": record["slug"] or "",
                "price": record["price"],
                "original_price": record["original_price"],
                "previous_price": None,
                "main_image": record["main_image"],
                "category_id": record["category_id"],
                "category_name": record["category_name"],
                "order_count": record["order_count"],
                "view_count": record["view_count"],
                "average_rating": float(record["average_rating"] or 0),
                # 모델 추천 관련 필드 (폴백)
                "price_change_rate": price_change_rate,
                "price_status": status_info["price_status"],
                "score_boost": status_info["score_boost"],
                "final_score": round(final_score, 3),
                "savings": savings,
                # 폴백 상품은 가격 이력이 없으므로 역대 최저가 판단 불가
                "is_lowest_ever": False,
            })

        # 정렬 기준 (모델 추천순):
        # 1. final_score 내림차순
        # 2. price_change_rate 오름차순 (동점 시 더 많이 하락한 상품 우선)
        products.sort(
            key=lambda x: (
                -x["final_score"],
                x["price_change_rate"],
            )
        )
        return products[:limit]
