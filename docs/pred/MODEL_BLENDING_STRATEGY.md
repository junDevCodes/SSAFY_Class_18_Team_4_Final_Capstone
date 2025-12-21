# SelF 모델 가중치 블렌딩 전략 설계서

> **문서 버전**: v1.0.0
> **최종 수정일**: 2025년 12월 14일

---

## 1. 개요

### 1.1 목적

이 문서는 SelF 추천 시스템의 **4개 모델을 어떻게 블렌딩하여 최종 추천을 생성하는지** 상세히 기술합니다.

### 1.2 모델 구성

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SelF 추천 모델 구성                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    전역 추천 모델 (Global)                            │  │
│  │                                                                       │  │
│  │  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐            │  │
│  │  │  Instacart    │  │     SelF      │  │ PriceAnomaly  │            │  │
│  │  │  ColdStart    │  │ Personalized  │  │  TimeSeries   │            │  │
│  │  │               │  │               │  │               │            │  │
│  │  │ 외부 데이터   │  │ 자체 데이터   │  │ 가격 데이터   │            │  │
│  │  │ 기반 추천    │  │ 기반 추천    │  │ 기반 추천    │            │  │
│  │  └───────────────┘  └───────────────┘  └───────────────┘            │  │
│  │                                                                       │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    컨텍스트 추천 모델 (Contextual)                    │  │
│  │                                                                       │  │
│  │  ┌───────────────────────────────────────────────────────────────┐   │  │
│  │  │                    RecipePickleModel                           │   │  │
│  │  │                                                                │   │  │
│  │  │  장바구니 기반 레시피 추천 + Gap 재료 상품 매칭                 │   │  │
│  │  │  (전역 모델과 독립적으로 동작)                                  │   │  │
│  │  └───────────────────────────────────────────────────────────────┘   │  │
│  │                                                                       │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. 블렌딩 계층 구조

### 2.1 전체 블렌딩 흐름

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       Blending Layer Architecture                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   API 요청                                                                  │
│       │                                                                     │
│       ▼                                                                     │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                    Context Analyzer                                  │  │
│   │                                                                      │  │
│   │  입력 분석:                                                          │  │
│   │  • user_id → 유저 타입 분류 (cold/lukewarm/warm)                    │  │
│   │  • page_type → 페이지 컨텍스트 파악                                  │  │
│   │  • time → 시간대 컨텍스트                                            │  │
│   │  • cart_items → 장바구니 컨텍스트                                    │  │
│   │                                                                      │  │
│   └───────────────────────────────┬─────────────────────────────────────┘  │
│                                   │                                         │
│                                   ▼                                         │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                    Phase Detector                                    │  │
│   │                                                                      │  │
│   │  서비스 전체 상호작용 수 기반 Phase 결정:                            │  │
│   │  • Phase 1 (Cold): < 1,000                                          │  │
│   │  • Phase 2 (Growing): 1,000 ~ 10,000                                │  │
│   │  • Phase 3 (Mature): 10,000 ~ 50,000                                │  │
│   │  • Phase 4 (Self-Sufficient): > 50,000                              │  │
│   │                                                                      │  │
│   └───────────────────────────────┬─────────────────────────────────────┘  │
│                                   │                                         │
│                                   ▼                                         │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                    Weight Calculator                                 │  │
│   │                                                                      │  │
│   │  Phase + User Type + Page Type 조합으로 가중치 결정                 │  │
│   │                                                                      │  │
│   └───────────────────────────────┬─────────────────────────────────────┘  │
│                                   │                                         │
│                                   ▼                                         │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                    Parallel Model Execution                          │  │
│   │                                                                      │  │
│   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │  │
│   │  │ Instacart   │  │    SelF     │  │   Price     │                 │  │
│   │  │ Model       │  │   Model     │  │   Model     │                 │  │
│   │  │             │  │             │  │             │                 │  │
│   │  │  (async)    │  │  (async)    │  │  (async)    │                 │  │
│   │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘                 │  │
│   │         │                │                │                         │  │
│   └─────────┼────────────────┼────────────────┼─────────────────────────┘  │
│             │                │                │                             │
│             ▼                ▼                ▼                             │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                    Score Fusion Layer                                │  │
│   │                                                                      │  │
│   │  final_score = Σ (weight_i × score_i)                               │  │
│   │                                                                      │  │
│   │  • 정규화 (Min-Max 또는 Z-Score)                                    │  │
│   │  • 가중 합계                                                         │  │
│   │  • 시간 컨텍스트 보정                                                │  │
│   │                                                                      │  │
│   └───────────────────────────────┬─────────────────────────────────────┘  │
│                                   │                                         │
│                                   ▼                                         │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                    Diversity Filter (MMR)                            │  │
│   │                                                                      │  │
│   │  카테고리 다양성 보장                                                │  │
│   │  λ × relevance + (1-λ) × diversity                                  │  │
│   │                                                                      │  │
│   └───────────────────────────────┬─────────────────────────────────────┘  │
│                                   │                                         │
│                                   ▼                                         │
│   최종 추천 결과                                                            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. 가중치 행렬

