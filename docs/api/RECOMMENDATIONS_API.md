# 추천 API 명세서

> **문서 버전**: v1.0.0
> **최종 수정일**: 2025년 12월 09일
> **담당 기능**: REC-005 (최근 본 상품)

---

## 1. 개요

추천 시스템 관련 API 엔드포인트를 정의합니다.
현재는 **최근 본 상품 조회** 기능을 제공하며, 향후 개인화 추천, 연관 상품 추천 등이 추가될 예정입니다.

### Base URL

```
/api/recommendations/
```

### 인증 요구사항

| 엔드포인트 | 인증 필요 | 비고 |
|-----------|----------|------|
| `GET /recent/` | 필수 | JWT Bearer Token |

---

## 2. 엔드포인트 목록

| Method | Endpoint | 설명 | 상태 |
|--------|----------|------|------|
| GET | `/api/recommendations/recent/` | 최근 본 상품 조회 | 구현 완료 |
| GET | `/api/recommendations/personalized/` | 개인화 추천 | 예정 |
| GET | `/api/recommendations/similar/{product_id}/` | 유사 상품 추천 | 예정 |

---

## 3. 최근 본 상품 조회

### `GET /api/recommendations/recent/`

로그인한 사용자가 최근에 조회한 상품 목록을 반환합니다.

#### 요청

**Headers**

| 이름 | 필수 | 설명 |
|------|------|------|
| `Authorization` | O | `Bearer {access_token}` |

**Query Parameters**

| 파라미터 | 타입 | 필수 | 기본값 | 설명 |
|---------|------|------|--------|------|
| `limit` | integer | X | 10 | 조회 개수 (1~100) |

#### 응답

**성공 (200 OK)**

```json
{
  "products": [
    {
      "id": 123,
      "slug": "organic-apple-1kg",
      "name": "유기농 사과 1kg",
      "price": 15000,
      "original_price": 18000,
      "unit": "1kg",
      "main_image": "https://example.com/images/apple.jpg",
      "category": {
        "id": 1,
        "name": "과일",
        "slug": "fruits"
      },
      "category_name": "과일",
      "status": "active",
      "product_type": "main",
      "view_count": 1523,
      "average_rating": "4.50",
      "review_count": 42,
      "wishlist_count": 156,
      "quality_score": "85.00",
      "stock_quantity": 50,
      "created_at": "2025-12-01T10:30:00Z"
    }
  ]
}
```

**인증 오류 (401 Unauthorized)**

```json
{
  "detail": "자격 인증데이터가 제공되지 않았습니다."
}
```

#### 정렬 기준

- `last_interacted_at` 내림차순 (최근 조회 순)
- 동일 상품 중복 조회 시 마지막 조회 시간 기준

#### 필터링 조건

- `view_count > 0`: 실제로 상품 상세 페이지를 조회한 경우만 포함
- 장바구니만 담은 경우 (view_count = 0)는 제외

---

## 4. 응답 DTO 스키마

### ProductListDTO (v2.1)

최근 본 상품 응답에 사용되는 DTO입니다.

| 필드 | 타입 | Nullable | 설명 |
|------|------|----------|------|
| `id` | integer | X | 상품 PK |
| `slug` | string | X | URL 슬러그 |
| `name` | string | X | 상품명 |
| `price` | integer | X | 현재 가격 (원) |
| `original_price` | integer | O | 원가 (할인 전 가격) |
| `unit` | string | O | 단위 (예: "1kg", "500g") |
| `main_image` | string | O | 대표 이미지 URL |
| `category` | CategoryDTO | O | 카테고리 정보 |
| `category_name` | string | O | 카테고리명 (간편 접근용) |
| `status` | string | X | 상품 상태 (active/inactive 등) |
| `product_type` | string | X | 상품 유형 (main/seller) |
| `view_count` | integer | X | 조회수 |
| `average_rating` | decimal | X | 평균 평점 (0.00~5.00) |
| `review_count` | integer | X | 리뷰 수 |
| `wishlist_count` | integer | X | 찜 수 |
| `quality_score` | decimal | X | 품질 점수 (0.00~100.00) |
| `stock_quantity` | integer | O | 재고 수량 (null = 무제한) |
| `created_at` | datetime | X | 상품 등록일 |

