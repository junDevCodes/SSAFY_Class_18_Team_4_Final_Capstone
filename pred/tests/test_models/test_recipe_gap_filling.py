"""
RecipeGapFilling 모델 테스트

레시피 Gap 분석 및 부족 재료 추천 모델 단위 테스트
"""

import pytest
from unittest.mock import AsyncMock, MagicMock


class TestRecipeGapFillingModel:
    """RecipeGapFilling 모델 테스트"""

    @pytest.mark.asyncio
    async def test_model_name_and_version(self, mock_db):
        """모델 이름과 버전 확인"""
        from ml.models.recipe_gap_filling import RecipeGapFillingModel

        # Given
        model = RecipeGapFillingModel(mock_db)

        # Then
        assert model.model_name == "recipe_gap_filling"
        assert model.model_version == "1.0.0"

    @pytest.mark.asyncio
    async def test_recommend_without_cart(self, mock_db):
        """장바구니 없이 시간대 기반 추천"""
        from ml.models.recipe_gap_filling import RecipeGapFillingModel
        from ml.base import RecommendationContext

        # Given
        model = RecipeGapFillingModel(mock_db)

        # Mock 레시피 데이터
        mock_db.fetch_all = AsyncMock(return_value=[
            {
                "id": 1,
                "name": "계란찜",
                "meal_type": "breakfast",
            }
        ])
        mock_db.fetch_one = AsyncMock(return_value=None)

        context = RecommendationContext(
            user_id=100,
            user_type="warm",
            time_context="morning",
            is_weekend=False,
            day_of_week=1,
            hour_of_day=8,
            cart_product_ids=[],  # 빈 장바구니
        )

        # When
        results = await model.recommend(context, limit=10)

        # Then
        assert isinstance(results, dict)
        assert "products" in results
        assert results["model_name"] == "recipe_gap_filling"

    @pytest.mark.asyncio
    async def test_recommend_with_cart(self, mock_db):
        """장바구니 기반 Gap 분석 추천"""
        from ml.models.recipe_gap_filling import RecipeGapFillingModel
        from ml.base import RecommendationContext

        # Given
        model = RecipeGapFillingModel(mock_db)

        # Mock 레시피 Gap 데이터
        mock_db.fetch_all = AsyncMock(side_effect=[
            # find_recipes_with_gap 결과
            [
                {
                    "recipe_id": 1,
                    "name": "김치찌개",
                    "gap_count": 2,
                    "match_percentage": 75,
                    "missing_ingredient_ids": [3, 4],
                }
            ],
            # get_gap_filling_products 결과
            [
                {
                    "product_id": 10,
                    "name": "두부",
                    "price": 2000,
                    "ingredient_id": 3,
                },
                {
                    "product_id": 11,
                    "name": "대파",
                    "price": 1500,
                    "ingredient_id": 4,
                },
            ],
        ])

        context = RecommendationContext(
            user_id=100,
            user_type="warm",
            time_context="dinner",
            is_weekend=False,
            day_of_week=3,
            hour_of_day=18,
            cart_product_ids=[1, 2, 5],  # 장바구니에 일부 재료
        )

        # When
        results = await model.recommend(context, limit=10)

        # Then
        assert isinstance(results, dict)


class TestRecipeGapAnalysis:
    """레시피 Gap 분석 테스트"""

    @pytest.mark.asyncio
    async def test_analyze_recipe_gaps_dinner_time(self, mock_db):
        """저녁 시간대 레시피 Gap 분석"""
        from ml.models.recipe_gap_filling import RecipeGapFillingModel

        # Given
        model = RecipeGapFillingModel(mock_db)

        mock_db.fetch_all = AsyncMock(return_value=[
            {
                "recipe_id": 1,
                "name": "저녁 레시피",
                "meal_type": "dinner",
                "gap_count": 1,
            }
        ])

        # When
        result = await model._analyze_recipe_gaps(
            cart_product_ids=[1, 2, 3],
            time_context="dinner",
        )

        # Then
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_max_gap_count_filter(self, mock_db):
        """최대 Gap 개수 필터링"""
        from ml.models.recipe_gap_filling import RecipeGapFillingModel

        # Given
        model = RecipeGapFillingModel(mock_db)

        # Then: 기본 설정 확인
        assert model.max_gap_count == 3
        assert model.min_match_ratio == 0.5


class TestRecipeSuggestions:
    """레시피 제안 테스트"""

    @pytest.mark.asyncio
    async def test_get_recipe_suggestions(self, mock_db):
        """레시피 제안 조회"""
        from ml.models.recipe_gap_filling import RecipeGapFillingModel

        # Given
        model = RecipeGapFillingModel(mock_db)

        mock_db.fetch_all = AsyncMock(side_effect=[
            # find_recipes_with_gap 결과
            [
                {
                    "recipe_id": 1,
                    "name": "된장찌개",
                    "description": "맛있는 된장찌개",
                    "cooking_time_minutes": 30,
                    "difficulty": "easy",
                    "gap_count": 1,
                    "match_percentage": 90,
                    "missing_ingredient_ids": [5],
                }
            ],
            # get_gap_filling_products 결과
            [
                {
                    "product_id": 20,
                    "name": "양파",
                    "price": 1000,
                    "rank": 1,
                }
            ],
        ])

        # When
        suggestions = await model.get_recipe_suggestions(
            cart_product_ids=[1, 2, 3, 4],
            limit=3,
        )

        # Then
        assert isinstance(suggestions, list)

    @pytest.mark.asyncio
    async def test_get_recipe_suggestions_empty_cart(self, mock_db):
        """빈 장바구니로 레시피 제안"""
        from ml.models.recipe_gap_filling import RecipeGapFillingModel

        # Given
        model = RecipeGapFillingModel(mock_db)

        # When
        suggestions = await model.get_recipe_suggestions(
            cart_product_ids=[],
            limit=3,
        )

        # Then: 빈 결과 반환
        assert suggestions == []


