"""
# ========================= 인증 모듈 시작(이식 가이드) =========================
# 커스텀 DRF 퍼미션 클래스를 정의합니다.
# ============================================================================
"""

from __future__ import annotations

from rest_framework.permissions import BasePermission, SAFE_METHODS
from typing import Iterable
from .services import has_any_role


class IsAuthenticatedOrCreate(BasePermission):
    """읽기는 허용, 생성은 누구나 가능, 그 외는 인증 필요"""

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        if request.method.lower() == "post":
            return True
        return bool(request.user and request.user.is_authenticated)


class IsSelf(BasePermission):
    """사용자 객체 접근 시 자기 자신만 수정 가능"""

    def has_object_permission(self, request, view, obj):
        return bool(request.user and request.user.is_authenticated and obj == request.user)


class RoleRequired(BasePermission):
    """뷰에 required_roles 속성을 정의하면 해당 역할만 허용

    Role 상하관계: admin > seller > user > guest
    
    예)
    class SomeView(APIView):
        permission_classes = [RoleRequired]
        required_roles = ["admin", "seller"]  # 관리자 또는 판매자만 접근 가능
    """

    def has_permission(self, request, view):
        roles = getattr(view, "required_roles", None)
        if not roles:
            return bool(request.user and request.user.is_authenticated)
        if isinstance(roles, (list, tuple, set)):
            return has_any_role(request.user, roles)  # 사용자 역할 확인
        return False
