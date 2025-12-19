"""
# ========================= 인증 모듈 공식 가이드 =========================
# 본 모듈에서 인증 관련 기본 설정을 환경 변수로 로딩하는 유틸입니다.
# 프로젝트별로 `AUTH_CONFIG` 값을 settings.py 에서 오버라이드하여 사용할 수 있습니다.
# ============================================================================
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict


def _env(key: str, default: Any | None = None) -> Any:
    """환경 변수를 조회하는 헬퍼 (비어 있으면 기본값 반환)

    - 실제 운영 환경에서는 환경 변수로 민감 정보를 관리
    - `.env` 를 사용하는 경우 settings.py 에서 이미 로드한 뒤 사용
    """

    val = os.environ.get(key)
    return val if val not in (None, "") else default


AUTH_CONFIG: Dict[str, Any] = {
    # OAuth2 - Google
    "GOOGLE_CLIENT_ID": _env("GOOGLE_CLIENT_ID"),
    "GOOGLE_CLIENT_SECRET": _env("GOOGLE_CLIENT_SECRET"),
    "GOOGLE_CALLBACK_URL": _env("GOOGLE_CALLBACK_URL", "/auth/google/callback/"),
    # OAuth2 - Kakao
    "KAKAO_CLIENT_ID": _env("KAKAO_REST_API_KEY"),
    "KAKAO_CLIENT_SECRET": _env("KAKAO_CLIENT_SECRET", ""),
    "KAKAO_CALLBACK_URL": _env("KAKAO_CALLBACK_URL", "/auth/kakao/callback/"),
    # JWT 만료 설정
    "JWT_ACCESS_TOKEN_LIFETIME": int(_env("JWT_ACCESS_TOKEN_LIFETIME", 15)),  # minutes
    "JWT_REFRESH_TOKEN_LIFETIME": int(_env("JWT_REFRESH_TOKEN_LIFETIME", 7)),  # days
    # 기본 역할 설정 (guest: 비회원, user: 일반회원, seller: 판매자, admin: 관리자)
    "DEFAULT_ROLE": _env("DEFAULT_ROLE", "guest"),
    # 관리자 이메일 화이트리스트(콤마 구분)
    "ADMIN_EMAIL_WHITELIST": _env("ADMIN_EMAIL_WHITELIST", ""),
    # 개발 용 옵션 (토큰 응답 포함 여부)
    "PASSWORD_RESET_RETURN_TOKEN_IN_RESPONSE": str(
        _env("PASSWORD_RESET_RETURN_TOKEN_IN_RESPONSE", "false")
    ).lower()
    in ("1", "true", "yes"),
    # 이메일 인증
    "EMAIL_VERIFICATION_CODE_LENGTH": int(_env("EMAIL_VERIFICATION_CODE_LENGTH", 6)),
    "EMAIL_VERIFICATION_FROM_EMAIL": _env("EMAIL_VERIFICATION_FROM_EMAIL"),
    "EMAIL_VERIFICATION_EXPIRES_MINUTES": int(
        _env("EMAIL_VERIFICATION_EXPIRES_MINUTES", 30)
    ),
}


@dataclass
class OAuthProviderConfig:
    """OAuth 공급자에서 사용하는 공통 설정 컨테이너"""

    client_id: str | None
    client_secret: str | None
    callback_url: str


def get_google_config() -> OAuthProviderConfig:
    """Google OAuth 설정 반환"""

    return OAuthProviderConfig(
        client_id=AUTH_CONFIG.get("GOOGLE_CLIENT_ID"),
        client_secret=AUTH_CONFIG.get("GOOGLE_CLIENT_SECRET"),
        callback_url=str(AUTH_CONFIG.get("GOOGLE_CALLBACK_URL")),
    )


def get_kakao_config() -> OAuthProviderConfig:
    """Kakao OAuth 설정 반환"""

    return OAuthProviderConfig(
        client_id=AUTH_CONFIG.get("KAKAO_CLIENT_ID"),
        client_secret=AUTH_CONFIG.get("KAKAO_CLIENT_SECRET"),
        callback_url=str(AUTH_CONFIG.get("KAKAO_CALLBACK_URL")),
    )
