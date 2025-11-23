"""
주문 관련 URL 설정
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import OrderViewSet

# Router 설정
router = DefaultRouter()
router.register(r'', OrderViewSet, basename='order')

urlpatterns = [
    path('', include(router.urls)),
]
