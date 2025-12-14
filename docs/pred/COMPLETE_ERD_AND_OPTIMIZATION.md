# SelF 추천 시스템 완전 ERD 및 최적화 전략

> **문서 버전**: v1.1.0
> **최종 수정일**: 2025년 12월 10일
> **변경 사항**: 사전 집계 테이블 추가, 파티셔닝 전략 현실화, 쿼리 성능 예상치 보정, 트랜잭션 경계 명시

---

## 1. 전체 시스템 ERD

### 1.1 테이블 그룹 개요

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    SelF 추천 시스템 전체 ERD                                 │
│                                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────────────────────┐   │
│  │                           Group A: 기존 SelF 백엔드 (30개 테이블)                    │   │
│  │                                    [수정 없음 - FK 참조만]                           │   │
│  │                                                                                     │   │
│  │   Users & Auth (8)          Products (8)           Orders (4)       Sellers (5)    │   │
│  │   ┌─────────────┐          ┌─────────────┐        ┌──────────┐     ┌──────────┐   │   │
│  │   │users        │          │products     │        │orders    │     │sellers   │   │   │
│  │   │user_profiles│          │categories   │        │order_items│    │seller_   │   │   │
│  │   │user_addresses│         │product_     │        │shipments │     │businesses│   │   │
│  │   │pending_     │          │details      │        │payments  │     │seller_   │   │   │
│  │   │registrations│          │product_     │        └──────────┘     │settlements│  │   │
│  │   │auth_email_  │          │inventories  │                         │seller_   │   │   │
│  │   │credentials  │          │product_     │                         │schedules │   │   │
│  │   │auth_google_ │          │images       │                         │seller_kpi│   │   │
│  │   │accounts     │          │product_     │                         └──────────┘   │   │
│  │   │auth_kakao_  │          │price_       │◀─────── PriceAnomaly 모델 핵심 테이블   │   │
│  │   │accounts     │          │histories    │                                        │   │
│  │   └─────────────┘          │product_stats│                                        │   │
│  │                            │user_product_│                                        │   │
│  │                            │stats        │                                        │   │
│  │                            └─────────────┘                                        │   │
│  │                                                                                     │   │
│  │   Interactions (3)         Reviews (2)                                             │   │
│  │   ┌─────────────┐          ┌─────────────┐                                        │   │
│  │   │carts        │          │reviews      │                                        │   │
│  │   │wishlists    │          │review_images│                                        │   │
│  │   │seller_follows│         └─────────────┘                                        │   │
│  │   └─────────────┘                                                                  │   │
│  └─────────────────────────────────────────────────────────────────────────────────────┘   │
│                                            │                                               │
│                                            │ FK 참조                                       │
│                                            ▼                                               │
│  ┌─────────────────────────────────────────────────────────────────────────────────────┐   │
│  │                       Group B: 추천 시스템 전용 테이블 (17개 신규)                   │   │
│  │                                                                                     │   │
│  │   Instacart (9)                    Recipe (4)                  Embedding & Cache(4)│   │
│  │   ┌───────────────────┐           ┌───────────────────┐      ┌────────────────────┐│   │
│  │   │pred_instacart_    │           │pred_recipes       │      │pred_product_       ││   │
│  │   │departments        │           │pred_ingredients   │      │embeddings          ││   │
│  │   │pred_instacart_    │           │pred_recipe_       │      │pred_user_          ││   │
│  │   │aisles             │           │ingredients        │      │embeddings          ││   │
│  │   │pred_instacart_    │           │pred_ingredient_   │      │pred_recommendation_││   │
│  │   │products           │           │products           │      │cache               ││   │
│  │   │pred_instacart_    │           └───────────────────┘      │pred_price_anomaly_ ││   │
│  │   │orders (파티셔닝)  │                                      │cache               ││   │
│  │   │pred_instacart_    │                                      └────────────────────┘│   │
│  │   │order_items        │                                                            │   │
│  │   │pred_product_      │                                                            │   │
│  │   │mapping            │                                                            │   │
│  │   │pred_instacart_    │◀─────── 사전 집계 테이블 (32M 쿼리 최적화)                  │   │
│  │   │time_patterns      │                                                            │   │
│  │   │pred_instacart_    │                                                            │   │
│  │   │category_mapping   │                                                            │   │
│  │   │pred_item_         │◀─────── 사전 계산된 유사도 테이블                          │   │
│  │   │similarity         │                                                            │   │
│  │   └───────────────────┘                                                            │   │
│  └─────────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                             │
│  총 47개 테이블 (기존 30 + 신규 17)                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

### 1.2 상세 ERD (Mermaid)

