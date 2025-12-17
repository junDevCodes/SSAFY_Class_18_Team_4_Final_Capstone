"""
SelfPersonalized 모델 테스트

개인화 추천 모델 단위 테스트
"""

import pytest
from unittest.mock import AsyncMock, MagicMock


class TestSelfPersonalizedModel:
    """SelfPersonalized 모델 테스트"""

    @pytest.mark.asyncio
    async def test_model_name_and_version(self, mock_db):
        """모델 이름과 버전 확인"""
        from ml.models.self_personalized import SelfPersonalizedModel

        # Given
        model = SelfPersonalizedModel(mock_db)

        # Then
        assert model.model_name == "self_personalized"
        assert model.model_version == "1.0.0"

    @pytest.mark.asyncio
    async def test_recommend_warm_user(self, mock_db):
        """Warm 사용자 추천 테스트"""
        from ml.models.self_personalized import SelfPersonalizedModel
        from ml.base import RecommendationContext

        # Given
        model = SelfPersonalizedModel(mock_db)

        # Mock 상호작용 데이터
        mock_db.fetch_all = AsyncMock(return_value=[
            {
                "product_id": 1,
                "interaction_type": "order",
                "category_id": 1,
            },
            {
                "product_id": 2,
                "interaction_type": "view",
                "category_id": 2,
            },
        ])
        mock_db.fetch_one = AsyncMock(return_value=None)

        context = RecommendationContext(
            user_id=100,
            user_type="warm",
            time_context="dinner",
            is_weekend=False,
            day_of_week=2,
            hour_of_day=19,
            cart_product_ids=[],
        )

        # When
        results = await model.recommend(context, limit=10)

        # Then
        assert isinstance(results, dict)
        assert "products" in results
        assert results["model_name"] == "self_personalized"

    @pytest.mark.asyncio
    async def test_recommend_lukewarm_user(self, mock_db):
        """Lukewarm 사용자 추천 테스트"""
        from ml.models.self_personalized import SelfPersonalizedModel
        from ml.base import RecommendationContext

        # Given
        model = SelfPersonalizedModel(mock_db)
        mock_db.fetch_all = AsyncMock(return_value=[])
        mock_db.fetch_one = AsyncMock(return_value=None)

        context = RecommendationContext(
            user_id=101,
            user_type="lukewarm",
            time_context="lunch",
            is_weekend=True,
            day_of_week=6,
            hour_of_day=12,
            cart_product_ids=[],
        )

        # When
        results = await model.recommend(context, limit=5)

        # Then
        assert isinstance(results, dict)

    @pytest.mark.asyncio
    async def test_recommend_with_cart(self, mock_db):
        """장바구니 기반 개인화 추천 테스트"""
        from ml.models.self_personalized import SelfPersonalizedModel
        from ml.base import RecommendationContext

        # Given
        model = SelfPersonalizedModel(mock_db)
        mock_db.fetch_all = AsyncMock(return_value=[])
        mock_db.fetch_one = AsyncMock(return_value=None)

        context = RecommendationContext(
            user_id=102,
            user_type="warm",
            time_context="dinner",
            is_weekend=False,
            day_of_week=4,
            hour_of_day=18,
            cart_product_ids=[1, 2, 3],
        )

        # When
        results = await model.recommend(context, limit=10)

        # Then
        assert isinstance(results, dict)


