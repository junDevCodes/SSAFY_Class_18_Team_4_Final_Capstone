# SelF 추천 시스템 아키텍처 설계서

> **문서 버전**: v3.1.0
> **최종 수정일**: 2025년 12월 10일
> **담당**: pred/ 서비스 (FastAPI 기반 ML 추천 서버)

---

## 1. 개요

### 1.1 목적
SelF 플랫폼의 개인화 추천 시스템을 설계합니다. 4개의 독립적인 모델이 조화롭게 작동하여 사용자 맥락에 맞는 최적의 추천을 제공합니다.

### 1.2 핵심 모델 (4개)

| 모델 | 코드명 | 목적 | 데이터 소스 |
|------|--------|------|-------------|
| 🥶 콜드스타트 추천 | `InstacartColdStart` | 신규 사용자 추천 | Instacart Kaggle 데이터셋 (사전 집계) |
| 🔥 개인화 추천 | `SelfPersonalized` | 기존 사용자 추천 | SelF 자체 행동 데이터 |
| 💰 가격 이상치 추천 | `PriceAnomaly` | 급할인 상품 탐지 | `product_price_histories` 테이블 |
| 🍳 레시피 갭필링 | `RecipeGapFilling` | 장바구니 기반 재료 추천 | 만개의레시피 크롤링 데이터 |

### 1.3 모델 평가 지표

추천 시스템의 품질을 측정하기 위한 지표:

| 지표 | 설명 | 목표값 | 측정 주기 |
|------|------|--------|----------|
| **Precision@10** | 상위 10개 추천 중 클릭/구매된 비율 | ≥ 0.15 | 일간 |
| **Recall@20** | 실제 관심 상품 중 상위 20개에 포함된 비율 | ≥ 0.30 | 일간 |
| **NDCG@10** | 순위 품질 (높은 순위에 좋은 상품) | ≥ 0.40 | 일간 |
| **CTR (클릭률)** | 추천 노출 대비 클릭 비율 | ≥ 3% | 실시간 |
| **CVR (구매전환율)** | 클릭 대비 구매 비율 | ≥ 5% | 일간 |
| **Coverage** | 전체 상품 중 추천된 상품 비율 | ≥ 60% | 주간 |
| **Diversity** | 추천 목록 내 카테고리 다양성 | ≥ 0.70 | 일간 |

**평가 데이터 수집:**
```sql
-- 추천 로그 테이블 (기존 테이블 아님, 별도 로깅)
-- 추천 노출, 클릭, 구매 이벤트를 기록하여 평가 지표 산출
-- pred 서비스 내부 로깅 또는 별도 분석 파이프라인에서 처리
```

---

## 2. 시스템 아키텍처

### 2.1 전체 구조

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Frontend (Vue 3)                                │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Backend (Django + DRF)                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ products/    │  │ orders/      │  │ authentication│  │ sellers/     │    │
│  │ views.py     │  │ views.py     │  │ views.py      │  │ views.py     │    │
│  └──────┬───────┘  └──────┬───────┘  └──────┬────────┘  └──────┬───────┘    │
│         └──────────────────┴─────────────────┴─────────────────┘            │
│                                      │                                       │
│                         ┌────────────▼────────────┐                         │
│                         │    pred_client.py       │                         │
│                         │  (Pred API 클라이언트)   │                         │
│                         └────────────┬────────────┘                         │
└──────────────────────────────────────┼──────────────────────────────────────┘
                                       │ HTTP/JSON
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Pred Service (FastAPI)                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         API Layer (api/)                             │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐    │   │
│  │  │ /recommend │  │ /price     │  │ /recipe    │  │ /health    │    │   │
│  │  │ /personal  │  │ /anomaly   │  │ /gap-fill  │  │ /metrics   │    │   │
│  │  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘  └────────────┘    │   │
│  └────────┼───────────────┼───────────────┼────────────────────────────┘   │
│           └───────────────┼───────────────┘                                │
│                           ▼                                                 │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     Orchestrator Layer (core/)                       │   │
│  │              ┌─────────────────────────────────┐                     │   │
│  │              │     RecommendationOrchestrator   │                     │   │
│  │              │  - 모델 선택 로직                 │                     │   │
│  │              │  - 결과 병합/순위화               │                     │   │
│  │              │  - 폴백 처리                     │                     │   │
│  │              └───────────────┬─────────────────┘                     │   │
│  └──────────────────────────────┼──────────────────────────────────────┘   │
│                                 ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      Model Layer (ml/models/)                        │   │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌─────────────┐ │   │
│  │  │ Instacart    │ │ Self         │ │ Price        │ │ Recipe      │ │   │
│  │  │ ColdStart    │ │ Personalized │ │ Anomaly      │ │ GapFilling  │ │   │
│  │  │              │ │              │ │              │ │             │ │   │
│  │  │ • 사전집계   │ │ • BERT 임베딩│ │ • Z-Score    │ │ • Ingredient│ │   │
│  │  │   테이블    │ │ • Item-CF    │ │ • IQR        │ │   Matching  │ │   │
│  │  │ • 시간대패턴│ │ • 컨텐츠기반 │ │ • MA-based   │ │ • Recipe    │ │   │
│  │  └──────┬───────┘ └──────┬───────┘ └──────┬───────┘ │   Matching  │ │   │
│  └─────────┼────────────────┼────────────────┼─────────┴──────┬──────┴─┘   │
│            └────────────────┴────────────────┴────────────────┘            │
│                                      │                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      Data Layer (data/)                              │   │
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐         │   │
│  │  │ PostgreSQL     │  │ Redis Cache    │  │ File Storage   │         │   │
│  │  │ (asyncpg)      │  │ (추천캐시)     │  │ (모델파일)     │         │   │
│  │  └────────────────┘  └────────────────┘  └────────────────┘         │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 폴백 및 장애 대응 전략

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           장애 대응 폴백 체인                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1단계: 정상 추천 흐름                                                      │
│  ─────────────────────                                                      │
│  사용자 요청 → 오케스트레이터 → 개인화 모델 → Redis 캐시 저장 → 응답       │
│                                                                             │
│  2단계: 모델 장애 시                                                        │
│  ─────────────────────                                                      │
│  개인화 모델 실패 → 콜드스타트 모델로 폴백 → 응답                          │
│  콜드스타트 모델 실패 → 인기도 기반 폴백 → 응답                            │
│                                                                             │
│  3단계: Redis 장애 시                                                       │
│  ─────────────────────                                                      │
│  Redis 연결 실패 → PostgreSQL pred_recommendation_cache 조회 → 응답        │
│  캐시 모두 실패 → 실시간 계산 (성능 저하 감수)                              │
│                                                                             │
│  4단계: DB 장애 시                                                          │
│  ─────────────────────                                                      │
│  PostgreSQL 연결 실패 → 최근 캐시된 인기 상품 목록 반환                     │
│  모든 것 실패 → 503 Service Unavailable + 빈 추천 목록                     │
│                                                                             │
│  타임아웃 설정:                                                             │
│  - 개인화 모델: 200ms                                                       │
│  - 콜드스타트 모델: 100ms                                                   │
│  - 가격 이상치: 150ms                                                       │
│  - 레시피 갭필링: 200ms                                                     │
│  - 전체 API 응답: 500ms                                                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.3 pred/ 폴더 구조

