"""
제품 관련 뷰

v2.1: ProductDetail, ProductInventory, ProductStats, ProductPriceHistory 지원
"""
from rest_framework import viewsets, filters, generics, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import F, Subquery, OuterRef, Value, IntegerField
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.db import transaction
from decimal import Decimal
from django.db.models import Avg
from django.core.cache import cache
from django.utils.encoding import iri_to_uri
from django.conf import settings
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes
from .models import (
    Category, Product, ProductImage, Wishlist, Cart,
    ProductDetail as ProductDetailModel, ProductStats, UserProductStats,
    Review, ReviewImage, ReviewStatus, DailySalesStats
)
from rest_framework.parsers import MultiPartParser, FormParser
from .serializers import (
    CategorySerializer, ProductSerializer, ProductDetailSerializer,
    ProductListSerializer, ProductImageSerializer, WishlistSerializer, CartSerializer,
    ProductListSerializerV2, ProductDetailSerializerV2,
    ReviewSerializer, ReviewCreateSerializer,
    NewProductListSerializer, BestProductListSerializer,
    SellerProductCreateSerializer, ProductImageUploadSerializer, ProductDetailImageUploadSerializer
)
from .services.s3_upload import S3ImageUploader, S3UploadError


class StandardResultsSetPagination(PageNumberPagination):
    """표준 페이지네이션 설정"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


@extend_schema_view(
    list=extend_schema(
        tags=['카테고리'],
        summary='카테고리 목록 조회',
        description='모든 카테고리 목록을 페이지네이션과 함께 반환합니다.',
    ),
    retrieve=extend_schema(
        tags=['카테고리'],
        summary='카테고리 상세 조회',
        description='특정 카테고리의 상세 정보를 반환합니다.',
    ),
)
class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    카테고리 ViewSet (읽기 전용)

    list: 카테고리 목록 조회
    retrieve: 카테고리 상세 조회
    """
    queryset = Category.objects.all().order_by('id')
    serializer_class = CategorySerializer
    pagination_class = StandardResultsSetPagination


@extend_schema_view(
    list=extend_schema(
        tags=['상품'],
        summary='상품 목록 조회 (레거시)',
        description='모든 상품 목록을 조회합니다. 카테고리 및 상태로 필터링 가능합니다.',
    ),
    retrieve=extend_schema(
        tags=['상품'],
        summary='상품 상세 조회 (레거시)',
        description='특정 상품의 상세 정보를 반환합니다.',
    ),
)
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
    filterset_fields = ['category', 'status']
    search_fields = ['name']


