"""
# ========================= 인증 모듈 제작(공식 가이드) =========================
# 인증 관련 모든 REST API 엔드포인트를 정의합니다.
# - 일반 회원가입/로그인/로그아웃/JWT 갱신/프로필/비밀번호 변경·재설정
# - 이메일 인증(회원가입용 인증번호 확인)
# - Google/Kakao OAuth2 리다이렉트 및 콜백 처리
# ============================================================================
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict
import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import (
    url_has_allowed_host_and_scheme,
    urlsafe_base64_decode,
    urlsafe_base64_encode,
)
from django.utils.translation import gettext_lazy as _
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework import generics, permissions, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView as SimpleJWTTokenRefreshView

from .config import AUTH_CONFIG
from .models import PendingRegistration, Provider
from .permissions import IsAuthenticatedOrCreate
from .providers import (
    build_google_authorize_url,
    build_kakao_authorize_url,
    exchange_google_token,
    exchange_kakao_token,
)
from .models import UserAddress, UserPaymentMethod, UserProfile, AuthGoogleAccount, AuthKakaoAccount, AuthEmailCredential
from .serializers import (
    LoginSerializer,
    PasswordChangeSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    UserSerializer,
    EmailVerificationConfirmSerializer,
    UserAddressSerializer,
    UserPaymentMethodSerializer,
    AccountDeleteSerializer,
)
from .services import (
    finalize_pending_registration,
    issue_tokens_with_claims,
    revoke_all_refresh_tokens,
)

logger = logging.getLogger(__name__)


def error_response(message: str, code: str, http_status: int) -> Response:
    """일관된 에러 응답 포맷 반환"""

    return Response({"detail": message, "code": code}, status=http_status)


def _normalize_ui_mode(raw: str | None) -> str:
    # OAuth 콜백 응답 모드(web/api) 정규화
    return "web" if (raw or "").lower() == "web" else "api"


def _resolve_next_url(request: Request, raw: str | None) -> str:
    """
    OAuth redirect URL 검증 및 정제
    Django의 url_has_allowed_host_and_scheme를 사용하여 open-redirect 방지
    """
    from django.conf import settings

    # 환경변수에서 프론트엔드 URL 가져오기 (기본값: localhost:5173)
    default = os.getenv('FRONTEND_BASE_URL', 'http://localhost:5173')

    if not raw:
        return default

    # 허용된 호스트 목록 (CORS + ALLOWED_HOSTS)
    allowed_hosts = set()

    # CORS_ALLOWED_ORIGINS에서 호스트 추출
    cors_origins = getattr(settings, 'CORS_ALLOWED_ORIGINS', [])
    for origin in cors_origins:
        # http://localhost:5173 -> localhost:5173
        host = origin.replace('http://', '').replace('https://', '')
        allowed_hosts.add(host)

    # ALLOWED_HOSTS 추가
    allowed_hosts.update(settings.ALLOWED_HOSTS)

    # 개발 환경용 추가 호스트
    if settings.DEBUG:
        allowed_hosts.update(['localhost:3000', 'localhost:5173', '127.0.0.1:3000', '127.0.0.1:5173'])

    # url_has_allowed_host_and_scheme로 검증
    if url_has_allowed_host_and_scheme(raw, allowed_hosts=allowed_hosts, require_https=False if settings.DEBUG else True):
        return raw

    # 검증 실패 시 기본 URL 반환
    logger.warning(f"OAuth redirect URL rejected: {raw}")
    return default


def _oauth_response(request: Request, user, tokens: Dict[str, str], ui_mode: str, next_url: str):
    """OAuth 로그인 뒤 응답 생성
    
    ui_mode가 "web"인 경우 프론트엔드로 리다이렉트하면서 토큰을 URL 파라미터로 전달
    ui_mode가 "api"인 경우 JSON 응답 반환
    """
    user_data = UserSerializer(user).data
    
    if ui_mode == "web":
        # 프론트엔드로 리다이렉트하면서 토큰 전달
        # 보안상 URL에 토큰을 포함하는 것은 좋지 않지만, SPA 환경에서는 필요
        # 프로덕션에서는 세션 기반 또는 별도 엔드포인트 사용 권장
        from urllib.parse import urlencode
        params = {
            "access_token": tokens["access"],
            "refresh_token": tokens["refresh"],
            "user": json.dumps(user_data, ensure_ascii=False),
        }
        redirect_url = f"{next_url}?{urlencode(params)}"
        return HttpResponseRedirect(redirect_url)
    
    # API 모드: JSON 응답 반환
    return Response(
        {
            "access": tokens["access"],
            "refresh": tokens["refresh"],
            "user": user_data,
        }
    )



# ----- 기본 인증 -----


class RegisterView(generics.CreateAPIView):
    """POST /auth/register/ - 일반 회원가입
    
    회원가입은 누구나 가능해야 하므로 AllowAny 권한 사용
    """

    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer

    def create(self, request: Request, *args, **kwargs):
        """회원가입 처리
        
        이메일 발송 실패 시에도 PendingRegistration은 생성되므로,
        사용자는 나중에 인증 코드를 다시 요청할 수 있습니다.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # serializer.save()에서 이메일 발송 시도
        # 이메일 발송 실패 시 EmailDeliveryError 발생 (serializer에서 처리)
        pending = serializer.save()
        
        data = {
            "email": pending.email,
            "detail": "인증 메일을 발송했습니다.",
            "expires_at": pending.expires_at.isoformat(),
        }
        
        # 개발 환경에서 console 백엔드 사용 시 인증 코드도 응답에 포함 (선택사항)
        from django.conf import settings
        email_backend = getattr(settings, "EMAIL_BACKEND", "")
        if email_backend == "django.core.mail.backends.console.EmailBackend":
            # 실제 서비스에서는 인증 코드를 메일로만 전달하고,
            # 개발 환경에서만 응답에 포함하여 테스트 편의성만 제공
            data["verification_code"] = pending.verification_code
        
        return Response(data, status=status.HTTP_201_CREATED)


