# SelF 개인화 추천 시스템 상세 설계서

> **문서 버전**: v1.0.0
> **최종 수정일**: 2025년 12월 14일

---

## 1. 개요

### 1.1 목적

이 문서는 **유저별 개인화 추천 시스템**의 상세 설계를 다룹니다. 핵심 목표는:

1. 유저가 아무리 많아져도 **실시간 응답 (< 50ms)** 유지
2. 유저별 데이터가 쌓이면 **즉시 개인화 반영**
3. **부하 분산**을 통한 안정적 서비스

### 1.2 핵심 도전 과제

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Personalization Challenges                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Challenge 1: 연산량 폭발                                                   │
│  ─────────────────────────────────────────────────────────────────────────  │
│  유저 100만명 × 상품 10만개 = 1000억 조합                                   │
│  → 실시간 계산 불가능                                                       │
│                                                                             │
│  Challenge 2: 캐시 효율 저하                                                │
│  ─────────────────────────────────────────────────────────────────────────  │
│  각 유저마다 다른 추천 = 캐시 히트율 매우 낮음                               │
│  → 메모리 폭발 또는 캐시 무용                                               │
│                                                                             │
│  Challenge 3: 실시간 컨텍스트                                               │
│  ─────────────────────────────────────────────────────────────────────────  │
│  장바구니, 시간대, 방금 본 상품이 계속 변함                                  │
│  → 미리 계산한 결과가 outdated                                              │
│                                                                             │
│  Challenge 4: Cold/Warm 혼재                                                │
│  ─────────────────────────────────────────────────────────────────────────  │
│  같은 서비스에서 Cold user와 Warm user가 공존                               │
│  → 다른 전략 필요                                                           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. 해결 전략: Precompute + Realtime Reranking

