# FreshPick 프론트엔드 프로젝트 구조 문서

> **최종 업데이트**: 2025.11.24
> **상태**: 프로덕션 준비 완료

## 🛠 기술 스택
- **프레임워크**: Vue 3.5+ (Composition API)
- **빌드 도구**: Vite 7+
- **언어**: TypeScript 5+ (Strict Mode)
- **상태 관리**: Pinia 2+
- **라우팅**: Vue Router 4+
- **스타일링**: Tailwind CSS 3+
- **아이콘**: Lucide Vue (Vue 3용)
- **HTTP 클라이언트**: Axios 1.7+

## 📊 프로젝트 통계
- **총 파일**: 52개 (TS + Vue)
- **페이지**: 17개
- **컴포넌트**: 12개 (Layout 2, Section 6, UI 4)
- **Store**: 6개
- **API 서비스**: 6개 도메인
- **TypeScript 타입**: 2개 주요 파일
- **Composables**: 2개

## 📁 디렉토리 구조

```
frontend/
├── src/
│   ├── pages/                           # 17개 페이지
│   │   ├── HomePage.vue                 # 메인 페이지
│   │   ├── SearchPage.vue               # 검색 페이지
│   │   ├── ProductDetailPage.vue        # 상품 상세
│   │   ├── CartPage.vue                 # 장바구니
│   │   ├── WishlistPage.vue             # 찜 목록
│   │   ├── CheckoutPage.vue             # 주문/결제
│   │   ├── mypage/
│   │   │   ├── MyPageLayout.vue         # 마이페이지 레이아웃 (사이드바)
│   │   │   ├── ProfilePage.vue          # 프로필 관리
│   │   │   ├── OrdersPage.vue           # 주문 내역
│   │   │   └── OrderDetailPage.vue      # 주문 상세
│   │   ├── seller/
│   │   │   ├── RegisterPage.vue         # 판매자 등록
│   │   │   ├── DashboardPage.vue        # 판매자 대시보드
│   │   │   ├── ProductsPage.vue         # 상품 관리
│   │   │   ├── ProductCreatePage.vue    # 상품 등록
│   │   │   └── ProductEditPage.vue      # 상품 수정
│   │   └── brand/
│   │       ├── BrandMallPage.vue        # 브랜드몰 목록
│   │       └── BrandDetailPage.vue      # 브랜드 상세
│   │
│   ├── components/
│   │   ├── layout/
│   │   │   ├── AppHeader.vue            # 헤더 (동적 스타일, 인증 상태)
│   │   │   └── AppFooter.vue            # 푸터
│   │   ├── sections/
│   │   │   ├── HeroSection.vue          # 히어로 배너
│   │   │   ├── CategoryNav.vue          # 카테고리 네비게이션
│   │   │   ├── QuickCategories.vue      # 빠른 카테고리
│   │   │   ├── BrandPromise.vue         # 브랜드 약속
│   │   │   ├── TimeDeal.vue             # 타임딜 (카운트다운)
│   │   │   └── ProductList.vue          # 상품 리스트
│   │   └── ui/
│   │       ├── ProductCard.vue          # 상품 카드
│   │       ├── LoginModal.vue           # 로그인/회원가입 모달
│   │       ├── CartDrawer.vue           # 장바구니 드로어
│   │       └── Toast.vue                # 토스트 알림
│   │
│   ├── stores/                          # Pinia 상태 관리 (6개)
│   │   ├── auth.ts                      # 인증 (로그인, 회원가입, OAuth)
│   │   ├── cart.ts                      # 장바구니 (추가, 수정, 삭제, 요약)
│   │   ├── wishlist.ts                  # 찜 목록 (토글, 삭제)
│   │   ├── products.ts                  # 상품 (목록, 카테고리, 캐싱)
│   │   ├── orders.ts                    # 주문 (생성, 조회, 취소)
│   │   └── ui.ts                        # UI (모달, 드로어, 토스트, 탭)
│   │
│   ├── services/api/                    # API 서비스 레이어
│   │   ├── client.ts                    # Axios 인스턴스 (인터셉터)
│   │   └── index.ts                     # 통합 API (6개 도메인)
│   │       # authAPI, productsAPI, wishlistAPI, cartAPI, ordersAPI, sellersAPI
│   │
│   ├── composables/                     # 재사용 로직
│   │   ├── useTimer.ts                  # 타임딜 카운트다운
│   │   └── useScroll.ts                 # 스크롤 유틸리티
│   │
│   ├── types/                           # TypeScript 타입 정의
│   │   ├── product.ts                   # Product, ProductDetail, Category, 필터/정렬
│   │   └── auth.ts                      # User, LoginRequest/Response, 인증 관련
│   │
│   ├── utils/                           # 유틸리티 함수
│   │   ├── formatters.ts                # formatPrice, formatDate
│   │   ├── constants.ts                 # CATEGORIES, QUICK_CATEGORIES
│   │   └── oauth.ts                     # OAuth 헬퍼 함수
│   │
│   ├── router/
│   │   └── index.ts                     # Vue Router 설정 (인증 가드)
│   │
│   ├── styles/
│   │   └── main.css                     # 전역 스타일 (Tailwind)
│   │
│   ├── App.vue                          # 루트 컴포넌트
│   └── main.ts                          # 진입점
│
├── public/                              # 정적 파일
├── index.html                           # HTML 템플릿
├── package.json                         # 의존성 관리
├── vite.config.ts                       # Vite 설정
├── tsconfig.json                        # TypeScript 설정
├── tailwind.config.js                   # Tailwind 설정
├── .env.development                     # 개발 환경 변수
├── PROGRESS.md                          # 진행 상황
├── PROJECT_STRUCTURE.md                 # 이 파일
└── plan.md                              # 프로젝트 계획서
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

## 🗂 상태 관리 전략 (Pinia)

### Store 구조 (6개)

#### 1. auth.ts - 인증 상태
**Computed:**
- `isAuthenticated`: 로그인 여부
- `isSeller`: 판매자 권한
- `isAdmin`: 관리자 권한

**Actions:**
- `login`, `logout`, `register`, `verifyEmail`
- `loadUser`, `updateUser`, `changePassword`

#### 2. cart.ts - 장바구니
**Computed:**
- `count`: 항목 수
- `totalQuantity`: 전체 수량
- `total`: 총 가격

**Actions:**
- `loadCart`, `loadSummary`, `addToCart`
- `updateQuantity`, `increaseQuantity`, `decreaseQuantity`
- `removeFromCart`, `clearCart`

#### 3. wishlist.ts - 찜 목록
**Computed:**
- `count`: 찜 항목 수
- `productIds`: 찜한 상품 ID 배열

**Actions:**
- `loadWishlist`, `toggleWishlist`, `removeFromWishlist`
- `isWishlisted(productId)`: 찜 여부 확인

#### 4. products.ts - 상품 데이터
**Actions:**
- `fetchProducts(params)`: 상품 목록 (필터링, 검색, 정렬)
- `fetchCategories()`: 카테고리 목록
- `fetchBestProducts()`: 베스트 상품

#### 5. orders.ts - 주문
**Computed:**
- `count`: 주문 수

**Actions:**
- `loadOrders`, `loadOrder`, `createOrder`
- `cancelOrder`, `confirmDelivery`

#### 6. ui.ts - UI 상태
**Actions:**
- 모달: `openLogin`, `closeLogin`, `setAuthMode`
- 드로어: `openCart`, `closeCart`
- 토스트: `showToast(message)`
- 기타: `setScrolled`, `setActiveTab`, `setRedirectPath`

### 컴포저블 함수 (2개)
- **useTimer**: 타임딜 카운트다운 (timer reactive object)
- **useScroll**: 스크롤 이벤트 핸들링 및 유틸리티

## 스타일링 전략

### Tailwind CSS
- 유틸리티 클래스 우선 사용
- 커스텀 클래스는 최소화
- 반응형 디자인 모바일 우선

### 커스텀 스타일
- 전역 애니메이션은 `styles/animations.css`
- 브랜드 색상은 `tailwind.config.js`

## 🌐 API 통신 전략

### Axios 클라이언트 설정 ([client.ts](src/services/api/client.ts))
```typescript
baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
timeout: 30000 // 30초 (이메일 발송 고려)
```

**요청 인터셉터:**
- localStorage의 `access_token`을 Authorization 헤더에 자동 추가

**응답 인터셉터:**
- 401 에러 발생 시 자동 토큰 갱신 시도
- 토큰 갱신 실패 시 로그아웃 처리 (`auth:logout` 이벤트)

### 통합 API 서비스 ([index.ts](src/services/api/index.ts))

6개 도메인으로 분리:
1. **authAPI**: 회원가입, 로그인, 사용자 정보, 비밀번호 변경
2. **productsAPI**: 상품 목록/상세, 카테고리
3. **wishlistAPI**: 찜 추가/삭제/조회, 토글
4. **cartAPI**: 장바구니 CRUD, 요약 조회
5. **ordersAPI**: 주문 생성/조회/취소, 배송 확인
6. **sellersAPI & sellerProductsAPI**: 판매자 관리, 상품 관리

### TypeScript 타입 안정성
- 모든 API 요청/응답 타입 정의
- Generic 활용으로 타입 안전성 보장
- 런타임 오류 최소화

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

