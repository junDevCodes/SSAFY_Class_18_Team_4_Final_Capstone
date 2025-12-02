# FreshPick 데이터베이스 스키마 상세 문서 (DB v2.1)

> **문서 버전**: v2.1.0
> **최종 수정일**: 2025년 12월 01일
>
> 이 문서는 DBML 스타일 스키마 정의(Enums, Group 1~9 테이블)를 기준으로,
> 각 도메인/테이블/컬럼이 **무슨 역할을 하고 어떤 비즈니스 규칙을 가지는지**를
> 상세하게 설명합니다. 실제 구현은 PostgreSQL + Django ORM을 기준으로 합니다.
>
> **v2.1 변경사항**:
> - `product_price_histories` 테이블 추가 (가격 변동 이력 추적)
> - 데이터 파이프라인(JSON → DB)에서 가격 변동 자동 기록 지원

---

## 1. 공통 설계 개요

- **DBMS**: PostgreSQL 14+ (개발 환경에서는 SQLite3 가능)
- **ORM**: Django ORM
- **네이밍**
  - 테이블/컬럼: `snake_case`
  - PK: 대부분 `bigint` + `id` (또는 `<entity>_id` 형태)
  - 시간 컬럼: `created_at`, `updated_at`, `deleted_at` 패턴 사용
- **타입 선택**
  - ID/참조키: `bigint`
  - 상태/역할: 별도 `Enum` 정의 후 `varchar`/`enum` 으로 매핑
  - 카운트/집계: 트래픽 급증과 장기 누적을 고려해 주요 집계 컬럼은 `bigint`
- **타임스탬프**
  - `created_at`: 생성 시각 (대부분 `DEFAULT CURRENT_TIMESTAMP`)
  - `updated_at`: 갱신 시각 (트리거/애플리케이션 레벨에서 관리)
  - `deleted_at`: 소프트 삭제(휴먼/기록 보존용) 시각

---

## 2. Enum 정의

### 2.1 `user_role`

사용자 계정의 권한 레벨을 나타내는 열거형입니다.

- `guest`: 게스트/비회원. 일반적으로 회원가입 전 상태 또는 최소 권한 유저.
- `user`: 일반 회원. 기본 구매/리뷰/찜 기능을 사용할 수 있는 일반 소비자.
- `seller`: 판매자. `sellers` 레코드와 1:1로 연결되는 셀러 계정.
- `admin`: 관리자. 운영/CS/모니터링/통계 등 백오피스 권한 보유.

**주요 사용 위치**
- `users.role`
- 인가 로직 (예: 셀러 기능 접근은 `role = seller` 이상 등)

---

### 2.2 `business_type`

판매자의 사업자 유형을 나타냅니다.

- `individual`: 개인 사업자
- `corporate`: 법인 사업자
- `cooperative`: 협동조합/단체 등

**주요 사용 위치**
- `seller_businesses.business_type`
- 세금계산서/정산/계약 조건이 사업자 유형별로 다를 때 분기 근거로 사용.

---

### 2.3 `seller_status`

판매자 계정/브랜드의 운영 상태입니다.

- `pending`: 심사 대기/서류 검토 완료 전 상태
- `active`: 정상 판매 중
- `suspended`: 일시 중지 (정책 위반/문의 등으로 일시 제한)
- `inactive`: 영구 종료/퇴점 상태

**주요 사용 위치**
- `sellers.status`
- 마켓플레이스에서 노출/판매 가능 여부, 정산 가능 여부 제어.

---

### 2.4 `product_status`

상품의 판매/노출 상태입니다.

- `draft`: 비공개 임시 저장 상태 (셀러가 편집 중)
- `active`: 정상 판매/노출 중
- `inactive`: 비노출 (판매 중단, 정책 위반 등)
- `out_of_stock`: 품절 (재고 0, 일시적인 상태)
- `discontinued`: 단종 (재입고 계획 없음)

**주요 사용 위치**
- `products.status`
- 검색/리스트/상세 노출 여부, 장바구니/주문 시 유효성 검사에 활용.

---

### 2.5 `product_type`

상품의 역할/출처 유형입니다.

- `main`: 플랫폼의 메인 상품 (기본/대표 상품)
- `seller`: 셀러 자체 등록 상품 (크롤링/CSV가 아닌 직접 등록 등)

**주요 사용 위치**
- `products.product_type`
- 추천/프로모션/정산에서 메인 상품과 셀러 상품을 구분할 때 사용.

---

### 2.6 `order_status`

주문 전체(헤더)의 상태를 나타냅니다.

- `pending`: 주문 생성 직후, 결제/확인 대기
- `paid`: 결제 완료 (입금/승인 완료)
- `processing`: 주문 처리 중 (픽/패킹 등)
- `shipped`: 발송 완료 (운송장 등록 이후)
- `delivered`: 배송 완료
- `cancelled`: 전체 주문 취소
- `refunded`: 전체 주문 환불 완료

**주요 사용 위치**
- `orders.status`
- 주문 단위 CS/정산/분석에서 기준이 되는 상태 값.

---

### 2.7 `order_item_status`

개별 주문 품목 단위의 상태입니다. 주문 전체와 구분해 부분 취소/부분 환불을 표현합니다.

- `pending`: 주문 생성 직후
- `paid`: 결제 완료
- `shipping`: 배송 중
- `delivered`: 배송 완료
- `cancelled`: 해당 품목만 취소
- `refunded`: 해당 품목만 환불

**주요 사용 위치**
- `order_items.status`
- 주문 내 특정 품목만 취소/환불/재발송하는 시나리오 처리.

---

### 2.8 `payment_status`

결제 트랜잭션 단위의 상태입니다.