### 3.1 Phase × User Type 가중치

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Phase × User Type Weight Matrix                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Phase 1 (Cold) - 서비스 초기, 데이터 부족                                  │
│  ─────────────────────────────────────────────────────────────────────────  │
│  │ User Type   │ Instacart │   SelF   │ PriceAnomaly │                     │
│  │─────────────┼───────────┼──────────┼──────────────│                     │
│  │ cold        │   0.75    │   0.05   │    0.20      │                     │
│  │ lukewarm    │   0.70    │   0.10   │    0.20      │                     │
│  │ warm        │   0.65    │   0.15   │    0.20      │                     │
│                                                                             │
│  Phase 2 (Growing) - 데이터 축적 중                                         │
│  ─────────────────────────────────────────────────────────────────────────  │
│  │ User Type   │ Instacart │   SelF   │ PriceAnomaly │                     │
│  │─────────────┼───────────┼──────────┼──────────────│                     │
│  │ cold        │   0.55    │   0.25   │    0.20      │                     │
│  │ lukewarm    │   0.45    │   0.35   │    0.20      │                     │
│  │ warm        │   0.35    │   0.45   │    0.20      │                     │
│                                                                             │
│  Phase 3 (Mature) - 충분한 데이터                                           │
│  ─────────────────────────────────────────────────────────────────────────  │
│  │ User Type   │ Instacart │   SelF   │ PriceAnomaly │                     │
│  │─────────────┼───────────┼──────────┼──────────────│                     │
│  │ cold        │   0.40    │   0.35   │    0.25      │                     │
│  │ lukewarm    │   0.25    │   0.50   │    0.25      │                     │
│  │ warm        │   0.15    │   0.60   │    0.25      │                     │
│                                                                             │
│  Phase 4 (Self-Sufficient) - 완전 자립                                      │
│  ─────────────────────────────────────────────────────────────────────────  │
│  │ User Type   │ Instacart │   SelF   │ PriceAnomaly │                     │
│  │─────────────┼───────────┼──────────┼──────────────│                     │
│  │ cold        │   0.25    │   0.50   │    0.25      │                     │
│  │ lukewarm    │   0.10    │   0.65   │    0.25      │                     │
│  │ warm        │   0.05    │   0.70   │    0.25      │                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Page Type별 가중치 조정

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Page Type Weight Adjustments                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  페이지 유형별로 기본 가중치에 승수 적용                                    │
│                                                                             │
│  ┌───────────────┬─────────────────────────────────────────────────────┐  │
│  │ Page Type     │ 가중치 조정                                          │  │
│  ├───────────────┼─────────────────────────────────────────────────────┤  │
│  │               │                                                      │  │
│  │ home          │ 기본 가중치 그대로                                   │  │
│  │               │ (전역 추천)                                          │  │
│  │               │                                                      │  │
│  ├───────────────┼─────────────────────────────────────────────────────┤  │
│  │               │                                                      │  │
│  │ category      │ SelF × 1.2 (카테고리 선호 반영)                      │  │
│  │               │ Instacart × 0.8                                      │  │
│  │               │                                                      │  │
│  ├───────────────┼─────────────────────────────────────────────────────┤  │
│  │               │                                                      │  │
│  │ product       │ SelF × 1.3 (유사 상품 추천)                          │  │
│  │               │ PriceAnomaly × 1.2 (같은 카테고리 할인)              │  │
│  │               │                                                      │  │
│  ├───────────────┼─────────────────────────────────────────────────────┤  │
│  │               │                                                      │  │
│  │ cart          │ Recipe 모델 추가 활성화                              │  │
│  │               │ SelF × 1.4 (장바구니 보완)                           │  │
│  │               │                                                      │  │
│  ├───────────────┼─────────────────────────────────────────────────────┤  │
│  │               │                                                      │  │
│  │ time_sale     │ PriceAnomaly × 2.0 (가격 중심)                       │  │
│  │               │ Instacart × 0.5 (시간대만 참고)                      │  │
│  │               │ SelF × 0.5                                           │  │
│  │               │                                                      │  │
│  └───────────────┴─────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.3 시간 컨텍스트별 가중치

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Time Context Weight Adjustments                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  시간대별 PriceAnomaly 모델 가중치 조정                                     │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                                                                      │  │
│  │   시간대       │ PriceAnomaly 승수 │ 설명                            │  │
│  │   ─────────────┼───────────────────┼───────────────────────────────  │  │
│  │   morning      │      1.0          │ 기본 (아침 쇼핑 정상)           │  │
│  │   (06-11)      │                   │                                 │  │
│  │                │                   │                                 │  │
│  │   lunch        │      1.2          │ 점심시간 할인 관심↑            │  │
│  │   (11-14)      │                   │                                 │  │
│  │                │                   │                                 │  │
│  │   dinner       │      1.3          │ 저녁 장보기 할인 민감↑          │  │
│  │   (17-21)      │                   │                                 │  │
│  │                │                   │                                 │  │
│  │   night        │      1.5          │ 야간 할인 민감도 최고           │  │
│  │   (21-06)      │                   │ (야식/충동구매)                 │  │
│  │                │                   │                                 │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Score Fusion 알고리즘