```
pred/
├── main.py                          # FastAPI 앱 진입점
├── requirements.txt                 # Python 의존성
├── Dockerfile                       # 컨테이너 빌드
│
├── api/                             # API 레이어
│   ├── __init__.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── recommend.py             # 통합 추천 엔드포인트
│   │   ├── price.py                 # 가격 이상치 엔드포인트
│   │   ├── recipe.py                # 레시피 갭필링 엔드포인트
│   │   └── health.py                # 헬스체크/메트릭스
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── request.py               # 요청 DTO
│   │   └── response.py              # 응답 DTO
│   └── dependencies.py              # FastAPI 의존성 주입
│
├── core/                            # 핵심 인프라
│   ├── __init__.py
│   ├── config.py                    # 환경 설정
│   ├── database.py                  # DB 연결 (asyncpg)
│   ├── cache.py                     # Redis 캐시
│   ├── logging.py                   # 로깅 설정
│   ├── exceptions.py                # 커스텀 예외
│   └── orchestrator.py              # 모델 오케스트레이터
│
├── ml/                              # 머신러닝 레이어
│   ├── __init__.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py                  # 모델 베이스 클래스
│   │   ├── instacart_coldstart.py   # 🥶 콜드스타트 모델
│   │   ├── self_personalized.py     # 🔥 개인화 모델
│   │   ├── price_anomaly.py         # 💰 가격 이상치 모델
│   │   └── recipe_gapfilling.py     # 🍳 레시피 갭필링 모델
│   ├── embeddings/
│   │   ├── __init__.py
│   │   └── text_embedding.py        # BERT 기반 텍스트 임베딩
│   └── utils/
│       ├── __init__.py
│       ├── similarity.py            # 유사도 계산
│       └── ranking.py               # 랭킹 알고리즘
│
├── data/                            # 데이터 레이어
│   ├── __init__.py
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── product_repo.py          # 상품 데이터 접근
│   │   ├── user_repo.py             # 사용자 데이터 접근
│   │   ├── price_repo.py            # 가격 이력 접근
│   │   ├── recipe_repo.py           # 레시피 데이터 접근
│   │   └── instacart_repo.py        # Instacart 사전집계 접근
│   └── loaders/
│       ├── __init__.py
│       ├── instacart_loader.py      # Instacart CSV → 사전집계 로더
│       └── recipe_loader.py         # 레시피 크롤링 로더
│
├── batch/                           # 배치 처리
│   ├── __init__.py
│   ├── aggregate_instacart.py       # Instacart 사전 집계 배치
│   ├── update_embeddings.py         # 임베딩 갱신
│   ├── update_anomaly_cache.py      # 가격 이상치 캐시 갱신
│   └── scheduler.py                 # 스케줄러 (APScheduler)
│
└── tests/                           # 테스트
    ├── __init__.py
    ├── conftest.py
    ├── test_models/
    ├── test_api/
    └── test_data/
```

---

## 3. 4개 모델 상세 설계

### 3.1 🥶 InstacartColdStart (콜드스타트 추천)

#### 목적
- 행동 데이터가 없는 신규 사용자에게 추천 제공
- Instacart 데이터에서 **사전 집계된 시간대/요일별 인기 패턴** 활용

#### 핵심 설계 원칙

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Instacart 데이터 활용 전략 (수정됨)                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ❌ 기존 문제점:                                                            │
│  ─────────────────                                                          │
│  - 32M 레코드 실시간 조회 → 성능 불가                                       │
│  - 미국 상품 → 한국 상품 직접 전이 → 논리적 결함                            │
│  - Prod2Vec 임베딩 전이 → 언어/문화 차이로 의미 없음                        │
│                                                                             │
│  ✅ 수정된 접근법:                                                          │
│  ─────────────────                                                          │
│  1. Instacart 데이터는 "소비 패턴"만 추출                                   │
│     - 시간대별 (아침/점심/저녁/야식) 카테고리 선호도                        │
│     - 요일별 (평일/주말) 카테고리 선호도                                    │
│     - 재구매율 높은 카테고리 패턴                                           │
│                                                                             │
│  2. 사전 집계 테이블로 변환 (배치 처리)                                     │
│     - pred_instacart_time_patterns: 시간대별 카테고리 인기도                │
│     - pred_instacart_category_mapping: Instacart→SelF 카테고리 매핑         │
│                                                                             │
│  3. 실시간 쿼리는 사전 집계 테이블만 조회 (< 50ms)                          │
│                                                                             │
│  4. 상품 레벨 매핑은 선택적                                                 │
│     - 카테고리 수준에서 SelF 상품 인기도로 보정                             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### 데이터 소스
```
Instacart Kaggle Dataset (3.4M orders, 206K users, 49K products)
├── orders.csv           # 주문 메타데이터
├── order_products_prior.csv  # 이전 주문 상품
├── order_products_train.csv  # 학습용 주문 상품
├── products.csv         # 상품 정보
├── aisles.csv          # 통로(소분류)
└── departments.csv      # 부서(대분류)

    ↓ (배치 처리로 사전 집계)

pred_instacart_time_patterns (신규 - 사전 집계 테이블)
├── time_slot (morning/lunch/dinner/night)
├── day_type (weekday/weekend)
├── category_id (SelF 카테고리와 매핑됨)
├── popularity_score
└── reorder_rate
```

