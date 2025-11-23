# 농산물 직거래 플랫폼 - 데이터베이스 ERD 설계

## 1. 개요

### 1.1 설계 원칙
- **완전 정규화**: 3NF 이상, 중복 최소화
- **확장성**: 신규 기능 추가 시 스키마 변경 최소화
- **성능**: 인덱스 최적화, 쿼리 효율성 고려
- **추천 알고리즘 대비**: 사용자 행동 로그 상세 수집
- **유연성**: 선택적 필드는 nullable 처리

### 1.2 기술 스택
- **프로덕션**: PostgreSQL 14+
- **개발**: SQLite3
- **ORM**: Django ORM
- **마이그레이션**: Django Migrations

---

## 2. 핵심 엔티티 설계

### 2.1 사용자 관리 (User Management)

#### 2.1.1 User (사용자)
```sql
CREATE TABLE users (
    -- 기본 정보
    id BIGSERIAL PRIMARY KEY,
    username VARCHAR(150) UNIQUE NOT NULL,
    email VARCHAR(254) UNIQUE NOT NULL,
    password VARCHAR(128) NOT NULL,  -- 해시값

    -- 역할 및 권한
    role VARCHAR(20) NOT NULL DEFAULT 'guest',
    -- 'guest', 'user', 'seller', 'admin'

    -- 인증 정보
    provider VARCHAR(20) NOT NULL DEFAULT 'email',
    -- 'email', 'google', 'kakao', 'naver', 'apple'
    provider_id VARCHAR(255) NULL,
    is_email_verified BOOLEAN DEFAULT FALSE,
    email_verification_code VARCHAR(64) NULL,

    -- 프로필
    profile_image_url TEXT NULL,
    phone_number VARCHAR(20) NULL,  -- 향후 인증용
    date_of_birth DATE NULL,
    gender VARCHAR(10) NULL,  -- 'male', 'female', 'other', 'prefer_not_to_say'

    -- 설정
    timezone VARCHAR(64) DEFAULT 'Asia/Seoul',
    language VARCHAR(10) DEFAULT 'ko',
    notification_enabled BOOLEAN DEFAULT TRUE,
    marketing_agreed BOOLEAN DEFAULT FALSE,

    -- 상태
    is_active BOOLEAN DEFAULT TRUE,
    is_staff BOOLEAN DEFAULT FALSE,
    is_superuser BOOLEAN DEFAULT FALSE,
    last_login TIMESTAMP NULL,

    -- 메타데이터
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP NULL,  -- 소프트 삭제

    -- 인덱스
    INDEX idx_user_email (email),
    INDEX idx_user_role (role),
    INDEX idx_user_provider (provider, provider_id),
    INDEX idx_user_created_at (created_at)
);
```

**Django 모델 확장 사항:**
```python
class User(AbstractUser):
    ROLE_CHOICES = [
        ('guest', '비회원'),
        ('user', '일반회원'),
        ('seller', '판매자'),
        ('admin', '관리자'),
    ]

    PROVIDER_CHOICES = [
        ('email', '이메일'),
        ('google', 'Google'),
        ('kakao', 'Kakao'),
        ('naver', 'Naver'),
        ('apple', 'Apple'),
    ]

    # 기존 필드 외 추가
    phone_number = PhoneNumberField(null=True, blank=True)  # django-phonenumber-field
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=20, null=True, blank=True)
```

#### 2.1.2 UserAddress (배송지)
```sql
CREATE TABLE user_addresses (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- 주소 정보
    name VARCHAR(100) NOT NULL,  -- 배송지명 (집, 회사 등)
    recipient_name VARCHAR(100) NOT NULL,
    recipient_phone VARCHAR(20) NOT NULL,

    postal_code VARCHAR(10) NOT NULL,
    address_line1 VARCHAR(255) NOT NULL,  -- 기본 주소
    address_line2 VARCHAR(255) NULL,      -- 상세 주소
    city VARCHAR(100) NOT NULL,
    state VARCHAR(100) NOT NULL,
    country VARCHAR(2) DEFAULT 'KR',      -- ISO 3166-1 alpha-2

    -- 위치 정보 (향후 거리 기반 추천용)
    latitude DECIMAL(10, 8) NULL,
    longitude DECIMAL(11, 8) NULL,

    -- 설정
    is_default BOOLEAN DEFAULT FALSE,

    -- 메타데이터
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_user_addresses_user_id (user_id),
    INDEX idx_user_addresses_default (user_id, is_default)
);
```