### 4.1 점수 정규화

```python
class ScoreNormalizer:
    """
    각 모델의 점수를 0~1 범위로 정규화

    정규화 방법:
    1. Min-Max: (x - min) / (max - min)
    2. Z-Score: (x - mean) / std → sigmoid
    """

    def normalize_minmax(
        self,
        scores: List[float],
        epsilon: float = 1e-8,
    ) -> List[float]:
        """Min-Max 정규화"""
        min_score = min(scores)
        max_score = max(scores)
        range_score = max_score - min_score + epsilon

        return [(s - min_score) / range_score for s in scores]

    def normalize_zscore(
        self,
        scores: List[float],
    ) -> List[float]:
        """Z-Score 정규화 + Sigmoid"""
        mean = np.mean(scores)
        std = np.std(scores) + 1e-8

        z_scores = [(s - mean) / std for s in scores]

        # Sigmoid로 0~1 변환
        return [1 / (1 + np.exp(-z)) for z in z_scores]
```

### 4.2 가중 합계

```python
class ScoreFusion:
    """
    정규화된 점수의 가중 합계
    """

    def fuse(
        self,
        instacart_scores: Dict[int, float],
        self_scores: Dict[int, float],
        price_scores: Dict[int, float],
        weights: Dict[str, float],
    ) -> Dict[int, float]:
        """
        각 모델 점수를 가중 합계

        Args:
            instacart_scores: {product_id: score}
            self_scores: {product_id: score}
            price_scores: {product_id: score}
            weights: {'instacart': 0.4, 'self': 0.4, 'price': 0.2}

        Returns:
            {product_id: final_score}
        """
        all_product_ids = set(
            list(instacart_scores.keys()) +
            list(self_scores.keys()) +
            list(price_scores.keys())
        )

        final_scores = {}

        for pid in all_product_ids:
            score = 0.0

            # Instacart 점수
            if pid in instacart_scores:
                score += weights['instacart'] * instacart_scores[pid]

            # SelF 점수
            if pid in self_scores:
                score += weights['self'] * self_scores[pid]

            # Price 점수
            if pid in price_scores:
                score += weights['price'] * price_scores[pid]

            final_scores[pid] = score

        return final_scores

    def apply_time_boost(
        self,
        scores: Dict[int, float],
        products: Dict[int, Dict],
        time_context: str,
    ) -> Dict[int, float]:
        """
        시간 컨텍스트 기반 부스트 적용
        """
        TIME_CATEGORY_BOOST = {
            'morning': {'dairy': 1.2, 'bakery': 1.3, 'coffee': 1.4},
            'lunch': {'ready_meal': 1.3, 'salad': 1.2},
            'dinner': {'meat': 1.3, 'seafood': 1.3, 'vegetable': 1.2},
            'night': {'snack': 1.4, 'ramen': 1.5, 'drink': 1.3},
        }

        boosts = TIME_CATEGORY_BOOST.get(time_context, {})

        for pid, score in scores.items():
            product = products.get(pid, {})
            category = product.get('category_type')

            boost = boosts.get(category, 1.0)
            scores[pid] = score * boost

        return scores
```

