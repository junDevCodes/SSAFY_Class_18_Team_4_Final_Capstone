# 베스트 상품 API 명세서

> **문서 버전**: v1.0.0
> **최종 수정일**: 2025년 12월 21일
> **담당 기능**: 베스트 상품 목록 조회 (판매량 기준)

---

## 1. 개요

판매자 상품(`product_type='seller'`) 중 판매량 기준으로 상위 40개 베스트 상품을 조회하는 API입니다.

### Base URL

```
GET /api/products/best/
```

### 인증 요구사항

| 엔드포인트 | 인증 필요 | 비고 |
|-----------|----------|------|
| `GET /api/products/best/` | 불필요 | 공개 API |

---

## 2. 조회 기준

### 대상 상품

- `product_type='seller'` (판매자 상품만)
- `status='active'` (판매중인 상품만)

### 정렬 우선순위

1. **일일 판매량 (오늘)**: 오늘 주문 횟수 기준 상위
2. **누적 판매량**: 일일 판매량이 동일하거나 없으면 누적 주문 횟수로 정렬
3. **등록일**: 판매량이 동일하면 최신 상품 우선

### 반환 개수

- 최대 40개
- 조건에 맞는 상품이 40개 미만이면 해당 개수만 반환

---

## 3. 요청

### HTTP 요청

```http
GET /api/products/best/ HTTP/1.1
Host: localhost:8000
Accept: application/json
```

### Query Parameters

현재 버전에서는 별도의 쿼리 파라미터가 없습니다.

---

## 4. 응답

### 성공 (200 OK)

```json
{
  "count": 40,
  "results": [
    {
      "id": 1,
      "slug": "fresh-milk-1l",
      "name": "신선한 우유 1L",
      "price": 3500,
      "original_price": 4000,
      "main_image": "https://example.com/images/milk.jpg",
      "category_name": "유제품",
      "review_count": 42,
      "average_rating": "4.50",
      "daily_order_count": 15,
      "total_order_count": 230,
      "created_at": "2025-12-01T10:30:00Z"
    },
    {
      "id": 5,
      "slug": "organic-apple-1kg",
      "name": "유기농 사과 1kg",
      "price": 12000,
      "original_price": 15000,
      "main_image": "https://example.com/images/apple.jpg",
      "category_name": "과일",
      "review_count": 28,
      "average_rating": "4.80",
      "daily_order_count": 12,
      "total_order_count": 185,
      "created_at": "2025-11-15T09:00:00Z"
    }
  ]
}
```

### 응답 필드 설명

| 필드 | 타입 | 설명 |
|------|------|------|
| `count` | integer | 반환된 상품 개수 |
| `results` | array | 베스트 상품 목록 |

#### results 배열 내 객체

| 필드 | 타입 | 설명 |
|------|------|------|
| `id` | integer | 상품 고유 ID |
| `slug` | string | URL 슬러그 |
| `name` | string | 상품명 |
| `price` | integer | 현재 판매가 (원) |
| `original_price` | integer \| null | 원가/정가 (할인 전 가격) |
| `main_image` | string \| null | 대표 이미지 URL |
| `category_name` | string \| null | 카테고리명 |
| `review_count` | integer | 리뷰 개수 |
| `average_rating` | string | 평균 평점 (1.00 ~ 5.00) |
| `daily_order_count` | integer | 오늘 주문 횟수 |
| `total_order_count` | integer | 누적 주문 횟수 |
| `created_at` | datetime | 상품 등록일시 (ISO 8601) |

---

## 5. 관련 테이블

### DailySalesStats (일일 판매 통계)

베스트 상품 산정을 위해 일일 판매량을 저장하는 테이블입니다.

| 필드 | 타입 | 설명 |
|------|------|------|
| `id` | integer | 고유 ID (PK) |
| `product_id` | integer | 상품 ID (FK) |
| `date` | date | 판매 날짜 |
| `order_count` | integer | 해당 날짜의 주문 횟수 |
| `created_at` | datetime | 생성일시 |
| `updated_at` | datetime | 수정일시 |

**인덱스**:
- `ix_dss_date_order`: `(date, -order_count)` - 날짜별 판매량 상위 조회 최적화
- `ix_dss_product_date`: `(product_id, date)` - 상품별 일일 통계 조회

### ProductStats (상품 통계)

누적 판매량 및 리뷰 통계를 저장하는 기존 테이블입니다.