#### 2.1.3 UserPaymentMethod (결제 수단)
```sql
CREATE TABLE user_payment_methods (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- 결제 수단 정보
    type VARCHAR(20) NOT NULL,
    -- 'credit_card', 'debit_card', 'bank_account', 'virtual_account', 'mobile'

    provider VARCHAR(50) NOT NULL,
    -- 'kakaopay', 'naverpay', 'tosspay', 'payco', 'card'

    -- 카드 정보 (암호화 필요)
    card_number_last4 VARCHAR(4) NULL,  -- 마지막 4자리만 저장
    card_issuer VARCHAR(50) NULL,       -- 카드사
    card_type VARCHAR(20) NULL,         -- 'credit', 'debit', 'prepaid'

    -- 계좌 정보
    bank_name VARCHAR(50) NULL,
    account_number_last4 VARCHAR(4) NULL,

    -- PG사 토큰
    payment_gateway_token TEXT NULL,  -- PG사에서 발급한 빌링키

    -- 설정
    is_default BOOLEAN DEFAULT FALSE,

    -- 메타데이터
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NULL,  -- 카드 유효기간

    INDEX idx_user_payment_user_id (user_id),
    INDEX idx_user_payment_default (user_id, is_default)
);
```

---

### 2.2 판매자 관리 (Seller Management)

#### 2.2.1 Seller (판매자)
```sql
CREATE TABLE sellers (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- 브랜드 정보
    brand_name VARCHAR(200) UNIQUE NOT NULL,
    brand_name_en VARCHAR(200) UNIQUE NULL,
    brand_slug VARCHAR(200) UNIQUE NOT NULL,
    brand_description TEXT NULL,
    brand_logo_url TEXT NULL,
    brand_banner_url TEXT NULL,

    -- 사업자 정보
    business_registration_number VARCHAR(20) UNIQUE NULL,  -- 사업자등록번호
    business_type VARCHAR(20) NULL,  -- 'individual', 'corporate', 'cooperative'
    company_name VARCHAR(200) NULL,
    ceo_name VARCHAR(100) NULL,

    -- 인증 정보
    is_verified BOOLEAN DEFAULT FALSE,
    verified_at TIMESTAMP NULL,
    verification_document_url TEXT NULL,

    -- 연락처
    business_phone VARCHAR(20) NULL,
    business_email VARCHAR(254) NULL,
    customer_service_phone VARCHAR(20) NULL,

    -- 주소
    business_address TEXT NULL,
    warehouse_address TEXT NULL,

    -- 정산 정보
    bank_name VARCHAR(50) NULL,
    bank_account_number VARCHAR(50) NULL,  -- 암호화 필요
    account_holder_name VARCHAR(100) NULL,

    -- 운영 정보
    min_order_amount INTEGER DEFAULT 0,
    shipping_fee INTEGER DEFAULT 0,
    free_shipping_threshold INTEGER NULL,

    -- 통계 (비정규화 - 성능 최적화)
    total_products INTEGER DEFAULT 0,
    total_sales INTEGER DEFAULT 0,
    total_reviews INTEGER DEFAULT 0,
    average_rating DECIMAL(3, 2) DEFAULT 0.00,

    -- 상태
    status VARCHAR(20) DEFAULT 'pending',
    -- 'pending', 'active', 'suspended', 'inactive'

    -- 메타데이터
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_seller_user_id (user_id),
    INDEX idx_seller_brand_slug (brand_slug),
    INDEX idx_seller_status (status),
    INDEX idx_seller_verified (is_verified)
);
```

#### 2.2.2 SellerOperatingHours (영업 시간)
```sql
CREATE TABLE seller_operating_hours (
    id BIGSERIAL PRIMARY KEY,
    seller_id BIGINT NOT NULL REFERENCES sellers(id) ON DELETE CASCADE,

    day_of_week SMALLINT NOT NULL,  -- 0=월, 1=화, ..., 6=일
    open_time TIME NOT NULL,
    close_time TIME NOT NULL,
    is_open BOOLEAN DEFAULT TRUE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(seller_id, day_of_week),
    INDEX idx_seller_hours_seller_id (seller_id)
);
```

---

### 2.3 상품 관리 (Product Management)

#### 2.3.1 Category (카테고리)
```sql
CREATE TABLE categories (
    id BIGSERIAL PRIMARY KEY,

    -- 계층 구조 (Nested Set Model 또는 Path Enumeration)
    parent_id BIGINT NULL REFERENCES categories(id) ON DELETE SET NULL,
    path VARCHAR(255) NOT NULL,  -- 예: '/1/5/12/' (조상 경로)
    level SMALLINT DEFAULT 0,    -- 깊이 (0=최상위)

    -- 기본 정보
    name VARCHAR(100) NOT NULL,
    name_en VARCHAR(100) NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    description TEXT NULL,

    -- 이미지
    icon_url TEXT NULL,
    image_url TEXT NULL,

    -- 정렬 및 표시
    display_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    is_featured BOOLEAN DEFAULT FALSE,  -- 메인에 노출

    -- 메타데이터
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_category_parent_id (parent_id),
    INDEX idx_category_path (path),
    INDEX idx_category_slug (slug),
    INDEX idx_category_active_featured (is_active, is_featured)
);
```

