"""
InstacartColdStart 모델 테스트

신규/비로그인 사용자 추천 모델 단위 테스트
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestInstacartColdStartModel:
    """InstacartColdStart 모델 테스트"""

    @pytest.mark.asyncio
    async def test_model_name_and_version(self, mock_db):
        """모델 이름과 버전 확인"""
        from ml.models.instacart_cold_start import InstacartColdStartModel

        # Given
        model = InstacartColdStartModel(mock_db)

        # Then
        assert model.model_name == "instacart_cold_start"
        assert model.model_version == "1.0.0"

    @pytest.mark.asyncio
    async def test_recommend_with_time_context(self, mock_db):
        """시간대 컨텍스트 기반 추천 테스트"""
        from ml.models.instacart_cold_start import InstacartColdStartModel
        from ml.base import RecommendationContext

        # Given
        model = InstacartColdStartModel(mock_db)

        # 시간 패턴 데이터 Mock
        mock_db.fetch_all = AsyncMock(side_effect=[
            # get_time_context_patterns 결과
            [
                {"aisle_id": 1, "total_orders": 100},
                {"aisle_id": 2, "total_orders": 80},
            ],
            # get_all_mappings 결과 (빈 결과로 처리)
            [],
            # get_popular_products_by_categories 결과
            [],
        ])

        context = RecommendationContext(
            user_id=None,
            user_type="cold",
            time_context="morning",
            is_weekend=False,
            day_of_week=1,
            hour_of_day=9,
            cart_product_ids=[],
        )

        # When
        results = await model.recommend(context, limit=10)

        # Then
        assert isinstance(results, dict)
        assert "products" in results
        assert "model_name" in results
        assert results["model_name"] == "instacart_cold_start"

    @pytest.mark.asyncio
    async def test_recommend_with_category_context(self, mock_db):
        """카테고리 컨텍스트 기반 추천 테스트"""
        from ml.models.instacart_cold_start import InstacartColdStartModel
        from ml.base import RecommendationContext

        # Given
        model = InstacartColdStartModel(mock_db)

        mock_db.fetch_all = AsyncMock(return_value=[
            {
                "product_id": 1,
                "name": "테스트 상품",
                "price": 10000,
                "category_id": 1,
                "order_event_count": 50,
            }
        ])

        context = RecommendationContext(
            user_id=None,
            user_type="cold",
            time_context="lunch",
            is_weekend=True,
            day_of_week=6,
            hour_of_day=12,
            category_id=1,
            cart_product_ids=[],
        )

        # When
        results = await model.recommend(context, limit=5)

        # Then
        assert isinstance(results, dict)

    @pytest.mark.asyncio
    async def test_recommend_with_cart(self, mock_db):
        """장바구니 기반 추천 테스트"""
        from ml.models.instacart_cold_start import InstacartColdStartModel
        from ml.base import RecommendationContext

        # Given
        model = InstacartColdStartModel(mock_db)

        mock_db.fetch_all = AsyncMock(return_value=[
            {
                "product_id": 2,
                "name": "함께 구매 상품",
                "weighted_score": 0.85,
            }
        ])

        context = RecommendationContext(
            user_id=None,
            user_type="cold",
            time_context="dinner",
            is_weekend=False,
            day_of_week=3,
            hour_of_day=18,
            cart_product_ids=[1, 3, 5],
        )

        # When
        results = await model.recommend(context, limit=10)

        # Then
        assert isinstance(results, dict)


class TestDeduplicationAndRanking:
    """중복 제거 및 랭킹 테스트"""

    def test_deduplicate_products(self, mock_db):
        """상품 중복 제거 테스트"""
        from ml.models.instacart_cold_start import InstacartColdStartModel

        # Given
        model = InstacartColdStartModel(mock_db)

        products = [
            {"product_id": 1, "name": "상품1", "_score": 100, "_source": "time"},
            {"product_id": 2, "name": "상품2", "_score": 80, "_source": "category"},
            {"product_id": 1, "name": "상품1", "_score": 90, "_source": "cart"},  # 중복
            {"product_id": 3, "name": "상품3", "_score": 70, "_source": "time"},
        ]

        # When
        result = model._deduplicate_and_rank(products)

        # Then: 중복 제거됨
        assert len(result) == 3
        product_ids = [p["product_id"] for p in result]
        assert product_ids == [1, 2, 3]  # 점수 순 정렬

    def test_rank_by_score(self, mock_db):
        """점수 기반 정렬 테스트"""
        from ml.models.instacart_cold_start import InstacartColdStartModel

        # Given
        model = InstacartColdStartModel(mock_db)

        products = [
            {"product_id": 1, "_score": 50},
            {"product_id": 2, "_score": 100},
            {"product_id": 3, "_score": 75},
        ]

        # When
        result = model._deduplicate_and_rank(products)

        # Then: 점수 내림차순 정렬
        scores_order = [p["product_id"] for p in result]
        assert scores_order == [2, 3, 1]

    def test_internal_fields_removed(self, mock_db):
        """내부 필드 제거 테스트"""
        from ml.models.instacart_cold_start import InstacartColdStartModel

        # Given
        model = InstacartColdStartModel(mock_db)

        products = [
            {"product_id": 1, "_score": 100, "_source": "test"},
        ]

        # When
        result = model._deduplicate_and_rank(products)

        # Then: 내부 필드 제거됨
        assert "_score" not in result[0]
        assert "_source" not in result[0]


class TestConfidenceCalculation:
    """신뢰도 계산 테스트"""

    def test_confidence_with_empty_products(self, mock_db):
        """빈 결과의 신뢰도"""
        from ml.models.instacart_cold_start import InstacartColdStartModel
        from ml.base import RecommendationContext

        # Given
        model = InstacartColdStartModel(mock_db)
        context = RecommendationContext(
            user_id=None,
            user_type="cold",
            time_context="morning",
            is_weekend=False,
            day_of_week=1,
            hour_of_day=9,
            cart_product_ids=[],
        )

        # When
        confidence = model._calculate_confidence(context, [])

        # Then
        assert confidence == 0.0

    def test_confidence_increases_with_cart(self, mock_db):
        """장바구니가 있으면 신뢰도 증가"""
        from ml.models.instacart_cold_start import InstacartColdStartModel
        from ml.base import RecommendationContext

        # Given
        model = InstacartColdStartModel(mock_db)
        products = [{"product_id": i} for i in range(10)]

        context_without_cart = RecommendationContext(
            user_id=None,
            user_type="cold",
            time_context="morning",
            is_weekend=False,
            day_of_week=1,
            hour_of_day=9,
            cart_product_ids=[],
        )

        context_with_cart = RecommendationContext(
            user_id=None,
            user_type="cold",
            time_context="morning",
            is_weekend=False,
            day_of_week=1,
            hour_of_day=9,
            cart_product_ids=[1, 2, 3],
        )

        # When
        conf_without = model._calculate_confidence(context_without_cart, products)
        conf_with = model._calculate_confidence(context_with_cart, products)

        # Then
        assert conf_with > conf_without

    def test_confidence_increases_with_category(self, mock_db):
        """카테고리가 있으면 신뢰도 증가"""
        from ml.models.instacart_cold_start import InstacartColdStartModel
        from ml.base import RecommendationContext

        # Given
        model = InstacartColdStartModel(mock_db)
        products = [{"product_id": i} for i in range(10)]

        context_without_category = RecommendationContext(
            user_id=None,
            user_type="cold",
            time_context="morning",
            is_weekend=False,
            day_of_week=1,
            hour_of_day=9,
            cart_product_ids=[],
        )

        context_with_category = RecommendationContext(
            user_id=None,
            user_type="cold",
            time_context="morning",
            is_weekend=False,
            day_of_week=1,
            hour_of_day=9,
            category_id=1,
            cart_product_ids=[],
        )

        # When
        conf_without = model._calculate_confidence(context_without_category, products)
        conf_with = model._calculate_confidence(context_with_category, products)

        # Then
        assert conf_with > conf_without
