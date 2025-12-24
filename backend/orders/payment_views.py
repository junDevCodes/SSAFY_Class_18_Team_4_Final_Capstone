"""
결제 ViewSet (토스페이먼츠 PG 연동)

- POST /api/orders/payments/prepare/     : 결제 준비 (주문 생성 + PG 초기화)
- POST /api/orders/payments/confirm/     : 결제 승인 (PG 콜백 후)
- POST /api/orders/payments/{id}/cancel/ : 결제 취소
- GET  /api/orders/payments/{id}/        : 결제 상태 조회
"""

from __future__ import annotations

import logging

from django.db import transaction
from django.db.models import F
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view

from authentication.models import UserAddress
from products.models import Cart, ProductInventory, ProductStats, UserProductStats, DailySalesStats

from .models import (
    Order,
    OrderItem,
    Shipment,
    Payment,
    PaymentLog,
    OrderStatus,
    OrderItemStatus,
    PaymentStatus,
    PaymentMethodType,
    PaymentLogType,
)
from .serializers import (
    OrderSerializer,
    PaymentSerializer,
    PaymentPrepareSerializer,
    PaymentConfirmSerializer,
    PaymentCancelSerializer,
    PaymentPrepareResponseSerializer,
    PaymentConfirmResponseSerializer,
)
from .services import get_payment_gateway
from .services.pg_factory import is_demo_mode


logger = logging.getLogger(__name__)


def get_client_ip(request) -> str:
    """클라이언트 IP 주소 추출"""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