@extend_schema(
    tags=['상품'],
    summary='상품 목록 조회',
    description='''상품 목록을 조회합니다. 다양한 필터링과 정렬을 지원합니다.

### 커스텀 필터
- `is_featured=true`: 추천 상품 (quality_score 70 이상)
- `is_best=true`: 베스트 상품 (주문수/조회수 기준)
- `is_new=true`: 신상품 (최근 7일 내 등록)
- `is_on_sale=true`: 할인 상품 (original_price > price)

### 기본 필터
- `category`: 카테고리 ID
- `price__gte`, `price__lte`: 가격 범위
- `status`: 상품 상태 (active, inactive 등)
- `product_type`: 상품 유형 (main, seller)
''',
    parameters=[
        OpenApiParameter(name='is_featured', type=OpenApiTypes.BOOL, description='추천 상품 필터'),
        OpenApiParameter(name='is_best', type=OpenApiTypes.BOOL, description='베스트 상품 필터'),
        OpenApiParameter(name='is_new', type=OpenApiTypes.BOOL, description='신상품 필터 (7일 이내)'),
        OpenApiParameter(name='is_on_sale', type=OpenApiTypes.BOOL, description='할인 상품 필터'),
        OpenApiParameter(name='category', type=OpenApiTypes.INT, description='카테고리 ID'),
        OpenApiParameter(name='search', type=OpenApiTypes.STR, description='상품명 검색'),
        OpenApiParameter(name='ordering', type=OpenApiTypes.STR, description='정렬 기준 (예: -created_at, price)'),
    ],
)
class ProductListView(generics.ListAPIView):
    """상품 목록 API (필터링 및 정렬 지원)

    v2.1: ProductStats 테이블에서 통계 데이터를 가져옵니다.

    커스텀 필터 (프론트엔드 호환):
    - is_featured: 추천 상품 (quality_score 기준 정렬)
    - is_best: 베스트 상품 (조회수/주문수 기준 정렬)
    - is_new: 신상품 (최근 7일 내 등록)
    - is_on_sale: 할인 상품 (original_price > price)
    """

    serializer_class = ProductListSerializerV2
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]

    # 필터링 (ERD V2.1 필드만 사용)
    filterset_fields = {
        'category': ['exact'],
        'price': ['gte', 'lte'],
        'status': ['exact'],
        'product_type': ['exact'],
    }

    # 검색 (ERD V2.1 필드만 사용)
    search_fields = ['name']

    # 정렬 (ERD V2.1 필드, stats 테이블 필드 포함)
    ordering_fields = [
        'price', 'created_at',
        'stats__quality_score', 'stats__view_count',
        'stats__order_event_count', 'stats__average_rating'
    ]
    ordering = ['-created_at']  # 기본 정렬: 최신순

    def get_queryset(self):
        """쿼리셋 최적화 - v2.1 stats 테이블 prefetch + 커스텀 필터"""
        from datetime import timedelta
        from django.db.models import Q

        queryset = Product.objects.filter(status='active').select_related(
            'category', 'stats', 'inventory'
        )

        # 커스텀 필터: is_featured (추천 상품 - quality_score 기준)
        is_featured = self.request.query_params.get('is_featured')
        if is_featured and is_featured.lower() in ('true', '1'):
            # quality_score 70 이상인 상품을 quality_score 내림차순으로 정렬
            queryset = queryset.filter(
                stats__quality_score__gte=70
            ).order_by('-stats__quality_score', '-created_at')

        # 커스텀 필터: is_best (베스트 상품 - 조회수/주문수 기준)
        is_best = self.request.query_params.get('is_best')
        if is_best and is_best.lower() in ('true', '1'):
            # 주문 이벤트 또는 조회수가 높은 상품 (주문수 > 0 또는 조회수 > 100)
            queryset = queryset.filter(
                Q(stats__order_event_count__gt=0) | Q(stats__view_count__gte=100)
            ).order_by('-stats__order_event_count', '-stats__view_count', '-created_at')

        # 커스텀 필터: is_new (신상품 - 최근 7일 내 등록)
        is_new = self.request.query_params.get('is_new')
        if is_new and is_new.lower() in ('true', '1'):
            seven_days_ago = timezone.now() - timedelta(days=7)
            queryset = queryset.filter(
                created_at__gte=seven_days_ago
            ).order_by('-created_at')

        # 커스텀 필터: is_on_sale (할인 상품 - original_price > price)
        is_on_sale = self.request.query_params.get('is_on_sale')
        if is_on_sale and is_on_sale.lower() in ('true', '1'):
            queryset = queryset.filter(
                original_price__isnull=False,
                original_price__gt=F('price')
            ).order_by('-created_at')

        return queryset

    def list(self, request, *args, **kwargs):
        """
        상품 목록 응답을 Redis 캐시에 저장하여 배치/가격 추적 중에도
        최근 결과를 안정적으로 제공한다.

        - 캐시 키: 요청 URL 전체 (쿼리 파라미터 포함)
        - TTL: settings.PRODUCT_LIST_CACHE_TTL (기본 60초, 환경변수로 조정 가능)
        """
        cache_key = "product_list:" + iri_to_uri(request.get_full_path())

        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        response = super().list(request, *args, **kwargs)

        # 정상 응답 데이터를 캐시에 저장 (기본 TTL 60초, 환경변수로 조정)
        cache.set(cache_key, response.data, timeout=settings.PRODUCT_LIST_CACHE_TTL)

        return response


@extend_schema(
    tags=['상품'],
    summary='상품 상세 조회',
    description='''상품의 상세 정보를 조회합니다.

### 포함 정보
- 기본 정보 (이름, 가격, 카테고리 등)
- 상세 설명 (detail)
- 재고 정보 (inventory)
- 통계 정보 (stats: 조회수, 리뷰 수, 평점 등)
- 판매자 정보
- 상품 이미지 목록
- 관련 상품 추천

### 조회수 증가
- 상세 페이지 조회 시 자동으로 조회수가 증가합니다.
- 로그인 사용자의 경우 개인별 조회 통계도 기록됩니다.
''',
)
class ProductDetailView(generics.RetrieveAPIView):
    """상품 상세 API (ERD V2.1)

    ERD V2.1: detail, inventory, stats 분리 테이블을 포함하여 응답합니다.
    """

    queryset = Product.objects.select_related(
        'category', 'seller', 'detail', 'inventory', 'stats'
    ).prefetch_related('images')
    serializer_class = ProductDetailSerializerV2

    def retrieve(self, request, *args, **kwargs):
        """조회수 증가 (ERD V2.1: ProductStats 테이블 사용)"""
        instance = self.get_object()

        # ERD V2.1: ProductStats 테이블의 view_count 증가 (전체 조회수)
        ProductStats.objects.filter(product_id=instance.id).update(
            view_count=F('view_count') + 1
        )

        # REC-005: 로그인 사용자일 경우 UserProductStats 업데이트
        if request.user.is_authenticated:
            # UPDATE 먼저 시도 (기존 레코드가 있는 경우)
            rows_updated = UserProductStats.objects.filter(
                user=request.user,
                product=instance
            ).update(
                view_count=F('view_count') + 1,
                last_interacted_at=timezone.now()
            )

            # 기존 레코드가 없으면 생성 (최초 조회)
            if rows_updated == 0:
                # get_or_create로 race condition 방지
                UserProductStats.objects.get_or_create(
                    user=request.user,
                    product=instance,
                    defaults={'view_count': 1}
                )

        # instance를 다시 가져와서 업데이트된 view_count 반영
        instance.refresh_from_db()

        return super().retrieve(request, *args, **kwargs)

    def get_object(self):
        """
        PK와 slug 모두 지원
        - /products/<int:pk>/
        - /products/<slug:slug>/
        """
        queryset = self.get_queryset()
        pk = self.kwargs.get('pk')
        if pk is not None:
            return queryset.get(pk=pk)
        slug = self.kwargs.get('slug')
        return queryset.get(slug=slug)


