"""
토스페이먼츠 웹훅 핸들러

가상계좌 입금 완료 등 비동기 이벤트를 처리합니다.
- POST /api/orders/webhooks/toss/
"""

import json
import logging

from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from products.models import Cart

from .models import (
    Payment,
    PaymentLog,
    PaymentStatus,
    PaymentLogType,
    OrderStatus,
    OrderItemStatus,
)
from .services import get_payment_gateway


logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def toss_webhook(request):
    """토스페이먼츠 웹훅 핸들러

    웹훅 이벤트:
    - PAYMENT_STATUS_CHANGED: 결제 상태 변경 (가상계좌 입금 등)

    시그니처 검증 후 이벤트를 처리합니다.
    """
    # 시그니처 검증
    signature = request.headers.get("Toss-Signature", "")
    pg = get_payment_gateway()

    if not pg.verify_webhook(request.body, signature):
        logger.warning("웹훅 시그니처 검증 실패")
        return JsonResponse({"error": "Invalid signature"}, status=401)

    # 요청 본문 파싱
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        logger.warning("웹훅 JSON 파싱 실패")
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    event_type = data.get("eventType")
    logger.info(f"토스 웹훅 수신: {event_type}")

    # 이벤트 타입별 처리
    if event_type == "PAYMENT_STATUS_CHANGED":
        return handle_payment_status_changed(data)
    else:
        logger.info(f"처리하지 않는 이벤트 타입: {event_type}")
        return JsonResponse({"status": "ignored"})


@transaction.atomic
def handle_payment_status_changed(data: dict):
    """결제 상태 변경 이벤트 처리

    주로 가상계좌 입금 완료 시 호출됩니다.
    """
    payment_data = data.get("data", {})
    payment_key = payment_data.get("paymentKey")
    new_status = payment_data.get("status")

    if not payment_key:
        logger.warning("paymentKey 없음")
        return JsonResponse({"error": "Missing paymentKey"}, status=400)

    # Payment 조회
    try:
        payment = Payment.objects.select_for_update().get(pg_tid=payment_key)
    except Payment.DoesNotExist:
        logger.warning(f"결제 정보 없음: {payment_key}")
        return JsonResponse({"error": "Payment not found"}, status=404)

    order = payment.order

    # 로그 기록
    PaymentLog.objects.create(
        payment=payment,
        log_type=PaymentLogType.WEBHOOK,
        request_data=data,
    )

    # 상태별 처리
    if new_status == "DONE":
        # 결제 완료 (가상계좌 입금 완료)
        if payment.status == PaymentStatus.PENDING:
            payment.status = PaymentStatus.SUCCESS
            payment.processed_at = timezone.now()
            payment.save()

            # 주문 상태 업데이트
            order.status = OrderStatus.PAID
            order.save(update_fields=["status", "updated_at"])

            # 품목 상태 업데이트
            order.items.update(status=OrderItemStatus.PAID)

            # 장바구니 삭제
            if order.user:
                Cart.objects.filter(user=order.user).delete()

            logger.info(f"가상계좌 입금 완료: {order.order_no}")

    elif new_status == "CANCELED":
        # 결제 취소됨
        if payment.status not in [PaymentStatus.CANCELLED, PaymentStatus.FAILED]:
            payment.status = PaymentStatus.CANCELLED
            payment.refunded_at = timezone.now()
            payment.save()

            # 주문 상태 업데이트
            order.status = OrderStatus.CANCELLED
            order.cancelled_at = timezone.now()
            order.save(update_fields=["status", "cancelled_at", "updated_at"])

            logger.info(f"결제 취소됨: {order.order_no}")

    elif new_status == "PARTIAL_CANCELED":
        # 부분 취소 (현재 미지원, 로그만 기록)
        logger.info(f"부분 취소: {order.order_no}")

    elif new_status == "ABORTED":
        # 결제 중단
        if payment.status == PaymentStatus.PENDING:
            payment.status = PaymentStatus.FAILED
            payment.failure_reason = "결제 중단됨"
            payment.save()

            logger.info(f"결제 중단: {order.order_no}")

    elif new_status == "EXPIRED":
        # 가상계좌 입금 기한 만료
        if payment.status == PaymentStatus.PENDING:
            payment.status = PaymentStatus.FAILED
            payment.failure_reason = "입금 기한 만료"
            payment.save()

            # 주문 취소
            order.status = OrderStatus.CANCELLED
            order.cancelled_at = timezone.now()
            order.cancel_reason = "가상계좌 입금 기한 만료"
            order.save()

            # 재고 복원
            if order.inventory_deducted:
                from django.db.models import F
                from products.models import ProductInventory

                for order_item in order.items.all():
                    ProductInventory.objects.filter(product_id=order_item.product_id).update(
                        stock_quantity=F("stock_quantity") + order_item.quantity
                    )
                order.inventory_deducted = False
                order.save(update_fields=["inventory_deducted"])

            logger.info(f"가상계좌 입금 기한 만료: {order.order_no}")

    return JsonResponse({"status": "ok"})