#### 알고리즘
```python
class InstacartColdStart:
    """콜드스타트 추천 모델

    핵심 변경사항:
    - 32M 레코드 실시간 조회 제거
    - 사전 집계된 시간대/요일별 패턴 테이블 활용
    - 카테고리 수준 매핑 (상품 직접 매핑 아님)
    """

    def __init__(self):
        self.time_patterns = None       # 사전 집계된 시간대별 패턴
        self.category_mapping = None     # Instacart→SelF 카테고리 매핑

    async def recommend(self, context: dict) -> List[int]:
        """콜드스타트 추천 생성

        Args:
            context: {
                'category_id': Optional[int],  # 현재 카테고리
                'time_slot': str,              # morning/lunch/dinner/night
                'day_type': str,               # weekday/weekend
            }

        Returns:
            추천 상품 ID 리스트

        성능: < 50ms (사전 집계 테이블 조회)
        """
        # 1. 시간대/요일 기반 카테고리 선호도 조회 (사전 집계 테이블)
        preferred_categories = await self._get_time_based_categories(context)

        # 2. 해당 카테고리의 SelF 인기 상품 조회
        candidates = await self._get_popular_products_by_categories(
            preferred_categories,
            context.get('category_id')
        )

        # 3. 다양성 보장 (MMR)
        return self._diversify(candidates, top_k=20)

    async def _get_time_based_categories(self, context: dict) -> List[dict]:
        """사전 집계된 시간대별 카테고리 선호도 조회

        쿼리 대상: pred_instacart_time_patterns (수백 행)
        예상 성능: < 10ms
        """
        query = """
            SELECT self_category_id, popularity_score, reorder_rate
            FROM pred_instacart_time_patterns
            WHERE time_slot = $1 AND day_type = $2
            ORDER BY popularity_score DESC
            LIMIT 10
        """
        return await self.db.fetch(query, context['time_slot'], context['day_type'])

    async def _get_popular_products_by_categories(
        self,
        categories: List[dict],
        current_category_id: Optional[int]
    ) -> List[dict]:
        """카테고리별 SelF 인기 상품 조회

        쿼리 대상: products + product_stats (기존 테이블)
        예상 성능: < 30ms
        """
        category_ids = [c['self_category_id'] for c in categories]

        # 현재 카테고리 있으면 가중치 부여
        if current_category_id and current_category_id in category_ids:
            category_ids.remove(current_category_id)
            category_ids.insert(0, current_category_id)

        query = """
            SELECT p.id, p.name, p.price, p.category_id,
                   ps.view_count, ps.order_event_count
            FROM products p
            JOIN product_stats ps ON p.id = ps.product_id
            WHERE p.category_id = ANY($1)
              AND p.status = 'active'
            ORDER BY ps.order_event_count DESC, ps.view_count DESC
            LIMIT 100
        """
        return await self.db.fetch(query, category_ids)
```

#### 사용 시점
- 비로그인 사용자의 메인 페이지 방문
- 신규 가입 직후 (행동 데이터 부족)
- 카테고리 페이지 초기 진입

---

### 3.2 🔥 SelfPersonalized (개인화 추천)

#### 목적
- SelF 플랫폼 내 사용자 행동 기반 개인화 추천
- 조회/장바구니/구매 이력 기반 추천

#### 데이터 소스
```sql
-- 주요 테이블 (기존 SelF 백엔드)
user_product_stats     -- 사용자×상품 상호작용 집계
product_stats          -- 상품별 글로벌 통계
orders / order_items   -- 구매 이력
carts                  -- 장바구니
wishlists              -- 찜 목록
```

#### 알고리즘
```python
class SelfPersonalized:
    """SelF 데이터 기반 개인화 모델

    하이브리드 접근:
    1. Item-based Collaborative Filtering (상품-상품 유사도)
    2. Content-based (BERT 텍스트 임베딩)
    3. 최근 행동 기반 가중치
    """

    def __init__(self):
        self.item_similarity = None      # 상품-상품 유사도 행렬 (배치 계산)
        self.bert_embeddings = None       # 상품 텍스트 임베딩

    async def recommend(self, user_id: int, context: dict) -> List[int]:
        """개인화 추천 생성

        Args:
            user_id: 사용자 ID
            context: {
                'recent_views': List[int],      # 최근 조회 상품
                'cart_items': List[int],        # 장바구니 상품
                'exclude_purchased': bool,      # 구매 상품 제외
            }

        Returns:
            추천 상품 ID 리스트 (점수순)
        """
        scores = {}

        # 1. 최근 조회/장바구니 기반 유사 상품 (Item-CF)
        seed_items = (context.get('recent_views', []) +
                      context.get('cart_items', []))[:10]

        if seed_items:
            cf_scores = await self._get_similar_items(seed_items)
            scores = cf_scores
        else:
            # 시드 상품 없으면 사용자 이력 기반
            cf_scores = await self._get_user_history_based(user_id)
            scores = cf_scores

        # 2. 구매 이력 제외
        if context.get('exclude_purchased', True):
            scores = await self._exclude_purchased(user_id, scores)

        return self._rank_and_filter(scores, top_k=20)

    async def _get_similar_items(self, seed_items: List[int]) -> dict:
        """시드 상품 기반 유사 상품 조회

        사전 계산된 상품-상품 유사도 행렬 활용
        """
        # 배치로 계산된 유사도 테이블 조회
        query = """
            SELECT target_product_id, AVG(similarity_score) as score
            FROM pred_item_similarity
            WHERE source_product_id = ANY($1)
              AND target_product_id != ALL($1)
            GROUP BY target_product_id
            ORDER BY score DESC
            LIMIT 50
        """
        rows = await self.db.fetch(query, seed_items)
        return {row['target_product_id']: row['score'] for row in rows}
```