### 2.1 핵심 아이디어

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Precompute + Realtime Reranking                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   무거운 연산 (Precompute)           가벼운 연산 (Realtime)                 │
│   ─────────────────────────         ──────────────────────────             │
│   • 유저 임베딩 계산                 • 점수 조정 (곱셈/덧셈)                │
│   • 상품 임베딩 계산                 • 필터링 (품절 제외)                   │
│   • 유저×상품 유사도                 • 정렬                                 │
│   • Top-100 후보 선정                • Top-N 추출                          │
│                                                                             │
│   실행 시점: 배치 (야간)             실행 시점: API 요청 시                 │
│   소요 시간: 수 시간                 소요 시간: < 50ms                      │
│                                                                             │
│   ┌───────────────────────────────────────────────────────────────────┐   │
│   │                                                                    │   │
│   │   [배치] Top-100 계산  →  [저장]  →  [API] 조회 + 리랭킹 → Top-10 │   │
│   │                                                                    │   │
│   └───────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 데이터 흐름

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Data Flow Architecture                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   [실시간 이벤트 수집]                                                      │
│   ─────────────────────────────────────────────────────────────────────────│
│   │                                                                         │
│   │  사용자 행동                                                            │
│   │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│   │  │ 상품조회 │  │ 장바구니 │  │   구매   │  │  리뷰   │               │
│   │  │  추가    │  │   담기   │  │          │  │  작성   │               │
│   │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘              │
│   │       │             │             │             │                      │
│   │       ▼             ▼             ▼             ▼                      │
│   │  ┌──────────────────────────────────────────────────────────────┐    │
│   │  │                  user_product_stats 테이블                    │    │
│   │  │                                                               │    │
│   │  │  user_id | product_id | view_count | cart_count | order_count│    │
│   │  │  ────────┼────────────┼────────────┼────────────┼────────────│    │
│   │  │  1001    │ 5001       │ 5          │ 2          │ 1          │    │
│   │  │  1001    │ 5002       │ 3          │ 0          │ 0          │    │
│   │  │  ...     │ ...        │ ...        │ ...        │ ...        │    │
│   │  └──────────────────────────────────────────────────────────────┘    │
│   │                                                                         │
│   ──────────────────────────────────────────────────────────────────────────│
│                                                                             │
│   [배치 처리 - 매일 새벽]                                                   │
│   ─────────────────────────────────────────────────────────────────────────│
│   │                                                                         │
│   │  Step 1: 임베딩 계산                                                    │
│   │  ┌──────────────────────────────────────────────────────────────┐    │
│   │  │                                                               │    │
│   │  │  user_product_stats  →  SVD/ALS  →  user_embeddings          │    │
│   │  │                                   →  product_embeddings       │    │
│   │  │                                                               │    │
│   │  │  user_id | embedding_vector (128차원)                        │    │
│   │  │  ────────┼─────────────────────────────────────────────────  │    │
│   │  │  1001    │ [0.12, -0.34, 0.56, ..., 0.23]                    │    │
│   │  │  1002    │ [0.45, 0.12, -0.78, ..., -0.11]                   │    │
│   │  │                                                               │    │
│   │  └──────────────────────────────────────────────────────────────┘    │
│   │                                                                         │
│   │  Step 2: Top-100 추천 미리 계산                                         │
│   │  ┌──────────────────────────────────────────────────────────────┐    │
│   │  │                                                               │    │
│   │  │  for each user:                                               │    │
│   │  │      similarities = dot(user_emb, all_product_embs)          │    │
│   │  │      top_100 = argsort(similarities)[-100:]                  │    │
│   │  │      save to user_precomputed_recommendations                │    │
│   │  │                                                               │    │
│   │  │  user_id | recommendations (JSON)                            │    │
│   │  │  ────────┼─────────────────────────────────────────────────  │    │
│   │  │  1001    │ [{pid: 5001, score: 0.95}, {pid: 5002, score: 0.87}, ...]│
│   │  │                                                               │    │
│   │  └──────────────────────────────────────────────────────────────┘    │
│   │                                                                         │
│   ──────────────────────────────────────────────────────────────────────────│
│                                                                             │
│   [실시간 API]                                                              │
│   ─────────────────────────────────────────────────────────────────────────│
│   │                                                                         │
│   │  Request: GET /recommend/personalized?user_id=1001&limit=10            │
│   │                                                                         │
│   │  ┌──────────────────────────────────────────────────────────────┐    │
│   │  │                                                               │    │
│   │  │  1. Precomputed 조회 (5ms)                                   │    │
│   │  │     candidates = SELECT recommendations                       │    │
│   │  │                  FROM user_precomputed_recommendations        │    │
│   │  │                  WHERE user_id = 1001                         │    │
│   │  │                                                               │    │
│   │  │  2. 실시간 리랭킹 (10ms)                                     │    │
│   │  │     for candidate in candidates:                              │    │
│   │  │         score = candidate.score                               │    │
│   │  │         score *= cart_boost(candidate)      # 장바구니 보완   │    │
│   │  │         score *= time_boost(candidate)      # 시간대 적합     │    │
│   │  │         score *= recency_boost(candidate)   # 최근 조회 관련  │    │
│   │  │                                                               │    │
│   │  │  3. 필터링 & 정렬 (5ms)                                      │    │
│   │  │     filtered = filter(candidates, is_available=True)         │    │
│   │  │     sorted = sort(filtered, by=final_score, desc=True)       │    │
│   │  │     return sorted[:10]                                        │    │
│   │  │                                                               │    │
│   │  └──────────────────────────────────────────────────────────────┘    │
│   │                                                                         │
│   │  Response: [{product_id: 5001, ...}, {product_id: 5023, ...}, ...]    │
│   │                                                                         │
│   ──────────────────────────────────────────────────────────────────────────│
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. 유저 분류 체계

