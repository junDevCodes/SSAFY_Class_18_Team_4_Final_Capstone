# 기술 스택 버전 명세서

> **최종 수정일**: 2025-12-02
> **목적**: 프로젝트 전체의 기술 스택 버전을 통합 관리하여 개발/CI/CD/배포 환경 간 일관성 보장

---

## 📋 버전 통합 요약

| 구분 | 기술 | 버전 | 비고 |
|------|------|------|------|
| **런타임** | Python | 3.12.x | Django 5.x 호환 (3.10+) |
| **런타임** | Node.js | 20.x LTS | 2023.10 ~ 2026.04 Active LTS |
| **런타임** | npm | 10.x | Node 20에 포함 |

---

## 🐍 Backend (Django)

### Python 런타임
- **버전**: `3.12.x` (최신 안정 버전)
- **최소 요구**: `3.10` (Django 5.x 요구사항)
- **설정 파일**: `.python-version`, `pyproject.toml`

### 핵심 프레임워크
| 패키지 | 버전 | 용도 |
|--------|------|------|
| Django | 5.2.x | 메인 웹 프레임워크 |
| djangorestframework | 3.16.x | REST API |
| django-cors-headers | 4.3.x | CORS 처리 |
| django-filter | 25.x | 쿼리 필터링 |

### 인증/보안
| 패키지 | 버전 | 용도 |
|--------|------|------|
| django-allauth | 65.x | 소셜 로그인 (카카오, 구글) |
| djangorestframework-simplejwt | 5.5.x | JWT 인증 |
| PyJWT | 2.10.x | JWT 처리 |

### 데이터베이스
| 패키지 | 버전 | 용도 |
|--------|------|------|
| psycopg2-binary | 2.9.x | PostgreSQL 드라이버 |
| redis | 5.x | Redis 클라이언트 (캐시/세션) |

### 비동기/태스크
| 패키지 | 버전 | 용도 |
|--------|------|------|
| celery | 5.4.x | 비동기 태스크 큐 |
| redis | 5.x | Celery 브로커 |

### 프로덕션 서버
| 패키지 | 버전 | 용도 |
|--------|------|------|
| gunicorn | 23.x | WSGI 서버 |
| uvicorn | 0.34.x | ASGI 서버 (선택) |

---

## ⚡ Backend ML (FastAPI)

### Python 런타임
- **버전**: `3.12.x` (Django와 통일)

### 핵심 프레임워크
| 패키지 | 버전 | 용도 |
|--------|------|------|
| fastapi | 0.115.x | ML API 서버 |
| uvicorn | 0.34.x | ASGI 서버 |
| pydantic | 2.10.x | 데이터 검증 |

### ML/DL 라이브러리
| 패키지 | 버전 | 용도 |
|--------|------|------|
| sentence-transformers | 3.x | Bert4Vec 임베딩 |
| prophet | 1.1.x | 시계열 예측 |
| scikit-learn | 1.6.x | ML 유틸리티 |
| pandas | 2.2.x | 데이터 처리 |
| numpy | 2.2.x | 수치 연산 |

---

## 🎨 Frontend (Vue 3)

### Node.js 런타임
- **버전**: `20.x` LTS (Active LTS: 2023.10 ~ 2026.04)
- **npm 버전**: `10.x` (Node 20에 포함)
- **설정 파일**: `.nvmrc`, `package.json#engines`

### 핵심 프레임워크
| 패키지 | 버전 | 용도 |
|--------|------|------|
| vue | 3.5.x | UI 프레임워크 |
| vue-router | 4.4.x | 라우팅 |
| pinia | 3.x | 상태 관리 |
| axios | 1.13.x | HTTP 클라이언트 |

### 빌드 도구
| 패키지 | 버전 | 용도 |
|--------|------|------|
| vite | 7.x | 빌드 도구 |
| typescript | 5.9.x | 타입 시스템 |
| vue-tsc | 3.x | Vue TypeScript 검사 |