- `pending`: 결제 시도 중 / 결과 대기
- `success`: 결제 성공
- `failed`: 결제 실패
- `cancelled`: 결제 취소(승인 취소/전표 취소 등)

**주요 사용 위치**
- `payments.status`
- PG 연동, 재시도 로직, 결제 로그 분석에서 사용.

---

### 2.9 `payment_method_type`

결제 수단의 유형입니다.

- `card`: 신용/체크 카드
- `bank_transfer`: 계좌이체
- `virtual_account`: 가상계좌
- `mobile`: 휴대폰 결제
- `other`: 기타(포인트, 상품권, 복합결제 등)

**주요 사용 위치**
- `payments.method_type`
- 결제 수단별 매출/수수료/전환율 지표 분석.

---

### 2.10 `gender_type`

선택적인 성별 정보입니다.

- `male`
- `female`
- `other`
- `prefer_not_to_say`: 응답 거부

**주요 사용 위치**
- `user_profiles.gender`
- 통계/맞춤형 추천 등에서 선택적으로 사용 (민감정보이므로 최소 수집/활용 원칙).

---

## 3. Group 1 – Users & Auth (JWT 기반)

**도메인 개요:**  
회원 계정, 프로필, 배송지, 이메일 회원가입, 이메일/소셜 로그인 자격을 관리하는 영역입니다.  
JWT 기반 인증을 사용하며, 토큰 자체는 DB에 저장하지 않고 User/자격정보만 관리합니다.

### 3.1 `users` 테이블

회원 계정의 **기본 식별자와 권한/활성화 상태**를 관리하는 핵심 엔터티입니다.

- 한 유저당 1 레코드
- `user_profiles`, `user_addresses`, `auth_email_credentials`, `auth_google_accounts`, `auth_kakao_accounts`, `sellers`, `orders`, `carts`, `wishlists` 등 대부분 도메인의 루트 FK가 됩니다.

#### 주요 컬럼

| 컬럼          | 타입            | 제약                           | 설명 |
|--------------|-----------------|--------------------------------|------|
| `id`         | `bigint`        | PK, auto increment             | 사용자 고유 ID. 모든 도메인의 FK 기준이 되는 키. |
| `email`      | `varchar(254)`  | NOT NULL, UNIQUE               | 로그인 및 공지용 이메일. 중복 가입 방지를 위해 유니크. |
| `username`   | `varchar(150)`  | NOT NULL, UNIQUE               | 서비스 내 표시 이름/아이디. 검색/표시 용도로 사용. |
| `role`       | `user_role`     | NOT NULL, DEFAULT `'guest'`    | 권한 레벨(`guest`/`user`/`seller`/`admin`). 접근 제어에 사용. |
| `is_active`  | `boolean`       | NOT NULL, DEFAULT `true`       | 계정 활성화 여부. 탈퇴/정지 시 false, 로그인 차단. |
| `last_login` | `timestamp`     | NULL                           | 마지막 로그인 시각. 휴면 계정 처리 및 보안 감사용. |
| `created_at` | `timestamp`     | NOT NULL, DEFAULT now          | 계정 생성 시각. 통계/운영 기준. |
| `updated_at` | `timestamp`     | NOT NULL, DEFAULT now          | 마지막 정보 변경 시각. |
| `deleted_at` | `timestamp`     | NULL                           | 소프트 삭제 시각. 실제 삭제 대신 기록 유지용. |

#### 인덱스 및 사용 패턴

- `email`: 로그인/인증/가입 중복 체크에서 자주 사용.
- `role`: 역할별 필터링 (셀러/관리자 목록 조회 등).
- `created_at`: 가입 추이, 통계 집계 시 사용.

---

### 3.2 `user_profiles` 테이블

사용자의 **프로필/환경 설정/마케팅 동의** 정보를 관리하는 1:1 확장 테이블입니다.

- PK가 `user_id` 이므로 `users` 와 완전 1:1 관계.
- 계정 기본 정보와 분리해, 민감도/변동성이 높은 프로필 정보를 별도 관리합니다.

#### 주요 컬럼

| 컬럼                    | 타입            | 제약                       | 설명 |
|------------------------|-----------------|----------------------------|------|
| `user_id`              | `bigint`        | PK, FK → `users.id`        | 사용자 ID (1:1 관계). |
| `profile_image_url`    | `text`          | NULL                       | 프로필 이미지 URL. CDN/스토리지 경로. |
| `phone_number`         | `varchar(20)`   | NULL, UNIQUE               | 휴대폰 번호. 인증/알림/CS용. 유니크로 중복 번호 방지. |
| `date_of_birth`        | `date`          | NULL                       | 생년월일. 선택 입력. |
| `gender`               | `gender_type`   | NULL                       | 성별 정보. 선택 입력. |
| `timezone`             | `varchar(64)`   | NOT NULL, DEFAULT `'Asia/Seoul'` | 사용자 기본 시간대. 알림/이벤트 시간 계산용. |
| `language`             | `varchar(10)`   | NOT NULL, DEFAULT `'ko'`   | UI/메일/알림에 사용할 언어 코드. |
| `notification_enabled` | `boolean`       | NOT NULL, DEFAULT `true`   | 서비스 알림(푸시/이메일) 수신 여부. |
| `marketing_agreed`     | `boolean`       | NOT NULL, DEFAULT `false`  | 마케팅 수신 동의 여부. 광고성 정보 발송에 활용. |
| `updated_at`           | `timestamp`     | NOT NULL, DEFAULT now      | 마지막 수정 시각. |

---

### 3.3 `user_addresses` 테이블

사용자의 **배송지 주소록**을 관리합니다.

- 1 유저 : N 주소
- 기본 배송지(`is_default`)를 한 개 관리할 수 있도록 `(user_id, is_default)` 인덱스를 구성합니다.

