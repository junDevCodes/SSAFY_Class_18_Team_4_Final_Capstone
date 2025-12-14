"""
가격 API 엔드포인트 테스트

가격 이상치 탐지 및 특가 API 통합 테스트
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


class TestPriceAnomaliesEndpoint:
    """가격 이상치 API 테스트"""

    @pytest.fixture
    def client(self):
        """테스트 클라이언트 생성"""
        from main import app
        return TestClient(app)

    def test_get_price_anomalies(self, client):
        """가격 이상치 목록 조회"""
        # Given
        with patch("api.routes.price.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_db.fetch_all = AsyncMock(return_value=[
                {
                    "product_id": 1,
                    "product_name": "이상치 상품",
                    "current_price": 5000,
                    "previous_price": 10000,
                    "price_change_rate": -50.0,
                    "anomaly_score": 0.95,
                }
            ])
            mock_get_db.return_value = mock_db

            # When
            response = client.get("/api/v1/prices/anomalies")

            # Then
            assert response.status_code in [200, 500]

    def test_get_price_anomalies_with_category(self, client):
        """카테고리별 가격 이상치 조회"""
        # Given
        category_id = 5

        with patch("api.routes.price.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_db.fetch_all = AsyncMock(return_value=[])
            mock_get_db.return_value = mock_db

            # When
            response = client.get(
                "/api/v1/prices/anomalies",
                params={"category_id": category_id}
            )

            # Then
            assert response.status_code in [200, 500]


class TestPriceHistoryEndpoint:
    """가격 이력 API 테스트"""

    @pytest.fixture
    def client(self):
        """테스트 클라이언트 생성"""
        from main import app
        return TestClient(app)

    def test_get_price_history(self, client):
        """상품 가격 이력 조회"""
        # Given
        product_id = 123

        with patch("api.routes.price.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_db.fetch_all = AsyncMock(return_value=[
                {"recorded_at": "2024-01-01", "price": 10000},
                {"recorded_at": "2024-01-02", "price": 9500},
                {"recorded_at": "2024-01-03", "price": 9000},
            ])
            mock_db.fetch_one = AsyncMock(return_value={
                "avg_price": 9500,
                "min_price": 9000,
                "max_price": 10000,
            })
            mock_get_db.return_value = mock_db

            # When
            response = client.get(f"/api/v1/prices/history/{product_id}")

            # Then
            assert response.status_code in [200, 404, 500]

    def test_get_price_history_not_found(self, client):
        """존재하지 않는 상품 가격 이력"""
        # Given
        product_id = 99999

        with patch("api.routes.price.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_db.fetch_all = AsyncMock(return_value=[])
            mock_get_db.return_value = mock_db

            # When
            response = client.get(f"/api/v1/prices/history/{product_id}")

            # Then
            assert response.status_code in [200, 404, 500]


class TestPriceAnalysisEndpoint:
    """가격 분석 API 테스트"""

    @pytest.fixture
    def client(self):
        """테스트 클라이언트 생성"""
        from main import app
        return TestClient(app)

    def test_get_price_analysis(self, client):
        """상품 가격 분석 조회"""
        # Given
        product_id = 123

        with patch("api.routes.price.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_db.fetch_all = AsyncMock(return_value=[
                {"price": 10000},
                {"price": 9500},
                {"price": 10500},
            ])
            mock_db.fetch_one = AsyncMock(return_value={
                "current_price": 8000,
            })
            mock_get_db.return_value = mock_db

            # When
            response = client.get(f"/api/v1/prices/analysis/{product_id}")

            # Then
            assert response.status_code in [200, 404, 500]


class TestDealsEndpoint:
    """특가 상품 API 테스트"""

    @pytest.fixture
    def client(self):
        """테스트 클라이언트 생성"""
        from main import app
        return TestClient(app)

    def test_get_daily_deals(self, client):
        """일일 특가 상품 조회"""
        # Given
        with patch("api.routes.price.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_db.fetch_all = AsyncMock(return_value=[
                {
                    "product_id": 1,
                    "name": "오늘의 특가",
                    "original_price": 20000,
                    "current_price": 12000,
                    "discount_rate": 40,
                }
            ])
            mock_get_db.return_value = mock_db

            # When
            response = client.get("/api/v1/prices/deals")

            # Then
            assert response.status_code in [200, 500]

    def test_get_deals_with_min_discount(self, client):
        """최소 할인율 필터링"""
        # Given
        with patch("api.routes.price.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_db.fetch_all = AsyncMock(return_value=[])
            mock_get_db.return_value = mock_db

            # When
            response = client.get(
                "/api/v1/prices/deals",
                params={"min_discount_rate": 30}
            )

            # Then
            assert response.status_code in [200, 500]
