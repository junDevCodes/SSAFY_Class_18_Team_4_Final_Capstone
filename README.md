# SelF

> 소비자가 원하는 상품을 추천하고, 가장 저렴하게 찾을 수 있는 전자상거래 플랫폼.

<img src="[https://i.postimg.cc/FsR1X5cv/Self_로고.png](https://i.postimg.cc/B6sF45VC/Sel-F.png)" alt="SelF-Logo" width="200">

## 📌 프로젝트 소개

SelF은 농산물 전자상거래 플랫폼으로, 신선한 농산물을 합리적인 가격에 제공하는 것을 목표로 합니다.
판매자(농가, 유통업체)는 자신의 브랜드몰을 운영할 수 있으며, 소비자는 다양한 브랜드의 농산물을 한 곳에서 구매할 수 있습니다.

**주요 특징:**
- 🛒 일반 상품(크롤링/관리자 등록) + 판매자 직접 등록 상품 통합 관리
- 🏪 판매자 브랜드몰 시스템 (자체 상품 등록 및 관리)
- 📊 데이터 기반 상품 추천 (품질 점수, CTR, 사용자 행동 분석)
- 🔐 다중 인증 방식 (이메일, Google OAuth, Kakao OAuth)
- 💳 장바구니, 찜 목록, 주문/결제 통합 시스템

- **1차 개발 기간**: 2025.11.10 ~ 2025.11.24 (MVP)
- **추가 개발 기간**: 2025.11.25 ~ 2025.12.28 (고도화)
- **팀 구성**: 3명

## 👥 팀원 소개

