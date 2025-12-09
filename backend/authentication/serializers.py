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
from django.contrib.auth.hashers import check_password
from django.core import exceptions
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from .models import User, UserAddress, UserPaymentMethod, UserProfile, AuthEmailCredential
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
            # ERD V2.1: is_email_verified는 AuthEmailCredential에 있음
            is_verified = False
            if hasattr(existing, 'email_credential'):
                is_verified = existing.email_credential.is_email_verified
            if is_verified:
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
        # ERD V2.1: is_email_verified는 AuthEmailCredential에 있음
        is_verified = False
        if hasattr(user, 'email_credential'):
            is_verified = user.email_credential.is_email_verified
        if not is_verified:
            raise serializers.ValidationError({"detail": _("이메일 인증이 완료되지 않은 계정입니다.")})
        attrs["user"] = user
        return attrs


class UserProfileSerializer(serializers.ModelSerializer):
    """사용자 프로필 정보 시리얼라이저 (ERD V2.1)"""

    class Meta:
        model = UserProfile
        fields = [
            "profile_image_url",
            "phone_number",
            "date_of_birth",
            "gender",
            "timezone",
            "language",
            "notification_enabled",
            "marketing_agreed",
        ]


class UserSerializer(serializers.ModelSerializer):
    """사용자 시리얼라이저 (ERD V2.1)"""

    # UserProfile 정보 포함
    profile_image_url = serializers.SerializerMethodField()
    timezone = serializers.SerializerMethodField()
    profile = UserProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "username",
            "role",
            "profile_image_url",
            "timezone",
            "profile",
        ]
        read_only_fields = ["email", "role"]  # role은 관리자만 수정 가능하도록 읽기 전용

    def get_profile_image_url(self, obj):
        """UserProfile에서 프로필 이미지 URL 가져오기"""
        if hasattr(obj, 'profile') and obj.profile:
            return obj.profile.profile_image_url
        return None

    def get_timezone(self, obj):
        """UserProfile에서 타임존 가져오기"""
        if hasattr(obj, 'profile') and obj.profile:
            return obj.profile.timezone
        return "Asia/Seoul"


class PasswordChangeSerializer(serializers.Serializer):
    """비밀번호 변경"""

    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        user: User = self.context["request"].user
        cred = getattr(user, "email_credential", None)
        if cred is None or not check_password(attrs["old_password"], cred.password_hash):
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


class UserAddressSerializer(serializers.ModelSerializer):
    """사용자 배송지 시리얼라이저 (ERD V2.1)"""

    class Meta:
        model = UserAddress
        fields = [
            'id',
            'address_name',
            'recipient_name',
            'recipient_phone',
            'postal_code',
            'address_line1',
            'address_line2',
            'delivery_memo',
            'is_default',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate(self, attrs):
        # 기본 배송지가 아닌 경우, 사용자에게 기본 배송지가 없으면 자동으로 설정
        if not attrs.get('is_default'):
            user = self.context.get('request').user
            if not UserAddress.objects.filter(user=user).exists():
                attrs['is_default'] = True
        return attrs


class UserPaymentMethodSerializer(serializers.ModelSerializer):
    """사용자 결제 수단 시리얼라이저 (MVP: 저장만)"""

    class Meta:
        model = UserPaymentMethod
        fields = [
            'id',
            'type',
            'provider',
            'card_number_last4',
            'card_issuer',
            'card_type',
            'bank_name',
            'account_number_last4',
            'is_default',
            'expires_at',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate(self, attrs):
        # 기본 결제 수단이 아닌 경우, 사용자에게 기본 결제 수단이 없으면 자동으로 설정
        if not attrs.get('is_default'):
            user = self.context.get('request').user
            if not UserPaymentMethod.objects.filter(user=user).exists():
                attrs['is_default'] = True
        return attrs
