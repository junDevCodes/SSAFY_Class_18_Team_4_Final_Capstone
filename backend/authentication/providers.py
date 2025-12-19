"""
# ========================= 인증 모듈 시작(이식 가이드) =========================
# OAuth2 제공자별 헬퍼 함수 모음입니다. (Google / Kakao)
# - 권장: django-allauth 사용. 본 헬퍼는 REST 엔드포인트에서 직접 사용 가능하도록 구현.
# ============================================================================
"""

from __future__ import annotations
import secrets
from dataclasses import dataclass
from typing import Any, Dict, Tuple

import requests

from .config import get_google_config, get_kakao_config


@dataclass
class OAuthState:
    """state 값 관리용 컨테이너"""

    value: str

    @staticmethod
    def generate() -> "OAuthState":
        # CSRF 방지를 위한 난수 state 생성
        raw = secrets.token_urlsafe(24)
        return OAuthState(value=raw)


def build_google_authorize_url(request) -> Tuple[str, str]:
    """Google 인증 URL 생성 (state 포함 반환)

    반환: (authorize_url, state)
    """

    cfg = get_google_config()
    state = OAuthState.generate().value
    params = {
        "client_id": cfg.client_id,
        "redirect_uri": request.build_absolute_uri(cfg.callback_url),
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "include_granted_scopes": "true",
        "state": state,
        "prompt": "consent",
    }
    query = "&".join(f"{k}={requests.utils.quote(str(v))}" for k, v in params.items())
    url = f"https://accounts.google.com/o/oauth2/v2/auth?{query}"
    return url, state


def exchange_google_token(request, code: str) -> Dict[str, Any]:
    """Google 액세스 토큰 교환 및 사용자 정보 조회"""

    cfg = get_google_config()
    token_resp = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": cfg.client_id,
            "client_secret": cfg.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": request.build_absolute_uri(cfg.callback_url),
        },
        timeout=10,
    )
    token_resp.raise_for_status()
    tokens = token_resp.json()

    # OpenID Connect userinfo
    userinfo_resp = requests.get(
        "https://openidconnect.googleapis.com/v1/userinfo",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        timeout=10,
    )
    userinfo_resp.raise_for_status()
    userinfo = userinfo_resp.json()
    return {"tokens": tokens, "profile": userinfo}


def build_kakao_authorize_url(request) -> Tuple[str, str]:
    """Kakao 인증 URL 생성 (state 포함 반환)

    반환: (authorize_url, state)
    """

    cfg = get_kakao_config()
    state = OAuthState.generate().value
    params = {
        "client_id": cfg.client_id,
        "redirect_uri": request.build_absolute_uri(cfg.callback_url),
        "response_type": "code",
        "state": state,
    }
    query = "&".join(f"{k}={requests.utils.quote(str(v))}" for k, v in params.items())
    url = f"https://kauth.kakao.com/oauth/authorize?{query}"
    return url, state


def exchange_kakao_token(request, code: str) -> Dict[str, Any]:
    """Kakao 액세스 토큰 교환 및 사용자 정보 조회"""

    cfg = get_kakao_config()
    token_resp = requests.post(
        "https://kauth.kakao.com/oauth/token",
        data={
            "grant_type": "authorization_code",
            "client_id": cfg.client_id,
            "client_secret": cfg.client_secret or "",
            "redirect_uri": request.build_absolute_uri(cfg.callback_url),
            "code": code,
        },
        timeout=10,
    )
    token_resp.raise_for_status()
    tokens = token_resp.json()

    # 사용자 정보 조회
    userinfo_resp = requests.get(
        "https://kapi.kakao.com/v2/user/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        timeout=10,
    )
    userinfo_resp.raise_for_status()
    profile = userinfo_resp.json()

    # 카카오 이메일/프로필 정규화
    kakao_account = profile.get("kakao_account", {})
    properties = profile.get("properties", {})
    normalized = {
        "id": str(profile.get("id")),
        "email": kakao_account.get("email"),
        "name": properties.get("nickname"),
        "picture": properties.get("profile_image") or kakao_account.get("profile", {}).get("profile_image_url"),
    }
    return {"tokens": tokens, "profile": normalized}
