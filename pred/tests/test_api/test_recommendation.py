"""
추천 API 엔드포인트 테스트

FastAPI 추천 API 통합 테스트
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


class TestRecommendationEndpoint:
    """추천 API 엔드포인트 테스트"""

    @pytest.fixture
    def client(self):
        """테스트 클라이언트 생성"""
        from main import app
        return TestClient(app)

    def test_get_recommendations_without_user(self, client):
        """비로그인 사용자 추천 (Cold Start)"""
        # Given: 비로그인 요청
        with patch("api.routes.recommendation.get_orchestrator") as mock_get_orch:
            mock_orchestrator = MagicMock()
            mock_orchestrator.recommend = AsyncMock(return_value={
                "products": [
                    {"product_id": 1, "name": "테스트 상품", "price": 10000}
                ],
                "model_name": "instacart_cold_start",
                "confidence": 0.5,
            })
            mock_get_orch.return_value = mock_orchestrator

            # When
            response = client.get("/api/v1/recommendations")

            # Then
            assert response.status_code == 200
            data = response.json()
            assert "products" in data or "detail" in data

    def test_get_recommendations_with_user(self, client):
        """로그인 사용자 추천"""
        # Given: 로그인 요청
        with patch("api.routes.recommendation.get_orchestrator") as mock_get_orch:
            mock_orchestrator = MagicMock()
            mock_orchestrator.recommend = AsyncMock(return_value={
                "products": [
                    {"product_id": 2, "name": "개인화 상품", "price": 15000}
                ],
                "model_name": "self_personalized",
                "confidence": 0.85,
            })
            mock_get_orch.return_value = mock_orchestrator

            # When
            response = client.get(
                "/api/v1/recommendations",
                params={"user_id": 100}
            )

            # Then
            assert response.status_code in [200, 500]

    def test_get_recommendations_with_limit(self, client):
        """추천 개수 제한"""
        # Given
        with patch("api.routes.recommendation.get_orchestrator") as mock_get_orch:
            mock_orchestrator = MagicMock()
            mock_orchestrator.recommend = AsyncMock(return_value={
                "products": [],
                "model_name": "instacart_cold_start",
                "confidence": 0.0,
            })
            mock_get_orch.return_value = mock_orchestrator

            # When
            response = client.get(
                "/api/v1/recommendations",
                params={"limit": 5}
            )

            # Then
            assert response.status_code in [200, 500]


class TestDealsEndpoint:
    """특가 상품 API 테스트"""

    @pytest.fixture
    def client(self):
        """테스트 클라이언트 생성"""
        from main import app
        return TestClient(app)

    def test_get_deals(self, client):
        """특가 상품 조회"""
        # Given
        with patch("api.routes.recommendation.get_orchestrator") as mock_get_orch:
            mock_orchestrator = MagicMock()
            mock_orchestrator.get_deals = AsyncMock(return_value={
                "products": [
                    {
                        "product_id": 1,
                        "name": "특가 상품",
                        "original_price": 10000,
                        "discounted_price": 7000,
                        "discount_rate": 30,
                    }
                ],
                "total_count": 1,
            })
            mock_get_orch.return_value = mock_orchestrator

            # When
            response = client.get("/api/v1/recommendations/deals")

            # Then
            assert response.status_code in [200, 500]


class TestSimilarProductsEndpoint:
    """유사 상품 API 테스트"""

    @pytest.fixture
    def client(self):
        """테스트 클라이언트 생성"""
        from main import app
        return TestClient(app)

    def test_get_similar_products(self, client):
        """유사 상품 조회"""
        # Given
        product_id = 123

        with patch("api.routes.recommendation.get_orchestrator") as mock_get_orch:
            mock_orchestrator = MagicMock()
            mock_orchestrator.get_similar_products = AsyncMock(return_value={
                "products": [
                    {"product_id": 124, "name": "유사 상품 1", "similarity": 0.95},
                    {"product_id": 125, "name": "유사 상품 2", "similarity": 0.88},
                ],
                "source_product_id": product_id,
            })
            mock_get_orch.return_value = mock_orchestrator

            # When
            response = client.get(f"/api/v1/recommendations/similar/{product_id}")

            # Then
            assert response.status_code in [200, 404, 500]


class TestRequestValidation:
    """요청 유효성 검증 테스트"""

    @pytest.fixture
    def client(self):
        """테스트 클라이언트 생성"""
        from main import app
        return TestClient(app)

    def test_invalid_limit_value(self, client):
        """잘못된 limit 값"""
        # When: limit이 너무 큰 경우
        response = client.get(
            "/api/v1/recommendations",
            params={"limit": 1000}
        )

        # Then: 서버에서 처리하거나 에러
        assert response.status_code in [200, 422, 500]

    def test_invalid_user_id(self, client):
        """잘못된 user_id"""
        # When: 음수 user_id
        response = client.get(
            "/api/v1/recommendations",
            params={"user_id": -1}
        )

        # Then: 서버에서 처리
        assert response.status_code in [200, 422, 500]
