"""
주문 관련 모델 (ERD V2.1)
Orders & Payments 테이블 정의
"""
from django.db import models
from django.utils import timezone
import uuid


# ============================================================================
# Enums
# ============================================================================

class OrderStatus(models.TextChoices):
    """주문 상태"""
    PENDING = "pending", "주문대기"
    PAID = "paid", "결제완료"
    PROCESSING = "processing", "처리중"
    SHIPPED = "shipped", "배송중"
    DELIVERED = "delivered", "배송완료"
    CANCELLED = "cancelled", "취소"
    REFUNDED = "refunded", "환불"


class OrderItemStatus(models.TextChoices):
    """주문 품목 상태"""
    PENDING = "pending", "대기"
    PAID = "paid", "결제완료"
    SHIPPING = "shipping", "배송중"
    DELIVERED = "delivered", "배송완료"
    CANCELLED = "cancelled", "취소"
    REFUNDED = "refunded", "환불"


class PaymentStatus(models.TextChoices):
    """결제 상태"""
    PENDING = "pending", "대기"
    SUCCESS = "success", "성공"
    FAILED = "failed", "실패"
    CANCELLED = "cancelled", "취소"


class PaymentMethodType(models.TextChoices):
    """결제 수단 유형"""
    CARD = "card", "카드"
    BANK_TRANSFER = "bank_transfer", "계좌이체"
    VIRTUAL_ACCOUNT = "virtual_account", "가상계좌"
    MOBILE = "mobile", "간편결제"
    OTHER = "other", "기타"


# ============================================================================
# Group 4: Orders & Payments (ERD V2.1)
# ============================================================================

class Order(models.Model):
    """주문 헤더 (ERD: orders)

    금액/배송지/배송비/결제는 하위 테이블에서 관리.
    """

    order_no = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="주문번호",
    )
    user = models.ForeignKey(
        "authentication.User",
        on_delete=models.RESTRICT,
        related_name="orders",
        verbose_name="주문자",
        null=True,
        blank=True,
    )
    # 비회원 주문 시 사용
    guest_email = models.EmailField(
        null=True,
        blank=True,
        verbose_name="비회원 이메일",
    )
    guest_name = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="비회원 이름",
    )
    guest_phone = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name="비회원 연락처",
    )

    status = models.CharField(
        max_length=20,
        choices=OrderStatus.choices,
        default=OrderStatus.PENDING,
        verbose_name="주문 상태",
    )

    cancelled_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="취소 시각",
    )
    cancel_reason = models.TextField(
        null=True,
        blank=True,
        verbose_name="취소 사유",
    )
    refunded_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="환불 시각",
    )

    # 재고 차감 여부 (취소 시 복원 판단용)
    inventory_deducted = models.BooleanField(
        default=False,
        verbose_name="재고 차감 여부",
        help_text="주문 생성 시 재고가 차감되었는지 여부 (취소 시 복원 판단용)",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일시")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일시")

    class Meta:
        db_table = "orders"
        verbose_name = "주문"
        verbose_name_plural = "주문"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user"], name="ix_orders_user"),
            models.Index(fields=["status"], name="ix_orders_status"),
            models.Index(fields=["created_at"], name="ix_orders_created_at"),
        ]

    def __str__(self):
        if self.user:
            return f"{self.order_no} - {self.user.username}"
        return f"{self.order_no} - 비회원({self.guest_email or self.guest_name or '익명'})"

    def save(self, *args, **kwargs):
        """주문번호 자동 생성"""
        if not self.order_no:
            today = timezone.now().strftime("%Y%m%d")
            unique_id = str(uuid.uuid4())[:6].upper()
            self.order_no = f"ORD-{today}-{unique_id}"
        super().save(*args, **kwargs)


