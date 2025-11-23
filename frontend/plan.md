# FreshPick Vue 3 프론트엔드 개발 계획서

> **최종 업데이트**: 2025.11.24
> **프로젝트 상태**: Phase 1-5 완료, Phase 6 진행 중

## 프로젝트 개요
- **목표**: 농산물 전자상거래 플랫폼의 완전한 프론트엔드 구축
- **요구사항**: 백엔드 API 완전 통합, TypeScript 타입 안정성, 프로덕션 준비
- **기술 스택**: Vue 3.5+, Vite 7+, Pinia, TypeScript 5+, Tailwind CSS 3+

## 작업 단계

### Phase 1: 프로젝트 초기 설정 ✅
- [x] plan.md 작성
- [x] Vue 3 + Vite 프로젝트 생성
- [x] TypeScript 설정
- [x] Tailwind CSS 설정
- [x] Pinia 상태 관리 설정
- [x] 프로젝트 구조 설계

### Phase 2: 컴포넌트 분리 및 구현 ✅
- [x] App.vue 메인 컴포넌트
- [x] Header 컴포넌트 (로고, 검색, 로그인, 장바구니)
- [x] Hero 섹션 컴포넌트
- [x] CategoryNav 컴포넌트 (Sticky)
- [x] QuickCategories 컴포넌트
- [x] BrandPromise 컴포넌트
- [x] TimeDeal 컴포넌트
- [x] ProductList 컴포넌트
- [x] ProductCard 컴포넌트
- [x] Footer 컴포넌트
- [x] LoginModal 컴포넌트
- [x] CartDrawer 컴포넌트
- [x] Toast 컴포넌트

### Phase 3: 상태 관리 및 로직 구현 ✅
- [x] Pinia Store 생성 (cart, auth, products, ui)
- [x] API 서비스 레이어 구현
- [x] 유틸리티 함수 구현 (formatPrice, scroll 등)
- [x] 컴포저블 함수 구현 (useCart, useAuth, useTimer 등)

### Phase 4: 스타일링 및 애니메이션 ✅
- [x] Tailwind CSS 커스텀 설정
- [x] 전역 스타일 설정
- [x] 애니메이션 및 트랜지션 구현
- [x] 반응형 디자인 검증

### Phase 5: 백엔드 연동 준비 ✅
- [x] API 인터페이스 정의
- [x] Axios 인스턴스 설정
- [x] 에러 핸들링 구현
- [x] 로딩 상태 관리

### Phase 6: 테스트 및 최적화 🚧
- [ ] **Unit 테스트 작성** (Vitest)
  - [ ] Store 액션 테스트
  - [ ] Composable 함수 테스트
  - [ ] 유틸리티 함수 테스트

- [ ] **E2E 테스트** (Playwright)
  - [ ] 회원가입/로그인 플로우
  - [ ] 상품 검색/구매 플로우
  - [ ] 판매자 상품 등록 플로우

- [ ] **성능 최적화**
  - [ ] 이미지 lazy loading 개선
  - [ ] 코드 스플리팅 최적화
  - [ ] 번들 사이즈 분석 및 축소
  - [ ] Lighthouse 점수 90+ 달성

- [ ] **접근성 개선**
  - [ ] ARIA 속성 추가
  - [ ] 키보드 네비게이션 개선
  - [ ] 스크린 리더 지원 검증

- [ ] **브라우저 호환성 테스트**
  - [ ] Chrome, Firefox, Safari, Edge 테스트
  - [ ] 모바일 브라우저 테스트

## 프로젝트 구조

```
front_demo_2/
├── src/
│   ├── assets/          # 정적 파일
│   ├── components/      # Vue 컴포넌트
│   │   ├── layout/     # 레이아웃 컴포넌트
│   │   ├── sections/   # 섹션 컴포넌트
│   │   └── ui/         # UI 컴포넌트
│   ├── composables/    # Composition API 함수
│   ├── stores/         # Pinia 스토어
│   ├── services/       # API 서비스
│   ├── utils/          # 유틸리티 함수
│   ├── types/          # TypeScript 타입 정의
│   ├── styles/         # 전역 스타일
│   ├── App.vue
│   └── main.ts
├── public/             # 공개 파일
├── package.json
├── vite.config.ts
├── tsconfig.json
├── tailwind.config.js
└── plan.md
```

## 컴포넌트 설계

### Layout Components
- **AppHeader**: 헤더 (로고, 검색, 로그인, 장바구니)
- **AppFooter**: 푸터

### Section Components
- **HeroSection**: 히어로 섹션
- **CategoryNav**: 카테고리 네비게이션 (Sticky)
- **QuickCategories**: 빠른 카테고리
- **BrandPromise**: 브랜드 약속
- **TimeDeal**: 타임딜
- **ProductList**: 상품 리스트

### UI Components
- **ProductCard**: 상품 카드
- **LoginModal**: 로그인/회원가입 모달
- **CartDrawer**: 장바구니 드로어
- **Toast**: 토스트 알림

## 상태 관리 설계

### Stores (Pinia)
- **useCartStore**: 장바구니 상태 관리
- **useAuthStore**: 인증 상태 관리
- **useProductStore**: 상품 데이터 관리
- **useUIStore**: UI 상태 관리 (모달, 토스트 등)

## API 인터페이스 설계

### Products API
- `GET /api/products` - 상품 목록 조회
- `GET /api/products/:id` - 상품 상세 조회

### Auth API
- `POST /api/auth/login` - 로그인
- `POST /api/auth/signup` - 회원가입
- `POST /api/auth/verify` - 이메일 인증

### Cart API
- `GET /api/cart` - 장바구니 조회
- `POST /api/cart` - 장바구니 추가
- `PUT /api/cart/:id` - 장바구니 수량 변경
- `DELETE /api/cart/:id` - 장바구니 삭제

## 📊 진행 상황 추적 (2025.11.24 기준)

### 현재 단계: Phase 6 - 테스트 및 최적화 🚧

### 완료된 작업:
- ✅ **Phase 1**: 프로젝트 초기 설정 (100%)
- ✅ **Phase 2**: 모든 컴포넌트 구현 (100% - 12개)
- ✅ **Phase 3**: 상태 관리 및 로직 (100% - 6개 Store)
- ✅ **Phase 4**: 스타일링 및 애니메이션 (100%)
- ✅ **Phase 5**: 백엔드 연동 완료 (100%)
- 🚧 **Phase 6**: 테스트 및 최적화 (20%)

### 전체 진행률: **95%**

### 다음 우선순위:
1. Unit 테스트 작성 (Vitest)
2. E2E 테스트 구현 (Playwright)
3. 성능 최적화 (Lighthouse)
4. 접근성 개선 (ARIA, 키보드)

## 참고 사항
- 모든 주석은 한국어로 작성
- 컴포넌트는 단일 책임 원칙 준수
- TypeScript 타입 정의 필수
- 반응형 디자인 모바일 우선
- 접근성 고려 (ARIA 속성 등)

