"""
추천 관련 URL 설정 (REC-005)

/api/recommendations/ 하위의 모든 추천 관련 엔드포인트를 정의합니다.
"""
from django.urls import path

from .recommendations_views import RecentViewedProductsView

urlpatterns = [
    # 최근 본 상품 조회 (REC-005)
    path('recent/', RecentViewedProductsView.as_view(), name='recent-viewed'),
]