#### 2.3.2 Product (상품 - 메인 + 판매자 통합)
```sql
CREATE TABLE products (
    id BIGSERIAL PRIMARY KEY,

    -- 상품 유형
    product_type VARCHAR(20) NOT NULL DEFAULT 'main',
    -- 'main' (크롤링/관리자 등록), 'seller' (판매자 등록)

    -- 관계
    category_id BIGINT NULL REFERENCES categories(id) ON DELETE SET NULL,
    seller_id BIGINT NULL REFERENCES sellers(id) ON DELETE CASCADE,
    -- seller_id는 product_type='seller'일 때만 NOT NULL

    -- 크롤링 메타데이터 (main 상품용)
    source_site VARCHAR(100) NULL,  -- 'naver', 'coupang' 등
    source_url TEXT NULL,
    crawled_at TIMESTAMP NULL,

    -- 기본 정보
    name VARCHAR(500) NOT NULL,
    name_en VARCHAR(500) NULL,
    slug VARCHAR(500) NULL,  -- SEO용
    short_description TEXT NULL,
    description TEXT NULL,

    -- 가격 정보
    price INTEGER NOT NULL CHECK (price >= 0),
    original_price INTEGER NULL CHECK (original_price >= 0),
    discount_rate SMALLINT DEFAULT 0 CHECK (discount_rate BETWEEN 0 AND 100),
    cost_price INTEGER NULL,  -- 원가 (판매자만)

    -- 단위
    unit VARCHAR(50) NULL,  -- 'kg', 'g', '개', '박스' 등
    unit_quantity DECIMAL(10, 2) DEFAULT 1.00,  -- 예: 1.5kg

    -- 재고 (판매자 상품만 사용)
    stock_quantity INTEGER DEFAULT 0,
    low_stock_threshold INTEGER DEFAULT 10,
    is_in_stock BOOLEAN DEFAULT TRUE,

    -- 이미지
    main_image_url TEXT NOT NULL,

    -- 상품 품질 점수 (추천 알고리즘용)
    quality_score DECIMAL(5, 2) DEFAULT 50.00 CHECK (quality_score BETWEEN 0 AND 100),
    -- 이미지 품질, 설명 완성도, CTR 등을 종합

    image_quality_score DECIMAL(5, 2) DEFAULT 50.00,  -- 이미지 유효성 점수
    content_quality_score DECIMAL(5, 2) DEFAULT 50.00, -- 설명 완성도 점수

    -- 통계 (비정규화 - 성능 최적화)
    view_count INTEGER DEFAULT 0,
    click_count INTEGER DEFAULT 0,
    cart_count INTEGER DEFAULT 0,
    wishlist_count INTEGER DEFAULT 0,
    purchase_count INTEGER DEFAULT 0,
    review_count INTEGER DEFAULT 0,
    average_rating DECIMAL(3, 2) DEFAULT 0.00,

    -- CTR (Click-Through Rate)
    ctr DECIMAL(5, 4) DEFAULT 0.0000,  -- click_count / view_count

    -- 배송 정보
    shipping_required BOOLEAN DEFAULT TRUE,
    shipping_fee INTEGER DEFAULT 0,
    free_shipping_threshold INTEGER NULL,
    estimated_delivery_days SMALLINT NULL,

    -- 상태
    status VARCHAR(20) DEFAULT 'active',
    -- 'draft', 'active', 'inactive', 'out_of_stock', 'discontinued'

    is_featured BOOLEAN DEFAULT FALSE,  -- 추천 상품
    is_best BOOLEAN DEFAULT FALSE,      -- 베스트 상품
    is_new BOOLEAN DEFAULT FALSE,       -- 신상품
    is_on_sale BOOLEAN DEFAULT FALSE,   -- 할인 중

    -- 메타데이터
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    published_at TIMESTAMP NULL,

    -- SEO
    meta_title VARCHAR(200) NULL,
    meta_description TEXT NULL,
    meta_keywords VARCHAR(500) NULL,

    -- 인덱스
    INDEX idx_product_type (product_type),
    INDEX idx_product_category (category_id),
    INDEX idx_product_seller (seller_id),
    INDEX idx_product_status (status),
    INDEX idx_product_quality_score (quality_score DESC),
    INDEX idx_product_view_count (view_count DESC),
    INDEX idx_product_ctr (ctr DESC),
    INDEX idx_product_created_at (created_at DESC),
    INDEX idx_product_featured (is_featured, status),
    INDEX idx_product_best (is_best, status),
    INDEX idx_product_slug (slug),

    -- 복합 인덱스 (추천 알고리즘용)
    INDEX idx_product_recommend (product_type, status, quality_score DESC, ctr DESC),
    INDEX idx_product_category_recommend (category_id, status, quality_score DESC)
);
```

#### 2.3.3 ProductImage (상품 이미지)
```sql
CREATE TABLE product_images (
    id BIGSERIAL PRIMARY KEY,
    product_id BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,

    image_url TEXT NOT NULL,
    alt_text VARCHAR(255) NULL,
    display_order INTEGER DEFAULT 0,

    -- 이미지 메타데이터
    width INTEGER NULL,
    height INTEGER NULL,
    file_size INTEGER NULL,  -- bytes
    format VARCHAR(10) NULL,  -- 'jpg', 'png', 'webp'

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_product_image_product_id (product_id),
    INDEX idx_product_image_order (product_id, display_order)
);
```

