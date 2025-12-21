"""
추천 관련 API 뷰 에지 케이스 테스트

- category_id 쿼리 파라미터가 숫자가 아닐 때 500 에러가 발생하지 않아야 함
- pred 서비스가 {"recommendations": null} 을 반환해도 500 에러가 발생하지 않아야 함
"""
from unittest.mock import patch

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient


class RecommendationViewsEdgeCaseTests(TestCase):
    """추천 API 뷰 에지 케이스 테스트"""

    def setUp(self):
        """공통 API 클라이언트 초기화"""
        self.client = APIClient()

    @patch("products.recommendations_views.pred_client.get_deal_recommendations")
    def test_deal_추천_invalid_category_id_500_발생하지_않음(self, mock_get_deals):
        """category_id가 숫자가 아닐 때 500 에러 대신 정상 응답을 반환해야 한다"""
        # Arrange: pred 클라이언트가 정상 응답을 반환하도록 모킹
        mock_get_deals.return_value = {"success": True, "recommendations": []}

        # Act: 숫자가 아닌 category_id로 요청
        response = self.client.get("/api/recommendations/deals/?category_id=abc")

        # Assert: 500 에러가 발생하지 않아야 하며, category_id는 None으로 전달되어야 함
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_get_deals.assert_called_once()
        _, kwargs = mock_get_deals.call_args
        self.assertIsNone(kwargs.get("category_id"))

    @patch("products.recommendations_views.pred_client.get_home_recommendations")
    def test_home_추천_recommendations_null_이어도_500_발생하지_않음(self, mock_get_home):
        """홈 추천에서 recommendations가 null이어도 TypeError 없이 응답해야 한다"""
        # Arrange: recommendations가 명시적으로 null인 응답 모킹
        mock_get_home.return_value = {"success": True, "recommendations": None}

        # Act
        response = self.client.get("/api/recommendations/home/")

        # Assert
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("products", response.data)

    @patch("products.recommendations_views.pred_client.get_home_recommendations")
    def test_home_추천_model_results_비정상값이어도_500_발생하지_않음(self, mock_get_home):
        """홈 추천에서 model_results가 None 또는 비 dict 리스트여도 에러 없이 처리해야 한다"""
        # Arrange: model_results가 [None] 인 경우
        mock_get_home.return_value = {
            "success": True,
            "recommendations": [{"product_id": 999}],
            "model_results": [None],
        }

        # Act
        response = self.client.get("/api/recommendations/home/")

        # Assert
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("products", response.data)
        # model_name은 안전하게 'unknown'으로 처리되어야 함
        self.assertEqual(response.data.get("model_name"), "unknown")

    @patch("products.recommendations_views.pred_client.get_product_recommendations")
    def test_product_추천_recommendations_null_이어도_500_발생하지_않음(self, mock_get_product):
        """상품 상세 추천에서 recommendations가 null이어도 TypeError 없이 응답해야 한다"""
        # Arrange
        mock_get_product.return_value = {"success": True, "recommendations": None}

        # Act
        response = self.client.get("/api/recommendations/product/123/")

        # Assert
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("products", response.data)

    @patch("products.recommendations_views.pred_client.get_deal_recommendations")
    def test_deal_추천_recommendations_null_이어도_500_발생하지_않음(self, mock_get_deals_null):
        """할인 추천에서 recommendations가 null이어도 TypeError 없이 응답해야 한다"""
        # Arrange
        mock_get_deals_null.return_value = {"success": True, "recommendations": None}

        # Act
        response = self.client.get("/api/recommendations/deals/")

        # Assert
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("products", response.data)