@extend_schema_view(
    prepare=extend_schema(
        tags=["결제"],
        summary="결제 준비",
        description="""장바구니 기반으로 주문을 생성하고 PG 초기화 데이터를 반환합니다.

### 처리 순서
1. 재고 확인 및 차감 (동시성 제어)
2. Order, OrderItem, Shipment 생성
3. Payment 생성 (status=PENDING)
4. PG 초기화 데이터 생성

### 주의사항
- 결제가 완료되기 전까지 주문 상태는 PENDING입니다.
- 장바구니는 결제 승인 후 삭제됩니다.
""",
        request=PaymentPrepareSerializer,
        responses={200: PaymentPrepareResponseSerializer},
    ),
    confirm=extend_schema(
        tags=["결제"],
        summary="결제 승인",
        description="""토스페이먼츠 SDK 결제 완료 후 결제를 승인합니다.

### 처리 순서
1. Payment 조회 (pg_order_id로)
2. 금액 위변조 검증
3. PG 승인 API 호출
4. Payment/Order 상태 업데이트
5. 장바구니 삭제
""",
        request=PaymentConfirmSerializer,
        responses={200: PaymentConfirmResponseSerializer},
    ),
    cancel=extend_schema(
        tags=["결제"],
        summary="결제 취소",
        description="결제를 취소하고 주문 상태를 변경합니다.",
        request=PaymentCancelSerializer,
    ),
    retrieve=extend_schema(
        tags=["결제"],
        summary="결제 상태 조회",
        description="결제 상세 정보를 조회합니다.",
        responses={200: PaymentSerializer},
    ),
)
class PaymentViewSet(viewsets.GenericViewSet):
    """결제 ViewSet

    토스페이먼츠 PG 연동을 위한 결제 API.
    - 데모 모드: 실제 PG 연동 없이 시뮬레이션
    - 프로덕션 모드: 토스페이먼츠 API 연동
    """

    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """현재 사용자의 결제만 조회"""
        return Payment.objects.filter(order__user=self.request.user).select_related("order")

    # ------------------------------------------------------------------
    # 결제 준비 (주문 생성 + PG 초기화)
    # ------------------------------------------------------------------

    @transaction.atomic
    @action(detail=False, methods=["post"])
    def prepare(self, request):
        """결제 준비

        1) 재고 확인 및 차감
        2) Order, OrderItem, Shipment 생성
        3) Payment 생성 (PENDING)
        4) PG 초기화 데이터 반환
        """
        serializer = PaymentPrepareSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        cart_items = serializer.validated_data["cart_items"]
        recipient_name = serializer.validated_data["recipient_name"]
        recipient_phone = serializer.validated_data["recipient_phone"]
        shipping_address = serializer.validated_data["shipping_address"]
        shipping_memo = serializer.validated_data.get("shipping_memo", "")
        save_address = serializer.validated_data.get("save_address", False)
        address_name = serializer.validated_data.get("address_name", "")

        user = request.user

        # 1) 재고 확인 및 차감 (select_for_update로 동시성 제어)
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

        # 재고 부족 체크
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

        # 재고 차감
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
        total_amount = subtotal + shipping_fee

        # 2) 주문 헤더 생성
        order = Order.objects.create(
            user=user,
            status=OrderStatus.PENDING,
            inventory_deducted=inventory_deducted,
        )

        # 3) 주문 상품 항목 생성
        for cart_item in cart_items:
            product = cart_item.product
            seller = getattr(product, "seller", None)
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

        # 4) 배송 정보 생성
        Shipment.objects.create(
            order=order,
            recipient_name=recipient_name,
            recipient_phone=recipient_phone,
            address_full=shipping_address,
            shipping_memo=shipping_memo,
            shipping_fee=shipping_fee,
        )

        # 5) 새 배송지 저장 (옵션)
        if save_address and address_name:
            # 주소 파싱 (간단히 처리)
            UserAddress.objects.create(
                user=user,
                address_name=address_name,
                recipient_name=recipient_name,
                recipient_phone=recipient_phone,
                postal_code="",  # 별도 입력 필요
                address_line1=shipping_address,
                address_line2="",
                delivery_memo=shipping_memo,
                is_default=False,
            )

        # 6) PG 초기화
        pg = get_payment_gateway()

        # 주문명 생성 (상품명 외 N건)
        first_product_name = cart_items[0].product.name
        if len(cart_items) > 1:
            order_name = f"{first_product_name} 외 {len(cart_items) - 1}건"
        else:
            order_name = first_product_name

        # 주문명 길이 제한 (토스 최대 100자)
        if len(order_name) > 100:
            order_name = order_name[:97] + "..."

        prepare_result = pg.prepare_payment(
            order_no=order.order_no,
            amount=total_amount,
            order_name=order_name,
            customer_email=user.email,
            customer_name=user.username,
        )

        if not prepare_result.success:
            # PG 초기화 실패 시 롤백
            raise Exception(f"PG 초기화 실패: {prepare_result.error_message}")

        # 7) Payment 생성 (PENDING)
        payment = Payment.objects.create(
            order=order,
            method_type=PaymentMethodType.PENDING,
            amount=total_amount,
            expected_amount=total_amount,  # 위변조 방지
            pg_order_id=prepare_result.order_id,
            status=PaymentStatus.PENDING,
            is_simulation=is_demo_mode(),
            pg_provider="demo" if is_demo_mode() else "tosspayments",
        )

        # 8) 결제 로그 기록
        PaymentLog.objects.create(
            payment=payment,
            log_type=PaymentLogType.REQUEST,
            request_data={
                "order_no": order.order_no,
                "amount": total_amount,
                "order_name": order_name,
            },
            response_data=prepare_result.extra,
            ip_address=get_client_ip(request),
        )

        return Response({
            "order_id": order.id,
            "order_no": order.order_no,
            "payment_id": payment.id,
            "toss_order_id": prepare_result.order_id,
            "amount": prepare_result.amount,
            "client_key": prepare_result.client_key,
            "order_name": order_name,
            "is_demo": is_demo_mode(),
            "customer_email": user.email,
            "customer_name": user.username,
            **prepare_result.extra,
        })

    # ------------------------------------------------------------------
    # 결제 승인
    # ------------------------------------------------------------------

    @transaction.atomic
    @action(detail=False, methods=["post"])
    def confirm(self, request):
        """결제 승인

        1) Payment 조회 (pg_order_id로)
        2) 금액 위변조 검증
        3) PG 승인 API 호출
        4) Payment/Order 상태 업데이트
        5) 장바구니 삭제
        """
        serializer = PaymentConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        payment_key = serializer.validated_data["paymentKey"]
        order_id = serializer.validated_data["orderId"]
        amount = serializer.validated_data["amount"]

        # 1) Payment 조회
        try:
            payment = Payment.objects.select_for_update().get(pg_order_id=order_id)
        except Payment.DoesNotExist:
            logger.warning(f"결제 정보 없음: {order_id}")
            return Response(
                {"success": False, "error_code": "NOT_FOUND", "error_message": "결제 정보를 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND,
            )

        order = payment.order

        # 사용자 검증
        if order.user != request.user:
            return Response(
                {"success": False, "error_code": "FORBIDDEN", "error_message": "권한이 없습니다."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # 2) 금액 위변조 검증
        if payment.expected_amount != amount:
            PaymentLog.objects.create(
                payment=payment,
                log_type=PaymentLogType.ERROR,
                error_message=f"금액 불일치: 예상={payment.expected_amount}, 요청={amount}",
                ip_address=get_client_ip(request),
            )
            return Response(
                {"success": False, "error_code": "AMOUNT_MISMATCH", "error_message": "결제 금액이 일치하지 않습니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 이미 승인된 결제인지 확인
        if payment.status == PaymentStatus.SUCCESS:
            return Response({
                "success": True,
                "order_id": order.id,
                "order_no": order.order_no,
                "amount": payment.amount,
                "method": payment.method_type,
            })

        # 3) PG 승인 요청
        pg = get_payment_gateway()
        confirm_result = pg.confirm_payment(payment_key, order_id, amount)

        if confirm_result.success:
            # 4) 결제 성공 처리
            payment.status = PaymentStatus.SUCCESS
            payment.pg_tid = confirm_result.payment_key
            payment.method_type = self._map_method_type(confirm_result.method_type)
            payment.processed_at = timezone.now()
            payment.pg_raw_response = confirm_result.raw_response

            # 카드 정보 저장
            if confirm_result.card_info:
                payment.card_company = confirm_result.card_info.get("company")
                payment.card_number_masked = confirm_result.card_info.get("number")
                payment.card_installment_months = confirm_result.card_info.get("installmentPlanMonths")

            # 가상계좌 정보 저장
            if confirm_result.virtual_account_info:
                payment.virtual_account_number = confirm_result.virtual_account_info.get("accountNumber")
                payment.virtual_account_bank = confirm_result.virtual_account_info.get("bank")
                payment.virtual_account_holder = confirm_result.virtual_account_info.get("customerName")
                # 입금 기한 파싱
                due_date_str = confirm_result.virtual_account_info.get("dueDate")
                if due_date_str:
                    from django.utils.dateparse import parse_datetime
                    payment.virtual_account_due_date = parse_datetime(due_date_str)

            payment.save()

            # 주문 상태 업데이트
            # 가상계좌는 입금 대기 상태로
            if confirm_result.status == "WAITING_FOR_DEPOSIT":
                order.status = OrderStatus.PENDING
            else:
                order.status = OrderStatus.PAID
                # 품목 상태도 PAID로 업데이트
                order.items.update(status=OrderItemStatus.PAID)

            order.save(update_fields=["status", "updated_at"])

            # 5) 장바구니 삭제 (가상계좌 입금 대기가 아닌 경우)
            if confirm_result.status != "WAITING_FOR_DEPOSIT":
                Cart.objects.filter(user=request.user).delete()

                # 통계 업데이트
                self._update_order_stats(order, request.user)

            # 로그 기록
            PaymentLog.objects.create(
                payment=payment,
                log_type=PaymentLogType.CONFIRM,
                request_data={"paymentKey": payment_key, "orderId": order_id, "amount": amount},
                response_data=confirm_result.raw_response,
                ip_address=get_client_ip(request),
            )

            return Response({
                "success": True,
                "order_id": order.id,
                "order_no": order.order_no,
                "amount": confirm_result.amount,
                "method": confirm_result.method_type,
            })
        else:
            # 결제 실패
            payment.status = PaymentStatus.FAILED
            payment.failure_reason = confirm_result.error_message
            payment.save()

            # 재고 복원 (결제 실패 시)
            if order.inventory_deducted:
                self._restore_inventory(order)
                order.inventory_deducted = False
                order.save(update_fields=["inventory_deducted"])

            PaymentLog.objects.create(
                payment=payment,
                log_type=PaymentLogType.ERROR,
                error_message=f"{confirm_result.error_code}: {confirm_result.error_message}",
                ip_address=get_client_ip(request),
            )

            return Response({
                "success": False,
                "error_code": confirm_result.error_code,
                "error_message": confirm_result.error_message,
            }, status=status.HTTP_400_BAD_REQUEST)

    # ------------------------------------------------------------------
    # 결제 취소
    # ------------------------------------------------------------------

    @transaction.atomic
    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """결제 취소"""
        try:
            payment = Payment.objects.select_for_update().get(pk=pk, order__user=request.user)
        except Payment.DoesNotExist:
            return Response(
                {"error": "결제 정보를 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND,
            )

        order = payment.order

        if payment.status != PaymentStatus.SUCCESS:
            return Response(
                {"error": "취소할 수 없는 결제 상태입니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = PaymentCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cancel_reason = serializer.validated_data["cancel_reason"]

        # PG 취소 요청
        pg = get_payment_gateway()
        cancel_result = pg.cancel_payment(payment.pg_tid, cancel_reason)

        if cancel_result.success:
            # 결제 상태 업데이트
            payment.status = PaymentStatus.CANCELLED
            payment.refund_amount = payment.amount
            payment.refunded_at = timezone.now()
            payment.failure_reason = cancel_reason
            payment.save()

            # 주문 상태 업데이트
            order.status = OrderStatus.CANCELLED
            order.cancelled_at = timezone.now()
            order.cancel_reason = cancel_reason
            order.refunded_at = timezone.now()
            order.save()

            # 품목 상태 업데이트
            order.items.exclude(
                status__in=[OrderItemStatus.CANCELLED, OrderItemStatus.REFUNDED]
            ).update(status=OrderItemStatus.CANCELLED)

            # 재고 복원
            if order.inventory_deducted:
                self._restore_inventory(order)
                order.inventory_deducted = False
                order.save(update_fields=["inventory_deducted"])

            PaymentLog.objects.create(
                payment=payment,
                log_type=PaymentLogType.CANCEL,
                request_data={"cancel_reason": cancel_reason},
                ip_address=get_client_ip(request),
            )

            return Response({
                "success": True,
                "refund_amount": payment.refund_amount,
                "order": OrderSerializer(order).data,
            })
        else:
            PaymentLog.objects.create(
                payment=payment,
                log_type=PaymentLogType.ERROR,
                error_message=f"취소 실패: {cancel_result.error_code}: {cancel_result.error_message}",
                ip_address=get_client_ip(request),
            )

            return Response({
                "success": False,
                "error_code": cancel_result.error_code,
                "error_message": cancel_result.error_message,
            }, status=status.HTTP_400_BAD_REQUEST)

    # ------------------------------------------------------------------
    # 결제 상태 조회
    # ------------------------------------------------------------------

    def retrieve(self, request, pk=None):
        """결제 상태 조회"""
        try:
            payment = Payment.objects.get(pk=pk, order__user=request.user)
        except Payment.DoesNotExist:
            return Response(
                {"error": "결제 정보를 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(PaymentSerializer(payment).data)

    # ------------------------------------------------------------------
    # 헬퍼 메서드
    # ------------------------------------------------------------------

    def _map_method_type(self, method_type: str) -> str:
        """PG 결제 수단을 내부 타입으로 매핑"""
        mapping = {
            "card": PaymentMethodType.CARD,
            "virtualAccount": PaymentMethodType.VIRTUAL_ACCOUNT,
            "virtual_account": PaymentMethodType.VIRTUAL_ACCOUNT,
            "transfer": PaymentMethodType.BANK_TRANSFER,
            "bank_transfer": PaymentMethodType.BANK_TRANSFER,
            "mobilePhone": PaymentMethodType.MOBILE,
            "mobile": PaymentMethodType.MOBILE,
        }
        return mapping.get(method_type, PaymentMethodType.OTHER)

    def _restore_inventory(self, order: Order):
        """재고 복원"""
        for order_item in order.items.all():
            ProductInventory.objects.filter(product_id=order_item.product_id).update(
                stock_quantity=F("stock_quantity") + order_item.quantity
            )

    def _update_order_stats(self, order: Order, user):
        """주문 통계 업데이트"""
        today = timezone.now().date()

        for order_item in order.items.all():
            product = order_item.product

            # ProductStats 업데이트
            ProductStats.objects.filter(product_id=product.id).update(
                order_event_count=F("order_event_count") + 1
            )

            # UserProductStats 업데이트
            rows_updated = UserProductStats.objects.filter(
                user=user,
                product=product,
            ).update(
                order_event_count=F("order_event_count") + 1,
                last_interacted_at=timezone.now(),
            )

            if rows_updated == 0:
                UserProductStats.objects.create(
                    user=user,
                    product=product,
                    order_event_count=1,
                )

            # DailySalesStats 업데이트
            rows_updated = DailySalesStats.objects.filter(
                product=product,
                date=today,
            ).update(order_count=F("order_count") + 1)

            if rows_updated == 0:
                DailySalesStats.objects.create(
                    product=product,
                    date=today,
                    order_count=1,
                )