### 3.1 유저 타입 정의

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         User Type Classification                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                          Cold User                                   │  │
│  ├─────────────────────────────────────────────────────────────────────┤  │
│  │                                                                      │  │
│  │  조건: interaction_count == 0                                        │  │
│  │                                                                      │  │
│  │  특성:                                                               │  │
│  │  • 비로그인 또는 신규 가입                                           │  │
│  │  • 개인 데이터 없음                                                  │  │
│  │                                                                      │  │
│  │  추천 전략:                                                          │  │
│  │  • Instacart 시간대 패턴 100%                                       │  │
│  │  • 전역 인기 상품                                                    │  │
│  │  • 카테고리 브라우징 기반 (클릭 시 반영)                             │  │
│  │                                                                      │  │
│  │  캐시 TTL: 1시간 (변화 적음)                                        │  │
│  │                                                                      │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                        Lukewarm User                                 │  │
│  ├─────────────────────────────────────────────────────────────────────┤  │
│  │                                                                      │  │
│  │  조건: 1 <= interaction_count < 10                                   │  │
│  │                                                                      │  │
│  │  특성:                                                               │  │
│  │  • 초기 탐색 단계                                                    │  │
│  │  • 일부 선호 카테고리 파악 가능                                      │  │
│  │  • 임베딩 신뢰도 낮음                                                │  │
│  │                                                                      │  │
│  │  추천 전략:                                                          │  │
│  │  • 선호 카테고리 인기 상품 60%                                       │  │
│  │  • Instacart 보완 30%                                               │  │
│  │  • 탐색용 다양성 10%                                                 │  │
│  │                                                                      │  │
│  │  캐시 TTL: 30분 (빠른 변화 반영)                                     │  │
│  │                                                                      │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                          Warm User                                   │  │
│  ├─────────────────────────────────────────────────────────────────────┤  │
│  │                                                                      │  │
│  │  조건: interaction_count >= 10                                       │  │
│  │                                                                      │  │
│  │  특성:                                                               │  │
│  │  • 충분한 행동 데이터                                                │  │
│  │  • 신뢰할 수 있는 임베딩                                             │  │
│  │  • 선호 패턴 명확                                                    │  │
│  │                                                                      │  │
│  │  추천 전략:                                                          │  │
│  │  • 유저 임베딩 기반 개인화 70%                                       │  │
│  │  • 협업 필터링 (유사 유저) 20%                                       │  │
│  │  • 탐색용 다양성 10%                                                 │  │
│  │                                                                      │  │
│  │  캐시 TTL: 10분 (개인화 정확도 유지)                                 │  │
│  │                                                                      │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 유저 타입별 처리 로직

```python
class UserTypeClassifier:
    """
    유저 타입 분류 및 전략 선택
    """

    THRESHOLDS = {
        'cold': 0,
        'lukewarm': 1,
        'warm': 10,
    }

    async def classify(self, user_id: int) -> str:
        """유저 타입 분류"""
        if not user_id:
            return 'cold'

        stats = await self.user_repo.get_user_interaction_count(user_id)
        total = (
            stats['total_views'] +
            stats['total_carts'] * 2 +
            stats['total_orders'] * 5
        )

        if total == 0:
            return 'cold'
        elif total < 10:
            return 'lukewarm'
        else:
            return 'warm'

    def get_strategy(self, user_type: str) -> Dict[str, float]:
        """유저 타입별 추천 전략 가중치"""
        return {
            'cold': {
                'instacart': 0.90,
                'category_popular': 0.10,
                'embedding': 0.00,
                'collaborative': 0.00,
            },
            'lukewarm': {
                'instacart': 0.30,
                'category_popular': 0.50,
                'embedding': 0.10,
                'collaborative': 0.10,
            },
            'warm': {
                'instacart': 0.05,
                'category_popular': 0.15,
                'embedding': 0.50,
                'collaborative': 0.30,
            },
        }[user_type]
```

---

## 4. 임베딩 시스템

### 4.1 유저 임베딩

