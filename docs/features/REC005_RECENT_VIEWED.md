# REC-005: 최근 본 상품 기능 명세

> **문서 버전**: v1.0.0
> **최종 수정일**: 2025년 12월 09일
> **상태**: 구현 완료
> **담당자**: SelF 개발팀

---

## 1. 기능 개요

### 1.1 목적

사용자가 최근에 조회한 상품 목록을 제공하여 재방문 및 구매 전환율을 높입니다.

### 1.2 주요 기능

| 기능 | 설명 | 구현 상태 |
|------|------|----------|
| 조회 기록 저장 | 상품 상세 페이지 조회 시 자동 기록 | 완료 |
| 최근 본 상품 조회 | 마지막 조회 시간 기준 내림차순 반환 | 완료 |
| 중복 제거 | 같은 상품 여러 번 조회 시 1건만 표시 | 완료 |
| 조회 횟수 추적 | 동일 상품 재조회 시 카운트 증가 | 완료 |

### 1.3 비즈니스 규칙

1. **로그인 사용자 전용**: 비로그인 사용자는 조회 기록이 저장되지 않음
2. **실제 조회만 기록**: 장바구니 추가만 한 경우는 "최근 본 상품"에 포함되지 않음
3. **최대 100개**: limit 파라미터의 최대값은 100개
4. **기본 10개**: limit 미지정 시 최근 10개 반환

---

## 2. 아키텍처

### 2.1 데이터 흐름

```
┌─────────────────────────────────────────────────────────────────────┐
│                           사용자 흐름                                │
└─────────────────────────────────────────────────────────────────────┘

  [사용자]
     │
     ▼
  ┌──────────────────┐     ┌──────────────────┐
  │  상품 상세 조회   │────▶│  ProductDetail   │
  │  GET /products/1 │     │     View         │
  └──────────────────┘     └────────┬─────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
            ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
            │ ProductStats │ │UserProduct   │ │   Response   │
            │ view_count+1 │ │Stats 갱신    │ │   반환       │
            └──────────────┘ └──────────────┘ └──────────────┘


  [사용자]
     │
     ▼
  ┌──────────────────┐     ┌──────────────────┐     ┌──────────────┐
  │ 최근 본 상품 조회 │────▶│ RecentViewed     │────▶│ ProductList  │
  │ GET /recent/     │     │ ProductsView     │     │ DTO 반환     │
  └──────────────────┘     └──────────────────┘     └──────────────┘
```

### 2.2 테이블 관계

```
┌─────────────────┐       ┌─────────────────────┐       ┌─────────────┐
│     users       │       │  user_product_stats │       │  products   │
├─────────────────┤       ├─────────────────────┤       ├─────────────┤
│ id (PK)         │◀──────│ user_id (FK)        │       │ id (PK)     │
│ email           │       │ product_id (FK)     │──────▶│ name        │
│ username        │       │ view_count          │       │ price       │
└─────────────────┘       │ cart_event_count    │       │ ...         │
                          │ order_event_count   │       └─────────────┘
                          │ last_interacted_at  │
                          └─────────────────────┘
```

---

## 3. 구현 상세

### 3.1 Backend 파일 구조

```
backend/products/
├── models.py                    # UserProductStats 모델 (기존)
├── views.py                     # ProductDetailView 수정 (조회 기록)
├── recommendations_views.py     # RecentViewedProductsView (신규)
├── recommendations_urls.py      # /api/recommendations/ 라우팅 (신규)
├── serializers.py               # ProductListSerializerV2 (기존)
├── migrations/
│   └── 0005_add_user_recent_index.py  # 인덱스 마이그레이션 (신규)
└── tests/
    └── test_recent_viewed.py    # TDD 테스트 13개 (신규)
```

### 3.2 Frontend 파일 구조

```
frontend/src/
├── services/api/
│   └── recommendations.ts       # 추천 API 클라이언트 (신규)
└── composables/
    └── useRecentProducts.ts     # 최근 본 상품 Composable (신규)
```

### 3.3 핵심 코드