#### 주요 컬럼

| 컬럼             | 타입            | 제약                          | 설명 |
|-----------------|-----------------|-------------------------------|------|
| `id`            | `bigint`        | PK, auto increment            | 주소 레코드 ID. |
| `user_id`       | `bigint`        | NOT NULL, FK → `users.id`     | 주소 소유자. |
| `address_name`  | `varchar(100)`  | NOT NULL                      | “집”, “회사” 등 사용자가 붙인 별칭. |
| `recipient_name`| `varchar(100)`  | NOT NULL                      | 수령인 이름. |
| `recipient_phone`| `varchar(20)`  | NOT NULL                      | 수령인 연락처. |
| `postal_code`   | `varchar(10)`   | NOT NULL                      | 우편번호. |
| `address_line1` | `varchar(255)`  | NOT NULL                      | 기본 주소 (도로명/지번). |
| `address_line2` | `varchar(255)`  | NULL                          | 상세 주소 (동/호수 등). |
| `is_default`    | `boolean`       | NOT NULL, DEFAULT `false`     | 기본 배송지 여부. |
| `created_at`    | `timestamp`     | NOT NULL, DEFAULT now         | 생성 시각. |
| `updated_at`    | `timestamp`     | NOT NULL, DEFAULT now         | 수정 시각. |

#### 인덱스

- `user_id`: 유저별 주소 목록 조회.
- `(user_id, is_default)`: 기본 배송지 1건 빠르게 조회.

---

### 3.4 `pending_registrations` 테이블

이메일 회원가입 **인증 대기 상태**를 저장합니다.

- 사용자가 이메일/비밀번호/닉네임을 입력하면, 먼저 이 테이블에 저장 후 인증 메일 발송.
- 인증 코드가 검증되면 실제 `users` / `auth_email_credentials` 레코드로 승격.

#### 주요 컬럼

| 컬럼                | 타입            | 제약                  | 설명 |
|--------------------|-----------------|-----------------------|------|
| `id`               | `bigint`        | PK, auto increment    | 대기 레코드 ID. |
| `email`            | `varchar(254)`  | NOT NULL, UNIQUE      | 가입 요청 이메일. 중복 요청 방지. |
| `username`         | `varchar(150)`  | NOT NULL              | 희망 사용자명. |
| `password_hash`    | `varchar(128)`  | NOT NULL              | 해시된 비밀번호. |
| `verification_code`| `varchar(64)`   | NOT NULL              | 이메일 인증 코드(토큰). |
| `expires_at`       | `timestamp`     | NOT NULL              | 인증 코드 만료 시각. |
| `created_at`       | `timestamp`     | NOT NULL, DEFAULT now | 생성 시각. |
| `updated_at`       | `timestamp`     | NOT NULL, DEFAULT now | 수정 시각. |

#### 사용 시나리오

1. 사용자가 회원가입 정보 제출 → `pending_registrations` 생성.
2. 이메일로 인증 코드 전송.
3. 사용자가 코드 입력 → `verification_code`/`expires_at` 검증.
4. 성공 시 `users`/`auth_email_credentials` 생성 후, 이 레코드는 삭제 or 보관.

---

### 3.5 `auth_email_credentials` 테이블

이메일/비밀번호 기반 로그인 자격 정보를 관리합니다.

- `users` 와 1:1 관계 (`user_id`가 PK).
- 로그인 실패 횟수, 이메일 인증 여부 등을 포함해 보안 정책을 구현합니다.

#### 주요 컬럼

| 컬럼               | 타입           | 제약                       | 설명 |
|-------------------|----------------|----------------------------|------|
| `user_id`         | `bigint`       | PK, FK → `users.id`        | 사용자 ID. |
| `password_hash`   | `varchar(128)` | NOT NULL                   | 비밀번호 해시. |
| `is_email_verified`| `boolean`     | NOT NULL, DEFAULT `false`  | 이메일 인증 여부. |
| `fail_count`      | `int`          | NOT NULL, DEFAULT `0`      | 최근 로그인 실패 횟수. 계정 잠금 정책에 활용. |
| `last_changed_at` | `timestamp`    | NOT NULL, DEFAULT now      | 마지막 비밀번호 변경 시각. |

---

### 3.6 `auth_google_accounts` / 3.7 `auth_kakao_accounts`

각 소셜 로그인 제공자(Google, Kakao)에 대한 **연결 정보**를 별도 테이블로 관리합니다.

- 1 `user` : N 소셜 계정 → 사용자가 여러 소셜 계정을 연결할 수 있도록 설계.
- OAuth access token/refresh token은 보안상 DB에 저장하지 않고, 인증 시점에만 사용 후 폐기합니다.

#### 공통 컬럼

| 컬럼            | 타입           | 제약                            | 설명 |
|----------------|----------------|---------------------------------|------|
| `id`           | `bigint`       | PK, auto increment             | 소셜 계정 매핑 ID. |
| `user_id`      | `bigint`       | NOT NULL, FK → `users.id`      | 연결된 서비스 사용자 ID. |
| `<provider>_user_id` | `varchar(255)` | NOT NULL, UNIQUE        | Google/Kakao 측 고유 사용자 ID (sub, id 등). |
| `email`        | `varchar(254)` | NOT NULL                       | 공급자가 제공한 이메일. |
| `connected_at` | `timestamp`    | NOT NULL, DEFAULT now          | 계정 연결 시각. |

#### 사용 시나리오

- 최초 소셜 로그인 시:
  - 제공자 ID로 기존 매핑 존재 여부 확인.
  - 없으면 신규 가입 플로우(또는 기존 계정 연결 플로우)로 유도.
