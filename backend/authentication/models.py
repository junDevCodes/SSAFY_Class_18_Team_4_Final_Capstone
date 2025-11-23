"""
# ========================= 인증 모듈 공식 가이드 =========================
# 본 모듈에서 사용하는 사용자/대기 엔터티 정의
# ============================================================================
"""

from __future__ import annotations

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class Provider(models.TextChoices):
    """인증 공급자 구분 값"""

    EMAIL = "email", _("이메일")
    GOOGLE = "google", _("구글")
    KAKAO = "kakao", _("카카오")
    NAVER = "naver", _("네이버")
    APPLE = "apple", _("애플")


class User(AbstractUser):
    """커스텀 사용자 모델 (AbstractUser 확장)

    - 이메일을 고유 필드로 사용
    - provider / provider_id 로 소셜 계정 매핑
    - 이메일 인증 상태와 인증 코드 기록
    - 프로필 이미지 및 타임존 정보 저장
    """

    ROLE_CHOICES = (
        ("guest", "비회원"),  # 방문만 한 기본 권한
        ("user", "일반회원"),  # 일반 회원가입한 유저 권한
        ("seller", "판매자"),  # 판매자 회원 권한 (게시판에 물품 등록/수정/삭제 가능)
        ("admin", "관리자"),  # 최고 관리자 권한
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="guest")

    email = models.EmailField(_("이메일 주소"), unique=True)

    provider = models.CharField(
        max_length=20,
        choices=Provider.choices,
        default=Provider.EMAIL,
        help_text="해당 계정이 마지막으로 로그인한 공급자",
    )
    provider_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="OAuth 공급자의 사용자 고유 ID",
    )

    is_email_verified = models.BooleanField(
        default=False,
        help_text="이메일 주소 인증 완료 여부",
    )
    email_verification_code = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        help_text="기존 버전 호환을 위한 이메일 인증 코드",
    )

    profile_image_url = models.URLField(
        null=True,
        blank=True,
        help_text="프로필 이미지 URL",
    )
    timezone = models.CharField(
        max_length=64,
        default="Asia/Seoul",
        help_text="사용자 타임존 (IANA 포맷)",
    )

    # 추가 프로필 정보
    phone_number = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text="전화번호 (향후 인증용)",
    )
    date_of_birth = models.DateField(
        null=True,
        blank=True,
        help_text="생년월일",
    )
    gender = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        choices=[
            ("male", "남성"),
            ("female", "여성"),
            ("other", "기타"),
            ("prefer_not_to_say", "선택 안함"),
        ],
        help_text="성별",
    )

    # 설정
    language = models.CharField(
        max_length=10,
        default="ko",
        help_text="선호 언어 (ko, en 등)",
    )
    notification_enabled = models.BooleanField(
        default=True,
        help_text="알림 수신 여부",
    )
    marketing_agreed = models.BooleanField(
        default=False,
        help_text="마케팅 정보 수신 동의",
    )

    # 소프트 삭제
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="회원 탈퇴 일시 (소프트 삭제)",
    )

    class Meta:
        verbose_name = "사용자"
        verbose_name_plural = "사용자들"
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "provider_id"],
                name="uq_user_provider_provider_id",
            )
        ]
        indexes = [
            models.Index(fields=["email"], name="ix_user_email"),
            models.Index(fields=["provider", "provider_id"], name="ix_user_provider_pair"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.username or self.email}"


class PendingRegistration(models.Model):
    """인증 대기 중인 가입 정보를 저장"""

    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150, blank=True)
    password_hash = models.CharField(max_length=128)
    verification_code = models.CharField(max_length=64)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "가입 대기"
        verbose_name_plural = "가입 대기"
        indexes = [
            models.Index(fields=["expires_at"], name="ix_pending_expires_at"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.email} (대기)"


class UserAddress(models.Model):
    """사용자 배송지 정보"""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="addresses",
        help_text="배송지 소유자",
    )

    # 배송지 정보
    name = models.CharField(
        max_length=100,
        help_text="배송지명 (예: 집, 회사)",
    )
    recipient_name = models.CharField(
        max_length=100,
        help_text="수령인 이름",
    )
    recipient_phone = models.CharField(
        max_length=20,
        help_text="수령인 전화번호",
    )

    # 주소
    postal_code = models.CharField(
        max_length=10,
        help_text="우편번호",
    )
    address_line1 = models.CharField(
        max_length=255,
        help_text="기본 주소",
    )
    address_line2 = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="상세 주소",
    )
    city = models.CharField(
        max_length=100,
        help_text="시/도",
    )
    state = models.CharField(
        max_length=100,
        help_text="구/군",
    )
    country = models.CharField(
        max_length=2,
        default="KR",
        help_text="국가 코드 (ISO 3166-1 alpha-2)",
    )

    # 위치 정보 (향후 거리 기반 추천용)
    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=8,
        null=True,
        blank=True,
        help_text="위도",
    )
    longitude = models.DecimalField(
        max_digits=11,
        decimal_places=8,
        null=True,
        blank=True,
        help_text="경도",
    )

    # 설정
    is_default = models.BooleanField(
        default=False,
        help_text="기본 배송지 여부",
    )

    # 메타데이터
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_addresses"
        verbose_name = "배송지"
        verbose_name_plural = "배송지"
        indexes = [
            models.Index(fields=["user", "is_default"], name="ix_user_addr_user_default"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.user.username} - {self.name}"

    def save(self, *args, **kwargs):
        # is_default=True일 때 다른 주소의 is_default를 False로 변경
        if self.is_default:
            UserAddress.objects.filter(user=self.user).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)