#### 웜/콜드 판단 기준 (강화됨)
```python
def classify_user(user_id: int) -> str:
    """사용자 분류 (cold/lukewarm/warm)

    기준 강화:
    - cold: 의미있는 개인화 불가
    - lukewarm: 제한적 개인화 (컨텐츠 기반 혼합)
    - warm: 완전한 개인화 가능
    """
    stats = get_user_stats(user_id)

    # 구매 이력이 있으면 warm
    if stats['order_count'] >= 1:
        return 'warm'

    # 장바구니 3회 이상이면 warm
    if stats['cart_count'] >= 3:
        return 'warm'

    # 조회 10회 이상 + 장바구니 1회 이상이면 lukewarm
    if stats['view_count'] >= 10 and stats['cart_count'] >= 1:
        return 'lukewarm'

    # 그 외는 cold
    return 'cold'


def get_model_for_user(user_type: str):
    """사용자 타입별 모델 선택"""
    if user_type == 'warm':
        return SelfPersonalized()  # 완전한 개인화
    elif user_type == 'lukewarm':
        return HybridModel()       # 개인화 + 콜드스타트 혼합
    else:
        return InstacartColdStart()  # 콜드스타트
```

---

### 3.3 💰 PriceAnomaly (가격 이상치 추천)

#### 목적
- 급격한 가격 하락(할인) 상품 탐지
- `product_price_histories` 테이블의 가격 변동 분석

#### 데이터 소스
```sql
-- product_price_histories 테이블 구조 (기존)
id                  -- PK
product_id          -- 상품 FK
price               -- 현재 가격
original_price      -- 원가
previous_price      -- 이전 가격
price_change        -- 변동액 (음수 = 인하)
price_change_rate   -- 변동률 (%)
is_current          -- 현재 가격 여부
recorded_at         -- 기록 시각
source              -- 변경 출처
```

#### 알고리즘 (3가지 탐지 방법)
```python
class PriceAnomaly:
    """가격 이상치 탐지 모델

    3가지 탐지 방법의 앙상블:
    1. Z-Score: 표준편차 기반
    2. IQR: 사분위수 기반
    3. Moving Average: 이동평균 대비
    """

    def __init__(self):
        self.z_threshold = -2.0        # Z-Score 임계값
        self.iqr_multiplier = 1.5      # IQR 배수
        self.ma_window = 7             # 이동평균 윈도우 (일)
        self.ma_threshold = -0.15      # MA 대비 15% 이상 하락

    async def detect_anomalies(self, category_id: Optional[int] = None) -> List[dict]:
        """가격 이상치 상품 탐지

        캐시 우선 전략:
        1. pred_price_anomaly_cache 조회 (TTL 1시간)
        2. 캐시 미스 시 실시간 계산 후 캐시 저장

        Returns:
            [
                {
                    'product_id': 123,
                    'current_price': 9000,
                    'previous_price': 15000,
                    'price_change_rate': -40.0,
                    'anomaly_score': 0.85,
                    'detection_methods': ['zscore', 'iqr'],
                }
            ]
        """
        # 캐시 조회
        cached = await self._get_cached_anomalies(category_id)
        if cached:
            return cached

        # 실시간 계산 (캐시 미스)
        results = await self._calculate_anomalies(category_id)

        # 캐시 저장 (비동기, 응답 지연 없음)
        asyncio.create_task(self._save_to_cache(results, category_id))

        return results

    async def _calculate_anomalies(self, category_id: Optional[int]) -> List[dict]:
        """실시간 이상치 계산

        최적화:
        - is_current=TRUE인 레코드만 조회 (인덱스 활용)
        - 최근 30일 이력만 분석
        - 배치 쿼리로 상품별 통계 한 번에 계산
        """
        query = """
            WITH recent_prices AS (
                SELECT
                    product_id,
                    price,
                    previous_price,
                    price_change_rate,
                    recorded_at,
                    -- 30일 이력 기반 통계
                    AVG(price) OVER w AS avg_price,
                    STDDEV(price) OVER w AS stddev_price,
                    PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY price) OVER w AS q1,
                    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY price) OVER w AS q3
                FROM product_price_histories
                WHERE recorded_at >= NOW() - INTERVAL '30 days'
                  AND ($1::bigint IS NULL OR product_id IN (
                      SELECT id FROM products WHERE category_id = $1
                  ))
                WINDOW w AS (PARTITION BY product_id)
            )
            SELECT DISTINCT ON (product_id)
                product_id,
                price AS current_price,
                previous_price,
                price_change_rate,
                avg_price,
                stddev_price,
                q1, q3,
                -- Z-Score 계산
                CASE WHEN stddev_price > 0
                    THEN (price - avg_price) / stddev_price
                    ELSE 0
                END AS z_score,
                -- IQR 하한 계산
                q1 - 1.5 * (q3 - q1) AS iqr_lower
            FROM recent_prices rp
            JOIN product_price_histories pph
                ON rp.product_id = pph.product_id AND pph.is_current = TRUE
            WHERE rp.price < rp.avg_price  -- 가격 하락만
            ORDER BY product_id, recorded_at DESC
        """
        rows = await self.db.fetch(query, category_id)

        results = []
        for row in rows:
            methods = []
            scores = []

            # Z-Score 판정
            if row['z_score'] < self.z_threshold:
                methods.append('zscore')
                scores.append(min(abs(row['z_score']) / 3, 1.0))

            # IQR 판정
            if row['current_price'] < row['iqr_lower']:
                methods.append('iqr')
                iqr = row['q3'] - row['q1']
                if iqr > 0:
                    scores.append(min((row['iqr_lower'] - row['current_price']) / iqr, 1.0))

            # MA 판정 (price_change_rate 활용)
            if row['price_change_rate'] and row['price_change_rate'] < self.ma_threshold * 100:
                methods.append('ma')
                scores.append(min(abs(row['price_change_rate']) / 50, 1.0))

            if methods:
                anomaly_score = sum(scores) / len(scores)
                anomaly_score *= (1 + 0.1 * len(methods))  # 다중 탐지 보너스

                results.append({
                    'product_id': row['product_id'],
                    'current_price': row['current_price'],
                    'previous_price': row['previous_price'],
                    'price_change_rate': row['price_change_rate'],
                    'anomaly_score': min(anomaly_score, 1.0),
                    'detection_methods': methods,
                })

        return sorted(results, key=lambda x: x['anomaly_score'], reverse=True)
```