```mermaid
erDiagram
    %% ==========================================
    %% Group A: 기존 SelF 백엔드 테이블
    %% ==========================================

    %% Users & Auth
    users ||--|| user_profiles : "has profile"
    users ||--o{ user_addresses : "has addresses"
    users ||--o| auth_email_credentials : "has email auth"
    users ||--o{ auth_google_accounts : "has google"
    users ||--o{ auth_kakao_accounts : "has kakao"

    %% Products
    categories ||--o{ categories : "parent-child"
    categories ||--o{ products : "contains"
    sellers ||--o{ products : "sells"
    products ||--|| product_details : "has detail"
    products ||--|| product_inventories : "has inventory"
    products ||--o{ product_images : "has images"
    products ||--o{ product_price_histories : "has price history"
    products ||--|| product_stats : "has stats"

    %% User-Product Interactions
    users ||--o{ user_product_stats : "interacts"
    products ||--o{ user_product_stats : "tracked"
    users ||--o{ carts : "has cart"
    products ||--o{ carts : "in cart"
    users ||--o{ wishlists : "has wishlist"
    products ||--o{ wishlists : "wishlisted"

    %% Orders
    users ||--o{ orders : "places"
    orders ||--o{ order_items : "contains"
    products ||--o{ order_items : "ordered"
    orders ||--o{ shipments : "has shipments"
    orders ||--o{ payments : "has payments"

    %% Reviews
    users ||--o{ reviews : "writes"
    products ||--o{ reviews : "reviewed"
    reviews ||--o{ review_images : "has images"

    %% Sellers
    users ||--o| sellers : "is seller"
    sellers ||--|| seller_businesses : "has business"
    sellers ||--|| seller_settlements : "has settlement"
    sellers ||--o{ seller_schedules : "has schedules"
    users ||--o{ seller_follows : "follows"
    sellers ||--o{ seller_follows : "followed by"

    %% ==========================================
    %% Group B: 추천 시스템 전용 테이블 (신규)
    %% ==========================================

    %% Instacart Domain
    pred_instacart_departments ||--o{ pred_instacart_aisles : "contains"
    pred_instacart_aisles ||--o{ pred_instacart_products : "contains"
    pred_instacart_orders ||--o{ pred_instacart_order_items : "has items"
    pred_instacart_products ||--o{ pred_instacart_order_items : "ordered"

    %% 사전 집계 테이블 (신규)
    pred_instacart_departments ||--o{ pred_instacart_time_patterns : "aggregated"
    categories ||--o{ pred_instacart_time_patterns : "mapped to"
    pred_instacart_departments ||--o{ pred_instacart_category_mapping : "maps"
    categories ||--o{ pred_instacart_category_mapping : "mapped"

    %% SelF ↔ Instacart Mapping
    products ||--o{ pred_product_mapping : "maps to"
    pred_instacart_products ||--o{ pred_product_mapping : "maps from"

    %% 유사도 테이블 (신규)
    products ||--o{ pred_item_similarity : "source item"
    products ||--o{ pred_item_similarity : "similar item"

    %% Recipe Domain
    pred_recipes ||--o{ pred_recipe_ingredients : "has ingredients"
    pred_ingredients ||--o{ pred_recipe_ingredients : "used in"
    pred_ingredients ||--o{ pred_ingredient_products : "maps to"
    products ||--o{ pred_ingredient_products : "matches"

    %% Embeddings
    products ||--o| pred_product_embeddings : "has embedding"
    users ||--o| pred_user_embeddings : "has embedding"

    %% Cache
    users ||--o{ pred_recommendation_cache : "has cache"
    products ||--o| pred_price_anomaly_cache : "has anomaly"
    categories ||--o{ pred_price_anomaly_cache : "categorizes"

    %% ==========================================
    %% 테이블 상세 정의
    %% ==========================================

    users {
        bigint id PK
        varchar(254) email UK
        varchar(150) username UK
        varchar(20) role "guest|user|seller|admin"
        boolean is_active
        timestamp last_login
        timestamp date_joined
        timestamp deleted_at
    }

    products {
        bigint id PK
        bigint seller_id FK
        bigint category_id FK
        varchar(500) name
        varchar(500) slug UK
        int price
        int original_price
        varchar(20) status
        varchar(20) product_type
        varchar(50) unit
        timestamp created_at
    }

    product_price_histories {
        bigint id PK
        bigint product_id FK
        int price
        int original_price
        int previous_price
        int price_change
        decimal price_change_rate
        boolean is_current
        timestamp recorded_at
        varchar(50) source
    }

    user_product_stats {
        bigint id PK
        bigint user_id FK
        bigint product_id FK
        bigint view_count
        bigint cart_event_count
        bigint order_event_count
        timestamp last_interacted_at
    }

    pred_instacart_departments {
        smallint id PK
        varchar(100) name UK
        varchar(255) description
    }

    pred_instacart_aisles {
        smallint id PK
        smallint department_id FK
        varchar(100) name
    }

    pred_instacart_products {
        int id PK
        smallint aisle_id FK
        varchar(300) name
        varchar(300) name_normalized
        int order_count
        decimal reorder_rate
    }

    pred_instacart_orders {
        int id PK
        int user_id
        smallint order_number
        smallint order_dow
        smallint order_hour_of_day
        smallint days_since_prior_order
        varchar(10) eval_set
    }

    pred_instacart_order_items {
        bigint id PK
        int order_id FK
        int product_id FK
        smallint add_to_cart_order
        boolean is_reordered
    }

    pred_instacart_time_patterns {
        int id PK
        varchar(20) time_slot "morning|lunch|dinner|night"
        varchar(20) day_type "weekday|weekend"
        smallint instacart_department_id FK
        bigint self_category_id FK
        bigint popularity_score
        decimal reorder_rate
        timestamp aggregated_at
    }

    pred_instacart_category_mapping {
        int id PK
        smallint instacart_department_id FK
        bigint self_category_id FK
        decimal confidence_score
        boolean is_verified
        timestamp created_at
    }

    pred_product_mapping {
        bigint id PK
        bigint self_product_id FK
        int instacart_product_id FK
        decimal similarity_score
        varchar(50) mapping_method
        boolean is_active
        timestamp created_at
    }

    pred_item_similarity {
        bigint id PK
        bigint source_product_id FK
        bigint similar_product_id FK
        decimal similarity_score
        varchar(30) similarity_type
        timestamp calculated_at
    }

    pred_recipes {
        bigint id PK
        varchar(50) source_site
        varchar(50) source_id
        varchar(200) name
        varchar(200) name_normalized
        text description
        decimal rating
        int like_count
        varchar(50) category_main
        varchar(50) category_sub
        boolean is_active
        timestamp created_at
    }

    pred_ingredients {
        int id PK
        varchar(100) name UK
        varchar(100) name_normalized
        varchar(50) category
        decimal importance_score
        boolean is_processed
    }

    pred_recipe_ingredients {
        bigint id PK
        bigint recipe_id FK
        int ingredient_id FK
        varchar(100) quantity_text
        boolean is_required
        boolean is_main
    }

    pred_ingredient_products {
        bigint id PK
        int ingredient_id FK
        bigint product_id FK
        decimal similarity_score
        varchar(50) mapping_method
        smallint priority
        boolean is_active
    }

    pred_product_embeddings {
        bigint product_id PK_FK
        jsonb bert_vector "768차원 BERT 임베딩"
        varchar(20) bert_version
        timestamp updated_at
    }

    pred_user_embeddings {
        bigint user_id PK_FK
        jsonb preference_vector
        varchar(20) user_type "cold|lukewarm|warm"
        int interaction_count
        timestamp updated_at
    }

    pred_recommendation_cache {
        bigint id PK
        bigint user_id FK
        varchar(30) page_type
        varchar(64) context_hash
        jsonb recommendations
        timestamp created_at
        timestamp expires_at
    }

    pred_price_anomaly_cache {
        bigint id PK
        bigint product_id FK_UK
        bigint category_id FK
        int current_price
        decimal anomaly_score
        varchar(100) detection_methods
        timestamp created_at
        timestamp expires_at
    }
```

---

## 2. 정규화 검증

### 2.1 정규화 수준 분석

| 테이블 | 1NF | 2NF | 3NF | BCNF | 비고 |
|--------|:---:|:---:|:---:|:----:|------|
| **기존 테이블** |
| `users` | ✅ | ✅ | ✅ | ✅ | 완전 정규화 |
| `products` | ✅ | ✅ | ✅ | ✅ | seller, category 분리 |
| `product_price_histories` | ✅ | ✅ | ✅ | ✅ | 이력 테이블 |
| `user_product_stats` | ✅ | ✅ | ✅ | ✅ | 집계 테이블 (의도적 비정규화) |
| **신규 테이블** |
| `pred_instacart_departments` | ✅ | ✅ | ✅ | ✅ | 마스터 |
| `pred_instacart_aisles` | ✅ | ✅ | ✅ | ✅ | department FK 분리 |
| `pred_instacart_products` | ✅ | ✅ | ✅ | ✅ | aisle FK 분리 |
| `pred_instacart_orders` | ✅ | ✅ | ✅ | ✅ | 컨텍스트 분리 (파티셔닝) |
| `pred_instacart_order_items` | ✅ | ✅ | ✅ | ✅ | N:M 브릿지 |
| `pred_instacart_time_patterns` | ✅ | ✅ | ✅ | ✅ | 사전 집계 (의도적 비정규화) |
| `pred_instacart_category_mapping` | ✅ | ✅ | ✅ | ✅ | N:M 브릿지 |
| `pred_product_mapping` | ✅ | ✅ | ✅ | ✅ | N:M 브릿지 |
| `pred_item_similarity` | ✅ | ✅ | ✅ | ✅ | 사전 계산 (의도적 비정규화) |
| `pred_recipes` | ✅ | ✅ | ✅ | ✅ | 마스터 |
| `pred_ingredients` | ✅ | ✅ | ✅ | ✅ | 마스터 |
| `pred_recipe_ingredients` | ✅ | ✅ | ✅ | ✅ | N:M 브릿지 |
| `pred_ingredient_products` | ✅ | ✅ | ✅ | ✅ | N:M 브릿지 |
| `pred_product_embeddings` | ✅ | ✅ | ✅ | ✅ | 1:1 확장 |
| `pred_user_embeddings` | ✅ | ✅ | ✅ | ✅ | 1:1 확장 |
| `pred_recommendation_cache` | ✅ | ✅ | ✅ | ✅ | 캐시 (의도적 비정규화) |
| `pred_price_anomaly_cache` | ✅ | ✅ | ✅ | ✅ | 캐시 (의도적 비정규화) |

