"""
인증 모듈 시그널 (ERD V2.1)

사용자 생성/업데이트 관련 시그널 훅입니다.
ERD V2.1에서는 OAuth 정보가 auth_google_accounts, auth_kakao_accounts 테이블로 분리되어
별도의 provider 필드가 필요 없습니다.
"""

from __future__ import annotations

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import User, UserProfile


@receiver(post_save, sender=User)
def create_user_profile(sender, instance: User, created: bool, **kwargs):
    """신규 사용자 생성 시 UserProfile 자동 생성"""
    if created:
        UserProfile.objects.get_or_create(user=instance)