class EmailVerificationConfirmView(APIView):
    """POST /auth/register/verify/ - 회원가입 이메일 인증 번호 확인"""

    permission_classes = [permissions.AllowAny]

    def post(self, request: Request):
        serializer = EmailVerificationConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        code = serializer.validated_data["code"]

        # 신규 플로우: PendingRegistration 기반 처리
        with transaction.atomic():
            pending = (
                PendingRegistration.objects.select_for_update()
                .filter(email=email)
                .first()
            )
            if pending:
                if pending.expires_at < timezone.now():
                    pending.delete()
                    return error_response(
                        "인증번호가 만료되었습니다. 다시 회원가입을 진행해주세요.",
                        "verification_expired",
                        status.HTTP_400_BAD_REQUEST,
                    )
                if pending.verification_code != code:
                    return error_response(
                        "인증번호가 일치하지 않습니다.",
                        "invalid_verification_code",
                        status.HTTP_400_BAD_REQUEST,
                    )
                finalize_pending_registration(pending)
                return Response({"detail": "이메일 인증이 완료되었습니다."}, status=status.HTTP_200_OK)

        # 레거시 호환 (이미 User 레코드가 존재하는 경우)
        User = get_user_model()
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return error_response(
                "해당 이메일의 가입 대기 내역을 찾을 수 없습니다.",
                "user_not_found",
                status.HTTP_400_BAD_REQUEST,
            )

        if getattr(user, "is_email_verified", False):
            return Response(
                {"detail": "이미 이메일 인증이 완료된 계정입니다."},
                status=status.HTTP_200_OK,
            )

        if not getattr(user, "email_verification_code", None) or getattr(user, "email_verification_code", None) != code:
            return error_response(
                "인증번호가 일치하지 않습니다.",
                "invalid_verification_code",
                status.HTTP_400_BAD_REQUEST,
            )

        user.is_email_verified = True
        user.email_verification_code = None
        user.save(update_fields=["is_email_verified", "email_verification_code"])

        return Response({"detail": "이메일 인증이 완료되었습니다."}, status=status.HTTP_200_OK)