---

## 5. 타임세일 블렌딩 특화

### 5.1 타임세일 추천 흐름

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Time-Sale Recommendation Blending                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   입력: user_id, current_time, category_filter (optional)                   │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                  Step 1: 후보 수집                                   │  │
│   │                                                                      │  │
│   │  ┌───────────────────────────────────────────────────────────────┐ │  │
│   │  │                 PriceAnomaly Model (주력)                     │ │  │
│   │  │                                                               │ │  │
│   │  │  • 현재 할인 중인 상품 (original_price > price)              │ │  │
│   │  │  • 가격 하락 감지 상품 (최근 24시간)                          │ │  │
│   │  │  • Z-Score 이상치 상품 (카테고리 평균 대비)                   │ │  │
│   │  │  • 타임세일 지정 상품                                         │ │  │
│   │  │                                                               │ │  │
│   │  │  점수 = discount_rate × 0.5 + z_score_abs × 0.3              │ │  │
│   │  │         + time_limited_bonus × 0.2                           │ │  │
│   │  │                                                               │ │  │
│   │  └───────────────────────────────────────────────────────────────┘ │  │
│   │                                                                      │  │
│   │  ┌───────────────────────────────────────────────────────────────┐ │  │
│   │  │              Instacart Model (시간대 보조)                    │ │  │
│   │  │                                                               │ │  │
│   │  │  • 현재 시간대에 인기 있는 카테고리 상품                      │ │  │
│   │  │  • 가중치: 0.2 (보조 역할)                                   │ │  │
│   │  │                                                               │ │  │
│   │  └───────────────────────────────────────────────────────────────┘ │  │
│   │                                                                      │  │
│   │  ┌───────────────────────────────────────────────────────────────┐ │  │
│   │  │               SelF Model (개인화 보조)                        │ │  │
│   │  │                                                               │ │  │
│   │  │  • 유저 선호 카테고리의 할인 상품                             │ │  │
│   │  │  • 가중치: warm user만 0.2, 그 외 0.1                        │ │  │
│   │  │                                                               │ │  │
│   │  └───────────────────────────────────────────────────────────────┘ │  │
│   │                                                                      │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                      │                                      │
│                                      ▼                                      │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                  Step 2: 점수 계산 및 융합                           │  │
│   │                                                                      │  │
│   │  time_sale_score =                                                  │  │
│   │      0.6 × price_anomaly_score +                                    │  │
│   │      0.2 × instacart_time_score +                                   │  │
│   │      0.2 × self_preference_score                                    │  │
│   │                                                                      │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                      │                                      │
│                                      ▼                                      │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                  Step 3: 긴급도 부스트                               │  │
│   │                                                                      │  │
│   │  if time_remaining < 1h:                                            │  │
│   │      urgency_boost = 1.5                                            │  │
│   │  elif time_remaining < 3h:                                          │  │
│   │      urgency_boost = 1.3                                            │  │
│   │  elif time_remaining < 6h:                                          │  │
│   │      urgency_boost = 1.15                                           │  │
│   │  else:                                                               │  │
│   │      urgency_boost = 1.0                                            │  │
│   │                                                                      │  │
│   │  final_score = time_sale_score × urgency_boost                      │  │
│   │                                                                      │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                      │                                      │
│                                      ▼                                      │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                  Step 4: 다양성 & 정렬                               │  │
│   │                                                                      │  │
│   │  • 카테고리별 최소 1개 보장 (다양성)                                │  │
│   │  • 할인율 × 인기도 복합 정렬                                        │  │
│   │  • 품절 상품 제외                                                   │  │
│   │                                                                      │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                      │                                      │
│                                      ▼                                      │
│   출력: 타임세일 추천 리스트 (할인율, 남은시간, 긴급도 포함)               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.2 타임세일 정렬 옵션