#### Backend: 조회 기록 저장 (views.py)

```python
# ProductDetailView.retrieve() 내부
if request.user.is_authenticated:
    # UPDATE 먼저 시도 (기존 레코드)
    rows_updated = UserProductStats.objects.filter(
        user=request.user,
        product=instance
    ).update(
        view_count=F('view_count') + 1,
        last_interacted_at=timezone.now()
    )

    # 없으면 CREATE (최초 조회)
    if rows_updated == 0:
        UserProductStats.objects.create(
            user=request.user,
            product=instance,
            view_count=1
        )
```

#### Backend: 최근 본 상품 조회 (recommendations_views.py)

```python
class RecentViewedProductsView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        limit = int(request.query_params.get('limit', 10))
        limit = max(1, min(limit, 100))

        recent_stats = UserProductStats.objects.filter(
            user=request.user,
            view_count__gt=0  # 실제 조회한 상품만
        ).select_related(
            'product__category',
            'product__stats',
            'product__inventory'
        ).prefetch_related(
            'product__images'
        ).order_by('-last_interacted_at')[:limit]

        products = [stat.product for stat in recent_stats]
        serializer = ProductListSerializerV2(products, many=True)

        return Response({'products': serializer.data})
```

#### Frontend: Composable (useRecentProducts.ts)

```typescript
export function useRecentProducts(limit: number = 10) {
  const recentProducts = ref<Product[]>([])
  const isLoading = ref(false)
  const error = ref<Error | null>(null)

  const fetchRecentProducts = async () => {
    isLoading.value = true
    error.value = null

    try {
      recentProducts.value = await recommendationApi.getRecentViewedProducts(limit)
    } catch (e) {
      error.value = e as Error
      const axiosError = e as AxiosError
      if (axiosError?.response?.status !== 401) {
        console.error('최근 본 상품 조회 실패:', e)
      }
    } finally {
      isLoading.value = false
    }
  }

  onMounted(fetchRecentProducts)

  return { recentProducts, isLoading, error, refresh: fetchRecentProducts }
}
```

---

## 4. 데이터베이스

### 4.1 테이블: user_product_stats

| 컬럼 | 타입 | 설명 |
|------|------|------|
| user_id | FK (bigint) | 사용자 ID |
| product_id | FK (bigint) | 상품 ID |
| view_count | bigint | 조회 횟수 |
| cart_event_count | bigint | 장바구니 추가 횟수 |
| order_event_count | bigint | 주문 횟수 |
| last_interacted_at | datetime | 마지막 상호작용 시간 |

**제약 조건**
- PRIMARY KEY: (user_id, product_id)
- UNIQUE: (user_id, product_id) - 중복 방지

### 4.2 인덱스

```sql
-- 최근 본 상품 조회 최적화
CREATE INDEX ix_ups_user_recent
ON user_product_stats (user_id, last_interacted_at DESC);
```

**인덱스 효과**
- 정렬 없이 인덱스 스캔으로 결과 반환
- ORDER BY 절 최적화

### 4.3 마이그레이션

```python
# 0005_add_user_recent_index.py
class Migration(migrations.Migration):
    dependencies = [
        ('products', '0004_optimize_price_history'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='userproductstats',
            index=models.Index(
                fields=['user', '-last_interacted_at'],
                name='ix_ups_user_recent'
            ),
        ),
    ]
```

---

## 5. API 엔드포인트

### 5.1 최근 본 상품 조회

```
GET /api/recommendations/recent/?limit=10
```

**요청 헤더**
```
Authorization: Bearer {access_token}
```

**응답 (200 OK)**
```json
{
  "products": [
    {
      "id": 1,
      "name": "유기농 사과",
      "price": 15000,
      "main_image": "https://...",
      ...
    }
  ]
}
```

자세한 API 명세는 [RECOMMENDATIONS_API.md](../api/RECOMMENDATIONS_API.md) 참조

---

## 6. 테스트

### 6.1 테스트 케이스 (13개)