class UserPaymentMethod(models.Model):
    """사용자 결제 수단 정보 (MVP: 저장만, 실제 결제 연동은 Phase 4-5)"""

    PAYMENT_TYPE_CHOICES = [
        ("credit_card", "신용카드"),
        ("debit_card", "체크카드"),
        ("bank_account", "계좌이체"),
        ("virtual_account", "가상계좌"),
        ("mobile", "간편결제"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="payment_methods",
        help_text="결제 수단 소유자",
    )

    # 결제 수단 정보
    type = models.CharField(
        max_length=20,
        choices=PAYMENT_TYPE_CHOICES,
        help_text="결제 수단 유형",
    )
    provider = models.CharField(
        max_length=50,
        help_text="결제 제공자 (kakaopay, tosspay, card 등)",
    )

    # 카드 정보 (마지막 4자리만 저장 - MVP에서는 검증 없이 저장만)
    card_number_last4 = models.CharField(
        max_length=4,
        null=True,
        blank=True,
        help_text="카드 번호 마지막 4자리",
    )
    card_issuer = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="카드 발급사",
    )
    card_type = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text="카드 종류 (credit, debit, prepaid)",
    )

    # 계좌 정보
    bank_name = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="은행명",
    )
    account_number_last4 = models.CharField(
        max_length=4,
        null=True,
        blank=True,
        help_text="계좌번호 마지막 4자리",
    )

    # PG사 토큰 (Phase 4-5에서 암호화 처리)
    payment_gateway_token = models.TextField(
        null=True,
        blank=True,
        help_text="PG사 빌링키 (나중에 암호화 필요)",
    )

    # 설정
    is_default = models.BooleanField(
        default=False,
        help_text="기본 결제 수단 여부",
    )

    # 메타데이터
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="카드 유효기간",
    )

    class Meta:
        db_table = "user_payment_methods"
        verbose_name = "결제 수단"
        verbose_name_plural = "결제 수단"
        indexes = [
            models.Index(fields=["user", "is_default"], name="ix_user_payment_user_default"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.user.username} - {self.get_type_display()}"

    def save(self, *args, **kwargs):
        # is_default=True일 때 다른 결제 수단의 is_default를 False로 변경
        if self.is_default:
            UserPaymentMethod.objects.filter(user=self.user).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)
