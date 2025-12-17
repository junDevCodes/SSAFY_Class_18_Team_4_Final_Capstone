"""
pytest 설정 및 공통 fixture

테스트 환경 설정, DB/캐시 모킹, 공통 fixture 정의
"""

import asyncio
import pytest
from typing import AsyncGenerator, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

# pytest-asyncio 설정
pytest_plugins = ["pytest_asyncio"]


# ============================================================================
# 이벤트 루프 설정
# ============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """세션 범위 이벤트 루프"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# 데이터베이스 모킹
# ============================================================================

class MockDatabase:
    """테스트용 Mock 데이터베이스"""

    def __init__(self):
        self._pool = MagicMock()
        self._data: Dict[str, List[Dict]] = {}

    async def connect(self):
        pass

    async def disconnect(self):
        pass

    async def fetch_one(self, query: str, *args) -> Optional[Dict]:
        """단일 행 조회"""
        return {"count": 1, "id": 1}

    async def fetch_all(self, query: str, *args) -> List[Dict]:
        """복수 행 조회"""
        return []

    async def execute(self, query: str, *args) -> str:
        """쿼리 실행"""
        return "OK"

    def set_mock_data(self, table: str, data: List[Dict]):
        """테스트 데이터 설정"""
        self._data[table] = data


@pytest.fixture
def mock_db() -> MockDatabase:
    """Mock 데이터베이스 fixture"""
    return MockDatabase()


# ============================================================================
# 캐시 모킹
# ============================================================================

class MockCache:
    """테스트용 Mock 캐시"""

    def __init__(self):
        self._redis = MagicMock()
        self._cache: Dict[str, str] = {}

    async def connect(self):
        pass

    async def disconnect(self):
        pass

    async def get(self, key: str) -> Optional[str]:
        return self._cache.get(key)

    async def set(self, key: str, value: str, ttl: int = None):
        self._cache[key] = value

    async def get_json(self, key: str) -> Optional[Dict]:
        import json
        value = self._cache.get(key)
        return json.loads(value) if value else None

    async def set_json(self, key: str, value: Dict, ttl: int = None):
        import json
        self._cache[key] = json.dumps(value)

    async def delete(self, key: str):
        self._cache.pop(key, None)

    async def ping(self):
        return True

    async def info(self):
        return {"db0": {"keys": len(self._cache)}}


@pytest.fixture
def mock_cache() -> MockCache:
    """Mock 캐시 fixture"""
    return MockCache()


# ============================================================================
# 모델 모킹
# ============================================================================

@pytest.fixture
def mock_instacart_model():
    """Mock InstacartColdStart 모델"""
    model = AsyncMock()
    model.recommend.return_value = [
        {"product_id": 1, "score": 0.9, "reason": "시간대 기반 추천"},
        {"product_id": 2, "score": 0.8, "reason": "인기 상품"},
    ]
    return model


@pytest.fixture
def mock_self_model():
    """Mock SelfPersonalized 모델"""
    model = AsyncMock()
    model.recommend.return_value = [
        {"product_id": 3, "score": 0.95, "reason": "최근 조회 상품 유사"},
        {"product_id": 4, "score": 0.85, "reason": "장바구니 상품 연관"},
    ]
    return model


@pytest.fixture
def mock_price_model():
    """Mock PriceAnomaly 모델"""
    model = AsyncMock()
    model.detect_anomalies.return_value = [
        {
            "product_id": 5,
            "current_price": 9000,
            "previous_price": 15000,
            "price_change_rate": -40.0,
            "anomaly_score": 0.92,
            "detection_methods": ["zscore", "iqr"],
        },
    ]
    return model


@pytest.fixture
def mock_recipe_model():
    """Mock RecipeGapFilling 모델"""
    model = AsyncMock()
    model.find_gap_products.return_value = [
        {
            "product_id": 6,
            "product_name": "대파",
            "reason": "된장찌개 재료",
            "recipe_id": 1,
            "recipe_name": "된장찌개",
            "match_score": 0.85,
        },
    ]
    return model


# ============================================================================
# 샘플 데이터
# ============================================================================

@pytest.fixture
def sample_products() -> List[Dict]:
    """샘플 상품 데이터"""
    return [
        {
            "id": 1,
            "name": "유기농 사과 1kg",
            "price": 12000,
            "category_id": 1,
            "seller_id": 1,
            "status": "active",
        },
        {
            "id": 2,
            "name": "제주 당근 500g",
            "price": 3500,
            "category_id": 1,
            "seller_id": 1,
            "status": "active",
        },
        {
            "id": 3,
            "name": "국내산 돼지고기 삼겹살 500g",
            "price": 15000,
            "category_id": 2,
            "seller_id": 2,
            "status": "active",
        },
    ]


@pytest.fixture
def sample_user_interactions() -> List[Dict]:
    """샘플 사용자 상호작용 데이터"""
    return [
        {
            "user_id": 1,
            "product_id": 1,
            "view_count": 5,
            "cart_event_count": 1,
            "order_event_count": 1,
        },
        {
            "user_id": 1,
            "product_id": 2,
            "view_count": 3,
            "cart_event_count": 0,
            "order_event_count": 0,
        },
    ]


@pytest.fixture
def sample_recipes() -> List[Dict]:
    """샘플 레시피 데이터"""
    return [
        {
            "id": 1,
            "name": "된장찌개",
            "category_main": "한식",
            "rating": 4.5,
            "ingredients": ["된장", "두부", "양파", "대파", "청양고추"],
        },
        {
            "id": 2,
            "name": "김치찌개",
            "category_main": "한식",
            "rating": 4.3,
            "ingredients": ["김치", "돼지고기", "두부", "대파"],
        },
    ]


# ============================================================================
# FastAPI 테스트 클라이언트
# ============================================================================

@pytest.fixture
def test_client():
    """FastAPI 테스트 클라이언트"""
    from fastapi.testclient import TestClient
    from main import app

    return TestClient(app)


@pytest.fixture
async def async_test_client():
    """비동기 FastAPI 테스트 클라이언트"""
    from httpx import AsyncClient
    from main import app

    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
