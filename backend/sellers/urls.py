"""
판매자 관련 URL 설정
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SellerRegistrationView,
    SellerViewSet,
    SellerApprovalView,
    SellerDashboardView,
)

# Router 설정
router = DefaultRouter()
router.register(r'', SellerViewSet, basename='seller')

urlpatterns = [
    # 판매자 등록
    path('register/', SellerRegistrationView.as_view(), name='seller-register'),

    # 판매자 승인 (관리자용)
    path('<int:pk>/approve/', SellerApprovalView.as_view(), name='seller-approve'),

    # 판매자 대시보드
    path('dashboard/', SellerDashboardView.as_view(), name='seller-dashboard'),

    # ViewSet URLs
    path('', include(router.urls)),
]
