"""
# ========================= 인증 모듈 시작(이식 가이드) =========================
# 이 모듈은 Django 앱 설정을 담당합니다. 다른 프로젝트로 이식 시 수정 없이 사용 가능합니다.
# ============================================================================
"""

from django.apps import AppConfig


class AuthenticationConfig(AppConfig):
    """인증 앱 설정 클래스"""

    default_auto_field = "django.db.models.BigAutoField"
    name = "authentication"
    verbose_name = "인증"

    def ready(self) -> None:  # pragma: no cover - 앱 초기화 훅
        # 시그널 연결을 위해 임포트 수행
        # (앱 로딩 시 한 번만 실행됨)
        from . import signals  # noqa: F401

