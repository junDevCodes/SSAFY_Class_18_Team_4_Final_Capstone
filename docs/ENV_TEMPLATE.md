# EC2 환경변수 설정 가이드

> EC2 서버에서 `.env` 파일을 생성할 때 참고하세요.

---

## 📁 파일 위치

```bash
~/self-app/.env
```

---

## 🔐 환경변수 템플릿

EC2에서 다음 명령어로 파일을 생성하세요:

```bash
cd ~/self-app
nano .env
```

아래 내용을 복사하고 **실제 값으로 교체**하세요:

```env
# ============================================
# EC2 프로덕션 환경변수
# ============================================

# === EC2 서버 정보 ===
EC2_PUBLIC_IP=15.165.232.91

# === Django 기본 설정 ===
SECRET_KEY=여기에-랜덤-문자열-입력
DEBUG=False
ALLOWED_HOSTS=*

# === 데이터베이스 ===
DB_NAME=selfdb
DB_USER=selfuser
DB_PASSWORD=여기에-강력한-비밀번호

# === OAuth 인증 (선택) ===
KAKAO_REST_API_KEY=
KAKAO_CLIENT_SECRET=
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
```

---

## 🔑 SECRET_KEY 생성 방법

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
```

출력 예시:
```
8J_kL2mN3pQ4rS5tU6vW7xY8zA9bC0dE1fG2hI3jK4lM5nO6pQ7rS8tU9vW0xY
```

이 값을 `SECRET_KEY=` 뒤에 붙여넣으세요.

---

## 📋 DB_PASSWORD 규칙

- 최소 8자 이상
- 대문자, 소문자, 숫자, 특수문자 포함 권장
- 예: `MyP@ssw0rd123!`

---

## ⚠️ 보안 주의사항

1. **`.env` 파일은 절대 Git에 커밋하지 마세요!**
2. 파일 권한을 `600`으로 설정하세요:
   ```bash
   chmod 600 .env
   ```
3. 시크릿 키는 슬랙, 카카오톡 등에 공유하지 마세요.
4. 정기적으로 비밀번호/키를 교체하세요.

---

## ✅ 확인 방법

```bash
# 파일 내용 확인
cat .env

# 권한 확인 (소유자만 읽기/쓰기)
ls -la .env
# 출력: -rw------- 1 ubuntu ubuntu ...
```

---

## 🔗 OAuth 키 발급 URL

| 서비스 | 개발자 콘솔 URL |
|--------|----------------|
| 카카오 | https://developers.kakao.com |
| 구글   | https://console.cloud.google.com |

---

**작성일**: 2025-12-04