- 소셜 계정 해제:
  - 이 테이블의 레코드 삭제 (JWT는 만료되도록만 처리).

---

## 4. Group 2 – Seller Domain

**도메인 개요:**  
판매자 계정과 브랜드, 사업자/정산 정보, 영업 시간 등 **마켓플레이스의 공급자 측 데이터를 관리**합니다.

### 4.1 `sellers` 테이블

판매자 브랜드의 **공개 정보 및 상태**를 관리하는 핵심 엔터티입니다.

- 1 `user` : 1 `seller` (PK 별도, `user_id` UNIQUE FK).
- 브랜드 이름/슬러그는 노출/URL/검색에 사용합니다.

#### 주요 컬럼

| 컬럼              | 타입            | 제약                              | 설명 |
|------------------|-----------------|-----------------------------------|------|
| `id`             | `bigint`        | PK, auto increment                | 셀러 고유 ID. |
| `user_id`        | `bigint`        | NOT NULL, UNIQUE, FK → `users.id` | 셀러 계정의 사용자 ID. |
| `brand_name`     | `varchar(200)`  | NOT NULL, UNIQUE                  | 브랜드 이름. 화면 노출용. |
| `brand_slug`     | `varchar(200)`  | NOT NULL, UNIQUE                  | URL/path에 사용하는 슬러그. |
| `brand_logo_url` | `text`          | NULL                              | 로고 이미지 경로. |
| `brand_description` | `text`       | NULL                              | 브랜드 소개/스토리. |
| `status`         | `seller_status` | NOT NULL, DEFAULT `'pending'`     | 셀러 상태 (심사/활성/중단 등). |
| `created_at`     | `timestamp`     | NOT NULL, DEFAULT now             | 생성 시각. |
| `updated_at`     | `timestamp`     | NOT NULL, DEFAULT now             | 수정 시각. |

#### 인덱스

- `user_id`: 유저에서 셀러 정보 조회.
- `brand_slug`: 브랜드 상세 페이지 라우팅/조회.
- `status`: 심사 대기/활성 셀러 목록 필터링.

---

### 4.2 `seller_businesses` 테이블

판매자의 **사업자 등록 및 인증 정보**를 1:1로 관리합니다.

#### 주요 컬럼

| 컬럼                  | 타입            | 제약                        | 설명 |
|----------------------|-----------------|-----------------------------|------|
| `seller_id`          | `bigint`        | PK, FK → `sellers.id`       | 셀러 ID (1:1). |
| `registration_number`| `varchar(20)`   | NULL, UNIQUE                | 사업자등록번호. |
| `business_type`      | `business_type` | NULL                        | 사업자 유형(개인/법인/협동조합). |
| `company_name`       | `varchar(200)`  | NULL                        | 상호/법인명. |
| `ceo_name`           | `varchar(100)`  | NULL                        | 대표자 이름. |
| `business_address`   | `text`          | NULL                        | 사업장 주소. |
| `cs_phone`           | `varchar(20)`   | NULL                        | 고객센터/문의 전화. |
| `verification_doc_url`| `text`         | NULL                        | 사업자 증빙 서류(스캔본 등) URL. |
| `verified_at`        | `timestamp`     | NULL                        | 인증 완료 시각. |

---

### 4.3 `seller_settlements` 테이블

정산을 위한 **은행 계좌 정보**를 1:1로 관리합니다.

#### 주요 컬럼

| 컬럼             | 타입           | 제약                  | 설명 |
|-----------------|----------------|-----------------------|------|
| `seller_id`     | `bigint`       | PK, FK → `sellers.id` | 셀러 ID. |
| `bank_name`     | `varchar(50)`  | NOT NULL              | 은행 이름. |
| `account_number`| `varchar(50)`  | NOT NULL              | 계좌 번호(마스킹 가능). |
| `account_holder`| `varchar(100)` | NOT NULL              | 예금주 이름. |

---

### 4.4 `seller_schedules` 테이블

판매자의 **영업 요일/시간/휴무일**을 관리합니다.

- 한 셀러당 요일(0~6)별 한 레코드 (`(seller_id, day_of_week)` UNIQUE).

#### 주요 컬럼

| 컬럼         | 타입        | 제약                                | 설명 |
|-------------|-------------|-------------------------------------|------|
| `id`        | `bigint`    | PK, auto increment                  | 스케줄 레코드 ID. |
| `seller_id` | `bigint`    | NOT NULL, FK → `sellers.id`         | 셀러 ID. |
| `day_of_week`| `smallint` | NOT NULL                            | 0~6 (요일). |
| `open_time` | `time`      | NOT NULL                            | 오픈 시간. |
| `close_time`| `time`      | NOT NULL                            | 마감 시간. |
| `is_holiday`| `boolean`   | NOT NULL, DEFAULT `false`           | 해당 요일 휴무 여부. |
| `created_at`| `timestamp` | NOT NULL, DEFAULT now               | 생성 시각. |
| `updated_at`| `timestamp` | NOT NULL, DEFAULT now               | 수정 시각. |

---

## 5. Group 3 – Product Domain

**도메인 개요:**  
카테고리, 상품 기본 정보, 상세 설명, 재고, 이미지 등 **상품 카탈로그 전체**를 관리합니다.

### 5.1 `categories` 테이블

계층형 상품 카테고리를 관리합니다.

#### 주요 컬럼