### 2.2 의도적 비정규화 (성능 최적화)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          의도적 비정규화 테이블                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. user_product_stats (기존)                                               │
│     - 목적: 사용자별 상품 상호작용 실시간 집계                               │
│     - 비정규화: view_count, cart_event_count 등 집계 컬럼                    │
│     - 이유: JOIN 없이 단일 테이블 조회로 성능 확보                           │
│     - 트레이드오프: 데이터 일관성 vs 조회 성능 (배치 동기화로 해결)          │
│                                                                             │
│  2. product_stats (기존)                                                    │
│     - 목적: 상품별 글로벌 통계 집계                                         │
│     - 비정규화: review_count, average_rating 등                             │
│     - 이유: 상품 목록 조회 시 매번 COUNT/AVG 연산 방지                       │
│                                                                             │
│  3. pred_instacart_time_patterns (신규) ⭐ 핵심 최적화                       │
│     - 목적: 32M 주문 데이터 사전 집계                                       │
│     - 비정규화: time_slot + day_type 조합별 카테고리 인기도                  │
│     - 이유: 32M 레코드 실시간 쿼리 → 168행 사전 집계 테이블 조회             │
│     - 갱신 주기: 주 1회 배치 (Instacart 데이터 정적)                         │
│                                                                             │
│  4. pred_item_similarity (신규)                                             │
│     - 목적: 상품 간 유사도 사전 계산                                        │
│     - 비정규화: 유사도 점수 미리 계산하여 저장                               │
│     - 이유: 실시간 임베딩 유사도 계산 → 인덱스 조회로 전환                   │
│     - 갱신 주기: 일 1회 배치 (신규 상품 추가 시)                             │
│                                                                             │
│  5. pred_recommendation_cache (신규)                                        │
│     - 목적: 추천 결과 캐시                                                  │
│     - 비정규화: recommendations JSONB에 상품 정보 포함                      │
│     - 이유: 추천 API 응답 속도 최적화 (Redis 백업용)                         │
│                                                                             │
│  6. pred_price_anomaly_cache (신규)                                         │
│     - 목적: 가격 이상치 분석 결과 캐시                                       │
│     - 비정규화: 분석 결과 (zscore, iqr 등) 미리 계산                         │
│     - 이유: 복잡한 통계 연산 결과 재사용                                     │
│                                                                             │
│  7. pred_instacart_products.order_count, reorder_rate (신규)                │
│     - 목적: Instacart 상품 인기도                                           │
│     - 비정규화: 주문 집계 값을 상품 테이블에 포함                            │
│     - 이유: 인기도 기반 정렬 시 JOIN 제거                                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. 파티셔닝 전략

### 3.1 Instacart 주문 테이블 파티셔닝 (필수)

```sql
-- ═══════════════════════════════════════════════════════════════════════════
-- pred_instacart_orders: eval_set 기준 LIST 파티셔닝
-- 목적: 32M 데이터를 논리적으로 분리하여 쿼리 성능 향상
-- ═══════════════════════════════════════════════════════════════════════════

CREATE TABLE pred_instacart_orders (
    id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    order_number SMALLINT NOT NULL,
    order_dow SMALLINT NOT NULL CHECK (order_dow BETWEEN 0 AND 6),
    order_hour_of_day SMALLINT NOT NULL CHECK (order_hour_of_day BETWEEN 0 AND 23),
    days_since_prior_order SMALLINT,
    eval_set VARCHAR(10) NOT NULL CHECK (eval_set IN ('prior', 'train', 'test')),
    PRIMARY KEY (id, eval_set)
) PARTITION BY LIST (eval_set);

-- 파티션 생성
CREATE TABLE pred_instacart_orders_prior
    PARTITION OF pred_instacart_orders FOR VALUES IN ('prior');
-- 예상 레코드: 3,214,874건

CREATE TABLE pred_instacart_orders_train
    PARTITION OF pred_instacart_orders FOR VALUES IN ('train');
-- 예상 레코드: 131,209건

CREATE TABLE pred_instacart_orders_test
    PARTITION OF pred_instacart_orders FOR VALUES IN ('test');
-- 예상 레코드: 75,000건

-- 각 파티션별 인덱스 자동 생성
-- PostgreSQL은 파티션 테이블에 인덱스 생성 시 각 파티션에 자동 적용
CREATE INDEX ix_inst_orders_time_context
ON pred_instacart_orders(eval_set, order_dow, order_hour_of_day);

CREATE INDEX ix_inst_orders_user_seq
ON pred_instacart_orders(user_id, order_number);
```

### 3.2 가격 이력 테이블 파티셔닝 (향후)

```sql
-- ═══════════════════════════════════════════════════════════════════════════
-- product_price_histories: 월별 RANGE 파티셔닝 (데이터 증가 시 적용)
-- 현재 예상: 100,000건, 월 10,000건 증가
-- 파티셔닝 권장 시점: 1,000,000건 초과 시
-- ═══════════════════════════════════════════════════════════════════════════

-- 향후 파티셔닝 전환 DDL (참고용)
CREATE TABLE product_price_histories_partitioned (
    id BIGSERIAL,
    product_id BIGINT NOT NULL,
    price INTEGER NOT NULL,
    original_price INTEGER,
    previous_price INTEGER,
    price_change INTEGER,
    price_change_rate DECIMAL(5,2),
    is_current BOOLEAN NOT NULL DEFAULT FALSE,
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    source VARCHAR(50),
    PRIMARY KEY (id, recorded_at)
) PARTITION BY RANGE (recorded_at);

-- 월별 파티션 생성
CREATE TABLE product_price_histories_2025_12
    PARTITION OF product_price_histories_partitioned
    FOR VALUES FROM ('2025-12-01') TO ('2026-01-01');

CREATE TABLE product_price_histories_2026_01
    PARTITION OF product_price_histories_partitioned
    FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');
```

---

## 4. 인덱스 최적화 전략

