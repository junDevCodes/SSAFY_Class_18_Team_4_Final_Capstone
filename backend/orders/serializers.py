"""
주문 도메인 Serializer (ERD V2.1 기준)

orders, order_items, shipments, payments 테이블 구조에 맞춰
주문 목록/상세/생성/취소에 사용되는 DTO를 정의한다.
"""

from __future__ import annotations

from decimal import Decimal

from rest_framework import serializers

from products.serializers import ProductListSerializer

from .models import Order, OrderItem, Shipment, Payment, OrderStatus, PaymentStatus


class OrderItemSerializer(serializers.ModelSerializer):
    """주문 상품 항목 Serializer (ERD: order_items)

    - product_name: product_name_snapshot 매핑
    - unit_price: unit_price_snapshot 매핑
    - total_price: unit_price * quantity 계산 필드
    - image_url: 연관 상품의 대표 이미지 (있으면)
    - seller_name: 주문 시점의 판매자명 스냅샷
    - seller_id: 판매자 ID (정산/쿼리용)
    """

    product = ProductListSerializer(read_only=True)
    product_name = serializers.CharField(source="product_name_snapshot", read_only=True)
    unit_price = serializers.IntegerField(source="unit_price_snapshot", read_only=True)
    # price: 기존 프론트 호환을 위한 alias (unit_price와 동일)
    price = serializers.IntegerField(source="unit_price_snapshot", read_only=True)
    total_price = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()
    # 판매자 정보 (스냅샷 기반)
    seller_name = serializers.CharField(source="seller_name_snapshot", read_only=True)
    seller_id = serializers.IntegerField(source="seller.id", read_only=True, allow_null=True)

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "product",
            "product_name",
            "image_url",
            "quantity",
            "price",
            "unit_price",
            "discount_amount",
            "total_price",
            "status",
            "seller_id",
            "seller_name",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def get_total_price(self, obj: OrderItem) -> int:
        return (obj.unit_price_snapshot or 0) * obj.quantity

    def get_image_url(self, obj: OrderItem) -> str | None:
        product = obj.product
        if not product:
            return None
        first_image = product.images.order_by("display_order").first()
        if first_image:
            return first_image.image_url
        return None


class ShipmentSerializer(serializers.ModelSerializer):
    """배송 정보 Serializer (ERD: shipments)"""

    class Meta:
        model = Shipment
        fields = [
            "id",
            "recipient_name",
            "recipient_phone",
            "address_full",
            "shipping_memo",
            "courier",
            "tracking_no",
            "shipping_fee",
            "shipped_at",
            "delivered_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class PaymentSerializer(serializers.ModelSerializer):
    """결제 정보 Serializer (ERD: payments)"""

    class Meta:
        model = Payment
        fields = [
            "id",
            "method_type",
            "amount",
            "status",
            "is_simulation",
            "simulation_note",
            "pg_provider",
            "pg_tid",
            "created_at",
            "processed_at",
            "failure_reason",
        ]
        read_only_fields = ["id", "created_at", "processed_at"]


class OrderSerializer(serializers.ModelSerializer):
    """주문 Serializer (목록/상세 공용)

    ERD 구조:
      - Order: 주문 헤더(식별자/상태)
      - OrderItem: 주문 상품 스냅샷
      - Shipment: 배송 정보
      - Payment: 결제 정보

    추가로 금액 관련 집계 필드(subtotal, total_amount 등)를 계산해 제공한다.
    """

    items = OrderItemSerializer(many=True, read_only=True)
    # 단일 배송/결제만 사용하는 MVP 구현 (여러 건을 지원할 수 있도록 리스트로 확장 가능)
    shipment = serializers.SerializerMethodField()
    payment = serializers.SerializerMethodField()

    status_display = serializers.CharField(source="get_status_display", read_only=True)

    subtotal = serializers.SerializerMethodField()
    shipping_fee = serializers.SerializerMethodField()
    discount_amount = serializers.SerializerMethodField()
    total_amount = serializers.SerializerMethodField()

    payment_status = serializers.SerializerMethodField()
    payment_status_display = serializers.SerializerMethodField()
    paid_at = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id",
            "order_no",
            "user",
            "status",
            "status_display",
            "subtotal",
            "shipping_fee",
            "discount_amount",
            "total_amount",
            "cancelled_at",
            "cancel_reason",
            "refunded_at",
            "created_at",
            "updated_at",
            "items",
            "shipment",
            "payment",
            "payment_status",
            "payment_status_display",
            "paid_at",
        ]
        read_only_fields = [
            "id",
            "order_no",
            "user",
            "status",
            "status_display",
            "subtotal",
            "shipping_fee",
            "discount_amount",
            "total_amount",
            "cancelled_at",
            "cancel_reason",
            "refunded_at",
            "created_at",
            "updated_at",
            "payment_status",
            "payment_status_display",
            "paid_at",
        ]

    # ----- nested helper -----

    def _get_first_shipment(self, obj: Order) -> Shipment | None:
        return obj.shipments.order_by("id").first()

    def _get_first_payment(self, obj: Order) -> Payment | None:
        return obj.payments.order_by("id").first()

    # ----- SerializerMethodField 구현 -----

    def get_shipment(self, obj: Order):
        shipment = self._get_first_shipment(obj)
        if not shipment:
            return None
        return ShipmentSerializer(shipment).data

    def get_payment(self, obj: Order):
        payment = self._get_first_payment(obj)
        if not payment:
            return None
        return PaymentSerializer(payment).data

    def get_subtotal(self, obj: Order) -> int:
        total = 0
        for item in obj.items.all():
            total += (item.unit_price_snapshot or 0) * item.quantity
        return total

    def get_shipping_fee(self, obj: Order) -> int:
        shipment = self._get_first_shipment(obj)
        if not shipment:
            return 0
        return shipment.shipping_fee

    def get_discount_amount(self, obj: Order) -> int:
        # 현재는 OrderItem.discount_amount 합산 기준 (쿠폰/프로모션 확장 가능)
        return sum(item.discount_amount for item in obj.items.all())

    def get_total_amount(self, obj: Order) -> int:
        subtotal = self.get_subtotal(obj)
        shipping_fee = self.get_shipping_fee(obj)
        discount_amount = self.get_discount_amount(obj)
        return subtotal + shipping_fee - discount_amount

    def get_payment_status(self, obj: Order) -> str | None:
        payment = self._get_first_payment(obj)
        if not payment:
            return None
        return payment.status

    def get_payment_status_display(self, obj: Order) -> str | None:
        payment = self._get_first_payment(obj)
        if not payment:
            return None
        return payment.get_status_display()

    def get_paid_at(self, obj: Order):
        payment = self._get_first_payment(obj)
        if not payment:
            return None
        if payment.status == PaymentStatus.SUCCESS and payment.processed_at:
            return payment.processed_at
        return None


