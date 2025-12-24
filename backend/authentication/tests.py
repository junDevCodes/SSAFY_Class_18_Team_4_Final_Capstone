"""
# ========================= 인증 모듈 공식 테스트 =========================
# 기본 가입/검증/로그인 플로우와 OAuth 콜백의 HTML/JSON 응답을 검증한다.
# ========================================================================
"""

from __future__ import annotations

from datetime import timedelta
import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from unittest.mock import patch

from .models import PendingRegistration


class AuthAPITest(APITestCase):
    """이메일 인증 기반 가입/로그인 흐름 검증"""

    def test_이메일_가입부터_로그인까지_정상동작(self):
        """회원가입→이메일검증→로그인→마이페이지 조회까지 진행"""

        email = "tester@example.com"
        password = "ValidPassw0rd!"

        res = self.client.post(
            reverse("authentication:register"),
            {"email": email, "password": password},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["email"], email)

        User = get_user_model()
        self.assertFalse(User.objects.filter(email=email).exists())
        pending = PendingRegistration.objects.get(email=email)
        self.assertIsNotNone(pending.verification_code)

        res = self.client.post(
            reverse("authentication:login"),
            {"email": email, "password": password},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

        verification_code = pending.verification_code
        res = self.client.post(
            reverse("authentication:register_verify"),
            {"email": email, "code": verification_code},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.assertFalse(PendingRegistration.objects.filter(email=email).exists())

        user = User.objects.get(email=email)
        # ERD V2.1: is_email_verified는 AuthEmailCredential에 저장
        self.assertTrue(hasattr(user, 'email_credential'))
        self.assertTrue(user.email_credential.is_email_verified)

        res = self.client.post(
            reverse("authentication:login"),
            {"email": email, "password": password},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        access = res.data["access"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        res = self.client.get(reverse("authentication:user_me"))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["email"], email)

        decoded = jwt.decode(access, options={"verify_signature": False})
        self.assertIn("role", decoded)
        self.assertIn(decoded["role"], ["guest", "user", "seller", "admin"])

    def test_재가입요청시_대기정보와코드가_갱신된다(self):
        email = "dup@example.com"
        first = self.client.post(
            reverse("authentication:register"),
            {"email": email, "password": "ValidPassw0rd!"},
            format="json",
        )
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        pending = PendingRegistration.objects.get(email=email)
        old_code = pending.verification_code
        old_hash = pending.password_hash

        second = self.client.post(
            reverse("authentication:register"),
            {"email": email, "password": "NewValidPassw0rd!"},
            format="json",
        )
        self.assertEqual(second.status_code, status.HTTP_201_CREATED)

        pending.refresh_from_db()
        self.assertNotEqual(old_code, pending.verification_code)
        self.assertNotEqual(old_hash, pending.password_hash)

    def test_만료된_코드는_삭제되고_오류를반환한다(self):
        email = "expire@example.com"
        self.client.post(
            reverse("authentication:register"),
            {"email": email, "password": "ValidPassw0rd!"},
            format="json",
        )
        pending = PendingRegistration.objects.get(email=email)
        pending.expires_at = timezone.now() - timedelta(minutes=1)
        pending.save(update_fields=["expires_at"])

        res = self.client.post(
            reverse("authentication:register_verify"),
            {"email": email, "code": pending.verification_code},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(PendingRegistration.objects.filter(email=email).exists())


class OAuthCallbackViewTest(APITestCase):
    """OAuth 콜백 응답 모드(웹/JSON) 검증"""

    @patch("authentication.views.exchange_google_token")
    def test_google_callback_web렌더링(self, mock_exchange):
        """UI=web 흐름이면 프론트엔드로 리다이렉트하면서 토큰을 URL 파라미터로 전달해야 한다"""

        mock_exchange.return_value = {
            "profile": {
                "email": "oauth-web@example.com",
                "sub": "sub-web",
                "picture": "https://example.com/web.png",
                "name": "OAuth Web",
            }
        }

        session = self.client.session
        session["oauth_state_google"] = {"value": "state-web", "ui": "web", "next": "/mypage/"}
        session.save()

        url = reverse("authentication:google_callback")
        response = self.client.get(f"{url}?state=state-web&code=dummy", HTTP_ACCEPT="text/html")

        # 302 리다이렉트이어야 하고, Location 에 토큰과 사용자 정보가 쿼리로 포함되어야 한다
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        redirect_url = response["Location"]

        # 리다이렉트 경로가 /mypage/ 인지 확인
        from urllib.parse import urlparse, parse_qs

        parsed = urlparse(redirect_url)
        self.assertEqual(parsed.path, "/mypage/")

        # 쿼리 파라미터에 access_token, refresh_token, user 가 포함되어야 한다
        qs = parse_qs(parsed.query)
        self.assertIn("access_token", qs)
        self.assertIn("refresh_token", qs)
        self.assertIn("user", qs)
        # user 파라미터에 이메일 정보가 포함되어야 한다
        self.assertIn("oauth-web@example.com", qs["user"][0])

    @patch("authentication.views.exchange_google_token")
    def test_google_callback_json응답(self, mock_exchange):
        """UI=api 흐름이면 JSON 페이로드를 반환"""

        mock_exchange.return_value = {
            "profile": {
                "email": "oauth-api@example.com",
                "sub": "sub-api",
                "picture": "https://example.com/api.png",
                "name": "OAuth API",
            }
        }

        session = self.client.session
        session["oauth_state_google"] = {"value": "state-api", "ui": "api", "next": "/"}
        session.save()

        url = reverse("authentication:google_callback")
        response = self.client.get(f"{url}?state=state-api&code=dummy", HTTP_ACCEPT="application/json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user"]["email"], "oauth-api@example.com")
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)


class AdminUserApiTests(APITestCase):
    """관리자용 유저 목록/상세 API 테스트"""

    def setUp(self) -> None:
        """관리자와 일반 사용자 생성"""
        User = get_user_model()
        self.admin = User.objects.create_user(
            email="admin-api@example.com",
            password="AdminPassw0rd!",
            username="admin-api",
            role="admin",
            is_staff=True,
        )
        self.user1 = User.objects.create_user(
            email="user1@example.com",
            password="UserPassw0rd1!",
            username="user1",
            role="user",
        )
        self.user2 = User.objects.create_user(
            email="user2@example.com",
            password="UserPassw0rd2!",
            username="user2",
            role="user",
            is_active=False,
        )

    def test_admin_can_list_users(self):
        """관리자는 유저 목록을 조회할 수 있어야 한다"""
        self.client.force_authenticate(user=self.admin)
        res = self.client.get("/api/admin/users/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(res.data), 3)
        first = res.data[0]
        self.assertIn("email", first)
        self.assertIn("username", first)
        self.assertIn("role", first)
        self.assertIn("is_active", first)

    def test_non_admin_forbidden(self):
        """일반 사용자는 Admin 유저 API에 접근할 수 없어야 한다"""
        self.client.force_authenticate(user=self.user1)
        res = self.client.get("/api/admin/users/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)