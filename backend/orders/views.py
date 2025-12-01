"""
주문 관련 뷰
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.db import transaction
from django.utils import timezone
from django.shortcuts import get_object_or_404
from .models import Order, OrderItem
from .serializers import (
    OrderSerializer,
    OrderItemSerializer,
    OrderCreateSerializer,
    OrderCancelSerializer
)
from products.models import Cart


class StandardResultsSetPagination(PageNumberPagination):
    """표준 페이지네이션 설정"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    """주문 ViewSet"""

    serializer_class = OrderSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """자신의 주문만 조회"""
        return Order.objects.filter(user=self.request.user).prefetch_related('items', 'items__product')

    @transaction.atomic
    @action(detail=False, methods=['post'])
    def create_order(self, request):
        """장바구니에서 주문 생성 (MVP)"""
        serializer = OrderCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        # 검증된 데이터
        cart_items = serializer.validated_data['cart_items']
        recipient_name = serializer.validated_data['recipient_name']
        recipient_phone = serializer.validated_data['recipient_phone']
        shipping_address = serializer.validated_data['shipping_address']
        shipping_memo = serializer.validated_data.get('shipping_memo', '')
        payment_method_type = serializer.validated_data.get('payment_method_type', 'card')

        # 금액 계산
        subtotal = sum(item.subtotal for item in cart_items)
        shipping_fee = 3000 if subtotal < 30000 else 0  # 3만원 이상 무료배송
        discount_amount = 0  # MVP: 할인 없음
        total_amount = subtotal + shipping_fee - discount_amount

        # 주문 생성
        order = Order.objects.create(
            user=request.user,
            recipient_name=recipient_name,
            recipient_phone=recipient_phone,
            shipping_address=shipping_address,
            shipping_memo=shipping_memo,
            payment_method_type=payment_method_type,
            subtotal=subtotal,
            shipping_fee=shipping_fee,
            discount_amount=discount_amount,
            total_amount=total_amount,
            order_status='pending',
            payment_status='pending',
        )

        # 주문 상품 생성 (장바구니 상품 스냅샷)
        order_items = []
        for cart_item in cart_items:
            product = cart_item.product
            order_item = OrderItem.objects.create(
                order=order,
                product=product,
                seller=product.seller if hasattr(product, 'seller') else None,
                product_name=product.name,
                product_image_url=product.main_image_url or product.image_url,
                quantity=cart_item.quantity,
                unit_price=product.final_price,
                discount_amount=0,
                total_price=product.final_price * cart_item.quantity,
            )
            order_items.append(order_item)

        # 장바구니에서 주문한 항목 삭제
        Cart.objects.filter(id__in=[item.id for item in cart_items]).delete()

        # MVP: 실제 결제 없이 바로 결제 완료 처리
        order.payment_status = 'paid'
        order.order_status = 'paid'
        order.paid_at = timezone.now()
        order.save()

        # 응답
        response_serializer = OrderSerializer(order)
        return Response({
            'message': '주문이 완료되었습니다.',
            'order': response_serializer.data
        }, status=status.HTTP_201_CREATED)

    @transaction.atomic
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """주문 취소"""
        order = self.get_object()

        # 취소 가능 상태 확인
        if order.order_status not in ['pending', 'paid', 'processing']:
            return Response(
                {'error': '취소할 수 없는 주문입니다. (배송 중이거나 이미 취소된 주문)'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = OrderCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # 취소 처리
        order.order_status = 'cancelled'
        order.cancelled_at = timezone.now()
        order.cancel_reason = serializer.validated_data['cancel_reason']

        # MVP: 환불 처리 (실제로는 PG사 연동 필요)
        if order.payment_status == 'paid':
            order.payment_status = 'refunded'
            order.refunded_at = timezone.now()
            order.refund_amount = order.total_amount

        order.save()

        return Response({
            'message': '주문이 취소되었습니다.',
            'order': OrderSerializer(order).data
        })

    @action(detail=True, methods=['post'])
    def confirm_delivery(self, request, pk=None):
        """배송 완료 확인"""
        order = self.get_object()

        if order.order_status != 'shipped':
            return Response(
                {'error': '배송 중인 주문만 배송 완료 처리할 수 있습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        order.order_status = 'delivered'
        order.delivered_at = timezone.now()
        order.save()

        return Response({
            'message': '배송이 완료되었습니다.',
            'order': OrderSerializer(order).data
        })
