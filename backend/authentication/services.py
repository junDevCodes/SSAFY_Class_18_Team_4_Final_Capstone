"""
# ========================= 인증 모듈 공식 가이드 =========================
# 인증 서비스 계층: 토큰 발급, 역할 정책, 이메일 인증 대기 관리, 메일 발송
# ============================================================================
"""

from __future__ import annotations

from datetime import timedelta
import logging
import secrets
import string
import socket
from smtplib import SMTPAuthenticationError
from typing import Iterable, Optional

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from .config import AUTH_CONFIG
from .models import PendingRegistration, Provider, AuthEmailCredential

logger = logging.getLogger(__name__)


class EmailDeliveryError(Exception):
    """인증 메일 발송 실패를 표현"""


def parse_admin_whitelist() -> set[str]:
    """관리자 이메일 화이트리스트 파싱"""

    raw = AUTH_CONFIG.get("ADMIN_EMAIL_WHITELIST") or ""
    return {x.strip().lower() for x in raw.split(",") if x.strip()}


def apply_role_policy_on_create(user) -> None:
    """신규 사용자에게 역할 정책 적용
    
    주의: 이 함수는 role이 이미 설정된 경우에만 관리자 화이트리스트를 확인합니다.
    role이 설정되지 않은 경우에만 기본값을 설정합니다.
    
    - 관리자 화이트리스트: admin (관리자)
    - role이 없으면 기본값: guest (비회원)
    """

    # role이 이미 설정되어 있으면 관리자 화이트리스트만 확인
    if not hasattr(user, 'role') or not user.role:
        default_role = AUTH_CONFIG.get("DEFAULT_ROLE") or "guest"
        user.role = default_role

    # 관리자 화이트리스트 확인 (role이 이미 설정되어 있어도 덮어씀)
    admins = parse_admin_whitelist()
    if user.email and user.email.lower() in admins:
        user.role = "admin"


def generate_email_verification_code(length: Optional[int] = None) -> str:
    """이메일 인증번호(숫자 코드) 생성"""

    if length is None:
        length = int(AUTH_CONFIG.get("EMAIL_VERIFICATION_CODE_LENGTH") or 6)
    digits = string.digits
    return "".join(secrets.choice(digits) for _ in range(length))


def send_email_verification_email(recipient_email: str, verification_code: str) -> None:
    """인증 번호를 포함한 메일 발송

    Gmail SMTP 를 사용할 경우 앱 비밀번호를 발급받아 EMAIL_HOST_PASSWORD 에 넣어야 한다.
    기본 계정 비밀번호를 그대로 쓰면 Google 보안 정책상 2단계 인증을 요구하며 차단된다.
    
    개발 환경에서는 console 백엔드를 사용하여 즉시 응답하도록 권장합니다.
    """

    from_email = AUTH_CONFIG.get("EMAIL_VERIFICATION_FROM_EMAIL") or getattr(
        settings, "DEFAULT_FROM_EMAIL", None
    ) or "noreply@example.com"  # 기본값 설정
    
    email_backend = getattr(settings, "EMAIL_BACKEND", "")
    
    # console 백엔드 사용 시에는 즉시 처리
    if email_backend == "django.core.mail.backends.console.EmailBackend":
        from_email = from_email or "noreply@example.com"
        subject = "회원가입 이메일 인증번호"
        message = (
            "아래 인증번호를 입력하면 회원가입이 완료됩니다.\n\n"
            f"인증번호: {verification_code}"
        )
        # console 백엔드는 즉시 반환되므로 타임아웃 없음
        send_mail(subject, message, from_email, [recipient_email], fail_silently=False)
        return

    # SMTP 백엔드 사용 시 타임아웃 설정
    subject = "회원가입 이메일 인증번호"
    message = (
        "아래 인증번호를 입력하면 회원가입이 완료됩니다.\n\n"
        f"인증번호: {verification_code}"
    )
    
    try:
        # SMTP 연결 타임아웃 설정 (settings에서 가져오거나 기본값 5초)
        email_timeout = getattr(settings, 'EMAIL_TIMEOUT', 5)
        # 주의: socket.setdefaulttimeout()은 전역 설정이므로 임시로 설정 후 복원
        old_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(email_timeout)
        
        try:
            send_mail(subject, message, from_email, [recipient_email], fail_silently=False)
        finally:
            # 타임아웃 설정 복원
            socket.setdefaulttimeout(old_timeout)
    except socket.timeout:
        logger.error(f"이메일 발송 타임아웃: {recipient_email} - SMTP 서버 연결 시간 초과")
        raise EmailDeliveryError("이메일 발송 중 타임아웃이 발생했습니다. 네트워크 연결을 확인하거나 개발 환경에서는 console 백엔드를 사용하세요.")
    except SMTPAuthenticationError as exc:
        logger.exception("SMTP 인증 실패: Gmail 의 앱 비밀번호를 설정했는지 확인 필요", exc_info=exc)
        raise EmailDeliveryError("SMTP 인증에 실패했습니다. Gmail은 앱 비밀번호만 허용합니다. 개발 환경에서는 EMAIL_BACKEND를 console로 설정하세요.")
    except Exception as exc:
        logger.exception("인증 메일 발송 실패", exc_info=exc)
        # 타임아웃이나 연결 실패인 경우 명확한 메시지 제공
        error_msg = str(exc).lower()
        if "timeout" in error_msg or "timed out" in error_msg:
            raise EmailDeliveryError("이메일 발송 중 타임아웃이 발생했습니다. 개발 환경에서는 EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend를 사용하세요.")
        elif "connection" in error_msg or "refused" in error_msg:
            raise EmailDeliveryError("이메일 서버에 연결할 수 없습니다. 개발 환경에서는 EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend를 사용하세요.")
        else:
            raise EmailDeliveryError(f"인증 메일 발송 중 오류가 발생했습니다: {str(exc)}")


