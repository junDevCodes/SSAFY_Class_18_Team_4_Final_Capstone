"""
# ========================= 인증 모듈 시작(이식 가이드) =========================
# django-allauth 연동 시 소셜 로그인 계정 병합/생성 로직을 커스터마이징하는 어댑터입니다.
# 프로젝트 settings.py 에서 SOCIALACCOUNT_ADAPTER = 'authentication.adapters.SocialAccountAdapter'
# 로 지정하여 사용합니다.
# ============================================================================
"""

from __future__ import annotations

from typing import Any

from django.contrib.auth import get_user_model

try:  # pragma: no cover - 선택적 의존성
    from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
except Exception:  # pragma: no cover - allauth 미설치 시 무시
    DefaultSocialAccountAdapter = object  # type: ignore

from .models import Provider


class SocialAccountAdapter(DefaultSocialAccountAdapter):  # type: ignore[misc]
    """이메일 중복 시 기존 계정에 OAuth 연결 및 자동 가입 처리"""

    def pre_social_login(self, request, sociallogin):  # type: ignore[override]
        # 소셜 프로필에서 이메일 추출
        email = None
        try:
            email = sociallogin.account.extra_data.get("email")
        except Exception:
            pass
        if not email:
            return

        User = get_user_model()
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return  # 기존 사용자 없음 -> 이후 save_user 에서 신규 생성됨

        # 기존 사용자와 소셜계정 연결 (자동 병합)
        sociallogin.connect(request, user)

    def save_user(self, request, sociallogin, form=None):  # type: ignore[override]
        # 기본 저장 로직 수행
        user = super().save_user(request, sociallogin, form)

        # provider 정보 업데이트
        provider = sociallogin.account.provider
        provider_id = str(sociallogin.account.uid)
        updates = {}
        if provider == "google" and user.provider != Provider.GOOGLE:
            updates["provider"] = Provider.GOOGLE
        elif provider == "kakao" and user.provider != Provider.KAKAO:
            updates["provider"] = Provider.KAKAO

        if user.provider_id != provider_id:
            updates["provider_id"] = provider_id

        # 프로필 이미지 반영 (가능한 경우)
        picture = sociallogin.account.extra_data.get("picture") or (
            sociallogin.account.extra_data.get("properties", {}).get("profile_image")
        )
        if picture and getattr(user, "profile_image_url", None) != picture:
            updates["profile_image_url"] = picture

        if updates:
            for k, v in updates.items():
                setattr(user, k, v)
            user.save(update_fields=list(updates.keys()))
        return user

