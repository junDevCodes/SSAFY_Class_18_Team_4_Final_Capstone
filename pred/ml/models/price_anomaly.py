"""
Price Anomaly 추천 모델

가격 이상치(할인, 저평가) 상품 탐지 및 추천

모드:
1. Pickle 모드: 사전 계산된 카테고리 통계/베스트 딜 활용 (프로덕션)
2. DB 모드: 실시간 쿼리 기반 추천 (폴백/개발)
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

import pandas as pd

from ml.base import HybridModel, RecommendationContext
from ml.model_loader import model_loader
from data.repositories.price_repo import (
    PriceHistoryRepository,
    PriceAnomalyCacheRepository,
)
from data.repositories.product_repo import ProductRepository
from data.repositories.user_repo import UserInteractionRepository
from core.database import Database
from core.cache import CacheManager
from core.logging import get_logger

logger = get_logger(__name__)


class PriceAnomalyModel(HybridModel):
    """가격 이상치 추천 모델

    핵심 특징:
    - Pickle 모드: 사전 계산된 카테고리 통계/베스트 딜 활용
    - DB 모드: 실시간 쿼리 기반 할인 상품 탐지
    - Z-score 기반 카테고리 내 가격 이상치 탐지
    - 사용자 관심 카테고리 기반 개인화 할인 추천
    """

    def __init__(
        self,
        db: Database,
        cache: Optional[CacheManager] = None,
    ):
        super().__init__(db, cache)
        self.price_history_repo = PriceHistoryRepository(db)
        self.price_cache_repo = PriceAnomalyCacheRepository(db)
        self.product_repo = ProductRepository(db)
        self.user_repo = UserInteractionRepository(db)

        # 이상치 탐지 임계값
        self.z_threshold = 2.0  # Z-score 임계값 (95% 신뢰구간)
        self.min_discount_rate = 10.0  # 최소 할인율 (%)

        # Pickle 모델 데이터 (initialize에서 로드)
        self._pickle_model = None
        self._use_pickle = False

    @property
    def model_name(self) -> str:
        return "price_anomaly"

    @property
    def model_version(self) -> str:
        if self._pickle_model:
            return self._pickle_model.get("version", "1.0.0")
        return "1.0.0"

    async def initialize(self) -> None:
        """모델 초기화 - pickle 모델 로드 시도"""
        # Pickle 모델 로드 시도
        self._pickle_model = model_loader.get_model("price_anomaly")

        if self._pickle_model:
            self._use_pickle = True
            # pickle에서 하이퍼파라미터 로드
            hyperparams = self._pickle_model.get("hyperparameters", {})
            self.z_threshold = hyperparams.get("z_threshold", 2.0)
            self.min_discount_rate = hyperparams.get("min_discount_rate", 10.0)

            logger.info(
                "Pickle 모델 로드 완료 (price_anomaly)",
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
        """가격 이상치 추천 로직

        Args:
            context: 추천 컨텍스트
            limit: 추천 개수

        Returns:
            추천 상품 목록
        """
        # Pickle 모델이 있으면 사전 계산된 베스트 딜 활용
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
        """Pickle 모델 기반 추천

        카테고리 통계를 활용하여 가격 이상치(할인) 상품 탐지

        Args:
            context: 추천 컨텍스트
            limit: 추천 개수

        Returns:
            추천 상품 목록
        """
        import numpy as np

        components = self._pickle_model.get("components", {})
        hyperparams = self._pickle_model.get("hyperparameters", {})

        # 카테고리 통계 가져오기
        category_stats = components.get("category_statistics", {})
        global_stats = components.get("global_statistics", {})
        thresholds = components.get("thresholds", {})

        warning_thresh = thresholds.get("warning", hyperparams.get("warning_threshold", 2.5))
        use_log = hyperparams.get("use_log_transform", True)

        if not category_stats and not global_stats:
            # 통계 정보 없으면 DB 폴백
            return []

        # DB에서 할인 상품 조회
        query = """
            SELECT p.id AS product_id, p.name, p.price, p.original_price,
                   p.category_id, c.name AS category_name, p.seller_id,
                   (p.original_price - p.price) AS savings,
                   ROUND((1 - p.price::DECIMAL / NULLIF(p.original_price, 0)) * 100, 1) AS discount_rate,
                   COALESCE(ps.order_event_count, 0) AS order_count
            FROM products p
            LEFT JOIN product_stats ps ON p.id = ps.product_id
            LEFT JOIN categories c ON p.category_id = c.id
            WHERE p.status = 'active'
              AND p.original_price IS NOT NULL
              AND p.original_price > p.price
        """
        params = []

        if context.category_id:
            query += f" AND p.category_id = ${len(params)+1}"
            params.append(context.category_id)

        query += f" ORDER BY discount_rate DESC LIMIT ${len(params)+1}"
        params.append(limit * 3)  # 여유분

        records = await self.db.fetch_all(query, *params)
        products = []

        for record in records:
            product = dict(record)
            price = product.get("price", 0)
            category_name = product.get("category_name", "")

            # 카테고리 통계 선택
            if category_name and category_name in category_stats:
                stats = category_stats[category_name]
            elif global_stats:
                stats = global_stats
            else:
                stats = None

            # Modified Z-Score 계산
            anomaly_score = 0.0
            if stats and price > 0:
                if use_log:
                    log_price = np.log10(max(1, price))
                else:
                    log_price = price

                median = stats.get("log_median", 0)
                mad = stats.get("log_mad", 0.0001) or 0.0001

                modified_zscore = 0.6745 * (log_price - median) / mad

                # 낮은 가격(음수 z-score)은 좋은 딜
                if modified_zscore < -warning_thresh:
                    anomaly_score = abs(modified_zscore)

            # 최종 점수: 할인율 + 이상치 점수
            discount_rate = float(product.get("discount_rate", 0) or 0)
            combined_score = discount_rate * 0.7 + anomaly_score * 30 * 0.3

            product["_score"] = combined_score
            product["anomaly_score"] = round(anomaly_score, 3)
            product["_source"] = "pickle_anomaly"
            product["anomaly_reason"] = "statistical_low_price" if anomaly_score > 0 else "current_discount"
            products.append(product)

        # 점수순 정렬
        products.sort(key=lambda x: x.get("_score", 0), reverse=True)

        # 내부 필드 정리
        result = []
        for product in products[:limit]:
            score = product.pop("_score", 0)
            source = product.pop("_source", "unknown")
            product["recommendation_score"] = round(score, 2)
            product["recommendation_source"] = source
            result.append(product)

        return result

    async def _fetch_products_by_ids(
        self,
        product_ids: List[int],
    ) -> List[Dict[str, Any]]:
        """상품 ID로 상품 정보 조회"""
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
        """DB 기반 추천 (폴백)"""
        products = []

        # 1. 캐시된 이상치 상품 조회 (배치로 계산된 결과)
        cached_anomalies = await self._get_cached_anomalies(context, limit)
        products.extend(cached_anomalies)

        # 2. 최근 가격 하락 상품 조회 (실시간)
        price_dropped = await self._get_price_dropped_products(context, limit)
        products.extend(price_dropped)

        # 3. 개인화: 사용자 관심 카테고리의 할인 상품
        if context.user_type != "cold":
            personalized = await self._get_personalized_deals(context, limit)
            products.extend(personalized)

        # 중복 제거 및 점수 기반 정렬
        unique_products = self._deduplicate_and_rank(products)

        return unique_products[:limit]

    async def _get_cached_anomalies(
        self,
        context: RecommendationContext,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """캐시된 가격 이상치 조회

        배치 작업으로 미리 계산된 이상치 캐시 활용
        캐시가 없으면 현재 할인율 기반 폴백

        Args:
            context: 추천 컨텍스트
            limit: 조회 개수

        Returns:
            캐시된 이상치 상품 목록
        """
        try:
            # 최고 할인 상품 조회
            best_deals = await self.price_cache_repo.get_best_deals(
                category_ids=[context.category_id] if context.category_id else None,
                limit=limit,
            )
        except Exception as e:
            logger.warning(f"가격 이상치 캐시 조회 실패: {e}")
            best_deals = []

        # 캐시가 없으면 현재 할인율 기반 폴백
        if not best_deals:
            return await self._get_discounted_products_fallback(context, limit)

        for product in best_deals:
            # 할인율 기반 점수 계산
            discount_rate = product.get("discount_rate", 0) or 0
            product["_score"] = float(discount_rate) * 10
            product["_source"] = "cached_deal"
            product["anomaly_reason"] = "best_deal"

        return best_deals

    async def _get_discounted_products_fallback(
        self,
        context: RecommendationContext,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """현재 할인 중인 상품 조회 (폴백)

        original_price > price 인 상품 조회

        Args:
            context: 추천 컨텍스트
            limit: 조회 개수

        Returns:
            할인 상품 목록
        """
        query = """
            SELECT p.id AS product_id, p.name, p.price, p.original_price,
                   p.category_id, p.seller_id,
                   (p.original_price - p.price) AS savings,
                   ROUND((1 - p.price::DECIMAL / NULLIF(p.original_price, 0)) * 100, 1) AS discount_rate,
                   COALESCE(ps.order_event_count, 0) AS order_count
            FROM products p
            LEFT JOIN product_stats ps ON p.id = ps.product_id
            WHERE p.status = 'active'
              AND p.original_price IS NOT NULL
              AND p.original_price > p.price
        """
        params = []

        if context.category_id:
            query += f" AND p.category_id = ${len(params)+1}"
            params.append(context.category_id)

        query += f" ORDER BY discount_rate DESC, COALESCE(ps.order_event_count, 0) DESC LIMIT ${len(params)+1}"
        params.append(limit)

        records = await self.db.fetch_all(query, *params)
        products = []
        for record in records:
            product = dict(record)
            discount_rate = product.get("discount_rate", 0) or 0
            product["_score"] = float(discount_rate) * 10
            product["_source"] = "current_discount"
            product["anomaly_reason"] = "current_sale"
            products.append(product)

        return products

    async def _get_price_dropped_products(
        self,
        context: RecommendationContext,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """가격 하락 상품 조회

        최근 가격이 급격히 하락한 상품 탐지
        가격 이력 데이터가 없으면 빈 목록 반환 (다른 전략이 커버)

        Args:
            context: 추천 컨텍스트
            limit: 조회 개수

        Returns:
            가격 하락 상품 목록
        """
        try:
            products = await self.price_history_repo.get_price_dropped_products(
                min_drop_rate=self.min_discount_rate,
                category_id=context.category_id,
                limit=limit,
            )
        except Exception as e:
            logger.warning(f"가격 하락 상품 조회 실패: {e}")
            return []

        for product in products:
            # 가격 하락률 기반 점수
            drop_rate = abs(product.get("price_change_rate", 0) or 0)
            product["_score"] = float(drop_rate) * 8
            product["_source"] = "price_drop"
            product["anomaly_reason"] = "recent_price_drop"
            product["savings"] = abs(product.get("price_change", 0) or 0)

        return products

    async def _get_personalized_deals(
        self,
        context: RecommendationContext,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """개인화 할인 추천

        사용자 관심 카테고리의 할인 상품

        Args:
            context: 추천 컨텍스트
            limit: 조회 개수

        Returns:
            개인화 할인 상품 목록
        """
        try:
            # 사용자 선호 카테고리 조회
            preferred_categories = await self.user_repo.get_user_preferred_categories(
                user_id=context.user_id,
                limit=5,
            )

            if not preferred_categories:
                return []

            category_ids = [c["category_id"] for c in preferred_categories]

            # 선호 카테고리의 할인 상품
            products = []
            for category_id in category_ids[:3]:  # 상위 3개 카테고리만
                try:
                    category_deals = await self.price_history_repo.get_price_dropped_products(
                        min_drop_rate=self.min_discount_rate,
                        category_id=category_id,
                        limit=limit // 3 + 1,
                    )

                    for product in category_deals:
                        drop_rate = abs(product.get("price_change_rate", 0) or 0)
                        product["_score"] = float(drop_rate) * 12  # 개인화 가중치
                        product["_source"] = "personalized_deal"
                        product["anomaly_reason"] = "personalized_category_deal"

                    products.extend(category_deals)
                except Exception:
                    continue

            return products
        except Exception as e:
            logger.warning(f"개인화 할인 추천 실패: {e}")
            return []

    async def get_category_anomalies(
        self,
        category_id: int,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """카테고리 내 가격 이상치 조회

        Z-score 기반 통계적 이상치 탐지

        Args:
            category_id: 카테고리 ID
            limit: 조회 개수

        Returns:
            가격 이상치 상품 목록
        """
        anomalies = await self.price_history_repo.get_category_price_anomalies(
            category_id=category_id,
            z_threshold=self.z_threshold,
            limit=limit,
        )

        for product in anomalies:
            z_score = abs(product.get("z_score", 0) or 0)
            anomaly_type = product.get("anomaly_type", "unknown")

            # 평균 이하 가격(할인)에 더 높은 점수
            if anomaly_type == "below_average":
                product["_score"] = float(z_score) * 15
            else:
                product["_score"] = float(z_score) * 5

            product["_source"] = "statistical_anomaly"
            product["anomaly_reason"] = f"z_score_{anomaly_type}"

        return anomalies

    async def analyze_product_price(
        self,
        product_id: int,
    ) -> Dict[str, Any]:
        """상품 가격 분석

        개별 상품의 가격 이상 여부 분석

        Args:
            product_id: 상품 ID

        Returns:
            가격 분석 결과
        """
        # 가격 통계 조회
        stats = await self.price_history_repo.get_price_statistics(
            product_id=product_id,
            days=90,
        )

        # 가격 이력 조회
        history = await self.price_history_repo.get_price_history(
            product_id=product_id,
            days=30,
        )

        # 현재 가격 조회
        current_prices = await self.price_history_repo.get_current_prices([product_id])
        current = current_prices.get(product_id, {})

        if not current:
            return {"error": "상품을 찾을 수 없습니다"}

        current_price = current.get("price", 0)
        avg_price = stats.get("avg_price") or current_price
        stddev = stats.get("stddev_price") or 1

        # Z-score 계산
        z_score = (current_price - avg_price) / stddev if stddev > 0 else 0

        # 이상치 판정
        is_anomaly = abs(z_score) >= self.z_threshold
        anomaly_type = None
        if is_anomaly:
            anomaly_type = "below_average" if z_score < 0 else "above_average"

        return {
            "product_id": product_id,
            "current_price": current_price,
            "avg_price_90d": round(avg_price, 2) if avg_price else None,
            "min_price_90d": stats.get("min_price"),
            "max_price_90d": stats.get("max_price"),
            "stddev": round(stddev, 2) if stddev else None,
            "z_score": round(z_score, 3),
            "is_anomaly": is_anomaly,
            "anomaly_type": anomaly_type,
            "price_history": history,
            "recent_change": current.get("price_change"),
            "recent_change_rate": current.get("price_change_rate"),
        }

    def _deduplicate_and_rank(
        self,
        products: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """중복 제거 및 점수 기반 정렬

        Args:
            products: 상품 목록

        Returns:
            정렬된 고유 상품 목록
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

        # 내부 필드 정리
        for product in unique_products:
            score = product.pop("_score", 0)
            source = product.pop("_source", "unknown")
            product["recommendation_score"] = round(score, 2)
            product["recommendation_source"] = source

        return unique_products

    def _calculate_confidence(
        self,
        context: RecommendationContext,
        products: List[Dict[str, Any]],
    ) -> float:
        """신뢰도 계산

        Args:
            context: 추천 컨텍스트
            products: 추천 상품 목록

        Returns:
            신뢰도 (0.0 ~ 1.0)
        """
        if not products:
            return 0.0

        # 가격 기반 추천은 데이터 기반이므로 높은 기본 신뢰도
        base_confidence = 0.8

        # 개인화된 추천이면 신뢰도 증가
        personalized_count = sum(
            1 for p in products
            if p.get("recommendation_source") == "personalized_deal"
        )
        if personalized_count > 0:
            base_confidence += 0.1

        # 결과 개수에 따른 조정
        result_ratio = min(1.0, len(products) / 10.0)

        return min(1.0, base_confidence * result_ratio)


