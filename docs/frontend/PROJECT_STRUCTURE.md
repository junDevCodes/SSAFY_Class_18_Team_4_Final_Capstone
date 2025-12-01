# FreshPick 프론트엔드 프로젝트 구조 문서

> **최종 업데이트**: 2025.12.01
> **상태**: 프로덕션 준비 완료

## 🛠 기술 스택

| 분류 | 기술 | 버전 |
|------|------|------|
| **프레임워크** | Vue 3 (Composition API) | 3.5.24 |
| **빌드 도구** | Vite | 7.2.4 |
| **언어** | TypeScript (Strict Mode) | 5.9.3 |
| **상태 관리** | Pinia | 3.0.4 |
| **라우팅** | Vue Router | 4.4.5 |
| **스타일링** | Tailwind CSS | 3.4.18 |
| **아이콘** | Lucide Vue Next | 0.554.0 |
| **HTTP 클라이언트** | Axios | 1.13.2 |

## 📊 프로젝트 통계

| 항목 | 개수 |
|------|------|
| **페이지** | 17개 |
| **컴포넌트** | 12개 (Layout 2, Section 6, UI 4) |
| **Store** | 6개 |
| **API 서비스** | 7개 도메인 |
| **TypeScript 타입** | 2개 주요 파일 |
| **Composables** | 2개 |
| **총 라우트** | 21개 |

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
│   │   └── index.ts                     # 통합 API (7개 도메인)
│   │
│   ├── composables/                     # 재사용 로직
│   │   ├── useTimer.ts                  # 타임딜 카운트다운
│   │   └── useScroll.ts                 # 스크롤 유틸리티
│   │
│   ├── types/                           # TypeScript 타입 정의
│   │   ├── product.ts                   # Product, ProductDetail, Category 등
│   │   └── auth.ts                      # User, LoginRequest/Response 등
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
│   │   └── main.css                     # 전역 스타일 (Tailwind + 애니메이션)
│   │
│   ├── App.vue                          # 루트 컴포넌트
│   ├── main.ts                          # 진입점
│   └── vite-env.d.ts                    # Vite 타입 정의
│
├── public/                              # 정적 파일
│   └── images/
│       └── default-product.svg          # 기본 상품 이미지
│
├── dist/                                # 빌드 결과물
├── index.html                           # HTML 템플릿
├── package.json                         # 의존성 관리
├── vite.config.ts                       # Vite 설정
├── tsconfig.json                        # TypeScript 설정
├── tsconfig.node.json                   # TypeScript Node 설정
├── tailwind.config.js                   # Tailwind 설정
├── postcss.config.js                    # PostCSS 설정
├── .env.development                     # 개발 환경 변수
├── README.md                            # 프로젝트 소개
└── PROJECT_STRUCTURE.md                 # 이 파일
```

---

## 📄 페이지 상세

### 홈 영역
| 페이지 | 파일 | 설명 |
|--------|------|------|
| 메인 | `HomePage.vue` | 히어로, 카테고리, 타임딜, 상품 목록 섹션 배치 |

### 상품 영역
| 페이지 | 파일 | 설명 |
|--------|------|------|
| 검색 | `SearchPage.vue` | 검색 결과 필터링, 정렬 |
| 상세 | `ProductDetailPage.vue` | 상품 정보, 리뷰, 관련 상품 |
| 장바구니 | `CartPage.vue` | 항목 관리, 예상 배송비 |
| 결제 | `CheckoutPage.vue` | 배송지 입력, 결제 정보 |
| 찜 목록 | `WishlistPage.vue` | 찜한 상품 목록 |

### 마이페이지 영역
| 페이지 | 파일 | 설명 |
|--------|------|------|
| 레이아웃 | `mypage/MyPageLayout.vue` | 사이드바 네비게이션 |
| 프로필 | `mypage/ProfilePage.vue` | 개인정보 수정 |
| 주문 내역 | `mypage/OrdersPage.vue` | 주문 목록 (페이지네이션) |
| 주문 상세 | `mypage/OrderDetailPage.vue` | 주문 상세, 취소/배송확인 |

### 판매자 영역
| 페이지 | 파일 | 설명 |
|--------|------|------|
| 등록 | `seller/RegisterPage.vue` | 판매자 등록 폼 |
| 대시보드 | `seller/DashboardPage.vue` | 판매 통계 |
| 상품 관리 | `seller/ProductsPage.vue` | 상품 목록, 상태 변경 |
| 상품 등록 | `seller/ProductCreatePage.vue` | 상품 등록 폼 |
| 상품 수정 | `seller/ProductEditPage.vue` | 상품 수정 폼 |

### 브랜드 영역
| 페이지 | 파일 | 설명 |
|--------|------|------|
| 브랜드몰 | `brand/BrandMallPage.vue` | 판매자 목록 |
| 브랜드 상세 | `brand/BrandDetailPage.vue` | 판매자 상세 및 상품 |

---

## 🧩 컴포넌트 설계

### Layout 컴포넌트 (2개)

| 컴포넌트 | 파일 | 설명 |
|---------|------|------|
| 헤더 | `AppHeader.vue` | 로고, 검색바, 사용자 인증 상태, 장바구니 아이콘 |
| 푸터 | `AppFooter.vue` | 회사 정보, 링크, 소셜 미디어 |

### Section 컴포넌트 (6개)

| 컴포넌트 | 파일 | 설명 |
|---------|------|------|
| 히어로 | `HeroSection.vue` | 메인 프로모션 배너 |
| 카테고리 네비 | `CategoryNav.vue` | 카테고리 선택 네비게이션 |
| 빠른 카테고리 | `QuickCategories.vue` | 빠른 카테고리 그리드 |
| 브랜드 약속 | `BrandPromise.vue` | 브랜드 특징 (신선함, 안전함, 편함) |
| 타임딜 | `TimeDeal.vue` | 실시간 카운트다운 타이머 |
| 상품 목록 | `ProductList.vue` | 상품 그리드 (ProductCard 반복) |

### UI 컴포넌트 (4개)

| 컴포넌트 | 파일 | 설명 |
|---------|------|------|
| 상품 카드 | `ProductCard.vue` | 상품 이미지, 가격, 할인, 별점, 찜 버튼 |
| 로그인 모달 | `LoginModal.vue` | 로그인/회원가입 폼 (이메일 인증) |
| 장바구니 드로어 | `CartDrawer.vue` | 장바구니 아이템 리스트 (추가/제거) |
| 토스트 | `Toast.vue` | 알림 메시지 (2초 표시) |

### 설계 원칙

1. **단일 책임 원칙**: 각 컴포넌트는 하나의 명확한 역할만 수행
2. **Props 타입 정의**: 모든 props는 TypeScript 인터페이스로 정의
3. **이벤트 명명 규칙**:
   - `@update:` - 양방향 바인딩
   - `@change:` - 값 변경
   - `@click:` - 클릭 이벤트
4. **컴포넌트 네이밍**: PascalCase 사용, 명확하고 설명적인 이름

---

## 🗂 상태 관리 전략 (Pinia)

### Store 요약

| 스토어 | 파일 | 역할 | State | Action |
|--------|------|------|-------|--------|
| auth | `auth.ts` | 인증 관리 | 3개 | 8개 |
| cart | `cart.ts` | 장바구니 | 4개 | 11개 |
| wishlist | `wishlist.ts` | 찜 목록 | 3개 | 4개 |
| products | `products.ts` | 상품 캐싱 | 3개 | 3개 |
| orders | `orders.ts` | 주문 관리 | 5개 | 5개 |
| ui | `ui.ts` | UI 상태 | 8개 | 10개 |

### 1. auth.ts - 인증 상태

**State:**
- `user`: 현재 로그인 사용자 정보
- `isLoading`: 로딩 상태
- `error`: 에러 메시지

**Computed:**
- `isAuthenticated`: 로그인 여부
- `isSeller`: 판매자 권한
- `isAdmin`: 관리자 권한

**Actions:**
- `login(email, password)` - 로그인
- `register(email, password, username)` - 회원가입
- `verifyEmail(email, code)` - 이메일 인증
- `logout()` - 로그아웃 (토큰 제거, 다른 store 초기화)
- `loadUser()` - 현재 사용자 정보 로드 (401 시 자동 로그아웃)
- `updateUser(data)` - 사용자 정보 수정
- `changePassword(oldPassword, newPassword)` - 비밀번호 변경

### 2. cart.ts - 장바구니

**State:**
- `items[]`: 장바구니 항목
- `summary`: 요약 정보 (total, count)
- `loading`: 로딩 상태
- `error`: 에러 메시지

**Computed:**
- `count`: 항목 수
- `totalQuantity`: 전체 수량
- `total`: 총 가격

**Actions:**
- `loadCart()` - 장바구니 항목 로드
- `loadSummary()` - 요약 정보 로드
- `addToCart(product, quantity)` - 장바구니 추가 (중복 시 수량 증가)
- `updateQuantity(id, quantity)` - 수량 변경
- `increaseQuantity(id)` / `decreaseQuantity(id)` - 수량 증감
- `removeFromCart(id)` - 항목 삭제
- `clearCart()` - 장바구니 비우기

### 3. wishlist.ts - 찜 목록

**State:**
- `items[]`: 찜 항목
- `loading`: 로딩 상태
- `error`: 에러 메시지

**Computed:**
- `count`: 찜 항목 수
- `productIds`: 찜한 상품 ID 배열
- `isWishlisted(productId)`: 찜 여부 확인 함수

**Actions:**
- `loadWishlist()` - 찜 목록 로드
- `toggleWishlist(product)` - 찜 추가/제거 토글
- `removeFromWishlist(id)` - 찜 삭제

### 4. products.ts - 상품 데이터

**State:**
- `products[]`: 상품 목록
- `categories[]`: 카테고리 목록
- `loading`: 로딩 상태
- `error`: 에러 메시지

**Actions:**
- `fetchProducts(params)` - 상품 목록 (필터링, 검색, 정렬)
- `fetchCategories()` - 카테고리 목록
- `fetchBestProducts()` - 베스트 상품만 조회

### 5. orders.ts - 주문

**State:**
- `orders[]`: 주문 목록
- `currentOrder`: 현재 주문 상세
- `loading`: 로딩 상태
- `error`: 에러 메시지
- `total`: 전체 주문 수

**Computed:**
- `count`: 주문 수

**Actions:**
- `loadOrders(params)` - 주문 목록 로드 (페이지네이션)
- `loadOrder(id)` - 주문 상세 로드
- `createOrder(data)` - 주문 생성
- `cancelOrder(id, reason)` - 주문 취소
- `confirmDelivery(id)` - 배송 완료 확인

### 6. ui.ts - UI 상태

**State:**
- `isScrolled`: 스크롤 상태
- `isCartOpen`: 장바구니 드로어 상태
- `isLoginOpen`: 로그인 모달 상태
- `activeTab`: 활성 탭
- `authMode`: 로그인/회원가입 모드
- `showVerification`: 인증 번호 입력 표시
- `toast`: 토스트 메시지 상태
- `redirectPath`: 로그인 후 리다이렉트 경로

**Actions:**
- `setScrolled(value)` - 스크롤 상태
- `openCart()` / `closeCart()` - 장바구니 드로어
- `openLogin()` / `closeLogin()` - 로그인 모달
- `setAuthMode(mode)` - 로그인/회원가입 모드 전환
- `setShowVerification(value)` - 인증 번호 입력 표시
- `showToast(message)` - 토스트 알림 (2초 후 자동 사라짐)
- `setActiveTab(tab)` - 활성 탭 변경
- `setRedirectPath(path)` - 로그인 후 리다이렉트 경로

---

## 🧰 Composables

### useTimer.ts
**목적**: 타임딜 카운트다운 타이머

```typescript
const { timer, startTimer, stopTimer } = useTimer()
// timer: { hours, minutes, seconds } 반응형 객체
// startTimer(): 매초 시간 계산 (23:59:59 - 현재시간)
// stopTimer(): 인터벌 정리
```

**라이프사이클**: mounted에서 자동 시작, unmounted에서 정리

### useScroll.ts
**목적**: 스크롤 이벤트 감지 및 제어

```typescript
const { scrollToTop, scrollToContent } = useScroll()
// scrollToTop(): 부드럽게 페이지 상단으로 스크롤
// scrollToContent(): #sticky-nav 요소로 스크롤
```

**기능**: scrollY > 50px 시 UI 상태 변경 감지

---

## 🌐 API 통신 전략

### Axios 클라이언트 설정 (client.ts)

```typescript
baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
timeout: 30000 // 30초 (이메일 발송 고려)
```

**요청 인터셉터:**
- localStorage의 `access_token`을 Authorization 헤더에 자동 추가

**응답 인터셉터:**
- 401 에러 발생 시 자동 토큰 갱신 시도
- 토큰 갱신 실패 시 로그아웃 처리 (`auth:logout` 이벤트)

**스킵되는 엔드포인트** (토큰 갱신 안 함):
- `/auth/register/`, `/auth/login/`, `/auth/register/verify/`
- `/auth/token/refresh/`
- `/auth/google/`, `/auth/google/callback/`
- `/auth/kakao/`, `/auth/kakao/callback/`

### 통합 API 서비스 (index.ts)

| API 도메인 | 엔드포인트 | 주요 메서드 |
|-----------|-----------|-----------|
| **authAPI** | `/auth/` | register, verifyEmail, login, logout, getCurrentUser, updateUser, changePassword, refreshToken |
| **productsAPI** | `/api/products/` | getProducts (필터링), getProduct (slug), getCategories |
| **wishlistAPI** | `/api/wishlist/` | getWishlist, addToWishlist, removeFromWishlist, toggleWishlist |
| **cartAPI** | `/api/cart/` | getCart, getCartSummary, addToCart, updateCartItem, removeFromCart, clearCart |
| **ordersAPI** | `/api/orders/` | getOrders, getOrder, createOrder, cancelOrder, confirmDelivery |
| **sellersAPI** | `/api/sellers/` | getSellers, getSeller, getMySellerProfile, registerAsSeller, updateSeller, getDashboard |
| **sellerProductsAPI** | `/api/seller-products/` | getMyProducts, createProduct, updateProduct, deleteProduct, publishProduct, unpublishProduct, addProductImages |

---

## 📝 TypeScript 타입 정의

### auth.ts - 인증 관련 타입

```typescript
// 요청 타입
LoginRequest { email, password }
SignupRequest { email, password, username? }
EmailVerificationRequest { email, code }

