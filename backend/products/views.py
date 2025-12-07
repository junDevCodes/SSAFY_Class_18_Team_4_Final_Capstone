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
from django.db.models import F
from django.utils import timezone
from django.shortcuts import get_object_or_404
from .models import (
    Category, Product, ProductImage, Wishlist, Cart,
    ProductDetail as ProductDetailModel, ProductStats
)
from .serializers import (
    CategorySerializer, ProductSerializer, ProductDetailSerializer,
    ProductListSerializer, ProductImageSerializer, WishlistSerializer, CartSerializer,
    ProductListSerializerV2, ProductDetailSerializerV2
)


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
    filterset_fields = ['category', 'status']
    search_fields = ['name']


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

        # ERD V2.1: ProductStats 테이블의 view_count 증가
        ProductStats.objects.filter(product_id=instance.id).update(
            view_count=F('view_count') + 1
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
