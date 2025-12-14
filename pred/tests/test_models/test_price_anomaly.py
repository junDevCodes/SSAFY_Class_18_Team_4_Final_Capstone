"""
PriceAnomaly 모델 테스트

가격 이상치 탐지 모델 단위 테스트
"""

import pytest
import numpy as np
from unittest.mock import AsyncMock, MagicMock


class TestPriceAnomalyDetection:
    """가격 이상치 탐지 테스트"""

    def test_zscore_detection_with_anomaly(self):
        """Z-Score 기반 이상치 탐지 - 이상치 케이스"""
        # Given: 평균 10000원, 표준편차 1000원인 가격 이력
        prices = [10000, 9500, 10500, 10200, 9800, 10100, 9900]
        current_price = 7000  # Z-Score = -3.0

        # When: Z-Score 계산
        mean = np.mean(prices)
        std = np.std(prices)
        z_score = (current_price - mean) / std

        # Then: 이상치로 판정 (Z < -2)
        assert z_score < -2.0
        assert abs(z_score) > 2.0

    def test_zscore_detection_without_anomaly(self):
        """Z-Score 기반 이상치 탐지 - 정상 케이스"""
        # Given: 가격 이력
        prices = [10000, 9500, 10500, 10200, 9800, 10100, 9900]
        current_price = 9700  # 정상 범위

        # When: Z-Score 계산
        mean = np.mean(prices)
        std = np.std(prices)
        z_score = (current_price - mean) / std

        # Then: 정상으로 판정 (-2 <= Z <= 2)
        assert abs(z_score) < 2.0

    def test_iqr_detection_with_anomaly(self):
        """IQR 기반 이상치 탐지 - 이상치 케이스"""
        # Given: 가격 이력
        prices = [10000, 9500, 10500, 10200, 9800, 10100, 9900, 10300, 9600, 10400]
        current_price = 5000  # IQR 하한보다 낮음

        # When: IQR 계산
        q1 = np.percentile(prices, 25)
        q3 = np.percentile(prices, 75)
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr

        # Then: 이상치로 판정
        assert current_price < lower_bound

    def test_iqr_detection_without_anomaly(self):
        """IQR 기반 이상치 탐지 - 정상 케이스"""
        # Given: 가격 이력
        prices = [10000, 9500, 10500, 10200, 9800, 10100, 9900, 10300, 9600, 10400]
        current_price = 9800

        # When: IQR 계산
        q1 = np.percentile(prices, 25)
        q3 = np.percentile(prices, 75)
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr

        # Then: 정상 범위 내
        assert lower_bound <= current_price <= upper_bound

    def test_ma_detection_with_anomaly(self):
        """이동평균 기반 이상치 탐지 - 이상치 케이스"""
        # Given: 7일 이동평균 10000원
        ma_7 = 10000
        current_price = 8000  # 20% 하락

        # When: MA 대비 하락률 계산
        drop_rate = (current_price - ma_7) / ma_7

        # Then: 15% 이상 하락시 이상치
        assert drop_rate < -0.15

    def test_anomaly_score_calculation(self):
        """이상치 점수 계산 테스트"""
        # Given: 여러 탐지 방법 결과
        detection_methods = ["zscore", "iqr", "ma"]
        scores = [0.8, 0.7, 0.6]

        # When: 앙상블 점수 계산
        base_score = sum(scores) / len(scores)
        # 다중 탐지 보너스 (10% per method)
        bonus = 1 + 0.1 * len(detection_methods)
        final_score = min(base_score * bonus, 1.0)

        # Then: 점수가 0~1 범위
        assert 0 <= final_score <= 1.0


class TestPriceAnomalyModel:
    """PriceAnomaly 모델 통합 테스트"""

    @pytest.mark.asyncio
    async def test_detect_anomalies_empty_category(self, mock_db):
        """카테고리 지정 없이 전체 이상치 탐지"""
        from ml.models.price_anomaly import PriceAnomalyModel

        # Given
        model = PriceAnomalyModel(mock_db)

        # Mock 데이터 설정
        mock_db.fetch_all = AsyncMock(return_value=[
            {
                "product_id": 1,
                "current_price": 7000,
                "previous_price": 10000,
                "price_change_rate": -30.0,
                "category_id": 1,
            }
        ])

        # When
        results = await model.detect_anomalies(category_id=None)

        # Then
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_detect_anomalies_with_category(self, mock_db):
        """특정 카테고리 이상치 탐지"""
        from ml.models.price_anomaly import PriceAnomalyModel

        # Given
        model = PriceAnomalyModel(mock_db)
        category_id = 1

        mock_db.fetch_all = AsyncMock(return_value=[])

        # When
        results = await model.detect_anomalies(category_id=category_id)

        # Then
        assert isinstance(results, list)


class TestPriceHistoryRepository:
    """가격 이력 Repository 테스트"""

    @pytest.mark.asyncio
    async def test_get_price_dropped_products(self, mock_db):
        """가격 하락 상품 조회 테스트"""
        from data.repositories import PriceHistoryRepository

        # Given
        repo = PriceHistoryRepository(mock_db)
        mock_db.fetch_all = AsyncMock(return_value=[
            {
                "product_id": 1,
                "price": 7000,
                "price_change_rate": -30.0,
            }
        ])

        # When
        results = await repo.get_price_dropped_products(
            min_drop_rate=20.0,
            category_id=None,
            limit=10,
        )

        # Then
        assert isinstance(results, list)