#### 2.3.4 ProductOption (상품 옵션)
```sql
CREATE TABLE product_options (
    id BIGSERIAL PRIMARY KEY,
    product_id BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,

    -- 옵션 정보
    name VARCHAR(100) NOT NULL,  -- 예: '중량', '색상'
    display_order INTEGER DEFAULT 0,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_product_option_product_id (product_id)
);

CREATE TABLE product_option_values (
    id BIGSERIAL PRIMARY KEY,
    option_id BIGINT NOT NULL REFERENCES product_options(id) ON DELETE CASCADE,

    value VARCHAR(100) NOT NULL,  -- 예: '1kg', '2kg'
    price_adjustment INTEGER DEFAULT 0,  -- 가격 조정
    stock_quantity INTEGER DEFAULT 0,
    is_available BOOLEAN DEFAULT TRUE,
    display_order INTEGER DEFAULT 0,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_option_value_option_id (option_id)
);
```

---

### 2.4 주문 및 결제 (Order & Payment)

#### 2.4.1 Order (주문)
```sql
CREATE TABLE orders (
    id BIGSERIAL PRIMARY KEY,
    order_number VARCHAR(50) UNIQUE NOT NULL,  -- 주문번호 (예: ORD-20250123-000001)

    -- 주문자
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,

    -- 배송 정보
    shipping_address_id BIGINT NULL REFERENCES user_addresses(id) ON DELETE SET NULL,
    recipient_name VARCHAR(100) NOT NULL,
    recipient_phone VARCHAR(20) NOT NULL,
    shipping_address TEXT NOT NULL,
    shipping_memo TEXT NULL,

    -- 결제 정보
    payment_method_id BIGINT NULL REFERENCES user_payment_methods(id) ON DELETE SET NULL,
    payment_method_type VARCHAR(20) NOT NULL,

    -- 금액
    subtotal INTEGER NOT NULL DEFAULT 0,      -- 상품 금액
    shipping_fee INTEGER DEFAULT 0,           -- 배송비
    discount_amount INTEGER DEFAULT 0,        -- 할인 금액
    total_amount INTEGER NOT NULL,            -- 최종 결제 금액

    -- 상태
    order_status VARCHAR(20) DEFAULT 'pending',
    -- 'pending', 'paid', 'processing', 'shipped', 'delivered', 'cancelled', 'refunded'

    payment_status VARCHAR(20) DEFAULT 'pending',
    -- 'pending', 'paid', 'failed', 'refunded', 'partially_refunded'

    -- 결제 정보
    payment_gateway VARCHAR(50) NULL,  -- 'iamport', 'tosspayments' 등
    payment_transaction_id VARCHAR(255) NULL,
    paid_at TIMESTAMP NULL,

    -- 배송 정보
    shipping_status VARCHAR(20) DEFAULT 'pending',
    -- 'pending', 'preparing', 'shipped', 'in_transit', 'delivered', 'failed'

    tracking_number VARCHAR(100) NULL,
    shipping_carrier VARCHAR(50) NULL,
    shipped_at TIMESTAMP NULL,
    delivered_at TIMESTAMP NULL,

    -- 취소/환불
    cancelled_at TIMESTAMP NULL,
    cancel_reason TEXT NULL,
    refunded_at TIMESTAMP NULL,
    refund_amount INTEGER DEFAULT 0,

    -- 메타데이터
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 인덱스
    INDEX idx_order_user_id (user_id),
    INDEX idx_order_number (order_number),
    INDEX idx_order_status (order_status),
    INDEX idx_order_payment_status (payment_status),
    INDEX idx_order_created_at (created_at DESC)
);
```

#### 2.4.2 OrderItem (주문 상품)
```sql
CREATE TABLE order_items (
    id BIGSERIAL PRIMARY KEY,
    order_id BIGINT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id BIGINT NOT NULL REFERENCES products(id) ON DELETE RESTRICT,

    -- 판매자 정보 (정산용)
    seller_id BIGINT NULL REFERENCES sellers(id) ON DELETE SET NULL,

    -- 상품 정보 (스냅샷 - 주문 시점 정보 보존)
    product_name VARCHAR(500) NOT NULL,
    product_image_url TEXT NULL,
    product_option TEXT NULL,  -- JSON 형태로 저장

    -- 수량 및 가격
    quantity INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),
    unit_price INTEGER NOT NULL,
    discount_amount INTEGER DEFAULT 0,
    total_price INTEGER NOT NULL,

    -- 상태
    status VARCHAR(20) DEFAULT 'pending',
    -- 'pending', 'confirmed', 'preparing', 'shipped', 'delivered', 'cancelled', 'refunded'

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_order_item_order_id (order_id),
    INDEX idx_order_item_product_id (product_id),
    INDEX idx_order_item_seller_id (seller_id)
);
```

---

### 2.5 장바구니 및 찜하기 (Cart & Wishlist)

#### 2.5.1 CartItem (장바구니)
```sql
CREATE TABLE cart_items (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    product_id BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,

    quantity INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),
    selected_options JSONB NULL,  -- 선택한 옵션 (JSON)

    is_selected BOOLEAN DEFAULT TRUE,  -- 결제 시 선택 여부

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(user_id, product_id),  -- 동일 상품 중복 방지
    INDEX idx_cart_user_id (user_id),
    INDEX idx_cart_product_id (product_id)
);
```