### 4.1 인덱스 설계 원칙

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           인덱스 설계 5원칙                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  원칙 1: 선택도 우선                                                        │
│  ─────────────────                                                          │
│  • 카디널리티가 높은 컬럼에 우선 인덱스                                      │
│  • 예: user_id (높음) > status (낮음)                                       │
│  • 낮은 카디널리티 컬럼은 복합 인덱스 뒤쪽에 배치                            │
│                                                                             │
│  원칙 2: 복합 인덱스 컬럼 순서                                               │
│  ─────────────────────────                                                  │
│  • 등호(=) 조건 컬럼을 앞에                                                  │
│  • 범위(>, <, BETWEEN) 조건 컬럼을 뒤에                                      │
│  • ORDER BY 컬럼은 가장 뒤에                                                │
│  • 예: (user_id, status, created_at DESC)                                   │
│                                                                             │
│  원칙 3: 커버링 인덱스                                                      │
│  ──────────────────                                                         │
│  • SELECT 컬럼까지 인덱스에 포함하여 테이블 액세스 제거                      │
│  • 자주 사용되는 조회 패턴에만 적용                                          │
│  • 예: CREATE INDEX ... INCLUDE (name, price)                               │
│                                                                             │
│  원칙 4: 부분 인덱스 (Partial Index)                                        │
│  ──────────────────────────────────                                         │
│  • 조건부 인덱스로 인덱스 크기 최소화                                        │
│  • 예: WHERE is_active = TRUE, WHERE expires_at > NOW()                     │
│                                                                             │
│  원칙 5: 인덱스 유지보수 비용 고려                                           │
│  ──────────────────────────────                                             │
│  • INSERT/UPDATE 시 인덱스 갱신 오버헤드                                    │
│  • 로그/이력 테이블은 최소 인덱스                                           │
│  • 읽기 위주 테이블에 인덱스 집중                                           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 모델별 핵심 쿼리 및 인덱스

#### 🥶 InstacartColdStart 모델 (사전 집계 테이블 활용)

```sql
-- ═══════════════════════════════════════════════════════════════════════════
-- 쿼리 1: 시간대별 인기 카테고리 조회 (사전 집계 테이블 사용)
-- 성능: < 10ms (168행 테이블 조회)
-- ═══════════════════════════════════════════════════════════════════════════

-- 쿼리 패턴 (v3.1.0 최적화)
SELECT itp.self_category_id, itp.popularity_score, itp.reorder_rate
FROM pred_instacart_time_patterns itp
WHERE itp.time_slot = $1      -- 'morning', 'lunch', 'dinner', 'night'
  AND itp.day_type = $2       -- 'weekday', 'weekend'
ORDER BY itp.popularity_score DESC
LIMIT 10;

-- 최적화 인덱스
CREATE UNIQUE INDEX ix_inst_time_patterns_lookup
ON pred_instacart_time_patterns(time_slot, day_type, instacart_department_id);

-- ═══════════════════════════════════════════════════════════════════════════
-- 쿼리 2: 카테고리별 SelF 상품 조회
-- 성능: < 50ms
-- ═══════════════════════════════════════════════════════════════════════════

-- 쿼리 패턴
SELECT p.id, p.name, p.price, ps.view_count
FROM products p
JOIN product_stats ps ON p.id = ps.product_id
WHERE p.category_id = $1
  AND p.status = 'active'
ORDER BY ps.view_count DESC, ps.average_rating DESC
LIMIT 20;

-- 기존 인덱스 활용 (products 테이블)
-- CREATE INDEX ix_products_category_status ON products(category_id, status);

-- ═══════════════════════════════════════════════════════════════════════════
-- 쿼리 3: SelF 상품 매핑 조회 (Fallback)
-- ═══════════════════════════════════════════════════════════════════════════

-- 쿼리 패턴
SELECT pm.self_product_id, p.name, pm.similarity_score
FROM pred_product_mapping pm
JOIN products p ON pm.self_product_id = p.id
WHERE pm.instacart_product_id IN ($1, $2, ...)
  AND pm.is_active = TRUE
  AND p.status = 'active'
ORDER BY pm.similarity_score DESC;

-- 최적화 인덱스
CREATE INDEX ix_product_mapping_inst_active
ON pred_product_mapping(instacart_product_id, similarity_score DESC)
WHERE is_active = TRUE;

-- 커버링 인덱스 (추가 성능 향상)
CREATE INDEX ix_product_mapping_covering
ON pred_product_mapping(instacart_product_id, similarity_score DESC)
INCLUDE (self_product_id)
WHERE is_active = TRUE;
```

#### 🔥 SelfPersonalized 모델

```sql
-- ═══════════════════════════════════════════════════════════════════════════
-- 쿼리 1: 사용자 최근 조회 상품
-- 성능: < 10ms
-- ═══════════════════════════════════════════════════════════════════════════

-- 쿼리 패턴
SELECT ups.product_id, ups.view_count, ups.last_interacted_at
FROM user_product_stats ups
WHERE ups.user_id = $1
  AND ups.view_count > 0
ORDER BY ups.last_interacted_at DESC
LIMIT 10;

-- 기존 인덱스 활용
-- CREATE INDEX ix_ups_user_recent ON user_product_stats(user_id, last_interacted_at DESC);

-- ═══════════════════════════════════════════════════════════════════════════
-- 쿼리 2: 사전 계산된 유사 상품 조회
-- 성능: < 20ms
-- ═══════════════════════════════════════════════════════════════════════════

-- 쿼리 패턴
SELECT pis.similar_product_id, pis.similarity_score
FROM pred_item_similarity pis
WHERE pis.source_product_id = $1
  AND pis.similarity_type = 'purchase'
ORDER BY pis.similarity_score DESC
LIMIT 20;

-- 최적화 인덱스
CREATE INDEX ix_item_sim_source_type
ON pred_item_similarity(source_product_id, similarity_type, similarity_score DESC);

-- ═══════════════════════════════════════════════════════════════════════════
-- 쿼리 3: 유사 사용자 상품 조회 (CF)
-- 성능: < 100ms
-- ═══════════════════════════════════════════════════════════════════════════

-- 쿼리 패턴 (사용자 임베딩 기반 유사 사용자 찾기)
SELECT DISTINCT ups.product_id, SUM(ups.order_event_count) AS score
FROM pred_user_embeddings pue1
JOIN pred_user_embeddings pue2
    ON pue2.user_type = 'warm'
    AND pue1.user_id != pue2.user_id
JOIN user_product_stats ups ON pue2.user_id = ups.user_id
WHERE pue1.user_id = $1
  AND ups.order_event_count > 0
GROUP BY ups.product_id
ORDER BY score DESC
LIMIT 50;

-- 최적화 인덱스
CREATE INDEX ix_user_emb_warm
ON pred_user_embeddings(user_type)
WHERE user_type = 'warm';

CREATE INDEX ix_ups_user_ordered
ON user_product_stats(user_id, order_event_count DESC)
WHERE order_event_count > 0;
```

#### 💰 PriceAnomaly 모델

