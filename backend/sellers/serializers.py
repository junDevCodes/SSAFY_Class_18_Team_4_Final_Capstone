"""
판매자 관련 Serializer (ERD V2.1)
"""
import uuid
from rest_framework import serializers
from django.db import IntegrityError
from django.utils.text import slugify
from orders.models import OrderItem, OrderItemStatus
from .models import Seller, SellerBusiness, SellerSettlement, SellerSchedule


class SellerScheduleSerializer(serializers.ModelSerializer):
    """영업시간 Serializer (ERD: seller_schedules)"""

    day_of_week_display = serializers.CharField(source='get_day_of_week_display', read_only=True)

    class Meta:
        model = SellerSchedule
        fields = ['id', 'day_of_week', 'day_of_week_display', 'open_time', 'close_time', 'is_holiday']


# 하위 호환성을 위한 alias
SellerOperatingHoursSerializer = SellerScheduleSerializer


class SellerBusinessSerializer(serializers.ModelSerializer):
    """판매자 사업자 정보 Serializer (ERD: seller_businesses)"""

    is_verified = serializers.ReadOnlyField()

    class Meta:
        model = SellerBusiness
        fields = [
            'registration_number',
            'business_type',
            'company_name',
            'ceo_name',
            'business_address',
            'cs_phone',
            'verification_doc_url',
            'verified_at',
            'is_verified',
        ]


class SellerSettlementSerializer(serializers.ModelSerializer):
    """판매자 정산 계좌 Serializer (ERD: seller_settlements)"""

    class Meta:
        model = SellerSettlement
        fields = ['bank_name', 'account_number', 'account_holder']