```python
class TimeSaleSorter:
    """
    타임세일 상품 정렬 전략
    """

    def sort_by_recommendation(
        self,
        products: List[Dict],
    ) -> List[Dict]:
        """기본 정렬: 추천 점수순"""
        return sorted(
            products,
            key=lambda x: x['final_score'],
            reverse=True,
        )

    def sort_by_discount(
        self,
        products: List[Dict],
    ) -> List[Dict]:
        """할인율순 정렬"""
        return sorted(
            products,
            key=lambda x: x['discount_rate'],
            reverse=True,
        )

    def sort_by_urgency(
        self,
        products: List[Dict],
    ) -> List[Dict]:
        """긴급도순 정렬 (종료 임박 우선)"""
        return sorted(
            products,
            key=lambda x: x['time_remaining'],
        )

    def sort_by_popularity(
        self,
        products: List[Dict],
    ) -> List[Dict]:
        """인기순 정렬 (주문 수 기반)"""
        return sorted(
            products,
            key=lambda x: x['order_count'],
            reverse=True,
        )

    def sort_hybrid(
        self,
        products: List[Dict],
    ) -> List[Dict]:
        """
        하이브리드 정렬 (추천 + 할인 + 긴급도 복합)

        score = 0.4 × recommendation +
                0.3 × discount_normalized +
                0.3 × urgency_normalized
        """
        # 정규화
        max_rec = max(p['final_score'] for p in products) or 1
        max_disc = max(p['discount_rate'] for p in products) or 1
        max_urg = max(1 / (p['time_remaining'] + 1) for p in products) or 1

        for p in products:
            rec_norm = p['final_score'] / max_rec
            disc_norm = p['discount_rate'] / max_disc
            urg_norm = (1 / (p['time_remaining'] + 1)) / max_urg

            p['hybrid_score'] = (
                0.4 * rec_norm +
                0.3 * disc_norm +
                0.3 * urg_norm
            )

        return sorted(products, key=lambda x: x['hybrid_score'], reverse=True)
```

---

## 6. Recipe 모델 통합

### 6.1 장바구니 페이지 통합

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Cart Page Recommendation Integration                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   장바구니 페이지에서는 두 가지 추천이 동시에 제공됨:                        │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                Section 1: 일반 추천 (전역 모델)                      │  │
│   │                                                                      │  │
│   │  "함께 구매하면 좋은 상품"                                           │  │
│   │                                                                      │  │
│   │  블렌딩: Instacart + SelF + PriceAnomaly                           │  │
│   │  컨텍스트: 장바구니 상품과의 동시구매율 가중치 ↑                    │  │
│   │                                                                      │  │
│   │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐                       │  │
│   │  │ 상품1  │ │ 상품2  │ │ 상품3  │ │ 상품4  │                       │  │
│   │  │        │ │        │ │        │ │        │                       │  │
│   │  │ +담기  │ │ +담기  │ │ +담기  │ │ +담기  │                       │  │
│   │  └────────┘ └────────┘ └────────┘ └────────┘                       │  │
│   │                                                                      │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                Section 2: 레시피 추천 (Recipe 모델)                  │  │
│   │                                                                      │  │
│   │  "이 재료로 만들 수 있는 요리"                                       │  │
│   │                                                                      │  │
│   │  블렌딩: Recipe 모델 독립 동작 (전역 모델과 분리)                   │  │
│   │                                                                      │  │
│   │  ┌────────────────────────────────────────────────────────────┐    │  │
│   │  │                                                             │    │  │
│   │  │  🍳 김치찌개                                                │    │  │
│   │  │                                                             │    │  │
│   │  │  보유: 김치, 돼지고기, 두부                                  │    │  │
│   │  │  부족: 청양고추, 대파                                        │    │  │
│   │  │                                                             │    │  │
│   │  │  ┌──────────┐ ┌──────────┐                                 │    │  │
│   │  │  │청양고추  │ │  대파    │                                 │    │  │
│   │  │  │ 2,500원 │ │ 1,800원 │                                 │    │  │
│   │  │  │ +담기   │ │ +담기   │                                 │    │  │
│   │  │  └──────────┘ └──────────┘                                 │    │  │
│   │  │                                                             │    │  │
│   │  └────────────────────────────────────────────────────────────┘    │  │
│   │                                                                      │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 6.2 Recipe 모델 독립 동작

