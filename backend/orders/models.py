"""
주문 관련 모델
"""
from django.db import models
from django.utils import timezone
import uuid


class Order(models.Model):
    """주문"""

    ORDER_STATUS_CHOICES = [
        ('pending', '주문대기'),
        ('paid', '결제완료'),
        ('processing', '처리중'),
        ('shipped', '배송중'),
        ('delivered', '배송완료'),
        ('cancelled', '취소'),
        ('refunded', '환불'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('pending', '결제대기'),
        ('paid', '결제완료'),
        ('failed', '결제실패'),
        ('refunded', '환불완료'),
        ('partially_refunded', '부분환불'),
    ]

    # 주문 번호 (ORD-20250123-xxxxxx)
    order_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="주문번호"
    )

    # 주문자
    user = models.ForeignKey(
        'authentication.User',
        on_delete=models.RESTRICT,
        related_name='orders',
        verbose_name="주문자"
    )

    # 배송 정보 (MVP: 간소화)
    recipient_name = models.CharField(max_length=100, verbose_name="받는분")
    recipient_phone = models.CharField(max_length=20, verbose_name="연락처")
    shipping_address = models.TextField(verbose_name="배송지")
    shipping_memo = models.TextField(null=True, blank=True, verbose_name="배송 메모")

    # 결제 정보 (MVP: 기본)
    payment_method_type = models.CharField(
        max_length=20,
        default='card',
        verbose_name="결제 수단"
    )

    # 금액
    subtotal = models.IntegerField(default=0, verbose_name="상품 금액")
    shipping_fee = models.IntegerField(default=0, verbose_name="배송비")
    discount_amount = models.IntegerField(default=0, verbose_name="할인 금액")
    total_amount = models.IntegerField(verbose_name="최종 결제 금액")

    # 상태
    order_status = models.CharField(
        max_length=20,
        choices=ORDER_STATUS_CHOICES,
        default='pending',
        verbose_name="주문 상태"
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending',
        verbose_name="결제 상태"
    )

    # 결제 정보 (MVP: 기본)
    payment_transaction_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="결제 트랜잭션 ID"
    )
    paid_at = models.DateTimeField(null=True, blank=True, verbose_name="결제 시각")

    # 배송 정보 (MVP: 기본)
    tracking_number = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="송장 번호"
    )
    shipped_at = models.DateTimeField(null=True, blank=True, verbose_name="배송 시각")
    delivered_at = models.DateTimeField(null=True, blank=True, verbose_name="배송 완료 시각")

    # 취소/환불
    cancelled_at = models.DateTimeField(null=True, blank=True, verbose_name="취소 시각")
    cancel_reason = models.TextField(null=True, blank=True, verbose_name="취소 사유")
    refunded_at = models.DateTimeField(null=True, blank=True, verbose_name="환불 시각")
    refund_amount = models.IntegerField(default=0, verbose_name="환불 금액")

    # 메타데이터
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일시")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일시")

    class Meta:
        db_table = 'orders'
        verbose_name = '주문'
        verbose_name_plural = '주문'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['order_number']),
            models.Index(fields=['order_status']),
            models.Index(fields=['payment_status']),
        ]

    def __str__(self):
        return f"{self.order_number} - {self.user.username}"

    def save(self, *args, **kwargs):
        """주문번호 자동 생성"""
        if not self.order_number:
            # ORD-20250123-xxxxxx 형식
            today = timezone.now().strftime('%Y%m%d')
            unique_id = str(uuid.uuid4())[:6].upper()
            self.order_number = f"ORD-{today}-{unique_id}"
        super().save(*args, **kwargs)


class OrderItem(models.Model):
    """주문 상품"""

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name="주문"
    )
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.RESTRICT,
        related_name='order_items',
        verbose_name="상품"
    )
    seller = models.ForeignKey(
        'sellers.Seller',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='order_items',
        verbose_name="판매자"
    )

    # 상품 정보 스냅샷 (주문 시점 정보 보존)
    product_name = models.CharField(max_length=500, verbose_name="상품명")
    product_image_url = models.TextField(null=True, blank=True, verbose_name="상품 이미지")

    # 수량 및 가격
    quantity = models.PositiveIntegerField(default=1, verbose_name="수량")
    unit_price = models.IntegerField(verbose_name="단가")
    discount_amount = models.IntegerField(default=0, verbose_name="할인 금액")
    total_price = models.IntegerField(verbose_name="총 가격")

    # 메타데이터
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일시")

    class Meta:
        db_table = 'order_items'
        verbose_name = '주문 상품'
        verbose_name_plural = '주문 상품'
        ordering = ['order', 'id']
        indexes = [
            models.Index(fields=['order']),
            models.Index(fields=['product']),
            models.Index(fields=['seller']),
        ]

    def __str__(self):
        return f"{self.order.order_number} - {self.product_name} x {self.quantity}"

    @property
    def subtotal(self):
        """소계"""
        return self.unit_price * self.quantity
