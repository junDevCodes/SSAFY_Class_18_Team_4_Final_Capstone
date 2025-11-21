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