```python
class RecipeIntegration:
    """
    Recipe 모델은 전역 블렌딩과 독립적으로 동작

    이유:
    1. 입력이 다름 (장바구니 재료 vs 유저 프로파일)
    2. 출력이 다름 (레시피 + Gap 재료 vs 상품 추천)
    3. 사용 시점이 특수함 (장바구니 페이지 전용)
    """

    async def get_cart_recommendations(
        self,
        cart_product_ids: List[int],
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        장바구니 페이지 통합 추천

        Returns:
            {
                'general_recommendations': [...],  # 전역 모델 결과
                'recipe_recommendations': {...},   # Recipe 모델 결과
            }
        """
        # 1. 전역 모델 추천 (병렬 실행)
        general_task = self.get_general_recommendations(
            user_id=user_id,
            cart_product_ids=cart_product_ids,
            page_type='cart',
        )

        # 2. Recipe 모델 추천 (병렬 실행)
        recipe_task = self.recipe_model.get_cart_recipe_recommendations(
            cart_product_ids=cart_product_ids,
        )

        # 병렬 실행
        general_result, recipe_result = await asyncio.gather(
            general_task,
            recipe_task,
        )

        return {
            'general_recommendations': general_result,
            'recipe_recommendations': recipe_result,
        }
```

---

## 7. A/B 테스트 및 탐색

### 7.1 Exploration vs Exploitation

```python
class ExplorationStrategy:
    """
    탐색 vs 활용 전략

    10%의 요청에서 새로운 조합을 시도하여
    모델 개선에 필요한 데이터 수집
    """

    EXPLORATION_RATE = 0.10  # 10% 탐색

    async def get_recommendations(
        self,
        context: RecommendationContext,
        limit: int = 10,
    ) -> List[Dict]:
        """
        탐색/활용 결정 후 추천
        """
        if random.random() < self.EXPLORATION_RATE:
            # 탐색: 다양한 조합 시도
            return await self.explore(context, limit)
        else:
            # 활용: 최적 추천
            return await self.exploit(context, limit)

    async def explore(
        self,
        context: RecommendationContext,
        limit: int,
    ) -> List[Dict]:
        """
        탐색 모드: 다양한 가중치 조합 테스트
        """
        # 랜덤 가중치 변형
        base_weights = self.weight_calculator.get_weights(context)

        # ±20% 변동
        exploration_weights = {
            k: v * (0.8 + random.random() * 0.4)
            for k, v in base_weights.items()
        }

        # 정규화
        total = sum(exploration_weights.values())
        exploration_weights = {
            k: v / total for k, v in exploration_weights.items()
        }

        return await self.blend_with_weights(context, exploration_weights, limit)

    async def exploit(
        self,
        context: RecommendationContext,
        limit: int,
    ) -> List[Dict]:
        """
        활용 모드: 검증된 최적 가중치 사용
        """
        weights = self.weight_calculator.get_weights(context)
        return await self.blend_with_weights(context, weights, limit)
```

### 7.2 성능 추적

```python
class BlendingMetrics:
    """
    블렌딩 성능 추적

    각 가중치 조합별 CTR, CVR 추적하여
    최적 가중치 찾기
    """

    async def log_recommendation(
        self,
        request_id: str,
        user_id: int,
        weights_used: Dict[str, float],
        products_shown: List[int],
        exploration_mode: bool,
    ):
        """추천 로그 저장"""
        await self.db.execute("""
            INSERT INTO recommendation_logs
            (request_id, user_id, weights, products, is_exploration, created_at)
            VALUES ($1, $2, $3, $4, $5, NOW())
        """, request_id, user_id, json.dumps(weights_used),
            products_shown, exploration_mode)

    async def log_interaction(
        self,
        request_id: str,
        product_id: int,
        interaction_type: str,  # 'click', 'cart', 'purchase'
    ):
        """상호작용 로그 저장"""
        await self.db.execute("""
            INSERT INTO interaction_logs
            (request_id, product_id, interaction_type, created_at)
            VALUES ($1, $2, $3, NOW())
        """, request_id, product_id, interaction_type)

    async def calculate_weight_performance(
        self,
        days: int = 7,
    ) -> Dict[str, Dict[str, float]]:
        """
        가중치 조합별 성능 계산

        Returns:
            {
                'instacart_0.7_self_0.2_price_0.1': {
                    'ctr': 0.045,
                    'cvr': 0.012,
                    'sample_size': 10000,
                },
                ...
            }
        """
        # 가중치 조합별 클릭률, 구매전환율 집계
        pass
```