```sql
-- ═══════════════════════════════════════════════════════════════════════════
-- 쿼리 1: 상품별 가격 이력 조회 (통계 분석용)
-- 성능: < 50ms
-- ═══════════════════════════════════════════════════════════════════════════

-- 쿼리 패턴
SELECT pph.price, pph.recorded_at
FROM product_price_histories pph
WHERE pph.product_id = $1
  AND pph.recorded_at >= NOW() - INTERVAL '30 days'
ORDER BY pph.recorded_at ASC;

-- 기존 인덱스 활용
-- CREATE INDEX ix_price_hist_analysis ON product_price_histories(product_id, recorded_at, price);

-- ═══════════════════════════════════════════════════════════════════════════
-- 쿼리 2: 현재 가격이 급락한 상품 조회
-- 성능: < 100ms
-- ═══════════════════════════════════════════════════════════════════════════

-- 쿼리 패턴
SELECT pph.product_id, pph.price, pph.previous_price, pph.price_change_rate
FROM product_price_histories pph
JOIN products p ON pph.product_id = p.id
WHERE pph.is_current = TRUE
  AND pph.price_change_rate < -20  -- 20% 이상 하락
  AND p.status = 'active'
ORDER BY pph.price_change_rate ASC
LIMIT 50;

-- 최적화 인덱스
CREATE INDEX ix_price_hist_current_drop
ON product_price_histories(is_current, price_change_rate)
WHERE is_current = TRUE AND price_change_rate < 0;

-- ═══════════════════════════════════════════════════════════════════════════
-- 쿼리 3: 카테고리별 이상치 캐시 조회
-- 성능: < 20ms
-- ═══════════════════════════════════════════════════════════════════════════

-- 쿼리 패턴
SELECT pac.product_id, pac.anomaly_score, pac.detection_methods
FROM pred_price_anomaly_cache pac
WHERE pac.category_id = $1
  AND pac.expires_at > NOW()
ORDER BY pac.anomaly_score DESC
LIMIT 20;

-- 최적화 인덱스
CREATE INDEX ix_anomaly_cache_category
ON pred_price_anomaly_cache(category_id, anomaly_score DESC)
WHERE expires_at > NOW();
```

#### 🍳 RecipeGapFilling 모델

```sql
-- ═══════════════════════════════════════════════════════════════════════════
-- 쿼리 1: 상품 → 재료 매핑 조회
-- 성능: < 30ms
-- ═══════════════════════════════════════════════════════════════════════════

-- 쿼리 패턴
SELECT ip.ingredient_id, i.name
FROM pred_ingredient_products ip
JOIN pred_ingredients i ON ip.ingredient_id = i.id
WHERE ip.product_id IN ($1, $2, $3)
  AND ip.is_active = TRUE;

-- 최적화 인덱스
CREATE INDEX ix_ing_prod_product_active
ON pred_ingredient_products(product_id, ingredient_id)
WHERE is_active = TRUE;

-- ═══════════════════════════════════════════════════════════════════════════
-- 쿼리 2: 재료 → 레시피 매칭
-- 성능: < 100ms
-- ═══════════════════════════════════════════════════════════════════════════

-- 쿼리 패턴
SELECT ri.recipe_id, COUNT(*) AS matched_count
FROM pred_recipe_ingredients ri
WHERE ri.ingredient_id IN ($1, $2, $3, ...)
GROUP BY ri.recipe_id
HAVING COUNT(*) >= 2  -- 최소 2개 재료 매칭
ORDER BY matched_count DESC
LIMIT 10;

-- 최적화 인덱스
CREATE INDEX ix_recipe_ing_ingredient
ON pred_recipe_ingredients(ingredient_id, recipe_id);

-- ═══════════════════════════════════════════════════════════════════════════
-- 쿼리 3: 레시피 상세 + 부족 재료 조회
-- 성능: < 50ms
-- ═══════════════════════════════════════════════════════════════════════════

-- 쿼리 패턴
SELECT r.id, r.name, r.rating,
       ri.ingredient_id, i.name AS ingredient_name,
       ri.is_required, ri.is_main
FROM pred_recipes r
JOIN pred_recipe_ingredients ri ON r.id = ri.recipe_id
JOIN pred_ingredients i ON ri.ingredient_id = i.id
WHERE r.id IN ($1, $2, ...)
  AND r.is_active = TRUE
ORDER BY r.rating DESC, ri.is_main DESC, ri.is_required DESC;

-- 최적화 인덱스
CREATE INDEX ix_recipe_ing_recipe_main
ON pred_recipe_ingredients(recipe_id, is_main DESC, is_required DESC);

-- ═══════════════════════════════════════════════════════════════════════════
-- 쿼리 4: 재료 → 상품 추천
-- 성능: < 30ms
-- ═══════════════════════════════════════════════════════════════════════════

-- 쿼리 패턴
SELECT ip.product_id, p.name, p.price, ip.similarity_score
FROM pred_ingredient_products ip
JOIN products p ON ip.product_id = p.id
WHERE ip.ingredient_id = $1
  AND ip.is_active = TRUE
  AND p.status = 'active'
ORDER BY ip.priority DESC, ip.similarity_score DESC
LIMIT 3;

-- 최적화 인덱스
CREATE INDEX ix_ing_prod_ingredient_priority
ON pred_ingredient_products(ingredient_id, priority DESC, similarity_score DESC)
WHERE is_active = TRUE;
```

### 4.3 인덱스 전체 목록

