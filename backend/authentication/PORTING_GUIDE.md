# authentication 폴더 이식 가이드

이 문서는 **로그인/회원관리 기능이 없는 Django 프로젝트**에 `authentication/` 폴더를 복사해 넣기만 해도 즉시 동작하도록 안내합니다. 아래 절차를 따르면 이메일 기반 회원가입(이메일 인증), 비밀번호 관리, JWT 로그인, Google/Kakao OAuth2, 권한(Role) 검증, 웹 데모 UI까지 한 번에 이식할 수 있습니다.

---

## 1. 폴더 설명 및 대상 시스템

- **authentication/**: Django + DRF + SimpleJWT 기반 인증 모듈. 커스텀 User 모델(`authentication.User`)과 OAuth/이메일 인증 로직, API 뷰, 권한 핸들러, 포팅 가이드를 포함합니다.
- **장착 가능한 시스템**: Django 4.2+ (5.x 포함), Python 3.10 이상, DB는 SQLite/PostgreSQL 등 기본 ORM 지원 DB면 모두 가능합니다.
- **의존 프로젝트 구조**: 일반적인 `manage.py`/`project/settings.py`/`project/urls.py` 형태의 Django 프로젝트.

---

## 2. 설치/환경 구성

1. **필수 라이브러리**
   ```bash
   pip install django>=4.2 djangorestframework djangorestframework-simplejwt django-allauth requests python-dotenv
   # (선택) CORS, API 문서 등이 필요하면
   pip install django-cors-headers drf-spectacular dj-rest-auth
   ```
2. **폴더 이식**
   - 기존 프로젝트 루트(예: `manage.py`와 동일한 경로)에 `authentication/` 폴더 전체를 복사합니다.
3. **settings.py 수정**
   - `INSTALLED_APPS`에 다음을 추가:
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
     ```
   - 기본 설정:
     ```python
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

     # 이메일 설정은 .env 참고
     ```
4. **URL 연결**
   ```python
   from django.urls import include, path

   urlpatterns = [
       path('', include('authentication.urls', namespace='authentication')),
       # 기존 웹/기타 앱 URL...
   ]
   ```
5. **환경변수(.env)**
   - `project/settings.py`에서 `python-dotenv`로 `.env`를 로드하도록 구성한 뒤, 아래 템플릿을 참고해 `.env` 파일 작성.
   - 예시(template): `.env.example` 파일 제공 (아래 7장 참조).

---

## 3. 데이터베이스 구조

### 3.1 User (authentication_user)
| 필드 | 설명 |
| --- | --- |
| email (unique) | 로그인 식별자 |
| username | 표시용 닉네임 |
| role | guest/member/vip/admin |
| provider | email/google/kakao |
| provider_id | OAuth 계정 ID |
| profile_image_url, timezone | 프로필/환경 정보 |
| is_email_verified | 이메일 인증 여부 |
| email_verification_code | 레거시 호환용 코드 |

### 3.2 PendingRegistration
| 필드 | 설명 |
| --- | --- |
| email (unique) | 가입 대기 이메일 |
| username | 선택 입력 |
| password_hash | 해시 결과 |
| verification_code | 인증 코드 |
| expires_at | 만료 시각 (기본 30분) |
| created_at/updated_at | 감사 로그 |

- 가입 시 PendingRegistration에만 데이터가 들어가며, 인증 완료 후 실제 User 레코드가 생성됩니다. 이로 인해 **인증 없이 이탈한 “유령 계정”이 DB에 남지 않습니다.**

---

## 4. 모듈 구조

| 경로 | 설명 |
| --- | --- |
| `authentication/models.py` | `User`, `PendingRegistration` 모델 정의 |
| `authentication/serializers.py` | 회원가입/로그인/비밀번호/인증 시리얼라이저 |
| `authentication/views.py` | `/auth/*` API 뷰 (이메일 인증, JWT, OAuth, 비밀번호, 프로필) |
| `authentication/services.py` | 토큰 발급, 이메일 발송, 대기 테이블 관리, 역할 정책 |
| `authentication/providers.py` | Google/Kakao OAuth authorize/token/userinfo 헬퍼 |
| `authentication/config.py` | 환경 변수 로딩 및 공통 설정 |
| `authentication/tests.py` | 기본 플로우 테스트 (가입→인증→로그인) + OAuth 콜백 테스트 |
| `authentication/PORTING_GUIDE.md` | (본 문서) |
| `web/` | 데모용 프론트엔드 템플릿 및 뷰 (선택적으로 사용) |

---

## 5. 환경 변수 (.env) 양식

`.env.example` 파일을 참고하세요. 대표 항목:
```bash
SECRET_KEY=change-me
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost

# SMTP (Gmail 예시)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=example@gmail.com
EMAIL_HOST_PASSWORD=앱비밀번호16자리
EMAIL_VERIFICATION_FROM_EMAIL=example@gmail.com
EMAIL_VERIFICATION_CODE_LENGTH=6
EMAIL_VERIFICATION_EXPIRES_MINUTES=30

# JWT / ROLE
JWT_ACCESS_TOKEN_LIFETIME=15
JWT_REFRESH_TOKEN_LIFETIME=7
DEFAULT_ROLE=guest  # guest: 비회원, user: 일반회원, seller: 판매자, admin: 관리자
ADMIN_EMAIL_WHITELIST=admin@example.com
PASSWORD_RESET_RETURN_TOKEN_IN_RESPONSE=false

# OAuth
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_CALLBACK_URL=http://localhost:8000/auth/google/callback/
KAKAO_REST_API_KEY=...
KAKAO_CLIENT_SECRET=
KAKAO_CALLBACK_URL=http://localhost:8000/auth/kakao/callback/
```
> **Gmail 주의:** SMTP는 일반 비밀번호를 허용하지 않습니다. 반드시 앱 비밀번호(16자리)를 생성해 `EMAIL_HOST_PASSWORD` 로 사용하세요.

---

## 6. 설치 후 단계별 가이드

1. `python manage.py makemigrations authentication && python manage.py migrate`.
2. `python manage.py createsuperuser` (관리자 계정이 필요하면).
3. `.env` 설정 검증 후 `python manage.py runserver` 실행.
4. 브라우저로 `http://localhost:8000/register/` 접속 → 회원가입 시도를 통해 이메일 인증 흐름 확인.
5. `/auth/register → /auth/register/verify → /auth/login` 순서대로 API 호출 테스트.
6. `/auth/google`, `/auth/kakao` 리디렉션 및 콜백 확인 (OAuth 콘솔에서 redirect URI 등록 필수).
7. `/auth/user` (GET/PATCH), `/auth/password/change`, `/auth/password/reset` 등 기타 엔드포인트 테스트.
8. 프런트엔드 템플릿(`web/`)을 사용할 경우, 추가로 `project/urls.py`에 `path('', include('web.urls', namespace='web'))` 를 연결하면 데모 화면을 확인할 수 있습니다.

---

## 7. 역할(Role) 및 권한 구조

### Role 종류 및 상하관계
- **guest** (비회원): 방문만 한 기본 권한, 기본값
- **user** (일반회원): 일반 회원가입 완료 시 자동 부여, OAuth 로그인 시에도 부여
- **seller** (판매자): 판매자 회원 권한, 게시판에 물품 등록/수정/삭제 가능
- **admin** (관리자): 최고 관리자 권한, 모든 권한 보유

### Role 부여 규칙
- 기본 Role: `guest` → `.env`의 `DEFAULT_ROLE` 값으로 초기화
- 일반 회원가입 완료 시: `user` 권한 자동 부여
- OAuth 로그인 시: `user` 권한 자동 부여
- `ADMIN_EMAIL_WHITELIST` 에 등록된 이메일로 가입하면 자동으로 `admin` 부여
- 권한이 필요한 API는 `authentication.permissions.RoleRequired` 를 참고하여 적용

### Role 상하관계
```
admin > seller > user > guest
```

---

## 8. 이메일 인증/로그인 플로우

1. `POST /auth/register/` → PendingRegistration 생성 + 인증 메일 발송.
2. `POST /auth/register/verify/` → 코드 검증 후 User 생성·자동 로그인 준비.
3. `POST /auth/login/` → JWT(access/refresh) + 사용자 정보 반환.
4. `POST /auth/logout/` → refresh 토큰 블랙리스트 등록.
5. `POST /auth/token/refresh/` → access 갱신.
6. `GET/PATCH /auth/user/` → 내 프로필 조회/수정.
7. 비밀번호 관련 API: `/auth/password/change/`, `/auth/password/reset/`, `/auth/password/reset/confirm/`.
8. OAuth2: `/auth/google/`, `/auth/google/callback/`, `/auth/kakao/`, `/auth/kakao/callback/`.

각 API는 `authentication/views.py` 에 설명이 있으며, 에러 응답 형식은 `{ "detail": "...", "code": "..." }` 로 일관적입니다.

---

## 9. 확장/커스터마이징
- **Provider 추가**: `authentication/providers.py` 에 authorize/token/userinfo 헬퍼 추가 → `views.py` 에 리다이렉트/콜백 뷰 작성.
- **Role 정책 변경**: `authentication/services.apply_role_policy_on_create` 수정.
- **메일 템플릿 변경**: `authentication/services.send_email_verification_email` 수정.
- **PendingRegistration 만료 로직 조정**: `.env` 의 `EMAIL_VERIFICATION_EXPIRES_MINUTES` 변경.
- **프론트엔드 교체**: `web/` 폴더를 참조하거나 SPA로 대체 가능. API 스펙만 맞추면 됩니다.

---

## 10. 충돌 방지 및 모듈 유지보수
- 기존 프로젝트에서 이미 커스텀 User 모델을 사용 중이면, 이 모듈과 충돌하므로 통합 계획(데이터 마이그레이션 등)을 세운 뒤 적용해야 합니다.
- URL 네임스페이스(`authentication`)를 그대로 사용할 것을 권장. 다른 인증 앱과 공존 시 prefix 조정.
- `PendingRegistration` 테이블은 인증 완료 후 자동 삭제되지만, 오래된 데이터는 주기적으로 정리(예: cron job)할 수 있습니다.
- `authentication/tests.py` 에 있는 테스트를 새 프로젝트에서도 실행하여 이식이 성공했는지 확인하세요.

---

## 11. 동작 확인 체크리스트
1. `.env` 작성 및 `settings.py` 수정 완료
2. `python manage.py migrate` 실행
3. `/auth/register` 호출 시 201 + 이메일 발송
4. `/auth/register/verify` 호출 시 PendingRegistration 삭제 및 User 생성
5. `/auth/login` → JWT 발급
6. `/auth/google` → OAuth 페이지로 리다이렉트
7. `/auth/token/refresh`, `/auth/logout`, `/auth/password/*` 테스트
8. `python manage.py test authentication` 통과
9. 웹 템플릿(`web/`)로 직접 가입/로그인 화면 확인 (선택)

모든 체크가 끝나면 기존 프로젝트에서도 완전한 로그인/인증 기능을 사용할 수 있습니다.

---

## 12. 요약

- `authentication/` 폴더는 이메일/비밀번호/이메일 인증/OAuth/JWT/역할 권한/비밀번호 관리/웹 데모 UI까지 포함한 **완결된 인증 모듈**입니다.
- 이 가이드에 따라 환경변수 설정 → 앱/URL/마이그레이션 적용 → 플로우 테스트만 끝내면 별도의 커스텀 작업 없이 어느 Django 프로젝트에서든 재활용 가능합니다.
- 가이드 준수 시 “로그인 기능이 없던 프로젝트”도 몇 분 안에 프로덕션 수준의 인증 시스템을 가질 수 있습니다.
