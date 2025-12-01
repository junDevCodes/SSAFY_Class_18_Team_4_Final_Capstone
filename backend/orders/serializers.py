"""
주문 관련 Serializer
"""
from rest_framework import serializers
from .models import Order, OrderItem
from products.serializers import ProductListSerializer


class OrderItemSerializer(serializers.ModelSerializer):
    """주문 상품 Serializer"""

    product = ProductListSerializer(read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            'id',
            'product',
            'product_name',
            'product_image_url',
            'quantity',
            'unit_price',
            'discount_amount',
            'total_price',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class OrderSerializer(serializers.ModelSerializer):
    """주문 Serializer"""

    items = OrderItemSerializer(many=True, read_only=True)
    order_status_display = serializers.CharField(source='get_order_status_display', read_only=True)
    payment_status_display = serializers.CharField(source='get_payment_status_display', read_only=True)

    class Meta:
        model = Order
        fields = [
            'id',
            'order_number',
            'user',
            'recipient_name',
            'recipient_phone',
            'shipping_address',
            'shipping_memo',
            'payment_method_type',
            'subtotal',
            'shipping_fee',
            'discount_amount',
            'total_amount',
            'order_status',
            'order_status_display',
            'payment_status',
            'payment_status_display',
            'payment_transaction_id',
            'paid_at',
            'tracking_number',
            'shipped_at',
            'delivered_at',
            'cancelled_at',
            'cancel_reason',
            'refunded_at',
            'refund_amount',
            'items',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id', 'order_number', 'user', 'subtotal', 'total_amount',
            'payment_transaction_id', 'paid_at', 'items',
            'created_at', 'updated_at'
        ]


class OrderCreateSerializer(serializers.Serializer):
    """주문 생성 Serializer (장바구니에서 주문)"""

    cart_item_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text="장바구니 ID 목록 (비어있으면 전체 장바구니)"
    )
    recipient_name = serializers.CharField(max_length=100)
    recipient_phone = serializers.CharField(max_length=20)
    shipping_address = serializers.CharField()
    shipping_memo = serializers.CharField(required=False, allow_blank=True)
    payment_method_type = serializers.CharField(default='card')

    def validate(self, data):
        """주문 가능 여부 검증"""
        user = self.context['request'].user
        from products.models import Cart

        # 장바구니 조회
        cart_queryset = Cart.objects.filter(user=user).select_related('product')
        cart_item_ids = data.get('cart_item_ids')

        if cart_item_ids:
            cart_queryset = cart_queryset.filter(id__in=cart_item_ids)

        cart_items = list(cart_queryset)

        if not cart_items:
            raise serializers.ValidationError('주문할 상품이 없습니다.')

        # 상품 재고 검증 (MVP: 생략)
        # 상품 상태 검증
        for item in cart_items:
            if item.product.status != 'active':
                raise serializers.ValidationError(
                    f'{item.product.name}은(는) 현재 구매할 수 없습니다.'
                )

        data['cart_items'] = cart_items
        return data


class OrderCancelSerializer(serializers.Serializer):
    """주문 취소 Serializer"""

    cancel_reason = serializers.CharField(required=True, help_text="취소 사유")