// 응답 타입
RegisterResponse { email, detail, expires_at, verification_code? }
VerificationResponse { detail }
AuthResponse { access, refresh, user }

// 사용자 타입
User {
  id, email, username, first_name, last_name, name?, phone?,
  postal_code, address, address_detail, profile_image_url,
  provider, role: 'guest' | 'user' | 'seller' | 'admin',
  timezone, created_at, last_login
}
```

### product.ts - 상품 관련 타입

```typescript
// 기본 타입
Category { id, name, slug, created_at, updated_at }
SellerBrief { brand_name, brand_slug, average_rating, total_products }
ProductImage { id, image_url, alt_text, display_order, width, height, format }

// 상품 타입
Product {
  id, slug, name, price, original_price, discount_rate,
  main_image, category_name,
  is_featured, is_best, is_new, is_on_sale,
  quality_score, view_count, average_rating, review_count
}

ProductDetail extends Product {
  description, short_description,
  images: ProductImage[],
  stock_quantity, min/max_order_quantity,
  shipping_fee, expected_delivery_days,
  ingredients, nutrition_info, storage_method,
  related_products: Product[],
  is_wishlist: boolean
}

// 장바구니/찜 타입
CartItem { id, product, quantity, subtotal, created_at, updated_at }
WishlistItem { id, product, created_at }

