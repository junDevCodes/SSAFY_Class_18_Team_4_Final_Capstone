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
    ProductImageManageView,
    WishlistViewSet,
    CartViewSet,
)

# Router 설정
router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'products-legacy', ProductViewSet, basename='product-legacy')
router.register(r'seller-products', SellerProductViewSet, basename='seller-product')
router.register(r'wishlist', WishlistViewSet, basename='wishlist')
router.register(r'cart', CartViewSet, basename='cart')

urlpatterns = [
    # 상품 API (새로운 버전)
    path('products/', ProductListView.as_view(), name='product-list'),
    path('products/<int:pk>/', ProductDetailView.as_view(), name='product-detail'),
    path('products/<slug:slug>/', ProductDetailView.as_view(), name='product-detail-slug'),

    # 판매자 상품 이미지 관리
    path('seller-products/<int:product_id>/images/', ProductImageManageView.as_view(), name='product-image-add'),
    path('seller-products/<int:product_id>/images/<int:image_id>/', ProductImageManageView.as_view(), name='product-image-delete'),

    # ViewSet URLs
    path('', include(router.urls)),
]