| 컬럼        | 타입           | 제약                            | 설명 |
|------------|----------------|---------------------------------|------|
| `id`       | `bigint`       | PK, auto increment              | 카테고리 ID. |
| `parent_id`| `bigint`       | NULL, FK → `categories.id`      | 부모 카테고리 ID (루트는 NULL). |
| `name`     | `varchar(100)` | NOT NULL                        | 카테고리명. |
| `slug`     | `varchar(100)` | NOT NULL, UNIQUE                | 카테고리 슬러그(라우팅/URL 용). |
| `created_at`| `timestamp`   | NOT NULL, DEFAULT now           | 생성 시각. |
| `updated_at`| `timestamp`   | NOT NULL, DEFAULT now           | 수정 시각. |

---

### 5.2 `products` 테이블

상품의 **핵심 스펙/가격/배송 정보**를 관리하는 메인 엔터티입니다.

#### 주요 컬럼

| 컬럼                     | 타입              | 제약                         | 설명 |
|-------------------------|-------------------|------------------------------|------|
| `id`                    | `bigint`          | PK, auto increment           | 상품 ID. |
| `seller_id`             | `bigint`          | NOT NULL, FK → `sellers.id`  | 판매자 ID. |
| `category_id`           | `bigint`          | NULL, FK → `categories.id`   | 카테고리 ID. |
| `source_site`           | `varchar(100)`    | NULL                         | 초기 데이터 출처 사이트명(CSV/크롤링). |
| `source_url`            | `text`            | NULL                         | 원본 상품 URL. |
| `crawled_at`            | `timestamp`       | NULL                         | 원본 데이터를 가져온 시각. |
| `name`                  | `varchar(500)`    | NOT NULL                     | 상품명. |
| `slug`                  | `varchar(500)`    | NOT NULL, UNIQUE             | 상품 슬러그(상세 URL에 사용). |
| `price`                 | `int`             | NOT NULL                     | 현재 판매가. |
| `original_price`        | `int`             | NULL                         | 정상가/비교가. |
| `status`                | `product_status`  | NOT NULL, DEFAULT `'active'` | 상품 상태. |
| `product_type`          | `product_type`    | NOT NULL, DEFAULT `'main'`   | 상품 유형(main/seller). |
| `unit`                  | `varchar(50)`     | NULL                         | 단위(팩, kg 등). |
| `unit_quantity`         | `decimal(10,2)`   | NOT NULL, DEFAULT `1.00`     | 단위 수량(예: 1팩에 몇 g). |
| `shipping_required`     | `boolean`         | NOT NULL, DEFAULT `true`     | 배송 필요 여부(디지털 상품 등 구분). |
| `shipping_fee`          | `int`             | NOT NULL, DEFAULT `0`        | 기본 배송비. |
| `free_shipping_threshold`| `int`            | NULL                         | 무료 배송 기준 금액. |
| `estimated_delivery_days`| `smallint`       | NULL                         | 예상 배송일(일 단위). |
| `created_at`            | `timestamp`       | NOT NULL, DEFAULT now        | 생성 시각. |
| `updated_at`            | `timestamp`       | NOT NULL, DEFAULT now        | 수정 시각. |

---

### 5.3 `product_details` 테이블

상품의 **상세 설명 및 SEO 메타 정보**를 관리하는 1:1 확장 테이블입니다.

#### 주요 컬럼

| 컬럼             | 타입            | 제약                        | 설명 |
|-----------------|-----------------|-----------------------------|------|
| `product_id`    | `bigint`        | PK, FK → `products.id`      | 상품 ID. |
| `short_description`| `text`       | NULL                        | 짧은 요약 설명. |
| `full_description` | `text`       | NULL                        | 상세 설명(HTML/리치 텍스트 등). |
| `meta_title`    | `varchar(200)`  | NULL                        | SEO용 메타 타이틀. |
| `meta_keywords` | `varchar(500)`  | NULL                        | SEO용 키워드. |

---

### 5.4 `product_inventories` 테이블

상품의 **재고 상태**를 관리합니다.

#### 주요 컬럼

| 컬럼             | 타입        | 제약                        | 설명 |
|-----------------|-------------|-----------------------------|------|
| `product_id`    | `bigint`    | PK, FK → `products.id`      | 상품 ID. |
| `stock_quantity`| `int`       | NOT NULL, DEFAULT `0`       | 현재 재고 수량. |
| `safe_stock_level`| `int`     | NOT NULL, DEFAULT `10`      | 안전 재고 기준. 이 값보다 낮으면 품절 위험. |
| `updated_at`    | `timestamp` | NOT NULL, DEFAULT now       | 마지막 재고 갱신 시각. |

---

### 5.5 `product_images` 테이블

상품 이미지 목록을 관리합니다.

- 1 상품 : N 이미지
- `display_order` 로 정렬해 대표 이미지/노출 순서를 제어합니다.

#### 주요 컬럼

| 컬럼          | 타입        | 제약                           | 설명 |
|--------------|-------------|--------------------------------|------|
| `id`         | `bigint`    | PK, auto increment             | 이미지 레코드 ID. |
| `product_id` | `bigint`    | NOT NULL, FK → `products.id`   | 상품 ID. |
| `image_url`  | `text`      | NOT NULL                       | 이미지 URL. |
| `display_order`| `int`     | NOT NULL, DEFAULT `0`          | 표시 순서. 가장 작은 값이 대표. |
| `created_at` | `timestamp` | NOT NULL, DEFAULT now          | 생성 시각. |

---

### 5.6 `product_price_histories` 테이블 (v2.1 구현 – 스냅샷 방식)

상품의 **가격 스냅샷 이력**을 관리합니다.

- 데이터 파이프라인 / 초기 임포트에서 **기존 상품의 가격이 변경될 때마다, 변경 후 가격을 한 줄씩 추가**합니다.
- 같은 상품에 대해 10000 → 9000 → 11000원이 들어오면, 이 테이블에는 시간 순으로 3개의 레코드가 쌓입니다.
- old/new/변동률을 컬럼으로 직접 들고 있는 것이 아니라, 각 시점의 가격 스냅샷을 여러 건 저장하는 구조입니다.

