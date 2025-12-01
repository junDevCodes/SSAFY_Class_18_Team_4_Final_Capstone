"""
# ========================= 인증 모듈 시작(이식 가이드) =========================
# 선택적 JWT 미들웨어: DRF 외 일반 뷰에서도 Authorization 헤더의 JWT 를 파싱하여
# request.user 를 설정하고자 할 때 사용합니다. (선택 사항)
# ============================================================================
"""

from __future__ import annotations

import logging
from typing import Callable

from django.contrib.auth.models import AnonymousUser
from django.utils.functional import SimpleLazyObject
from rest_framework_simplejwt.authentication import JWTAuthentication

logger = logging.getLogger(__name__)


def _get_user_from_request(request):
    """요청의 Authorization 헤더에서 JWT 를 파싱하여 사용자 반환"""

    try:
        authenticator = JWTAuthentication()
        res = authenticator.authenticate(request)
        if res is None:
            return AnonymousUser()
        user, _token = res
        return user
    except Exception as e:  # pragma: no cover - 방어적 로깅
        logger.debug("JWT 파싱 실패: %s", e)
        return AnonymousUser()


class JWTAuthenticationMiddleware:
    """선택적 JWT 인증 미들웨어 (DRF 없이도 user 설정)"""

    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request):
        request.user = SimpleLazyObject(lambda: _get_user_from_request(request))
        response = self.get_response(request)
        return response