#### 사용 시점
- 메인 페이지 "오늘의 특가" 섹션
- 카테고리 페이지 상단 배너
- 푸시 알림 (관심 상품 급할인)

---

### 3.4 🍳 RecipeGapFilling (레시피 갭필링)

#### 목적
- 장바구니 상품 기반 레시피 매칭
- 부족한 재료 추천으로 구매 전환율 향상

#### 데이터 소스
```
만개의레시피 (10000recipe.com) 크롤링 데이터
├── recipes.json         # 레시피 메타데이터
├── ingredients.json     # 재료 목록
└── steps.json          # 조리 단계

→ pred_recipes, pred_ingredients, pred_recipe_ingredients 테이블로 적재
```

#### 알고리즘
```python
class RecipeGapFilling:
    """레시피 기반 갭필링 모델

    프로세스:
    1. 장바구니 상품 → 재료 추출 (pred_ingredient_products 매핑)
    2. 재료 → 매칭 레시피 탐색 (pred_recipe_ingredients)
    3. 레시피 → 부족 재료 → 상품 매핑
    """

    def __init__(self):
        self.ingredient_dict = None      # 재료 사전 (캐시)

    async def find_gap_products(self, cart_items: List[int]) -> List[dict]:
        """갭필링 상품 추천

        Args:
            cart_items: 장바구니 상품 ID 리스트

        Returns:
            [
                {
                    'product_id': 456,
                    'product_name': '대파',
                    'reason': '된장찌개 재료',
                    'recipe_id': 789,
                    'recipe_name': '된장찌개',
                    'recipe_rating': 4.5,
                    'match_score': 0.8,
                }
            ]
        """
        if not cart_items:
            return []

        # 1. 장바구니 → 재료 추출 (DB 매핑 테이블 활용)
        cart_ingredients = await self._extract_ingredients_from_products(cart_items)

        if not cart_ingredients:
            return []

        # 2. 재료 조합 → 레시피 매칭
        matched_recipes = await self._match_recipes(cart_ingredients)

        # 3. 부족 재료 → 상품 추천
        gap_products = await self._get_gap_products(
            matched_recipes, cart_ingredients, cart_items
        )

        return gap_products[:10]

    async def _extract_ingredients_from_products(
        self, product_ids: List[int]
    ) -> List[int]:
        """상품 → 재료 매핑 (DB 기반)

        pred_ingredient_products 테이블 활용
        """
        query = """
            SELECT DISTINCT ingredient_id
            FROM pred_ingredient_products
            WHERE product_id = ANY($1)
              AND is_active = TRUE
              AND similarity_score >= 0.7
        """
        rows = await self.db.fetch(query, product_ids)
        return [row['ingredient_id'] for row in rows]

    async def _match_recipes(self, ingredient_ids: List[int]) -> List[dict]:
        """재료로 레시피 매칭

        매칭 기준:
        - 최소 2개 이상 재료 일치
        - 일치율 30% 이상
        - 레시피 평점으로 순위 보정
        """
        query = """
            WITH recipe_matches AS (
                SELECT
                    r.id AS recipe_id,
                    r.name AS recipe_name,
                    r.rating,
                    r.thumbnail_url,
                    COUNT(ri.ingredient_id) AS matched_count,
                    (SELECT COUNT(*) FROM pred_recipe_ingredients
                     WHERE recipe_id = r.id) AS total_ingredients
                FROM pred_recipes r
                JOIN pred_recipe_ingredients ri ON r.id = ri.recipe_id
                WHERE ri.ingredient_id = ANY($1)
                  AND r.is_active = TRUE
                GROUP BY r.id, r.name, r.rating, r.thumbnail_url
            )
            SELECT *,
                   matched_count::float / NULLIF(total_ingredients, 0) AS match_ratio
            FROM recipe_matches
            WHERE matched_count >= 2
              AND matched_count::float / NULLIF(total_ingredients, 0) >= 0.3
            ORDER BY match_ratio * 0.6 + rating / 5 * 0.4 DESC
            LIMIT 5
        """
        return await self.db.fetch(query, ingredient_ids)

    async def _get_gap_products(
        self,
        recipes: List[dict],
        owned_ingredients: List[int],
        owned_products: List[int]
    ) -> List[dict]:
        """부족 재료 → 상품 추천"""
        if not recipes:
            return []

        recipe_ids = [r['recipe_id'] for r in recipes]

        query = """
            SELECT DISTINCT ON (ip.product_id)
                ip.product_id,
                p.name AS product_name,
                p.price,
                i.name AS ingredient_name,
                r.id AS recipe_id,
                r.name AS recipe_name,
                r.rating AS recipe_rating,
                ri.is_main,
                ip.similarity_score
            FROM pred_recipe_ingredients ri
            JOIN pred_recipes r ON ri.recipe_id = r.id
            JOIN pred_ingredients i ON ri.ingredient_id = i.id
            JOIN pred_ingredient_products ip ON i.id = ip.ingredient_id
            JOIN products p ON ip.product_id = p.id
            WHERE ri.recipe_id = ANY($1)
              AND ri.ingredient_id != ALL($2)
              AND ip.product_id != ALL($3)
              AND ip.is_active = TRUE
              AND p.status = 'active'
            ORDER BY ip.product_id,
                     ri.is_main DESC,
                     ip.similarity_score DESC,
                     r.rating DESC
        """
        rows = await self.db.fetch(query, recipe_ids, owned_ingredients, owned_products)

        return [
            {
                'product_id': row['product_id'],
                'product_name': row['product_name'],
                'price': row['price'],
                'reason': f"{row['recipe_name']} 재료 ({row['ingredient_name']})",
                'recipe_id': row['recipe_id'],
                'recipe_name': row['recipe_name'],
                'recipe_rating': float(row['recipe_rating']) if row['recipe_rating'] else 0,
                'match_score': float(row['similarity_score']) if row['similarity_score'] else 0,
            }
            for row in rows
        ]
```

