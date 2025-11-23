"""
판매자 관련 Serializer
"""
from rest_framework import serializers
from django.utils.text import slugify
from .models import Seller, SellerOperatingHours


class SellerOperatingHoursSerializer(serializers.ModelSerializer):
    """판매자 영업시간 Serializer"""

    day_of_week_display = serializers.CharField(source='get_day_of_week_display', read_only=True)

    class Meta:
        model = SellerOperatingHours
        fields = ['id', 'day_of_week', 'day_of_week_display', 'open_time', 'close_time', 'is_open']


class SellerSerializer(serializers.ModelSerializer):
    """판매자 기본 Serializer"""

    operating_hours = SellerOperatingHoursSerializer(many=True, read_only=True)
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
            'brand_name_en',
            'brand_slug',
            'brand_description',
            'brand_logo_url',
            'brand_banner_url',
            'business_phone',
            'business_email',
            'customer_service_phone',
            'business_address',
            'min_order_amount',
            'shipping_fee',
            'free_shipping_threshold',
            'total_products',
            'total_sales',
            'total_reviews',
            'average_rating',
            'status',
            'is_verified',
            'verified_at',
            'operating_hours',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id', 'user', 'brand_slug', 'total_products', 'total_sales',
            'total_reviews', 'average_rating', 'is_verified', 'verified_at',
            'created_at', 'updated_at'
        ]


class SellerRegistrationSerializer(serializers.ModelSerializer):
    """판매자 등록 신청 Serializer"""

    class Meta:
        model = Seller
        fields = [
            'brand_name',
            'brand_name_en',
            'brand_description',
            'brand_logo_url',
            'brand_banner_url',
            'business_registration_number',
            'business_type',
            'company_name',
            'ceo_name',
            'business_phone',
            'business_email',
            'customer_service_phone',
            'business_address',
            'warehouse_address',
            'bank_name',
            'bank_account_number',
            'account_holder_name',
            'verification_document_url',
        ]

    def validate_business_registration_number(self, value):
        """사업자등록번호 중복 검증"""
        if value and Seller.objects.filter(business_registration_number=value).exists():
            raise serializers.ValidationError('이미 등록된 사업자등록번호입니다.')
        return value

    def validate_brand_name(self, value):
        """브랜드명 중복 검증"""
        if Seller.objects.filter(brand_name=value).exists():
            raise serializers.ValidationError('이미 사용 중인 브랜드명입니다.')
        return value

    def create(self, validated_data):
        """판매자 생성 (slug 자동 생성)"""
        brand_name = validated_data.get('brand_name')

        # brand_slug 자동 생성
        base_slug = slugify(brand_name, allow_unicode=True)
        slug = base_slug
        counter = 1

        while Seller.objects.filter(brand_slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        validated_data['brand_slug'] = slug
        return super().create(validated_data)


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
            'brand_name_en',
            'brand_slug',
            'brand_description',
            'brand_logo_url',
            'brand_banner_url',
            'business_phone',
            'customer_service_phone',
            'total_products',
            'total_reviews',
            'average_rating',
        ]
