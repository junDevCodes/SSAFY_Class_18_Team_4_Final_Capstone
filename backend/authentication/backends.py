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

from .models import AuthEmailCredential


class EmailAuthBackend(ModelBackend):
    """이메일 주소 + AuthEmailCredential 기반 로그인 백엔드"""

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

        if not check_password(password, cred.password_hash):
            return None

        if not self.user_can_authenticate(user):
            return None

        return user