@extend_schema_view(
    list=extend_schema(
        tags=['판매자'],
        summary='내 상품 목록 조회',
        description='판매자 본인이 등록한 상품 목록을 조회합니다.',
    ),
    retrieve=extend_schema(
        tags=['판매자'],
        summary='내 상품 상세 조회',
        description='판매자 본인이 등록한 특정 상품의 상세 정보를 조회합니다.',
    ),
    create=extend_schema(
        tags=['판매자'],
        summary='상품 등록',
        description='''새로운 상품을 등록합니다.

### 자동 생성되는 데이터
- ProductDetail (상세 정보)
- ProductInventory (재고 정보)
- ProductStats (통계 정보)

### 초기 상태
- status: 'draft' (임시저장)
- product_type: 'seller' (판매자 상품)

### 발행 절차
상품 등록 후 `/api/seller-products/{id}/publish/` 엔드포인트로 발행해야 실제 판매가 시작됩니다.
''',
    ),
    update=extend_schema(
        tags=['판매자'],
        summary='상품 수정',
        description='판매자 본인이 등록한 상품을 수정합니다.',
    ),
    partial_update=extend_schema(
        tags=['판매자'],
        summary='상품 부분 수정',
        description='판매자 본인이 등록한 상품을 부분 수정합니다.',
    ),
    destroy=extend_schema(
        tags=['판매자'],
        summary='상품 삭제',
        description='판매자 본인이 등록한 상품을 삭제합니다.',
    ),
)
class SellerProductViewSet(viewsets.ModelViewSet):
    """판매자 상품 관리 ViewSet

    상품 CRUD와 함께 ProductDetail, ProductInventory, ProductStats를 자동 관리합니다.
    """

    pagination_class = StandardResultsSetPagination

    def get_serializer_class(self):
        """액션별 시리얼라이저 분기"""
        if self.action == 'create':
            return SellerProductCreateSerializer
        return ProductSerializer

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
            ).select_related(
                'category', 'detail', 'inventory', 'stats'
            ).prefetch_related('images').order_by('-created_at')
        return Product.objects.none()

    def perform_create(self, serializer):
        """상품 생성 (판매자 상품)"""
        serializer.save(
            seller=self.request.user.seller_profile,
            product_type='seller',
            status='draft'  # 초기 상태는 임시저장
        )

    @action(detail=True, methods=['post'])
    @extend_schema(
        tags=['판매자'],
        summary='상품 발행',
        description='임시저장 상태의 상품을 발행하여 판매를 시작합니다.',
    )
    def publish(self, request, pk=None):
        """상품 발행 (draft → active)"""
        product = self.get_object()

        # ERD V2.1: 메인 이미지는 ProductImage 테이블에서 확인
        has_image = product.images.exists()

        # 필수 정보 검증
        if not all([product.name, product.price, has_image, product.category]):
            return Response(
                {'error': '필수 정보를 모두 입력해주세요. (상품명, 가격, 이미지, 카테고리)'},
                status=status.HTTP_400_BAD_REQUEST
            )

        product.status = 'active'
        product.save(update_fields=['status', 'updated_at'])

        return Response({
            'message': '상품이 발행되었습니다.',
            'product': self.get_serializer(product).data
        })

    @action(detail=True, methods=['post'])
    @extend_schema(
        tags=['판매자'],
        summary='상품 비공개',
        description='발행된 상품을 비공개 처리합니다.',
    )
    def unpublish(self, request, pk=None):
        """상품 비공개 (active → inactive)"""
        product = self.get_object()
        product.status = 'inactive'
        product.save(update_fields=['status', 'updated_at'])

        return Response({
            'message': '상품이 비공개 처리되었습니다.',
            'product': self.get_serializer(product).data
        })


