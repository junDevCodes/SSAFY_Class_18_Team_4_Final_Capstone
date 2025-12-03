"""
판매자 관련 뷰 (ERD V2.1)
"""
from rest_framework import viewsets, generics, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.utils import timezone
from django.db import transaction
from .models import Seller, SellerBusiness, SellerSchedule
from .serializers import (
    SellerSerializer,
    SellerRegistrationSerializer,
    SellerApprovalSerializer,
    SellerPublicSerializer,
    SellerScheduleSerializer,
)
from .permissions import IsSeller, IsOwnerSeller


class SellerRegistrationView(generics.CreateAPIView):
    """판매자 등록 신청 API"""

    serializer_class = SellerRegistrationSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        user = self.request.user

        # 이미 판매자인지 확인
        if hasattr(user, 'seller_profile'):
            return Response(
                {'error': '이미 판매자로 등록되어 있습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

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
        from django.db.models import Sum, Avg, Count

        products = Product.objects.filter(seller=seller)

        # ERD V2.1: ProductStats 테이블에서 통계 정보 집계
        product_ids = products.values_list('id', flat=True)
        stats_qs = ProductStats.objects.filter(product_id__in=product_ids)

        stats = {
            'total_products': products.count(),
            'active_products': products.filter(status='active').count(),
            'draft_products': products.filter(status='draft').count(),
            'total_views': stats_qs.aggregate(Sum('view_count'))['view_count__sum'] or 0,
            'total_clicks': stats_qs.aggregate(Sum('recommend_clicked_count'))['recommend_clicked_count__sum'] or 0,
            'avg_quality_score': stats_qs.aggregate(Avg('quality_score'))['quality_score__avg'] or 0,
        }

        serializer = self.get_serializer(seller)
        return Response({
            **serializer.data,
            'statistics': stats
        })