| 테스트명 | 설명 | 상태 |
|---------|------|------|
| `test_비로그인_사용자_401_반환` | 인증 없이 접근 시 401 | PASS |
| `test_최근_본_상품_없을_때_빈_목록_반환` | 조회 기록 없으면 [] | PASS |
| `test_최근_본_상품_목록_반환` | 기록 있으면 상품 반환 | PASS |
| `test_최근_본_상품_최신순_정렬` | last_interacted_at DESC | PASS |
| `test_limit_파라미터_동작` | limit=3이면 3개 반환 | PASS |
| `test_기본_limit_10` | 미지정 시 10개 | PASS |
| `test_view_count_0인_상품_제외` | 장바구니만 추가한 경우 제외 | PASS |
| `test_다른_사용자_기록_제외` | 본인 기록만 조회 | PASS |
| `test_응답_형식_ProductListDTO` | DTO 필드 검증 | PASS |
| `test_로그인_사용자_상품_조회시_UserProductStats_생성` | 최초 조회 시 생성 | PASS |
| `test_로그인_사용자_반복_조회시_view_count_증가` | 재조회 시 +1 | PASS |
| `test_비로그인_사용자_조회시_UserProductStats_미생성` | 비로그인 기록 안함 | PASS |
| `test_조회시_last_interacted_at_갱신` | 시간 갱신 확인 | PASS |

### 6.2 테스트 실행

```bash
cd backend
python manage.py test products.tests.test_recent_viewed -v 2
```

---

## 7. 사용 가이드

### 7.1 프론트엔드에서 사용하기

```vue
<script setup lang="ts">
import { useRecentProducts } from '@/composables/useRecentProducts'

// 최근 본 상품 5개 조회 (마운트 시 자동 fetch)
const { recentProducts, isLoading, error, refresh } = useRecentProducts(5)
</script>

<template>
  <section v-if="recentProducts.length > 0" class="recent-products">
    <h2>최근 본 상품</h2>

    <div v-if="isLoading" class="loading">로딩 중...</div>

    <div v-else class="product-grid">
      <ProductCard
        v-for="product in recentProducts"
        :key="product.id"
        :product="product"
      />
    </div>

    <button @click="refresh">새로고침</button>
  </section>
</template>
```

### 7.2 API 직접 호출

```typescript
import { recommendationApi } from '@/services/api/recommendations'

// 최근 본 상품 10개 조회
const products = await recommendationApi.getRecentViewedProducts(10)
```

---

## 8. 성능 최적화

### 8.1 쿼리 최적화

| 항목 | 최적화 전 | 최적화 후 |
|------|----------|----------|
| 쿼리 수 | 1 + N x 4 | 2 |
| 인덱스 | 없음 | ix_ups_user_recent |
| 정렬 비용 | filesort | index scan |

### 8.2 적용된 최적화 기법

1. **select_related**: FK 관계 JOIN으로 쿼리 감소
2. **prefetch_related**: images 역참조 별도 쿼리
3. **복합 인덱스**: (user_id, -last_interacted_at)
4. **UPDATE first 패턴**: get_or_create 대신 update → create

---

## 9. 향후 개선 계획

| 항목 | 설명 | 우선순위 |
|------|------|----------|
| 캐싱 | Redis로 최근 본 상품 캐싱 | 중 |
| 비로그인 지원 | localStorage 기반 구현 | 중 |
| 만료 정책 | 30일 이상 된 기록 자동 삭제 | 하 |
| 분석 연동 | 조회 패턴 분석 대시보드 | 하 |

---

## 10. 관련 문서

- [추천 API 명세서](../api/RECOMMENDATIONS_API.md)
- [데이터베이스 스키마](../backend/DATABASE_SCHEMA_DETAILED.md)
- [DTO 명세서](../DTO_SPECIFICATION.md)

---

## 11. 변경 이력

| 버전 | 날짜 | 변경 내용 | 작성자 |
|------|------|----------|--------|
| v1.0.0 | 2025-12-09 | 최초 작성 | SelF 개발팀 |

---

**작성자**: SelF 개발팀
**관련 이슈**: REC-005