class LoginView(APIView):
    """POST /auth/login/ - 이메일/비밀번호 로그인(JWT 반환)"""

    permission_classes = [permissions.AllowAny]

    def post(self, request: Request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]

        # 일반 이메일 로그인 시 role이 guest인 경우 user로 업데이트
        # (기존에 회원가입했지만 role이 제대로 설정되지 않은 경우 대비)
        if user.role == "guest":
            user.role = "user"
            user.save(update_fields=["role"])

        tokens = issue_tokens_with_claims(user)

        return Response(
            {
                "access": tokens["access"],
                "refresh": tokens["refresh"],
                "user": UserSerializer(user).data,
            }
        )


class LogoutView(APIView):
    """POST /auth/logout/ - 로그아웃 (리프레시 토큰 블랙리스트)"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request: Request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return error_response("리프레시 토큰이 필요합니다.", "missing_refresh", status.HTTP_400_BAD_REQUEST)
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()  # token_blacklist 앱 필요
        except TokenError:
            return error_response("유효하지 않은 리프레시 토큰입니다.", "invalid_token", status.HTTP_400_BAD_REQUEST)
        return Response({"detail": "로그아웃되었습니다."}, status=status.HTTP_205_RESET_CONTENT)


class TokenRefreshView(SimpleJWTTokenRefreshView):
    """POST /auth/token/refresh/ - JWT 토큰 갱신
    
    토큰 갱신 시 User가 존재하지 않을 경우 적절히 처리
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request: Request, *args, **kwargs):
        """토큰 갱신 처리 (User 존재 여부 확인)"""
        try:
            return super().post(request, *args, **kwargs)
        except Exception as exc:
            # User.DoesNotExist 또는 기타 에러 처리
            error_msg = str(exc).lower()
            if "does not exist" in error_msg or "matching query" in error_msg:
                # 토큰은 유효하지만 User가 존재하지 않는 경우
                logger.warning(f"토큰 갱신 실패: User가 존재하지 않음 - {request.data.get('refresh', '')[:20]}...")
                return error_response(
                    "토큰이 유효하지 않거나 사용자가 존재하지 않습니다. 다시 로그인해주세요.",
                    "user_not_found",
                    status.HTTP_401_UNAUTHORIZED
                )
            # 다른 에러는 상위 클래스에서 처리
            raise


