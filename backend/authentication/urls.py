"""
# ========================= 인증 모듈 제작(공식 가이드) =========================
# 인증 모듈의 URL 패턴을 정의합니다. 프로젝트 루트 urls.py 에서 include 하여 사용합니다.
# ============================================================================
"""

from __future__ import annotations

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    GoogleCallbackView,
    GoogleLoginRedirectView,
    KakaoCallbackView,
    KakaoLoginRedirectView,
    LoginView,
    LogoutView,
    PasswordChangeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RegisterView,
    TokenRefreshView,
    UserMeView,
    EmailVerificationConfirmView,
    UserAddressViewSet,
    UserPaymentMethodViewSet,
)

app_name = "authentication"

# Router for ViewSets
router = DefaultRouter()
router.register(r'addresses', UserAddressViewSet, basename='address')
router.register(r'payment-methods', UserPaymentMethodViewSet, basename='payment-method')

urlpatterns = [
    # 기본 인증
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/register/verify/", EmailVerificationConfirmView.as_view(), name="register_verify"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("auth/user/", UserMeView.as_view(), name="user_me"),
    path("auth/password/change/", PasswordChangeView.as_view(), name="password_change"),
    path("auth/password/reset/", PasswordResetRequestView.as_view(), name="password_reset"),
    path(
        "auth/password/reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    # OAuth2 - Google
    path("auth/google/", GoogleLoginRedirectView.as_view(), name="google_login"),
    path("auth/google/callback/", GoogleCallbackView.as_view(), name="google_callback"),
    # OAuth2 - Kakao
    path("auth/kakao/", KakaoLoginRedirectView.as_view(), name="kakao_login"),
    path("auth/kakao/callback/", KakaoCallbackView.as_view(), name="kakao_callback"),
    # ViewSet URLs (배송지 관리)
    path("auth/", include(router.urls)),
]

