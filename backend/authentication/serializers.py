"""
# ========================= 인증 모듈 공식 가이드 =========================
# DRF 시리얼라이저 모음. 회원가입/로그인/비밀번호 관리/이메일 인증 요청 처리
# ============================================================================
"""

from __future__ import annotations

import logging
from typing import Any

from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core import exceptions
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from .models import User
from .services import EmailDeliveryError, send_email_verification_email, upsert_pending_registration

logger = logging.getLogger(__name__)


class RegisterSerializer(serializers.Serializer):
    """회원가입 요청을 인증 대기 테이블에 저장"""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    username = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._legacy_user = None

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        email = attrs["email"].lower()
        attrs["email"] = email
        try:
            validate_password(attrs["password"])
        except exceptions.ValidationError as e:
            raise serializers.ValidationError({"password": list(e.messages)})

        UserModel = get_user_model()
        existing = UserModel.objects.filter(email=email).first()
        if existing:
            if existing.is_email_verified:
                raise serializers.ValidationError({"email": _("이미 가입된 이메일입니다.")})
            self._legacy_user = existing
        return attrs

    def create(self, validated_data: dict[str, Any]):
        """PendingRegistration 생성 및 이메일 발송
        
        이메일 발송 실패 시에도 PendingRegistration은 생성되므로,
        사용자는 나중에 인증 코드를 다시 요청할 수 있습니다.
        """
        username = (validated_data.get("username") or "").strip() or None
        pending = upsert_pending_registration(
            validated_data["email"],
            validated_data["password"],
            username,
        )
        
        # 이메일 발송 시도 (타임아웃 발생 가능)
        try:
            send_email_verification_email(pending.email, pending.verification_code)
        except EmailDeliveryError as exc:
            # 이메일 발송 실패 시에도 PendingRegistration은 생성되어 있음
            # 사용자에게 명확한 에러 메시지 제공
            error_message = str(exc)
            logger.error(f"이메일 발송 실패: {pending.email} - {error_message}")
            
            # 개발 환경에서 console 백엔드 사용 시 인증 코드 제공
            from django.conf import settings
            email_backend = getattr(settings, "EMAIL_BACKEND", "")
            error_data = {
                "detail": error_message,
                "code": "email_delivery_failed",
                "email": pending.email,  # 사용자가 입력한 이메일 반환
            }
            
            # 개발 환경에서는 인증 코드도 제공 (사용자가 직접 입력 가능)
            if email_backend == "django.core.mail.backends.console.EmailBackend":
                error_data["verification_code"] = pending.verification_code
                error_data["detail"] = f"{error_message} (개발 환경: 인증 코드는 {pending.verification_code}입니다)"
            
            raise serializers.ValidationError(error_data)
        
        if self._legacy_user:
            self._legacy_user.delete()
        return pending


class LoginSerializer(serializers.Serializer):
    """이메일/비밀번호 로그인"""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        email = attrs.get("email")
        password = attrs.get("password")
        user = authenticate(self.context.get("request"), email=email, password=password)
        if not user:
            raise serializers.ValidationError({"detail": _("이메일 또는 비밀번호가 올바르지 않습니다.")})
        if not user.is_active:
            raise serializers.ValidationError({"detail": _("비활성화된 계정입니다.")})
        if not getattr(user, "is_email_verified", False):
            raise serializers.ValidationError({"detail": _("이메일 인증이 완료되지 않은 계정입니다.")})
        attrs["user"] = user
        return attrs


class UserSerializer(serializers.ModelSerializer):
    """사용자 프로필 시리얼라이저"""

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "username",
            "first_name",
            "last_name",
            "profile_image_url",
            "provider",
            "role",
            "timezone",
        ]
        read_only_fields = ["email", "provider", "role"]  # role은 관리자만 수정 가능하도록 읽기 전용


class PasswordChangeSerializer(serializers.Serializer):
    """비밀번호 변경"""

    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        user: User = self.context["request"].user
        if not user.check_password(attrs["old_password"]):
            raise serializers.ValidationError({"old_password": _("기존 비밀번호가 일치하지 않습니다.")})
        try:
            validate_password(attrs["new_password"], user)
        except exceptions.ValidationError as e:
            raise serializers.ValidationError({"new_password": list(e.messages)})
        return attrs


class PasswordResetRequestSerializer(serializers.Serializer):
    """비밀번호 재설정 요청"""

    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    """비밀번호 재설정 확인"""

    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        try:
            validate_password(attrs["new_password"])
        except exceptions.ValidationError as e:
            raise serializers.ValidationError({"new_password": list(e.messages)})
        return attrs


class EmailVerificationConfirmSerializer(serializers.Serializer):
    """회원가입 이메일 인증 확인"""

    email = serializers.EmailField()
    code = serializers.CharField()