#### 주요 컬럼

| 컬럼           | 타입        | 제약                          | 설명 |
|----------------|-------------|-------------------------------|------|
| `id`           | `bigint`    | PK, auto increment            | 이력 레코드 ID. |
| `product_id`   | `bigint`    | NOT NULL, FK → `products.id`  | 상품 ID. |
| `price`        | `int`       | NOT NULL                      | 해당 시점 판매가. |
| `original_price` | `int`     | NULL                          | 해당 시점 기준가/정가. 없으면 `NULL`. |
| `recorded_at`  | `timestamp` | NOT NULL, DEFAULT now         | 가격 스냅샷 기록 시각. |
| `source`       | `varchar(50)` | NULL                        | 이력이 생성된 출처 (`import`, `crawl`, `manual` 등). |

#### 인덱스

- `product_id`: 상품별 가격 이력 조회.
- `(product_id, recorded_at)`: 상품별 최신/전체 가격 이력 조회.

#### 사용 시나리오

1. 데이터 파이프라인이 크롤링 데이터를 처리할 때
   - `source_url` 기준으로 기존 상품을 찾고, **이전 `products.price`와 새 가격이 다르면** 이 테이블에 한 줄 추가합니다.
   - 동시에 `products.price`, `products.original_price`를 새 값으로 업데이트합니다.
2. 초기 CSV import 시
   - 신규 상품을 생성하면서, 해당 시점 가격을 스냅샷으로 1건 적재합니다.
3. 프론트엔드 상품 상세에서
   - `product_price_histories`를 `product_id`와 `recorded_at` 순으로 조회해 가격 변동 그래프/리스트를 표시합니다.


---

## 6. Group 4 – Orders & Payments

**도메인 개요:**
주문 헤더/품목/배송/결제 정보를 정규화해서 관리합니다.  
금액, 배송지, 배송비, 결제는 각각 별도 테이블로 나눠 복잡한 주문 시나리오(부분배송/부분취소/여러 결제수단)를 표현할 수 있게 설계합니다.

### 6.1 `orders` 테이블

주문 전체(헤더)의 **식별자와 상태**를 관리합니다.

#### 주요 컬럼

| 컬럼          | 타입           | 제약                           | 설명 |
|--------------|----------------|--------------------------------|------|
| `id`         | `bigint`       | PK, auto increment             | 주문 ID. |
| `order_no`   | `varchar(50)`  | NOT NULL, UNIQUE               | 외부 노출용 주문번호. |
| `user_id`    | `bigint`       | NOT NULL, FK → `users.id`      | 주문자 ID. |
| `status`     | `order_status` | NOT NULL, DEFAULT `'pending'`  | 주문 상태. |
| `cancelled_at`| `timestamp`   | NULL                           | 전체 주문 취소 시각. |
| `cancel_reason`| `text`       | NULL                           | 취소 사유. |
| `refunded_at`| `timestamp`    | NULL                           | 전체 주문 환불 완료 시각. |
| `created_at` | `timestamp`    | NOT NULL, DEFAULT now          | 주문 생성 시각. |
| `updated_at` | `timestamp`    | NOT NULL, DEFAULT now          | 주문 상태/정보 변경 시각. |

---

### 6.2 `order_items` 테이블

주문 시점의 **상품명/단가/수량/할인** 정보를 스냅샷으로 저장합니다.

- 이후 상품 정보가 변경되더라도 주문 기록은 변하지 않도록 설계.

#### 주요 컬럼

| 컬럼                    | 타입               | 제약                          | 설명 |
|------------------------|--------------------|-------------------------------|------|
| `id`                   | `bigint`           | PK, auto increment            | 주문 품목 ID. |
| `order_id`             | `bigint`           | NOT NULL, FK → `orders.id`    | 상위 주문 ID. |
| `product_id`           | `bigint`           | NOT NULL, FK → `products.id`  | 상품 ID(참조용). |
| `product_name_snapshot`| `varchar(500)`     | NOT NULL                      | 주문 시점의 상품명. |
| `unit_price_snapshot`  | `int`              | NOT NULL                      | 주문 시점의 단가. |
| `quantity`             | `int`              | NOT NULL                      | 수량. |
| `discount_amount`      | `int`              | NOT NULL, DEFAULT `0`         | 해당 품목에 적용된 할인액. |
| `status`               | `order_item_status`| NOT NULL, DEFAULT `'pending'` | 품목 상태. |
| `created_at`           | `timestamp`        | NOT NULL, DEFAULT now         | 생성 시각. |

---

### 6.3 `shipments` 테이블

배송 단위를 관리합니다. 한 주문에 여러 번의 배송(부분배송)이 있을 수 있습니다.

#### 주요 컬럼

| 컬럼            | 타입           | 제약                        | 설명 |
|----------------|----------------|-----------------------------|------|
| `id`           | `bigint`       | PK, auto increment          | 배송 ID. |
| `order_id`     | `bigint`       | NOT NULL, FK → `orders.id`  | 주문 ID. |
| `recipient_name`| `varchar(100)`| NOT NULL                    | 수령인 이름. |
| `recipient_phone`|`varchar(20)` | NOT NULL                    | 수령인 연락처. |
| `address_full` | `varchar(500)` | NOT NULL                    | 배송지 전체 주소 문자열. |
| `shipping_memo`| `text`         | NULL                        | 배송 요청사항. |
| `courier`      | `varchar(50)`  | NULL                        | 택배사 이름. |
| `tracking_no`  | `varchar(100)` | NULL                        | 운송장 번호. |
| `shipping_fee` | `int`          | NOT NULL, DEFAULT `0`       | 배송비. |
| `shipped_at`   | `timestamp`    | NULL                        | 발송 시각. |
| `delivered_at` | `timestamp`    | NULL                        | 배송 완료 시각. |
| `created_at`   | `timestamp`    | NOT NULL, DEFAULT now       | 생성 시각. |
| `updated_at`   | `timestamp`    | NOT NULL, DEFAULT now       | 수정 시각. |

