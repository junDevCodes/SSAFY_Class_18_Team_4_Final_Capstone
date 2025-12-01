"""
# ========================= 인증 모듈 시작(이식 가이드) =========================
# 관리자에서 사용자 모델을 관리하기 위한 설정입니다.
# ============================================================================
"""

from __future__ import annotations

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """커스텀 사용자 관리자"""

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (_("개인 정보"), {"fields": ("first_name", "last_name", "email", "role")}),
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
        (_("중요 일자"), {"fields": ("last_login", "date_joined")}),
        (_("소셜 정보"), {"fields": ("provider", "provider_id", "profile_image_url", "timezone")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "email", "password1", "password2", "provider"),
            },
        ),
    )
    list_display = ("id", "username", "email", "role", "provider", "is_staff", "is_active")
    list_filter = ("role", "is_staff", "is_superuser", "is_active", "groups", "provider")
    search_fields = ("username", "first_name", "last_name", "email")
    ordering = ("id",)
