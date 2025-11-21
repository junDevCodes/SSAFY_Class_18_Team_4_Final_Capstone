# FreshPick Vue 3 변환 프로젝트 계획서

## 프로젝트 개요
- **목표**: `index_demo.html`을 Vue 3.0 프레임워크로 완전 변환
- **요구사항**: 백엔드 연결 가능한 수준의 정교한 구현, 유지보수 가능한 구조
- **기술 스택**: Vue 3.4+, Vite 5+, Pinia, TypeScript, Tailwind CSS

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

### Phase 6: 테스트 및 최적화
- [ ] 컴포넌트 테스트
- [ ] 성능 최적화
- [ ] 접근성 검증
- [ ] 브라우저 호환성 테스트

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

## 진행 상황 추적

### 현재 단계: Phase 6 - 테스트 및 최적화
### 완료된 작업: 
- ✅ 프로젝트 초기 설정 완료
- ✅ 모든 컴포넌트 구현 완료
- ✅ 상태 관리 및 API 레이어 구현 완료
- ✅ 스타일링 및 애니메이션 적용 완료
- ✅ 백엔드 연동 준비 완료

### 다음 작업: 테스트 및 최적화

## 참고 사항
- 모든 주석은 한국어로 작성
- 컴포넌트는 단일 책임 원칙 준수
- TypeScript 타입 정의 필수
- 반응형 디자인 모바일 우선
- 접근성 고려 (ARIA 속성 등)

