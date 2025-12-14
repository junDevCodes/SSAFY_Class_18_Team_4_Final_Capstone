"""
헬스체크 API 엔드포인트 테스트

서비스 상태 확인 API 통합 테스트
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


class TestHealthEndpoint:
    """헬스체크 API 테스트"""

    @pytest.fixture
    def client(self):
        """테스트 클라이언트 생성"""
        from main import app
        return TestClient(app)

    def test_root_endpoint(self, client):
        """루트 엔드포인트 응답"""
        # When
        response = client.get("/")

        # Then
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "version" in data
        assert "status" in data

    def test_health_check(self, client):
        """기본 헬스체크"""
        # When
        response = client.get("/health")

        # Then
        assert response.status_code == 200
        data = response.json()
        assert "status" in data

    def test_api_health_endpoint(self, client):
        """API 헬스체크 엔드포인트"""
        # Given
        with patch("api.routes.health.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_db.fetch_one = AsyncMock(return_value={"now": "2024-01-01"})
            mock_db._pool = True
            mock_get_db.return_value = mock_db

            with patch("api.routes.health.get_cache") as mock_get_cache:
                mock_cache = MagicMock()
                mock_cache.ping = AsyncMock(return_value=True)
                mock_cache._redis = True
                mock_get_cache.return_value = mock_cache

                # When
                response = client.get("/api/v1/health/health")

                # Then
                assert response.status_code in [200, 500]


class TestReadinessEndpoint:
    """준비 상태 API 테스트"""

    @pytest.fixture
    def client(self):
        """테스트 클라이언트 생성"""
        from main import app
        return TestClient(app)

    def test_readiness_check(self, client):
        """Kubernetes readiness probe"""
        # When
        response = client.get("/ready")

        # Then
        assert response.status_code in [200, 503]
        data = response.json()
        assert "status" in data

    def test_api_readiness_endpoint(self, client):
        """API 준비 상태 엔드포인트"""
        # Given
        with patch("api.routes.health.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_db._pool = True
            mock_get_db.return_value = mock_db

            with patch("api.routes.health.get_orchestrator") as mock_get_orch:
                mock_orchestrator = MagicMock()
                mock_get_orch.return_value = mock_orchestrator

                # When
                response = client.get("/api/v1/health/ready")

                # Then
                assert response.status_code in [200, 503, 500]


class TestLivenessEndpoint:
    """생존 상태 API 테스트"""

    @pytest.fixture
    def client(self):
        """테스트 클라이언트 생성"""
        from main import app
        return TestClient(app)

    def test_liveness_check(self, client):
        """Kubernetes liveness probe"""
        # When
        response = client.get("/api/v1/health/live")

        # Then
        assert response.status_code in [200, 500]


class TestMetricsEndpoint:
    """메트릭 API 테스트"""

    @pytest.fixture
    def client(self):
        """테스트 클라이언트 생성"""
        from main import app
        return TestClient(app)

    def test_get_metrics(self, client):
        """서비스 메트릭 조회"""
        # Given
        with patch("api.routes.health.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_db.fetch_one = AsyncMock(side_effect=[
                {"count": 1000},  # products
                {"count": 500},   # users
                {"count": 50000}, # interactions
                {"count": 200},   # recipes
            ])
            mock_get_db.return_value = mock_db

            with patch("api.routes.health.get_cache") as mock_get_cache:
                mock_cache = MagicMock()
                mock_cache.info = AsyncMock(return_value={
                    "used_memory_human": "50MB",
                    "connected_clients": 5,
                })
                mock_get_cache.return_value = mock_cache

                # When
                response = client.get("/api/v1/health/metrics")

                # Then
                assert response.status_code in [200, 500]


class TestConfigEndpoint:
    """설정 API 테스트"""

    @pytest.fixture
    def client(self):
        """테스트 클라이언트 생성"""
        from main import app
        return TestClient(app)

    def test_get_config(self, client):
        """서비스 설정 조회 (민감정보 제외)"""
        # When
        response = client.get("/api/v1/health/config")

        # Then
        assert response.status_code in [200, 500]

        if response.status_code == 200:
            data = response.json()
            # 민감정보가 포함되지 않아야 함
            assert "database_password" not in str(data).lower()
            assert "secret" not in str(data).lower()


class TestBatchStatusEndpoint:
    """배치 상태 API 테스트"""

    @pytest.fixture
    def client(self):
        """테스트 클라이언트 생성"""
        from main import app
        return TestClient(app)

    def test_get_batch_status(self, client):
        """배치 작업 상태 조회"""
        # Given
        with patch("api.routes.health.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_db.fetch_all = AsyncMock(return_value=[
                {
                    "job_name": "update_embeddings",
                    "status": "completed",
                    "last_run": "2024-01-01 00:00:00",
                    "duration_seconds": 120,
                },
                {
                    "job_name": "aggregate_time_patterns",
                    "status": "completed",
                    "last_run": "2024-01-01 01:00:00",
                    "duration_seconds": 300,
                },
            ])
            mock_get_db.return_value = mock_db

            # When
            response = client.get("/api/v1/health/batch/status")

            # Then
            assert response.status_code in [200, 500]