class ProductImageUploadView(APIView):
    """상품 메인 이미지 업로드 API (파일 업로드 → S3)

    POST /api/seller-products/{product_id}/images/upload/

    multipart/form-data로 이미지 파일을 받아 S3에 업로드하고
    ProductImage 레코드를 생성합니다.
    """
    parser_classes = [MultiPartParser, FormParser]

    def get_permissions(self):
        """판매자만 접근 가능"""
        from sellers.permissions import IsSeller
        return [IsSeller()]

    @extend_schema(
        tags=['판매자'],
        summary='상품 메인 이미지 업로드',
        description='''상품의 메인 이미지(썸네일)를 S3에 업로드합니다.

### 요청 형식
- Content-Type: multipart/form-data
- images: 이미지 파일 (여러 개 가능, 최대 10개)

### S3 저장 경로
- `homeplus/thumnail/{product_id}_{uuid}.{ext}`

### 이미지 순서
- 업로드 순서대로 display_order가 자동 할당됩니다.
- 기존 이미지가 있으면 마지막 순서 다음부터 할당됩니다.

### 지원 형식
- JPEG, PNG, GIF, WebP
- 최대 크기: 5MB/파일
''',
        request=ProductImageUploadSerializer,
        responses={201: ProductImageSerializer(many=True)}
    )
    def post(self, request, product_id):
        """이미지 파일 업로드 → S3 → DB 저장"""
        # 자신의 상품인지 확인
        product = get_object_or_404(
            Product,
            id=product_id,
            seller=request.user.seller_profile
        )

        serializer = ProductImageUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        images = serializer.validated_data['images']

        # S3 업로더 초기화
        uploader = S3ImageUploader()

        # 기존 이미지의 마지막 display_order 조회
        last_order = product.images.order_by('-display_order').values_list(
            'display_order', flat=True
        ).first()
        if last_order is None:
            last_order = -1

        created_images = []
        uploaded_urls = []  # 롤백 시 S3 정리용
        try:
            with transaction.atomic():
                for i, file_obj in enumerate(images):
                    # S3에 업로드
                    url = uploader.upload_thumbnail(file_obj, product.id, file_obj.name)
                    uploaded_urls.append(url)

                    # DB에 저장
                    image = ProductImage.objects.create(
                        product=product,
                        image_url=url,
                        display_order=last_order + 1 + i
                    )
                    created_images.append(image)
        except S3UploadError as e:
            # 업로드 실패 시 이미 업로드된 S3 이미지 정리
            for url in uploaded_urls:
                try:
                    uploader.delete_image(url)
                except Exception:
                    pass  # S3 정리 실패는 무시 (로그는 delete_image에서 처리)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        result_serializer = ProductImageSerializer(created_images, many=True)
        return Response({
            'message': f'{len(created_images)}개의 이미지가 업로드되었습니다.',
            'images': result_serializer.data
        }, status=status.HTTP_201_CREATED)


class ProductDetailImageUploadView(APIView):
    """상품 상세 설명 이미지 업로드 API

    POST /api/seller-products/{product_id}/detail-images/upload/

    상세 페이지 본문에 표시되는 이미지들을 S3에 업로드하고
    ProductDetail.full_image_description 배열에 추가합니다.
    """
    parser_classes = [MultiPartParser, FormParser]

    def get_permissions(self):
        """판매자만 접근 가능"""
        from sellers.permissions import IsSeller
        return [IsSeller()]

    @extend_schema(
        tags=['판매자'],
        summary='상품 상세 설명 이미지 업로드',
        description='''상품 상세 페이지 본문에 표시되는 이미지를 S3에 업로드합니다.

### 요청 형식
- Content-Type: multipart/form-data
- images: 이미지 파일 (여러 개 가능, 최대 20개)

### S3 저장 경로
- `homeplus/product_detail/{product_id}_{uuid}.{ext}`

### 저장 방식
- ProductDetail.full_image_description 배열에 URL이 순서대로 추가됩니다.
- 기존 이미지가 있으면 배열 끝에 추가됩니다.

### 지원 형식
- JPEG, PNG, GIF, WebP
- 최대 크기: 10MB/파일
''',
        request=ProductDetailImageUploadSerializer,
    )
    def post(self, request, product_id):
        """상세 이미지 파일 업로드 → S3 → ProductDetail 업데이트"""
        # 자신의 상품인지 확인
        product = get_object_or_404(
            Product,
            id=product_id,
            seller=request.user.seller_profile
        )

        serializer = ProductDetailImageUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        images = serializer.validated_data['images']

        # S3 업로더 초기화
        uploader = S3ImageUploader()

        # ProductDetail 조회 (없으면 생성)
        detail, created = ProductDetailModel.objects.get_or_create(
            product=product,
            defaults={
                'full_image_description': []
            }
        )

        uploaded_urls = []
        try:
            for file_obj in images:
                url = uploader.upload_detail_image(file_obj, product.id, file_obj.name)
                uploaded_urls.append(url)
        except S3UploadError as e:
            # 업로드 실패 시 이미 업로드된 S3 이미지 정리
            for url in uploaded_urls:
                try:
                    uploader.delete_image(url)
                except Exception:
                    pass  # S3 정리 실패는 무시
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # 기존 배열에 새 URL 추가 (select_for_update로 동시성 문제 방지)
        with transaction.atomic():
            # row lock을 걸어 다른 트랜잭션이 동시에 수정하지 못하도록 함
            locked_detail = ProductDetailModel.objects.select_for_update().get(
                product=product
            )
            current_images = locked_detail.full_image_description or []
            locked_detail.full_image_description = current_images + uploaded_urls
            locked_detail.save(update_fields=['full_image_description'])
            total_count = len(locked_detail.full_image_description)

        return Response({
            'message': f'{len(uploaded_urls)}개의 상세 이미지가 업로드되었습니다.',
            'image_urls': uploaded_urls,
            'total_images': total_count
        }, status=status.HTTP_201_CREATED)


