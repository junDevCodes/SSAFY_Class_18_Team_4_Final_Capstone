"""
추천 관련 URL 설정 (REC-005)

/api/recommendations/ 하위의 모든 추천 관련 엔드포인트를 정의합니다.
"""
from django.urls import path

from .recommendations_views import (
    CartRecommendationsView,
    PersonalizedRecommendationsView,
    RecentViewedProductsView,
    TimeDealProductsView,
    PriceHistoryView,
)

urlpatterns = [
    # 최근 본 상품 조회 (REC-005)
    path('recent/', RecentViewedProductsView.as_view(), name='recent-viewed'),
    # 장바구니 기반 ML 추천 (비회원 허용)
    path('cart/', CartRecommendationsView.as_view(), name='cart-recommendations'),
    # 개인화 추천 (로그인 필수) - MD's Pick 섹션용
    path('personalized/', PersonalizedRecommendationsView.as_view(), name='personalized-recommendations'),
    # 타임세일 가성비 상품 (비회원 허용) - PriceScout 모델 기반
    path('time-deal/', TimeDealProductsView.as_view(), name='time-deal-products'),
    # 가격 히스토리 (비회원 허용) - 폴센트 스타일 가격 추적 그래프
    path('price-history/<int:product_id>/', PriceHistoryView.as_view(), name='price-history'),
]
