# SelF 플랫폼 DTO (Data Transfer Object) 명세서

> **문서 버전**: v2.0.0
> **작성일**: 2025년 12월 01일
> **프로젝트명**: SelF (Special Selection All For You)

---

## 목차

1. [개요](#1-개요)
2. [공통 규칙](#2-공통-규칙)
3. [인증 (Authentication)](#3-인증-authentication)
4. [사용자 (User)](#4-사용자-user)
5. [상품 (Product)](#5-상품-product)
6. [판매자 상품 (Seller Product)](#6-판매자-상품-seller-product)
7. [장바구니 (Cart)](#7-장바구니-cart)
8. [찜 목록 (Wishlist)](#8-찜-목록-wishlist)
9. [주문 (Order)](#9-주문-order)
10. [판매자 (Seller)](#10-판매자-seller)
11. [리뷰 (Review)](#11-리뷰-review)
12. [추천 (Recommendation)](#12-추천-recommendation)
13. [공통 응답 형식](#13-공통-응답-형식)

---

## 1. 개요

이 문서는 프론트엔드와 백엔드 간의 데이터 통신에 사용되는 DTO(Data Transfer Object)를 정의합니다.

### 1.1 용어 정의
| 용어 | 설명 |
|------|------|
| Request DTO | 클라이언트 → 서버로 전송하는 데이터 구조 |
| Response DTO | 서버 → 클라이언트로 응답하는 데이터 구조 |
| Required | 필수 필드 (누락 시 400 에러) |
| Optional | 선택 필드 (기본값 적용) |
| Read-Only | 서버에서만 설정, 클라이언트 수정 불가 |

### 1.2 타입 표기법
| 표기 | 설명 | 예시 |
|------|------|------|
| `string` | 문자열 | `"hello"` |
| `number` | 정수 | `123` |
| `decimal` | 소수점 숫자 | `99.99` |
| `boolean` | 불리언 | `true`, `false` |
| `datetime` | ISO 8601 날짜시간 | `"2025-01-21T10:30:00Z"` |
| `date` | ISO 8601 날짜 | `"2025-01-21"` |
| `time` | 시간 | `"09:00:00"` |
| `array<T>` | T 타입의 배열 | `[1, 2, 3]` |
| `T \| null` | T 또는 null | `"value"` or `null` |

---

## 2. 공통 규칙

### 2.1 날짜/시간 형식
모든 날짜/시간은 ISO 8601 형식을 사용합니다.
```
datetime: "2025-01-21T10:30:00Z"
date: "2025-01-21"
time: "09:00:00"
```

### 2.2 페이지네이션 응답
```typescript
interface PaginatedResponse<T> {
  count: number;           // 전체 항목 수
  next: string | null;     // 다음 페이지 URL
  previous: string | null; // 이전 페이지 URL
  results: T[];            // 데이터 배열
}
```

### 2.3 에러 응답
```typescript
interface ErrorResponse {
  detail: string;          // 에러 메시지
  code?: string;           // 에러 코드 (선택)
}
```

### 2.4 HTTP 상태 코드
| 코드 | 설명 |
|------|------|
| 200 | OK - 조회/수정 성공 |
| 201 | Created - 생성 성공 |
| 204 | No Content - 삭제 성공 |
| 400 | Bad Request - 잘못된 요청 |
| 401 | Unauthorized - 인증 필요 |
| 403 | Forbidden - 권한 없음 |
| 404 | Not Found - 리소스 없음 |

---

## 3. 인증 (Authentication)

---

### ▼ [POST] 회원가입 요청

| 항목 | 내용 |
|------|------|
| **Description** | 이메일 회원가입 요청 |
| **URL** | `https://sellfresh.shop/api/auth/register/` |
| **Auth Required** | X |

| Parameter | Type | Required | Place | Description |
|-----------|------|----------|-------|-------------|
| `email` | string | O | body | 이메일 (이메일 형식) |
| `password` | string | O | body | 비밀번호 (최소 8자) |
| `username` | string | X | body | 사용자명 |

#### ✅ Response 201
```typescript
interface RegisterResponse {
  email: string;
  detail: string;          // "인증 메일을 발송했습니다."
  expires_at: datetime;    // 인증 코드 만료 시간
  verification_code?: string; // 개발 환경에서만 반환
}
```

#### ✅ Response 400
```typescript
{
  email?: string[];        // ["이 필드는 필수입니다."]
  password?: string[];     // ["비밀번호는 최소 8자 이상이어야 합니다."]
}
```

---

### ▼ [POST] 이메일 인증

| 항목 | 내용 |
|------|------|
| **Description** | 이메일 인증 코드 확인 |
| **URL** | `https://sellfresh.shop/api/auth/register/verify/` |
| **Auth Required** | X |

| Parameter | Type | Required | Place | Description |
|-----------|------|----------|-------|-------------|
| `email` | string | O | body | 이메일 |
| `code` | string | O | body | 인증 코드 |

#### ✅ Response 200
```typescript
interface EmailVerifyResponse {
  detail: string;          // "이메일 인증이 완료되었습니다."
}
```

#### ✅ Response 400
```typescript
{
  detail: string;          // "인증 코드가 일치하지 않습니다." 또는 "인증 코드가 만료되었습니다."
  code: string;            // "invalid_verification_code" 또는 "verification_expired"
}
```

---

### ▼ [POST] 로그인

| 항목 | 내용 |
|------|------|
| **Description** | 이메일/비밀번호 로그인 |
| **URL** | `https://sellfresh.shop/api/auth/login/` |
| **Auth Required** | X |

| Parameter | Type | Required | Place | Description |
|-----------|------|----------|-------|-------------|
| `email` | string | O | body | 이메일 |
| `password` | string | O | body | 비밀번호 |

#### ✅ Response 200
```typescript
interface LoginResponse {
  access: string;          // JWT Access Token
  refresh: string;         // JWT Refresh Token
  user: UserDTO;           // 사용자 정보
}
```

#### ✅ Response 401
```typescript
{
  detail: string;          // "이메일 또는 비밀번호가 일치하지 않습니다."
  code: string;            // "invalid_credentials"
}
```

---

### ▼ [POST] 로그아웃

| 항목 | 내용 |
|------|------|
| **Description** | 현재 세션 종료 |
| **URL** | `https://sellfresh.shop/api/auth/logout/` |
| **Auth Required** | O |

| Parameter | Type | Required | Place | Description |
|-----------|------|----------|-------|-------------|
| `refresh` | string | O | body | Refresh Token |

#### ✅ Response 205
```typescript
interface LogoutResponse {
  detail: string;          // "로그아웃되었습니다."
}
```

#### ✅ Response 401
```typescript
{
  detail: string;          // "자격 인증데이터가 제공되지 않았습니다."
}
```

---

### ▼ [POST] 토큰 갱신

| 항목 | 내용 |
|------|------|
| **Description** | JWT 토큰 갱신 |
| **URL** | `https://sellfresh.shop/api/auth/token/refresh/` |
| **Auth Required** | X |

| Parameter | Type | Required | Place | Description |
|-----------|------|----------|-------|-------------|
| `refresh` | string | O | body | Refresh Token |

#### ✅ Response 200
```typescript
interface TokenRefreshResponse {
  access: string;          // 새 Access Token
  refresh: string;         // 새 Refresh Token
}
```

#### ✅ Response 401
```typescript
{
  detail: string;          // "토큰이 만료되었습니다." 또는 "유효하지 않은 토큰입니다."
  code: string;            // "token_not_valid"
}
```

---

### ▼ [GET] 현재 사용자 정보 조회

| 항목 | 내용 |
|------|------|
| **Description** | 현재 로그인한 사용자 정보 조회 |
| **URL** | `https://sellfresh.shop/api/auth/user/` |
| **Auth Required** | O |

| Parameter | Type | Required | Place | Description |
|-----------|------|----------|-------|-------------|
| - | - | - | - | - |

#### ✅ Response 200
```typescript
interface UserDTO {
  id: number;                      // PK
  email: string;                   // 이메일
  username: string | null;         // 사용자명
  first_name: string;              // 이름
  last_name: string;               // 성
  profile_image_url: string | null; // 프로필 이미지 URL
  provider: string;                // 'email' | 'google' | 'kakao'
  role: string;                    // 'guest' | 'user' | 'seller' | 'admin'
  timezone: string | null;         // 타임존 (기본: 'Asia/Seoul')
}
```

#### ✅ Response 401
```typescript
{
  detail: string;          // "자격 인증데이터가 제공되지 않았습니다."
}
```

---

### ▼ [POST] 비밀번호 변경

| 항목 | 내용 |
|------|------|
| **Description** | 로그인한 사용자 비밀번호 변경 |
| **URL** | `https://sellfresh.shop/api/auth/password/change/` |
| **Auth Required** | O |

| Parameter | Type | Required | Place | Description |
|-----------|------|----------|-------|-------------|
| `old_password` | string | O | body | 현재 비밀번호 |
| `new_password` | string | O | body | 새 비밀번호 (최소 8자) |

#### ✅ Response 200
```typescript
interface PasswordChangeResponse {
  detail: string;          // "비밀번호가 변경되었습니다."
  revoked_refresh: number; // 무효화된 토큰 수
}
```

#### ✅ Response 400
```typescript
{
  old_password?: string[]; // ["현재 비밀번호가 일치하지 않습니다."]
  new_password?: string[]; // ["비밀번호는 최소 8자 이상이어야 합니다."]
}
```

---

### ▼ [POST] 비밀번호 재설정 요청

| 항목 | 내용 |
|------|------|
| **Description** | 비밀번호 재설정 이메일 발송 |
| **URL** | `https://sellfresh.shop/api/auth/password/reset/` |
| **Auth Required** | X |

| Parameter | Type | Required | Place | Description |
|-----------|------|----------|-------|-------------|
| `email` | string | O | body | 이메일 |

#### ✅ Response 200
```typescript
interface PasswordResetResponse {
  detail: string;          // "비밀번호 재설정 안내를 발송했습니다."
  // 개발 환경에서만 반환
  uid?: string;
  token?: string;
  reset_url?: string;
}
```

#### ✅ Response 404
```typescript
{}
```

---

### ▼ [POST] 비밀번호 재설정 확인

| 항목 | 내용 |
|------|------|
| **Description** | 비밀번호 재설정 완료 |
| **URL** | `https://sellfresh.shop/api/auth/password/reset/confirm/` |
| **Auth Required** | X |

| Parameter | Type | Required | Place | Description |
|-----------|------|----------|-------|-------------|
| `uid` | string | O | body | 사용자 ID (base64) |
| `token` | string | O | body | 재설정 토큰 |
| `new_password` | string | O | body | 새 비밀번호 (최소 8자) |

#### ✅ Response 200
```typescript
interface PasswordResetConfirmResponse {
  detail: string;          // "비밀번호가 재설정되었습니다."
  revoked_refresh: number; // 무효화된 토큰 수
}
```

#### ✅ Response 400
```typescript
{
  detail: string;          // "유효하지 않은 토큰입니다."
  code: string;            // "invalid_token"
}
```

---

### ▼ [GET] Google OAuth 콜백

| 항목 | 내용 |
|------|------|
| **Description** | Google OAuth 인증 콜백 |
| **URL** | `https://sellfresh.shop/api/auth/google/callback/` |
| **Auth Required** | X |

| Parameter | Type | Required | Place | Description |
|-----------|------|----------|-------|-------------|
| `code` | string | O | query | OAuth 인가 코드 |
| `state` | string | X | query | CSRF 토큰 |

#### ✅ Response 200 (API 모드)
```typescript
interface OAuthCallbackResponse {
  access: string;          // JWT Access Token
  refresh: string;         // JWT Refresh Token
  user: UserDTO;           // 사용자 정보
}
```

#### ✅ Response 302 (Web 모드)
```
리다이렉트 URL: {next_url}?access_token={access}&refresh_token={refresh}&user={user_json}
```

---

### ▼ [GET] Kakao OAuth 콜백

| 항목 | 내용 |
|------|------|
| **Description** | Kakao OAuth 인증 콜백 |
| **URL** | `https://sellfresh.shop/api/auth/kakao/callback/` |
| **Auth Required** | X |

| Parameter | Type | Required | Place | Description |
|-----------|------|----------|-------|-------------|
| `code` | string | O | query | OAuth 인가 코드 |
| `state` | string | X | query | CSRF 토큰 |

#### ✅ Response 200 (API 모드)
```typescript
interface OAuthCallbackResponse {
  access: string;          // JWT Access Token
  refresh: string;         // JWT Refresh Token
  user: UserDTO;           // 사용자 정보
}
```

#### ✅ Response 302 (Web 모드)
```
리다이렉트 URL: {next_url}?access_token={access}&refresh_token={refresh}&user={user_json}
```

---

## 4. 사용자 (User)

---

### ▼ [GET] 프로필 조회

| 항목 | 내용 |
|------|------|
| **Description** | 현재 사용자 프로필 조회 |
| **URL** | `https://sellfresh.shop/api/users/me/profile/` |
| **Auth Required** | O |

| Parameter | Type | Required | Place | Description |
|-----------|------|----------|-------|-------------|
| - | - | - | - | - |

#### ✅ Response 200
```typescript
interface UserProfileDTO {
  id: number;                      // PK
  email: string;                   // 이메일
  username: string | null;         // 사용자명
  first_name: string;              // 이름
  last_name: string;               // 성
  profile_image_url: string | null; // 프로필 이미지 URL
  phone: string | null;            // 연락처
  birth_date: date | null;         // 생년월일
  gender: string | null;           // 'M' | 'F' | null
  timezone: string | null;         // 타임존
  language: string;                // 언어 (기본: 'ko')
  push_notifications: boolean;     // 푸시 알림 설정
  email_notifications: boolean;    // 이메일 알림 설정
  marketing_agreed: boolean;       // 마케팅 동의
  provider: string;                // 'email' | 'google' | 'kakao'
  role: string;                    // 'guest' | 'user' | 'seller' | 'admin'
}
```

#### ✅ Response 401
```typescript
{
  detail: string;          // "자격 인증데이터가 제공되지 않았습니다."
}
```

---

### ▼ [PATCH] 프로필 수정

| 항목 | 내용 |
|------|------|
| **Description** | 사용자 프로필 수정 (부분 수정 가능) |
| **URL** | `https://sellfresh.shop/api/users/me/profile/` |
| **Auth Required** | O |

| Parameter | Type | Required | Place | Description |
|-----------|------|----------|-------|-------------|
| `first_name` | string | X | body | 이름 |
| `last_name` | string | X | body | 성 |
| `profile_image_url` | string | X | body | 프로필 이미지 URL |
| `phone` | string | X | body | 연락처 |
| `birth_date` | date | X | body | 생년월일 |
| `gender` | string | X | body | 성별 ('M' \| 'F') |
| `timezone` | string | X | body | 타임존 |
| `language` | string | X | body | 언어 |
| `push_notifications` | boolean | X | body | 푸시 알림 설정 |
| `email_notifications` | boolean | X | body | 이메일 알림 설정 |
| `marketing_agreed` | boolean | X | body | 마케팅 동의 |

#### ✅ Response 200
```typescript
// UserProfileDTO 참조
```

#### ✅ Response 400
```typescript
{
  phone?: string[];        // ["이 연락처는 이미 사용 중입니다."]
}
```

---

### ▼ [GET] 배송지 목록 조회

| 항목 | 내용 |
|------|------|
| **Description** | 사용자 배송지 목록 조회 |
| **URL** | `https://sellfresh.shop/api/users/me/addresses/` |
| **Auth Required** | O |

| Parameter | Type | Required | Place | Description |
|-----------|------|----------|-------|-------------|
| - | - | - | - | - |

#### ✅ Response 200
```typescript
interface AddressListResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: UserAddressDTO[];
}

interface UserAddressDTO {
  id: number;                      // PK
  name: string;                    // 배송지 이름 (예: '집', '회사')
  recipient_name: string;          // 수령인
  recipient_phone: string;         // 수령인 연락처
  postal_code: string;             // 우편번호
  address_line1: string;           // 주소
  address_line2: string | null;    // 상세주소
  city: string;                    // 시/도
  state: string;                   // 구/군
  country: string;                 // 국가 (기본: 'KR')
  latitude: decimal | null;        // 위도
  longitude: decimal | null;       // 경도
  is_default: boolean;             // 기본 배송지 여부
  created_at: datetime;            // 생성일
  updated_at: datetime;            // 수정일
}
```

#### ✅ Response 401
```typescript
{
  detail: string;          // "자격 인증데이터가 제공되지 않았습니다."
}
```

---

### ▼ [POST] 배송지 추가

| 항목 | 내용 |
|------|------|
| **Description** | 새 배송지 추가 |
| **URL** | `https://sellfresh.shop/api/users/me/addresses/` |
| **Auth Required** | O |

| Parameter | Type | Required | Place | Description |
|-----------|------|----------|-------|-------------|
| `name` | string | O | body | 배송지 이름 |
| `recipient_name` | string | O | body | 수령인 이름 |
| `recipient_phone` | string | O | body | 수령인 연락처 |
| `postal_code` | string | O | body | 우편번호 |
| `address_line1` | string | O | body | 주소 |
| `address_line2` | string | X | body | 상세주소 |
| `city` | string | O | body | 시/도 |
| `state` | string | O | body | 구/군 |
| `country` | string | X | body | 국가 (기본: 'KR') |
| `latitude` | decimal | X | body | 위도 |
| `longitude` | decimal | X | body | 경도 |
| `is_default` | boolean | X | body | 기본 배송지 여부 (기본: false) |

#### ✅ Response 201
```typescript
// UserAddressDTO 참조
```

#### ✅ Response 400
```typescript
{
  name?: string[];         // ["이 필드는 필수입니다."]
  recipient_name?: string[]; // ["이 필드는 필수입니다."]
}
```

---

### ▼ [PATCH] 배송지 수정

| 항목 | 내용 |
|------|------|
| **Description** | 배송지 정보 수정 (부분 수정 가능) |
| **URL** | `https://sellfresh.shop/api/users/me/addresses/{id}/` |
| **Auth Required** | O |

| Parameter | Type | Required | Place | Description |
|-----------|------|----------|-------|-------------|
| `id` | number | O | url | 배송지 ID |
| `name` | string | X | body | 배송지 이름 |
| `recipient_name` | string | X | body | 수령인 이름 |
| `recipient_phone` | string | X | body | 수령인 연락처 |
| `postal_code` | string | X | body | 우편번호 |
| `address_line1` | string | X | body | 주소 |
| `address_line2` | string | X | body | 상세주소 |
| `city` | string | X | body | 시/도 |
| `state` | string | X | body | 구/군 |
| `is_default` | boolean | X | body | 기본 배송지 여부 |

#### ✅ Response 200
```typescript
// UserAddressDTO 참조
```

#### ✅ Response 404
```typescript
{
  detail: string;          // "찾을 수 없습니다."
}
```

---

### ▼ [DELETE] 배송지 삭제

| 항목 | 내용 |
|------|------|
| **Description** | 배송지 삭제 |
| **URL** | `https://sellfresh.shop/api/users/me/addresses/{id}/` |
| **Auth Required** | O |

| Parameter | Type | Required | Place | Description |
|-----------|------|----------|-------|-------------|
| `id` | number | O | url | 배송지 ID |

#### ✅ Response 204
```
No Content
```

#### ✅ Response 404
```typescript
{
  detail: string;          // "찾을 수 없습니다."
}
```

---

### ▼ [POST] 기본 배송지 설정

| 항목 | 내용 |
|------|------|
| **Description** | 기본 배송지로 설정 |
| **URL** | `https://sellfresh.shop/api/users/me/addresses/{id}/set-default/` |
| **Auth Required** | O |

| Parameter | Type | Required | Place | Description |
|-----------|------|----------|-------|-------------|
| `id` | number | O | url | 배송지 ID |

#### ✅ Response 200
```typescript
// UserAddressDTO 참조 (is_default: true)
```

#### ✅ Response 404
```typescript
{
  detail: string;          // "찾을 수 없습니다."
}
```

---

## 5. 상품 (Product)

---

### ▼ [GET] 카테고리 목록 조회

| 항목 | 내용 |
|------|------|
| **Description** | 상품 카테고리 목록 조회 |
| **URL** | `https://sellfresh.shop/api/categories/` |
| **Auth Required** | X |

| Parameter | Type | Required | Place | Description |
|-----------|------|----------|-------|-------------|
| - | - | - | - | - |

#### ✅ Response 200
```typescript
interface CategoryListResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: CategoryDTO[];
}

interface CategoryDTO {
  id: number;                      // PK
  name: string;                    // 카테고리명
  slug: string;                    // URL용 슬러그
  parent: number | null;           // 상위 카테고리 ID
  created_at: datetime;            // 생성일
  updated_at: datetime;            // 수정일
}
```

---

### ▼ [GET] 카테고리 상세 조회

| 항목 | 내용 |
|------|------|
| **Description** | 카테고리 상세 정보 조회 |
| **URL** | `https://sellfresh.shop/api/categories/{slug}/` |
| **Auth Required** | X |

| Parameter | Type | Required | Place | Description |
|-----------|------|----------|-------|-------------|
| `slug` | string | O | url | 카테고리 슬러그 |

#### ✅ Response 200
```typescript
// CategoryDTO 참조
```

#### ✅ Response 404
```typescript
{
  detail: string;          // "찾을 수 없습니다."
}
```

---

### ▼ [GET] 상품 목록 조회

| 항목 | 내용 |
|------|------|
| **Description** | 상품 목록 조회 (필터, 검색, 정렬) |
| **URL** | `https://sellfresh.shop/api/products/` |
| **Auth Required** | X |

| Parameter | Type | Required | Place | Description |
|-----------|------|----------|-------|-------------|
| `category` | number | X | query | 카테고리 ID |
| `price__gte` | number | X | query | 최소 가격 |
| `price__lte` | number | X | query | 최대 가격 |
| `is_featured` | boolean | X | query | 추천 상품만 |
| `is_best` | boolean | X | query | 베스트 상품만 |
| `is_new` | boolean | X | query | 신상품만 |
| `is_on_sale` | boolean | X | query | 할인 상품만 |
| `status` | string | X | query | 상태 (active 등) |
| `product_type` | string | X | query | 유형 ('main' \| 'seller') |
| `seller` | number | X | query | 판매자 ID |
| `search` | string | X | query | 검색어 (상품명, 설명) |
| `ordering` | string | X | query | 정렬 기준 |
| `page` | number | X | query | 페이지 번호 (기본: 1) |
| `page_size` | number | X | query | 페이지 크기 (기본: 20) |

**정렬 옵션 (ordering)**
- `price` / `-price`: 가격 오름차순/내림차순
- `created_at` / `-created_at`: 생성일 오름차순/내림차순
- `quality_score` / `-quality_score`: 품질 점수 오름차순/내림차순
- `view_count` / `-view_count`: 조회수 오름차순/내림차순
- `average_rating` / `-average_rating`: 평점 오름차순/내림차순
- `order_count` / `-order_count`: 판매량 오름차순/내림차순

#### ✅ Response 200
```typescript
interface ProductListResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: ProductListDTO[];
}

interface ProductListDTO {
  id: number;                      // PK
  slug: string;                    // URL용 슬러그
  name: string;                    // 상품명
  price: number;                   // 판매가
  original_price: number | null;   // 원가
  discount_rate: number;           // 할인율 (0-100)
  discount: number;                // 할인 금액
  unit: string | null;             // 단위 (예: '1kg', '500g')
  main_image: string | null;       // 메인 이미지 URL
  category: CategoryDTO | null;    // 카테고리 정보
  category_name: string | null;    // 카테고리명
  is_featured: boolean;            // 추천 상품
  is_best: boolean;                // 베스트 상품
  is_new: boolean;                 // 신상품
  is_on_sale: boolean;             // 할인 중
  quality_score: decimal;          // 품질 점수 (0-100)
  view_count: number;              // 조회수
  average_rating: decimal;         // 평균 평점 (0-5)
  review_count: number;            // 리뷰 수
  wishlist_count: number;          // 찜 수
}
```

---

### ▼ [GET] 상품 상세 조회

| 항목 | 내용 |
|------|------|
| **Description** | 상품 상세 정보 조회 |
| **URL** | `https://sellfresh.shop/api/products/{slug}/` |
| **Auth Required** | X |

| Parameter | Type | Required | Place | Description |
|-----------|------|----------|-------|-------------|
| `slug` | string | O | url | 상품 슬러그 또는 ID |

#### ✅ Response 200
```typescript
interface ProductDetailDTO {
  // 기본 정보
  id: number;                      // PK
  product_type: string;            // 'main' | 'seller'
  slug: string;                    // URL용 슬러그
  name: string;                    // 상품명
  short_description: string | null; // 짧은 설명
  description: string | null;      // 상세 설명

  // 가격
  price: number;                   // 판매가
  original_price: number | null;   // 원가
  discount_rate: number;           // 할인율 (0-100)
  final_price: number;             // 최종가 (할인 적용)

  // 단위 및 재고
  unit: string | null;             // 단위
  unit_quantity: decimal | null;   // 단위 수량
  stock_quantity: number;          // 재고 수량
  is_in_stock: boolean;            // 재고 있음 여부
  low_stock_threshold: number;     // 재고 부족 기준

  // 이미지
  main_image_url: string | null;   // 메인 이미지 URL
  images: ProductImageDTO[];       // 추가 이미지 목록

  // 관계
  category: CategoryDTO | null;    // 카테고리
  seller: SellerBriefDTO | null;   // 판매자 (seller 타입만)

  // 상태 플래그
  status: string;                  // 'draft' | 'active' | 'inactive' | 'out_of_stock' | 'discontinued'
  is_featured: boolean;            // 추천 상품
  is_best: boolean;                // 베스트 상품
  is_new: boolean;                 // 신상품
  is_on_sale: boolean;             // 할인 중

  // 배송
  shipping_required: boolean;      // 배송 필요 여부
  shipping_fee: number;            // 배송비
  free_shipping_threshold: number | null; // 무료배송 기준
  estimated_delivery_days: number | null; // 예상 배송일

  // 통계
  quality_score: decimal;          // 품질 점수
  view_count: number;              // 조회수
  average_rating: decimal;         // 평균 평점
  review_count: number;            // 리뷰 수
  wishlist_count: number;          // 찜 수

  // 사용자 상태
  is_wishlist: boolean;            // 현재 사용자 찜 여부

  // 추천
  related_products: ProductListDTO[]; // 관련 상품

  // 메타
  created_at: datetime;            // 생성일
  updated_at: datetime;            // 수정일
  published_at: datetime | null;   // 발행일
}

interface ProductImageDTO {
  id: number;                      // PK
  image_url: string;               // 이미지 URL
  alt_text: string | null;         // 대체 텍스트
  display_order: number;           // 표시 순서
  width: number | null;            // 너비 (px)
  height: number | null;           // 높이 (px)
  format: string | null;           // 포맷 ('jpg', 'png', 'webp')
}

interface SellerBriefDTO {
  id: number;                      // PK
  brand_name: string;              // 브랜드명
  brand_slug: string;              // 브랜드 슬러그
  average_rating: decimal;         // 평균 평점
  total_products: number;          // 전체 상품 수
}
```

#### ✅ Response 404
```typescript
{
  detail: string;          // "찾을 수 없습니다."
}
```

---

### ▼ [GET] 상품 재고 조회

| 항목 | 내용 |
|------|------|
| **Description** | 상품 재고 상태 조회 |
| **URL** | `https://sellfresh.shop/api/products/{id}/inventory/` |
| **Auth Required** | X |

| Parameter | Type | Required | Place | Description |
|-----------|------|----------|-------|-------------|
| `id` | number | O | url | 상품 ID |

#### ✅ Response 200
```typescript
interface ProductInventoryDTO {
  product_id: number;              // 상품 ID
  stock_quantity: number;          // 현재 재고 수량
  is_in_stock: boolean;            // 재고 있음 여부
  low_stock_threshold: number;     // 재고 부족 기준
  is_low_stock: boolean;           // 재고 부족 여부
}
```

#### ✅ Response 404
```typescript
{
  detail: string;          // "찾을 수 없습니다."
}
```

---

## 6. 판매자 상품 (Seller Product)

---

### ▼ [GET] 판매자 상품 목록 조회

| 항목 | 내용 |
|------|------|
| **Description** | 판매자 자신의 상품 목록 조회 |
| **URL** | `https://sellfresh.shop/api/seller/products/` |
| **Auth Required** | 판매자 |

| Parameter | Type | Required | Place | Description |
|-----------|------|----------|-------|-------------|
| `status` | string | X | query | 상태 필터 |
| `page` | number | X | query | 페이지 번호 |

#### ✅ Response 200
```typescript
interface SellerProductListResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: SellerProductDTO[];
}

interface SellerProductDTO {
  id: number;                      // PK
  name: string;                    // 상품명
  slug: string;                    // URL용 슬러그
  short_description: string | null; // 짧은 설명
  description: string | null;      // 상세 설명
  price: number;                   // 판매가
  original_price: number | null;   // 원가
  discount_rate: number;           // 할인율
  category_id: number | null;      // 카테고리 ID
  main_image_url: string | null;   // 메인 이미지 URL
  unit: string | null;             // 단위
  unit_quantity: decimal | null;   // 단위 수량
  stock_quantity: number;          // 재고 수량
  low_stock_threshold: number;     // 재고 부족 기준
  shipping_fee: number;            // 배송비
  free_shipping_threshold: number | null; // 무료배송 기준
  status: string;                  // 상태
  is_low_stock: boolean;           // 재고 부족 여부
  view_count: number;              // 조회수
  order_count: number;             // 주문 수
  created_at: datetime;            // 생성일
  updated_at: datetime;            // 수정일
}
```

#### ✅ Response 403
```typescript
{
  detail: string;          // "이 작업을 수행할 권한이 없습니다."
  code: string;            // "not_seller"
}
```

---

### ▼ [POST] 판매자 상품 등록

| 항목 | 내용 |
|------|------|
| **Description** | 새 상품 등록 (초기 상태: draft) |
| **URL** | `https://sellfresh.shop/api/seller/products/` |
| **Auth Required** | 판매자 |

| Parameter | Type | Required | Place | Description |
|-----------|------|----------|-------|-------------|
| `name` | string | O | body | 상품명 |
| `slug` | string | X | body | URL용 슬러그 (자동 생성) |
| `short_description` | string | X | body | 짧은 설명 |
| `description` | string | X | body | 상세 설명 |
| `price` | number | O | body | 판매가 |
| `original_price` | number | X | body | 원가 |
| `discount_rate` | number | X | body | 할인율 (기본: 0) |
| `category_id` | number | X | body | 카테고리 ID |
| `main_image_url` | string | X | body | 메인 이미지 URL |
| `unit` | string | X | body | 단위 |
| `unit_quantity` | decimal | X | body | 단위 수량 |
| `stock_quantity` | number | X | body | 재고 수량 (기본: 0) |
| `low_stock_threshold` | number | X | body | 재고 부족 기준 (기본: 10) |
| `shipping_fee` | number | X | body | 배송비 (기본: 0) |
| `free_shipping_threshold` | number | X | body | 무료배송 기준 |

#### ✅ Response 201
```typescript
// SellerProductDTO 참조 (status: 'draft')
```

#### ✅ Response 400
```typescript
{
  name?: string[];         // ["이 필드는 필수입니다."]
  price?: string[];        // ["이 필드는 필수입니다."]
}
```

---

### ▼ [GET] 판매자 상품 상세 조회

| 항목 | 내용 |
|------|------|
| **Description** | 판매자 상품 상세 정보 조회 |
| **URL** | `https://sellfresh.shop/api/seller/products/{id}/` |
| **Auth Required** | 판매자 |

| Parameter | Type | Required | Place | Description |
|-----------|------|----------|-------|-------------|
| `id` | number | O | url | 상품 ID |

#### ✅ Response 200
```typescript
// SellerProductDTO 참조
```

#### ✅ Response 404
```typescript
{
  detail: string;          // "찾을 수 없습니다."
}
```

---

### ▼ [PATCH] 판매자 상품 수정

| 항목 | 내용 |
|------|------|
| **Description** | 상품 정보 수정 (부분 수정 가능) |
| **URL** | `https://sellfresh.shop/api/seller/products/{id}/` |
| **Auth Required** | 판매자 |

| Parameter | Type | Required | Place | Description |
|-----------|------|----------|-------|-------------|
| `id` | number | O | url | 상품 ID |
| `name` | string | X | body | 상품명 |
| `short_description` | string | X | body | 짧은 설명 |
| `description` | string | X | body | 상세 설명 |
| `price` | number | X | body | 판매가 |
| `original_price` | number | X | body | 원가 |
| `discount_rate` | number | X | body | 할인율 |
| `category_id` | number | X | body | 카테고리 ID |
| `main_image_url` | string | X | body | 메인 이미지 URL |
| `stock_quantity` | number | X | body | 재고 수량 |
| `shipping_fee` | number | X | body | 배송비 |

#### ✅ Response 200
```typescript
// SellerProductDTO 참조
```

#### ✅ Response 404
```typescript
{
  detail: string;          // "찾을 수 없습니다."
}
```

---

### ▼ [DELETE] 판매자 상품 삭제

| 항목 | 내용 |
|------|------|
| **Description** | 상품 삭제 |
| **URL** | `https://sellfresh.shop/api/seller/products/{id}/` |
| **Auth Required** | 판매자 |

| Parameter | Type | Required | Place | Description |
|-----------|------|----------|-------|-------------|
| `id` | number | O | url | 상품 ID |

#### ✅ Response 204
```
No Content
```

#### ✅ Response 404
```typescript
{
  detail: string;          // "찾을 수 없습니다."
}
```

---

### ▼ [POST] 상품 발행

| 항목 | 내용 |
|------|------|
| **Description** | 상품 발행 (draft → active) |
| **URL** | `https://sellfresh.shop/api/seller/products/{id}/publish/` |
| **Auth Required** | 판매자 |

| Parameter | Type | Required | Place | Description |
|-----------|------|----------|-------|-------------|
| `id` | number | O | url | 상품 ID |

#### ✅ Response 200
```typescript
interface PublishResponse {
  message: string;                 // "상품이 발행되었습니다."
  product: SellerProductDTO;       // status: 'active'
}
```

#### ✅ Response 400
```typescript
{
  detail: string;          // "필수 정보가 누락되었습니다."
  missing_fields?: string[]; // ["main_image_url", "category_id"]
}
```

---

### ▼ [POST] 상품 비공개

| 항목 | 내용 |
|------|------|
| **Description** | 상품 비공개 (active → inactive) |
| **URL** | `https://sellfresh.shop/api/seller/products/{id}/unpublish/` |
| **Auth Required** | 판매자 |

| Parameter | Type | Required | Place | Description |
|-----------|------|----------|-------|-------------|
| `id` | number | O | url | 상품 ID |

#### ✅ Response 200
```typescript
interface UnpublishResponse {
  message: string;                 // "상품이 비공개 처리되었습니다."
  product: SellerProductDTO;       // status: 'inactive'
}
```

#### ✅ Response 404
```typescript
{
  detail: string;          // "찾을 수 없습니다."
}
```

---

### ▼ [POST] 상품 이미지 추가

| 항목 | 내용 |
|------|------|
| **Description** | 상품에 이미지 추가 |
| **URL** | `https://sellfresh.shop/api/seller/products/{id}/images/` |
| **Auth Required** | 판매자 |

| Parameter | Type | Required | Place | Description |
|-----------|------|----------|-------|-------------|
| `id` | number | O | url | 상품 ID |
| `images` | array | O | body | 이미지 정보 배열 |
| `images[].image_url` | string | O | body | 이미지 URL |
| `images[].alt_text` | string | X | body | 대체 텍스트 |
| `images[].display_order` | number | X | body | 표시 순서 |

#### ✅ Response 201
```typescript
interface ProductImageAddResponse {
  message: string;                 // "N개의 이미지가 추가되었습니다."
  images: ProductImageDTO[];       // 추가된 이미지 목록
}
```

#### ✅ Response 400
```typescript
{
  images?: string[];       // ["이 필드는 필수입니다."]
}
```

---

### ▼ [DELETE] 상품 이미지 삭제

| 항목 | 내용 |
|------|------|
| **Description** | 상품 이미지 삭제 |
| **URL** | `https://sellfresh.shop/api/seller/products/{id}/images/{img_id}/` |
| **Auth Required** | 판매자 |

| Parameter | Type | Required | Place | Description |
|-----------|------|----------|-------|-------------|
| `id` | number | O | url | 상품 ID |
| `img_id` | number | O | url | 이미지 ID |

#### ✅ Response 204
```
No Content
```

#### ✅ Response 404
```typescript
{
  detail: string;          // "찾을 수 없습니다."
}
```

---

### ▼ [PATCH] 상품 재고 수정

| 항목 | 내용 |
|------|------|
| **Description** | 상품 재고 수량 수정 |
| **URL** | `https://sellfresh.shop/api/seller/products/{id}/inventory/` |
| **Auth Required** | 판매자 |

| Parameter | Type | Required | Place | Description |
|-----------|------|----------|-------|-------------|
| `id` | number | O | url | 상품 ID |
| `stock_quantity` | number | O | body | 재고 수량 |
| `low_stock_threshold` | number | X | body | 재고 부족 기준 |

#### ✅ Response 200
```typescript
interface InventoryUpdateResponse {
  message: string;                 // "재고가 수정되었습니다."
  stock_quantity: number;          // 수정된 재고 수량
  is_low_stock: boolean;           // 재고 부족 여부
}
```

#### ✅ Response 404
```typescript
{
  detail: string;          // "찾을 수 없습니다."
}
```

---

## 7. 장바구니 (Cart)

---

### ▼ [GET] 장바구니 조회

| 항목 | 내용 |
|------|------|
| **Description** | 장바구니 항목 목록 조회 |
| **URL** | `https://sellfresh.shop/api/cart/` |
| **Auth Required** | O |

| Parameter | Type | Required | Place | Description |
|-----------|------|----------|-------|-------------|
| - | - | - | - | - |

#### ✅ Response 200
```typescript
interface CartListResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: CartItemDTO[];
}

interface CartItemDTO {
  id: number;                      // PK
  product: ProductListDTO;         // 상품 정보
  quantity: number;                // 수량 (1-999)
  subtotal: number;                // 소계 (final_price * quantity)
  created_at: datetime;            // 생성일
  updated_at: datetime;            // 수정일
}
```

#### ✅ Response 401
```typescript
{
  detail: string;          // "자격 인증데이터가 제공되지 않았습니다."
}
```

---

### ▼ [POST] 장바구니 추가

| 항목 | 내용 |
|------|------|
| **Description** | 상품을 장바구니에 추가 |
| **URL** | `https://sellfresh.shop/api/cart/` |
| **Auth Required** | O |

| Parameter | Type | Required | Place | Description |
|-----------|------|----------|-------|-------------|
| `product_id` | number | O | body | 상품 ID |
| `quantity` | number | X | body | 수량 (기본: 1) |

#### ✅ Response 201
```typescript
// CartItemDTO 참조
```

#### ✅ Response 400
```typescript
{
  product_id?: string[];   // ["이 필드는 필수입니다."]
  detail?: string;         // "상품을 찾을 수 없습니다."
}
```

---

### ▼ [PATCH] 장바구니 수량 변경

| 항목 | 내용 |
|------|------|
| **Description** | 장바구니 항목 수량 변경 |
| **URL** | `https://sellfresh.shop/api/cart/{id}/` |
| **Auth Required** | O |

| Parameter | Type | Required | Place | Description |
|-----------|------|----------|-------|-------------|
| `id` | number | O | url | 장바구니 항목 ID |
| `quantity` | number | O | body | 새 수량 (1-999) |

#### ✅ Response 200
```typescript
// CartItemDTO 참조
```

#### ✅ Response 404
```typescript
{
  detail: string;          // "찾을 수 없습니다."
}
```

---

### ▼ [DELETE] 장바구니 항목 삭제

| 항목 | 내용 |
|------|------|
| **Description** | 장바구니에서 항목 삭제 |
| **URL** | `https://sellfresh.shop/api/cart/{id}/` |
| **Auth Required** | O |

| Parameter | Type | Required | Place | Description |
|-----------|------|----------|-------|-------------|
| `id` | number | O | url | 장바구니 항목 ID |

#### ✅ Response 204
```
No Content
```

#### ✅ Response 404
```typescript
{
  detail: string;          // "찾을 수 없습니다."
}
```

---

### ▼ [GET] 장바구니 요약

| 항목 | 내용 |
|------|------|
| **Description** | 장바구니 총액 및 요약 정보 조회 |
| **URL** | `https://sellfresh.shop/api/cart/summary/` |
| **Auth Required** | O |

| Parameter | Type | Required | Place | Description |
|-----------|------|----------|-------|-------------|
| - | - | - | - | - |

#### ✅ Response 200
```typescript
interface CartSummaryDTO {
  total: number;                   // 총 금액 (할인 적용)
  count: number;                   // 상품 종류 수
  total_quantity: number;          // 총 수량
  items: CartItemDTO[];            // 장바구니 항목
}
```

#### ✅ Response 401
```typescript
{
  detail: string;          // "자격 인증데이터가 제공되지 않았습니다."
}
```

---

### ▼ [POST] 장바구니 비우기

| 항목 | 내용 |
|------|------|
| **Description** | 장바구니 전체 항목 삭제 |
| **URL** | `https://sellfresh.shop/api/cart/clear/` |
| **Auth Required** | O |

| Parameter | Type | Required | Place | Description |
|-----------|------|----------|-------|-------------|
| - | - | - | - | - |

#### ✅ Response 200
```typescript
interface CartClearResponse {
  message: string;                 // "N개 상품이 장바구니에서 제거되었습니다."
}
```

#### ✅ Response 401
```typescript
{
  detail: string;          // "자격 인증데이터가 제공되지 않았습니다."
}
```

---

## 8. 찜 목록 (Wishlist)

---

### ▼ [GET] 찜 목록 조회

| 항목 | 내용 |
|------|------|
| **Description** | 찜 목록 조회 |
| **URL** | `https://sellfresh.shop/api/wishlist/` |
| **Auth Required** | O |

| Parameter | Type | Required | Place | Description |
|-----------|------|----------|-------|-------------|
| - | - | - | - | - |

#### ✅ Response 200
```typescript
interface WishlistListResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: WishlistItemDTO[];
}

interface WishlistItemDTO {
  id: number;                      // PK
  product: ProductListDTO;         // 상품 정보
  created_at: datetime;            // 생성일
}
```

#### ✅ Response 401
```typescript
{
  detail: string;          // "자격 인증데이터가 제공되지 않았습니다."
}
```

---

### ▼ [POST] 찜 토글

| 항목 | 내용 |
|------|------|
| **Description** | 찜 추가/제거 토글 |
| **URL** | `https://sellfresh.shop/api/wishlist/toggle/` |
| **Auth Required** | O |

| Parameter | Type | Required | Place | Description |
|-----------|------|----------|-------|-------------|
| `product_id` | number | O | body | 상품 ID |

#### ✅ Response 201 (추가됨)
```typescript
interface WishlistToggleAddResponse {
  message: string;                 // "찜 목록에 추가되었습니다."
  is_wishlist: boolean;            // true
  wishlist: WishlistItemDTO;       // 찜 정보
}
```

#### ✅ Response 200 (제거됨)
```typescript
interface WishlistToggleRemoveResponse {
  message: string;                 // "찜 목록에서 제거되었습니다."
  is_wishlist: boolean;            // false
}
```

#### ✅ Response 400
```typescript
{
  product_id?: string[];   // ["이 필드는 필수입니다."]
}
```

---

### ▼ [DELETE] 찜 삭제

| 항목 | 내용 |
|------|------|
| **Description** | 찜 목록에서 삭제 |
| **URL** | `https://sellfresh.shop/api/wishlist/{id}/` |
| **Auth Required** | O |

| Parameter | Type | Required | Place | Description |
|-----------|------|----------|-------|-------------|
| `id` | number | O | url | 찜 ID |

#### ✅ Response 204
```
No Content
```

#### ✅ Response 404
```typescript
{
  detail: string;          // "찾을 수 없습니다."
}
```

---

## 9. 주문 (Order)

---

### ▼ [GET] 주문 목록 조회

| 항목 | 내용 |
|------|------|
| **Description** | 주문 내역 목록 조회 |
| **URL** | `https://sellfresh.shop/api/orders/` |
| **Auth Required** | O |

| Parameter | Type | Required | Place | Description |
|-----------|------|----------|-------|-------------|
| `status` | string | X | query | 상태 필터 |
| `page` | number | X | query | 페이지 번호 |
| `page_size` | number | X | query | 페이지 크기 |

#### ✅ Response 200
```typescript
interface OrderListResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: OrderDTO[];
}

interface OrderDTO {
  // 기본 정보
  id: number;                      // PK
  order_number: string;            // 주문번호 (ORD-YYYYMMDD-XXXXXX)
  user: number;                    // 사용자 ID

  // 배송 정보
  recipient_name: string;          // 수령인
  recipient_phone: string;         // 연락처
  shipping_address: string;        // 배송 주소
  shipping_memo: string | null;    // 배송 메모

  // 결제 정보
  payment_method_type: string;     // 결제 수단 ('card', 'bank', 'phone')
  payment_transaction_id: string | null; // 결제 트랜잭션 ID

  // 금액
  subtotal: number;                // 상품 금액
  shipping_fee: number;            // 배송비
  discount_amount: number;         // 할인액
  total_amount: number;            // 총 결제금액

  // 상태
  order_status: string;            // 주문 상태
  order_status_display: string;    // 주문 상태 표시명
  payment_status: string;          // 결제 상태
  payment_status_display: string;  // 결제 상태 표시명

  // 날짜
  paid_at: datetime | null;        // 결제일
  shipped_at: datetime | null;     // 배송 시작일
  delivered_at: datetime | null;   // 배송 완료일

  // 취소/환불
  cancelled_at: datetime | null;   // 취소일
  cancel_reason: string | null;    // 취소 사유
  refunded_at: datetime | null;    // 환불일
  refund_amount: number | null;    // 환불 금액

  // 배송 추적
  tracking_number: string | null;  // 송장번호

  // 주문 항목
  items: OrderItemDTO[];           // 주문 항목

  // 메타
  created_at: datetime;            // 생성일
  updated_at: datetime;            // 수정일
}

interface OrderItemDTO {
  id: number;                      // PK
  product: ProductListDTO;         // 상품 정보
  product_name: string;            // 상품명 스냅샷
  product_image_url: string | null; // 이미지 스냅샷
  quantity: number;                // 수량
  unit_price: number;              // 단가
  discount_amount: number;         // 할인액
  total_price: number;             // 소계
  status: string;                  // 품목별 상태
  created_at: datetime;            // 생성일
}
```

**주문 상태 (order_status)**
| 값 | 표시명 | 설명 |
|-----|--------|------|
| `pending` | 주문대기 | 주문 생성됨 |
| `paid` | 결제완료 | 결제 완료됨 |
| `processing` | 처리중 | 상품 준비 중 |
| `shipped` | 배송중 | 배송 시작됨 |
| `delivered` | 배송완료 | 배송 완료됨 |
| `cancelled` | 취소 | 주문 취소됨 |
| `refunded` | 환불 | 환불 완료됨 |

**결제 상태 (payment_status)**
| 값 | 표시명 | 설명 |
|-----|--------|------|
| `pending` | 결제대기 | 결제 대기 중 |
| `paid` | 결제완료 | 결제 완료됨 |
| `failed` | 결제실패 | 결제 실패됨 |
| `refunded` | 환불완료 | 전액 환불됨 |
| `partially_refunded` | 부분환불 | 일부 환불됨 |

---

### ▼ [POST] 주문 생성

| 항목 | 내용 |
|------|------|
| **Description** | 장바구니에서 주문 생성 |
| **URL** | `https://sellfresh.shop/api/orders/` |
| **Auth Required** | O |

| Parameter | Type | Required | Place | Description |
|-----------|------|----------|-------|-------------|
| `cart_item_ids` | array<number> | X | body | 장바구니 항목 ID 배열 (없으면 전체) |
| `recipient_name` | string | O | body | 수령인 이름 |
| `recipient_phone` | string | O | body | 수령인 연락처 |
| `shipping_address` | string | O | body | 배송 주소 |
| `shipping_memo` | string | X | body | 배송 메모 |
| `payment_method_type` | string | X | body | 결제 수단 (기본: 'card') |

#### ✅ Response 201
```typescript
interface OrderCreateResponse {
  message: string;                 // "주문이 완료되었습니다."
  order: OrderDTO;
}
```

#### ✅ Response 400
```typescript
{
  detail: string;          // "장바구니가 비어있습니다."
  code: string;            // "cart_empty"
}
```

---

### ▼ [GET] 주문 상세 조회

| 항목 | 내용 |
|------|------|
| **Description** | 주문 상세 정보 조회 |
| **URL** | `https://sellfresh.shop/api/orders/{order_no}/` |
| **Auth Required** | O |

| Parameter | Type | Required | Place | Description |
|-----------|------|----------|-------|-------------|
| `order_no` | string | O | url | 주문번호 |

#### ✅ Response 200
```typescript
// OrderDTO 참조
```

#### ✅ Response 404
```typescript
{
  detail: string;          // "찾을 수 없습니다."
}
```

---

### ▼ [POST] 주문 취소

| 항목 | 내용 |
|------|------|
| **Description** | 주문 취소 |
| **URL** | `https://sellfresh.shop/api/orders/{order_no}/cancel/` |
| **Auth Required** | O |

| Parameter | Type | Required | Place | Description |
|-----------|------|----------|-------|-------------|
| `order_no` | string | O | url | 주문번호 |
| `cancel_reason` | string | O | body | 취소 사유 |

#### ✅ Response 200
```typescript
interface OrderCancelResponse {
  message: string;                 // "주문이 취소되었습니다."
  order: OrderDTO;
}
```

#### ✅ Response 400
```typescript
{
  detail: string;          // "취소할 수 없는 주문입니다."
  code: string;            // "order_not_cancellable"
}
```

---

### ▼ [POST] 배송 완료 확인

| 항목 | 내용 |
|------|------|
| **Description** | 배송 완료 확인 |
| **URL** | `https://sellfresh.shop/api/orders/{order_no}/confirm-delivery/` |
| **Auth Required** | O |

| Parameter | Type | Required | Place | Description |
|-----------|------|----------|-------|-------------|
| `order_no` | string | O | url | 주문번호 |

#### ✅ Response 200
```typescript
interface DeliveryConfirmResponse {
  message: string;                 // "배송이 완료되었습니다."
  order: OrderDTO;
}
```

#### ✅ Response 400
```typescript
{
  detail: string;          // "배송 확인을 할 수 없는 주문입니다."
  code: string;            // "order_not_confirmable"
}
```

---

### ▼ [POST] 품목 부분 취소

| 항목 | 내용 |
|------|------|
| **Description** | 주문 내 특정 품목 부분 취소 |
| **URL** | `https://sellfresh.shop/api/orders/{order_no}/items/{item_id}/cancel/` |
| **Auth Required** | O |

| Parameter | Type | Required | Place | Description |
|-----------|------|----------|-------|-------------|
| `order_no` | string | O | url | 주문번호 |
| `item_id` | number | O | url | 품목 ID |
| `cancel_reason` | string | O | body | 취소 사유 |

#### ✅ Response 200
```typescript
interface ItemCancelResponse {
  message: string;                 // "품목이 취소되었습니다."
  order_item: OrderItemDTO;
}
```

#### ✅ Response 400
```typescript
{
  detail: string;          // "취소할 수 없는 품목입니다."
}
```

---

## 10. 판매자 (Seller)

---

### ▼ [GET] 판매자 목록 조회

| 항목 | 내용 |
|------|------|
| **Description** | 활성 판매자(브랜드몰) 목록 조회 |
| **URL** | `https://sellfresh.shop/api/sellers/` |
| **Auth Required** | X |

| Parameter | Type | Required | Place | Description |
|-----------|------|----------|-------|-------------|
| `search` | string | X | query | 검색어 (브랜드명) |
| `page` | number | X | query | 페이지 번호 |
| `page_size` | number | X | query | 페이지 크기 |

#### ✅ Response 200
```typescript
interface SellerListResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: SellerPublicDTO[];
}

interface SellerPublicDTO {
  id: number;                      // PK
  brand_name: string;              // 브랜드명
  brand_name_en: string | null;    // 브랜드 영문명
  brand_slug: string;              // 브랜드 슬러그
  brand_description: string | null; // 브랜드 설명
  brand_logo_url: string | null;   // 로고 URL
  brand_banner_url: string | null; // 배너 URL
  business_phone: string | null;   // 사업자 연락처
  customer_service_phone: string | null; // 고객 서비스 전화
  total_products: number;          // 총 상품 수
  total_reviews: number;           // 총 리뷰 수
  average_rating: decimal;         // 평균 평점
  follower_count: number;          // 팔로워 수
}
```

---

### ▼ [GET] 판매자 상세 조회

| 항목 | 내용 |
|------|------|
| **Description** | 판매자(브랜드몰) 상세 정보 조회 |
| **URL** | `https://sellfresh.shop/api/sellers/{slug}/` |
| **Auth Required** | X |

| Parameter | Type | Required | Place | Description |
|-----------|------|----------|-------|-------------|
| `slug` | string | O | url | 브랜드 슬러그 |

#### ✅ Response 200
```typescript
interface SellerDetailDTO {
  // 기본 정보
  id: number;                      // PK
  brand_name: string;              // 브랜드명
  brand_name_en: string | null;    // 브랜드 영문명
  brand_slug: string;              // 브랜드 슬러그
  brand_description: string | null; // 브랜드 설명
  brand_logo_url: string | null;   // 로고 URL
  brand_banner_url: string | null; // 배너 URL

  // 연락처
  business_phone: string | null;   // 사업자 연락처
  customer_service_phone: string | null; // 고객 서비스 전화
  business_address: string | null; // 사업장 주소

  // 통계
  total_products: number;          // 총 상품 수
  total_reviews: number;           // 총 리뷰 수
  average_rating: decimal;         // 평균 평점
  follower_count: number;          // 팔로워 수

  // 영업시간
  operating_hours: SellerOperatingHoursDTO[]; // 영업시간

  // 사용자 상태 (로그인 시)
  is_following: boolean;           // 현재 사용자 팔로우 여부
}

interface SellerOperatingHoursDTO {
  id: number;                      // PK
  day_of_week: number;             // 요일 (0=월, 6=일)
  day_of_week_display: string;     // 요일 표시명
  open_time: time;                 // 오픈 시간
  close_time: time;                // 마감 시간
  is_open: boolean;                // 영업 여부
}
```

#### ✅ Response 404
```typescript
{
  detail: string;          // "찾을 수 없습니다."
}
```

---

### ▼ [POST] 판매자 등록

| 항목 | 내용 |
|------|------|
| **Description** | 판매자 입점 신청 |
| **URL** | `https://sellfresh.shop/api/sellers/register/` |
| **Auth Required** | O |

| Parameter | Type | Required | Place | Description |
|-----------|------|----------|-------|-------------|
| `brand_name` | string | O | body | 브랜드명 |
| `brand_name_en` | string | X | body | 브랜드 영문명 |
| `brand_description` | string | X | body | 브랜드 설명 |
| `brand_logo_url` | string | X | body | 로고 URL |
| `brand_banner_url` | string | X | body | 배너 URL |
| `business_registration_number` | string | O | body | 사업자등록번호 |
| `business_type` | string | X | body | 사업자 유형 ('individual' \| 'corporate' \| 'cooperative') |
| `company_name` | string | X | body | 회사명 |
| `ceo_name` | string | X | body | 대표자명 |
| `business_phone` | string | X | body | 사업자 연락처 |
| `business_email` | string | X | body | 사업자 이메일 |
| `customer_service_phone` | string | X | body | 고객 서비스 전화 |
| `business_address` | string | X | body | 사업장 주소 |
| `warehouse_address` | string | X | body | 창고 주소 |
| `bank_name` | string | X | body | 은행명 |
| `bank_account_number` | string | X | body | 계좌번호 |
| `account_holder_name` | string | X | body | 예금주 |
| `verification_document_url` | string | X | body | 인증 문서 URL |

#### ✅ Response 201
```typescript
interface SellerDTO {
  // 기본 정보
  id: number;                      // PK
  user: number;                    // 사용자 ID
  username: string;                // 사용자명
  email: string;                   // 이메일

  // 브랜드 정보
  brand_name: string;              // 브랜드명
  brand_name_en: string | null;    // 브랜드 영문명
  brand_slug: string;              // 브랜드 슬러그
  brand_description: string | null; // 브랜드 설명
  brand_logo_url: string | null;   // 로고 URL
  brand_banner_url: string | null; // 배너 URL

  // 연락처
  business_phone: string | null;   // 사업자 연락처
  business_email: string | null;   // 사업자 이메일
  customer_service_phone: string | null; // 고객 서비스 전화
  business_address: string | null; // 사업장 주소

  // 배송 설정
  min_order_amount: number;        // 최소 주문 금액
  shipping_fee: decimal;           // 배송비
  free_shipping_threshold: decimal; // 무료배송 기준

  // 통계
  total_products: number;          // 총 상품 수
  total_sales: decimal;            // 총 매출
  total_reviews: number;           // 총 리뷰 수
  average_rating: decimal;         // 평균 평점
  follower_count: number;          // 팔로워 수

  // 상태
  status: string;                  // 'pending' | 'active' | 'suspended' | 'inactive'
  is_verified: boolean;            // 인증 여부
  verified_at: datetime | null;    // 인증일

  // 영업시간
  operating_hours: SellerOperatingHoursDTO[]; // 영업시간

  // 메타
  created_at: datetime;            // 생성일
  updated_at: datetime;            // 수정일
}
```

#### ✅ Response 400
```typescript
{
  brand_name?: string[];   // ["이 필드는 필수입니다."]
  detail?: string;         // "이미 판매자로 등록되어 있습니다."
  code?: string;           // "already_seller"
}
```

---

### ▼ [GET] 내 판매자 정보 조회

| 항목 | 내용 |
|------|------|
| **Description** | 현재 로그인한 판매자 정보 조회 |
| **URL** | `https://sellfresh.shop/api/sellers/me/` |
| **Auth Required** | 판매자 |

| Parameter | Type | Required | Place | Description |
|-----------|------|----------|-------|-------------|
| - | - | - | - | - |

#### ✅ Response 200
```typescript
// SellerDTO 참조
```

#### ✅ Response 403
```typescript
{
  detail: string;          // "판매자가 아닙니다."
  code: string;            // "not_seller"
}
```

---

### ▼ [PATCH] 판매자 정보 수정

| 항목 | 내용 |
|------|------|
| **Description** | 판매자 정보 수정 (부분 수정 가능) |
| **URL** | `https://sellfresh.shop/api/sellers/me/` |
| **Auth Required** | 판매자 |

| Parameter | Type | Required | Place | Description |
|-----------|------|----------|-------|-------------|
| `brand_name` | string | X | body | 브랜드명 |
| `brand_name_en` | string | X | body | 브랜드 영문명 |
| `brand_description` | string | X | body | 브랜드 설명 |
| `brand_logo_url` | string | X | body | 로고 URL |
| `brand_banner_url` | string | X | body | 배너 URL |
| `business_phone` | string | X | body | 사업자 연락처 |
| `business_email` | string | X | body | 사업자 이메일 |
| `customer_service_phone` | string | X | body | 고객 서비스 전화 |
| `business_address` | string | X | body | 사업장 주소 |
| `min_order_amount` | number | X | body | 최소 주문 금액 |
| `shipping_fee` | decimal | X | body | 배송비 |
| `free_shipping_threshold` | decimal | X | body | 무료배송 기준 |

#### ✅ Response 200
```typescript
// SellerDTO 참조
```

#### ✅ Response 400
```typescript
{
  brand_name?: string[];   // ["이 브랜드명은 이미 사용 중입니다."]
}
```

---

### ▼ [GET] 판매자 대시보드

| 항목 | 내용 |
|------|------|
| **Description** | 판매자 통계 및 대시보드 정보 조회 |
| **URL** | `https://sellfresh.shop/api/sellers/me/dashboard/` |
| **Auth Required** | 판매자 |

| Parameter | Type | Required | Place | Description |
|-----------|------|----------|-------|-------------|
| - | - | - | - | - |

#### ✅ Response 200
```typescript
interface SellerDashboardDTO extends SellerDTO {
  statistics: {
    total_products: number;        // 전체 상품 수
    active_products: number;       // 활성 상품 수
    draft_products: number;        // 임시저장 상품 수
    total_views: number;           // 총 조회수
    total_orders: number;          // 총 주문 수
    avg_quality_score: decimal;    // 평균 품질 점수
  };
}
```

#### ✅ Response 403
```typescript
{
  detail: string;          // "판매자가 아닙니다."
  code: string;            // "not_seller"
}
```

---

### ▼ [GET] 영업 시간 조회

| 항목 | 내용 |
|------|------|
| **Description** | 판매자 영업 시간 조회 |
| **URL** | `https://sellfresh.shop/api/sellers/me/schedules/` |
| **Auth Required** | 판매자 |

| Parameter | Type | Required | Place | Description |
|-----------|------|----------|-------|-------------|
| - | - | - | - | - |

#### ✅ Response 200
```typescript
SellerOperatingHoursDTO[]
```

#### ✅ Response 403
```typescript
{
  detail: string;          // "판매자가 아닙니다."
}
```

---

### ▼ [PUT] 영업 시간 설정

| 항목 | 내용 |
|------|------|
| **Description** | 판매자 영업 시간 설정 |
| **URL** | `https://sellfresh.shop/api/sellers/me/schedules/` |
| **Auth Required** | 판매자 |

| Parameter | Type | Required | Place | Description |
|-----------|------|----------|-------|-------------|
| `schedules` | array | O | body | 영업 시간 배열 (7개) |
| `schedules[].day_of_week` | number | O | body | 요일 (0=월, 6=일) |
| `schedules[].open_time` | time | O | body | 오픈 시간 |
| `schedules[].close_time` | time | O | body | 마감 시간 |
| `schedules[].is_open` | boolean | O | body | 영업 여부 |

#### ✅ Response 200
```typescript
SellerOperatingHoursDTO[]
```

#### ✅ Response 400
```typescript
{
  schedules?: string[];    // ["7개의 요일 정보가 필요합니다."]
}
```

---

### ▼ [POST] 판매자 팔로우 토글

| 항목 | 내용 |
|------|------|
| **Description** | 판매자 팔로우/언팔로우 토글 |
| **URL** | `https://sellfresh.shop/api/sellers/{id}/follow/` |
| **Auth Required** | O |

| Parameter | Type | Required | Place | Description |
|-----------|------|----------|-------|-------------|
| `id` | number | O | url | 판매자 ID |

#### ✅ Response 201 (팔로우됨)
```typescript
interface FollowResponse {
  message: string;                 // "팔로우했습니다."
  is_following: boolean;           // true
  follower_count: number;          // 팔로워 수
}
```

#### ✅ Response 200 (언팔로우됨)
```typescript
interface UnfollowResponse {
  message: string;                 // "언팔로우했습니다."
  is_following: boolean;           // false
  follower_count: number;          // 팔로워 수
}
```

#### ✅ Response 404
```typescript
{
  detail: string;          // "찾을 수 없습니다."
}
```

---

### ▼ [PATCH] 판매자 승인 (관리자)

| 항목 | 내용 |
|------|------|
| **Description** | 판매자 등록 승인/거절 (관리자 전용) |
| **URL** | `https://sellfresh.shop/api/admin/sellers/{id}/approve/` |
| **Auth Required** | 관리자 |

| Parameter | Type | Required | Place | Description |
|-----------|------|----------|-------|-------------|
| `id` | number | O | url | 판매자 ID |
| `action` | string | O | body | 'approve' \| 'reject' \| 'suspend' |
| `reason` | string | X | body | 거절/중지 사유 (reject/suspend 시) |

#### ✅ Response 200 (승인)
```typescript
interface SellerApprovalResponse {
  message: string;                 // "판매자가 승인되었습니다."
  seller: SellerDTO;
}
```

#### ✅ Response 200 (거절)
```typescript
interface SellerRejectionResponse {
  message: string;                 // "판매자 등록이 거절되었습니다."
  reason: string;                  // 거절 사유
}
```

#### ✅ Response 403
```typescript
{
  detail: string;          // "이 작업을 수행할 권한이 없습니다."
}
```

---

## 11. 리뷰 (Review)

---

### ▼ [GET] 상품 리뷰 목록 조회

| 항목 | 내용 |
|------|------|
| **Description** | 상품의 리뷰 목록 조회 |
| **URL** | `https://sellfresh.shop/api/products/{id}/reviews/` |
| **Auth Required** | X |

| Parameter | Type | Required | Place | Description |
|-----------|------|----------|-------|-------------|
| `id` | number | O | url | 상품 ID |
| `ordering` | string | X | query | 정렬 기준 |
| `page` | number | X | query | 페이지 번호 |
| `page_size` | number | X | query | 페이지 크기 |

**정렬 옵션 (ordering)**
- `-created_at`: 최신순 (기본)
- `-rating`: 평점 높은순
- `rating`: 평점 낮은순
- `-has_images`: 사진 리뷰 우선

#### ✅ Response 200
```typescript
interface ReviewListResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: ReviewDTO[];
}

interface ReviewDTO {
  id: number;                      // PK
  user: ReviewUserDTO;             // 작성자 정보
  product_id: number;              // 상품 ID
  order_item_id: number;           // 주문 품목 ID
  rating: number;                  // 평점 (1-5)
  content: string;                 // 리뷰 내용
  images: ReviewImageDTO[];        // 리뷰 이미지
  has_images: boolean;             // 이미지 포함 여부
  created_at: datetime;            // 작성일
  updated_at: datetime;            // 수정일
}

interface ReviewUserDTO {
  id: number;                      // 사용자 ID
  username: string | null;         // 사용자명 (마스킹 처리)
  profile_image_url: string | null; // 프로필 이미지
}

interface ReviewImageDTO {
  id: number;                      // PK
  image_url: string;               // 이미지 URL
  display_order: number;           // 표시 순서
}
```

---

### ▼ [POST] 리뷰 작성

| 항목 | 내용 |
|------|------|
| **Description** | 상품 리뷰 작성 (구매한 상품만) |
| **URL** | `https://sellfresh.shop/api/products/{id}/reviews/` |
| **Auth Required** | O |

| Parameter | Type | Required | Place | Description |
|-----------|------|----------|-------|-------------|
| `id` | number | O | url | 상품 ID |
| `order_item_id` | number | O | body | 주문 품목 ID |
| `rating` | number | O | body | 평점 (1-5) |
| `content` | string | O | body | 리뷰 내용 |
| `images` | array | X | body | 이미지 URL 배열 |

#### ✅ Response 201
```typescript
// ReviewDTO 참조
```

#### ✅ Response 400
```typescript
{
  detail?: string;         // "이미 리뷰를 작성한 상품입니다." 또는 "구매하지 않은 상품입니다."
  rating?: string[];       // ["1~5 사이의 값이어야 합니다."]
}
```

---

### ▼ [GET] 리뷰 통계 조회

| 항목 | 내용 |
|------|------|
| **Description** | 상품 리뷰 통계 조회 |
| **URL** | `https://sellfresh.shop/api/products/{id}/reviews/stats/` |
| **Auth Required** | X |

| Parameter | Type | Required | Place | Description |
|-----------|------|----------|-------|-------------|
| `id` | number | O | url | 상품 ID |

#### ✅ Response 200
```typescript
interface ReviewStatsDTO {
  average_rating: decimal;         // 평균 평점
  total_count: number;             // 총 리뷰 수
  photo_review_count: number;      // 사진 리뷰 수
  rating_distribution: {           // 평점별 분포
    1: number;
    2: number;
    3: number;
    4: number;
    5: number;
  };
}
```

---

### ▼ [PATCH] 리뷰 수정

| 항목 | 내용 |
|------|------|
| **Description** | 리뷰 수정 (본인 리뷰만) |
| **URL** | `https://sellfresh.shop/api/reviews/{id}/` |
| **Auth Required** | O |

| Parameter | Type | Required | Place | Description |
|-----------|------|----------|-------|-------------|
| `id` | number | O | url | 리뷰 ID |
| `rating` | number | X | body | 평점 (1-5) |
| `content` | string | X | body | 리뷰 내용 |
| `images` | array | X | body | 이미지 URL 배열 |

#### ✅ Response 200
```typescript
// ReviewDTO 참조
```

#### ✅ Response 403
```typescript
{
  detail: string;          // "이 작업을 수행할 권한이 없습니다."
}
```

#### ✅ Response 404
```typescript
{
  detail: string;          // "찾을 수 없습니다."
}
```

---

### ▼ [DELETE] 리뷰 삭제

| 항목 | 내용 |
|------|------|
| **Description** | 리뷰 삭제 (본인 리뷰만) |
| **URL** | `https://sellfresh.shop/api/reviews/{id}/` |
| **Auth Required** | O |

| Parameter | Type | Required | Place | Description |
|-----------|------|----------|-------|-------------|
| `id` | number | O | url | 리뷰 ID |

#### ✅ Response 204
```
No Content
```

#### ✅ Response 403
```typescript
{
  detail: string;          // "이 작업을 수행할 권한이 없습니다."
}
```

---

## 12. 추천 (Recommendation)

---

### ▼ [GET] 베스트 상품 조회

| 항목 | 내용 |
|------|------|
| **Description** | 베스트 상품 목록 조회 |
| **URL** | `https://sellfresh.shop/api/recommendations/best/` |
| **Auth Required** | X |

| Parameter | Type | Required | Place | Description |
|-----------|------|----------|-------|-------------|
| `category` | number | X | query | 카테고리 ID |
| `limit` | number | X | query | 조회 개수 (기본: 10) |

#### ✅ Response 200
```typescript
interface BestProductsResponse {
  products: ProductListDTO[];      // 베스트 상품 목록
  criteria: string;                // 추천 기준 설명
}
```

---

### ▼ [GET] 개인화 추천 조회

| 항목 | 내용 |
|------|------|
| **Description** | 개인화 상품 추천 조회 (로그인 사용자) |
| **URL** | `https://sellfresh.shop/api/recommendations/personal/` |
| **Auth Required** | O |

| Parameter | Type | Required | Place | Description |
|-----------|------|----------|-------|-------------|
| `limit` | number | X | query | 조회 개수 (기본: 10) |

#### ✅ Response 200
```typescript
interface PersonalRecommendationsResponse {
  products: ProductListDTO[];      // 추천 상품 목록
  based_on: string;                // 추천 기준 설명
}
```

#### ✅ Response 401
```typescript
{
  detail: string;          // "자격 인증데이터가 제공되지 않았습니다."
}
```

---

### ▼ [GET] 최근 본 상품 조회

| 항목 | 내용 |
|------|------|
| **Description** | 사용자가 최근 조회한 상품 목록 |
| **URL** | `https://sellfresh.shop/api/recommendations/recent/` |
| **Auth Required** | O |

| Parameter | Type | Required | Place | Description |
|-----------|------|----------|-------|-------------|
| `limit` | number | X | query | 조회 개수 (기본: 10) |

#### ✅ Response 200
```typescript
interface RecentViewedResponse {
  products: ProductListDTO[];      // 최근 본 상품 목록
}
```

#### ✅ Response 401
```typescript
{
  detail: string;          // "자격 인증데이터가 제공되지 않았습니다."
}
```

---

### ▼ [GET] 연관 상품 조회

| 항목 | 내용 |
|------|------|
| **Description** | 상품과 관련된 추천 상품 조회 |
| **URL** | `https://sellfresh.shop/api/products/{id}/related/` |
| **Auth Required** | X |

| Parameter | Type | Required | Place | Description |
|-----------|------|----------|-------|-------------|
| `id` | number | O | url | 상품 ID |
| `limit` | number | X | query | 조회 개수 (기본: 10) |

#### ✅ Response 200
```typescript
interface RelatedProductsResponse {
  products: ProductListDTO[];      // 연관 상품 목록
  relation_type: string;           // 연관 유형 설명
}
```

#### ✅ Response 404
```typescript
{
  detail: string;          // "찾을 수 없습니다."
}
```

---

## 13. 공통 응답 형식

### 13.1 성공 응답 예시

**단일 객체**
```json
{
  "id": 1,
  "name": "상품명",
  "price": 15000
}
```

**목록 (페이지네이션)**
```json
{
  "count": 100,
  "next": "https://sellfresh.shop/api/products/?page=2",
  "previous": null,
  "results": [
    {"id": 1, "name": "상품1"},
    {"id": 2, "name": "상품2"}
  ]
}
```

**작업 결과**
```json
{
  "message": "작업이 완료되었습니다.",
  "data": { ... }
}
```

---

### 13.2 에러 응답 예시

**400 Bad Request - 유효성 검증 실패**
```json
{
  "email": ["이 필드는 필수입니다."],
  "password": ["비밀번호는 최소 8자 이상이어야 합니다."]
}
```

**401 Unauthorized - 인증 실패**
```json
{
  "detail": "자격 인증데이터(authentication credentials)가 제공되지 않았습니다."
}
```

**403 Forbidden - 권한 없음**
```json
{
  "detail": "이 작업을 수행할 권한이 없습니다."
}
```

**404 Not Found - 리소스 없음**
```json
{
  "detail": "찾을 수 없습니다."
}
```

**비즈니스 로직 에러**
```json
{
  "detail": "취소할 수 없는 주문입니다.",
  "code": "order_not_cancellable"
}
```

---

### 13.3 에러 코드 목록

| 코드 | 설명 | HTTP 상태 |
|------|------|----------|
| `invalid_credentials` | 이메일/비밀번호 불일치 | 401 |
| `email_not_verified` | 이메일 미인증 | 401 |
| `verification_expired` | 인증 코드 만료 | 400 |
| `invalid_verification_code` | 인증 코드 불일치 | 400 |
| `invalid_token` | 유효하지 않은 토큰 | 400 |
| `token_not_valid` | 만료되거나 잘못된 토큰 | 401 |
| `user_not_found` | 사용자 없음 | 401 |
| `already_registered` | 이미 가입된 이메일 | 400 |
| `already_seller` | 이미 판매자로 등록됨 | 400 |
| `not_seller` | 판매자가 아님 | 403 |
| `product_not_found` | 상품 없음 | 404 |
| `out_of_stock` | 재고 부족 | 400 |
| `cart_empty` | 장바구니 비어있음 | 400 |
| `order_not_cancellable` | 취소 불가 주문 | 400 |
| `order_not_confirmable` | 배송 확인 불가 주문 | 400 |
| `already_reviewed` | 이미 리뷰 작성됨 | 400 |
| `not_purchased` | 구매하지 않은 상품 | 400 |

---

## 변경 이력

| 버전 | 날짜 | 작성자 | 변경 내용 |
|------|------|--------|----------|
| 1.0.0 | 2025-11-21 | 송준서 | 초기 작성 |
| 2.0.0 | 2025-12-01 | 송준서 | 요구사항 명세서 v2.0.0 반영 - API URL `/api/` prefix 추가, 리뷰/추천/판매자 팔로우 API 추가, 새 형식으로 전면 수정 |

---

## 부록: TypeScript 타입 정의 파일

프론트엔드에서 사용할 수 있는 TypeScript 타입 정의입니다.

```typescript
// types/api.ts

// ===== 공통 =====
export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface ErrorResponse {
  detail: string;
  code?: string;
}

// ===== 인증 =====
export interface RegisterRequest {
  email: string;
  password: string;
  username?: string;
}

export interface RegisterResponse {
  email: string;
  detail: string;
  expires_at: string;
  verification_code?: string;
}

export interface EmailVerifyRequest {
  email: string;
  code: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access: string;
  refresh: string;
  user: UserDTO;
}

export interface TokenRefreshRequest {
  refresh: string;
}

export interface TokenRefreshResponse {
  access: string;
  refresh: string;
}

// ===== 사용자 =====
export interface UserDTO {
  id: number;
  email: string;
  username: string | null;
  first_name: string;
  last_name: string;
  profile_image_url: string | null;
  provider: 'email' | 'google' | 'kakao';
  role: 'guest' | 'user' | 'seller' | 'admin';
  timezone: string | null;
}

export interface UserProfileDTO extends UserDTO {
  phone: string | null;
  birth_date: string | null;
  gender: 'M' | 'F' | null;
  language: string;
  push_notifications: boolean;
  email_notifications: boolean;
  marketing_agreed: boolean;
}

export interface UserAddressDTO {
  id: number;
  name: string;
  recipient_name: string;
  recipient_phone: string;
  postal_code: string;
  address_line1: string;
  address_line2: string | null;
  city: string;
  state: string;
  country: string;
  latitude: number | null;
  longitude: number | null;
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

// ===== 상품 =====
export interface CategoryDTO {
  id: number;
  name: string;
  slug: string;
  parent: number | null;
  created_at: string;
  updated_at: string;
}

export interface ProductListDTO {
  id: number;
  slug: string;
  name: string;
  price: number;
  original_price: number | null;
  discount_rate: number;
  discount: number;
  unit: string | null;
  main_image: string | null;
  category: CategoryDTO | null;
  category_name: string | null;
  is_featured: boolean;
  is_best: boolean;
  is_new: boolean;
  is_on_sale: boolean;
  quality_score: number;
  view_count: number;
  average_rating: number;
  review_count: number;
  wishlist_count: number;
}

export interface ProductImageDTO {
  id: number;
  image_url: string;
  alt_text: string | null;
  display_order: number;
  width: number | null;
  height: number | null;
  format: string | null;
}

export interface SellerBriefDTO {
  id: number;
  brand_name: string;
  brand_slug: string;
  average_rating: number;
  total_products: number;
}

export interface ProductDetailDTO extends ProductListDTO {
  product_type: 'main' | 'seller';
  short_description: string | null;
  description: string | null;
  final_price: number;
  unit_quantity: number | null;
  stock_quantity: number;
  is_in_stock: boolean;
  low_stock_threshold: number;
  main_image_url: string | null;
  images: ProductImageDTO[];
  seller: SellerBriefDTO | null;
  status: 'draft' | 'active' | 'inactive' | 'out_of_stock' | 'discontinued';
  shipping_required: boolean;
  shipping_fee: number;
  free_shipping_threshold: number | null;
  estimated_delivery_days: number | null;
  is_wishlist: boolean;
  related_products: ProductListDTO[];
  published_at: string | null;
  created_at: string;
  updated_at: string;
}

// ===== 판매자 상품 =====
export interface SellerProductDTO {
  id: number;
  name: string;
  slug: string;
  short_description: string | null;
  description: string | null;
  price: number;
  original_price: number | null;
  discount_rate: number;
  category_id: number | null;
  main_image_url: string | null;
  unit: string | null;
  unit_quantity: number | null;
  stock_quantity: number;
  low_stock_threshold: number;
  shipping_fee: number;
  free_shipping_threshold: number | null;
  status: string;
  is_low_stock: boolean;
  view_count: number;
  order_count: number;
  created_at: string;
  updated_at: string;
}

// ===== 장바구니 =====
export interface CartItemDTO {
  id: number;
  product: ProductListDTO;
  quantity: number;
  subtotal: number;
  created_at: string;
  updated_at: string;
}

export interface CartSummaryDTO {
  total: number;
  count: number;
  total_quantity: number;
  items: CartItemDTO[];
}

// ===== 찜 목록 =====
export interface WishlistItemDTO {
  id: number;
  product: ProductListDTO;
  created_at: string;
}

// ===== 주문 =====
export type OrderStatus = 'pending' | 'paid' | 'processing' | 'shipped' | 'delivered' | 'cancelled' | 'refunded';
export type PaymentStatus = 'pending' | 'paid' | 'failed' | 'refunded' | 'partially_refunded';

export interface OrderItemDTO {
  id: number;
  product: ProductListDTO;
  product_name: string;
  product_image_url: string | null;
  quantity: number;
  unit_price: number;
  discount_amount: number;
  total_price: number;
  status: string;
  created_at: string;
}

export interface OrderDTO {
  id: number;
  order_number: string;
  user: number;
  recipient_name: string;
  recipient_phone: string;
  shipping_address: string;
  shipping_memo: string | null;
  payment_method_type: string;
  payment_transaction_id: string | null;
  subtotal: number;
  shipping_fee: number;
  discount_amount: number;
  total_amount: number;
  order_status: OrderStatus;
  order_status_display: string;
  payment_status: PaymentStatus;
  payment_status_display: string;
  paid_at: string | null;
  shipped_at: string | null;
  delivered_at: string | null;
  cancelled_at: string | null;
  cancel_reason: string | null;
  refunded_at: string | null;
  refund_amount: number | null;
  tracking_number: string | null;
  items: OrderItemDTO[];
  created_at: string;
  updated_at: string;
}

export interface OrderCreateRequest {
  cart_item_ids?: number[];
  recipient_name: string;
  recipient_phone: string;
  shipping_address: string;
  shipping_memo?: string;
  payment_method_type?: string;
}

// ===== 판매자 =====
export interface SellerOperatingHoursDTO {
  id: number;
  day_of_week: number;
  day_of_week_display: string;
  open_time: string;
  close_time: string;
  is_open: boolean;
}

export interface SellerPublicDTO {
  id: number;
  brand_name: string;
  brand_name_en: string | null;
  brand_slug: string;
  brand_description: string | null;
  brand_logo_url: string | null;
  brand_banner_url: string | null;
  business_phone: string | null;
  customer_service_phone: string | null;
  total_products: number;
  total_reviews: number;
  average_rating: number;
  follower_count: number;
}

export interface SellerDetailDTO extends SellerPublicDTO {
  business_address: string | null;
  operating_hours: SellerOperatingHoursDTO[];
  is_following: boolean;
}

export interface SellerDTO {
  id: number;
  user: number;
  username: string;
  email: string;
  brand_name: string;
  brand_name_en: string | null;
  brand_slug: string;
  brand_description: string | null;
  brand_logo_url: string | null;
  brand_banner_url: string | null;
  business_phone: string | null;
  business_email: string | null;
  customer_service_phone: string | null;
  business_address: string | null;
  min_order_amount: number;
  shipping_fee: number;
  free_shipping_threshold: number;
  total_products: number;
  total_sales: number;
  total_reviews: number;
  average_rating: number;
  follower_count: number;
  status: 'pending' | 'active' | 'suspended' | 'inactive';
  is_verified: boolean;
  verified_at: string | null;
  operating_hours: SellerOperatingHoursDTO[];
  created_at: string;
  updated_at: string;
}

export interface SellerDashboardDTO extends SellerDTO {
  statistics: {
    total_products: number;
    active_products: number;
    draft_products: number;
    total_views: number;
    total_orders: number;
    avg_quality_score: number;
  };
}

export interface SellerRegisterRequest {
  brand_name: string;
  brand_name_en?: string;
  brand_description?: string;
  brand_logo_url?: string;
  brand_banner_url?: string;
  business_registration_number: string;
  business_type?: 'individual' | 'corporate' | 'cooperative';
  company_name?: string;
  ceo_name?: string;
  business_phone?: string;
  business_email?: string;
  customer_service_phone?: string;
  business_address?: string;
  warehouse_address?: string;
  bank_name?: string;
  bank_account_number?: string;
  account_holder_name?: string;
  verification_document_url?: string;
}

// ===== 리뷰 =====
export interface ReviewUserDTO {
  id: number;
  username: string | null;
  profile_image_url: string | null;
}

export interface ReviewImageDTO {
  id: number;
  image_url: string;
  display_order: number;
}

export interface ReviewDTO {
  id: number;
  user: ReviewUserDTO;
  product_id: number;
  order_item_id: number;
  rating: number;
  content: string;
  images: ReviewImageDTO[];
  has_images: boolean;
  created_at: string;
  updated_at: string;
}

export interface ReviewStatsDTO {
  average_rating: number;
  total_count: number;
  photo_review_count: number;
  rating_distribution: {
    1: number;
    2: number;
    3: number;
    4: number;
    5: number;
  };
}

export interface ReviewCreateRequest {
  order_item_id: number;
  rating: number;
  content: string;
  images?: string[];
}

// ===== 추천 =====
export interface BestProductsResponse {
  products: ProductListDTO[];
  criteria: string;
}

export interface PersonalRecommendationsResponse {
  products: ProductListDTO[];
  based_on: string;
}

export interface RecentViewedResponse {
  products: ProductListDTO[];
}

export interface RelatedProductsResponse {
  products: ProductListDTO[];
  relation_type: string;
}
```