```python
class UserEmbeddingSystem:
    """
    유저 임베딩 계산 및 관리

    임베딩 차원: 128
    학습 알고리즘: SVD (Singular Value Decomposition)
    갱신 주기: 매일 새벽 (배치) + 실시간 증분
    """

    EMBEDDING_DIM = 128

    async def compute_user_embedding(self, user_id: int) -> np.ndarray:
        """
        유저 임베딩 계산

        방법: 상호작용한 상품 임베딩의 가중 평균
        가중치: order × 5 + cart × 3 + view × 1
        """
        interactions = await self.get_user_interactions(user_id)

        if not interactions:
            return None

        embeddings = []
        weights = []

        for interaction in interactions:
            product_embedding = await self.get_product_embedding(
                interaction['product_id']
            )

            if product_embedding is not None:
                weight = (
                    interaction['order_count'] * 5 +
                    interaction['cart_count'] * 3 +
                    interaction['view_count'] * 1
                )
                embeddings.append(product_embedding)
                weights.append(weight)

        if not embeddings:
            return None

        # 가중 평균 계산
        weights = np.array(weights) / sum(weights)
        user_embedding = np.average(embeddings, axis=0, weights=weights)

        return user_embedding

    async def find_similar_products(
        self,
        user_embedding: np.ndarray,
        limit: int = 100,
        exclude_ids: List[int] = None,
    ) -> List[Tuple[int, float]]:
        """
        유저 임베딩과 유사한 상품 검색

        코사인 유사도 기반
        """
        # 모든 상품 임베딩 로드 (캐시됨)
        product_embeddings = await self.get_all_product_embeddings()

        # 코사인 유사도 계산
        similarities = cosine_similarity(
            user_embedding.reshape(1, -1),
            product_embeddings
        )[0]

        # 제외 상품 마스킹
        if exclude_ids:
            for pid in exclude_ids:
                if pid < len(similarities):
                    similarities[pid] = -np.inf

        # Top-K 추출
        top_indices = np.argsort(similarities)[-limit:][::-1]

        return [
            (self.idx_to_pid[idx], float(similarities[idx]))
            for idx in top_indices
            if similarities[idx] > 0
        ]
```

### 4.2 상품 임베딩

```python
class ProductEmbeddingSystem:
    """
    상품 임베딩 계산 및 관리

    임베딩 소스:
    1. 협업 필터링 임베딩 (SVD)
    2. 컨텐츠 기반 임베딩 (카테고리, 속성)

    최종 임베딩: 두 소스의 결합
    """

    async def compute_product_embeddings_batch(self) -> Dict[int, np.ndarray]:
        """
        전체 상품 임베딩 배치 계산

        1. 유저-상품 상호작용 행렬 구성
        2. SVD 분해
        3. 상품 임베딩 추출
        """
        # 1. 상호작용 행렬 구성
        interactions = await self.get_all_interactions()
        matrix = self.build_interaction_matrix(interactions)

        # 2. SVD 분해
        # U: 유저 임베딩, S: 특이값, Vt: 상품 임베딩
        U, S, Vt = svds(matrix, k=self.EMBEDDING_DIM)

        # 3. 상품 임베딩 추출
        product_embeddings = Vt.T

        return {
            pid: product_embeddings[idx]
            for pid, idx in self.pid_to_idx.items()
        }
```

---

## 5. Precompute 시스템

### 5.1 배치 작업 설계

