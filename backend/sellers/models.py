"""
판매자 관련 모델 (ERD V2.1)
Seller Domain 테이블 정의
"""
from django.db import models
from authentication.models import User


# ============================================================================
# Enums
# ============================================================================

class BusinessType(models.TextChoices):
    """사업자 유형"""
    INDIVIDUAL = "individual", "개인사업자"
    CORPORATE = "corporate", "법인사업자"
    COOPERATIVE = "cooperative", "협동조합"


class SellerStatus(models.TextChoices):
    """판매자 상태"""
    PENDING = "pending", "승인대기"
    ACTIVE = "active", "활성"
    SUSPENDED = "suspended", "정지"
    INACTIVE = "inactive", "비활성"


# ============================================================================
# Group 2: Seller Domain (ERD V2.1)
# ============================================================================

class Seller(models.Model):
    """판매자 브랜드 공개 정보 (ERD: sellers)"""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="seller_profile",
        verbose_name="사용자",
    )

    brand_name = models.CharField(
        max_length=200,
        unique=True,
        verbose_name="브랜드명",
    )
    brand_slug = models.SlugField(
        max_length=200,
        unique=True,
        verbose_name="브랜드 슬러그",
    )
    brand_logo_url = models.TextField(
        null=True,
        blank=True,
        verbose_name="브랜드 로고 URL",
    )
    brand_banner_url = models.TextField(
        null=True,
        blank=True,
        verbose_name="브랜드 배너 URL",
    )
    profile_image_url = models.TextField(
        null=True,
        blank=True,
        verbose_name="판매자 프로필 이미지 URL",
    )
    brand_description = models.TextField(
        null=True,
        blank=True,
        verbose_name="브랜드 설명",
    )

    status = models.CharField(
        max_length=20,
        choices=SellerStatus.choices,
        default=SellerStatus.PENDING,
        verbose_name="상태",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일시")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일시")

    class Meta:
        db_table = "sellers"
        verbose_name = "판매자"
        verbose_name_plural = "판매자"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user"], name="ix_sellers_user"),
            models.Index(fields=["brand_slug"], name="ix_sellers_brand_slug"),
            models.Index(fields=["status"], name="ix_sellers_status"),
        ]

    def __str__(self):
        return self.brand_name


class SellerBusiness(models.Model):
    """판매자 사업자 등록 및 인증 정보 (ERD: seller_businesses)"""

    seller = models.OneToOneField(
        Seller,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="business",
        verbose_name="판매자",
    )

    registration_number = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        unique=True,
        verbose_name="사업자등록번호",
    )
    business_type = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        choices=BusinessType.choices,
        verbose_name="사업자 유형",
    )
    company_name = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        verbose_name="회사명",
    )
    ceo_name = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="대표자명",
    )

    business_address = models.TextField(
        null=True,
        blank=True,
        verbose_name="사업장 주소",
    )
    cs_phone = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name="고객센터 전화번호",
    )

    verification_doc_url = models.TextField(
        null=True,
        blank=True,
        verbose_name="인증 서류 URL",
    )
    verified_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="인증일시",
    )

    class Meta:
        db_table = "seller_businesses"
        verbose_name = "판매자 사업자 정보"
        verbose_name_plural = "판매자 사업자 정보"

    def __str__(self):
        return f"{self.seller.brand_name} 사업자 정보"

    @property
    def is_verified(self):
        """인증 완료 여부"""
        return self.verified_at is not None


class SellerSettlement(models.Model):
    """정산 계좌 정보 (ERD: seller_settlements)"""

    seller = models.OneToOneField(
        Seller,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="settlement",
        verbose_name="판매자",
    )

    bank_name = models.CharField(
        max_length=50,
        verbose_name="은행명",
    )
    account_number = models.CharField(
        max_length=50,
        verbose_name="계좌번호",
    )
    account_holder = models.CharField(
        max_length=100,
        verbose_name="예금주",
    )

    class Meta:
        db_table = "seller_settlements"
        verbose_name = "판매자 정산 계좌"
        verbose_name_plural = "판매자 정산 계좌"

    def __str__(self):
        return f"{self.seller.brand_name} 정산 계좌"


class SellerSchedule(models.Model):
    """영업 요일/시간 및 휴무일 (ERD: seller_schedules)"""

    DAY_OF_WEEK_CHOICES = [
        (0, "월요일"),
        (1, "화요일"),
        (2, "수요일"),
        (3, "목요일"),
        (4, "금요일"),
        (5, "토요일"),
        (6, "일요일"),
    ]

    seller = models.ForeignKey(
        Seller,
        on_delete=models.CASCADE,
        related_name="schedules",
        verbose_name="판매자",
    )
    day_of_week = models.SmallIntegerField(
        choices=DAY_OF_WEEK_CHOICES,
        verbose_name="요일",
    )
    open_time = models.TimeField(
        verbose_name="오픈 시간",
    )
    close_time = models.TimeField(
        verbose_name="마감 시간",
    )
    is_holiday = models.BooleanField(
        default=False,
        verbose_name="휴무일 여부",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일시")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일시")

    class Meta:
        db_table = "seller_schedules"
        verbose_name = "영업시간"
        verbose_name_plural = "영업시간"
        unique_together = [["seller", "day_of_week"]]
        ordering = ["seller", "day_of_week"]
        indexes = [
            models.Index(fields=["seller", "day_of_week"], name="ix_seller_schedules"),
        ]

    def __str__(self):
        return f"{self.seller.brand_name} - {self.get_day_of_week_display()}"
