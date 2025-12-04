"""
인증 모듈 모델 (ERD V2.1)
Group 1: Users & Auth 테이블 정의
"""

from __future__ import annotations

from django.contrib.auth.models import AbstractUser, UserManager as DjangoUserManager
from django.contrib.auth.hashers import is_password_usable
from django.db import models
from django.utils.translation import gettext_lazy as _


# ============================================================================
# Enums (ERD V2.1)
# ============================================================================

class UserRole(models.TextChoices):
    """사용자 역할 (user_role enum)"""
    GUEST = "guest", _("비회원")
    USER = "user", _("일반회원")
    SELLER = "seller", _("판매자")
    ADMIN = "admin", _("관리자")


class GenderType(models.TextChoices):
    """성별 타입 (gender_type enum)"""
    MALE = "male", _("남성")
    FEMALE = "female", _("여성")
    OTHER = "other", _("기타")
    PREFER_NOT_TO_SAY = "prefer_not_to_say", _("선택 안함")


# 하위 호환성을 위한 Provider enum (ERD V2.1에는 없지만 기존 코드 호환용)
class Provider(models.TextChoices):
    """인증 공급자 (하위 호환성)"""
    EMAIL = "email", _("이메일")
    GOOGLE = "google", _("구글")
    KAKAO = "kakao", _("카카오")


class UserManager(DjangoUserManager):
    """커스텀 UserManager (ERD V2.1 비밀번호 분리)

    - 실제 비밀번호 해시는 AuthEmailCredential.password_hash 에만 저장
    - users.password 필드는 항상 unusable password 로 유지
    """

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("이메일은 필수입니다.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        # User.password 는 항상 unusable 로 유지
        user.set_unusable_password()
        user.save(using=self._db)

        # 비밀번호가 제공된 경우 AuthEmailCredential 에만 해시 저장
        if password:
            from django.apps import apps
            from django.contrib.auth.hashers import make_password

            AuthEmailCredential = apps.get_model("authentication", "AuthEmailCredential")
            AuthEmailCredential.objects.create(
                user=user,
                password_hash=make_password(password),
                is_email_verified=True,
            )
        return user

    def create_user(self, email=None, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        extra_fields.setdefault("role", UserRole.USER)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email=None, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", UserRole.ADMIN)

        if password is None:
            raise ValueError("슈퍼유저 비밀번호는 필수입니다.")

        return self._create_user(email, password, **extra_fields)


# ============================================================================
# Group 1: Users & Auth (ERD V2.1)
# ============================================================================

class User(AbstractUser):
    """사용자 모델 (ERD: users)

    JWT 기반 계정. 휴면 계정은 last_login 기준으로 식별하고,
    토큰은 DB에 저장하지 않음.
    """

    # ERD 필드
    email = models.EmailField(
        _("이메일"),
        max_length=254,
        unique=True,
    )
    username = models.CharField(
        _("사용자명"),
        max_length=150,
        unique=True,
    )
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.GUEST,
        verbose_name="역할",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="활성 상태",
    )
    # last_login: AbstractUser에서 제공
    # created_at: date_joined으로 대체 (AbstractUser)
    # updated_at: auto_now로 추가
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="탈퇴 일시",
    )

    # AbstractUser의 불필요한 필드 제거
    first_name = None
    last_name = None

    # 커스텀 매니저 (비밀번호 분리)
    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    class Meta:
        db_table = "users"
        verbose_name = "사용자"
        verbose_name_plural = "사용자"
        indexes = [
            models.Index(fields=["email"], name="ix_users_email"),
            models.Index(fields=["role"], name="ix_users_role"),
            models.Index(fields=["date_joined"], name="ix_users_created_at"),
        ]

    def __str__(self) -> str:
        return f"{self.username} ({self.email})"

    def save(self, *args, **kwargs):
        """저장 시 항상 password 필드를 unusable 상태로 유지

        - ERD V2.1: 실제 비밀번호 해시는 AuthEmailCredential 에만 존재해야 함
        - User.password 에 사용 가능한 해시가 들어가면 즉시 unusable 로 변경
        """
        if is_password_usable(self.password):
            self.set_unusable_password()
        super().save(*args, **kwargs)