class TestRankAndDiversify:
    """랭킹 및 다양성 테스트"""

    def test_mmr_diversification(self, mock_db):
        """MMR 다양성 보장 테스트"""
        from ml.models.self_personalized import SelfPersonalizedModel
        from ml.base import RecommendationContext

        # Given
        model = SelfPersonalizedModel(mock_db)
        context = RecommendationContext(
            user_id=100,
            user_type="warm",
            time_context="dinner",
            is_weekend=False,
            day_of_week=2,
            hour_of_day=19,
            cart_product_ids=[],
        )

        # 같은 카테고리의 상품들
        products = [
            {"product_id": 1, "category_id": 1, "_score": 100, "_source": "interaction"},
            {"product_id": 2, "category_id": 1, "_score": 95, "_source": "embedding"},
            {"product_id": 3, "category_id": 2, "_score": 90, "_source": "collaborative"},
            {"product_id": 4, "category_id": 1, "_score": 85, "_source": "interaction"},
            {"product_id": 5, "category_id": 3, "_score": 80, "_source": "embedding"},
        ]

        # When
        result = model._rank_and_diversify(products, context, limit=5)

        # Then: 다양한 카테고리가 포함되어야 함
        categories = [p.get("category_id") for p in result]
        unique_categories = set(categories)
        assert len(unique_categories) >= 2  # 최소 2개 이상 카테고리

    def test_deduplicate_products(self, mock_db):
        """상품 중복 제거 테스트"""
        from ml.models.self_personalized import SelfPersonalizedModel
        from ml.base import RecommendationContext

        # Given
        model = SelfPersonalizedModel(mock_db)
        context = RecommendationContext(
            user_id=100,
            user_type="warm",
            time_context="dinner",
            is_weekend=False,
            day_of_week=2,
            hour_of_day=19,
            cart_product_ids=[],
        )

        products = [
            {"product_id": 1, "_score": 100},
            {"product_id": 2, "_score": 90},
            {"product_id": 1, "_score": 80},  # 중복
        ]

        # When
        result = model._rank_and_diversify(products, context, limit=5)

        # Then
        product_ids = [p["product_id"] for p in result]
        assert len(product_ids) == len(set(product_ids))  # 중복 없음

    def test_internal_fields_removed(self, mock_db):
        """내부 필드 제거 확인"""
        from ml.models.self_personalized import SelfPersonalizedModel
        from ml.base import RecommendationContext

        # Given
        model = SelfPersonalizedModel(mock_db)
        context = RecommendationContext(
            user_id=100,
            user_type="warm",
            time_context="dinner",
            is_weekend=False,
            day_of_week=2,
            hour_of_day=19,
            cart_product_ids=[],
        )

        products = [
            {"product_id": 1, "_score": 100, "_source": "test"},
        ]

        # When
        result = model._rank_and_diversify(products, context, limit=5)

        # Then
        assert "_score" not in result[0]
        assert "_source" not in result[0]


class TestPersonalizedConfidence:
    """개인화 신뢰도 테스트"""

    def test_warm_user_high_confidence(self, mock_db):
        """Warm 사용자는 높은 신뢰도"""
        from ml.models.self_personalized import SelfPersonalizedModel
        from ml.base import RecommendationContext

        # Given
        model = SelfPersonalizedModel(mock_db)
        products = [{"product_id": i} for i in range(10)]

        context = RecommendationContext(
            user_id=100,
            user_type="warm",
            time_context="dinner",
            is_weekend=False,
            day_of_week=2,
            hour_of_day=19,
            cart_product_ids=[],
        )

        # When
        confidence = model._calculate_confidence(context, products)

        # Then
        assert confidence >= 0.8

    def test_lukewarm_user_medium_confidence(self, mock_db):
        """Lukewarm 사용자는 중간 신뢰도"""
        from ml.models.self_personalized import SelfPersonalizedModel
        from ml.base import RecommendationContext

        # Given
        model = SelfPersonalizedModel(mock_db)
        products = [{"product_id": i} for i in range(10)]

        context = RecommendationContext(
            user_id=101,
            user_type="lukewarm",
            time_context="lunch",
            is_weekend=True,
            day_of_week=6,
            hour_of_day=12,
            cart_product_ids=[],
        )

        # When
        confidence = model._calculate_confidence(context, products)

        # Then
        assert 0.5 <= confidence < 0.8

    def test_cold_user_low_confidence(self, mock_db):
        """Cold 사용자는 낮은 신뢰도"""
        from ml.models.self_personalized import SelfPersonalizedModel
        from ml.base import RecommendationContext

        # Given
        model = SelfPersonalizedModel(mock_db)
        products = [{"product_id": i} for i in range(10)]

        context = RecommendationContext(
            user_id=102,
            user_type="cold",
            time_context="morning",
            is_weekend=False,
            day_of_week=1,
            hour_of_day=9,
            cart_product_ids=[],
        )

        # When
        confidence = model._calculate_confidence(context, products)

        # Then
        assert confidence < 0.5

    def test_empty_results_zero_confidence(self, mock_db):
        """빈 결과는 신뢰도 0"""
        from ml.models.self_personalized import SelfPersonalizedModel
        from ml.base import RecommendationContext

        # Given
        model = SelfPersonalizedModel(mock_db)
        context = RecommendationContext(
            user_id=100,
            user_type="warm",
            time_context="dinner",
            is_weekend=False,
            day_of_week=2,
            hour_of_day=19,
            cart_product_ids=[],
        )

        # When
        confidence = model._calculate_confidence(context, [])

        # Then
        assert confidence == 0.0
