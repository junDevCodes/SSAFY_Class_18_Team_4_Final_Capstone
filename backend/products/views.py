"""
제품 관련 뷰
"""
from rest_framework import viewsets, filters, generics, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import F
from django.utils import timezone
from django.shortcuts import get_object_or_404
from .models import Category, Product, ProductView, ProductImage
from .serializers import CategorySerializer, ProductSerializer, ProductDetailSerializer, ProductListSerializer, ProductImageSerializer


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


class SellerProductViewSet(viewsets.ModelViewSet):
    """판매자 상품 관리 ViewSet"""

    serializer_class = ProductSerializer
    pagination_class = StandardResultsSetPagination

    def get_permissions(self):
        """액션별 권한 설정"""
        from sellers.permissions import IsSeller, IsSellerProduct

        if self.action in ['list', 'retrieve']:
            # 자신의 상품 목록은 조회 가능
            permission_classes = [IsSeller]
        else:
            # 생성/수정/삭제는 판매자 권한 + 소유자 확인
            permission_classes = [IsSellerProduct]

        return [permission() for permission in permission_classes]

    def get_queryset(self):
        """자신의 상품만 조회"""
        if hasattr(self.request.user, 'seller_profile'):
            return Product.objects.filter(
                seller=self.request.user.seller_profile
            ).select_related('category').order_by('-created_at')
        return Product.objects.none()

    def perform_create(self, serializer):
        """상품 생성 (판매자 상품)"""
        serializer.save(
            seller=self.request.user.seller_profile,
            product_type='seller',
            status='draft'  # 초기 상태는 임시저장
        )

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """상품 발행 (draft → active)"""
        product = self.get_object()

        # 필수 정보 검증
        if not all([product.name, product.price, product.main_image_url, product.category]):
            return Response(
                {'error': '필수 정보를 모두 입력해주세요. (상품명, 가격, 이미지, 카테고리)'},
                status=status.HTTP_400_BAD_REQUEST
            )

        product.status = 'active'
        product.published_at = timezone.now()
        product.save()

        return Response({
            'message': '상품이 발행되었습니다.',
            'product': self.get_serializer(product).data
        })

    @action(detail=True, methods=['post'])
    def unpublish(self, request, pk=None):
        """상품 비공개 (active → inactive)"""
        product = self.get_object()
        product.status = 'inactive'
        product.save()

        return Response({
            'message': '상품이 비공개 처리되었습니다.',
            'product': self.get_serializer(product).data
        })


class ProductImageManageView(APIView):
    """상품 이미지 추가/삭제 API (판매자용)"""

    def get_permissions(self):
        """판매자만 접근 가능"""
        from sellers.permissions import IsSeller
        return [IsSeller()]

    def post(self, request, product_id):
        """이미지 추가 (URL 기반 - MVP)"""
        # 자신의 상품인지 확인
        product = get_object_or_404(
            Product,
            id=product_id,
            seller=request.user.seller_profile
        )

        # 이미지 URL 리스트 받기
        images_data = request.data.get('images', [])
        if not isinstance(images_data, list):
            return Response(
                {'error': 'images 필드는 배열이어야 합니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        created_images = []
        for img_data in images_data:
            image_url = img_data.get('image_url')
            if not image_url:
                continue

            # ProductImage 생성
            image = ProductImage.objects.create(
                product=product,
                image_url=image_url,
                alt_text=img_data.get('alt_text', product.name),
                display_order=img_data.get('display_order', 0),
            )
            created_images.append(image)

        serializer = ProductImageSerializer(created_images, many=True)
        return Response({
            'message': f'{len(created_images)}개의 이미지가 추가되었습니다.',
            'images': serializer.data
        }, status=status.HTTP_201_CREATED)

    def delete(self, request, product_id, image_id):
        """이미지 삭제"""
        # 자신의 상품인지 확인
        product = get_object_or_404(
            Product,
            id=product_id,
            seller=request.user.seller_profile
        )

        # 이미지 삭제
        image = get_object_or_404(ProductImage, id=image_id, product=product)
        image.delete()

        return Response({
            'message': '이미지가 삭제되었습니다.'
        }, status=status.HTTP_204_NO_CONTENT)