```sql
-- ═══════════════════════════════════════════════════════════════════════════
-- 전체 인덱스 DDL (신규 테이블용)
-- ═══════════════════════════════════════════════════════════════════════════

-- Instacart 테이블
CREATE INDEX ix_inst_aisles_dept ON pred_instacart_aisles(department_id);
CREATE INDEX ix_inst_products_aisle ON pred_instacart_products(aisle_id);
CREATE INDEX ix_inst_products_name ON pred_instacart_products(name_normalized);
CREATE INDEX ix_inst_products_popularity ON pred_instacart_products(order_count DESC);
CREATE INDEX ix_inst_orders_user ON pred_instacart_orders(user_id);
CREATE INDEX ix_inst_orders_eval ON pred_instacart_orders(eval_set);
CREATE INDEX ix_inst_orders_time_context ON pred_instacart_orders(eval_set, order_dow, order_hour_of_day);
CREATE INDEX ix_inst_orders_user_seq ON pred_instacart_orders(user_id, order_number);
CREATE INDEX ix_inst_order_items_order ON pred_instacart_order_items(order_id);
CREATE INDEX ix_inst_order_items_product ON pred_instacart_order_items(product_id);
CREATE INDEX ix_inst_order_items_product_reorder ON pred_instacart_order_items(product_id, is_reordered);

-- 사전 집계 테이블 (신규)
CREATE UNIQUE INDEX ix_inst_time_patterns_lookup ON pred_instacart_time_patterns(time_slot, day_type, instacart_department_id);
CREATE INDEX ix_inst_time_patterns_category ON pred_instacart_time_patterns(self_category_id);
CREATE UNIQUE INDEX ix_inst_category_mapping_lookup ON pred_instacart_category_mapping(instacart_department_id, self_category_id);

-- 유사도 테이블 (신규)
CREATE INDEX ix_item_sim_source_type ON pred_item_similarity(source_product_id, similarity_type, similarity_score DESC);
CREATE INDEX ix_item_sim_calculated ON pred_item_similarity(calculated_at);

-- Product Mapping 테이블
CREATE INDEX ix_product_mapping_self ON pred_product_mapping(self_product_id);
CREATE INDEX ix_product_mapping_inst ON pred_product_mapping(instacart_product_id);
CREATE INDEX ix_product_mapping_inst_active ON pred_product_mapping(instacart_product_id, similarity_score DESC) WHERE is_active = TRUE;
CREATE INDEX ix_product_mapping_score ON pred_product_mapping(similarity_score DESC);

-- Recipe 테이블
CREATE INDEX ix_recipes_name ON pred_recipes(name_normalized);
CREATE INDEX ix_recipes_category ON pred_recipes(category_main, category_sub);
CREATE INDEX ix_recipes_popularity ON pred_recipes(rating DESC, like_count DESC);
CREATE INDEX ix_recipes_active ON pred_recipes(is_active) WHERE is_active = TRUE;
CREATE INDEX ix_recipes_active_popular ON pred_recipes(category_main, rating DESC) WHERE is_active = TRUE;

-- Ingredient 테이블
CREATE INDEX ix_ingredients_name ON pred_ingredients(name_normalized);
CREATE INDEX ix_ingredients_category ON pred_ingredients(category);
CREATE INDEX ix_ingredients_processed ON pred_ingredients(is_processed);

-- Recipe-Ingredient 테이블
CREATE INDEX ix_recipe_ing_recipe ON pred_recipe_ingredients(recipe_id);
CREATE INDEX ix_recipe_ing_ingredient ON pred_recipe_ingredients(ingredient_id, recipe_id);
CREATE INDEX ix_recipe_ing_lookup ON pred_recipe_ingredients(ingredient_id, recipe_id, is_required);
CREATE INDEX ix_recipe_ing_recipe_main ON pred_recipe_ingredients(recipe_id, is_main DESC, is_required DESC);

-- Ingredient-Product 테이블
CREATE INDEX ix_ing_prod_ingredient ON pred_ingredient_products(ingredient_id);
CREATE INDEX ix_ing_prod_product ON pred_ingredient_products(product_id);
CREATE INDEX ix_ing_prod_product_active ON pred_ingredient_products(product_id, ingredient_id) WHERE is_active = TRUE;
CREATE INDEX ix_ing_prod_ingredient_priority ON pred_ingredient_products(ingredient_id, priority DESC, similarity_score DESC) WHERE is_active = TRUE;

-- Embedding 테이블
CREATE INDEX ix_user_emb_type ON pred_user_embeddings(user_type);
CREATE INDEX ix_user_emb_warm ON pred_user_embeddings(user_type) WHERE user_type = 'warm';
CREATE INDEX ix_user_emb_updated ON pred_user_embeddings(updated_at);

-- Cache 테이블
CREATE INDEX ix_rec_cache_user ON pred_recommendation_cache(user_id);
CREATE INDEX ix_rec_cache_lookup ON pred_recommendation_cache(user_id, page_type, context_hash, expires_at);
CREATE INDEX ix_rec_cache_expires ON pred_recommendation_cache(expires_at);
CREATE INDEX ix_anomaly_score ON pred_price_anomaly_cache(anomaly_score DESC);
CREATE INDEX ix_anomaly_category ON pred_price_anomaly_cache(category_id);
CREATE INDEX ix_anomaly_cache_category ON pred_price_anomaly_cache(category_id, anomaly_score DESC) WHERE expires_at > NOW();
CREATE INDEX ix_anomaly_expires ON pred_price_anomaly_cache(expires_at);
```

---

## 5. 트랜잭션 경계 및 격리 수준

### 5.1 트랜잭션 설계 원칙

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           트랜잭션 설계 원칙                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  원칙 1: 읽기 작업은 READ COMMITTED                                         │
│  ─────────────────────────────────                                          │
│  • 추천 조회, 캐시 읽기 등 대부분의 읽기 작업                                │
│  • 성능 우선, 약간의 데이터 불일치 허용                                      │
│                                                                             │
│  원칙 2: 캐시 갱신은 REPEATABLE READ                                        │
│  ──────────────────────────────────                                         │
│  • pred_recommendation_cache, pred_price_anomaly_cache 갱신 시              │
│  • 갱신 중 일관된 데이터 보장                                               │
│                                                                             │
│  원칙 3: 배치 작업은 청크 단위 트랜잭션                                      │
│  ─────────────────────────────────────                                      │
│  • 1000건씩 청크 단위로 커밋                                                │
│  • 실패 시 해당 청크만 롤백, 재시도                                          │
│                                                                             │
│  원칙 4: 교착 상태 방지                                                     │
│  ───────────────────────                                                    │
│  • 테이블 접근 순서 통일 (alphabetical)                                     │
│  • SELECT ... FOR UPDATE 최소화                                             │
│  • 타임아웃 설정 (statement_timeout = 30s)                                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.2 주요 작업별 트랜잭션 경계

```python
# ═══════════════════════════════════════════════════════════════════════════
# 1. 추천 결과 조회 (READ COMMITTED, 읽기 전용)
# ═══════════════════════════════════════════════════════════════════════════

async def get_recommendations(user_id: int, page_type: str):
    """
    트랜잭션 경계: 없음 (단일 쿼리)
    격리 수준: READ COMMITTED (기본값)
    """
    # 캐시 조회 → 단일 쿼리, 트랜잭션 불필요
    cache = await db.fetch_one("""
        SELECT recommendations FROM pred_recommendation_cache
        WHERE user_id = $1 AND page_type = $2 AND expires_at > NOW()
    """, user_id, page_type)
    return cache

# ═══════════════════════════════════════════════════════════════════════════
# 2. 추천 캐시 갱신 (REPEATABLE READ)
# ═══════════════════════════════════════════════════════════════════════════

async def update_recommendation_cache(user_id: int, page_type: str, recommendations: list):
    """
    트랜잭션 경계: BEGIN → INSERT/UPDATE → COMMIT
    격리 수준: REPEATABLE READ
    """
    async with db.transaction(isolation="repeatable read"):
        # UPSERT 패턴
        await db.execute("""
            INSERT INTO pred_recommendation_cache
                (user_id, page_type, context_hash, recommendations, expires_at)
            VALUES ($1, $2, $3, $4, NOW() + INTERVAL '1 hour')
            ON CONFLICT (user_id, page_type, context_hash)
            DO UPDATE SET recommendations = $4, expires_at = NOW() + INTERVAL '1 hour'
        """, user_id, page_type, context_hash, json.dumps(recommendations))

# ═══════════════════════════════════════════════════════════════════════════
# 3. 배치 집계 작업 (청크 단위 트랜잭션)
# ═══════════════════════════════════════════════════════════════════════════

async def aggregate_time_patterns():
    """
    트랜잭션 경계: 청크별 BEGIN → BULK INSERT → COMMIT
    격리 수준: READ COMMITTED
    청크 크기: 100건
    """
    CHUNK_SIZE = 100
    time_slots = ['morning', 'lunch', 'dinner', 'night']
    day_types = ['weekday', 'weekend']

    for time_slot in time_slots:
        for day_type in day_types:
            patterns = await compute_patterns(time_slot, day_type)

            for i in range(0, len(patterns), CHUNK_SIZE):
                chunk = patterns[i:i+CHUNK_SIZE]
                async with db.transaction():
                    await db.execute_many("""
                        INSERT INTO pred_instacart_time_patterns
                            (time_slot, day_type, instacart_department_id,
                             self_category_id, popularity_score, reorder_rate)
                        VALUES ($1, $2, $3, $4, $5, $6)
                        ON CONFLICT (time_slot, day_type, instacart_department_id)
                        DO UPDATE SET popularity_score = $5, reorder_rate = $6,
                                      aggregated_at = NOW()
                    """, chunk)

# ═══════════════════════════════════════════════════════════════════════════
# 4. 상품 유사도 계산 (배치, 청크 단위)
# ═══════════════════════════════════════════════════════════════════════════

async def compute_item_similarities():
    """
    트랜잭션 경계: 상품별 BEGIN → INSERT → COMMIT
    격리 수준: READ COMMITTED
    실행 주기: 일 1회 (새벽 3시)
    """
    products = await db.fetch_all("""
        SELECT id FROM products WHERE status = 'active'
    """)

    for product in products:
        similarities = await compute_similar_items(product.id)

        async with db.transaction():
            # 기존 유사도 삭제 후 새로 삽입
            await db.execute("""
                DELETE FROM pred_item_similarity
                WHERE source_product_id = $1
            """, product.id)

            await db.execute_many("""
                INSERT INTO pred_item_similarity
                    (source_product_id, similar_product_id, similarity_score,
                     similarity_type, calculated_at)
                VALUES ($1, $2, $3, $4, NOW())
            """, [(product.id, s.id, s.score, s.type) for s in similarities])
```