| 이름 | 역할 | GitHub | 담당 기능 |
|------|------|--------|-----------|
| 이준영 | 팀장/Data/AI/Embeded/DevOps | [@junDevCodes](@https://github.com/junDevCodes) | Data 분석 & 인사이트 도출, CI/CD 파이프라인 구축 |
| 배용건 | Frontend | [@dragun8](@https://github.com/dragun8) | MVP 설계, UI/UX 구현 |
| 송준서 | Backend/DevOps/AI Agent | [@Junseo5](@https://github.com/Junseo5) | API 개발, DB 설계, 기능 개발 |

## 🛠 기술 스택

### Frontend
![VUE](https://img.shields.io/badge/Vue.js-35495E?&logo=vuedotjs&logoColor=FFF&style=flat-square)
![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=flat-square&logo=html5&logoColor=white)
![CSS3](https://img.shields.io/badge/CSS3-1572B6?style=flat-square&logo=css3&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=flat-square&logo=javascript&logoColor=black)
![TypeScript](https://shields.io/badge/TypeScript-3178C6?logo=TypeScript&logoColor=FFF&style=flat-square)

### Backend
![Django](https://img.shields.io/badge/Django-092E20?&style=flat-square&logo=django&logoColor=green)
![DRF](https://img.shields.io/badge/django--rest--framework-3.12.4-blue?style=flat-square&labelColor=333333&logo=django&logoColor=white&color=blue)

### Database
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?logo=postgresql&logoColor=white&style=flat-square)![Redis:Database](https://img.shields.io/badge/Database-Redis-informational?style=flat-square&logo=redis&logoColor=white&color=red)

### Crawling / Scraping
![Playwright]()

### Data Processing & ML/DL
![Pandas](https://img.shields.io/badge/-Pandas-333333?style=flat-square&logo=pandas)
![Numpy](https://img.shields.io/badge/-Numpy-013243?&logo=NumPy&style=flat-square)
![Scikit-Learn](https://img.shields.io/badge/scikit--learn-F7931E?style=flat-square&logo=scikit-learn&logoColor=white)
![Keras](https://img.shields.io/badge/-Keras-D00000?style=flat-sqaure&logo=Keras)
![Prophet]()
![Sentence-Transformers]()
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat-square&logo=fastapi)

### Cloud & Infra
![Docker](https://img.shields.io/badge/docker-257bd6?style=flat-square&logo=docker&logoColor=white)
![Docker-compose](https://img.shields.io/badge/Docker%20Compose-061D2F?logo=docker&style=flat-square)
![AWS-Lightsail-Container]()
![Nginx](https://img.shields.io/badge/Nginx-009639?logo=nginx&logoColor=white&style=flat-square)
![Github-Actions](https://img.shields.io/badge/-GitHub%20Actions-333333?style=flat-square&logo=github-actions)

### Storage
![AWS-S3]()
![Nginx](https://img.shields.io/badge/Nginx-009639?logo=nginx&logoColor=white&style=flat-square)


### Authentication
![OAuth2](https://img.shields.io/badge/OAuth_2.0-Bearer-000000?style=flat-square)
<!-- ### Tools
![REDIS](https://img.shields.io/badge/Redis-DC382D?style=flat-square&logo=redis&logoColor=white)
![Kafka](https://img.shields.io/badge/Apache_Kafka-231F20?style=for-the-badge&logo=apache-kafka&logoColor=white) -->

### Communicate
![Git](https://img.shields.io/badge/Git-F05032?style=flat-square&logo=git&logoColor=white)
![GitHub](https://img.shields.io/badge/GitHub-181717?style=flat-square&logo=github&logoColor=white)
![Slack](https://img.shields.io/badge/Slack-Join?logo=Slack&style=flat-square)
![Discord](https://shields.io/discord/1442794136955654144?style=flat-square&label=discord&logo=discord&labelColor=black&color=5865F2)


## ✨ 주요 기능

### 1. 사용자 인증 시스템
- **이메일 회원가입/로그인**: 이메일 인증 코드 기반 회원가입
- **OAuth2 소셜 로그인**: Google, Kakao 계정으로 간편 로그인
- **JWT 토큰 관리**: 자동 토큰 갱신 (Access Token 15분, Refresh Token 7일)
- **역할 기반 권한**: Guest, User, Seller, Admin 4단계 권한 관리

### 2. 상품 관리
- **통합 상품 시스템**: 메인 상품(크롤링/관리자) + 판매자 상품 통합 관리
- **계층형 카테고리**: 무한 depth 카테고리 구조 지원
- **다중 이미지**: 상품당 여러 이미지 등록 및 순서 관리
- **품질 점수 시스템**: 이미지 품질, 콘텐츠 완성도, CTR 종합 평가
- **재고 관리**: 실시간 재고 추적 및 품절 표시

### 3. 판매자 센터
- **브랜드몰 운영**: 판매자별 독립적인 브랜드 페이지
- **상품 등록/수정**: 판매자가 직접 상품 등록 및 관리
- **판매자 대시보드**: 판매 통계, 주문 현황 실시간 조회
- **자동 승인 시스템**: MVP 단계 판매자 즉시 승인

### 4. 쇼핑 기능
- **장바구니**: 실시간 장바구니 동기화 및 수량 조절
- **찜 목록**: 관심 상품 저장 및 관리
- **주문/결제**: 배송지 입력, 주문서 생성, 주문 내역 조회
- **주문 관리**: 주문 취소, 배송 추적 (MVP: 기본 기능만)

### 5. 데이터 기반 추천
- **상품 조회 로그**: 모든 사용자 행동 추적 (로그인/비로그인)
- **CTR 계산**: 클릭률 기반 상품 품질 평가
- **통계 비정규화**: 조회수, 찜 수, 구매 수 실시간 집계

## 🏗 프로젝트 구조

```
SSAFY_Class_18_Team_4_Final_Capstone/
├── backend/                      # Django REST API 백엔드
│   ├── authentication/           # 사용자 인증 (이메일, OAuth2, JWT)
│   ├── products/                 # 상품, 카테고리, 장바구니, 찜 목록
│   ├── sellers/                  # 판매자 프로필 및 브랜드 관리
│   ├── orders/                   # 주문 및 주문 상품 관리
│   ├── project_self/             # Django 설정
│   ├── manage.py
│   └── requirements.txt
│
├── frontend/                     # Vue 3 + TypeScript 프론트엔드
│   ├── src/
│   │   ├── pages/                # 17개 페이지 (Home, MyPage, Seller, Brand 등)
│   │   ├── components/           # Layout, Section, UI 컴포넌트
│   │   ├── stores/               # Pinia 상태 관리 (auth, cart, products, orders, wishlist, ui)
│   │   ├── services/api/         # API 클라이언트 및 엔드포인트
│   │   ├── types/                # TypeScript 타입 정의
│   │   ├── composables/          # 재사용 로직 (useTimer, useScroll)
│   │   └── utils/                # 유틸리티 함수
│   └── package.json
│
├── crawler/
├── data/                         # 크롤링 날짜별 데이터(JSON)
├── docs/                         # 프로젝트 문서
│   ├── GIT_CONVENTION.md
│   ├── CODE_CONVENTION.md
│   ├── BRANCH_STRATEGY.md
│   ├── CODE_REVIEW.md
│   └── CONTRIBUTING.md
├── CLAUDE.md                     # AI 개발 가이드
└── README.md
```

## 🚀 설치 및 실행

### 요구사항

**Backend**
- Python 3.9 이상
- pip

**Frontend**
- Node.js 18.x 이상
- npm 또는 yarn

### Backend 설치 및 실행

#### 1. 가상환경 설정 (중요!)
```bash
# 프로젝트 루트로 이동
cd SSAFY_Class_18_Team_4_Final_Capstone

# 가상환경 활성화 (Windows Git Bash)
. venv/Scripts/activate

# 가상환경 활성화 (Windows CMD)
venv\Scripts\activate

# 가상환경 활성화 (Mac/Linux)
source venv/bin/activate
```

#### 2. 환경 변수 설정
```bash
# backend/.env 파일 생성 (backend/.env.example 참고)
cp backend/.env.example backend/.env

# 필수 환경 변수 설정:
# - EMAIL_HOST_USER, EMAIL_HOST_PASSWORD (Gmail 앱 비밀번호)
# - GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
# - KAKAO_CLIENT_ID, KAKAO_CLIENT_SECRET
```

#### 3. 의존성 설치 및 마이그레이션
```bash
# 백엔드 디렉토리로 이동
cd backend

# 의존성 설치
pip install -r requirements.txt

# 마이그레이션 적용
python manage.py migrate

# 샘플 데이터 임포트 (선택)
python manage.py import_products

# 개발 서버 실행 (포트 8000)
python manage.py runserver 8000
```

#### 4. 테스트 실행
```bash
# 전체 테스트
python manage.py test

# 특정 앱 테스트
python manage.py test authentication
python manage.py test products
```

### Frontend 설치 및 실행

#### 1. 의존성 설치
```bash
# 프론트엔드 디렉토리로 이동
cd frontend

# 의존성 설치
npm install
```

#### 2. 환경 변수 설정
```bash
# .env.development 파일이 이미 있는지 확인
# 없으면 생성:
echo "VITE_API_BASE_URL=http://localhost:8000" > .env.development
```

#### 3. 개발 서버 실행
```bash
# 개발 서버 실행 (포트 5173)
npm run dev

# TypeScript 타입 체크
npm run type-check

# 빌드 (프로덕션)
npm run build

# 빌드 결과 미리보기
npm run preview
```

### 전체 시스템 실행 순서
1. **Backend 서버 실행** (포트 8000)
2. **Frontend 서버 실행** (포트 5173)
3. 브라우저에서 `http://localhost:5173` 접속

## 📝 협업 규칙

- [Git Convention](docs/GIT_CONVENTION.md)
- [Code Convention](docs/CODE_CONVENTION.md)
- [Branch Strategy](docs/BRANCH_STRATEGY.md)
- [Code Review](docs/CODE_REVIEW.md)

## 🔗 링크

- [프로젝트 기획 노션 페이지](https://www.notion.so/SSAFY-SEOUL-CLASS-18-TEAM-4-FINAL-CAPSTONE-PROJECT-2a67359b60688023991cef2fa72846f1?source=copy_link)
- [배포 URL](https://sellfresh.shop)
- [API 문서](https://api.sellfresh.shop/docs)

## 📄 라이센스

MIT License

## 🤝 기여

이 프로젝트에 기여하고 싶으시다면 [CONTRIBUTING.md](docs/CONTRIBUTING.md)를 참고해주세요.