class SellerSerializer(serializers.ModelSerializer):
    """판매자 기본 Serializer (ERD: sellers)"""

    schedules = SellerScheduleSerializer(many=True, read_only=True)
    business = SellerBusinessSerializer(read_only=True)
    settlement = SellerSettlementSerializer(read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = Seller
        fields = [
            'id',
            'user',
            'username',
            'email',
            'brand_name',
            'brand_slug',
            'brand_logo_url',
            'brand_banner_url',
            'profile_image_url',
            'brand_description',
            'status',
            'schedules',
            'business',
            'settlement',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id', 'user', 'brand_slug', 'status',
            'created_at', 'updated_at'
        ]


class SellerRegistrationSerializer(serializers.ModelSerializer):
    """판매자 등록 신청 Serializer"""

    # SellerBusiness 필드들
    registration_number = serializers.CharField(write_only=True, required=False, allow_blank=True)
    business_type = serializers.CharField(write_only=True, required=False, allow_blank=True)
    company_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    ceo_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    business_address = serializers.CharField(write_only=True, required=False, allow_blank=True)
    cs_phone = serializers.CharField(write_only=True, required=False, allow_blank=True)
    verification_doc_url = serializers.CharField(write_only=True, required=False, allow_blank=True)

    # SellerSettlement 필드들
    bank_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    account_number = serializers.CharField(write_only=True, required=False, allow_blank=True)
    account_holder = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Seller
        fields = [
            'brand_name',
            'brand_description',
            'brand_logo_url',
            # 사업자 정보
            'registration_number',
            'business_type',
            'company_name',
            'ceo_name',
            'business_address',
            'cs_phone',
            'verification_doc_url',
            # 정산 정보
            'bank_name',
            'account_number',
            'account_holder',
        ]

    def validate_brand_name(self, value):
        """브랜드명 중복 검증"""
        if Seller.objects.filter(brand_name=value).exists():
            raise serializers.ValidationError('이미 사용 중인 브랜드명입니다.')
        return value

    def create(self, validated_data):
        """판매자 생성 (slug 자동 생성, 관련 테이블 생성)"""
        # 사업자 정보 추출
        business_data = {
            'registration_number': validated_data.pop('registration_number', None),
            'business_type': validated_data.pop('business_type', None),
            'company_name': validated_data.pop('company_name', None),
            'ceo_name': validated_data.pop('ceo_name', None),
            'business_address': validated_data.pop('business_address', None),
            'cs_phone': validated_data.pop('cs_phone', None),
            'verification_doc_url': validated_data.pop('verification_doc_url', None),
        }

        # 정산 정보 추출
        settlement_data = {
            'bank_name': validated_data.pop('bank_name', None),
            'account_number': validated_data.pop('account_number', None),
            'account_holder': validated_data.pop('account_holder', None),
        }

        brand_name = validated_data.get('brand_name')

        # brand_slug 자동 생성 (race condition 방어: UUID fallback)
        base_slug = slugify(brand_name, allow_unicode=True)
        if not base_slug:
            # 브랜드명이 특수문자만 있는 경우 UUID 기반 slug 생성
            base_slug = f"seller-{uuid.uuid4().hex[:8]}"

        slug = base_slug
        counter = 1
        max_attempts = 10

        # 중복 slug 처리 (최대 10회 시도)
        while Seller.objects.filter(brand_slug=slug).exists() and counter <= max_attempts:
            slug = f"{base_slug}-{counter}"
            counter += 1

        # max_attempts 초과 시 UUID 추가로 유일성 보장
        if counter > max_attempts:
            slug = f"{base_slug}-{uuid.uuid4().hex[:8]}"

        validated_data['brand_slug'] = slug

        # Seller 생성 (IntegrityError 대비 - 동시 요청 race condition)
        try:
            seller = super().create(validated_data)
        except IntegrityError:
            # 동시 요청으로 slug 충돌 시 UUID 추가하여 재시도
            validated_data['brand_slug'] = f"{base_slug}-{uuid.uuid4().hex[:8]}"
            seller = super().create(validated_data)

        # SellerBusiness 생성
        SellerBusiness.objects.create(seller=seller, **business_data)

        # SellerSettlement 생성 (모든 정산 정보가 있는 경우에만)
        # 부분 데이터 생성 방지: 은행명, 계좌번호, 예금주 모두 필수
        settlement_values = [v for v in settlement_data.values() if v]
        if len(settlement_values) == 3:
            # 모든 필드가 입력된 경우에만 생성
            SellerSettlement.objects.create(seller=seller, **settlement_data)
        elif len(settlement_values) > 0:
            # 부분 입력 시 로그 남기고 생성하지 않음 (데이터 무결성 보호)
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(
                f"SellerSettlement 부분 데이터 무시: seller_id={seller.id}, "
                f"입력된 필드 수={len(settlement_values)}/3"
            )

        return seller


class SellerApprovalSerializer(serializers.Serializer):
    """판매자 승인/거절 Serializer"""

    action = serializers.ChoiceField(choices=['approve', 'reject'], required=True)
    reason = serializers.CharField(required=False, allow_blank=True, help_text="거절 사유")


class SellerPublicSerializer(serializers.ModelSerializer):
    """판매자 공개 정보 Serializer (일반 사용자용)"""

    class Meta:
        model = Seller
        fields = [
            'id',
            'brand_name',
            'brand_slug',
            'brand_description',
            'brand_logo_url',
            'brand_banner_url',
            'profile_image_url',
            'status',
        ]


class SellerImageUploadSerializer(serializers.Serializer):
    """판매자 이미지 업로드 Serializer

    이미지 유형:
        - profile: 판매자 프로필 이미지
        - logo: 브랜드 로고
        - banner: 브랜드 배너
    """
    image = serializers.ImageField(
        required=True,
        help_text="업로드할 이미지 파일 (JPEG, PNG, GIF, WebP)"
    )
    image_type = serializers.ChoiceField(
        choices=['profile', 'logo', 'banner'],
        required=True,
        help_text="이미지 유형: profile(프로필), logo(브랜드 로고), banner(브랜드 배너)"
    )

    def validate_image(self, value):
        """이미지 유효성 검사"""
        # 파일 형식 검사
        allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
        if value.content_type not in allowed_types:
            raise serializers.ValidationError(
                f"지원하지 않는 이미지 형식입니다: {value.content_type}. "
                f"JPEG, PNG, GIF, WebP만 지원합니다."
            )

        # 파일 크기 검사 (최대 5MB)
        max_size = 5 * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError(
                f"이미지 크기가 너무 큽니다. 최대 5MB까지 업로드 가능합니다."
            )

        return value


class SellerOrderItemSerializer(serializers.ModelSerializer):
    """판매자 주문관리용 OrderItem Serializer"""

    product_name = serializers.CharField(source="product_name_snapshot", read_only=True)
    unit_price = serializers.IntegerField(source="unit_price_snapshot", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    order_id = serializers.IntegerField(source="order.id", read_only=True)
    order_no = serializers.CharField(source="order.order_no", read_only=True)
    order_status = serializers.CharField(source="order.status", read_only=True)
    order_status_display = serializers.CharField(source="order.get_status_display", read_only=True)
    order_created_at = serializers.DateTimeField(source="order.created_at", read_only=True)
    buyer_name = serializers.SerializerMethodField()
    buyer_phone = serializers.SerializerMethodField()
    shipping_address = serializers.SerializerMethodField()
    shipping_memo = serializers.SerializerMethodField()
    courier = serializers.SerializerMethodField()
    tracking_no = serializers.SerializerMethodField()
    product_image = serializers.SerializerMethodField()
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "order_id",
            "order_no",
            "order_status",
            "order_status_display",
            "order_created_at",
            "product_name",
            "product_image",
            "quantity",
            "unit_price",
            "discount_amount",
            "total_price",
            "status",
            "status_display",
            "buyer_name",
            "buyer_phone",
            "shipping_address",
            "shipping_memo",
            "courier",
            "tracking_no",
        ]
        read_only_fields = fields

    def _get_shipment(self, obj):
        return obj.order.shipments.order_by("id").first()

    def get_product_image(self, obj):
        product = obj.product
        if not product:
            return None
        image = product.images.order_by("display_order").first()
        return image.image_url if image else None

    def get_total_price(self, obj):
        return (obj.unit_price_snapshot or 0) * obj.quantity - (obj.discount_amount or 0)

    def get_buyer_name(self, obj):
        shipment = self._get_shipment(obj)
        if shipment and shipment.recipient_name:
            return shipment.recipient_name
        order = obj.order
        return getattr(order.user, "username", None) or order.guest_name

    def get_buyer_phone(self, obj):
        shipment = self._get_shipment(obj)
        if shipment and shipment.recipient_phone:
            return shipment.recipient_phone
        order = obj.order
        return getattr(order.user, "phone_number", None) or order.guest_phone

    def get_shipping_address(self, obj):
        shipment = self._get_shipment(obj)
        return shipment.address_full if shipment else None

    def get_shipping_memo(self, obj):
        shipment = self._get_shipment(obj)
        return shipment.shipping_memo if shipment else None

    def get_courier(self, obj):
        shipment = self._get_shipment(obj)
        return shipment.courier if shipment else None

    def get_tracking_no(self, obj):
        shipment = self._get_shipment(obj)
        return shipment.tracking_no if shipment else None


class SellerOrderItemStatusUpdateSerializer(serializers.Serializer):
    """판매자 주문항목 상태 업데이트 요청 Serializer"""

    allowed_statuses = [
        OrderItemStatus.PENDING,
        OrderItemStatus.PAID,
        OrderItemStatus.SHIPPING,
        OrderItemStatus.DELIVERED,
    ]
    status = serializers.ChoiceField(choices=allowed_statuses)