```python
async def precompute_all_user_recommendations(db: Database) -> int:
    """
    모든 활성 유저의 Top-100 추천 미리 계산

    실행 시점: 매일 새벽 5시
    의존성: 임베딩 계산 완료 후
    예상 소요: 4-6시간 (100만 유저 기준)
    """

    # 1. 활성 유저 조회 (최근 30일 활동)
    active_users = await db.fetch_all("""
        SELECT DISTINCT user_id
        FROM user_product_stats
        WHERE last_interacted_at > NOW() - INTERVAL '30 days'
    """)

    logger.info(f"Precompute 대상 유저: {len(active_users)}명")

    # 2. 상품 임베딩 메모리 로드 (한 번만)
    product_embeddings = await load_product_embeddings()
    product_ids = list(product_embeddings.keys())

    # 3. 배치 처리
    batch_size = 1000
    processed = 0

    for batch_start in range(0, len(active_users), batch_size):
        batch = active_users[batch_start:batch_start + batch_size]

        tasks = []
        for user in batch:
            tasks.append(
                compute_user_recommendations(
                    user['user_id'],
                    product_embeddings,
                    product_ids,
                    limit=100,
                )
            )

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 4. DB 저장 (배치 INSERT)
        recommendations_to_save = []
        for user, result in zip(batch, results):
            if isinstance(result, Exception):
                logger.warning(f"유저 {user['user_id']} 처리 실패: {result}")
                continue

            recommendations_to_save.append({
                'user_id': user['user_id'],
                'recommendations': json.dumps(result),
                'computed_at': datetime.now(),
            })

        await bulk_upsert_recommendations(db, recommendations_to_save)

        processed += len(batch)
        logger.info(f"진행: {processed}/{len(active_users)}")

    return processed


async def compute_user_recommendations(
    user_id: int,
    product_embeddings: Dict[int, np.ndarray],
    product_ids: List[int],
    limit: int = 100,
) -> List[Dict]:
    """
    단일 유저의 Top-100 추천 계산
    """
    # 1. 유저 임베딩 조회
    user_embedding = await get_user_embedding(user_id)

    if user_embedding is None:
        # Cold user: 빈 리스트 (실시간에서 처리)
        return []

    # 2. 모든 상품과 유사도 계산
    all_embeddings = np.array([
        product_embeddings.get(pid, np.zeros(128))
        for pid in product_ids
    ])

    # 코사인 유사도 (벡터 연산으로 빠름)
    user_norm = np.linalg.norm(user_embedding)
    product_norms = np.linalg.norm(all_embeddings, axis=1)

    similarities = np.dot(all_embeddings, user_embedding)
    similarities /= (product_norms * user_norm + 1e-8)

    # 3. 이미 구매한 상품 제외
    purchased = await get_user_purchased_products(user_id)
    for pid in purchased:
        idx = product_ids.index(pid) if pid in product_ids else -1
        if idx >= 0:
            similarities[idx] = -np.inf

    # 4. Top-100 추출
    top_indices = np.argsort(similarities)[-limit:][::-1]

    return [
        {
            'product_id': product_ids[idx],
            'score': float(similarities[idx]),
        }
        for idx in top_indices
        if similarities[idx] > 0
    ]
```

### 5.2 Precompute 테이블 스키마

```sql
-- 유저별 미리 계산된 추천 결과
CREATE TABLE user_precomputed_recommendations (
    user_id INTEGER PRIMARY KEY REFERENCES users(id),
    recommendations JSONB NOT NULL,
    computed_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 인덱스 (빠른 조회)
CREATE INDEX idx_precomputed_user_id ON user_precomputed_recommendations(user_id);
CREATE INDEX idx_precomputed_computed_at ON user_precomputed_recommendations(computed_at);

-- recommendations JSONB 구조:
-- [
--   {"product_id": 5001, "score": 0.95},
--   {"product_id": 5002, "score": 0.87},
--   ...
-- ]
```

---

## 6. 실시간 리랭킹

### 6.1 리랭킹 로직