---

### 6.4 `payments` 테이블

주문에 대한 **결제 트랜잭션**을 기록합니다.

- 한 주문에 여러 결제 시도/수단이 있을 수 있습니다.

#### 주요 컬럼

| 컬럼            | 타입                  | 제약                         | 설명 |
|----------------|-----------------------|------------------------------|------|
| `id`           | `bigint`              | PK, auto increment           | 결제 ID. |
| `order_id`     | `bigint`              | NOT NULL, FK → `orders.id`   | 주문 ID. |
| `method_type`  | `payment_method_type` | NOT NULL, DEFAULT `'card'`   | 결제 수단 유형. |
| `amount`       | `int`                 | NOT NULL                     | 결제 금액. |
| `status`       | `payment_status`      | NOT NULL, DEFAULT `'pending'`| 결제 상태. |
| `is_simulation`| `boolean`             | NOT NULL, DEFAULT `true`     | 모의 결제 여부. |
| `simulation_note`| `text`              | NULL                         | 모의 결제 설명/메모. |
| `pg_provider`  | `varchar(50)`         | NULL                         | PG사 이름. |
| `pg_tid`       | `varchar(100)`        | NULL, UNIQUE                 | PG 거래 ID(TID). |
| `created_at`   | `timestamp`           | NOT NULL, DEFAULT now        | 생성 시각. |
| `processed_at` | `timestamp`           | NULL                         | 결제 처리 완료 시각. |
| `failure_reason`| `text`               | NULL                         | 실패 사유(로그용). |

---

## 7. Group 5 – Interactions (Cart, Wishlist, Follow)

**도메인 개요:**  
사용자의 장바구니, 찜, 판매자 팔로우 등 **상호작용 기록**을 관리합니다.

### 7.1 `carts` 테이블

사용자의 **장바구니 품목**을 관리합니다.

- `(user_id, product_id)` UNIQUE → 한 사용자가 같은 상품을 중복 담지 않도록 제한.

#### 주요 컬럼

| 컬럼        | 타입        | 제약                                 | 설명 |
|------------|-------------|--------------------------------------|------|
| `id`       | `bigint`    | PK, auto increment                   | 장바구니 항목 ID. |
| `user_id`  | `bigint`    | NOT NULL, FK → `users.id`            | 사용자 ID. |
| `product_id`| `bigint`   | NOT NULL, FK → `products.id`         | 상품 ID. |
| `quantity` | `int`       | NOT NULL, DEFAULT `1`                | 수량. |
| `created_at`| `timestamp`| NOT NULL, DEFAULT now                | 생성 시각. |
| `updated_at`| `timestamp`| NOT NULL, DEFAULT now                | 수정 시각. |

---

### 7.2 `wishlists` 테이블

사용자의 **찜(위시리스트)** 정보를 관리합니다.

- `(user_id, product_id)` UNIQUE → 동일 상품 중복 찜 방지.

#### 주요 컬럼

| 컬럼        | 타입        | 제약                          | 설명 |
|------------|-------------|-------------------------------|------|
| `id`       | `bigint`    | PK, auto increment            | 찜 레코드 ID. |
| `user_id`  | `bigint`    | NOT NULL, FK → `users.id`     | 사용자 ID. |
| `product_id`| `bigint`   | NOT NULL, FK → `products.id`  | 상품 ID. |
| `created_at`| `timestamp`| NOT NULL, DEFAULT now         | 생성 시각. |

---

### 7.3 `seller_follows` 테이블

소비자(user)가 셀러(seller)를 **팔로우**하는 관계를 관리합니다.

- 유저가 다른 유저를 팔로우하는 소셜 그래프는 포함하지 않습니다.

#### 주요 컬럼

| 컬럼       | 타입        | 제약                               | 설명 |
|-----------|-------------|------------------------------------|------|
| `id`      | `bigint`    | PK, auto increment                 | 팔로우 ID. |
| `user_id` | `bigint`    | NOT NULL, FK → `users.id`          | 팔로우한 사용자. |
| `seller_id`| `bigint`   | NOT NULL, FK → `sellers.id`        | 팔로우 대상 셀러. |
| `created_at`|`timestamp`| NOT NULL, DEFAULT now              | 팔로우 시각. |

---

## 8. Group 6 – Reviews

**도메인 개요:**  
상품 리뷰와 사진 리뷰를 관리합니다. 실제 구매 기반 리뷰 여부, 사진 리뷰 여부 등을 구분해 분석과 품질 지표에 활용합니다.

### 8.1 `reviews` 테이블

상품에 대한 **텍스트 리뷰**를 관리합니다.

#### 주요 컬럼

| 컬럼          | 타입           | 제약                            | 설명 |
|--------------|----------------|---------------------------------|------|
| `id`         | `bigint`       | PK, auto increment              | 리뷰 ID. |
| `product_id` | `bigint`       | NOT NULL, FK → `products.id`    | 상품 ID. |
| `user_id`    | `bigint`       | NOT NULL, FK → `users.id`       | 작성자 ID. |
| `order_item_id`| `bigint`     | NULL, FK → `order_items.id`     | 구매 기반 리뷰 여부 판단용 연결. |
| `rating`     | `smallint`     | NOT NULL                        | 평점(1~5). |
| `content`    | `text`         | NOT NULL                        | 리뷰 본문. |
| `has_photos` | `boolean`      | NOT NULL, DEFAULT `false`       | 사진 리뷰 여부. |
| `status`     | `varchar(20)`  | NOT NULL, DEFAULT `'visible'`   | 리뷰 상태(visible/hidden/reported/deleted 등). |
| `created_at` | `timestamp`    | NOT NULL, DEFAULT now           | 작성 시각. |
| `updated_at` | `timestamp`    | NOT NULL, DEFAULT now           | 수정 시각. |

