import json
from unittest.mock import MagicMock, patch

from django.conf import settings
from django.test import SimpleTestCase

from products import pred_client


class PredClientTests(SimpleTestCase):
    @patch("products.pred_client.requests.get")
    def test_pred_health_정상응답(self, mock_get):
        """Pred API 헬스 엔드포인트 호출이 올바르게 이루어지는지 검증"""
        # Arrange
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "healthy"}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        # Act
        result = pred_client.fetch_pred_health()

        # Assert
        mock_get.assert_called_once_with(
            f"{settings.ML_API_URL.rstrip('/')}/health", timeout=5
        )
        self.assertEqual(result, {"status": "healthy"})

    @patch("products.pred_client.requests.post")
    def test_pred_recommend_정상호출(self, mock_post):
        """Pred API 추천 엔드포인트 호출이 올바르게 이루어지는지 검증"""
        # Arrange
        payload = {"user_id": 1}
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "ok", "items": [123, 456]}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        # Act
        result = pred_client.request_recommendations(payload)

        # Assert
        mock_post.assert_called_once_with(
            f"{settings.ML_API_URL.rstrip('/')}/api/recommend",
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        self.assertEqual(result, {"status": "ok", "items": [123, 456]})