```python
class RealtimeReranker:
    """
    실시간 컨텍스트 기반 리랭킹

    입력: Precomputed Top-100 후보
    출력: 컨텍스트 반영된 Top-N

    목표 응답시간: < 20ms
    """

    async def rerank(
        self,
        candidates: List[Dict],
        context: RecommendationContext,
        limit: int = 10,
    ) -> List[Dict]:
        """
        실시간 리랭킹 메인 로직
        """
        if not candidates:
            return []

        # 1. 컨텍스트 부스트 계산
        for candidate in candidates:
            base_score = candidate['score']

            # 1-1. 장바구니 보완 부스트
            cart_boost = self.calculate_cart_boost(
                candidate['product_id'],
                context.cart_product_ids,
            )

            # 1-2. 시간대 부스트
            time_boost = self.calculate_time_boost(
                candidate.get('category_id'),
                context.time_context,
            )

            # 1-3. 최근 조회 연관 부스트
            recency_boost = self.calculate_recency_boost(
                candidate['product_id'],
                context.recent_view_ids,
            )

            # 최종 점수
            candidate['final_score'] = (
                base_score *
                cart_boost *
                time_boost *
                recency_boost
            )

        # 2. 필터링
        filtered = await self.apply_filters(candidates, context)

        # 3. 다양성 보장 (MMR)
        diversified = self.apply_diversity(filtered, limit)

        return diversified

    def calculate_cart_boost(
        self,
        product_id: int,
        cart_product_ids: List[int],
    ) -> float:
        """
        장바구니 보완 상품 부스트

        장바구니에 있는 상품과 함께 자주 구매되는 상품에 가산점
        """
        if not cart_product_ids:
            return 1.0

        # 캐시된 동시구매 데이터 조회
        copurchase_score = self.get_copurchase_score(
            product_id, cart_product_ids
        )

        if copurchase_score > 0.5:
            return 1.5  # 높은 동시구매율
        elif copurchase_score > 0.2:
            return 1.2  # 중간 동시구매율
        else:
            return 1.0  # 기본

    def calculate_time_boost(
        self,
        category_id: int,
        time_context: str,
    ) -> float:
        """
        시간대별 카테고리 부스트
        """
        TIME_CATEGORY_BOOST = {
            'morning': {
                'dairy': 1.3,      # 유제품
                'bakery': 1.3,     # 빵
                'coffee': 1.4,     # 커피
                'cereal': 1.3,     # 시리얼
            },
            'lunch': {
                'ready_meal': 1.4, # 간편식
                'salad': 1.3,      # 샐러드
                'sandwich': 1.3,   # 샌드위치
            },
            'dinner': {
                'meat': 1.4,       # 육류
                'seafood': 1.3,    # 해산물
                'vegetable': 1.2,  # 채소
                'sauce': 1.2,      # 양념
            },
            'night': {
                'snack': 1.4,      # 야식
                'ramen': 1.5,      # 라면
                'alcohol_snack': 1.3, # 안주
            },
        }

        category_type = self.get_category_type(category_id)
        return TIME_CATEGORY_BOOST.get(time_context, {}).get(category_type, 1.0)

    def apply_diversity(
        self,
        candidates: List[Dict],
        limit: int,
        lambda_param: float = 0.7,
    ) -> List[Dict]:
        """
        MMR (Maximal Marginal Relevance) 기반 다양성 보장

        lambda_param: 관련성 vs 다양성 균형 (0.7 = 관련성 70%)
        """
        selected = []
        remaining = candidates.copy()

        while len(selected) < limit and remaining:
            if not selected:
                # 첫 번째는 최고 점수
                best = max(remaining, key=lambda x: x['final_score'])
                selected.append(best)
                remaining.remove(best)
                continue

            # MMR 점수 계산
            best_mmr = None
            best_score = float('-inf')

            selected_categories = set(
                s.get('category_id') for s in selected
            )

            for candidate in remaining:
                relevance = candidate['final_score']

                # 다양성: 이미 선택된 카테고리와 다르면 보너스
                diversity = 1.0
                if candidate.get('category_id') in selected_categories:
                    diversity = 0.5

                mmr_score = (
                    lambda_param * relevance +
                    (1 - lambda_param) * diversity * max(c['final_score'] for c in candidates)
                )

                if mmr_score > best_score:
                    best_score = mmr_score
                    best_mmr = candidate

            if best_mmr:
                selected.append(best_mmr)
                remaining.remove(best_mmr)

        return selected
```

---

## 7. 캐시 전략