| 필드 | 타입 | 설명 |
|------|------|------|
| `product_id` | integer | 상품 ID (PK, FK) |
| `order_event_count` | bigint | 누적 주문 횟수 |
| `review_count` | bigint | 리뷰 개수 |
| `average_rating` | decimal(3,2) | 평균 평점 |

---

## 6. 사용 예시

### cURL

```bash
curl -X GET "http://localhost:8000/api/products/best/" \
  -H "Accept: application/json"
```

### JavaScript (Axios)

```typescript
import axios from 'axios';

interface BestProduct {
  id: number;
  slug: string;
  name: string;
  price: number;
  original_price: number | null;
  main_image: string | null;
  category_name: string | null;
  review_count: number;
  average_rating: string;
  daily_order_count: number;
  total_order_count: number;
  created_at: string;
}

interface BestProductsResponse {
  count: number;
  results: BestProduct[];
}

const getBestProducts = async (): Promise<BestProduct[]> => {
  const response = await axios.get<BestProductsResponse>('/api/products/best/');
  return response.data.results;
};

// 사용 예시
const bestProducts = await getBestProducts();
console.log(`베스트 상품 ${bestProducts.length}개 조회 완료`);
```

### Vue 3 Composable

```typescript
// composables/useBestProducts.ts
import { ref, onMounted } from 'vue';
import axios from 'axios';

interface BestProduct {
  id: number;
  slug: string;
  name: string;
  price: number;
  original_price: number | null;
  main_image: string | null;
  category_name: string | null;
  review_count: number;
  average_rating: string;
  daily_order_count: number;
  total_order_count: number;
  created_at: string;
}

export function useBestProducts() {
  const products = ref<BestProduct[]>([]);
  const loading = ref(false);
  const error = ref<Error | null>(null);

  const fetchBestProducts = async () => {
    loading.value = true;
    error.value = null;

    try {
      const response = await axios.get('/api/products/best/');
      products.value = response.data.results;
    } catch (e) {
      error.value = e as Error;
    } finally {
      loading.value = false;
    }
  };

  onMounted(fetchBestProducts);

  return {
    products,
    loading,
    error,
    refetch: fetchBestProducts,
  };
}
```

---

## 7. 데이터 흐름

### 일일 판매량 업데이트

주문 생성 시 자동으로 `DailySalesStats` 테이블이 업데이트됩니다.

```
주문 생성 (OrderViewSet.create_order)
    │
    ├─► ProductStats.order_event_count += 1 (누적 판매량)
    │
    └─► DailySalesStats (오늘 날짜)
        ├─ 기존 레코드 있음: order_count += 1
        └─ 기존 레코드 없음: 새 레코드 생성 (order_count = 1)
```

### 베스트 상품 조회

```
GET /api/products/best/
    │
    ├─► Product 필터링
    │   └─ product_type='seller' AND status='active'
    │
    ├─► DailySalesStats 조인
    │   └─ 오늘 날짜의 order_count 가져오기 (없으면 0)
    │
    ├─► ProductStats 조인
    │   └─ order_event_count, review_count, average_rating 가져오기
    │
    └─► 정렬 및 반환
        └─ ORDER BY daily_order_count DESC, total_order_count DESC, created_at DESC
        └─ LIMIT 40
```

---

## 8. 성능 고려사항

### 쿼리 최적화

- `select_related`: category, stats 테이블 조인
- `prefetch_related`: images 테이블 프리페치
- `Subquery`: DailySalesStats에서 오늘 판매량 서브쿼리로 조회

### 인덱스 활용

```sql
-- 베스트 상품 조회 시 활용되는 인덱스
CREATE INDEX ix_products_type ON products (product_type);
CREATE INDEX ix_products_status ON products (status);
CREATE INDEX ix_dss_date_order ON daily_sales_stats (date, order_count DESC);
```

### 캐싱 권장

베스트 상품 목록은 실시간성이 중요하지 않으므로 Redis 캐싱을 권장합니다.

```python
# 캐싱 예시 (향후 구현 시)
CACHE_TTL = 60 * 5  # 5분
cache_key = f"best_products:{timezone.now().date()}"
```

---

## 9. 관련 API

| API | 설명 |
|-----|------|
| `GET /api/products/` | 상품 목록 (필터링/정렬) |
| `GET /api/products/new/` | 신상품 목록 (최신 40개) |
| `GET /api/products/<id>/` | 상품 상세 |
| `POST /api/orders/create_order/` | 주문 생성 (판매량 업데이트) |

---

## 10. 변경 이력

| 버전 | 날짜 | 변경 내용 |
|------|------|----------|
| v1.0.0 | 2025-12-21 | 최초 작성 |