---

## 6. 쿼리 성능 예상

### 6.1 주요 쿼리 실행 계획 예상

| 모델 | 쿼리 | 예상 실행 시간 | 인덱스 사용 | 비고 |
|------|------|---------------|-------------|------|
| **ColdStart** |
| | 시간대별 인기 카테고리 (집계 테이블) | < 10ms | ix_inst_time_patterns_lookup | 168행 테이블 |
| | 카테고리별 SelF 상품 | < 50ms | ix_products_category_status | 기존 인덱스 |
| | SelF 매핑 조회 (Fallback) | < 30ms | ix_product_mapping_inst_active | 10K 매핑 |
| **Personalized** |
| | 최근 조회 상품 | < 10ms | ix_ups_user_recent | 기존 인덱스 |
| | 사전 계산 유사 상품 | < 20ms | ix_item_sim_source_type | 집계 테이블 |
| | 유사 사용자 CF | < 100ms | ix_user_emb_warm, ix_ups_user_ordered | 복합 조인 |
| **PriceAnomaly** |
| | 가격 이력 조회 | < 50ms | ix_price_hist_analysis | 30일 범위 |
| | 급락 상품 조회 | < 100ms | ix_price_hist_current_drop | 전체 스캔 회피 |
| | 이상치 캐시 조회 | < 20ms | ix_anomaly_cache_category | 캐시 히트 |
| **GapFilling** |
| | 상품→재료 매핑 | < 30ms | ix_ing_prod_product_active | 부분 인덱스 |
| | 재료→레시피 | < 100ms | ix_recipe_ing_ingredient | GROUP BY |
| | 레시피→부족재료 | < 50ms | ix_recipe_ing_recipe_main | 다중 JOIN |
| | 재료→상품 추천 | < 30ms | ix_ing_prod_ingredient_priority | TOP 3 |

### 6.2 성능 목표 및 SLA

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           성능 목표 (SLA)                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  API 응답 시간 목표:                                                        │
│  ──────────────────                                                         │
│  • p50 (중앙값): < 100ms                                                    │
│  • p95: < 300ms                                                             │
│  • p99: < 500ms                                                             │
│                                                                             │
│  캐시 히트율 목표:                                                          │
│  ────────────────                                                           │
│  • Redis: > 80%                                                             │
│  • PostgreSQL 캐시 테이블: > 50% (Redis 미스 시)                            │
│                                                                             │
│  배치 처리 목표:                                                            │
│  ──────────────                                                             │
│  • 시간대별 집계 (pred_instacart_time_patterns): < 5분                      │
│  • 유사도 계산 (pred_item_similarity): < 30분 (10K 상품 기준)               │
│  • 가격 이상치 분석: < 10분                                                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 6.3 캐시 전략

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              캐시 레이어 전략                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Layer 1: Redis (메모리 캐시)                                               │
│  ────────────────────────────                                               │
│  • 추천 결과 캐시 (TTL: 5분~1시간)                                          │
│  • 사용자 임베딩 벡터 (TTL: 1일)                                            │
│  • 가격 이상치 목록 (TTL: 30분)                                             │
│  • Hot 상품 임베딩 (TTL: 1시간)                                             │
│                                                                             │
│  Layer 2: PostgreSQL Cache 테이블 (영속 캐시)                               │
│  ─────────────────────────────────────────────                              │
│  • pred_recommendation_cache (Redis 장애 대비)                              │
│  • pred_price_anomaly_cache (배치 분석 결과)                                │
│  • pred_instacart_time_patterns (사전 집계)                                 │
│  • pred_item_similarity (사전 계산 유사도)                                  │
│                                                                             │
│  Layer 3: Application Cache (프로세스 내 캐시)                              │
│  ──────────────────────────────────────────────                             │
│  • 정적 데이터 (카테고리 매핑, 재료 사전)                                    │
│  • 모델 파라미터                                                            │
│                                                                             │
│  캐시 무효화 전략:                                                          │
│  ──────────────────                                                         │
│  • 시간 기반 TTL (자동 만료)                                                │
│  • 이벤트 기반 (가격 변동 시 해당 상품 캐시 무효화)                          │
│  • 배치 갱신 (1시간마다 전체 이상치 분석)                                    │
│                                                                             │
│  TTL 설정:                                                                  │
│  ──────────                                                                 │
│  • 추천 캐시: 홈페이지 30분, 상품 상세 1시간, 장바구니 5분                   │
│  • 가격 이상치: 30분                                                        │
│  • 사용자 임베딩: 24시간                                                    │
│  • 상품 유사도: 24시간                                                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 7. 데이터 용량 및 확장성

### 7.1 테이블별 예상 용량

| 테이블 | 예상 레코드 | 예상 용량 | 증가율/월 |
|--------|------------|----------|----------|
| **기존 테이블** |
| `products` | 10,000 | 10 MB | +500 |
| `product_price_histories` | 100,000 | 50 MB | +10,000 |
| `user_product_stats` | 500,000 | 100 MB | +50,000 |
| **신규 테이블** |
| `pred_instacart_products` | 49,688 | 10 MB | 0 (정적) |
| `pred_instacart_orders` (파티셔닝) | 3,421,083 | 200 MB | 0 (정적) |
| `pred_instacart_order_items` | 32,434,489 | 1.5 GB | 0 (정적) |
| `pred_instacart_time_patterns` | 168 | < 1 MB | 0 (배치 갱신) |
| `pred_instacart_category_mapping` | 200 | < 1 MB | +10 |
| `pred_item_similarity` | 200,000 | 50 MB | +10,000 |
| `pred_recipes` | 50,000 | 50 MB | +1,000 |
| `pred_ingredients` | 5,000 | 1 MB | +100 |
| `pred_recipe_ingredients` | 500,000 | 50 MB | +10,000 |
| `pred_product_mapping` | 10,000 | 5 MB | +500 |
| `pred_ingredient_products` | 50,000 | 10 MB | +5,000 |
| `pred_product_embeddings` | 10,000 | 100 MB | +500 |
| `pred_user_embeddings` | 100,000 | 50 MB | +10,000 |
| `pred_recommendation_cache` | 1,000,000 | 500 MB | 자동 정리 |
| `pred_price_anomaly_cache` | 10,000 | 10 MB | 자동 정리 |
| **총계** | | **~2.7 GB** | |