#### 2.5.2 Wishlist (찜하기)
```sql
CREATE TABLE wishlist_items (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    product_id BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(user_id, product_id),
    INDEX idx_wishlist_user_id (user_id),
    INDEX idx_wishlist_product_id (product_id)
);
```

---

### 2.6 리뷰 시스템 (Review System)

#### 2.6.1 Review (리뷰)
```sql
CREATE TABLE reviews (
    id BIGSERIAL PRIMARY KEY,

    -- 관계
    product_id BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    order_item_id BIGINT NULL REFERENCES order_items(id) ON DELETE SET NULL,
    -- 구매 인증 (주문 아이템과 연결)

    -- 평점
    rating SMALLINT NOT NULL CHECK (rating BETWEEN 1 AND 5),

    -- 리뷰 내용
    title VARCHAR(200) NULL,
    content TEXT NOT NULL,

    -- 리뷰 유형
    is_photo_review BOOLEAN DEFAULT FALSE,

    -- 판매자 응답
    seller_reply TEXT NULL,
    seller_replied_at TIMESTAMP NULL,

    -- 통계
    helpful_count INTEGER DEFAULT 0,  -- 도움됨 수

    -- 상태
    status VARCHAR(20) DEFAULT 'active',
    -- 'active', 'hidden', 'reported', 'deleted'

    -- 메타데이터
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 제약조건: 한 주문에 대해 한 번만 리뷰 작성
    UNIQUE(order_item_id),

    INDEX idx_review_product_id (product_id),
    INDEX idx_review_user_id (user_id),
    INDEX idx_review_rating (rating),
    INDEX idx_review_created_at (created_at DESC),
    INDEX idx_review_photo (is_photo_review, status)
);
```

#### 2.6.2 ReviewImage (리뷰 이미지)
```sql
CREATE TABLE review_images (
    id BIGSERIAL PRIMARY KEY,
    review_id BIGINT NOT NULL REFERENCES reviews(id) ON DELETE CASCADE,

    image_url TEXT NOT NULL,
    display_order INTEGER DEFAULT 0,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_review_image_review_id (review_id)
);
```

#### 2.6.3 ReviewHelpful (리뷰 도움됨)
```sql
CREATE TABLE review_helpful (
    id BIGSERIAL PRIMARY KEY,
    review_id BIGINT NOT NULL REFERENCES reviews(id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(review_id, user_id),
    INDEX idx_review_helpful_review_id (review_id),
    INDEX idx_review_helpful_user_id (user_id)
);
```

---

### 2.7 사용자 행동 로그 (User Activity Logs)

#### 2.7.1 ProductView (상품 조회 로그)
```sql
CREATE TABLE product_views (
    id BIGSERIAL PRIMARY KEY,

    product_id BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    user_id BIGINT NULL REFERENCES users(id) ON DELETE SET NULL,
    -- NULL 허용 (비로그인 사용자)

    -- 세션 정보
    session_id VARCHAR(255) NOT NULL,

    -- 유입 경로
    referrer TEXT NULL,
    source VARCHAR(50) NULL,  -- 'search', 'recommendation', 'category', 'direct'

    -- 디바이스 정보
    user_agent TEXT NULL,
    ip_address INET NULL,
    device_type VARCHAR(20) NULL,  -- 'mobile', 'tablet', 'desktop'

    -- 체류 시간 (초)
    duration_seconds INTEGER NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_product_view_product_id (product_id),
    INDEX idx_product_view_user_id (user_id),
    INDEX idx_product_view_session_id (session_id),
    INDEX idx_product_view_created_at (created_at DESC),

    -- 파티셔닝: 월별로 파티션 (성능 최적화)
    -- PARTITION BY RANGE (created_at)
);
```

#### 2.7.2 ProductClick (상품 클릭 로그)
```sql
CREATE TABLE product_clicks (
    id BIGSERIAL PRIMARY KEY,

    product_id BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    user_id BIGINT NULL REFERENCES users(id) ON DELETE SET NULL,
    session_id VARCHAR(255) NOT NULL,

    -- 클릭 위치
    click_position INTEGER NULL,  -- 검색 결과 순서
    list_type VARCHAR(50) NULL,   -- 'search_result', 'recommendation', 'category_list'

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_product_click_product_id (product_id),
    INDEX idx_product_click_user_id (user_id),
    INDEX idx_product_click_created_at (created_at DESC)
);
```

#### 2.7.3 SearchLog (검색 로그)
```sql
CREATE TABLE search_logs (
    id BIGSERIAL PRIMARY KEY,

    user_id BIGINT NULL REFERENCES users(id) ON DELETE SET NULL,
    session_id VARCHAR(255) NOT NULL,

    -- 검색어
    query TEXT NOT NULL,

    -- 검색 결과
    result_count INTEGER DEFAULT 0,

    -- 필터
    filters JSONB NULL,  -- 적용된 필터 (JSON)

    -- 클릭 여부
    has_click BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_search_log_user_id (user_id),
    INDEX idx_search_log_query (query),
    INDEX idx_search_log_created_at (created_at DESC),

    -- 전체 텍스트 검색 인덱스 (PostgreSQL)
    INDEX idx_search_log_query_gin (query gin_trgm_ops)
);
```

