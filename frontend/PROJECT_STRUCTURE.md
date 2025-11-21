# FreshPick 프로젝트 구조 문서

## 기술 스택
- **프레임워크**: Vue 3.4+ (Composition API)
- **빌드 도구**: Vite 5+
- **언어**: TypeScript 5+
- **상태 관리**: Pinia 2+
- **스타일링**: Tailwind CSS 3+
- **아이콘**: Lucide Vue (Vue 3용)
- **HTTP 클라이언트**: Axios

## 디렉토리 구조

```
front_demo_2/
├── src/
│   ├── assets/
│   │   ├── images/          # 이미지 파일
│   │   └── fonts/            # 폰트 파일
│   │
│   ├── components/
│   │   ├── layout/
│   │   │   ├── AppHeader.vue      # 헤더 컴포넌트
│   │   │   └── AppFooter.vue      # 푸터 컴포넌트
│   │   │
│   │   ├── sections/
│   │   │   ├── HeroSection.vue    # 히어로 섹션
│   │   │   ├── CategoryNav.vue    # 카테고리 네비게이션
│   │   │   ├── QuickCategories.vue # 빠른 카테고리
│   │   │   ├── BrandPromise.vue   # 브랜드 약속
│   │   │   ├── TimeDeal.vue      # 타임딜
│   │   │   └── ProductList.vue   # 상품 리스트
│   │   │
│   │   └── ui/
│   │       ├── ProductCard.vue    # 상품 카드
│   │       ├── LoginModal.vue    # 로그인 모달
│   │       ├── CartDrawer.vue    # 장바구니 드로어
│   │       └── Toast.vue         # 토스트 알림
│   │
│   ├── composables/
│   │   ├── useCart.ts           # 장바구니 로직
│   │   ├── useAuth.ts           # 인증 로직
│   │   ├── useTimer.ts          # 타이머 로직
│   │   └── useScroll.ts         # 스크롤 로직
│   │
│   ├── stores/
│   │   ├── cart.ts              # 장바구니 스토어
│   │   ├── auth.ts              # 인증 스토어
│   │   ├── products.ts          # 상품 스토어
│   │   └── ui.ts                # UI 스토어
│   │
│   ├── services/
│   │   ├── api/
│   │   │   ├── client.ts        # Axios 인스턴스
│   │   │   ├── products.ts      # 상품 API
│   │   │   ├── auth.ts          # 인증 API
│   │   │   └── cart.ts          # 장바구니 API
│   │   └── types.ts             # API 타입 정의
│   │
│   ├── utils/
│   │   ├── formatters.ts        # 포맷팅 유틸
│   │   ├── validators.ts        # 검증 유틸
│   │   └── constants.ts         # 상수 정의
│   │
│   ├── types/
│   │   ├── product.ts           # 상품 타입
│   │   ├── cart.ts              # 장바구니 타입
│   │   ├── auth.ts              # 인증 타입
│   │   └── api.ts               # API 타입
│   │
│   ├── styles/
│   │   ├── main.css             # 메인 스타일
│   │   └── animations.css       # 애니메이션
│   │
│   ├── App.vue                  # 루트 컴포넌트
│   └── main.ts                  # 진입점
│
├── public/                      # 정적 파일
├── index.html                   # HTML 템플릿
├── package.json                 # 의존성 관리
├── vite.config.ts              # Vite 설정
├── tsconfig.json               # TypeScript 설정
├── tailwind.config.js          # Tailwind 설정
├── plan.md                     # 프로젝트 계획서
└── PROJECT_STRUCTURE.md        # 이 파일

```

## 컴포넌트 설계 원칙

### 1. 단일 책임 원칙
각 컴포넌트는 하나의 명확한 역할만 수행

### 2. Props 타입 정의
모든 props는 TypeScript 인터페이스로 정의

### 3. 이벤트 명명 규칙
- `@update:` - 양방향 바인딩
- `@change:` - 값 변경
- `@click:` - 클릭 이벤트

### 4. 컴포넌트 네이밍
- PascalCase 사용
- 명확하고 설명적인 이름

## 상태 관리 전략

### Pinia Stores
- **cart**: 장바구니 상태 및 액션
- **auth**: 인증 상태 및 액션
- **products**: 상품 데이터 캐싱
- **ui**: 모달, 토스트 등 UI 상태

### 컴포저블 함수
- 재사용 가능한 로직을 컴포저블로 분리
- 각 컴포저블은 단일 책임

## 스타일링 전략

### Tailwind CSS
- 유틸리티 클래스 우선 사용
- 커스텀 클래스는 최소화
- 반응형 디자인 모바일 우선

### 커스텀 스타일
- 전역 애니메이션은 `styles/animations.css`
- 브랜드 색상은 `tailwind.config.js`

## API 통신 전략

### Axios 인스턴스
- 기본 URL 설정
- 인터셉터로 토큰 관리
- 에러 핸들링 통합

### 타입 안정성
- 모든 API 응답 타입 정의
- 제네릭 활용

## 빌드 및 배포

### 개발 환경
```bash
npm run dev
```

### 프로덕션 빌드
```bash
npm run build
```

### 환경 변수
- `.env.development`
- `.env.production`