class OrderItem(models.Model):
    """주문 품목 (ERD: order_items)

    주문 시점의 상품명/단가/수량/할인만 저장.
    판매자는 products를 통해 계산.
    """

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="주문",
    )
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.RESTRICT,
        related_name="order_items",
        verbose_name="상품",
    )

    product_name_snapshot = models.CharField(
        max_length=500,
        verbose_name="상품명 스냅샷",
    )
    unit_price_snapshot = models.IntegerField(
        verbose_name="단가 스냅샷",
    )

    quantity = models.IntegerField(
        verbose_name="수량",
    )
    discount_amount = models.IntegerField(
        default=0,
        verbose_name="할인 금액",
    )

    status = models.CharField(
        max_length=20,
        choices=OrderItemStatus.choices,
        default=OrderItemStatus.PENDING,
        verbose_name="품목 상태",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일시")

    class Meta:
        db_table = "order_items"
        verbose_name = "주문 품목"
        verbose_name_plural = "주문 품목"
        ordering = ["order", "id"]
        indexes = [
            models.Index(fields=["order"], name="ix_order_items_order"),
            models.Index(fields=["product"], name="ix_order_items_product"),
        ]

    def __str__(self):
        return f"{self.order.order_no} - {self.product_name_snapshot} x {self.quantity}"

    @property
    def subtotal(self):
        """소계"""
        return self.unit_price_snapshot * self.quantity


class Shipment(models.Model):
    """배송 단위 (ERD: shipments)

    한 주문에 여러 배송(부분배송) 가능하며,
    배송지/배송비/송장은 여기서만 관리.
    """

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="shipments",
        verbose_name="주문",
    )

    recipient_name = models.CharField(
        max_length=100,
        verbose_name="수령인 이름",
    )
    recipient_phone = models.CharField(
        max_length=20,
        verbose_name="수령인 전화번호",
    )
    address_full = models.CharField(
        max_length=500,
        verbose_name="전체 주소",
    )
    shipping_memo = models.TextField(
        null=True,
        blank=True,
        verbose_name="배송 메모",
    )

    courier = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="택배사",
    )
    tracking_no = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="송장 번호",
    )

    shipping_fee = models.IntegerField(
        default=0,
        verbose_name="배송비",
    )

    shipped_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="출하 시각",
    )
    delivered_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="배송완료 시각",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일시")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일시")

    class Meta:
        db_table = "shipments"
        verbose_name = "배송"
        verbose_name_plural = "배송"
        indexes = [
            models.Index(fields=["order"], name="ix_shipments_order"),
            models.Index(fields=["tracking_no"], name="ix_shipments_tracking_no"),
        ]

    def __str__(self):
        return f"{self.order.order_no} 배송 - {self.recipient_name}"


class Payment(models.Model):
    """결제 트랜잭션 (ERD: payments)

    현재는 모의 결제, 추후 PG 연동 시 그대로 사용.
    """

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="payments",
        verbose_name="주문",
    )

    method_type = models.CharField(
        max_length=20,
        choices=PaymentMethodType.choices,
        default=PaymentMethodType.CARD,
        verbose_name="결제 수단",
    )

    amount = models.IntegerField(
        verbose_name="결제 금액",
    )
    status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        verbose_name="결제 상태",
    )

    is_simulation = models.BooleanField(
        default=True,
        verbose_name="시뮬레이션 여부",
    )
    simulation_note = models.TextField(
        null=True,
        blank=True,
        verbose_name="시뮬레이션 메모",
    )

    pg_provider = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="PG사",
    )
    pg_tid = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        unique=True,
        verbose_name="PG 트랜잭션 ID",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일시")
    processed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="처리 시각",
    )
    failure_reason = models.TextField(
        null=True,
        blank=True,
        verbose_name="실패 사유",
    )

    class Meta:
        db_table = "payments"
        verbose_name = "결제"
        verbose_name_plural = "결제"
        indexes = [
            models.Index(fields=["order"], name="ix_payments_order"),
            models.Index(fields=["status"], name="ix_payments_status"),
        ]

    def __str__(self):
        return f"{self.order.order_no} 결제 - {self.get_method_type_display()} {self.amount}원"