#### 재료 매핑 테이블 설계

재료-상품 매핑은 DB 테이블 기반으로 관리:

```sql
-- pred_ingredient_products 테이블
-- 재료 ↔ SelF 상품 매핑 (배치로 사전 생성)

-- 매핑 방법:
-- 1. 정확 매칭: 재료명이 상품명에 포함 (similarity_score = 1.0)
-- 2. 부분 매칭: 형태소 분석 후 핵심어 매칭 (similarity_score = 0.7~0.9)
-- 3. 카테고리 매칭: 같은 카테고리 내 대표 상품 (similarity_score = 0.5~0.7)

-- 가공식품 처리:
-- 고추장, 된장 등은 '양념' 재료로 분류
-- is_processed = TRUE 플래그로 구분
-- 레시피에서 필수 재료(is_required)인 경우 포함
```

---

## 4. 오케스트레이터 설계

### 4.1 모델 선택 로직

```python
class RecommendationOrchestrator:
    """추천 모델 오케스트레이터

    맥락에 따라 적절한 모델 조합을 선택하고 결과를 병합
    타임아웃 및 폴백 처리 포함
    """

    def __init__(self):
        self.instacart_model = InstacartColdStart()
        self.self_model = SelfPersonalized()
        self.price_model = PriceAnomaly()
        self.recipe_model = RecipeGapFilling()

        # 타임아웃 설정 (ms)
        self.timeouts = {
            'instacart': 100,
            'self': 200,
            'price': 150,
            'recipe': 200,
        }

    async def recommend(self, request: RecommendRequest) -> RecommendResponse:
        """통합 추천 생성

        Args:
            request: {
                'user_id': Optional[int],
                'page_type': str,           # home, category, product_detail, cart
                'category_id': Optional[int],
                'product_id': Optional[int],
                'cart_items': List[int],
                'limit': int,
            }
        """
        page_type = request.page_type
        user_id = request.user_id

        # 사용자 분류
        user_type = classify_user(user_id) if user_id else 'cold'

        # 페이지별 모델 조합 선택
        model_config = self._get_model_config(page_type, user_type)

        # 병렬 실행 (타임아웃 포함)
        results = await self._execute_models_parallel(model_config, request)

        # 결과 병합 및 순위화
        return self._merge_results(results, model_config, limit=request.limit)

    async def _execute_models_parallel(
        self, model_config: dict, request: RecommendRequest
    ) -> dict:
        """모델 병렬 실행 (타임아웃 + 폴백)"""
        tasks = {}
        results = {}

        for model_name, weight in model_config.items():
            if weight > 0:
                tasks[model_name] = self._execute_with_timeout(
                    model_name, request, self.timeouts[model_name]
                )

        # 병렬 실행
        task_results = await asyncio.gather(*tasks.values(), return_exceptions=True)

        for model_name, result in zip(tasks.keys(), task_results):
            if isinstance(result, Exception):
                # 타임아웃 또는 에러 → 빈 결과
                logger.warning(f"{model_name} 모델 실패: {result}")
                results[model_name] = []
            else:
                results[model_name] = result

        return results

    def _get_model_config(self, page_type: str, user_type: str) -> dict:
        """페이지/사용자 타입별 모델 가중치"""

        configs = {
            'home': {
                'warm': {'self': 0.5, 'price': 0.3, 'recipe': 0.2},
                'lukewarm': {'self': 0.3, 'instacart': 0.3, 'price': 0.25, 'recipe': 0.15},
                'cold': {'instacart': 0.5, 'price': 0.4, 'recipe': 0.1},
            },
            'category': {
                'warm': {'self': 0.6, 'price': 0.4},
                'lukewarm': {'self': 0.4, 'instacart': 0.2, 'price': 0.4},
                'cold': {'instacart': 0.4, 'price': 0.6},
            },
            'product_detail': {
                'warm': {'self': 0.8, 'price': 0.2},
                'lukewarm': {'self': 0.5, 'instacart': 0.3, 'price': 0.2},
                'cold': {'instacart': 0.7, 'price': 0.3},
            },
            'cart': {
                'warm': {'recipe': 0.6, 'self': 0.3, 'price': 0.1},
                'lukewarm': {'recipe': 0.6, 'self': 0.2, 'price': 0.2},
                'cold': {'recipe': 0.7, 'price': 0.3},
            },
        }

        return configs.get(page_type, configs['home']).get(user_type, configs['home']['cold'])
```

### 4.2 페이지별 모델 사용 매핑