class ProductImageManageView(APIView):
    """상품 이미지 관리 API (URL 기반 추가/삭제)"""

    def get_permissions(self):
        """판매자만 접근 가능"""
        from sellers.permissions import IsSeller
        return [IsSeller()]

    @extend_schema(
        tags=['판매자'],
        summary='상품 이미지 추가 (URL)',
        description='이미지 URL을 직접 입력하여 상품 이미지를 추가합니다.',
    )
    def post(self, request, product_id):
        """이미지 추가 (URL 기반)"""
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

            # ERD V2.1: ProductImage 생성 (alt_text 필드 없음)
            image = ProductImage.objects.create(
                product=product,
                image_url=image_url,
                display_order=img_data.get('display_order', 0),
            )
            created_images.append(image)

        serializer = ProductImageSerializer(created_images, many=True)
        return Response({
            'message': f'{len(created_images)}개의 이미지가 추가되었습니다.',
            'images': serializer.data
        }, status=status.HTTP_201_CREATED)

    @extend_schema(
        tags=['판매자'],
        summary='상품 이미지 삭제',
        description='상품 이미지를 삭제합니다. S3에서도 함께 삭제됩니다.',
    )
    def delete(self, request, product_id, image_id):
        """이미지 삭제 (S3 + DB)"""
        # 자신의 상품인지 확인
        product = get_object_or_404(
            Product,
            id=product_id,
            seller=request.user.seller_profile
        )

        # 이미지 조회
        image = get_object_or_404(ProductImage, id=image_id, product=product)

        # S3에서 이미지 삭제 시도 (실패해도 DB 레코드는 삭제)
        uploader = S3ImageUploader()
        uploader.delete_image(image.image_url)

        # DB에서 삭제
        image.delete()

        return Response({
            'message': '이미지가 삭제되었습니다.'
        }, status=status.HTTP_204_NO_CONTENT)