### CategoryDTO

| 필드 | 타입 | 설명 |
|------|------|------|
| `id` | integer | 카테고리 PK |
| `name` | string | 카테고리명 |
| `slug` | string | URL 슬러그 |

---

## 5. 에러 코드

| HTTP Status | 코드 | 설명 | 해결 방법 |
|-------------|------|------|----------|
| 401 | `authentication_required` | 인증 토큰 없음 | 로그인 후 재시도 |
| 401 | `token_expired` | 토큰 만료 | 토큰 갱신 후 재시도 |
| 400 | `invalid_limit` | limit 값 유효하지 않음 | 1~100 사이 정수 사용 |

---

## 6. 사용 예시

### cURL

```bash
# 기본 조회 (최근 10개)
curl -X GET "http://localhost:8000/api/recommendations/recent/" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..."

# 개수 지정 (최근 5개)
curl -X GET "http://localhost:8000/api/recommendations/recent/?limit=5" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..."
```

### JavaScript (Axios)

```typescript
import axios from 'axios'

// 최근 본 상품 조회
const getRecentProducts = async (limit: number = 10) => {
  const response = await axios.get('/api/recommendations/recent/', {
    params: { limit },
    headers: {
      Authorization: `Bearer ${accessToken}`
    }
  })
  return response.data.products
}
```

### Vue 3 Composable

```vue
<script setup lang="ts">
import { useRecentProducts } from '@/composables/useRecentProducts'

// 최근 본 상품 5개 조회
const { recentProducts, isLoading, error, refresh } = useRecentProducts(5)
</script>

<template>
  <div v-if="isLoading">로딩 중...</div>
  <div v-else-if="error">오류 발생: {{ error.message }}</div>
  <ProductCard
    v-for="product in recentProducts"
    :key="product.id"
    :product="product"
  />
</template>
```

---

## 7. 관련 테이블

### UserProductStats (사용자별 상품 통계)

최근 본 상품 데이터의 원천 테이블입니다.

```
┌─────────────────────────────────────────────────────────────┐
│                     user_product_stats                       │
├─────────────────────────────────────────────────────────────┤
│ user_id (FK)           │ 사용자 ID                          │
│ product_id (FK)        │ 상품 ID                            │
│ view_count             │ 조회 횟수                          │
│ cart_event_count       │ 장바구니 추가 횟수                 │
│ order_event_count      │ 주문 횟수                          │
│ last_interacted_at     │ 마지막 상호작용 시간               │
├─────────────────────────────────────────────────────────────┤
│ 인덱스: ix_ups_user_recent (user, -last_interacted_at)      │
└─────────────────────────────────────────────────────────────┘
```

### 데이터 갱신 시점

| 액션 | 갱신 내용 |
|------|----------|
| 상품 상세 페이지 조회 | `view_count += 1`, `last_interacted_at = now()` |
| 장바구니 추가 | `cart_event_count += 1`, `last_interacted_at = now()` |
| 주문 완료 | `order_event_count += 1`, `last_interacted_at = now()` |

---

## 8. 성능 고려사항

### 인덱스 최적화

```sql
-- 최근 본 상품 조회 최적화 인덱스
CREATE INDEX ix_ups_user_recent ON user_product_stats (user_id, last_interacted_at DESC);
```

### 쿼리 최적화

```python
# select_related: FK 관계 조인 (1:1, N:1)
# prefetch_related: 역참조/M:N 관계 별도 쿼리
UserProductStats.objects.filter(
    user=request.user,
    view_count__gt=0
).select_related(
    'product__category',
    'product__stats',
    'product__inventory'
).prefetch_related(
    'product__images'
).order_by('-last_interacted_at')[:limit]
```

### 예상 쿼리 수

| 조건 | 쿼리 수 |
|------|--------|
| 최적화 전 | 1 + N (상품 수) x 4 (관계) |
| 최적화 후 | 2 (메인 + images prefetch) |

---

## 9. 변경 이력

| 버전 | 날짜 | 변경 내용 | 작성자 |
|------|------|----------|--------|
| v1.0.0 | 2025-12-09 | 최초 작성, REC-005 구현 | SelF 개발팀 |

---

**작성자**: SelF 개발팀
**관련 이슈**: REC-005
