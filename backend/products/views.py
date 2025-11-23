"""
제품 관련 뷰
"""
from rest_framework import viewsets, filters, generics
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import F
from .models import Category, Product, ProductView
from .serializers import CategorySerializer, ProductSerializer, ProductDetailSerializer, ProductListSerializer


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


class ProductListView(generics.ListAPIView):
    """상품 목록 API (필터링 및 정렬 지원)"""

    serializer_class = ProductListSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]

    # 필터링
    filterset_fields = {
        'category': ['exact'],
        'price': ['gte', 'lte'],
        'is_featured': ['exact'],
        'is_best': ['exact'],
        'is_new': ['exact'],
        'is_on_sale': ['exact'],
        'status': ['exact'],
    }

    # 검색
    search_fields = ['name', 'description', 'short_description']

    # 정렬
    ordering_fields = ['price', 'created_at', 'quality_score', 'view_count', 'average_rating']
    ordering = ['-quality_score']  # 기본 정렬: 품질 점수 높은 순

    def get_queryset(self):
        """쿼리셋 최적화"""
        return Product.objects.filter(status='active').select_related('category')


class ProductDetailView(generics.RetrieveAPIView):
    """상품 상세 API (조회수 증가 및 로그 기록)"""

    queryset = Product.objects.select_related('category', 'seller').prefetch_related('images')
    serializer_class = ProductDetailSerializer
    lookup_field = 'slug'

    def retrieve(self, request, *args, **kwargs):
        """조회수 증가 및 로그 기록"""
        instance = self.get_object()

        # 조회수 증가 (F() 사용으로 race condition 방지)
        Product.objects.filter(id=instance.id).update(view_count=F('view_count') + 1)

        # 조회 로그 기록
        self.log_product_view(request, instance)

        # instance를 다시 가져와서 업데이트된 view_count 반영
        instance.refresh_from_db()

        return super().retrieve(request, *args, **kwargs)

    def log_product_view(self, request, product):
        """상품 조회 로그 저장"""
        ProductView.objects.create(
            product=product,
            user=request.user if request.user.is_authenticated else None,
            session_id=request.session.session_key or '',
            referrer=request.META.get('HTTP_REFERER'),
            user_agent=request.META.get('HTTP_USER_AGENT'),
            ip_address=self.get_client_ip(request),
        )

    def get_client_ip(self, request):
        """클라이언트 IP 주소 추출"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