### 7.1 다층 캐시 구조

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Multi-Layer Cache Strategy                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │ Layer 1: Application Cache (In-Memory)                                │ │
│  │                                                                        │ │
│  │ • 상품 임베딩 (전체)                                                   │ │
│  │ • 카테고리 정보                                                        │ │
│  │ • 동시구매 데이터                                                      │ │
│  │                                                                        │ │
│  │ TTL: 영구 (서버 재시작 시 갱신)                                       │ │
│  │ 크기: ~500MB                                                          │ │
│  │ 조회: O(1), < 1ms                                                     │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                      │                                      │
│                                      ▼                                      │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │ Layer 2: Redis Cache                                                  │ │
│  │                                                                        │ │
│  │ • 유저별 최종 추천 결과                                               │ │
│  │ • 활성 유저 임베딩                                                     │ │
│  │ • 세션 데이터                                                          │ │
│  │                                                                        │ │
│  │ TTL:                                                                  │ │
│  │   - Cold user 추천: 1시간                                             │ │
│  │   - Warm user 추천: 10분                                              │ │
│  │   - 임베딩: 24시간                                                    │ │
│  │                                                                        │ │
│  │ 크기: ~2GB                                                            │ │
│  │ 조회: O(1), 1-5ms                                                     │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                      │                                      │
│                                      ▼                                      │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │ Layer 3: PostgreSQL (Precomputed)                                     │ │
│  │                                                                        │ │
│  │ • user_precomputed_recommendations                                    │ │
│  │ • user_embeddings                                                     │ │
│  │ • product_embeddings                                                  │ │
│  │                                                                        │ │
│  │ 갱신: 매일 배치                                                       │ │
│  │ 조회: 인덱스 사용, 5-10ms                                             │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 7.2 캐시 무효화 정책

```python
class CacheInvalidationPolicy:
    """
    캐시 무효화 규칙
    """

    async def on_user_interaction(self, user_id: int, event_type: str):
        """
        유저 상호작용 시 캐시 무효화
        """
        if event_type in ['purchase', 'cart_add']:
            # 구매/장바구니 추가 시 추천 캐시 무효화
            await self.invalidate_user_recommendations(user_id)

        if event_type == 'purchase':
            # 구매 시 임베딩 갱신 큐에 추가
            await self.queue_embedding_update(user_id)

    async def on_product_update(self, product_id: int, update_type: str):
        """
        상품 정보 변경 시 캐시 무효화
        """
        if update_type == 'out_of_stock':
            # 품절 시 해당 상품 포함 캐시 무효화
            await self.invalidate_product_in_recommendations(product_id)

        if update_type == 'price_change':
            # 가격 변경 시 가격 이상치 캐시 갱신
            await self.refresh_price_anomaly_cache(product_id)
```

---

## 8. 성능 모니터링

### 8.1 핵심 지표

```yaml
# Personalization Performance Metrics

latency_metrics:
  - name: precomputed_lookup_latency
    description: Precomputed 결과 조회 시간
    target: "< 5ms"
    p50_threshold: 3ms
    p95_threshold: 10ms

  - name: reranking_latency
    description: 실시간 리랭킹 시간
    target: "< 15ms"
    p50_threshold: 8ms
    p95_threshold: 20ms

  - name: total_recommendation_latency
    description: 전체 추천 응답 시간
    target: "< 50ms"
    p50_threshold: 15ms
    p95_threshold: 50ms

quality_metrics:
  - name: cache_hit_rate
    description: 캐시 히트율
    target: "> 80%"

  - name: precomputed_coverage
    description: Precomputed 결과 존재 비율
    target: "> 90%"

  - name: embedding_coverage
    description: 임베딩 존재 유저 비율
    target: "> 85%"

business_metrics:
  - name: personalization_ctr
    description: 개인화 추천 클릭률
    target: "> 5%"

  - name: personalization_cvr
    description: 개인화 추천 구매전환율
    target: "> 8%"
```

---

## 9. 결론

이 개인화 시스템은 다음을 보장합니다:

1. **스케일**: 100만 유저에서도 < 50ms 응답
2. **품질**: 유저 데이터가 쌓일수록 개인화 정확도 향상
3. **유연성**: Cold/Lukewarm/Warm 유저별 최적 전략
4. **효율성**: 배치 + 실시간 하이브리드로 자원 최적화

---

*문서 끝*
