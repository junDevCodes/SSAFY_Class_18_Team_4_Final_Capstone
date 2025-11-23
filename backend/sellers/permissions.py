"""
판매자 관련 권한 클래스
"""
from rest_framework import permissions


class IsSeller(permissions.BasePermission):
    """판매자 권한 (승인된 판매자만)"""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        # seller_profile이 있고 status가 active인 경우만 허용
        if not hasattr(request.user, 'seller_profile'):
            return False

        return request.user.seller_profile.status == 'active'


class IsSellerOrReadOnly(permissions.BasePermission):
    """판매자는 수정 가능, 일반 사용자는 읽기만"""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True

        if not request.user or not request.user.is_authenticated:
            return False

        if not hasattr(request.user, 'seller_profile'):
            return False

        return request.user.seller_profile.status == 'active'


class IsOwnerSeller(permissions.BasePermission):
    """자신의 판매자 정보만 수정 가능"""

    def has_object_permission(self, request, view, obj):
        # 읽기 권한은 모두 허용
        if request.method in permissions.SAFE_METHODS:
            return True

        # 수정은 본인만
        if not request.user or not request.user.is_authenticated:
            return False

        return obj.user == request.user


class IsSellerProduct(permissions.BasePermission):
    """자신의 판매 상품만 수정 가능"""

    def has_permission(self, request, view):
        # 읽기는 모두 허용
        if request.method in permissions.SAFE_METHODS:
            return True

        # 생성/수정은 판매자만
        if not request.user or not request.user.is_authenticated:
            return False

        if not hasattr(request.user, 'seller_profile'):
            return False

        return request.user.seller_profile.status == 'active'

    def has_object_permission(self, request, view, obj):
        # 읽기는 모두 허용
        if request.method in permissions.SAFE_METHODS:
            return True

        # 수정은 해당 상품의 판매자만
        if not request.user or not request.user.is_authenticated:
            return False

        if not hasattr(obj, 'seller') or not obj.seller:
            return False

        return obj.seller.user == request.user