class UserProfile(models.Model):
    """사용자 프로필 (ERD: user_profiles)

    사용자 프로필 및 알림/마케팅 설정.
    """

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="profile",
        verbose_name="사용자",
    )

    profile_image_url = models.TextField(
        null=True,
        blank=True,
        verbose_name="프로필 이미지 URL",
    )
    phone_number = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        unique=True,
        verbose_name="전화번호",
    )
    date_of_birth = models.DateField(
        null=True,
        blank=True,
        verbose_name="생년월일",
    )
    gender = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        choices=GenderType.choices,
        verbose_name="성별",
    )

    timezone = models.CharField(
        max_length=64,
        default="Asia/Seoul",
        verbose_name="타임존",
    )
    language = models.CharField(
        max_length=10,
        default="ko",
        verbose_name="선호 언어",
    )
    notification_enabled = models.BooleanField(
        default=True,
        verbose_name="알림 수신 여부",
    )
    marketing_agreed = models.BooleanField(
        default=False,
        verbose_name="마케팅 수신 동의",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="수정일시",
    )

    class Meta:
        db_table = "user_profiles"
        verbose_name = "사용자 프로필"
        verbose_name_plural = "사용자 프로필"

    def __str__(self) -> str:
        return f"{self.user.username} 프로필"


class UserAddress(models.Model):
    """사용자 배송지 주소록 (ERD: user_addresses)"""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="addresses",
        verbose_name="사용자",
    )

    address_name = models.CharField(
        max_length=100,
        verbose_name="배송지명",
    )
    recipient_name = models.CharField(
        max_length=100,
        verbose_name="수령인 이름",
    )
    recipient_phone = models.CharField(
        max_length=20,
        verbose_name="수령인 전화번호",
    )

    postal_code = models.CharField(
        max_length=10,
        verbose_name="우편번호",
    )
    address_line1 = models.CharField(
        max_length=255,
        verbose_name="기본 주소",
    )
    address_line2 = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="상세 주소",
    )
    delivery_memo = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        verbose_name="배송 요청사항",
    )

    is_default = models.BooleanField(
        default=False,
        verbose_name="기본 배송지",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일시")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일시")

    class Meta:
        db_table = "user_addresses"
        verbose_name = "배송지"
        verbose_name_plural = "배송지"
        indexes = [
            models.Index(fields=["user"], name="ix_user_addresses_user"),
            models.Index(fields=["user", "is_default"], name="ix_user_addr_default"),
        ]

    def __str__(self) -> str:
        return f"{self.user.username} - {self.address_name}"

    def save(self, *args, **kwargs):
        if self.is_default:
            UserAddress.objects.filter(user=self.user).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)


class PendingRegistration(models.Model):
    """회원가입 이메일 인증 대기 상태 (ERD: pending_registrations)"""

    email = models.EmailField(
        max_length=254,
        unique=True,
        verbose_name="이메일",
    )
    username = models.CharField(
        max_length=150,
        verbose_name="사용자명",
    )
    password_hash = models.CharField(
        max_length=128,
        verbose_name="비밀번호 해시",
    )
    verification_code = models.CharField(
        max_length=64,
        verbose_name="인증 코드",
    )
    expires_at = models.DateTimeField(
        verbose_name="만료 시각",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일시")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일시")

    class Meta:
        db_table = "pending_registrations"
        verbose_name = "가입 대기"
        verbose_name_plural = "가입 대기"
        indexes = [
            models.Index(fields=["expires_at"], name="ix_pending_reg_expires"),
        ]

    def __str__(self) -> str:
        return f"{self.email} (대기)"