class UserMeView(APIView):
    """GET/PATCH /auth/user/ - 현재 사용자 조회/수정"""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request: Request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request: Request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class PasswordChangeView(APIView):
    """POST /auth/password/change/ - 비밀번호 변경"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request: Request):
        serializer = PasswordChangeSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = request.user
        new_password = serializer.validated_data["new_password"]

        cred = getattr(user, "email_credential", None)
        if cred is None:
            cred = AuthEmailCredential(user=user, is_email_verified=True)
        cred.password_hash = make_password(new_password)
        cred.save()

        user.set_unusable_password()
        user.save(update_fields=["password"])
        # 보안: 기존 리프레시 토큰 일괄 폐기 (글로벌 로그아웃 효과)
        try:
            revoked = revoke_all_refresh_tokens(user)
            return Response({"detail": "비밀번호가 변경되었습니다.", "revoked_refresh": revoked})
        except Exception:
            # token_blacklist 미구성 환경에서는 무시
            return Response({"detail": "비밀번호가 변경되었습니다."})


class AccountDeleteView(APIView):
    """DELETE /auth/account/ - 계정 삭제 (Soft Delete)

    계정 삭제 시 처리 순서:
    1. 본인 확인 (비밀번호 또는 OAuth 확인)
    2. 판매자인 경우 활성 상품/미완료 주문 검증
    3. 구매자 미완료 주문 검증
    4. Soft Delete 처리 (deleted_at 설정, is_active=False)
    5. 관련 데이터 정리 (장바구니, 찜, 토큰 등)
    6. 주문 이력은 보존 (Order.user → RESTRICT 정책)

    복구 불가능한 정보:
    - 장바구니, 찜 목록, 팔로우
    - 인증 정보 (이메일 자격증명, OAuth 연결)
    - 배송지, 결제수단

    보존되는 정보:
    - 주문 이력 (user FK는 유지되나 계정 비활성화)
    - 리뷰 (작성자 정보는 익명화)
    """

    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request: Request):
        """계정 삭제 처리"""
        serializer = AccountDeleteSerializer(
            data=request.data,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        user = request.user
        reason = serializer.validated_data.get("reason", "")

        with transaction.atomic():
            # 1. 모든 리프레시 토큰 폐기
            try:
                revoke_all_refresh_tokens(user)
            except Exception:
                pass  # token_blacklist 미구성 환경에서는 무시

            # 2. 장바구니 삭제
            from products.models import Cart
            Cart.objects.filter(user=user).delete()

            # 3. 찜 목록 삭제 + ProductStats.wishlist_count 감소
            from products.models import Wishlist, ProductStats
            from django.db.models import F

            # 찜한 상품 ID 목록 조회
            wishlisted_product_ids = list(
                Wishlist.objects.filter(user=user).values_list('product_id', flat=True)
            )

            if wishlisted_product_ids:
                # 각 상품의 wishlist_count 감소 (음수 방지)
                for product_id in wishlisted_product_ids:
                    ProductStats.objects.filter(
                        product_id=product_id,
                        wishlist_count__gt=0
                    ).update(wishlist_count=F('wishlist_count') - 1)

            # 찜 목록 삭제
            Wishlist.objects.filter(user=user).delete()

            # 4. 판매자 팔로우 삭제
            from products.models import SellerFollow
            SellerFollow.objects.filter(user=user).delete()

            # 5. 사용자별 상품 통계 삭제
            from products.models import UserProductStats
            UserProductStats.objects.filter(user=user).delete()

            # 6. 인증 정보 삭제 (OAuth 연결 해제)
            AuthGoogleAccount.objects.filter(user=user).delete()
            AuthKakaoAccount.objects.filter(user=user).delete()
            AuthEmailCredential.objects.filter(user=user).delete()

            # 7. 배송지, 결제수단 삭제
            UserAddress.objects.filter(user=user).delete()
            UserPaymentMethod.objects.filter(user=user).delete()

            # 8. 판매자 프로필 처리 (있는 경우)
            if hasattr(user, 'seller_profile') and user.seller_profile:
                seller = user.seller_profile
                # 상품들을 단종 상태로 변경
                from products.models import Product, ProductStatus
                Product.objects.filter(seller=seller).update(
                    status=ProductStatus.DISCONTINUED
                )
                # 판매자 상태를 비활성으로 변경
                from sellers.models import SellerStatus
                seller.status = SellerStatus.INACTIVE
                seller.save(update_fields=['status', 'updated_at'])

            # 9. 리뷰 익명화 처리 (리뷰 자체는 보존)
            from products.models import Review
            Review.objects.filter(user=user).update(
                status='hidden'  # 숨김 처리 (필요시 삭제로 변경 가능)
            )

            # 10. 사용자 Soft Delete 처리
            user.is_active = False
            user.deleted_at = timezone.now()
            # 이메일/username 충돌 방지를 위해 값 변경
            deleted_suffix = f"_deleted_{user.id}"
            user.email = f"{user.email}{deleted_suffix}"
            user.username = f"{user.username}{deleted_suffix}"
            user.save(update_fields=[
                'is_active', 'deleted_at', 'email', 'username'
            ])

            logger.info(
                f"계정 삭제 완료: user_id={user.id}, "
                f"reason={reason[:100] if reason else 'N/A'}"
            )

        return Response({
            "detail": "계정이 삭제되었습니다. 그동안 이용해 주셔서 감사합니다.",
            "deleted_at": user.deleted_at.isoformat()
        }, status=status.HTTP_200_OK)

    def get(self, request: Request):
        """DELETE 전 계정 삭제 가능 여부 조회

        프론트엔드에서 삭제 버튼 클릭 전에 호출하여
        삭제 가능 여부와 필요한 조건을 확인할 수 있습니다.
        """
        user = request.user
        result = {
            "can_delete": True,
            "blockers": [],
            "auth_method": None,
            "is_seller": False,
        }

        # 인증 방법 확인
        has_email_credential = hasattr(user, 'email_credential') and user.email_credential
        has_google = hasattr(user, 'google_accounts') and user.google_accounts.exists()
        has_kakao = hasattr(user, 'kakao_accounts') and user.kakao_accounts.exists()

        if has_email_credential:
            result["auth_method"] = "email"
        elif has_google:
            result["auth_method"] = "google"
        elif has_kakao:
            result["auth_method"] = "kakao"
        else:
            result["auth_method"] = "unknown"

        # 판매자 여부 확인
        if hasattr(user, 'seller_profile') and user.seller_profile:
            result["is_seller"] = True
            seller = user.seller_profile

            # 활성 상품 확인
            from products.models import Product, ProductStatus
            active_products = Product.objects.filter(
                seller=seller,
                status__in=[ProductStatus.ACTIVE, ProductStatus.OUT_OF_STOCK]
            ).count()

            if active_products > 0:
                result["can_delete"] = False
                result["blockers"].append({
                    "type": "active_products",
                    "count": active_products,
                    "message": f"활성 상품 {active_products}개를 비공개 처리해야 합니다."
                })

            # 판매자 미완료 주문 확인
            from orders.models import OrderItem, OrderItemStatus
            seller_incomplete = OrderItem.objects.filter(
                seller=seller,
                status__in=[
                    OrderItemStatus.PENDING,
                    OrderItemStatus.PAID,
                    OrderItemStatus.SHIPPING
                ]
            ).count()

            if seller_incomplete > 0:
                result["can_delete"] = False
                result["blockers"].append({
                    "type": "seller_orders",
                    "count": seller_incomplete,
                    "message": f"처리 중인 판매 주문 {seller_incomplete}건을 완료해야 합니다."
                })

        # 구매자 미완료 주문 확인
        from orders.models import Order, OrderStatus
        user_incomplete = Order.objects.filter(
            user=user,
            status__in=[
                OrderStatus.PENDING,
                OrderStatus.PAID,
                OrderStatus.PROCESSING,
                OrderStatus.SHIPPED
            ]
        ).count()

        if user_incomplete > 0:
            result["can_delete"] = False
            result["blockers"].append({
                "type": "user_orders",
                "count": user_incomplete,
                "message": f"처리 중인 주문 {user_incomplete}건의 배송이 완료되어야 합니다."
            })

        return Response(result)


class PasswordResetRequestView(APIView):
    """POST /auth/password/reset/ - 비밀번호 재설정 요청"""

    permission_classes = [permissions.AllowAny]

    def post(self, request: Request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        User = get_user_model()
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # 존재하지 않는 이메일도 보안상 동일 응답
            return Response({"detail": "비밀번호 재설정 안내를 발송했습니다."})

        token_gen = PasswordResetTokenGenerator()
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        token = token_gen.make_token(user)

        reset_url = request.build_absolute_uri(f"/auth/password/reset/confirm/?uid={uidb64}&token={token}")

        # 메일 발송 (환경에 따라 설정)
        subject = "비밀번호 재설정 안내"
        message = f"아래 링크를 통해 비밀번호를 재설정하세요:\n{reset_url}"
        try:
            send_mail(subject, message, getattr(settings, "DEFAULT_FROM_EMAIL", None), [email], fail_silently=True)
        except Exception as e:  # pragma: no cover - 발송 실패는 무시하고 로그만
            logger.debug("비밀번호 재설정 메일 발송 실패: %s", e)

        resp: Dict[str, Any] = {"detail": "비밀번호 재설정 안내를 발송했습니다."}
        if AUTH_CONFIG.get("PASSWORD_RESET_RETURN_TOKEN_IN_RESPONSE"):
            # 개발 환경용: 토큰을 응답으로도 전달 (운영 비권장)
            resp.update({"uid": uidb64, "token": token, "reset_url": reset_url})
        return Response(resp)


class PasswordResetConfirmView(APIView):
    """POST /auth/password/reset/confirm/ - 비밀번호 재설정 확인"""

    permission_classes = [permissions.AllowAny]

    def post(self, request: Request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        uidb64 = serializer.validated_data["uid"]
        token = serializer.validated_data["token"]
        new_password = serializer.validated_data["new_password"]

        User = get_user_model()
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except Exception:
            return error_response("유효하지 않은 요청입니다.", "invalid_uid", status.HTTP_400_BAD_REQUEST)

        token_gen = PasswordResetTokenGenerator()
        if not token_gen.check_token(user, token):
            return error_response("토큰이 유효하지 않거나 만료되었습니다.", "invalid_token", status.HTTP_400_BAD_REQUEST)

        cred = getattr(user, "email_credential", None)
        if cred is None:
            cred = AuthEmailCredential(user=user, is_email_verified=True)
        cred.password_hash = make_password(new_password)
        cred.save()

        user.set_unusable_password()
        user.save(update_fields=["password"])
        try:
            revoked = revoke_all_refresh_tokens(user)
            return Response({"detail": "비밀번호가 재설정되었습니다.", "revoked_refresh": revoked})
        except Exception:
            return Response({"detail": "비밀번호가 재설정되었습니다."})


# ----- OAuth2: Google -----


class GoogleLoginRedirectView(APIView):
    """GET /auth/google/ - 구글 로그인 리다이렉트 URL 생성 및 이동"""

    permission_classes = [permissions.AllowAny]

    def get(self, request: Request):
        ui_mode = _normalize_ui_mode(request.GET.get("ui"))
        next_url = _resolve_next_url(request, request.GET.get("next"))
        url, state = build_google_authorize_url(request)
        request.session["oauth_state_google"] = {
            "value": state,
            "ui": ui_mode,
            "next": next_url,
        }
        return HttpResponseRedirect(url)


class GoogleCallbackView(APIView):
    """GET /auth/google/callback/ - 구글 콜백 처리, 사용자 생성/병합, JWT 반환"""

    permission_classes = [permissions.AllowAny]

    def get(self, request: Request):
        state = request.GET.get("state")
        code = request.GET.get("code")
        if not state or not code:
            return error_response("요청 매개변수가 부족합니다.", "missing_params", status.HTTP_400_BAD_REQUEST)

        stored_meta = request.session.pop("oauth_state_google", None)
        saved_state = None
        ui_mode = "api"
        next_url = "/mypage/"
        if isinstance(stored_meta, dict):
            saved_state = stored_meta.get("value")
            ui_mode = _normalize_ui_mode(stored_meta.get("ui"))
            next_url = stored_meta.get("next") or next_url
        else:
            saved_state = stored_meta
        if saved_state != state:
            return error_response("state 검증에 실패했습니다.", "invalid_state", status.HTTP_400_BAD_REQUEST)

        next_url = _resolve_next_url(request, next_url)

        data = exchange_google_token(request, code)
        profile = data["profile"]
        email = profile.get("email")
        sub = profile.get("sub")  # Google 고유 ID
        picture = profile.get("picture")
        name = profile.get("name")

        if not email:
            return error_response("이메일을 확인할 수 없습니다.", "email_required", status.HTTP_400_BAD_REQUEST)

        User = get_user_model()

        # ERD V2.1: Google 계정으로 먼저 검색
        google_account = AuthGoogleAccount.objects.filter(google_user_id=str(sub)).first()
        if google_account:
            user = google_account.user
        else:
            # 이메일로 기존 사용자 검색
            user = User.objects.filter(email=email).first()

        if user is None:
            # 신규 사용자 생성 (ERD V2.1)
            with transaction.atomic():
                user = User.objects.create(
                    email=email,
                    username=email.split("@")[0],
                    role="user",  # OAuth 로그인 시 일반 회원 권한 부여
                )
                # UserProfile 업데이트 (signal에서 자동 생성됨)
                profile, _ = UserProfile.objects.get_or_create(user=user)
                if picture:
                    profile.profile_image_url = picture
                    profile.save(update_fields=["profile_image_url"])
                # AuthGoogleAccount 생성
                AuthGoogleAccount.objects.create(
                    user=user,
                    google_user_id=str(sub),
                    email=email,
                )
        else:
            # 기존 사용자: Google 계정 연결 확인 및 업데이트
            with transaction.atomic():
                # Google 계정 연결이 없으면 생성
                if not AuthGoogleAccount.objects.filter(user=user, google_user_id=str(sub)).exists():
                    AuthGoogleAccount.objects.create(
                        user=user,
                        google_user_id=str(sub),
                        email=email,
                    )
                # UserProfile 업데이트 (프로필 이미지)
                profile, _ = UserProfile.objects.get_or_create(user=user)
                if picture and profile.profile_image_url != picture:
                    profile.profile_image_url = picture
                    profile.save(update_fields=["profile_image_url"])
                # role이 guest인 경우 user로 업데이트 (OAuth 로그인은 일반 회원)
                if user.role == "guest":
                    user.role = "user"
                    user.save(update_fields=["role"])

        tokens = issue_tokens_with_claims(user)
        return _oauth_response(request, user, tokens, ui_mode, next_url)


# ----- OAuth2: Kakao -----


class KakaoLoginRedirectView(APIView):
    """GET /auth/kakao/ - 카카오 로그인 리다이렉트 URL 생성 및 이동"""

    permission_classes = [permissions.AllowAny]

    def get(self, request: Request):
        ui_mode = _normalize_ui_mode(request.GET.get("ui"))
        next_url = _resolve_next_url(request, request.GET.get("next"))
        url, state = build_kakao_authorize_url(request)
        request.session["oauth_state_kakao"] = {
            "value": state,
            "ui": ui_mode,
            "next": next_url,
        }
        return HttpResponseRedirect(url)


class KakaoCallbackView(APIView):
    """GET /auth/kakao/callback/ - 카카오 콜백 처리, 사용자 생성/병합, JWT 반환"""

    permission_classes = [permissions.AllowAny]

    def get(self, request: Request):
        state = request.GET.get("state")
        code = request.GET.get("code")
        if not state or not code:
            return error_response("요청 매개변수가 부족합니다.", "missing_params", status.HTTP_400_BAD_REQUEST)

        stored_meta = request.session.pop("oauth_state_kakao", None)
        saved_state = None
        ui_mode = "api"
        next_url = "/mypage/"
        if isinstance(stored_meta, dict):
            saved_state = stored_meta.get("value")
            ui_mode = _normalize_ui_mode(stored_meta.get("ui"))
            next_url = stored_meta.get("next") or next_url
        else:
            saved_state = stored_meta
        if saved_state != state:
            return error_response("state 검증에 실패했습니다.", "invalid_state", status.HTTP_400_BAD_REQUEST)

        next_url = _resolve_next_url(request, next_url)

        data = exchange_kakao_token(request, code)
        profile = data["profile"]
        email = profile.get("email")  # 카카?�에???�메??미제�???None ?????�음
        kakao_id = profile.get("id")
        picture = profile.get("picture")
        name = profile.get("name")

        if not kakao_id:
            return error_response("사용자 식별값을 확인할 수 없습니다.", "id_required", status.HTTP_400_BAD_REQUEST)

        User = get_user_model()

        # ERD V2.1: Kakao 계정으로 먼저 검색
        kakao_account = AuthKakaoAccount.objects.filter(kakao_user_id=str(kakao_id)).first()
        if kakao_account:
            user = kakao_account.user
        elif email:
            # 이메일로 기존 사용자 검색
            user = User.objects.filter(email=email).first()
        else:
            user = None

        if user is None:
            # 신규 사용자 생성 (ERD V2.1)
            with transaction.atomic():
                username = (email or f"kakao_{kakao_id}").split("@")[0] if email else f"kakao_{kakao_id}"
                user = User.objects.create(
                    email=email or f"kakao_{kakao_id}@example.com",
                    username=username,
                    role="user",  # OAuth 로그인 시 일반 회원 권한 부여
                )
                # UserProfile 업데이트 (signal에서 자동 생성됨)
                profile, _ = UserProfile.objects.get_or_create(user=user)
                if picture:
                    profile.profile_image_url = picture
                    profile.save(update_fields=["profile_image_url"])
                # AuthKakaoAccount 생성
                AuthKakaoAccount.objects.create(
                    user=user,
                    kakao_user_id=str(kakao_id),
                    email=email or f"kakao_{kakao_id}@example.com",
                )
        else:
            # 기존 사용자: Kakao 계정 연결 확인 및 업데이트
            with transaction.atomic():
                # Kakao 계정 연결이 없으면 생성
                if not AuthKakaoAccount.objects.filter(user=user, kakao_user_id=str(kakao_id)).exists():
                    AuthKakaoAccount.objects.create(
                        user=user,
                        kakao_user_id=str(kakao_id),
                        email=email or f"kakao_{kakao_id}@example.com",
                    )
                # UserProfile 업데이트 (프로필 이미지)
                profile, _ = UserProfile.objects.get_or_create(user=user)
                if picture and profile.profile_image_url != picture:
                    profile.profile_image_url = picture
                    profile.save(update_fields=["profile_image_url"])
                # role이 guest인 경우 user로 업데이트 (OAuth 로그인은 일반 회원)
                if user.role == "guest":
                    user.role = "user"
                    user.save(update_fields=["role"])

        tokens = issue_tokens_with_claims(user)
        return _oauth_response(request, user, tokens, ui_mode, next_url)


class UserAddressViewSet(viewsets.ModelViewSet):
    """사용자 배송지 관리 ViewSet

    API 엔드포인트:
    - GET /api/users/me/addresses/ - 배송지 목록 조회
    - POST /api/users/me/addresses/ - 배송지 추가
    - GET /api/users/me/addresses/{id}/ - 배송지 상세 조회
    - PATCH /api/users/me/addresses/{id}/ - 배송지 수정
    - DELETE /api/users/me/addresses/{id}/ - 배송지 삭제
    - POST /api/users/me/addresses/{id}/set-default/ - 기본 배송지 설정
    """

    serializer_class = UserAddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """현재 사용자의 배송지만 조회 (기본 배송지 우선, 최신순)"""
        return UserAddress.objects.filter(user=self.request.user).order_by('-is_default', '-created_at')

    def perform_create(self, serializer):
        """배송지 생성 시 현재 사용자 자동 설정"""
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'], url_path='set-default', url_name='set-default')
    def set_default(self, request, pk=None):
        """배송지를 기본 배송지로 설정

        POST /api/users/me/addresses/{id}/set-default/
        """
        address = self.get_object()

        # 기존 기본 배송지 해제
        UserAddress.objects.filter(user=request.user).update(is_default=False)

        # 선택한 배송지를 기본으로 설정
        address.is_default = True
        address.save()

        serializer = self.get_serializer(address)
        return Response(serializer.data)


class UserPaymentMethodViewSet(viewsets.ModelViewSet):
    """사용자 결제 수단 관리 ViewSet (MVP: 저장만, 실제 결제 연동은 나중)"""

    serializer_class = UserPaymentMethodSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """현재 사용자의 결제 수단만 조회"""
        return UserPaymentMethod.objects.filter(user=self.request.user).order_by('-is_default', '-created_at')

    def perform_create(self, serializer):
        """결제 수단 생성 시 현재 사용자 자동 설정"""
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        """결제 수단을 기본 결제 수단으로 설정"""
        payment_method = self.get_object()

        # 기존 기본 결제 수단 해제
        UserPaymentMethod.objects.filter(user=request.user).update(is_default=False)

        # 선택한 결제 수단을 기본으로 설정
        payment_method.is_default = True
        payment_method.save()

        serializer = self.get_serializer(payment_method)
        return Response(serializer.data)