// 응답 타입
ProductListResponse { count, next, previous, results: Product[] }
```

**헬퍼 함수:**
- `getProductImage(product)` - 상품 이미지 URL 반환
- `formatPrice(price)` - 한국 원화 형식 포맷
- `calculateDiscountRate(original, current)` - 할인율 계산
- `isProductDetail(product)` - 타입 가드

---

## 🛤 라우팅 설정

### 라우트 구조 (21개)

**공개 라우트** (누구나 접근):
- `/` - HomePage
- `/search` - SearchPage
- `/products/:slug` - ProductDetailPage
- `/brands` - BrandMallPage
- `/brands/:slug` - BrandDetailPage

**인증 필요 라우트** (`requiresAuth: true`):
- `/cart` - CartPage
- `/wishlist` - WishlistPage
- `/checkout` - CheckoutPage
- `/mypage/**` - 마이페이지 하위 라우트

**판매자 전용 라우트** (`requiresAuth: true, requiresSeller: true`):
- `/seller/register` - RegisterPage
- `/seller/dashboard` - DashboardPage
- `/seller/products` - ProductsPage
- `/seller/products/create` - ProductCreatePage
- `/seller/products/:id/edit` - ProductEditPage

### 네비게이션 가드

```typescript
// 1. 페이지 타이틀 설정
document.title = `${to.meta.title} | 농산물 전자상거래`

// 2. 인증 필요 체크
if (to.meta.requiresAuth && !authStore.isAuthenticated) {
  // 로그인 모달 열기 + 경로 저장
  window.dispatchEvent(new CustomEvent('auth:requireLogin'))
  return next(false)
}

// 3. 판매자 권한 체크
if (to.meta.requiresSeller && !authStore.isSeller) {
  return next('/seller/register')
}
```

### 스크롤 동작
- 저장된 위치 복원
- 해시 앵커 스크롤
- 기본값: 상단으로

---

## 🎨 스타일링 전략

### Tailwind CSS 설정 (tailwind.config.js)

**커스텀 색상:**
```javascript
colors: {
  brand: {
    50: '#f3e8f5',    // 가장 밝음
    500: '#5f0080',   // 기본 보라색
    600: '#4c0066',   // 어두운 보라색
    900: '#2d003d',   // 가장 어두움
  },
  gray: {
    850: '#1f2937',
    900: '#111827',
  },
  kakao: '#FEE500',   // 카카오 노란색
  google: '#FFFFFF'   // 구글 흰색
}
```

**커스텀 폰트:**
```javascript
fontFamily: {
  sans: ['Pretendard Variable', 'Pretendard', 'sans-serif'],
  display: ['GmarketSans', 'sans-serif'],  // 제목용
}
```

### 전역 스타일 (main.css)

**CSS 변수:**
- `--font-main`, `--font-display`
- `--primary`, `--primary-dark`

**애니메이션:**
- `fade` - 0.5s 페이드 트랜지션
- `header-transition` - 0.4s cubic-bezier 헤더 트랜지션
- `@keyframes float` - 떠있는 효과
- `@keyframes fade-in-up` - 아래에서 올라오는 효과
- `drawer-slide` - 드로어 슬라이드
- `toast`, `modal` - 알림 및 모달 애니메이션

**유틸리티:**
- `.no-scrollbar` - 스크롤바 숨김

---

## 🔧 설정 파일

### vite.config.ts

```typescript
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')  // @로 src 폴더 접근
    },
  },
  server: {
    port: 3000,    // 개발 서버 포트
    open: true,    // 자동 브라우저 열기
  },
})
```

### tsconfig.json

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "ESNext",
    "strict": true,                     // 엄격한 타입 체크
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "paths": {
      "@/*": ["src/*"]                  // @ 별칭
    }
  }
}
```

---

## 📦 의존성

### devDependencies

| 패키지 | 버전 | 용도 |
|--------|------|------|
| @types/node | ^24.10.1 | Node.js 타입 정의 |
| @vitejs/plugin-vue | ^6.0.2 | Vite Vue 플러그인 |
| autoprefixer | ^10.4.22 | CSS 브라우저 호환성 |
| postcss | ^8.5.6 | CSS 후처리 |
| tailwindcss | ^3.4.18 | 유틸리티 CSS |
| typescript | ^5.9.3 | TypeScript |
| vite | ^7.2.4 | 번들러/개발 서버 |
| vue | ^3.5.24 | Vue 3 |
| vue-tsc | ^3.1.4 | Vue TypeScript 컴파일러 |

### dependencies

| 패키지 | 버전 | 용도 |
|--------|------|------|
| axios | ^1.13.2 | HTTP 클라이언트 |
| lucide-vue-next | ^0.554.0 | 아이콘 라이브러리 |
| pinia | ^3.0.4 | 상태 관리 |
| vue-router | ^4.4.5 | 라우팅 |

---

## 🚀 개발 명령어

```bash
# 개발 서버 실행 (localhost:3000)
npm run dev

# 타입 체크
npm run type-check

# 프로덕션 빌드 (타입 체크 후 빌드)
npm run build

# 빌드 결과 미리보기
npm run preview
```

---

## 🔐 인증 플로우

### JWT 토큰 관리
1. 로그인 성공 시 `access_token`, `refresh_token` localStorage에 저장
2. 모든 API 요청 시 Authorization 헤더에 토큰 자동 추가
3. 401 에러 시 `refresh_token`으로 자동 갱신 시도
4. 갱신 실패 시 로그아웃 처리 및 로그인 모달 표시

### OAuth 콜백 처리
1. OAuth 로그인 후 리다이렉트 URL에서 토큰 파라미터 추출
2. `handleOAuthCallback()` 함수로 토큰 저장
3. URL 파라미터 제거 후 메인 페이지로 이동

### 역할 기반 접근 제어
- `guest`: 미인증 사용자
- `user`: 일반 회원
- `seller`: 판매자 (상품 등록/관리 가능)
- `admin`: 관리자

---

## ⚡ 성능 최적화

1. **Lazy Loading**: 페이지 동적 import
2. **API 캐싱**: products store에서 데이터 캐싱
3. **인터셉터**: 중복 토큰 갱신 요청 방지
4. **타입 안정성**: TypeScript strict mode로 런타임 에러 최소화
5. **코드 스플리팅**: Vite의 자동 코드 분할

---

## 📚 관련 문서

- [README.md](README.md) - 프로젝트 소개
- [../CLAUDE.md](../CLAUDE.md) - 전체 프로젝트 가이드
- [../docs/CODE_CONVENTION.md](../docs/CODE_CONVENTION.md) - 코드 컨벤션
- [../docs/GIT_CONVENTION.md](../docs/GIT_CONVENTION.md) - Git 컨벤션
