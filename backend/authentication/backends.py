"""
이메일 기반 인증 백엔드

ERD V2.1 기준으로 비밀번호 해시는 AuthEmailCredential 테이블에만 저장하고,
User.password 필드는 Django 내부 토큰/호환성 용도로만 사용한다.
"""

from __future__ import annotations

from typing import Optional

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.hashers import check_password
from django.utils import timezone

from .models import AuthEmailCredential


class EmailAuthBackend(ModelBackend):
    """이메일 주소 + AuthEmailCredential 기반 로그인 백엔드

    비밀번호 찾기 기능 지원:
    - 기존 비밀번호로 로그인 성공 시: 임시 비밀번호 무효화, must_change_password = False
    - 임시 비밀번호로 로그인 성공 시: 임시 비밀번호 무효화, must_change_password = True
    """

    def authenticate(
        self,
        request,
        username: Optional[str] = None,
        password: Optional[str] = None,
        **kwargs,
    ):  # type: ignore[override]
        # Django 기본 시그니처(username)와 email 파라미터 모두 수용
        email = kwargs.get("email") or username
        if email is None or password is None:
            return None

        User = get_user_model()
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return None

        # ERD V2.1: 비밀번호 해시는 AuthEmailCredential 에만 저장
        try:
            cred: AuthEmailCredential = user.email_credential  # type: ignore[attr-defined]
        except AuthEmailCredential.DoesNotExist:
            return None

        # 기존 비밀번호 확인
        if check_password(password, cred.password_hash):
            # 기존 비밀번호로 로그인 성공 → 임시 비밀번호 무효화 및 플래그 리셋
            if cred.temp_password_hash or cred.must_change_password:
                cred.temp_password_hash = None
                cred.must_change_password = False
                cred.save(update_fields=["temp_password_hash", "must_change_password"])

            if not self.user_can_authenticate(user):
                return None
            return user

        # 임시 비밀번호 확인 (만료 여부 체크)
        if cred.temp_password_hash and check_password(password, cred.temp_password_hash):
            # 임시 비밀번호 만료 확인
            if cred.temp_password_expires_at and cred.temp_password_expires_at < timezone.now():
                # 만료된 임시 비밀번호 → 무효화하고 로그인 실패
                cred.temp_password_hash = None
                cred.temp_password_expires_at = None
                cred.save(update_fields=["temp_password_hash", "temp_password_expires_at"])
                return None

            # 임시 비밀번호로 로그인 성공 → 임시 비밀번호 무효화, 비밀번호 변경 필요 플래그 설정
            cred.temp_password_hash = None
            cred.temp_password_expires_at = None
            cred.must_change_password = True
            cred.save(update_fields=["temp_password_hash", "temp_password_expires_at", "must_change_password"])

            if not self.user_can_authenticate(user):
                return None
            return user

        # 둘 다 실패
        return None