class TestShoppingList:
    """장보기 목록 테스트"""

    @pytest.mark.asyncio
    async def test_get_shopping_list(self, mock_db):
        """레시피 장보기 목록 조회"""
        from ml.models.recipe_gap_filling import RecipeGapFillingModel

        # Given
        model = RecipeGapFillingModel(mock_db)

        mock_db.fetch_all = AsyncMock(return_value=[
            {
                "ingredient_id": 1,
                "ingredient_name": "돼지고기",
                "product_id": 100,
                "product_name": "국내산 삼겹살",
                "price": 15000,
            }
        ])

        # When
        result = await model.get_shopping_list(
            recipe_id=1,
            owned_ingredient_ids=[2, 3],
        )

        # Then
        assert isinstance(result, dict)


class TestDeduplicateAndFormat:
    """중복 제거 및 포맷팅 테스트"""

    def test_deduplicate_products(self, mock_db):
        """상품 중복 제거"""
        from ml.models.recipe_gap_filling import RecipeGapFillingModel

        # Given
        model = RecipeGapFillingModel(mock_db)

        products = [
            {"product_id": 1, "_score": 100, "_recipe_id": 1, "_recipe_name": "레시피1"},
            {"product_id": 2, "_score": 80, "_recipe_id": 1, "_recipe_name": "레시피1"},
            {"product_id": 1, "_score": 90, "_recipe_id": 2, "_recipe_name": "레시피2"},  # 중복
        ]

        # When
        result = model._deduplicate_and_format(products, limit=10)

        # Then
        product_ids = [p["product_id"] for p in result]
        assert len(product_ids) == 2  # 중복 제거
        assert 1 in product_ids
        assert 2 in product_ids

    def test_recipe_context_added(self, mock_db):
        """recipe_context 필드 추가"""
        from ml.models.recipe_gap_filling import RecipeGapFillingModel

        # Given
        model = RecipeGapFillingModel(mock_db)

        products = [
            {
                "product_id": 1,
                "_score": 100,
                "_recipe_id": 1,
                "_recipe_name": "테스트 레시피",
                "_gap_count": 2,
                "_match_percentage": 80,
            }
        ]

        # When
        result = model._deduplicate_and_format(products, limit=10)

        # Then
        assert "recipe_context" in result[0]
        assert result[0]["recipe_context"]["recipe_id"] == 1
        assert result[0]["recipe_context"]["recipe_name"] == "테스트 레시피"

    def test_internal_fields_removed(self, mock_db):
        """내부 필드 제거 확인"""
        from ml.models.recipe_gap_filling import RecipeGapFillingModel

        # Given
        model = RecipeGapFillingModel(mock_db)

        products = [
            {
                "product_id": 1,
                "_score": 100,
                "_recipe_id": 1,
                "_recipe_name": "test",
                "rank": 1,
            }
        ]

        # When
        result = model._deduplicate_and_format(products, limit=10)

        # Then
        assert "_score" not in result[0]
        assert "_recipe_id" not in result[0]
        assert "rank" not in result[0]


class TestRecipeConfidence:
    """레시피 신뢰도 계산 테스트"""

    def test_confidence_with_cart(self, mock_db):
        """장바구니가 있으면 신뢰도 높음"""
        from ml.models.recipe_gap_filling import RecipeGapFillingModel
        from ml.base import RecommendationContext

        # Given
        model = RecipeGapFillingModel(mock_db)

        products_with_recipe = [
            {
                "product_id": 1,
                "recipe_context": {"recipe_id": 1},
            }
        ]

        context_with_cart = RecommendationContext(
            user_id=100,
            user_type="warm",
            time_context="dinner",
            is_weekend=False,
            day_of_week=3,
            hour_of_day=18,
            cart_product_ids=[1, 2, 3],
        )

        context_without_cart = RecommendationContext(
            user_id=100,
            user_type="warm",
            time_context="dinner",
            is_weekend=False,
            day_of_week=3,
            hour_of_day=18,
            cart_product_ids=[],
        )

        # When
        conf_with = model._calculate_confidence(context_with_cart, products_with_recipe)
        conf_without = model._calculate_confidence(context_without_cart, products_with_recipe)

        # Then
        assert conf_with > conf_without

    def test_empty_results_zero_confidence(self, mock_db):
        """빈 결과는 신뢰도 0"""
        from ml.models.recipe_gap_filling import RecipeGapFillingModel
        from ml.base import RecommendationContext

        # Given
        model = RecipeGapFillingModel(mock_db)

        context = RecommendationContext(
            user_id=100,
            user_type="warm",
            time_context="dinner",
            is_weekend=False,
            day_of_week=3,
            hour_of_day=18,
            cart_product_ids=[],
        )

        # When
        confidence = model._calculate_confidence(context, [])

        # Then
        assert confidence == 0.0
