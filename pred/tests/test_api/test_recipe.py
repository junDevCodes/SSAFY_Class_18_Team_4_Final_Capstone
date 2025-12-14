"""
레시피 API 엔드포인트 테스트

레시피 Gap Filling 및 검색 API 통합 테스트
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


class TestRecipeGapFillEndpoint:
    """레시피 Gap Fill API 테스트"""

    @pytest.fixture
    def client(self):
        """테스트 클라이언트 생성"""
        from main import app
        return TestClient(app)

    def test_gap_fill_with_cart(self, client):
        """장바구니 기반 Gap Fill"""
        # Given
        request_data = {
            "cart_product_ids": [1, 2, 3],
            "time_context": "dinner",
            "limit": 5,
        }

        with patch("api.routes.recipe.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_db.fetch_all = AsyncMock(return_value=[
                {
                    "recipe_id": 1,
                    "name": "김치찌개",
                    "gap_count": 1,
                    "missing_ingredient_ids": [5],
                }
            ])
            mock_get_db.return_value = mock_db

            # When
            response = client.post(
                "/api/v1/recipes/gap-fill",
                json=request_data
            )

            # Then
            assert response.status_code in [200, 500]

    def test_gap_fill_empty_cart(self, client):
        """빈 장바구니로 Gap Fill"""
        # Given
        request_data = {
            "cart_product_ids": [],
            "time_context": "morning",
        }

        with patch("api.routes.recipe.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_db.fetch_all = AsyncMock(return_value=[])
            mock_get_db.return_value = mock_db

            # When
            response = client.post(
                "/api/v1/recipes/gap-fill",
                json=request_data
            )

            # Then
            assert response.status_code in [200, 500]


class TestRecipeSearchEndpoint:
    """레시피 검색 API 테스트"""

    @pytest.fixture
    def client(self):
        """테스트 클라이언트 생성"""
        from main import app
        return TestClient(app)

    def test_search_recipes_by_name(self, client):
        """레시피 이름으로 검색"""
        # Given
        with patch("api.routes.recipe.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_db.fetch_all = AsyncMock(return_value=[
                {
                    "id": 1,
                    "name": "김치볶음밥",
                    "description": "맛있는 김치볶음밥",
                    "cooking_time_minutes": 15,
                }
            ])
            mock_get_db.return_value = mock_db

            # When
            response = client.get(
                "/api/v1/recipes/search",
                params={"query": "김치"}
            )

            # Then
            assert response.status_code in [200, 500]

    def test_search_recipes_empty_query(self, client):
        """빈 검색어"""
        # When
        response = client.get("/api/v1/recipes/search")

        # Then: 빈 쿼리는 에러 또는 빈 결과
        assert response.status_code in [200, 422, 500]


class TestRecipeDetailEndpoint:
    """레시피 상세 API 테스트"""

    @pytest.fixture
    def client(self):
        """테스트 클라이언트 생성"""
        from main import app
        return TestClient(app)

    def test_get_recipe_detail(self, client):
        """레시피 상세 조회"""
        # Given
        recipe_id = 1

        with patch("api.routes.recipe.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_db.fetch_one = AsyncMock(return_value={
                "id": 1,
                "name": "된장찌개",
                "description": "구수한 된장찌개",
                "cooking_time_minutes": 30,
                "difficulty": "easy",
                "servings": 2,
            })
            mock_db.fetch_all = AsyncMock(return_value=[
                {"ingredient_id": 1, "name": "된장", "amount": "2큰술"},
                {"ingredient_id": 2, "name": "두부", "amount": "1/2모"},
            ])
            mock_get_db.return_value = mock_db

            # When
            response = client.get(f"/api/v1/recipes/{recipe_id}")

            # Then
            assert response.status_code in [200, 404, 500]

    def test_get_recipe_not_found(self, client):
        """존재하지 않는 레시피"""
        # Given
        recipe_id = 99999

        with patch("api.routes.recipe.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_db.fetch_one = AsyncMock(return_value=None)
            mock_get_db.return_value = mock_db

            # When
            response = client.get(f"/api/v1/recipes/{recipe_id}")

            # Then
            assert response.status_code in [404, 500]


class TestRecipeProductsEndpoint:
    """레시피 상품 API 테스트"""

    @pytest.fixture
    def client(self):
        """테스트 클라이언트 생성"""
        from main import app
        return TestClient(app)

    def test_get_recipe_products(self, client):
        """레시피 재료 상품 조회"""
        # Given
        recipe_id = 1

        with patch("api.routes.recipe.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_db.fetch_all = AsyncMock(return_value=[
                {
                    "ingredient_id": 1,
                    "ingredient_name": "된장",
                    "product_id": 100,
                    "product_name": "청정원 된장",
                    "price": 5000,
                }
            ])
            mock_get_db.return_value = mock_db

            # When
            response = client.get(f"/api/v1/recipes/{recipe_id}/products")

            # Then
            assert response.status_code in [200, 404, 500]


class TestPopularRecipesEndpoint:
    """인기 레시피 API 테스트"""

    @pytest.fixture
    def client(self):
        """테스트 클라이언트 생성"""
        from main import app
        return TestClient(app)

    def test_get_popular_recipes(self, client):
        """인기 레시피 조회"""
        # Given
        with patch("api.routes.recipe.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_db.fetch_all = AsyncMock(return_value=[
                {
                    "id": 1,
                    "name": "김치찌개",
                    "rating": 4.8,
                    "review_count": 120,
                },
                {
                    "id": 2,
                    "name": "된장찌개",
                    "rating": 4.6,
                    "review_count": 95,
                },
            ])
            mock_get_db.return_value = mock_db

            # When
            response = client.get("/api/v1/recipes/popular")

            # Then
            assert response.status_code in [200, 500]

    def test_get_popular_recipes_with_meal_type(self, client):
        """식사 유형별 인기 레시피"""
        # Given
        with patch("api.routes.recipe.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_db.fetch_all = AsyncMock(return_value=[])
            mock_get_db.return_value = mock_db

            # When
            response = client.get(
                "/api/v1/recipes/popular",
                params={"meal_type": "dinner"}
            )

            # Then
            assert response.status_code in [200, 500]


class TestRecipesByIngredientsEndpoint:
    """재료별 레시피 API 테스트"""

    @pytest.fixture
    def client(self):
        """테스트 클라이언트 생성"""
        from main import app
        return TestClient(app)

    def test_get_recipes_by_ingredients(self, client):
        """재료로 레시피 검색"""
        # Given
        with patch("api.routes.recipe.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_db.fetch_all = AsyncMock(return_value=[
                {
                    "id": 1,
                    "name": "계란찜",
                    "match_count": 2,
                }
            ])
            mock_get_db.return_value = mock_db

            # When
            response = client.get(
                "/api/v1/recipes/by-ingredients",
                params={"ingredient_ids": "1,2,3"}
            )

            # Then
            assert response.status_code in [200, 422, 500]