---

## 8. 구현 코드 예시

### 8.1 AdaptiveBlendingOrchestrator

```python
class AdaptiveBlendingOrchestrator:
    """
    적응형 블렌딩 오케스트레이터

    모든 추천 요청의 진입점
    """

    def __init__(
        self,
        db: Database,
        cache: CacheManager,
        instacart_model: InstacartColdStartModel,
        self_model: SelfPersonalizedModel,
        price_model: PriceAnomalyModel,
        recipe_model: RecipePickleModel,
    ):
        self.db = db
        self.cache = cache
        self.instacart_model = instacart_model
        self.self_model = self_model
        self.price_model = price_model
        self.recipe_model = recipe_model

        self.phase_detector = PhaseDetector(db)
        self.weight_calculator = WeightCalculator()
        self.score_fusion = ScoreFusion()
        self.reranker = RealtimeReranker()

    async def recommend(
        self,
        context: RecommendationContext,
        limit: int = 10,
    ) -> RecommendationResult:
        """
        메인 추천 로직
        """
        start_time = time.time()

        # 1. Phase 및 가중치 결정
        phase = await self.phase_detector.get_current_phase()
        weights = self.weight_calculator.get_weights(
            phase=phase,
            user_type=context.user_type,
            page_type=context.page_type,
        )

        # 2. 모델 병렬 실행
        instacart_task = self.instacart_model.recommend(context, limit * 3)
        self_task = self.self_model.recommend(context, limit * 3)
        price_task = self.price_model.recommend(context, limit * 3)

        results = await asyncio.gather(
            instacart_task,
            self_task,
            price_task,
            return_exceptions=True,
        )

        # 3. 결과 추출 (에러 처리)
        instacart_products = results[0].products if not isinstance(results[0], Exception) else []
        self_products = results[1].products if not isinstance(results[1], Exception) else []
        price_products = results[2].products if not isinstance(results[2], Exception) else []

        # 4. 점수 정규화
        instacart_scores = self.normalize_scores(instacart_products)
        self_scores = self.normalize_scores(self_products)
        price_scores = self.normalize_scores(price_products)

        # 5. 점수 융합
        fused_scores = self.score_fusion.fuse(
            instacart_scores=instacart_scores,
            self_scores=self_scores,
            price_scores=price_scores,
            weights=weights,
        )

        # 6. 시간 컨텍스트 부스트
        fused_scores = self.score_fusion.apply_time_boost(
            fused_scores,
            self.get_product_info(fused_scores.keys()),
            context.time_context,
        )

        # 7. 리랭킹 및 다양성
        candidates = self.build_candidates(fused_scores, all_products)
        final_products = await self.reranker.rerank(
            candidates=candidates,
            context=context,
            limit=limit,
        )

        execution_time = (time.time() - start_time) * 1000

        return RecommendationResult(
            products=final_products,
            weights_used=weights,
            phase=phase,
            execution_time_ms=execution_time,
        )
```

---

## 9. 3-Layer 처리 아키텍처

