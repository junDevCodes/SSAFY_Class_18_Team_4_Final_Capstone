# Authentication 모듈 안내

`authentication/` 폴더는 Django 5 + DRF + SimpleJWT 기반의 모듈형 인증 패키지입니다. 이메일 기반 회원가입(이메일 인증), 비밀번호 관리, JWT 로그인, Google/Kakao OAuth2, 권한(Role) 검증, PendingRegistration 기반 대기 로직을 모두 포함하며 **폴더만 복사해도 다른 Django 프로젝트에서 즉시 사용**할 수 있습니다.

---

## 1. 필수 패키지

루트의 `requirements.txt` 를 사용하거나 다음 패키지를 설치하세요.

```bash
pip install -r requirements.txt
# 또는
pip install Django djangorestframework \
    djangorestframework_simplejwt django-allauth \
    requests python-dotenv
```

추가적으로 `django-cors-headers`, `drf-spectacular` 등은 선택사항입니다.

---

## 2. settings.py 연결

```python
INSTALLED_APPS += [
    'django.contrib.sites',
    'rest_framework',
    'rest_framework_simplejwt.token_blacklist',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'authentication',
]

AUTH_USER_MODEL = 'authentication.User'
SITE_ID = 1

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': ('rest_framework.permissions.AllowAny',),
}

from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'authentication.backends.EmailAuthBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
)
```

`.env` 는 `python-dotenv` 로 로드하고, 이메일 설정은 루트 `README.md` / `.env.example` / `PORTING_GUIDE.md` 를 참고하세요.

---

## 3. .env 템플릿

`authentication/PORTING_GUIDE.md` 와 루트 `.env.example` 에 상세 템플릿이 있습니다. 핵심 값은 다음과 같습니다.

```bash
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=example@gmail.com
EMAIL_HOST_PASSWORD=앱비밀번호16자리
EMAIL_VERIFICATION_FROM_EMAIL=example@gmail.com
EMAIL_VERIFICATION_CODE_LENGTH=6
EMAIL_VERIFICATION_EXPIRES_MINUTES=30

DEFAULT_ROLE=guest  # guest: 비회원, user: 일반회원, seller: 판매자, admin: 관리자
ADMIN_EMAIL_WHITELIST=admin@example.com
PASSWORD_RESET_RETURN_TOKEN_IN_RESPONSE=false

GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
KAKAO_REST_API_KEY=...
KAKAO_CLIENT_SECRET=
```

**주의:** Gmail SMTP는 일반 비밀번호가 아니라 앱 비밀번호(16자리)를 사용해야 합니다.

---

## 4. URL 및 마이그레이션

```python
from django.urls import include, path

urlpatterns = [
    path('', include('authentication.urls', namespace='authentication')),
]
```

```bash
python manage.py makemigrations authentication
python manage.py migrate
```

이 과정에서 `authentication_user`, `authentication_pendingregistration` 테이블이 생성됩니다.

---

## 5. 제공 API 요약

| 구분 | 엔드포인트 |
| --- | --- |
| 회원가입 | `POST /auth/register/` → PendingRegistration 생성 & 메일 발송 |
| 이메일 인증 | `POST /auth/register/verify/` |
| 로그인/로그아웃 | `POST /auth/login/`, `POST /auth/logout/`, `POST /auth/token/refresh/` |
| 프로필 | `GET/PATCH /auth/user/` |
| 비밀번호 | `POST /auth/password/change/`, `POST /auth/password/reset/`, `/auth/password/reset/confirm/` |
| OAuth2 | `GET /auth/google/`, `/auth/google/callback/`, `/auth/kakao/`, `/auth/kakao/callback/` |

모든 에러 응답은 `{ "detail": "...", "code": "..." }` 형식을 따릅니다.

---

## 6. PendingRegistration 구조

이메일 인증 전에는 User 레코드를 만들지 않고 `PendingRegistration` 에만 저장합니다. 인증 성공 시 `services.finalize_pending_registration` 이 호출되어 실제 `authentication.User` 가 생성되고, 대기 레코드는 삭제됩니다. 덕분에 인증 없이 이탈한 계정이 User 테이블에 남지 않습니다.

---

## 7. 프런트엔드/테스트

- `web/` 앱의 템플릿을 사용하면 `/register`, `/login`, `/mypage` 등 UI로 바로 확인할 수 있습니다.
- `python manage.py test authentication` 으로 가입→인증→로그인 및 OAuth 콜백 시나리오를 검증했습니다.

---

## 8. 가이드 문서

- **PORTING_GUIDE.md**: 이식 절차, 환경 변수, 충돌 방지, 체크리스트를 모두 포함합니다. 다른 프로젝트로 복사할 때 반드시 읽어 주세요.
- **루트 README.md**: 전체 프로젝트 개요와 실행 방법을 간단히 정리했습니다.

이 문서들을 참고하면 authentication 모듈을 빠르게 붙이고, 로그인 기능이 없는 Django 프로젝트에도 몇 분 만에 완전한 인증 시스템을 이식할 수 있습니다.