def get_user_provider(user) -> str | None:
    """사용자의 인증 공급자 확인 (ERD V2.1)

    Google/Kakao 계정이 연결되어 있는지 확인하여 provider 반환.
    여러 계정이 연결된 경우 email을 우선 반환.
    """
    if hasattr(user, 'email_credential'):
        return Provider.EMAIL
    if hasattr(user, 'google_accounts') and user.google_accounts.exists():
        return Provider.GOOGLE
    if hasattr(user, 'kakao_accounts') and user.kakao_accounts.exists():
        return Provider.KAKAO
    return None


def issue_tokens_with_claims(user) -> dict[str, str]:
    """JWT 발급 (role/provider 정보를 페이로드에 포함)"""

    refresh = RefreshToken.for_user(user)
    refresh["role"] = getattr(user, "role", None)
    refresh["provider"] = get_user_provider(user)

    access = refresh.access_token
    access["role"] = getattr(user, "role", None)
    access["provider"] = get_user_provider(user)
    return {"access": str(access), "refresh": str(refresh)}


def has_any_role(user, roles: Iterable[str]) -> bool:
    """사용자가 지정된 역할 중 하나라도 갖고 있는지 판별"""

    return bool(user and user.is_authenticated and getattr(user, "role", None) in set(roles))


def revoke_all_refresh_tokens(user) -> int:
    """해당 사용자의 모든 리프레시 토큰을 블랙리스트 처리"""

    count = 0
    for ot in OutstandingToken.objects.filter(user=user):
        _, created = BlacklistedToken.objects.get_or_create(token=ot)
        if created:
            count += 1
    return count


def _resolve_username(email: str, desired: str | None = None) -> str:
    """요청된 닉네임이 없을 때 이메일 기반으로 고유한 username 생성"""

    User = get_user_model()
    base = (desired or "" or email.split("@")[0]).strip() or email.split("@")[0]
    candidate = base
    suffix = 1
    while User.objects.filter(username=candidate).exists():
        suffix += 1
        candidate = f"{base}{suffix}"
    return candidate


def upsert_pending_registration(email: str, raw_password: str, username: str | None = None) -> PendingRegistration:
    """인증 대기 정보를 생성/갱신"""

    ttl_minutes = int(AUTH_CONFIG.get("EMAIL_VERIFICATION_EXPIRES_MINUTES") or 30)
    expires_at = timezone.now() + timedelta(minutes=ttl_minutes)
    password_hash = make_password(raw_password)
    code = generate_email_verification_code()

    pending, _ = PendingRegistration.objects.update_or_create(
        email=email,
        defaults={
            "username": username or "",
            "password_hash": password_hash,
            "verification_code": code,
            "expires_at": expires_at,
        },
    )
    return pending


def finalize_pending_registration(pending: PendingRegistration):
    """인증이 완료된 대기 정보를 실제 사용자로 전환 (ERD V2.1)

    일반 회원가입 완료 시 role을 'user'로 설정.
    이메일 인증 정보는 AuthEmailCredential에 저장.
    """

    User = get_user_model()
    with transaction.atomic():
        # username 생성
        username = _resolve_username(pending.email, pending.username)

        # User 객체 생성 (ERD V2.1: provider, is_email_verified 필드 제거됨)
        user = User(
            email=pending.email,
            username=username,
            role="user",  # 일반 회원가입 완료 시 user 권한 부여
        )
        # password_hash는 이미 해시된 상태이므로 직접 할당
        user.set_unusable_password()

        # 관리자 화이트리스트 확인 (role이 이미 user로 설정되어 있으므로 덮어쓰지 않음)
        # 단, 관리자 화이트리스트에 있으면 admin으로 변경
        try:
            admins = parse_admin_whitelist()
            if user.email and user.email.lower() in admins:
                user.role = "admin"
        except Exception as e:
            # 관리자 화이트리스트 확인 실패 시에도 회원가입은 진행
            logger.warning(f"관리자 화이트리스트 확인 실패: {e}")

        user.save()

        # AuthEmailCredential 생성 (ERD V2.1)
        AuthEmailCredential.objects.create(
            user=user,
            password_hash=pending.password_hash,
            is_email_verified=True,
        )

        PendingRegistration.objects.filter(pk=pending.pk).delete()
        return user
