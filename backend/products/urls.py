"""
제품 관련 URL 설정
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CategoryViewSet,
    ProductViewSet,
    ProductListView,
    ProductDetailView,
    SellerProductViewSet,
)

# Router 설정
router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'products-legacy', ProductViewSet, basename='product-legacy')
router.register(r'seller-products', SellerProductViewSet, basename='seller-product')

urlpatterns = [
    # 상품 API (새로운 버전)
    path('products/', ProductListView.as_view(), name='product-list'),
    path('products/<slug:slug>/', ProductDetailView.as_view(), name='product-detail'),

    # ViewSet URLs
    path('', include(router.urls)),
]