class SelFPriceAnalyzer:
    """가격 예측(self_price_analyzer)용 단순 분석기.

    원래는 Prophet 기반 모델을 사용하지만, 실행 환경 제약을 고려해
    직렬화된 패킷의 메타데이터만 활용하고, 시계열의 완만한 추세선을
    단순 지수이동평균(EMA)으로 근사합니다.

    price_model_validation.py 와의 인터페이스 호환만을 목표로 합니다.
    """

    def __init__(self) -> None:
        self._meta: Dict[str, Any] = {}

    def load_from_packet(self, packet: Dict[str, Any]) -> None:
        """Pickle 패킷 메타데이터 로드 (버전/스케일러 등).

        실제 Prophet 모델은 복원하지 않고,
        이후 analyze 단계에서 EMA 기반의 간단한 기대가격을 계산합니다.
        """
        self._meta = {
            "version": packet.get("version"),
            "created_at": packet.get("created_at"),
            "model_type": packet.get("model_type"),
        }

    def analyze(self, df: pd.DataFrame) -> pd.DataFrame:
        """입력 데이터에 대해 기대 가격(expected_price)을 계산.

        - 입력: 'ds' (datetime), 'y' (실제 가격) 컬럼 포함
        - 출력: 'expected_price' 컬럼이 추가된 DataFrame

        구현: y 값에 대해 span=7 의 지수이동평균(EMA)을 적용해
        완만한 추세선을 기대가격으로 사용합니다.
        """
        if "y" not in df.columns:
            raise ValueError("입력 데이터에 'y' 컬럼이 필요합니다.")
        if "ds" not in df.columns:
            raise ValueError("입력 데이터에 'ds' 컬럼이 필요합니다.")

        result = df.copy()
        result = result.sort_values("ds").reset_index(drop=True)
        y = result["y"].astype(float)

        # 간단한 추세선: 7포인트 지수이동평균
        expected = y.ewm(span=7, adjust=False).mean()
        result["expected_price"] = expected.astype(float)
        return result