class AuthEmailCredential(models.Model):
    """이메일/비밀번호 로그인 자격 정보 (ERD: auth_email_credentials)"""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="email_credential",
        verbose_name="사용자",
    )

    password_hash = models.CharField(
        max_length=128,
        verbose_name="비밀번호 해시",
    )
    is_email_verified = models.BooleanField(
        default=False,
        verbose_name="이메일 인증 완료",
    )
    fail_count = models.IntegerField(
        default=0,
        verbose_name="로그인 실패 횟수",
    )
    last_changed_at = models.DateTimeField(
        auto_now=True,
        verbose_name="비밀번호 변경일시",
    )

    class Meta:
        db_table = "auth_email_credentials"
        verbose_name = "이메일 인증 정보"
        verbose_name_plural = "이메일 인증 정보"

    def __str__(self) -> str:
        return f"{self.user.email} 인증 정보"


class AuthGoogleAccount(models.Model):
    """Google 계정 연결 정보 (ERD: auth_google_accounts)

    Google 계정과 사용자 매핑. OAuth 토큰은 DB에 저장하지 않고 JWT 발급에만 사용.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="google_accounts",
        verbose_name="사용자",
    )

    google_user_id = models.CharField(
        max_length=255,
        unique=True,
        verbose_name="Google 사용자 ID",
    )
    email = models.EmailField(
        max_length=254,
        verbose_name="Google 이메일",
    )

    connected_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="연결일시",
    )

    class Meta:
        db_table = "auth_google_accounts"
        verbose_name = "Google 계정"
        verbose_name_plural = "Google 계정"
        indexes = [
            models.Index(fields=["user"], name="ix_auth_google_user"),
        ]

    def __str__(self) -> str:
        return f"{self.user.username} - Google ({self.email})"


class AuthKakaoAccount(models.Model):
    """Kakao 계정 연결 정보 (ERD: auth_kakao_accounts)

    Kakao 계정과 사용자 매핑. OAuth 토큰은 DB에 저장하지 않고 JWT 발급에만 사용.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="kakao_accounts",
        verbose_name="사용자",
    )

    kakao_user_id = models.CharField(
        max_length=255,
        unique=True,
        verbose_name="Kakao 사용자 ID",
    )
    email = models.EmailField(
        max_length=254,
        verbose_name="Kakao 이메일",
    )

    connected_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="연결일시",
    )

    class Meta:
        db_table = "auth_kakao_accounts"
        verbose_name = "Kakao 계정"
        verbose_name_plural = "Kakao 계정"
        indexes = [
            models.Index(fields=["user"], name="ix_auth_kakao_user"),
        ]

    def __str__(self) -> str:
        return f"{self.user.username} - Kakao ({self.email})"


# ============================================================================
# 하위 호환성 모델 (ERD V2.1에 없음 - 기존 코드 호환용)
# ============================================================================

class UserPaymentMethod(models.Model):
    """사용자 결제 수단 정보 (하위 호환성)"""

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
        verbose_name="사용자",
    )

    type = models.CharField(
        max_length=20,
        choices=PAYMENT_TYPE_CHOICES,
        verbose_name="결제 수단 유형",
    )
    provider = models.CharField(
        max_length=50,
        verbose_name="결제 제공자",
    )

    card_number_last4 = models.CharField(
        max_length=4,
        null=True,
        blank=True,
        verbose_name="카드 번호 마지막 4자리",
    )
    card_issuer = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="카드 발급사",
    )
    card_type = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name="카드 종류",
    )

    bank_name = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="은행명",
    )
    account_number_last4 = models.CharField(
        max_length=4,
        null=True,
        blank=True,
        verbose_name="계좌번호 마지막 4자리",
    )

    payment_gateway_token = models.TextField(
        null=True,
        blank=True,
        verbose_name="PG사 빌링키",
    )

    is_default = models.BooleanField(
        default=False,
        verbose_name="기본 결제 수단",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "user_payment_methods"
        verbose_name = "결제 수단"
        verbose_name_plural = "결제 수단"

    def __str__(self) -> str:
        return f"{self.user.username} - {self.get_type_display()}"

    def save(self, *args, **kwargs):
        if self.is_default:
            UserPaymentMethod.objects.filter(user=self.user).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)
