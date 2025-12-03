"""
인증 모듈 Admin (ERD V2.1)

관리자에서 사용자/프로필/주소/인증 관련 모델을 관리하기 위한 설정입니다.
"""

from __future__ import annotations

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import (
    User,
    UserProfile,
    UserAddress,
    PendingRegistration,
    AuthEmailCredential,
    AuthGoogleAccount,
    AuthKakaoAccount,
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """커스텀 사용자 관리자 (ERD V2.1)

    - User.password 는 unusable 값만 유지
    - 실제 비밀번호 관리는 AuthEmailCredential 에서만 수행
    - 관리자 화면에서는 비밀번호 필드를 숨긴다.
    """

    fieldsets = (
        (None, {"fields": ("username",)}),
        (_("개인 정보"), {"fields": ("email", "role")}),
        (
            _("권한"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (_("중요 날짜"), {"fields": ("last_login", "date_joined", "deleted_at")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                # 관리자에서 사용자 생성 시에도 비밀번호는 입력하지 않음
                "fields": ("username", "email"),
            },
        ),
    )
    list_display = ("id", "username", "email", "role", "is_staff", "is_active")
    list_filter = ("role", "is_staff", "is_superuser", "is_active", "groups")
    search_fields = ("username", "email")
    ordering = ("id",)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """사용자 프로필 관리자"""

    list_display = ("user", "gender", "date_of_birth", "phone_number")
    search_fields = ("user__username", "user__email", "phone_number")


@admin.register(UserAddress)
class UserAddressAdmin(admin.ModelAdmin):
    """사용자 주소 관리자"""

    list_display = ("user", "address_name", "is_default", "recipient_name")
    list_filter = ("is_default",)
    search_fields = ("user__username", "address_name", "address_line1")


@admin.register(PendingRegistration)
class PendingRegistrationAdmin(admin.ModelAdmin):
    """가등록 관리자"""

    list_display = ("email", "username", "verification_code", "expires_at", "created_at")
    search_fields = ("email", "username")


@admin.register(AuthEmailCredential)
class AuthEmailCredentialAdmin(admin.ModelAdmin):
    """이메일 인증 정보 관리자"""

    list_display = ("user", "is_email_verified", "fail_count", "last_changed_at")
    list_filter = ("is_email_verified",)


@admin.register(AuthGoogleAccount)
class AuthGoogleAccountAdmin(admin.ModelAdmin):
    """Google 계정 연동 관리자"""

    list_display = ("user", "google_user_id", "email", "connected_at")
    search_fields = ("google_user_id", "email")


@admin.register(AuthKakaoAccount)
class AuthKakaoAccountAdmin(admin.ModelAdmin):
    """Kakao 계정 연동 관리자"""

    list_display = ("user", "kakao_user_id", "email", "connected_at")
    search_fields = ("kakao_user_id", "email")