| 페이지 | 웜 유저 | 루크웜 유저 | 콜드 유저 | 비고 |
|--------|---------|------------|-----------|------|
| 메인 홈 | Self(50%) + Price(30%) + Recipe(20%) | Self(30%) + Instacart(30%) + Price(25%) + Recipe(15%) | Instacart(50%) + Price(40%) + Recipe(10%) | 개인화 + 특가 + 레시피 |
| 카테고리 | Self(60%) + Price(40%) | Self(40%) + Instacart(20%) + Price(40%) | Instacart(40%) + Price(60%) | 카테고리 내 추천 |
| 상품 상세 | Self(80%) + Price(20%) | Self(50%) + Instacart(30%) + Price(20%) | Instacart(70%) + Price(30%) | 연관 상품 |
| 장바구니 | Recipe(60%) + Self(30%) + Price(10%) | Recipe(60%) + Self(20%) + Price(20%) | Recipe(70%) + Price(30%) | 갭필링 중심 |
| 검색 결과 | Self(40%) + Price(60%) | Self(30%) + Price(70%) | Price(100%) | 검색어 기반 특가 |
| 타임딜 | Price(100%) | Price(100%) | Price(100%) | 가격 이상치만 |

---

## 5. API 명세

### 5.1 통합 추천 API

```
POST /api/recommend
```

**Request:**
```json
{
    "user_id": 123,
    "page_type": "home",
    "category_id": null,
    "product_id": null,
    "cart_items": [1, 2, 3],
    "limit": 20,
    "context": {
        "time_slot": "dinner",
        "day_type": "weekday"
    }
}
```

**Response:**
```json
{
    "recommendations": [
        {
            "product_id": 456,
            "score": 0.95,
            "source": "self",
            "reason": "최근 조회 상품과 유사"
        },
        {
            "product_id": 789,
            "score": 0.88,
            "source": "price",
            "reason": "40% 급할인 중",
            "price_info": {
                "current_price": 9000,
                "previous_price": 15000,
                "discount_rate": -40
            }
        },
        {
            "product_id": 321,
            "score": 0.75,
            "source": "recipe",
            "reason": "된장찌개 재료",
            "recipe_info": {
                "recipe_id": 999,
                "recipe_name": "된장찌개"
            }
        }
    ],
    "metadata": {
        "model_used": ["self", "price", "recipe"],
        "user_type": "warm",
        "processing_time_ms": 45
    }
}
```

### 5.2 가격 이상치 API

```
GET /api/price/anomalies?category_id=1&limit=10
```

**Response:**
```json
{
    "anomalies": [
        {
            "product_id": 456,
            "product_name": "유기농 사과 1kg",
            "current_price": 9000,
            "previous_price": 15000,
            "price_change_rate": -40.0,
            "anomaly_score": 0.92,
            "detection_methods": ["zscore", "iqr", "ma"],
            "recorded_at": "2025-12-10T09:30:00Z"
        }
    ],
    "total_count": 15,
    "cached": true,
    "cache_expires_at": "2025-12-10T10:30:00Z"
}
```

### 5.3 레시피 갭필링 API

```
POST /api/recipe/gap-fill
```

**Request:**
```json
{
    "cart_items": [123, 456, 789]
}
```

**Response:**
```json
{
    "matched_recipes": [
        {
            "recipe_id": 999,
            "recipe_name": "된장찌개",
            "recipe_image": "https://...",
            "match_ratio": 0.7,
            "missing_ingredients": ["대파", "청양고추"]
        }
    ],
    "gap_products": [
        {
            "product_id": 321,
            "product_name": "대파 2단",
            "price": 2500,
            "reason": "된장찌개 재료 (대파)",
            "recipe_id": 999,
            "match_score": 0.85
        }
    ]
}
```

---

## 6. 임베딩 전략

### 6.1 상품 임베딩 (BERT 기반)

```python
class ProductEmbedding:
    """상품 텍스트 임베딩

    BERT 기반 한국어 임베딩:
    - 모델: klue/bert-base
    - 차원: 768
    - 입력: 상품명 + 카테고리명 + 짧은 설명

    Prod2Vec은 사용하지 않음:
    - 이유: SelF 초기 데이터 부족으로 의미있는 시퀀스 학습 불가
    - 대안: 텍스트 기반 유사도로 충분
    """

    def __init__(self):
        self.model_name = 'klue/bert-base'
        self.dimension = 768
        self.tokenizer = None
        self.model = None

    def encode(self, product: dict) -> np.ndarray:
        """상품 → 임베딩 벡터

        입력 텍스트 구성:
        "[CLS] {카테고리명} [SEP] {상품명} [SEP] {짧은설명}"
        """
        text = f"{product.get('category_name', '')} {product['name']}"
        if product.get('short_description'):
            text += f" {product['short_description']}"

        inputs = self.tokenizer(
            text,
            return_tensors='pt',
            max_length=128,
            truncation=True,
            padding=True
        )
        outputs = self.model(**inputs)

        # [CLS] 토큰 임베딩 사용
        return outputs.last_hidden_state[:, 0, :].numpy()
```

### 6.2 유사도 계산

```python
class SimilarityCalculator:
    """상품 유사도 계산

    방법:
    1. 코사인 유사도 (임베딩 벡터)
    2. 같은 카테고리 보너스 (+0.1)
    3. 가격대 유사도 보너스 (±20% 이내 +0.05)
    """

    def calculate(self, product_a: dict, product_b: dict) -> float:
        """두 상품 간 유사도 계산 (0.0 ~ 1.0)"""
        # 1. 임베딩 코사인 유사도
        emb_sim = cosine_similarity(
            product_a['embedding'],
            product_b['embedding']
        )

        # 2. 카테고리 보너스
        category_bonus = 0.1 if product_a['category_id'] == product_b['category_id'] else 0

        # 3. 가격대 유사도
        price_ratio = min(product_a['price'], product_b['price']) / \
                      max(product_a['price'], product_b['price'])
        price_bonus = 0.05 if price_ratio >= 0.8 else 0

        return min(emb_sim + category_bonus + price_bonus, 1.0)
```

---

## 7. 배치 처리 설계

### 7.1 Instacart 사전 집계 배치