### 스타일링
| 패키지 | 버전 | 용도 |
|--------|------|------|
| tailwindcss | 3.4.x | CSS 프레임워크 |
| autoprefixer | 10.x | CSS 후처리 |
| postcss | 8.x | CSS 변환 |

---

## 🐳 인프라/DevOps

### 컨테이너
| 기술 | 버전 | 용도 |
|------|------|------|
| Docker | 27.x | 컨테이너 런타임 |
| Docker Compose | 2.x | 멀티 컨테이너 관리 |

### 웹 서버
| 기술 | 버전 | 용도 |
|------|------|------|
| Nginx | 1.27.x (alpine) | 리버스 프록시, 정적 파일 |

### 데이터베이스
| 기술 | 버전 | 용도 |
|------|------|------|
| PostgreSQL | 16.x | 메인 데이터베이스 |
| Redis | 7.x (alpine) | 캐시/세션/태스크 브로커 |

### 클라우드 (현재)
| 서비스 | 용도 |
|--------|------|
| AWS Lightsail | 컨테이너 호스팅 (Main + Pred 서버) |
| AWS S3 | 정적 파일/이미지 스토리지 |
| AWS ECR | Docker 이미지 레지스트리 (예정) |

### 클라우드 (미래)
| 서비스 | 용도 |
|--------|------|
| AWS EC2 | 컨테이너 호스팅 (t3.small × 2) |
| AWS Auto Scaling | 트래픽 대응 |

---

## 🔄 CI/CD

### GitHub Actions
| Action | 버전 | 용도 |
|--------|------|------|
| actions/checkout | v4 | 코드 체크아웃 |
| actions/setup-python | v5 | Python 설정 |
| actions/setup-node | v4 | Node.js 설정 |
| docker/login-action | v3 | Docker 레지스트리 로그인 |
| docker/build-push-action | v6 | Docker 이미지 빌드/푸시 |

### 브랜치 전략
- **main**: 프로덕션 배포
- **dev**: 개발/테스트 배포
- **feature/***: 기능 개발
- **hotfix/***: 긴급 수정

---

## 🔧 로컬 개발 환경 설정

### Python 환경 (pyenv 사용 권장)
```bash
# pyenv로 Python 3.12 설치
pyenv install 3.12.0
pyenv local 3.12.0

# 가상환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r backend/requirements.txt
```

### Node.js 환경 (nvm 사용 권장)
```bash
# nvm으로 Node 20 설치
nvm install 20
nvm use 20

# 의존성 설치
cd frontend
npm ci
```

### Docker 환경
```bash
# 전체 스택 실행
docker-compose up --build

# 개별 서비스 실행
docker-compose up backend frontend
```

---

## ⚠️ 버전 호환성 주의사항

### Django 5.x 요구사항
- **Python 3.10+** 필수 (Python 3.9 이하 미지원)
- SQLite 3.31.0+, PostgreSQL 13+, MySQL 8.0.11+, Oracle 21c+

### Node.js LTS 정책
- Node 20.x: Active LTS (2023.10 ~ 2026.04)
- Node 18.x: Maintenance LTS (2023.10 ~ 2025.04)
- Node 22.x: Current → 2024.10부터 LTS

### Docker 이미지 태그 정책
- 개발: `latest`, `dev`
- 프로덕션: `v{버전}`, `{git-sha}`

---

## 📝 버전 업데이트 절차

1. **의존성 업데이트 시**:
   - `requirements.txt` 또는 `package.json` 수정
   - 로컬에서 테스트
   - CI 파이프라인 통과 확인
   - 이 문서 업데이트

2. **런타임 버전 업데이트 시**:
   - `.python-version`, `.nvmrc` 수정
   - `backend-ci.yml`, `frontend-ci.yml` 수정
   - Dockerfile 수정
   - 이 문서 업데이트

---

**작성자**: SelF 개발팀
**버전**: 1.0