@extend_schema_view(
    list=extend_schema(
        tags=['찜 목록'],
        summary='찜 목록 조회',
        description='로그인한 사용자의 찜 목록을 조회합니다.',
    ),
    create=extend_schema(
        tags=['찜 목록'],
        summary='찜 추가',
        description='상품을 찜 목록에 추가합니다.',
    ),
    destroy=extend_schema(
        tags=['찜 목록'],
        summary='찜 삭제',
        description='찜 목록에서 상품을 제거합니다.',
    ),
    toggle=extend_schema(
        tags=['찜 목록'],
        summary='찜 토글',
        description='상품의 찜 상태를 토글합니다. 찜 되어 있으면 제거, 없으면 추가합니다.',
    ),
)
class WishlistViewSet(viewsets.ModelViewSet):
    """찜 목록 ViewSet"""

    serializer_class = WishlistSerializer
    pagination_class = StandardResultsSetPagination

    def get_permissions(self):
        """로그인 사용자만 접근"""
        from rest_framework.permissions import IsAuthenticated
        return [IsAuthenticated()]

    def get_queryset(self):
        """자신의 찜 목록만 조회"""
        return Wishlist.objects.filter(user=self.request.user).select_related('product', 'product__category')

    def perform_create(self, serializer):
        """찜 추가"""
        serializer.save(user=self.request.user)

    def destroy(self, request, *args, **kwargs):
        """찜 삭제 시 ProductStats의 wishlist_count도 감소"""
        instance = self.get_object()
        product_id = instance.product_id

        # 찜 삭제
        self.perform_destroy(instance)

        # v2.1: ProductStats의 wishlist_count 감소
        ProductStats.objects.filter(product_id=product_id).update(
            wishlist_count=F('wishlist_count') - 1
        )

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['post'])
    def toggle(self, request):
        """찜하기 토글 (있으면 삭제, 없으면 추가)"""
        product_id = request.data.get('product_id')
        if not product_id:
            return Response(
                {'error': 'product_id가 필요합니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 상품 존재 확인
        product = get_object_or_404(Product, id=product_id)

        # 찜 토글
        wishlist, created = Wishlist.objects.get_or_create(
            user=request.user,
            product=product
        )

        if not created:
            # 이미 존재하면 삭제
            wishlist.delete()

            # v2.1: ProductStats의 wishlist_count 감소
            ProductStats.objects.filter(product_id=product_id).update(
                wishlist_count=F('wishlist_count') - 1
            )

            # 현재 wishlist_count 조회
            stats = ProductStats.objects.filter(product_id=product_id).first()
            current_count = stats.wishlist_count if stats else 0

            return Response({
                'message': '찜 목록에서 제거되었습니다.',
                'is_wishlist': False,
                'wishlist_count': max(0, current_count)
            })
        else:
            # 새로 생성

            # v2.1: ProductStats의 wishlist_count 증가
            ProductStats.objects.filter(product_id=product_id).update(
                wishlist_count=F('wishlist_count') + 1
            )

            # 현재 wishlist_count 조회
            stats = ProductStats.objects.filter(product_id=product_id).first()
            current_count = stats.wishlist_count if stats else 1

            return Response({
                'message': '찜 목록에 추가되었습니다.',
                'is_wishlist': True,
                'wishlist': self.get_serializer(wishlist).data,
                'wishlist_count': current_count
            }, status=status.HTTP_201_CREATED)


@extend_schema_view(
    list=extend_schema(
        tags=['장바구니'],
        summary='장바구니 목록 조회',
        description='로그인한 사용자의 장바구니 목록을 조회합니다.',
    ),
    create=extend_schema(
        tags=['장바구니'],
        summary='장바구니 추가',
        description='상품을 장바구니에 추가합니다. 이미 있는 상품이면 수량이 증가합니다.',
    ),
    update=extend_schema(
        tags=['장바구니'],
        summary='장바구니 수정',
        description='장바구니 항목의 수량을 수정합니다.',
    ),
    partial_update=extend_schema(
        tags=['장바구니'],
        summary='장바구니 부분 수정',
        description='장바구니 항목의 수량을 부분 수정합니다.',
    ),
    destroy=extend_schema(
        tags=['장바구니'],
        summary='장바구니 삭제',
        description='장바구니에서 상품을 제거합니다.',
    ),
    summary=extend_schema(
        tags=['장바구니'],
        summary='장바구니 요약',
        description='장바구니의 총 금액, 상품 수, 총 수량을 조회합니다.',
    ),
    clear=extend_schema(
        tags=['장바구니'],
        summary='장바구니 비우기',
        description='장바구니의 모든 상품을 제거합니다.',
    ),
)
class CartViewSet(viewsets.ModelViewSet):
    """장바구니 ViewSet"""

    serializer_class = CartSerializer
    pagination_class = StandardResultsSetPagination

    def get_permissions(self):
        """로그인 사용자만 접근"""
        from rest_framework.permissions import IsAuthenticated
        return [IsAuthenticated()]

    def get_queryset(self):
        """자신의 장바구니만 조회"""
        return Cart.objects.filter(user=self.request.user).select_related('product', 'product__category')

    def perform_create(self, serializer):
        """장바구니 추가 (이미 있으면 수량 증가)"""
        product = serializer.validated_data['product']
        quantity = serializer.validated_data.get('quantity', 1)

        # 이미 장바구니에 있는지 확인
        cart_item, created = Cart.objects.get_or_create(
            user=self.request.user,
            product=product,
            defaults={'quantity': quantity}
        )

        if not created:
            # 이미 있으면 수량 증가
            cart_item.quantity += quantity
            cart_item.save()

        # 통계 업데이트: 새로 장바구니에 추가된 경우에만 cart_event_count 증가
        if created:
            # 전체 상품 통계 (ProductStats)
            ProductStats.objects.filter(product_id=product.id).update(
                cart_event_count=F('cart_event_count') + 1
            )

            # 사용자별 상품 통계 (UserProductStats)
            rows_updated = UserProductStats.objects.filter(
                user=self.request.user,
                product=product
            ).update(
                cart_event_count=F('cart_event_count') + 1,
                last_interacted_at=timezone.now()
            )

            # 기존 레코드가 없으면 생성
            if rows_updated == 0:
                UserProductStats.objects.create(
                    user=self.request.user,
                    product=product,
                    cart_event_count=1
                )

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """장바구니 요약 (총 금액 등)"""
        cart_items = self.get_queryset()

        total = sum(item.subtotal for item in cart_items)
        count = cart_items.count()
        total_quantity = sum(item.quantity for item in cart_items)

        return Response({
            'total': total,
            'count': count,
            'total_quantity': total_quantity,
            'items': self.get_serializer(cart_items, many=True).data
        })

    @action(detail=False, methods=['post'])
    def clear(self, request):
        """장바구니 비우기"""
        deleted_count, _ = self.get_queryset().delete()
        return Response({
            'message': f'{deleted_count}개 상품이 장바구니에서 제거되었습니다.'
        })


@extend_schema_view(
    list=extend_schema(
        tags=['리뷰'],
        summary='리뷰 목록 조회',
        description='리뷰 목록을 조회합니다. 상품 ID로 필터링 가능합니다.',
        parameters=[
            OpenApiParameter(name='product', type=OpenApiTypes.INT, description='상품 ID로 필터링'),
            OpenApiParameter(name='rating', type=OpenApiTypes.INT, description='평점으로 필터링 (1-5)'),
        ],
    ),
    retrieve=extend_schema(
        tags=['리뷰'],
        summary='리뷰 상세 조회',
        description='특정 리뷰의 상세 정보를 조회합니다.',
    ),
    create=extend_schema(
        tags=['리뷰'],
        summary='리뷰 작성',
        description='상품에 대한 리뷰를 작성합니다. 로그인이 필요하며, 한 상품에 하나의 리뷰만 작성 가능합니다.',
    ),
    update=extend_schema(
        tags=['리뷰'],
        summary='리뷰 수정',
        description='본인이 작성한 리뷰를 수정합니다.',
    ),
    partial_update=extend_schema(
        tags=['리뷰'],
        summary='리뷰 부분 수정',
        description='본인이 작성한 리뷰를 부분 수정합니다.',
    ),
    destroy=extend_schema(
        tags=['리뷰'],
        summary='리뷰 삭제',
        description='본인이 작성한 리뷰를 삭제합니다.',
    ),
    my=extend_schema(
        tags=['리뷰'],
        summary='내 리뷰 목록',
        description='로그인한 사용자가 작성한 리뷰 목록을 조회합니다.',
    ),
)
class ReviewViewSet(viewsets.ModelViewSet):
    """리뷰 ViewSet

    - GET /api/reviews/                    : 리뷰 목록 (상품별 필터링 가능)
    - GET /api/reviews/{id}/               : 리뷰 상세
    - POST /api/reviews/                   : 리뷰 작성 (로그인 필수)
    - PUT/PATCH /api/reviews/{id}/         : 리뷰 수정 (본인만)
    - DELETE /api/reviews/{id}/            : 리뷰 삭제 (본인만)
    - GET /api/reviews/my/                 : 내 리뷰 목록
    """

    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['product', 'rating']
    ordering_fields = ['created_at', 'rating']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'create':
            return ReviewCreateSerializer
        return ReviewSerializer

    def get_permissions(self):
        """액션별 권한 설정"""
        from rest_framework.permissions import IsAuthenticated, AllowAny

        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_queryset(self):
        """조회 가능한 리뷰 (visible 상태만)"""
        queryset = Review.objects.filter(
            status=ReviewStatus.VISIBLE
        ).select_related('user', 'product').prefetch_related('images')

        # 상품별 필터링
        product_id = self.request.query_params.get('product')
        if product_id:
            queryset = queryset.filter(product_id=product_id)

        return queryset

    def perform_create(self, serializer):
        """리뷰 생성 + ProductStats 업데이트"""
        review = serializer.save()
        self._update_product_stats(review.product)

    def perform_update(self, serializer):
        """리뷰 수정 + ProductStats 업데이트 (평점 변경 시)"""
        old_rating = serializer.instance.rating
        review = serializer.save()

        # 평점이 변경된 경우에만 통계 업데이트
        if old_rating != review.rating:
            self._update_product_stats(review.product)

    def perform_destroy(self, instance):
        """리뷰 삭제 + ProductStats 업데이트"""
        product = instance.product
        instance.delete()
        self._update_product_stats(product)

    def _update_product_stats(self, product):
        """상품의 리뷰 통계 재계산

        - review_count: 총 리뷰 수
        - average_rating: 평균 평점
        - photo_review_count: 사진 리뷰 수
        - first_review_at: 첫 리뷰 시각
        """
        reviews = Review.objects.filter(
            product=product,
            status=ReviewStatus.VISIBLE
        )

        # 집계 계산
        review_count = reviews.count()
        avg_rating = reviews.aggregate(avg=Avg('rating'))['avg'] or Decimal('0.00')
        photo_review_count = reviews.filter(has_photos=True).count()
        first_review = reviews.order_by('created_at').first()
        first_review_at = first_review.created_at if first_review else None

        # ProductStats 업데이트
        ProductStats.objects.filter(product=product).update(
            review_count=review_count,
            average_rating=round(Decimal(str(avg_rating)), 2),
            photo_review_count=photo_review_count,
            first_review_at=first_review_at
        )

    @action(detail=False, methods=['get'])
    def my(self, request):
        """내 리뷰 목록"""
        if not request.user.is_authenticated:
            return Response(
                {'detail': '로그인이 필요합니다.'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        reviews = Review.objects.filter(
            user=request.user
        ).select_related('product').prefetch_related('images').order_by('-created_at')

        page = self.paginate_queryset(reviews)
        if page is not None:
            serializer = ReviewSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = ReviewSerializer(reviews, many=True)
        return Response(serializer.data)


class ProductRecommendClickView(APIView):
    """추천 상품 클릭 기록 API

    POST /api/products/{id}/recommend-click/

    추천 섹션에서 상품을 클릭했을 때 호출하여
    recommend_clicked_count를 증가시킵니다.
    """

    def post(self, request, pk):
        """추천 클릭 수 증가"""
        product = get_object_or_404(Product, pk=pk)

        # ProductStats 업데이트
        ProductStats.objects.filter(product=product).update(
            recommend_clicked_count=F('recommend_clicked_count') + 1
        )

        return Response({
            'message': '추천 클릭이 기록되었습니다.',
            'product_id': product.id
        })


class NewProductListView(APIView):
    """신상품 목록 API

    GET /api/products/new/

    product_type이 'main'인 상품 중 최신순으로 40개를 반환합니다.
    프론트엔드에서 7일 필터링을 위해 created_at 필드를 포함합니다.
    """

    @extend_schema(
        tags=['신상품'],
        summary='신상품 목록 조회',
        description='''신상품 목록을 조회합니다.

### 조회 조건
- `product_type='main'` (메인 상품만)
- `status='active'` (판매중인 상품만)
- 최신순 정렬 (`-created_at`)
- 최대 40개 반환

### 프론트엔드 7일 필터
응답에 `created_at` 필드가 포함되어 있어 프론트엔드에서 7일 이내 상품만 필터링할 수 있습니다.
''',
        responses={
            200: OpenApiExample(
                name='성공 응답',
                value={
                    'count': 40,
                    'results': [
                        {
                            'id': 1,
                            'slug': 'organic-apple',
                            'name': '유기농 사과',
                            'price': 15000,
                            'original_price': 18000,
                            'main_image': 'https://example.com/images/apple.jpg',
                            'category_name': '과일',
                            'created_at': '2025-12-19T10:30:00Z'
                        }
                    ]
                }
            )
        }
    )
    def get(self, request):
        """신상품 40개 조회 (최신순 정렬)"""
        products = Product.objects.filter(
            product_type='main',
            status='active'
        ).select_related('category').prefetch_related('images').order_by('-created_at')[:40]

        serializer = NewProductListSerializer(products, many=True)

        return Response({
            'count': len(serializer.data),
            'results': serializer.data
        })


class BestProductListView(APIView):
    """베스트 상품 목록 API

    GET /api/products/best/

    product_type='seller'인 판매자 상품 중:
    1. 오늘 일일 판매량(주문 횟수) 상위 40개를 우선 선정
    2. 부족하면 누적 판매량(order_event_count) 순으로 채움
    3. 최종 40개를 판매량 내림차순 정렬하여 반환

    응답에는 리뷰 개수, 평균 평점, 일일/누적 판매량 정보가 포함됩니다.
    """

    @extend_schema(
        tags=['베스트 상품'],
        summary='베스트 상품 목록 조회',
        description='''판매자 상품 중 베스트 상품 40개를 조회합니다.

### 조회 조건
- `product_type='seller'` (판매자 상품만)
- `status='active'` (판매중인 상품만)

### 정렬 우선순위
1. **일일 판매량 (오늘)**: 오늘 주문 횟수 기준 상위
2. **누적 판매량**: 일일 판매량이 동일하거나 없으면 누적 주문 횟수로 정렬
3. **등록일**: 판매량이 동일하면 최신 상품 우선

### 응답 포함 정보
- 기본 상품 정보 (id, name, price, main_image 등)
- `review_count`: 리뷰 개수
- `average_rating`: 평균 평점 (1~5)
- `daily_order_count`: 오늘 주문 횟수
- `total_order_count`: 누적 주문 횟수
''',
        responses={
            200: OpenApiExample(
                name='성공 응답',
                value={
                    'count': 40,
                    'results': [
                        {
                            'id': 1,
                            'slug': 'fresh-milk-1l',
                            'name': '신선한 우유 1L',
                            'price': 3500,
                            'original_price': 4000,
                            'main_image': 'https://example.com/milk.jpg',
                            'category_name': '유제품',
                            'review_count': 42,
                            'average_rating': '4.50',
                            'daily_order_count': 15,
                            'total_order_count': 230,
                            'created_at': '2025-12-01T10:30:00Z'
                        }
                    ]
                }
            )
        }
    )
    def get(self, request):
        """베스트 상품 40개 조회 (판매량 기준 정렬)"""
        today = timezone.now().date()

        # 오늘 일일 판매량 서브쿼리
        daily_sales_subquery = DailySalesStats.objects.filter(
            product=OuterRef('pk'),
            date=today
        ).values('order_count')[:1]

        # 베이스 쿼리: 판매자 상품 + 활성 상태
        # 일일 판매량과 누적 판매량을 annotate로 추가
        products = Product.objects.filter(
            product_type='seller',
            status='active'
        ).select_related(
            'category', 'stats'
        ).prefetch_related(
            'images'
        ).annotate(
            daily_order_count=Coalesce(
                Subquery(daily_sales_subquery),
                Value(0),
                output_field=IntegerField()
            ),
            total_order_count=Coalesce(
                F('stats__order_event_count'),
                Value(0),
                output_field=IntegerField()
            )
        ).order_by(
            '-daily_order_count',   # 일일 판매량 내림차순
            '-total_order_count',   # 누적 판매량 내림차순
            '-created_at'           # 최신순
        )[:40]

        serializer = BestProductListSerializer(products, many=True)

        return Response({
            'count': len(serializer.data),
            'results': serializer.data
        })