#### 2.7.4 RecentlyViewedProduct (최근 본 상품)
```sql
CREATE TABLE recently_viewed_products (
    id BIGSERIAL PRIMARY KEY,

    user_id BIGINT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id VARCHAR(255) NOT NULL,  -- 비로그인 사용자용
    product_id BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,

    viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 동일 상품 중복 방지 (최신 기록만 유지)
    UNIQUE(user_id, product_id),
    UNIQUE(session_id, product_id),

    INDEX idx_recently_viewed_user_id (user_id, viewed_at DESC),
    INDEX idx_recently_viewed_session_id (session_id, viewed_at DESC),
    INDEX idx_recently_viewed_product_id (product_id)
);
```

---

### 2.8 추천 시스템 데이터 (Recommendation System)

#### 2.8.1 UserInteraction (사용자 상호작용)
```sql
CREATE TABLE user_interactions (
    id BIGSERIAL PRIMARY KEY,

    user_id BIGINT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id VARCHAR(255) NOT NULL,
    product_id BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,

    -- 상호작용 유형
    interaction_type VARCHAR(20) NOT NULL,
    -- 'view', 'click', 'cart_add', 'wishlist_add', 'purchase', 'review'

    -- 가중치 (추천 알고리즘용)
    weight DECIMAL(5, 2) DEFAULT 1.00,
    -- view: 1.0, click: 2.0, cart_add: 3.0, wishlist_add: 3.0, purchase: 5.0, review: 4.0

    -- 컨텍스트 정보
    context JSONB NULL,  -- 추가 컨텍스트 (시간대, 디바이스 등)

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_user_interaction_user_id (user_id, created_at DESC),
    INDEX idx_user_interaction_product_id (product_id),
    INDEX idx_user_interaction_type (interaction_type),
    INDEX idx_user_interaction_created_at (created_at DESC)
);
```

#### 2.8.2 ProductSimilarity (상품 유사도)
```sql
CREATE TABLE product_similarity (
    id BIGSERIAL PRIMARY KEY,

    product_id_1 BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    product_id_2 BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,

    -- 유사도 점수
    similarity_score DECIMAL(5, 4) NOT NULL CHECK (similarity_score BETWEEN 0 AND 1),

    -- 유사도 계산 방법
    method VARCHAR(50) NOT NULL,
    -- 'collaborative', 'content_based', 'hybrid'

    -- 메타데이터
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(product_id_1, product_id_2),
    INDEX idx_product_similarity_product_1 (product_id_1, similarity_score DESC),
    INDEX idx_product_similarity_product_2 (product_id_2, similarity_score DESC)
);
```

#### 2.8.3 RecommendationResult (추천 결과 캐시)
```sql
CREATE TABLE recommendation_results (
    id BIGSERIAL PRIMARY KEY,

    user_id BIGINT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- 추천 유형
    recommendation_type VARCHAR(50) NOT NULL,
    -- 'personalized', 'popular', 'similar', 'cold_start'

    -- 추천 상품 목록 (JSON)
    product_ids JSONB NOT NULL,
    scores JSONB NOT NULL,  -- 각 상품의 추천 점수

    -- 메타데이터
    algorithm VARCHAR(50) NOT NULL,  -- 'SASRec', 'BERT4Rec', 'Airscout' 등
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,

    INDEX idx_recommendation_user_id (user_id, recommendation_type),
    INDEX idx_recommendation_expires_at (expires_at)
);
```

---

### 2.9 쿠폰 및 프로모션 (향후 확장)

#### 2.9.1 Coupon (쿠폰)
```sql
CREATE TABLE coupons (
    id BIGSERIAL PRIMARY KEY,

    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT NULL,

    -- 할인 정보
    discount_type VARCHAR(20) NOT NULL,  -- 'percentage', 'fixed_amount'
    discount_value INTEGER NOT NULL,
    max_discount_amount INTEGER NULL,

    -- 최소 주문 금액
    min_order_amount INTEGER DEFAULT 0,

    -- 사용 제한
    usage_limit INTEGER NULL,  -- 전체 사용 제한
    usage_limit_per_user INTEGER DEFAULT 1,

    -- 적용 대상
    applicable_products JSONB NULL,  -- 특정 상품에만 적용
    applicable_categories JSONB NULL,  -- 특정 카테고리에만 적용

    -- 유효 기간
    valid_from TIMESTAMP NOT NULL,
    valid_until TIMESTAMP NOT NULL,

    -- 상태
    is_active BOOLEAN DEFAULT TRUE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_coupon_code (code),
    INDEX idx_coupon_valid_period (valid_from, valid_until),
    INDEX idx_coupon_active (is_active)
);
```