### 7.2 확장 전략

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              확장 전략                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Phase 1: 현재 (사용자 1K~10K)                                              │
│  ─────────────────────────────                                              │
│  • 단일 PostgreSQL 인스턴스                                                 │
│  • Redis 단일 인스턴스                                                      │
│  • 파티셔닝: pred_instacart_orders만 적용                                   │
│                                                                             │
│  Phase 2: 성장기 (사용자 10K~100K)                                          │
│  ───────────────────────────────                                            │
│  • PostgreSQL Read Replica 추가                                             │
│  • Redis Cluster 전환                                                       │
│  • 파티셔닝: product_price_histories 추가                                   │
│                                                                             │
│  Phase 3: 확장기 (사용자 100K+)                                             │
│  ──────────────────────────────                                             │
│  • 샤딩 고려 (user_id 기반)                                                 │
│  • 임베딩 벡터 전용 DB (Milvus/Pinecone)                                    │
│  • 캐시 테이블 별도 DB 분리                                                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 8. 설계 검증 체크리스트

### 8.1 정규화 체크리스트

- [x] 모든 테이블 1NF 만족 (원자값)
- [x] 복합키 테이블 2NF 만족 (부분 함수 종속 없음)
- [x] 모든 테이블 3NF 만족 (이행적 종속 없음)
- [x] BCNF 만족 검증 완료
- [x] 의도적 비정규화 문서화 완료
- [x] 비정규화 데이터 동기화 전략 수립

### 8.2 인덱스 체크리스트

- [x] 모든 FK에 인덱스 생성
- [x] 주요 쿼리 패턴 분석 완료
- [x] 복합 인덱스 컬럼 순서 최적화
- [x] 부분 인덱스 적용 (is_active, expires_at)
- [x] 커버링 인덱스 검토 완료

### 8.3 데이터 무결성 체크리스트

- [x] FK 제약조건 정의 (CASCADE, SET NULL, RESTRICT)
- [x] UNIQUE 제약조건 정의
- [x] NOT NULL 제약조건 검토
- [x] CHECK 제약조건 필요 컬럼 식별
- [x] 기본값 (DEFAULT) 설정

### 8.4 확장성 체크리스트

- [x] 데이터 용량 예측 완료
- [x] 파티셔닝 전략 수립 (pred_instacart_orders 적용)
- [x] 캐시 계층 설계
- [x] 인덱스 유지보수 비용 검토

### 8.5 트랜잭션 체크리스트 (v1.1.0 추가)

- [x] 읽기/쓰기 작업별 격리 수준 정의
- [x] 배치 작업 청크 단위 트랜잭션 설계
- [x] 교착 상태 방지 전략 수립
- [x] 타임아웃 설정 검토

### 8.6 문서 동기화 체크리스트 (v1.1.0 추가)

- [x] RECOMMENDATION_SYSTEM_ARCHITECTURE.md와 테이블 동기화
- [x] DATABASE_SCHEMA_RECOMMENDATION.md와 컬럼 동기화
- [x] 신규 테이블 반영: pred_instacart_time_patterns
- [x] 신규 테이블 반영: pred_instacart_category_mapping
- [x] 신규 테이블 반영: pred_item_similarity
- [x] pred_ingredients.is_processed 컬럼 추가
- [x] pred_recipes 컬럼 동기화 (name_normalized, like_count, category_sub)

---

## 9. 데이터 무결성 규칙

### 9.1 FK 제약조건 정책

| 참조 테이블 | ON DELETE 동작 | 이유 |
|------------|---------------|------|
| `users` | CASCADE | 사용자 삭제 시 추천 데이터도 삭제 |
| `products` | CASCADE | 상품 삭제 시 관련 데이터도 삭제 |
| `categories` | RESTRICT | 카테고리는 참조 중이면 삭제 불가 |
| Instacart 테이블 | 없음 (정적) | 삭제 없음, 참조만 |

### 9.2 데이터 동기화 규칙

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          데이터 동기화 정책                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. 상품 삭제 시:                                                           │
│     - CASCADE로 자동 정리 (임베딩, 유사도, 캐시)                             │
│     - Redis 캐시는 배치에서 정리 (키 만료 의존)                               │
│                                                                             │
│  2. 가격 변동 시:                                                           │
│     - pred_price_anomaly_cache 즉시 무효화 필요                             │
│     - 트리거 또는 애플리케이션 레벨에서 처리                                   │
│                                                                             │
│     예시 트리거:                                                             │
│     CREATE OR REPLACE FUNCTION invalidate_price_cache()                     │
│     RETURNS TRIGGER AS $$                                                   │
│     BEGIN                                                                   │
│         DELETE FROM pred_price_anomaly_cache                                │
│         WHERE product_id = NEW.product_id;                                  │
│         RETURN NEW;                                                         │
│     END;                                                                    │
│     $$ LANGUAGE plpgsql;                                                    │
│                                                                             │
│  3. 임베딩 갱신 시:                                                         │
│     - 버전 컬럼으로 관리 (bert_version, version)                             │
│     - 읽기 중 갱신 안전 (MVCC)                                              │
│     - 갱신 완료 후 캐시 웜업                                                 │
│                                                                             │
│  4. 배치 작업 시:                                                           │
│     - 대용량 INSERT는 청크 단위 (1000건씩)                                   │
│     - 실패 시 해당 청크만 롤백                                               │
│     - UPSERT 패턴 사용 (ON CONFLICT DO UPDATE)                              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 9.3 데이터 보존 정책

| 테이블 | 보존 기간 | 정리 방법 |
|--------|----------|----------|
| `pred_recommendation_cache` | TTL 기반 (1시간~1일) | 배치 정리 + 자동 만료 |
| `pred_price_anomaly_cache` | TTL 기반 (30분~6시간) | 배치 정리 + 자동 만료 |
| `pred_item_similarity` | 영구 (갱신) | 배치에서 전체 교체 |
| `pred_user_embeddings` | 영구 (갱신) | 비활성 유저 90일 후 삭제 |
| `pred_instacart_*` | 영구 | 정적 데이터, 삭제 없음 |

---

**작성자**: SelF 개발팀
**관련 문서**:
- RECOMMENDATION_SYSTEM_ARCHITECTURE.md (v3.1.0)
- MODEL_BLENDING_STRATEGY.md (v1.0.0)
- docs/backend/DATABASE_SCHEMA_DETAILED.md