---

### 8.2 `review_images` 테이블

사진 리뷰용 **이미지 목록**을 관리합니다.

#### 주요 컬럼

| 컬럼          | 타입        | 제약                           | 설명 |
|--------------|-------------|--------------------------------|------|
| `id`         | `bigint`    | PK, auto increment             | 리뷰 이미지 ID. |
| `review_id`  | `bigint`    | NOT NULL, FK → `reviews.id`    | 리뷰 ID. |
| `image_url`  | `text`      | NOT NULL                       | 이미지 URL. |
| `display_order`| `int`     | NOT NULL, DEFAULT `0`          | 표시 순서. |
| `created_at` | `timestamp` | NOT NULL, DEFAULT now          | 생성 시각. |

---

## 9. Group 7 – Recommendation & Analytics

**도메인 개요:**  
추천/정렬/대시보드에 사용할 **집계/품질 피처**를 저장하는 테이블입니다.  
로그/이벤트 테이블에서 배치 또는 스트림 처리로 집계한 결과를 저장합니다.

### 9.1 `product_stats` 테이블

상품별 **집계/품질 피처**를 저장합니다.

- 카운트 컬럼은 장기간 누적 및 대용량 트래픽을 고려해 `bigint` 사용.

#### 주요 컬럼

| 컬럼                    | 타입             | 제약                        | 설명 |
|------------------------|------------------|-----------------------------|------|
| `product_id`           | `bigint`         | PK, FK → `products.id`      | 상품 ID. |
| `view_count`           | `bigint`         | NOT NULL, DEFAULT `0`       | 상세 페이지 조회 수. |
| `recommend_clicked_count`| `bigint`       | NOT NULL, DEFAULT `0`       | 추천 리스트/배너 등에서의 카드 클릭 수. |
| `cart_event_count`     | `bigint`         | NOT NULL, DEFAULT `0`       | 장바구니 담기 이벤트 수. |
| `order_event_count`    | `bigint`         | NOT NULL, DEFAULT `0`       | 주문(해당 상품 포함) 발생 횟수. |
| `wishlist_count`       | `bigint`         | NOT NULL, DEFAULT `0`       | 찜 수. |
| `review_count`         | `bigint`         | NOT NULL, DEFAULT `0`       | 리뷰 개수. |
| `average_rating`       | `decimal(3,2)`   | NOT NULL, DEFAULT `0.00`    | 평균 평점(1~5). |
| `photo_review_count`   | `bigint`         | NOT NULL, DEFAULT `0`       | 사진 리뷰 개수. |
| `sentiment_score_avg`  | `decimal(5,2)`   | NOT NULL, DEFAULT `0.00`    | 리뷰 감성 점수 평균(0~1 등). |
| `first_review_at`      | `timestamp`      | NULL                        | 첫 리뷰 작성 시각. |
| `quality_score`        | `decimal(5,2)`   | NOT NULL, DEFAULT `50.00`   | 종합 품질 점수. |
| `image_quality_score`  | `decimal(5,2)`   | NOT NULL, DEFAULT `50.00`   | 이미지 품질 점수. |
| `content_quality_score`| `decimal(5,2)`   | NOT NULL, DEFAULT `50.00`   | 콘텐츠(설명/리뷰 등) 품질 점수. |
| `last_updated`         | `timestamp`      | NOT NULL, DEFAULT now       | 마지막 집계 갱신 시각. |

---

### 9.2 `user_product_stats` 테이블

유저 × 상품별 **개인화 집계 피처**를 저장합니다.

- 추천, 리마인드, 최근 본 상품 정렬 등에 사용.

#### 주요 컬럼

| 컬럼               | 타입        | 제약                           | 설명 |
|-------------------|-------------|--------------------------------|------|
| `id`              | `bigint`    | PK, auto increment             | 레코드 ID. |
| `user_id`         | `bigint`    | NOT NULL, FK → `users.id`      | 사용자 ID. |
| `product_id`      | `bigint`    | NOT NULL, FK → `products.id`   | 상품 ID. |
| `view_count`      | `bigint`    | NOT NULL, DEFAULT `0`          | 해당 유저가 이 상품을 본 횟수. |
| `cart_event_count`| `bigint`    | NOT NULL, DEFAULT `0`          | 장바구니에 담은 횟수. |
| `order_event_count`| `bigint`   | NOT NULL, DEFAULT `0`          | 구매한 횟수. |
| `last_interacted_at`| `timestamp`| NOT NULL, DEFAULT now         | 마지막 상호작용(조회/담기/구매) 시각. |

---

## 10. 정리 및 활용 가이드

- 이 스키마는 **정규화된 코어 도메인 테이블**과 **집계/품질 피처 테이블**을 분리해,
  - 온라인 트랜잭션(주문/재고/장바구니)에 대한 일관성,
  - 추천/분석/대시보드용 읽기 성능과 유연성을 동시에 확보하는 것이 목표입니다.
- 실제 구현 시에는
  - Django 모델/시리얼라이저/서비스 레이어에서 이 문서를 참고해 비즈니스 규칙을 맞추고,
  - 배치/스트림 잡에서 `product_stats`, `user_product_stats`를 주기적으로 갱신하는 구조를 권장합니다.