#### 2.9.2 UserCoupon (사용자 쿠폰)
```sql
CREATE TABLE user_coupons (
    id BIGSERIAL PRIMARY KEY,

    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    coupon_id BIGINT NOT NULL REFERENCES coupons(id) ON DELETE CASCADE,

    -- 사용 정보
    is_used BOOLEAN DEFAULT FALSE,
    used_at TIMESTAMP NULL,
    order_id BIGINT NULL REFERENCES orders(id) ON DELETE SET NULL,

    -- 유효 기간 (개인별)
    valid_until TIMESTAMP NOT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_user_coupon_user_id (user_id),
    INDEX idx_user_coupon_coupon_id (coupon_id),
    INDEX idx_user_coupon_valid (user_id, is_used, valid_until)
);
```

---

### 2.10 알림 시스템 (Notification)

#### 2.10.1 Notification (알림)
```sql
CREATE TABLE notifications (
    id BIGSERIAL PRIMARY KEY,

    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- 알림 유형
    type VARCHAR(50) NOT NULL,
    -- 'order_status', 'shipping', 'review', 'promotion', 'announcement'

    -- 알림 내용
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,

    -- 관련 엔티티
    related_entity_type VARCHAR(50) NULL,  -- 'order', 'product', 'review'
    related_entity_id BIGINT NULL,

    -- 링크
    action_url TEXT NULL,

    -- 상태
    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMP NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_notification_user_id (user_id, is_read, created_at DESC),
    INDEX idx_notification_type (type)
);
```

---

### 2.11 관리자 기능 (Admin)

#### 2.11.1 AdminLog (관리자 활동 로그)
```sql
CREATE TABLE admin_logs (
    id BIGSERIAL PRIMARY KEY,

    admin_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- 액션 정보
    action VARCHAR(50) NOT NULL,
    -- 'create', 'update', 'delete', 'approve', 'reject'

    target_type VARCHAR(50) NOT NULL,  -- 'product', 'seller', 'user', 'order'
    target_id BIGINT NOT NULL,

    -- 변경 내용
    changes JSONB NULL,  -- 변경 전/후 데이터

    -- 메타데이터
    ip_address INET NULL,
    user_agent TEXT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_admin_log_admin_id (admin_id, created_at DESC),
    INDEX idx_admin_log_target (target_type, target_id),
    INDEX idx_admin_log_created_at (created_at DESC)
);
```

---

## 3. 인덱스 전략

### 3.1 주요 쿼리별 인덱스

**상품 목록 조회 (메인 + 판매자 통합):**
```sql
-- 추천 알고리즘 기반 정렬
CREATE INDEX idx_product_recommend ON products (product_type, status, quality_score DESC, ctr DESC);

-- 카테고리별 조회
CREATE INDEX idx_product_category_recommend ON products (category_id, status, quality_score DESC);

-- 판매자별 조회
CREATE INDEX idx_product_seller_active ON products (seller_id, status, created_at DESC);

-- 베스트 상품
CREATE INDEX idx_product_best_active ON products (is_best, status, purchase_count DESC);
```

**검색 최적화 (PostgreSQL):**
```sql
-- 전체 텍스트 검색
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE INDEX idx_product_name_gin ON products USING gin (name gin_trgm_ops);
CREATE INDEX idx_product_description_gin ON products USING gin (description gin_trgm_ops);

-- 복합 텍스트 검색
CREATE INDEX idx_product_search ON products USING gin (
    to_tsvector('korean', coalesce(name, '') || ' ' || coalesce(description, ''))
);
```

**사용자 행동 로그 조회:**
```sql
-- 사용자별 최근 활동
CREATE INDEX idx_user_interaction_user_recent ON user_interactions (user_id, created_at DESC);

-- 상품별 인기도 분석
CREATE INDEX idx_product_view_product_date ON product_views (product_id, created_at DESC);
```

---

## 4. 파티셔닝 전략

### 4.1 시계열 데이터 파티셔닝

**ProductView (월별 파티션):**
```sql
-- 파티션 테이블 생성 (PostgreSQL 10+)
CREATE TABLE product_views (
    ...
) PARTITION BY RANGE (created_at);

-- 파티션 생성
CREATE TABLE product_views_2025_01 PARTITION OF product_views
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

CREATE TABLE product_views_2025_02 PARTITION OF product_views
    FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');

-- 자동 파티션 생성 (pg_partman 사용 권장)
```

**UserInteraction (분기별 파티션):**
```sql
CREATE TABLE user_interactions (
    ...
) PARTITION BY RANGE (created_at);

CREATE TABLE user_interactions_2025_q1 PARTITION OF user_interactions
    FOR VALUES FROM ('2025-01-01') TO ('2025-04-01');
```

---

## 5. 성능 최적화

### 5.1 비정규화 전략

**통계 데이터 캐싱:**
- `products.view_count`, `products.purchase_count` 등은 실시간 집계가 아닌 비정규화 필드
- 주기적으로 배치 작업으로 업데이트 (Celery Beat)
- 정확성보다 성능 우선

**Django 시그널로 업데이트:**
```python
@receiver(post_save, sender=OrderItem)
def update_product_purchase_count(sender, instance, created, **kwargs):
    if created and instance.status == 'confirmed':
        Product.objects.filter(id=instance.product_id).update(
            purchase_count=F('purchase_count') + instance.quantity
        )
```

