"""
# ========================= 인증 모듈 시작(이식 가이드) =========================
# 이메일 기반 인증 백엔드입니다. settings.py 의 AUTHENTICATION_BACKENDS 에 추가하여 사용합니다.
# ============================================================================
"""

from __future__ import annotations

from typing import Optional

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailAuthBackend(ModelBackend):
    """이메일 주소로 로그인 가능하게 하는 인증 백엔드"""

    def authenticate(self, request, username: Optional[str] = None, password: Optional[str] = None, **kwargs):  # type: ignore[override]
        # Django 는 기본적으로 username 인자를 사용하므로 email 파라미터도 고려
        email = kwargs.get("email") or username
        if email is None or password is None:
            return None
        User = get_user_model()
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return None
        else:
            if user.check_password(password) and self.user_can_authenticate(user):
                return user
        return None

