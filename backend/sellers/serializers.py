"""
판매자 관련 Serializer (ERD V2.1)
"""
from rest_framework import serializers
from django.utils.text import slugify
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

        # brand_slug 자동 생성
        base_slug = slugify(brand_name, allow_unicode=True)
        slug = base_slug
        counter = 1

        while Seller.objects.filter(brand_slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        validated_data['brand_slug'] = slug

        # Seller 생성
        seller = super().create(validated_data)

        # SellerBusiness 생성
        SellerBusiness.objects.create(seller=seller, **business_data)

        # SellerSettlement 생성 (정산 정보가 있는 경우만)
        if any(settlement_data.values()):
            SellerSettlement.objects.create(seller=seller, **settlement_data)

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
            'status',
        ]
