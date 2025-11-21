# FreshPick - Vue 3 E-commerce Frontend

FreshPick은 Vue 3와 TypeScript로 구축된 프리미엄 신선식품 이커머스 플랫폼입니다.

## 기술 스택

- **프레임워크**: Vue 3.5+ (Composition API)
- **빌드 도구**: Vite 7+
- **언어**: TypeScript 5+
- **상태 관리**: Pinia 3+
- **스타일링**: Tailwind CSS 4+
- **아이콘**: Lucide Vue Next
- **HTTP 클라이언트**: Axios

## 프로젝트 구조

```
front_demo_2/
├── src/
│   ├── components/      # Vue 컴포넌트
│   ├── composables/     # Composition API 함수
│   ├── stores/          # Pinia 스토어
│   ├── services/        # API 서비스
│   ├── utils/           # 유틸리티 함수
│   ├── types/           # TypeScript 타입 정의
│   └── styles/          # 전역 스타일
├── public/              # 정적 파일
└── index.html           # HTML 템플릿
```

## 시작하기

### 설치

```bash
npm install
```

### 개발 서버 실행

```bash
npm run dev
```

개발 서버는 `http://localhost:3000`에서 실행됩니다.

### 빌드

```bash
npm run build
```

### 타입 체크

```bash
npm run type-check
```

## 환경 변수

`.env.development` 파일을 생성하여 다음 변수를 설정하세요:

```env
VITE_API_BASE_URL=http://localhost:8000
```

## 주요 기능

- ✅ 반응형 디자인 (모바일 우선)
- ✅ 장바구니 기능
- ✅ 로그인/회원가입 모달
- ✅ 상품 목록 및 상세
- ✅ 타임딜 타이머
- ✅ 카테고리 필터링
- ✅ 토스트 알림

## 백엔드 연동

API 서비스는 `src/services/api/` 디렉토리에 정의되어 있습니다:

- `products.ts` - 상품 관련 API
- `auth.ts` - 인증 관련 API
- `cart.ts` - 장바구니 관련 API

모든 API 호출은 `src/services/api/client.ts`의 Axios 인스턴스를 사용합니다.

## 컴포넌트 구조

### Layout Components
- `AppHeader` - 헤더 (로고, 검색, 로그인, 장바구니)
- `AppFooter` - 푸터

### Section Components
- `HeroSection` - 히어로 섹션
- `CategoryNav` - 카테고리 네비게이션
- `QuickCategories` - 빠른 카테고리
- `BrandPromise` - 브랜드 약속
- `TimeDeal` - 타임딜
- `ProductList` - 상품 리스트

### UI Components
- `ProductCard` - 상품 카드
- `LoginModal` - 로그인/회원가입 모달
- `CartDrawer` - 장바구니 드로어
- `Toast` - 토스트 알림

## 상태 관리

Pinia를 사용하여 상태를 관리합니다:

- `useCartStore` - 장바구니 상태
- `useUIStore` - UI 상태 (모달, 토스트 등)
- `useProductStore` - 상품 데이터

## 라이선스

ISC