### 9.1 계층별 역할

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    3-Layer Processing Architecture                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │ Layer 1: 오프라인 배치 (Offline Batch)                                │ │
│  │                                                                        │ │
│  │ 실행 주기: 매일 새벽 3시                                               │ │
│  │ 소요 시간: 2~6시간                                                     │ │
│  │                                                                        │ │
│  │ 작업 내용:                                                             │ │
│  │ • SVD/ALS 행렬 분해 → 유저/상품 임베딩 갱신                            │ │
│  │ • 전체 유저별 Top-100 추천 미리 계산                                   │ │
│  │ • 아이템 유사도 행렬 갱신                                              │ │
│  │ • Pickle 파일 생성 및 교체                                             │ │
│  │                                                                        │ │
│  │ 저장소: pred_user_embeddings, pred_item_similarity, *.pkl             │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                      │                                      │
│                                      ▼                                      │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │ Layer 2: 준실시간 갱신 (Near-Realtime Update)                         │ │
│  │                                                                        │ │
│  │ 실행 주기: 매 시간 또는 5분마다                                        │ │
│  │ 소요 시간: 수 분                                                       │ │
│  │                                                                        │ │
│  │ 작업 내용:                                                             │ │
│  │ • 활성 유저 임베딩만 갱신                                              │ │
│  │ • 가격 이상치 캐시 갱신                                                │ │
│  │ • 실시간 트렌드 상품 집계                                              │ │
│  │ • 품절/재입고 상품 반영                                                │ │
│  │                                                                        │ │
│  │ 저장소: pred_price_anomaly_cache, Redis                               │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                      │                                      │
│                                      ▼                                      │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │ Layer 3: 실시간 리랭킹 (Realtime Reranking)                           │ │
│  │                                                                        │ │
│  │ 실행 시점: API 요청 시                                                 │ │
│  │ 목표 응답시간: < 50ms (P95)                                           │ │
│  │                                                                        │ │
│  │ 작업 내용:                                                             │ │
│  │ 1. Precomputed 결과 조회 (5ms)                                        │ │
│  │ 2. 실시간 컨텍스트 점수 조정 (10ms)                                   │ │
│  │    - 장바구니 보완 상품 가중치 ↑                                      │ │
│  │    - 시간대 적합 상품 가중치 ↑                                        │ │
│  │ 3. 필터링 및 정렬 (5ms)                                               │ │
│  │    - 품절 상품 제외, 다양성 보장 (MMR)                                │ │
│  │                                                                        │ │
│  │ 캐시 TTL: Cold user 1시간, Warm user 10분                            │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 10. 배치 작업 스케줄

### 10.1 작업 스케줄 표

| 작업명 | 스케줄 | 설명 | 예상 소요시간 |
|--------|--------|------|--------------|
| **일간 작업** |
| `compute_user_embeddings` | 매일 03:00 | 전체 유저 임베딩 재계산 | 2~4시간 |
| `precompute_recommendations` | 매일 05:00 | 유저별 Top-100 추천 미리 계산 | 4~6시간 |
| `update_item_similarity` | 매일 02:00 | 아이템 유사도 행렬 갱신 | 1~2시간 |
| **시간별 작업** |
| `refresh_price_anomaly_cache` | 매시 정각 | 가격 이상치 캐시 갱신 | 5~10분 |
| `update_active_user_embeddings` | 매시 30분 | 활성 유저 임베딩 갱신 | 10~20분 |
| **빈번한 작업** |
| `cleanup_expired_cache` | 10분마다 | 만료 캐시 정리 | 1~2분 |

---

## 11. 모니터링 및 성능 목표

### 11.1 성능 벤치마크 (SLA)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Performance Benchmarks                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  응답 시간 목표:                                                            │
│  ├─ P50 (중간값):    15ms                                                  │
│  ├─ P95:             50ms                                                  │
│  ├─ P99:             100ms                                                 │
│  └─ 타임아웃:        500ms                                                 │
│                                                                             │
│  캐시 히트율 목표:                                                          │
│  ├─ Redis:           > 80%                                                 │
│  └─ PostgreSQL 캐시: > 50% (Redis 미스 시)                                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 11.2 핵심 모니터링 지표

| 지표 | 설명 | 목표 | 알림 임계값 |
|------|------|------|------------|
| `recommendation_latency_p95` | 추천 응답 시간 95% | < 50ms | > 100ms |
| `recommendation_ctr` | 추천 클릭률 | ≥ 3% | < 1% |
| `recommendation_cvr` | 추천 구매전환율 | ≥ 5% | < 2% |
| `data_confidence` | 현재 데이터 신뢰도 | 모니터링 | - |
| `current_phase` | 현재 Phase | 모니터링 | - |
| `model_weights` | 현재 모델별 가중치 | 모니터링 | - |

---

## 12. 결론

이 블렌딩 전략은 다음을 보장합니다:

1. **유연한 전환**: Phase에 따라 자동으로 모델 가중치 조정
2. **컨텍스트 인식**: 페이지, 시간, 유저 타입별 최적화
3. **품질 유지**: 다양성 보장 (MMR) + 실시간 리랭킹
4. **지속적 개선**: 탐색/활용 전략으로 데이터 수집 및 최적화
5. **프로덕션 성능**: 3-Layer 아키텍처로 < 50ms 응답 보장

---

*문서 끝*