```python
# batch/aggregate_instacart.py

async def aggregate_time_patterns():
    """Instacart 데이터 → 시간대별 패턴 집계

    실행 주기: 최초 1회 (데이터 변경 없음)
    소요 시간: 약 30분 (32M 레코드 처리)
    """
    # 1. 시간대별 카테고리 인기도 집계
    query = """
        INSERT INTO pred_instacart_time_patterns
            (time_slot, day_type, instacart_department_id, popularity_score, reorder_rate)
        SELECT
            CASE
                WHEN order_hour_of_day BETWEEN 6 AND 10 THEN 'morning'
                WHEN order_hour_of_day BETWEEN 11 AND 14 THEN 'lunch'
                WHEN order_hour_of_day BETWEEN 17 AND 21 THEN 'dinner'
                ELSE 'night'
            END AS time_slot,
            CASE
                WHEN order_dow IN (0, 6) THEN 'weekend'
                ELSE 'weekday'
            END AS day_type,
            ip.department_id,
            COUNT(*) AS popularity_score,
            AVG(CASE WHEN ioi.is_reordered THEN 1 ELSE 0 END) AS reorder_rate
        FROM pred_instacart_order_items ioi
        JOIN pred_instacart_orders io ON ioi.order_id = io.id
        JOIN pred_instacart_products ip ON ioi.product_id = ip.id
        JOIN pred_instacart_aisles ia ON ip.aisle_id = ia.id
        WHERE io.eval_set = 'prior'
        GROUP BY time_slot, day_type, ip.department_id
    """
    await db.execute(query)

    # 2. SelF 카테고리와 매핑
    # (수동 매핑 테이블 pred_instacart_category_mapping 필요)
```

### 7.2 가격 이상치 캐시 갱신

```python
# batch/update_anomaly_cache.py

async def update_price_anomaly_cache():
    """가격 이상치 캐시 갱신

    실행 주기: 1시간마다
    소요 시간: 약 5분
    """
    # 전체 카테고리 대상 이상치 분석
    anomalies = await price_model.detect_anomalies(category_id=None)

    # 캐시 테이블 갱신 (UPSERT)
    for anomaly in anomalies:
        await db.execute("""
            INSERT INTO pred_price_anomaly_cache
                (product_id, category_id, current_price, previous_price,
                 price_change_rate, anomaly_score, detection_methods, expires_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, NOW() + INTERVAL '1 hour')
            ON CONFLICT (product_id) DO UPDATE SET
                current_price = EXCLUDED.current_price,
                anomaly_score = EXCLUDED.anomaly_score,
                detection_methods = EXCLUDED.detection_methods,
                expires_at = EXCLUDED.expires_at
        """, anomaly['product_id'], ...)

    # 만료된 캐시 정리
    await db.execute("""
        DELETE FROM pred_price_anomaly_cache
        WHERE expires_at < NOW()
    """)
```

### 7.3 배치 스케줄

| 배치 작업 | 실행 주기 | 소요 시간 | 비고 |
|----------|----------|----------|------|
| Instacart 사전 집계 | 최초 1회 | 30분 | 정적 데이터 |
| 상품 임베딩 갱신 | 일 1회 (새벽 3시) | 10분 | 신규/변경 상품만 |
| 상품-상품 유사도 갱신 | 일 1회 (새벽 4시) | 20분 | Top 100 유사 상품 |
| 가격 이상치 캐시 | 1시간마다 | 5분 | 전체 상품 |
| 레시피-재료 매핑 | 주 1회 | 15분 | 신규 레시피만 |
| 캐시 정리 | 6시간마다 | 1분 | 만료 캐시 삭제 |

---

## 8. 테스트 전략

### 8.1 단위 테스트

```python
# tests/test_models/test_price_anomaly.py

class TestPriceAnomaly:
    """가격 이상치 모델 테스트"""

    def test_zscore_detection(self):
        """Z-Score 기반 이상치 탐지 테스트"""
        # Given: 평균 10000원, 표준편차 1000원인 가격 이력
        prices = [10000, 9500, 10500, 10200, 9800, 10100, 9900]
        # When: 현재 가격 7000원 (Z-Score = -3.0)
        prices.append(7000)

        # Then: 이상치로 탐지되어야 함
        result = price_model._analyze_price(1, prices)
        assert result['is_anomaly'] is True
        assert 'zscore' in result['detection_methods']

    def test_no_anomaly_for_normal_price(self):
        """정상 가격은 이상치로 탐지되지 않아야 함"""
        prices = [10000, 9500, 10500, 10200, 9800, 10100, 9900, 9700]

        result = price_model._analyze_price(1, prices)
        assert result['is_anomaly'] is False
```

### 8.2 통합 테스트

```python
# tests/test_api/test_recommend.py

class TestRecommendAPI:
    """추천 API 통합 테스트"""

    async def test_cold_user_recommendation(self):
        """콜드 유저 추천 테스트"""
        # Given: 행동 이력 없는 신규 사용자
        request = {
            "user_id": None,
            "page_type": "home",
            "limit": 10,
            "context": {"time_slot": "dinner", "day_type": "weekday"}
        }

        # When: 추천 API 호출
        response = await client.post("/api/recommend", json=request)

        # Then: 콜드스타트 모델 사용, 10개 추천
        assert response.status_code == 200
        data = response.json()
        assert len(data['recommendations']) == 10
        assert 'instacart' in data['metadata']['model_used']

    async def test_recommendation_timeout_fallback(self):
        """타임아웃 시 폴백 테스트"""
        # Given: 개인화 모델 지연 시뮬레이션
        with patch('self_model.recommend', side_effect=asyncio.TimeoutError):
            request = {"user_id": 1, "page_type": "home", "limit": 10}

            # When: 추천 API 호출
            response = await client.post("/api/recommend", json=request)

            # Then: 폴백으로 콜드스타트 결과 반환
            assert response.status_code == 200
```

---

**작성자**: SelF 개발팀
**관련 문서**: DATABASE_SCHEMA_RECOMMENDATION.md, COMPLETE_ERD_AND_OPTIMIZATION.md
