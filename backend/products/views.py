"""
제품 관련 뷰
"""
from rest_framework import viewsets, filters
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from .models import Category, Product
from .serializers import CategorySerializer, ProductSerializer


class StandardResultsSetPagination(PageNumberPagination):
    """표준 페이지네이션 설정"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    카테고리 ViewSet (읽기 전용)

    list: 카테고리 목록 조회
    retrieve: 카테고리 상세 조회
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    pagination_class = StandardResultsSetPagination


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """
    제품 ViewSet (읽기 전용)

    list: 제품 목록 조회
    retrieve: 제품 상세 조회

    필터링:
    - category: 카테고리 ID로 필터링
    - is_best: 베스트 제품 필터링 (true/false)

    검색:
    - search: 제품명 또는 설명으로 검색
    """
    queryset = Product.objects.select_related('category').all()
    serializer_class = ProductSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['category', 'is_best']
    search_fields = ['name', 'description']
