"""
주문 도메인 ViewSet (ERD V2.1 기준)

- 주문 목록/상세 조회
- 장바구니 기반 주문 생성
- 주문 취소
- 배송 완료 확인
"""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from django.db.models import F

from products.models import Cart, ProductInventory, ProductStats, UserProductStats

from .models import (
    Order,
    OrderItem,
    Shipment,
    Payment,
    OrderStatus,
    OrderItemStatus,
    PaymentStatus,
    PaymentMethodType,
)
from .serializers import (
    OrderSerializer,
    OrderItemSerializer,
    OrderCreateSerializer,
    OrderCancelSerializer,
    GuestOrderCreateSerializer,
    GuestOrderLookupSerializer,
)


class StandardResultsSetPagination(PageNumberPagination):
    """기본 페이지네이션 설정"""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    """주문 ViewSet (조회 + 커스텀 액션)

    - GET /api/orders/                 : 주문 목록
    - GET /api/orders/{id}/            : 주문 상세
    - POST /api/orders/create_order/   : 장바구니 기반 주문 생성
    - POST /api/orders/{id}/cancel/    : 주문 취소
    - POST /api/orders/{id}/confirm_delivery/ : 배송 완료 확인
    """

    serializer_class = OrderSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """현재 로그인한 사용자의 주문만 조회"""
        return (
            Order.objects.filter(user=self.request.user)
            .prefetch_related("items", "items__product", "items__seller", "shipments", "payments")
            .order_by("-created_at")
        )

    # ------------------------------------------------------------------
    # 주문 생성
    # ------------------------------------------------------------------

    @transaction.atomic
    @action(detail=False, methods=["post"])
    def create_order(self, request):
        """장바구니에서 주문 생성 (MVP)

        1) 재고 확인 및 차감 (동시성 제어)
        2) Order 생성
        3) OrderItem 생성 (Cart 기반)
        4) Shipment 생성 (배송 정보)
        5) Payment 생성 (모의 결제)
        6) Cart 항목 삭제
        """

        serializer = OrderCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        cart_items = serializer.validated_data["cart_items"]
        recipient_name = serializer.validated_data["recipient_name"]
        recipient_phone = serializer.validated_data["recipient_phone"]
        shipping_address = serializer.validated_data["shipping_address"]
        shipping_memo = serializer.validated_data.get("shipping_memo", "")
        payment_method_type = serializer.validated_data.get("payment_method_type", "card")

        # 1) 재고 확인 및 차감 (select_for_update로 동시성 제어)
        # 상품별 총 주문 수량 집계 (중복 상품 처리)
        product_quantity_map = {}
        for cart_item in cart_items:
            pid = cart_item.product_id
            product_quantity_map[pid] = product_quantity_map.get(pid, 0) + cart_item.quantity

        product_ids = list(product_quantity_map.keys())
        inventories = {
            inv.product_id: inv
            for inv in ProductInventory.objects.filter(
                product_id__in=product_ids
            ).select_for_update()
        }

        # 재고 부족 체크 (집계된 수량 기준)
        # - inventory가 없으면 재고 무제한으로 간주
        # - is_unlimited=True이면 재고 체크 스킵 (크롤링 상품 등)
        inventory_deducted = False
        for pid, total_qty in product_quantity_map.items():
            inventory = inventories.get(pid)
            if inventory and not inventory.is_unlimited and inventory.stock_quantity < total_qty:
                product_name = next(
                    (item.product.name for item in cart_items if item.product_id == pid), "상품"
                )
                return Response(
                    {"error": f"'{product_name}' 상품의 재고가 부족합니다. (현재 재고: {inventory.stock_quantity}개, 요청 수량: {total_qty}개)"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # 재고 차감 (집계된 수량 기준)
        # - is_unlimited=True인 상품은 재고 차감하지 않음
        for pid, total_qty in product_quantity_map.items():
            inventory = inventories.get(pid)
            if inventory and not inventory.is_unlimited:
                ProductInventory.objects.filter(product_id=pid).update(
                    stock_quantity=F("stock_quantity") - total_qty
                )
                inventory_deducted = True

        # 금액 계산
        subtotal = sum(item.product.price * item.quantity for item in cart_items)
        shipping_fee = 3000 if subtotal < 30000 else 0
        discount_amount = 0
        total_amount = subtotal + shipping_fee - discount_amount

        # 2) 주문 헤더 생성
        order = Order.objects.create(
            user=request.user,
            status=OrderStatus.PENDING,
            inventory_deducted=inventory_deducted,
        )

        # 3) 주문 상품 항목 생성 (판매자 스냅샷 포함)
        for cart_item in cart_items:
            product = cart_item.product
            # 판매자 정보 스냅샷 (주문 시점 정보 보존)
            seller = getattr(product, 'seller', None)
            seller_name = seller.brand_name if seller else None
            OrderItem.objects.create(
                order=order,
                product=product,
                product_name_snapshot=product.name,
                unit_price_snapshot=product.price,
                seller=seller,
                seller_name_snapshot=seller_name,
                quantity=cart_item.quantity,
                discount_amount=0,
                status=OrderItemStatus.PENDING,
            )

        # 4) 배송 정보 생성 (단일 Shipment 기준)
        Shipment.objects.create(
            order=order,
            recipient_name=recipient_name,
            recipient_phone=recipient_phone,
            address_full=shipping_address,
            shipping_memo=shipping_memo,
            shipping_fee=shipping_fee,
        )

        # 5) 결제 정보 생성 (모의 결제: 성공 처리)
        Payment.objects.create(
            order=order,
            method_type=payment_method_type or PaymentMethodType.CARD,
            amount=total_amount,
            status=PaymentStatus.SUCCESS,
            is_simulation=True,
            processed_at=timezone.now(),
        )

        # 주문 상태 갱신
        order.status = OrderStatus.PAID
        order.save(update_fields=["status", "updated_at"])

        # 6) 장바구니 항목 삭제
        Cart.objects.filter(id__in=[item.id for item in cart_items]).delete()

        # 7) 통계 업데이트: 주문 완료 시 order_event_count 증가
        for cart_item in cart_items:
            product = cart_item.product

            # 전체 상품 통계 (ProductStats)
            ProductStats.objects.filter(product_id=product.id).update(
                order_event_count=F('order_event_count') + 1
            )

            # 사용자별 상품 통계 (UserProductStats) - 로그인 사용자인 경우
            if request.user.is_authenticated:
                rows_updated = UserProductStats.objects.filter(
                    user=request.user,
                    product=product
                ).update(
                    order_event_count=F('order_event_count') + 1,
                    last_interacted_at=timezone.now()
                )

                # 기존 레코드가 없으면 생성
                if rows_updated == 0:
                    UserProductStats.objects.create(
                        user=request.user,
                        product=product,
                        order_event_count=1
                    )

        response_serializer = OrderSerializer(order)
        return Response(
            {
                "message": "주문이 생성되었습니다.",
                "order": response_serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )

    # ------------------------------------------------------------------
    # 주문 취소
    # ------------------------------------------------------------------

    @transaction.atomic
    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """주문 취소

        - 가능한 상태: pending, paid, processing
        - 결제 상태가 success 인 경우 Payment.status 를 cancelled 로 변경
        - 재고 복원 처리
        """

        order: Order = self.get_object()

        if order.status not in [OrderStatus.PENDING, OrderStatus.PAID, OrderStatus.PROCESSING]:
            return Response(
                {"error": "해당 주문은 취소할 수 없습니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = OrderCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # 재고 복원 (재고 차감된 주문만 복원)
        if order.inventory_deducted:
            for order_item in order.items.all():
                ProductInventory.objects.filter(product_id=order_item.product_id).update(
                    stock_quantity=F("stock_quantity") + order_item.quantity
                )

        # 주문 상태 갱신
        order.status = OrderStatus.CANCELLED
        order.cancelled_at = timezone.now()
        order.cancel_reason = serializer.validated_data["cancel_reason"]

        # 결제 상태 갱신 (모의 결제 기준)
        payments = order.payments.all()
        refunded = False
        for payment in payments:
            if payment.status == PaymentStatus.SUCCESS:
                payment.status = PaymentStatus.CANCELLED
                payment.failure_reason = "user_cancel"
                payment.processed_at = timezone.now()
                payment.save(update_fields=["status", "failure_reason", "processed_at"])
                refunded = True

        if refunded:
            order.refunded_at = timezone.now()

        order.save(update_fields=["status", "cancelled_at", "cancel_reason", "refunded_at", "updated_at"])

        return Response(
            {
                "message": "주문이 취소되었습니다.",
                "order": OrderSerializer(order).data,
            }
        )

    # ------------------------------------------------------------------
    # 배송 완료 확인
    # ------------------------------------------------------------------

    @transaction.atomic
    @action(detail=True, methods=["post"])
    def confirm_delivery(self, request, pk=None):
        """배송 완료 확인

        - 현재는 단일 Shipment 기준으로 처리
        """

        order: Order = self.get_object()
        shipment = order.shipments.order_by("id").first()

        if not shipment:
            return Response(
                {"error": "배송 정보가 존재하지 않습니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if order.status not in [OrderStatus.PAID, OrderStatus.SHIPPED]:
            return Response(
                {"error": "배송 완료로 변경할 수 없는 주문 상태입니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        now = timezone.now()
        shipment.delivered_at = now
        shipment.save(update_fields=["delivered_at", "updated_at"])

        order.status = OrderStatus.DELIVERED
        order.save(update_fields=["status", "updated_at"])

        return Response(
            {
                "message": "배송이 완료되었습니다.",
                "order": OrderSerializer(order).data,
            }
        )


class GuestOrderViewSet(viewsets.GenericViewSet):
    """비회원 주문 ViewSet

    - POST /api/orders/guest/create_order/  : 비회원 주문 생성
    - POST /api/orders/guest/lookup/        : 비회원 주문 조회
    """

    permission_classes = [AllowAny]

    # ------------------------------------------------------------------
    # 비회원 주문 생성
    # ------------------------------------------------------------------

    @transaction.atomic
    @action(detail=False, methods=["post"])
    def create_order(self, request):
        """비회원 주문 생성

        1) 재고 확인 및 차감 (동시성 제어)
        2) Order 생성
        3) OrderItem 생성
        4) Shipment 생성 (배송 정보)
        5) Payment 생성 (모의 결제)
        """

        serializer = GuestOrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        items = serializer.validated_data["items"]
        guest_email = serializer.validated_data["guest_email"]
        guest_name = serializer.validated_data["guest_name"]
        guest_phone = serializer.validated_data["guest_phone"]
        recipient_name = serializer.validated_data["recipient_name"]
        recipient_phone = serializer.validated_data["recipient_phone"]
        shipping_address = serializer.validated_data["shipping_address"]
        shipping_memo = serializer.validated_data.get("shipping_memo", "")
        payment_method_type = serializer.validated_data.get("payment_method_type", "card")

        # 1) 재고 확인 및 차감 (select_for_update로 동시성 제어)
        # 상품별 총 주문 수량 집계 (중복 상품 처리)
        product_quantity_map = {}
        for item in items:
            pid = item["product"].id
            product_quantity_map[pid] = product_quantity_map.get(pid, 0) + item["quantity"]

        product_ids = list(product_quantity_map.keys())
        inventories = {
            inv.product_id: inv
            for inv in ProductInventory.objects.filter(
                product_id__in=product_ids
            ).select_for_update()
        }

        # 재고 부족 체크 (집계된 수량 기준)
        # - inventory가 없으면 재고 무제한으로 간주
        # - is_unlimited=True이면 재고 체크 스킵 (크롤링 상품 등)
        inventory_deducted = False
        for pid, total_qty in product_quantity_map.items():
            inventory = inventories.get(pid)
            if inventory and not inventory.is_unlimited and inventory.stock_quantity < total_qty:
                product_name = next(
                    (item["product"].name for item in items if item["product"].id == pid), "상품"
                )
                return Response(
                    {"error": f"'{product_name}' 상품의 재고가 부족합니다. (현재 재고: {inventory.stock_quantity}개, 요청 수량: {total_qty}개)"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # 재고 차감 (집계된 수량 기준)
        # - is_unlimited=True인 상품은 재고 차감하지 않음
        for pid, total_qty in product_quantity_map.items():
            inventory = inventories.get(pid)
            if inventory and not inventory.is_unlimited:
                ProductInventory.objects.filter(product_id=pid).update(
                    stock_quantity=F("stock_quantity") - total_qty
                )
                inventory_deducted = True

        # 금액 계산
        subtotal = sum(item["product"].price * item["quantity"] for item in items)
        shipping_fee = 3000 if subtotal < 30000 else 0
        discount_amount = 0
        total_amount = subtotal + shipping_fee - discount_amount

        # 2) 비회원 주문 헤더 생성
        order = Order.objects.create(
            user=None,  # 비회원
            guest_email=guest_email,
            guest_name=guest_name,
            guest_phone=guest_phone,
            status=OrderStatus.PENDING,
            inventory_deducted=inventory_deducted,
        )

        # 3) 주문 상품 항목 생성 (판매자 스냅샷 포함)
        for item in items:
            product = item["product"]
            # 판매자 정보 스냅샷 (주문 시점 정보 보존)
            seller = getattr(product, 'seller', None)
            seller_name = seller.brand_name if seller else None
            OrderItem.objects.create(
                order=order,
                product=product,
                product_name_snapshot=product.name,
                unit_price_snapshot=product.price,
                seller=seller,
                seller_name_snapshot=seller_name,
                quantity=item["quantity"],
                discount_amount=0,
                status=OrderItemStatus.PENDING,
            )

        # 4) 배송 정보 생성
        Shipment.objects.create(
            order=order,
            recipient_name=recipient_name,
            recipient_phone=recipient_phone,
            address_full=shipping_address,
            shipping_memo=shipping_memo,
            shipping_fee=shipping_fee,
        )

        # 5) 결제 정보 생성 (모의 결제: 성공 처리)
        Payment.objects.create(
            order=order,
            method_type=payment_method_type or PaymentMethodType.CARD,
            amount=total_amount,
            status=PaymentStatus.SUCCESS,
            is_simulation=True,
            processed_at=timezone.now(),
        )

        # 주문 상태 갱신
        order.status = OrderStatus.PAID
        order.save(update_fields=["status", "updated_at"])

        # 6) 통계 업데이트: 주문 완료 시 order_event_count 증가 (비회원)
        for item in items:
            product = item["product"]
            # 전체 상품 통계 (ProductStats) - 비회원도 전체 통계에는 반영
            ProductStats.objects.filter(product_id=product.id).update(
                order_event_count=F('order_event_count') + 1
            )

        response_serializer = OrderSerializer(order)
        return Response(
            {
                "message": "비회원 주문이 생성되었습니다.",
                "order": response_serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )

    # ------------------------------------------------------------------
    # 비회원 주문 조회
    # ------------------------------------------------------------------

    @action(detail=False, methods=["post"])
    def lookup(self, request):
        """비회원 주문 조회

        주문번호와 이메일로 주문 조회
        """

        serializer = GuestOrderLookupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        order_no = serializer.validated_data["order_no"]
        guest_email = serializer.validated_data["guest_email"]

        try:
            order = Order.objects.prefetch_related(
                "items", "items__product", "items__seller", "shipments", "payments"
            ).get(
                order_no=order_no,
                guest_email=guest_email,
                user__isnull=True,  # 비회원 주문만
            )
        except Order.DoesNotExist:
            return Response(
                {"error": "주문을 찾을 수 없습니다. 주문번호와 이메일을 확인해주세요."},
                status=status.HTTP_404_NOT_FOUND,
            )

        response_serializer = OrderSerializer(order)
        return Response(response_serializer.data)

