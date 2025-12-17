"""
추천 관련 URL 설정 (REC-005)

/api/recommendations/ 하위의 모든 추천 관련 엔드포인트를 정의합니다.
"""
from django.urls import path

from .recommendations_views import (
    RecentViewedProductsView,
    HomeRecommendationsView,
    ProductRecommendationsView,
    DealRecommendationsView,
    CartUnifiedRecommendationsView,
    CartRecipeRecommendationsView,
    RecipeDetailView,
    RecipeSearchView,
)

urlpatterns = [
    # 최근 본 상품 조회 (REC-005)
    path('recent/', RecentViewedProductsView.as_view(), name='recent-viewed'),

    # ML 추천 API (pred 서비스 연동)
    path('home/', HomeRecommendationsView.as_view(), name='home-recommendations'),
    path('product/<int:product_id>/', ProductRecommendationsView.as_view(), name='product-recommendations'),
    path('deals/', DealRecommendationsView.as_view(), name='deal-recommendations'),

    # 장바구니 통합 추천 API (레시피 > 개인화 > Instacart 우선순위)
    path('cart/unified/', CartUnifiedRecommendationsView.as_view(), name='cart-unified-recommendations'),

    # 레시피 GapFilling 추천 API
    path('cart-recipes/', CartRecipeRecommendationsView.as_view(), name='cart-recipe-recommendations'),
    path('recipe/<int:recipe_id>/', RecipeDetailView.as_view(), name='recipe-detail'),
    path('recipe/search/', RecipeSearchView.as_view(), name='recipe-search'),
]
