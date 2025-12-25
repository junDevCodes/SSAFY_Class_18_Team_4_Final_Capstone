"""
판매자 관련 뷰 (ERD V2.1)
"""
from rest_framework import viewsets, generics, status, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.pagination import PageNumberPagination
from django.utils import timezone
from django.db import transaction
from django.db.models import Count
from drf_spectacular.utils import extend_schema, extend_schema_view
from orders.models import OrderItem, OrderItemStatus, OrderStatus
from .models import Seller, SellerBusiness, SellerSchedule
from .serializers import (
    SellerSerializer,
    SellerRegistrationSerializer,
    SellerApprovalSerializer,
    SellerPublicSerializer,
    SellerScheduleSerializer,
    SellerImageUploadSerializer,
    SellerOrderItemSerializer,
    SellerOrderItemStatusUpdateSerializer,
)
from .permissions import IsSeller, IsOwnerSeller
from products.services.s3_upload import S3ImageUploader, S3UploadError


class SellerOrderPagination(PageNumberPagination):
    """판매자 주문관리 기본 페이지네이션"""

    page_size = 15
    page_size_query_param = "page_size"
    max_page_size = 50


@extend_schema(
    tags=['판매자'],
    summary='판매자 등록 신청',
    description='일반 회원이 판매자로 등록을 신청합니다. MVP에서는 자동 승인됩니다.',
)
class SellerRegistrationView(generics.CreateAPIView):
    """판매자 등록 신청 API"""

    serializer_class = SellerRegistrationSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        """판매자 등록 (이미 판매자인 경우 사전 검증)"""
        # 이미 판매자인지 확인 (perform_create가 아닌 create에서 검증)
        if hasattr(request.user, 'seller_profile'):
            return Response(
                {'error': '이미 판매자로 등록되어 있습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().create(request, *args, **kwargs)

    @transaction.atomic
    def perform_create(self, serializer):
        """판매자 생성 (트랜잭션 보장)"""
        user = self.request.user

        # MVP: 자동 승인 (프로덕션에서는 pending 상태로 저장)
        seller = serializer.save(
            user=user,
            status='active',  # MVP: 자동 승인
        )

        # SellerBusiness의 verified_at 업데이트 (ERD V2.1)
        if hasattr(seller, 'business'):
            seller.business.verified_at = timezone.now()
            seller.business.save()

        # User role 업데이트
        user.role = 'seller'
        user.save()

        return seller


@extend_schema_view(
    list=extend_schema(
        tags=['판매자'],
        summary='판매자 목록 조회',
        description='활성 상태의 판매자 목록을 조회합니다.',
    ),
    retrieve=extend_schema(
        tags=['판매자'],
        summary='판매자 상세 조회',
        description='판매자의 상세 정보를 조회합니다.',
    ),
    me=extend_schema(
        tags=['판매자'],
        summary='내 판매자 정보',
        description='현재 로그인한 사용자의 판매자 정보를 조회합니다.',
    ),
)
class SellerViewSet(viewsets.ModelViewSet):
    """판매자 ViewSet"""

    queryset = Seller.objects.all()
    serializer_class = SellerSerializer
    lookup_field = 'brand_slug'

    def get_permissions(self):
        """액션별 권한 설정"""
        if self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [IsAuthenticated, IsOwnerSeller]
        elif self.action == 'create':
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = []
        return [permission() for permission in permission_classes]

    def get_serializer_class(self):
        """액션별 시리얼라이저 설정"""
        if self.action in ['list', 'retrieve']:
            return SellerPublicSerializer
        return SellerSerializer

    def get_queryset(self):
        """필터링된 쿼리셋"""
        queryset = Seller.objects.filter(status='active')

        # 검색
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(brand_name__icontains=search)

        return queryset.select_related('user')

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def me(self, request):
        """자신의 판매자 정보 조회"""
        if not hasattr(request.user, 'seller_profile'):
            return Response(
                {'error': '판매자로 등록되지 않았습니다.'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = self.get_serializer(request.user.seller_profile)
        return Response(serializer.data)


class SellerApprovalView(generics.UpdateAPIView):
    """판매자 승인/거절 API (관리자용)"""

    queryset = Seller.objects.all()
    serializer_class = SellerApprovalSerializer
    permission_classes = [IsAdminUser]

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        seller = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        action_type = serializer.validated_data['action']
        reason = serializer.validated_data.get('reason', '')

        if action_type == 'approve':
            seller.status = 'active'
            seller.save()

            # SellerBusiness의 verified_at 업데이트 (ERD V2.1)
            if hasattr(seller, 'business'):
                seller.business.verified_at = timezone.now()
                seller.business.save()

            # User role 업데이트
            seller.user.role = 'seller'
            seller.user.save()

            # TODO: 판매자에게 승인 알림 이메일 발송

            return Response({
                'message': '판매자가 승인되었습니다.',
                'seller': SellerSerializer(seller).data
            })

        elif action_type == 'reject':
            seller.status = 'inactive'
            seller.save()

            # TODO: 판매자에게 거절 알림 이메일 발송 (reason 포함)

            return Response({
                'message': '판매자 등록이 거절되었습니다.',
                'reason': reason
            })

        return Response(
            {'error': 'Invalid action'},
            status=status.HTTP_400_BAD_REQUEST
        )


@extend_schema(
    tags=['판매자'],
    summary='판매자 대시보드',
    description='판매자의 상품 통계 및 대시보드 정보를 조회합니다.',
)
class SellerDashboardView(generics.RetrieveAPIView):
    """판매자 대시보드 API (통계 정보)"""

    serializer_class = SellerSerializer
    permission_classes = [IsSeller]

    def get_object(self):
        return self.request.user.seller_profile

    def retrieve(self, request, *args, **kwargs):
        seller = self.get_object()

        # 추가 통계 정보 계산 (ERD V2.1: ProductStats 테이블에서 집계)
        from products.models import Product, ProductStats
        from orders.models import OrderItem, OrderItemStatus, OrderStatus
        from django.db.models import Sum, Avg, F, IntegerField

        products = Product.objects.filter(seller=seller)

        # ERD V2.1: ProductStats 테이블에서 통계 정보 집계
        product_ids = products.values_list('id', flat=True)
        stats_qs = ProductStats.objects.filter(product_id__in=product_ids)

        valid_order_statuses = [
            OrderStatus.PAID,
            OrderStatus.PROCESSING,
            OrderStatus.SHIPPED,
            OrderStatus.DELIVERED,
        ]
        order_items_qs = (
            OrderItem.objects.filter(
                seller=seller,
                order__status__in=valid_order_statuses,
            )
            .exclude(status__in=[OrderItemStatus.CANCELLED, OrderItemStatus.REFUNDED])
        )

        revenue_expr = F('unit_price_snapshot') * F('quantity') - F('discount_amount')
        total_revenue = (
            order_items_qs.aggregate(
                total=Sum(revenue_expr, output_field=IntegerField())
            )['total']
            or 0
        )

        total_review_count = stats_qs.aggregate(total=Sum('review_count'))['total'] or 0
        if total_review_count:
            weighted_rating_sum = (
                stats_qs.annotate(
                    weighted_rating=F('average_rating') * F('review_count')
                ).aggregate(total=Sum('weighted_rating'))['total']
                or 0
            )
            average_rating = float(weighted_rating_sum) / float(total_review_count)
        else:
            average_rating = 0.0

        stats = {
            'total_products': products.count(),
            'active_products': products.filter(status='active').count(),
            'draft_products': products.filter(status='draft').count(),
            'total_orders': order_items_qs.count(),
            'total_revenue': total_revenue,
            'average_rating': round(average_rating, 2),
            'total_views': stats_qs.aggregate(Sum('view_count'))['view_count__sum'] or 0,
            'total_clicks': stats_qs.aggregate(Sum('recommend_clicked_count'))['recommend_clicked_count__sum'] or 0,
            'avg_quality_score': stats_qs.aggregate(Avg('quality_score'))['quality_score__avg'] or 0,
        }

        serializer = self.get_serializer(seller)
        return Response({
            **serializer.data,
            'statistics': stats
        })


class SellerImageUploadView(APIView):
    """판매자 이미지 업로드 API

    POST /api/sellers/me/images/upload/

    판매자 프로필 이미지, 브랜드 로고, 브랜드 배너를 S3에 업로드합니다.
    """
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAuthenticated, IsSeller]

    @extend_schema(
        tags=['판매자'],
        summary='판매자 이미지 업로드',
        description='''판매자 관련 이미지를 S3에 업로드합니다.

### 요청 형식
- Content-Type: multipart/form-data
- image: 이미지 파일 (JPEG, PNG, GIF, WebP)
- image_type: 이미지 유형
  - `profile`: 판매자 프로필 이미지
  - `logo`: 브랜드 로고
  - `banner`: 브랜드 배너

### S3 저장 경로
- 프로필: `seller_profile/seller_profile/seller_{id}_{uuid}.{ext}`
- 로고: `seller_profile/brand_logo/seller_{id}_{uuid}.{ext}`
- 배너: `seller_profile/brand_banner/seller_{id}_{uuid}.{ext}`

### 파일 제한
- 지원 형식: JPEG, PNG, GIF, WebP
- 최대 크기: 5MB
''',
        request=SellerImageUploadSerializer,
    )
    def post(self, request):
        """이미지 파일 업로드 → S3 → DB 저장"""
        # 판매자 프로필 확인
        if not hasattr(request.user, 'seller_profile'):
            return Response(
                {'error': '판매자로 등록되지 않았습니다.'},
                status=status.HTTP_404_NOT_FOUND
            )

        seller = request.user.seller_profile

        serializer = SellerImageUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        image = serializer.validated_data['image']
        image_type = serializer.validated_data['image_type']

        # S3 업로더 초기화
        try:
            uploader = S3ImageUploader()
        except S3UploadError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # 이미지 타입별 업로드 및 DB 필드 업데이트
        try:
            old_url = None
            if image_type == 'profile':
                old_url = seller.profile_image_url
                url = uploader.upload_seller_profile(image, seller.id, image.name)
                seller.profile_image_url = url
                field_name = 'profile_image_url'
            elif image_type == 'logo':
                old_url = seller.brand_logo_url
                url = uploader.upload_brand_logo(image, seller.id, image.name)
                seller.brand_logo_url = url
                field_name = 'brand_logo_url'
            elif image_type == 'banner':
                old_url = seller.brand_banner_url
                url = uploader.upload_brand_banner(image, seller.id, image.name)
                seller.brand_banner_url = url
                field_name = 'brand_banner_url'
            else:
                return Response(
                    {'error': '지원하지 않는 이미지 타입입니다.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            seller.save(update_fields=[field_name, 'updated_at'])

            # 기존 이미지 삭제 (선택적)
            if old_url:
                try:
                    uploader.delete_image(old_url)
                except Exception:
                    pass  # 기존 이미지 삭제 실패는 무시

            return Response({
                'message': f'{image_type} 이미지가 업로드되었습니다.',
                'image_type': image_type,
                'image_url': url
            }, status=status.HTTP_201_CREATED)

        except S3UploadError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SellerOrderItemViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """판매자 주문관리용 OrderItem ViewSet"""

    serializer_class = SellerOrderItemSerializer
    permission_classes = [IsAuthenticated, IsSeller]
    pagination_class = SellerOrderPagination

    def get_queryset(self):
        seller = getattr(self.request.user, 'seller_profile', None)
        if not seller:
            return OrderItem.objects.none()

        queryset = (
            OrderItem.objects.filter(seller=seller)
            .select_related('order', 'product')
            .prefetch_related('product__images')
            .order_by('-created_at')
        )

        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)

        return queryset

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """상태별 개수 요약 (탭 배지용)"""
        counts = {choice[0]: 0 for choice in OrderItemStatus.choices}
        for row in self.get_queryset().values('status').annotate(count=Count('id')):
            counts[row['status']] = row['count']
        return Response(counts)

    @action(detail=True, methods=['patch'], url_path='status')
    def update_status(self, request, pk=None):
        """주문 항목 상태 변경 (주문확인중/배송출고/배송중/배송완료)"""
        order_item = self.get_object()
        serializer = SellerOrderItemStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_status = serializer.validated_data['status']
        order_item.status = new_status
        order_item.save(update_fields=['status'])

        self._sync_order_status(order_item.order)

        return Response(
            {
                'message': '상태가 변경되었습니다.',
                'item': SellerOrderItemSerializer(order_item).data,
            }
        )

    def _sync_order_status(self, order):
        """주문 아이템 상태에 맞춰 주문 상태도 최신화"""
        statuses = list(order.items.values_list('status', flat=True))
        target_status = order.status

        if statuses and all(status == OrderItemStatus.DELIVERED for status in statuses):
            target_status = OrderStatus.DELIVERED
        elif any(status == OrderItemStatus.SHIPPING for status in statuses):
            target_status = OrderStatus.SHIPPED
        elif any(status == OrderItemStatus.PAID for status in statuses):
            target_status = OrderStatus.PROCESSING
        elif any(status == OrderItemStatus.PENDING for status in statuses):
            target_status = OrderStatus.PAID

        if target_status != order.status:
            order.status = target_status
            order.save(update_fields=['status', 'updated_at'])
