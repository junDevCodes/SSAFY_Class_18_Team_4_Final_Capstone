"""
# ========================= 인증 모듈 시작(이식 가이드) =========================
# 사용자 생성/업데이트 관련 시그널 훅입니다.
# ============================================================================
"""

from __future__ import annotations

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Provider, User


@receiver(post_save, sender=User)
def ensure_provider_default(sender, instance: User, created: bool, **kwargs):  # pragma: no cover - 단순 기본값 보정
    """신규 사용자 생성 시 기본 provider 를 email 로 보정"""

    if created and not instance.provider:
        instance.provider = Provider.EMAIL
        instance.save(update_fields=["provider"])