class OrderCreateSerializer(serializers.Serializer):
    """주문 생성 Serializer (카트 기반)

    - cart_item_ids: 선택된 장바구니 항목 ID 목록 (없으면 전체)
    - recipient_name / recipient_phone / shipping_address / shipping_memo: 배송 정보
    - payment_method_type: 결제 수단 (card / bank_transfer 등)
    """

    cart_item_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text="장바구니 ID 목록 (비어 있으면 전체 장바구니)",
    )
    recipient_name = serializers.CharField(max_length=100)
    recipient_phone = serializers.CharField(max_length=20)
    shipping_address = serializers.CharField()
    shipping_memo = serializers.CharField(required=False, allow_blank=True)
    payment_method_type = serializers.CharField(default="card")

    def validate(self, data):
        """주문 가능 여부 검증"""
        user = self.context["request"].user
        from products.models import Cart

        cart_queryset = Cart.objects.filter(user=user).select_related("product")
        cart_item_ids = data.get("cart_item_ids")

        if cart_item_ids:
            cart_queryset = cart_queryset.filter(id__in=cart_item_ids)

        cart_items = list(cart_queryset)
        if not cart_items:
            raise serializers.ValidationError("주문할 상품이 없습니다.")

        # 상품 상태 검증 (MVP: 재고 검증은 생략)
        for item in cart_items:
            if item.product.status != "active":
                raise serializers.ValidationError(f"{item.product.name}은(는) 현재 구매할 수 없습니다.")

        data["cart_items"] = cart_items
        return data


class OrderCancelSerializer(serializers.Serializer):
    """주문 취소 Serializer"""

    cancel_reason = serializers.CharField(required=True, help_text="취소 사유")


class GuestOrderCreateSerializer(serializers.Serializer):
    """비회원 주문 생성 Serializer

    비회원 주문을 위한 상품 정보와 배송 정보를 받는다.
    장바구니가 아닌 직접 상품 정보를 전달받는다.
    """

    # 상품 목록 (로컬 장바구니에서 전달)
    items = serializers.ListField(
        child=serializers.DictField(),
        required=True,
        help_text="주문 상품 목록 [{product_id, quantity}, ...]",
    )

    # 비회원 정보
    guest_email = serializers.EmailField(required=True, help_text="비회원 이메일")
    guest_name = serializers.CharField(max_length=100, required=True, help_text="비회원 이름")
    guest_phone = serializers.CharField(max_length=20, required=True, help_text="비회원 연락처")

    # 배송 정보
    recipient_name = serializers.CharField(max_length=100, required=True)
    recipient_phone = serializers.CharField(max_length=20, required=True)
    shipping_address = serializers.CharField(required=True)
    shipping_memo = serializers.CharField(required=False, allow_blank=True)

    # 결제 정보
    payment_method_type = serializers.CharField(default="card")

    def validate_items(self, value):
        """상품 목록 검증"""
        if not value:
            raise serializers.ValidationError("주문할 상품이 없습니다.")

        from products.models import Product

        validated_items = []
        for item_data in value:
            product_id = item_data.get("product_id")
            quantity = item_data.get("quantity", 1)

            if not product_id:
                raise serializers.ValidationError("상품 ID가 필요합니다.")

            try:
                product = Product.objects.get(id=product_id)
            except Product.DoesNotExist:
                raise serializers.ValidationError(f"상품 ID {product_id}를 찾을 수 없습니다.")

            if product.status != "active":
                raise serializers.ValidationError(f"{product.name}은(는) 현재 구매할 수 없습니다.")

            if quantity < 1:
                raise serializers.ValidationError("수량은 1 이상이어야 합니다.")

            validated_items.append({
                "product": product,
                "quantity": quantity,
            })

        return validated_items


class GuestOrderLookupSerializer(serializers.Serializer):
    """비회원 주문 조회 Serializer"""

    order_no = serializers.CharField(required=True, help_text="주문번호")
    guest_email = serializers.EmailField(required=True, help_text="비회원 이메일")