### 5.2 캐싱 전략

**Redis 캐싱 대상:**
1. 상품 목록 (카테고리별, TTL: 5분)
2. 상품 상세 (TTL: 10분)
3. 카테고리 목록 (TTL: 1시간)
4. 베스트 상품 (TTL: 30분)
5. 추천 결과 (TTL: 1시간)

**Django 캐시 예시:**
```python
from django.core.cache import cache

def get_product_list(category_id=None):
    cache_key = f'products:category:{category_id}'
    products = cache.get(cache_key)

    if not products:
        products = Product.objects.filter(category_id=category_id, status='active')
        cache.set(cache_key, products, 300)  # 5분

    return products
```

---

## 6. 데이터 마이그레이션 계획

### 6.1 초기 데이터 임포트

**CSV → PostgreSQL:**
```python
# management/commands/import_all_csvs.py
import os
import glob
from django.core.management.base import BaseCommand
from products.models import Product, Category

class Command(BaseCommand):
    def handle(self, *args, **options):
        csv_files = glob.glob('data/*.csv')

        for csv_file in csv_files:
            self.import_csv(csv_file)

    def import_csv(self, file_path):
        # 중복 체크: product_url 기준
        # 카테고리 자동 생성
        # 이미지 URL 유효성 검증
        # quality_score 초기 계산
        pass
```

### 6.2 SQLite → PostgreSQL 전환

**데이터 백업:**
```bash
# 1. SQLite 덤프
python manage.py dumpdata --natural-foreign --natural-primary -e contenttypes -e auth.Permission > backup.json

# 2. PostgreSQL 설정 변경 (settings.py)

# 3. 마이그레이션
python manage.py migrate

# 4. 데이터 복원
python manage.py loaddata backup.json
```

---

## 7. 보안 고려사항

### 7.1 민감 정보 암호화

**암호화 필요 필드:**
- `user_payment_methods.payment_gateway_token`
- `sellers.bank_account_number`
- `user_addresses` (선택적)

**Django 암호화 라이브러리:**
```python
from django_cryptography.fields import encrypt

class UserPaymentMethod(models.Model):
    payment_gateway_token = encrypt(models.TextField(null=True))
```

### 7.2 SQL Injection 방지

- Django ORM 사용 (Raw SQL 최소화)
- 사용자 입력 검증
- Prepared Statement 사용

### 7.3 접근 제어

- Django Permission 시스템 활용
- Row-Level Security (PostgreSQL RLS)

---

## 8. 모니터링 및 유지보수

### 8.1 느린 쿼리 모니터링

**PostgreSQL 설정:**
```sql
-- postgresql.conf
log_min_duration_statement = 1000  -- 1초 이상 쿼리 로그
log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d '
```

**Django Debug Toolbar:**
```python
# settings.py
if DEBUG:
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
```

### 8.2 인덱스 사용률 확인

```sql
-- 사용되지 않는 인덱스 확인
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE idx_scan = 0
ORDER BY pg_relation_size(indexrelid) DESC;
```

---

## 9. 확장 로드맵

### 9.1 Phase 1 (현재 ~ 1개월)
- [x] User, Category, Product, Order 기본 모델
- [ ] CSV 데이터 임포트
- [ ] PostgreSQL 전환
- [ ] 기본 인덱스 생성

### 9.2 Phase 2 (1~3개월)
- [ ] Seller, Review, Cart, Wishlist 모델
- [ ] 사용자 행동 로그 수집
- [ ] Redis 캐싱
- [ ] 추천 시스템 v1 (품질 점수 기반)

### 9.3 Phase 3 (3~6개월)
- [ ] 추천 시스템 v2 (SASRec, BERT4Rec)
- [ ] Coupon, Notification 모델
- [ ] 파티셔닝 적용
- [ ] 성능 최적화

### 9.4 Phase 4 (6개월~)
- [ ] 실시간 추천
- [ ] 머신러닝 모델 서빙
- [ ] A/B 테스팅 시스템
- [ ] 글로벌 확장 (다국어, 다중 통화)

---

## 10. 결론

본 ERD 설계는 다음 요구사항을 모두 충족합니다:

✅ **완전 정규화**: 데이터 중복 최소화, 무결성 보장
✅ **확장성**: 신규 기능 추가 용이 (nullable 필드, JSONB 활용)
✅ **추천 알고리즘 대비**: 사용자 행동 로그, 상품 유사도, 품질 점수
✅ **대용량 데이터 처리**: 인덱스 최적화, 파티셔닝, 캐싱
✅ **판매자 시스템**: 브랜드, 상품 등록, 대시보드 지원
✅ **관리자 시스템**: 메인 상품 관리, 판매자/유저 관리
✅ **SEO 최적화**: meta 필드, slug, 전체 텍스트 검색
✅ **성능 최적화**: 비정규화 통계, Redis 캐싱, 복합 인덱스

다음 단계로 이 ERD를 기반으로 Django 모델 코드를 작성하고, API 엔드포인트를 구현합니다.
