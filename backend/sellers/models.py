"""
판매자 관련 모델
"""
from django.db import models
from django.core.validators import MinValueValidator
from authentication.models import User


class Seller(models.Model):
    """판매자 모델"""

    BUSINESS_TYPE_CHOICES = [
        ('individual', '개인사업자'),
        ('corporate', '법인사업자'),
        ('cooperative', '협동조합'),
    ]

    STATUS_CHOICES = [
        ('pending', '승인대기'),
        ('active', '활성'),
        ('suspended', '정지'),
        ('inactive', '비활성'),
    ]

    # 관계
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='seller_profile',
        verbose_name="사용자"
    )

    # 브랜드 정보
    brand_name = models.CharField(max_length=200, unique=True, verbose_name="브랜드명")
    brand_name_en = models.CharField(max_length=200, unique=True, null=True, blank=True, verbose_name="브랜드명(영문)")
    brand_slug = models.SlugField(max_length=200, unique=True, verbose_name="브랜드 슬러그")
    brand_description = models.TextField(null=True, blank=True, verbose_name="브랜드 설명")
    brand_logo_url = models.TextField(null=True, blank=True, verbose_name="브랜드 로고 URL")
    brand_banner_url = models.TextField(null=True, blank=True, verbose_name="브랜드 배너 URL")

    # 사업자 정보 (MVP: 검증 없이 저장만)
    business_registration_number = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        verbose_name="사업자등록번호"
    )
    business_type = models.CharField(
        max_length=20,
        choices=BUSINESS_TYPE_CHOICES,
        null=True,
        blank=True,
        verbose_name="사업자 유형"
    )
    company_name = models.CharField(max_length=200, null=True, blank=True, verbose_name="회사명")
    ceo_name = models.CharField(max_length=100, null=True, blank=True, verbose_name="대표자명")

    # 인증 정보 (MVP: 자동 승인)
    is_verified = models.BooleanField(default=False, verbose_name="인증 여부")
    verified_at = models.DateTimeField(null=True, blank=True, verbose_name="인증일시")
    verification_document_url = models.TextField(null=True, blank=True, verbose_name="인증 서류 URL")

    # 연락처
    business_phone = models.CharField(max_length=20, null=True, blank=True, verbose_name="사업장 전화번호")
    business_email = models.EmailField(max_length=254, null=True, blank=True, verbose_name="사업장 이메일")
    customer_service_phone = models.CharField(max_length=20, null=True, blank=True, verbose_name="고객센터 전화번호")

    # 주소
    business_address = models.TextField(null=True, blank=True, verbose_name="사업장 주소")
    warehouse_address = models.TextField(null=True, blank=True, verbose_name="창고 주소")

    # 정산 정보 (MVP: 저장만, 향후 암호화 필요)
    bank_name = models.CharField(max_length=50, null=True, blank=True, verbose_name="은행명")
    bank_account_number = models.CharField(max_length=50, null=True, blank=True, verbose_name="계좌번호")
    account_holder_name = models.CharField(max_length=100, null=True, blank=True, verbose_name="예금주명")

    # 운영 정보
    min_order_amount = models.IntegerField(default=0, verbose_name="최소 주문 금액")
    shipping_fee = models.IntegerField(default=0, verbose_name="기본 배송비")
    free_shipping_threshold = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="무료 배송 기준 금액"
    )

    # 통계 (비정규화 - 성능 최적화)
    total_products = models.IntegerField(default=0, verbose_name="총 상품 수")
    total_sales = models.IntegerField(default=0, verbose_name="총 판매액")
    total_reviews = models.IntegerField(default=0, verbose_name="총 리뷰 수")
    average_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.00,
        verbose_name="평균 평점"
    )

    # 상태
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="상태"
    )

    # 메타데이터
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일시")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일시")

    class Meta:
        db_table = 'sellers'
        verbose_name = '판매자'
        verbose_name_plural = '판매자'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['brand_slug']),
            models.Index(fields=['status']),
            models.Index(fields=['is_verified']),
        ]

    def __str__(self):
        return self.brand_name


class SellerOperatingHours(models.Model):
    """판매자 영업시간 모델"""

    DAY_OF_WEEK_CHOICES = [
        (0, '월요일'),
        (1, '화요일'),
        (2, '수요일'),
        (3, '목요일'),
        (4, '금요일'),
        (5, '토요일'),
        (6, '일요일'),
    ]

    seller = models.ForeignKey(
        Seller,
        on_delete=models.CASCADE,
        related_name='operating_hours',
        verbose_name="판매자"
    )
    day_of_week = models.SmallIntegerField(choices=DAY_OF_WEEK_CHOICES, verbose_name="요일")
    open_time = models.TimeField(verbose_name="오픈 시간")
    close_time = models.TimeField(verbose_name="마감 시간")
    is_open = models.BooleanField(default=True, verbose_name="영업 여부")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일시")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일시")

    class Meta:
        db_table = 'seller_operating_hours'
        verbose_name = '영업시간'
        verbose_name_plural = '영업시간'
        unique_together = [['seller', 'day_of_week']]
        ordering = ['seller', 'day_of_week']
        indexes = [
            models.Index(fields=['seller']),
        ]

    def __str__(self):
        return f"{self.seller.brand_name} - {self.get_day_of_week_display()}"
