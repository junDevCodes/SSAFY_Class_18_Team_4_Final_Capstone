"""
제품 관련 URL 설정
"""
from django.urls import path, include, re_path
from rest_framework.routers import DefaultRouter
from .views import (
    CategoryViewSet,
    ProductViewSet,
    ProductListView,
    ProductDetailView,
    SellerProductViewSet,
    ProductImageManageView,
    ProductImageUploadView,
    ProductDetailImageUploadView,
    WishlistViewSet,
    CartViewSet,
    ReviewViewSet,
    ProductRecommendClickView,
    NewProductListView,
    BestProductListView,
)

# Router 설정
router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'products-legacy', ProductViewSet, basename='product-legacy')
router.register(r'seller-products', SellerProductViewSet, basename='seller-product')
router.register(r'wishlist', WishlistViewSet, basename='wishlist')
router.register(r'cart', CartViewSet, basename='cart')
router.register(r'reviews', ReviewViewSet, basename='review')

urlpatterns = [
    # 상품 API (새로운 버전)
    path('products/', ProductListView.as_view(), name='product-list'),
    # 신상품 목록 API (product_type='main', 최신순 40개)
    path('products/new/', NewProductListView.as_view(), name='product-new-list'),
    # 베스트 상품 목록 API (product_type='seller', 판매량 기준 40개)
    path('products/best/', BestProductListView.as_view(), name='product-best-list'),
    path('products/<int:pk>/', ProductDetailView.as_view(), name='product-detail'),
    # 한글 slug 지원을 위해 re_path 사용 (유니코드 문자 허용)
    re_path(r'^products/(?P<slug>[\w\-]+)/$', ProductDetailView.as_view(), name='product-detail-slug'),

    # 추천 클릭 기록 API
    path('products/<int:pk>/recommend-click/', ProductRecommendClickView.as_view(), name='product-recommend-click'),

    # 판매자 상품 이미지 관리 (URL 기반)
    path('seller-products/<int:product_id>/images/', ProductImageManageView.as_view(), name='product-image-add'),
    path('seller-products/<int:product_id>/images/<int:image_id>/', ProductImageManageView.as_view(), name='product-image-delete'),

    # 판매자 상품 이미지 업로드 (파일 업로드 → S3)
    path('seller-products/<int:product_id>/images/upload/', ProductImageUploadView.as_view(), name='product-image-upload'),
    path('seller-products/<int:product_id>/detail-images/upload/', ProductDetailImageUploadView.as_view(), name='product-detail-image-upload'),

    # ViewSet URLs
    path('', include(router.urls)),
]
