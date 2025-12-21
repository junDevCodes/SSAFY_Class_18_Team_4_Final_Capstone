# SelF ML 모델 고도화 구현 계획서

> **문서 버전**: v1.0.0
> **최종 수정일**: 2025년 12월 14일
> **작성자**: AI/ML Architecture Team

---

## 1. 현재 상태 분석

### 1.1 모델별 현황

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        현재 ML 모델 구현 상태                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  모델명                  │ Pickle 모드 │ DB 폴백 │  상태                     │
│  ───────────────────────┼─────────────┼─────────┼─────────────────────────  │
│  RecipePickleModel      │     ✅      │   ✅    │ 완성 (검증 완료)           │
│  InstacartColdStart     │     ❌      │   ✅    │ DB 폴백만 동작             │
│  SelfPersonalizedModel  │     ❌      │   ✅    │ DB 폴백만 동작             │
│  PriceAnomalyModel      │     ❌      │   ✅    │ DB 폴백만 동작             │
│                                                                             │
│  문제점:                                                                     │
│  • Pickle 모델이 없어서 DB에서 실시간 쿼리 → 느림                           │
│  • Instacart 32M 데이터 미활용 (168 시간패턴만 설계됨)                      │
│  • SVD 임베딩 미생성 → 개인화 품질 낮음                                     │
│  • 카테고리 통계 미계산 → 가격 이상치 탐지 정확도 낮음                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Recipe 모델 성공 사례 분석

Recipe 모델이 성공한 이유:
1. **체계적인 데이터 탐색** (01_recipe_data_exploration.ipynb)
2. **재료 파싱 고도화** (02_ingredient_parsing.ipynb)
3. **GapFilling 알고리즘 검증** (03_recipe_gapfilling_model.ipynb)
4. **모델 평가** (04_model_evaluation.ipynb)
5. **Pickle 내보내기** (05_pickle_export.ipynb)

→ **이 5단계 프로세스를 나머지 3개 모델에 적용**

---

## 2. 구현 로드맵

### 2.1 전체 Phase 구조

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          ML 모델 고도화 로드맵                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Phase 1: Instacart 데이터 전처리 및 검증                                    │
│  ─────────────────────────────────────────────────────────────────────────  │
│  • notebooks/10_instacart_data_exploration.ipynb                           │
│  • notebooks/11_instacart_time_pattern_analysis.ipynb                      │
│  • notebooks/12_instacart_category_mapping.ipynb                           │
│  • notebooks/13_instacart_pickle_export.ipynb                              │
│                                                                             │
│  Phase 2: SelF SVD 임베딩 모델 구축                                          │
│  ─────────────────────────────────────────────────────────────────────────  │
│  • notebooks/20_self_data_exploration.ipynb                                │
│  • notebooks/21_self_svd_model_training.ipynb                              │
│  • notebooks/22_self_embedding_evaluation.ipynb                            │
│  • notebooks/23_self_pickle_export.ipynb                                   │
│                                                                             │
│  Phase 3: Price Anomaly 통계 모델 구축                                       │
│  ─────────────────────────────────────────────────────────────────────────  │
│  • notebooks/30_price_data_exploration.ipynb                               │
│  • notebooks/31_price_zscore_analysis.ipynb                                │
│  • notebooks/32_price_anomaly_evaluation.ipynb                             │
│  • notebooks/33_price_pickle_export.ipynb                                  │
│                                                                             │
│  Phase 4: Adaptive Blending Orchestrator 구현                                │
│  ─────────────────────────────────────────────────────────────────────────  │
│  • pred/ml/orchestrator/adaptive_blending.py                               │
│  • pred/ml/orchestrator/weight_controller.py                               │
│  • pred/ml/orchestrator/score_fusion.py                                    │
│                                                                             │
│  Phase 5: 배치 작업 및 모니터링 구현                                         │
│  ─────────────────────────────────────────────────────────────────────────  │
│  • pred/batch/precompute_jobs.py                                           │
│  • pred/batch/embedding_update_jobs.py                                     │
│  • pred/api/metrics.py                                                     │
│                                                                             │
│  Phase 6: 통합 테스트 및 검증                                                │
│  ─────────────────────────────────────────────────────────────────────────  │
│  • pred/tests/test_instacart_model.py                                      │
│  • pred/tests/test_self_model.py                                           │
│  • pred/tests/test_price_model.py                                          │
│  • pred/tests/test_blending.py                                             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Phase 1: Instacart Cold Start 모델 고도화

### 3.1 목표

```
현재: DB에서 실시간 쿼리 → 168 시간패턴 테이블에서 데이터 조회
목표: Pickle 파일에 사전 집계된 시간패턴 + 카테고리 매핑 로드
```

### 3.2 세부 태스크

#### Task 1.1: 데이터 탐색 (10_instacart_data_exploration.ipynb)

```python
# 목표: Instacart 데이터셋 구조 파악 및 SelF 카테고리 매핑 가능성 검증

# 검증 항목:
# 1. Instacart 데이터셋 로드 가능 여부
# 2. department/aisle 구조 파악
# 3. 시간 패턴 (order_hour_of_day, order_dow) 분포
# 4. 재주문율 (reordered) 패턴
# 5. SelF categories 테이블과의 매핑 가능성

# 입력 데이터:
# - orders.csv (3.4M 주문)
# - order_products_*.csv (32M 상품)
# - products.csv (50K 상품)
# - aisles.csv (134 aisles)
# - departments.csv (21 departments)

# 출력:
# - 데이터 품질 리포트
# - 매핑 가능한 카테고리 목록
# - 시간대별 인기 aisle 분포
```

**검증 체크리스트:**
- [ ] Instacart CSV 파일 로드 성공
- [ ] 데이터 결측치/이상치 확인
- [ ] department-aisle 계층 구조 파악
- [ ] 시간대(168개) × aisle(134개) 분포 시각화
- [ ] SelF categories와 aisle 이름 유사도 분석

#### Task 1.2: 시간 패턴 분석 (11_instacart_time_pattern_analysis.ipynb)

```python
# 목표: 168개 시간 패턴 (24시간 × 7요일) 집계

# 분석 내용:
# 1. 시간대별 주문량 분포
# 2. 시간대별 인기 aisle Top-10
# 3. 시간대별 재주문율
# 4. 장바구니 평균 위치 (cart_position)

# 출력 데이터 구조:
time_patterns = {
    (day_of_week, hour_of_day): {
        'top_aisles': [
            {'aisle_id': 1, 'order_count': 10000, 'reorder_rate': 0.65},
            ...
        ],
        'total_orders': 50000,
        'avg_basket_size': 8.3,
    },
    ...
}

# 검증:
# - 아침(6-11): 유제품, 빵, 커피 상위인지 확인
# - 저녁(17-21): 육류, 채소 상위인지 확인
# - 야간(21-6): 간편식, 라면 상위인지 확인
```

**검증 체크리스트:**
- [ ] 168개 시간 패턴 모두 생성 완료
- [ ] 각 패턴당 최소 1000개 이상 주문 데이터 존재
- [ ] 시간대별 인기 카테고리가 상식적으로 맞는지 확인
- [ ] 재주문율 분포가 합리적인지 확인 (0.3 ~ 0.7 범위)

#### Task 1.3: 카테고리 매핑 (12_instacart_category_mapping.ipynb)

```python
# 목표: Instacart aisle → SelF category 매핑 테이블 생성

# 매핑 방법:
# 1. 이름 유사도 기반 자동 매핑 (Fuzzy Matching)
# 2. 수동 검토 및 보정
# 3. 매핑 불가 aisle 처리 방안

# 매핑 예시:
category_mapping = {
    # Instacart aisle_id: SelF category_id
    1: 10,   # 'frozen desserts' → '냉동식품'
    2: 11,   # 'ice cream' → '아이스크림'
    3: 5,    # 'prepared foods' → '간편식'
    ...
    # 매핑 불가 시:
    99: None,  # 'beauty' → SelF에 없음 (무시)
}

# 검증:
# - 매핑률 70% 이상 달성
# - 주요 카테고리 (육류, 채소, 유제품) 매핑 완료
```

**검증 체크리스트:**
- [ ] 134개 aisle 중 70% 이상 매핑 완료
- [ ] 식품 관련 aisle 95% 이상 매핑
- [ ] 매핑 테이블 CSV 저장
- [ ] 매핑 결과 샘플 검토 (20개 이상)

#### Task 1.4: Pickle 내보내기 (13_instacart_pickle_export.ipynb)

```python
# 목표: instacart_cold_start.pkl 생성

# Pickle 구조:
instacart_model = {
    'version': '1.0.0',
    'created_at': datetime.now().isoformat(),
    'metadata': {
        'total_orders': 3421083,
        'time_patterns_count': 168,
        'mapped_aisles': 96,
    },
    'components': {
        # 168개 시간 패턴
        'time_patterns': {
            (0, 6): {'top_aisles': [...], 'order_count': ...},
            (0, 7): {...},
            ...
        },

        # Instacart → SelF 카테고리 매핑
        'category_mapping': {
            1: 10, 2: 11, ...
        },

        # aisle별 통계 (재주문율, 평균 가격대 등)
        'aisle_stats': {
            1: {'reorder_rate': 0.65, 'avg_price_range': 'mid'},
            ...
        },

        # 글로벌 인기 aisle (시간 무관)
        'global_popular_aisles': [24, 83, 123, ...],
    },
    'hyperparameters': {
        'top_aisles_per_pattern': 10,
        'min_orders_threshold': 100,
    },
}

# 검증:
# - Pickle 파일 크기 < 50MB
# - 로드 시간 < 1초
# - 모든 컴포넌트 접근 가능
```

**검증 체크리스트:**
- [ ] Pickle 파일 생성 완료 (models/instacart_cold_start_v1.pkl)
- [ ] 파일 크기 50MB 이하
- [ ] 로드 테스트 통과 (< 1초)
- [ ] 168개 시간 패턴 모두 존재
- [ ] 모델 버전 정보 포함

---

## 4. Phase 2: SelF Personalized SVD 모델

### 4.1 목표

```
현재: DB에서 user_product_stats 실시간 쿼리
목표: SVD 기반 유저/상품 임베딩으로 빠른 유사도 계산
```

### 4.2 세부 태스크

#### Task 2.1: 데이터 탐색 (20_self_data_exploration.ipynb)

```python
# 목표: SelF 상호작용 데이터 분석

# 분석 항목:
# 1. user_product_stats 테이블 크기 및 분포
# 2. 유저당 상호작용 수 분포 (Cold/Lukewarm/Warm 비율)
# 3. 상품당 상호작용 수 분포 (인기 상품 vs 롱테일)
# 4. 상호작용 유형별 가중치 검증 (view:cart:order = 1:3:5)

# 출력:
# - 유저 분포 히스토그램
# - 상품 인기도 분포
# - Sparse Matrix 생성 가능성 검증
```

**검증 체크리스트:**
- [ ] user_product_stats 로드 성공
- [ ] 유저 타입 분포 확인 (Cold/Lukewarm/Warm)
- [ ] 상호작용 행렬 sparsity 계산 (< 1% 예상)
- [ ] SVD 적용 가능 최소 데이터 확보 여부 확인

#### Task 2.2: SVD 모델 학습 (21_self_svd_model_training.ipynb)

```python
# 목표: 유저/상품 임베딩 생성

# 알고리즘: Truncated SVD (scikit-learn)
# 임베딩 차원: 128

# 학습 과정:
# 1. 유저-상품 상호작용 행렬 구성
#    R[user_id][product_id] = view*1 + cart*3 + order*5
#
# 2. SVD 분해
#    R ≈ U × Σ × V^T
#    - U: 유저 임베딩 (n_users × 128)
#    - V^T: 상품 임베딩 (128 × n_products)
#
# 3. 인덱스 매핑 생성
#    user_id_to_idx, idx_to_user_id
#    product_id_to_idx, idx_to_product_id

from scipy.sparse import csr_matrix
from sklearn.decomposition import TruncatedSVD

# 상호작용 행렬 구성
def build_interaction_matrix(stats_df):
    # 유저/상품 ID를 인덱스로 변환
    user_ids = stats_df['user_id'].unique()
    product_ids = stats_df['product_id'].unique()

    user_id_to_idx = {uid: i for i, uid in enumerate(user_ids)}
    product_id_to_idx = {pid: i for i, pid in enumerate(product_ids)}

    # 희소 행렬 생성
    rows = stats_df['user_id'].map(user_id_to_idx)
    cols = stats_df['product_id'].map(product_id_to_idx)
    values = (
        stats_df['view_count'] * 1 +
        stats_df['cart_event_count'] * 3 +
        stats_df['order_event_count'] * 5
    )

    matrix = csr_matrix(
        (values, (rows, cols)),
        shape=(len(user_ids), len(product_ids))
    )

    return matrix, user_id_to_idx, product_id_to_idx

# SVD 학습
def train_svd(matrix, n_components=128):
    svd = TruncatedSVD(n_components=n_components, random_state=42)
    user_embeddings = svd.fit_transform(matrix)
    product_embeddings = svd.components_.T

    explained_variance = svd.explained_variance_ratio_.sum()
    print(f"설명된 분산: {explained_variance:.2%}")

    return user_embeddings, product_embeddings, svd
```

**검증 체크리스트:**
- [ ] 상호작용 행렬 구성 완료
- [ ] SVD 학습 완료 (설명 분산 > 50%)
- [ ] 유저 임베딩 shape: (n_users, 128)
- [ ] 상품 임베딩 shape: (n_products, 128)
- [ ] 학습 시간 측정 (목표: < 30분)

#### Task 2.3: 임베딩 품질 검증 (22_self_embedding_evaluation.ipynb)

```python
# 목표: 생성된 임베딩 품질 검증

# 검증 방법:
# 1. 유사 상품 검색 테스트
#    - 육류 상품의 유사 상품이 육류인지 확인
#    - 유제품 상품의 유사 상품이 유제품인지 확인
#
# 2. 유사 유저 검색 테스트
#    - 비슷한 구매 패턴 유저가 실제로 유사한지 확인
#
# 3. 추천 품질 테스트
#    - Hold-out 데이터로 Hit Rate, NDCG 계산

def evaluate_product_similarity(product_embeddings, product_id_to_idx, products_df):
    """상품 임베딩 품질 검증"""
    from sklearn.metrics.pairwise import cosine_similarity

    # 테스트 상품 선택 (각 카테고리별 1개)
    test_products = products_df.groupby('category_id').first().reset_index()

    results = []
    for _, product in test_products.iterrows():
        pid = product['id']
        if pid not in product_id_to_idx:
            continue

        idx = product_id_to_idx[pid]
        target_emb = product_embeddings[idx].reshape(1, -1)

        # 유사 상품 검색
        similarities = cosine_similarity(target_emb, product_embeddings)[0]
        top_indices = np.argsort(similarities)[::-1][1:6]  # Top 5 (자기 제외)

        # 같은 카테고리 비율 계산
        same_category_count = 0
        for top_idx in top_indices:
            top_pid = idx_to_product_id[top_idx]
            top_category = products_df[products_df['id'] == top_pid]['category_id'].values[0]
            if top_category == product['category_id']:
                same_category_count += 1

        results.append({
            'product_id': pid,
            'category': product['category_id'],
            'same_category_ratio': same_category_count / 5,
        })

    avg_ratio = np.mean([r['same_category_ratio'] for r in results])
    print(f"같은 카테고리 유사 상품 비율: {avg_ratio:.2%}")

    return results

# 목표: 같은 카테고리 비율 > 60%
```

**검증 체크리스트:**
- [ ] 상품 유사도 테스트: 같은 카테고리 비율 > 60%
- [ ] 유저 유사도 테스트: 구매 패턴 유사도 확인
- [ ] Hold-out 테스트: Hit@10 > 10%, NDCG@10 > 0.1
- [ ] 임베딩 시각화 (t-SNE) - 카테고리 클러스터 확인

#### Task 2.4: Pickle 내보내기 (23_self_pickle_export.ipynb)

```python
# 목표: self_personalized_v1.pkl 생성

self_model = {
    'version': '1.0.0',
    'created_at': datetime.now().isoformat(),
    'metadata': {
        'n_users': len(user_embeddings),
        'n_products': len(product_embeddings),
        'embedding_dim': 128,
        'explained_variance': 0.65,
        'training_interactions': 150000,
    },
    'components': {
        # 유저 임베딩 (numpy array)
        'user_embeddings': user_embeddings,  # shape: (n_users, 128)

        # 상품 임베딩 (numpy array)
        'product_embeddings': product_embeddings,  # shape: (n_products, 128)

        # ID 매핑
        'user_id_to_idx': user_id_to_idx,
        'idx_to_user_id': idx_to_user_id,
        'product_id_to_idx': product_id_to_idx,
        'idx_to_product_id': idx_to_product_id,

        # 유저-상품 행렬 (구매 여부 확인용)
        'user_product_matrix': interaction_matrix,

        # 카테고리별 인기 상품 (cold user용)
        'category_popular': {
            1: [101, 102, 103, ...],
            2: [201, 202, 203, ...],
            ...
        },

        # 전체 인기 상품
        'global_popular': [1001, 1002, 1003, ...],
    },
    'hyperparameters': {
        'n_components': 128,
        'weight_view': 1,
        'weight_cart': 3,
        'weight_order': 5,
    },
}
```

**검증 체크리스트:**
- [ ] Pickle 파일 생성 완료 (models/self_personalized_v1.pkl)
- [ ] 파일 크기 적정 (유저 10만명 기준 ~60MB)
- [ ] 로드 테스트 통과
- [ ] 추천 테스트 통과 (유저 ID로 Top-10 추천)

---

## 5. Phase 3: Price Anomaly 통계 모델

### 5.1 목표

```
현재: DB에서 실시간으로 카테고리 통계 계산
목표: 사전 계산된 카테고리 통계 + 베스트 딜 목록 로드
```

### 5.2 세부 태스크

#### Task 3.1: 데이터 탐색 (30_price_data_exploration.ipynb)

```python
# 목표: 가격 데이터 분석

# 분석 항목:
# 1. price_history 테이블 데이터 존재 여부
# 2. original_price vs price 할인 분포
# 3. 카테고리별 가격 분포
# 4. 가격 변동 패턴

# 참고: price_history 테이블이 비어있을 수 있음
# → 대안: products 테이블의 price, original_price 활용
```

**검증 체크리스트:**
- [ ] 가격 데이터 로드 성공
- [ ] 할인 상품 비율 확인
- [ ] 카테고리별 가격 분포 시각화
- [ ] Z-score 적용 가능성 확인

#### Task 3.2: Z-Score 분석 (31_price_zscore_analysis.ipynb)

```python
# 목표: 카테고리별 가격 이상치 탐지

# 방법:
# 1. 카테고리별 평균/표준편차 계산
# 2. 각 상품의 Z-score 계산
# 3. |Z| > 2.0 인 상품을 이상치로 분류

def calculate_category_stats(products_df):
    """카테고리별 가격 통계 계산"""
    stats = products_df.groupby('category_id').agg({
        'price': ['mean', 'std', 'min', 'max', 'count'],
    }).reset_index()

    stats.columns = ['category_id', 'avg_price', 'std_price',
                     'min_price', 'max_price', 'product_count']

    return stats

def find_anomalies(products_df, category_stats, z_threshold=2.0):
    """가격 이상치 탐지"""
    merged = products_df.merge(category_stats, on='category_id')

    merged['z_score'] = (merged['price'] - merged['avg_price']) / merged['std_price']
    merged['is_anomaly'] = abs(merged['z_score']) > z_threshold
    merged['anomaly_type'] = np.where(
        merged['z_score'] < -z_threshold, 'below_average',
        np.where(merged['z_score'] > z_threshold, 'above_average', None)
    )

    return merged[merged['is_anomaly']]
```

**검증 체크리스트:**
- [ ] 카테고리별 통계 계산 완료
- [ ] Z-score 분포 확인 (정규분포 근사)
- [ ] 이상치 상품 비율 확인 (5% 내외)
- [ ] 이상치 상품 샘플 검토 (실제로 할인 상품인지)

#### Task 3.3: 평가 (32_price_anomaly_evaluation.ipynb)

```python
# 목표: 가격 이상치 모델 품질 검증

# 검증 방법:
# 1. 할인율과 Z-score 상관관계 확인
# 2. 실제 "베스트 딜" 상품 선정
# 3. 시간대별 가격 트렌드 확인 (가능 시)

def evaluate_price_model(anomalies_df, products_df):
    """가격 모델 평가"""
    # 실제 할인율 계산
    products_with_discount = products_df[
        products_df['original_price'] > products_df['price']
    ].copy()

    products_with_discount['actual_discount'] = (
        1 - products_with_discount['price'] / products_with_discount['original_price']
    ) * 100

    # Z-score와 할인율 상관관계
    merged = anomalies_df.merge(
        products_with_discount[['id', 'actual_discount']],
        left_on='product_id', right_on='id'
    )

    correlation = merged['z_score'].corr(merged['actual_discount'])
    print(f"Z-score와 할인율 상관계수: {correlation:.3f}")

    # 목표: 음의 상관관계 (Z < 0 = 할인)
    # correlation < -0.3 이면 양호
```

**검증 체크리스트:**
- [ ] Z-score와 할인율 상관관계 확인 (r < -0.3)
- [ ] 베스트 딜 상품 Top-50 선정
- [ ] 선정된 상품 실제 할인 여부 확인

#### Task 3.4: Pickle 내보내기 (33_price_pickle_export.ipynb)

```python
# 목표: price_anomaly_v1.pkl 생성

price_model = {
    'version': '1.0.0',
    'created_at': datetime.now().isoformat(),
    'metadata': {
        'total_products': 10000,
        'total_categories': 50,
        'anomalies_count': 500,
    },
    'components': {
        # 카테고리별 통계
        'category_stats': {
            1: {'avg': 5000, 'std': 1500, 'min': 1000, 'max': 15000},
            2: {'avg': 3000, 'std': 800, 'min': 500, 'max': 8000},
            ...
        },

        # 베스트 딜 목록 (Z-score 기준)
        'best_deals': [
            {'product_id': 101, 'z_score': -2.5, 'discount_rate': 30, 'score': 0.95},
            {'product_id': 102, 'z_score': -2.3, 'discount_rate': 25, 'score': 0.90},
            ...
        ],

        # 카테고리별 베스트 딜
        'category_best_deals': {
            1: [101, 105, 108, ...],
            2: [201, 203, 207, ...],
            ...
        },
    },
    'hyperparameters': {
        'z_threshold': 2.0,
        'min_discount_rate': 10.0,
    },
}
```

**검증 체크리스트:**
- [ ] Pickle 파일 생성 완료 (models/price_anomaly_v1.pkl)
- [ ] 파일 크기 적정 (< 10MB)
- [ ] 로드 테스트 통과
- [ ] 베스트 딜 추천 테스트 통과

---

## 6. Phase 4: Adaptive Blending Orchestrator

### 6.1 목표

```
현재: 각 모델이 독립적으로 동작
목표: Phase/UserType/PageType에 따른 동적 가중치 블렌딩
```

### 6.2 구현 파일 구조

```
pred/ml/orchestrator/
├── __init__.py
├── adaptive_blending.py      # 메인 오케스트레이터
├── weight_controller.py      # 가중치 계산
├── score_fusion.py           # 점수 융합
├── phase_detector.py         # Phase 감지
└── diversity_filter.py       # MMR 다양성 필터
```

### 6.3 세부 태스크

#### Task 4.1: Phase Detector 구현

```python
# pred/ml/orchestrator/phase_detector.py

class PhaseDetector:
    """서비스 Phase 감지"""

    THRESHOLDS = {
        'cold': 0,
        'growing': 1_000,
        'mature': 10_000,
        'self_sufficient': 50_000,
    }

    async def get_current_phase(self, db: Database) -> str:
        """현재 서비스 Phase 반환"""
        total_interactions = await db.fetch_val("""
            SELECT COUNT(*) FROM user_product_stats
        """)

        if total_interactions < self.THRESHOLDS['growing']:
            return 'cold'
        elif total_interactions < self.THRESHOLDS['mature']:
            return 'growing'
        elif total_interactions < self.THRESHOLDS['self_sufficient']:
            return 'mature'
        else:
            return 'self_sufficient'
```

#### Task 4.2: Weight Controller 구현

```python
# pred/ml/orchestrator/weight_controller.py

class WeightController:
    """가중치 계산"""

    # Phase × UserType × PageType 가중치 행렬
    # (문서 MODEL_BLENDING_STRATEGY.md 참조)

    def get_weights(
        self,
        phase: str,
        user_type: str,
        page_type: str,
    ) -> Dict[str, float]:
        """가중치 반환"""
        base_weights = self.BASE_WEIGHTS[phase][user_type]
        page_multipliers = self.PAGE_MULTIPLIERS[page_type]

        # 가중치 적용 후 정규화
        adjusted = {}
        for model, weight in base_weights.items():
            adjusted[model] = weight * page_multipliers.get(model, 1.0)

        total = sum(adjusted.values())
        return {k: v / total for k, v in adjusted.items()}
```

#### Task 4.3: Score Fusion 구현

```python
# pred/ml/orchestrator/score_fusion.py

class ScoreFusion:
    """점수 융합"""

    def fuse(
        self,
        model_results: Dict[str, List[Dict]],
        weights: Dict[str, float],
    ) -> List[Dict]:
        """모델 결과 융합"""
        # 1. 점수 정규화
        normalized = self.normalize_scores(model_results)

        # 2. 가중 합계
        fused = self.weighted_sum(normalized, weights)

        # 3. 시간 컨텍스트 부스트
        boosted = self.apply_time_boost(fused)

        return sorted(boosted, key=lambda x: x['score'], reverse=True)
```

#### Task 4.4: Adaptive Blending Orchestrator 구현

```python
# pred/ml/orchestrator/adaptive_blending.py

class AdaptiveBlendingOrchestrator:
    """적응형 블렌딩 오케스트레이터"""

    async def recommend(
        self,
        context: RecommendationContext,
        limit: int = 10,
    ) -> RecommendationResult:
        """메인 추천 로직"""
        # 1. Phase 감지
        phase = await self.phase_detector.get_current_phase()

        # 2. 가중치 계산
        weights = self.weight_controller.get_weights(
            phase=phase,
            user_type=context.user_type,
            page_type=context.page_type,
        )

        # 3. 모델 병렬 실행
        results = await asyncio.gather(
            self.instacart_model.recommend(context, limit * 3),
            self.self_model.recommend(context, limit * 3),
            self.price_model.recommend(context, limit * 3),
            return_exceptions=True,
        )

        # 4. 점수 융합
        fused = self.score_fusion.fuse(
            model_results={
                'instacart': results[0].products,
                'self': results[1].products,
                'price': results[2].products,
            },
            weights=weights,
        )

        # 5. 다양성 필터
        diversified = self.diversity_filter.apply(fused, limit)

        return RecommendationResult(
            products=diversified,
            weights_used=weights,
            phase=phase,
        )
```

**검증 체크리스트:**
- [ ] PhaseDetector 구현 및 테스트
- [ ] WeightController 구현 및 테스트
- [ ] ScoreFusion 구현 및 테스트
- [ ] AdaptiveBlendingOrchestrator 통합 테스트
- [ ] 응답 시간 < 100ms 확인

---

## 7. Phase 5: 배치 작업 및 모니터링

### 7.1 Precompute 배치 작업

```python
# pred/batch/precompute_jobs.py

async def precompute_user_recommendations():
    """유저별 Top-100 추천 미리 계산"""
    # 활성 유저 조회
    # SVD 임베딩 로드
    # 유저별 Top-100 계산
    # DB 저장
    pass

async def update_price_anomaly_cache():
    """가격 이상치 캐시 갱신"""
    # 카테고리 통계 재계산
    # 베스트 딜 목록 갱신
    # 캐시 테이블 갱신
    pass
```

### 7.2 모니터링 API

```python
# pred/api/metrics.py

@router.get("/metrics")
async def get_metrics():
    """모델 성능 지표"""
    return {
        'current_phase': await phase_detector.get_current_phase(),
        'data_confidence': await calculate_confidence(),
        'model_weights': current_weights,
        'recommendation_stats': {
            'total_requests': ...,
            'avg_latency_ms': ...,
            'cache_hit_rate': ...,
        },
    }
```

---

## 8. Phase 6: 통합 테스트

### 8.1 테스트 범위

```python
# pred/tests/test_integration.py

class TestMLModelsIntegration:
    """통합 테스트"""

    async def test_instacart_cold_start(self):
        """Instacart Cold Start 모델 테스트"""
        # Pickle 로드 확인
        # 시간대별 추천 동작 확인
        # 응답 시간 < 50ms 확인
        pass

    async def test_self_personalized(self):
        """SelF Personalized 모델 테스트"""
        # Pickle 로드 확인
        # 유저 임베딩 기반 추천 확인
        # Cold user 폴백 확인
        pass

    async def test_price_anomaly(self):
        """Price Anomaly 모델 테스트"""
        # Pickle 로드 확인
        # 베스트 딜 추천 확인
        # Z-score 기반 이상치 확인
        pass

    async def test_adaptive_blending(self):
        """Adaptive Blending 통합 테스트"""
        # Phase별 가중치 확인
        # UserType별 동작 확인
        # PageType별 동작 확인
        pass
```

### 8.2 성능 벤치마크

```python
async def benchmark_recommendations():
    """성능 벤치마크"""
    results = []

    for _ in range(100):
        start = time.time()
        await orchestrator.recommend(test_context, limit=10)
        elapsed = (time.time() - start) * 1000
        results.append(elapsed)

    print(f"P50: {np.percentile(results, 50):.1f}ms")
    print(f"P95: {np.percentile(results, 95):.1f}ms")
    print(f"P99: {np.percentile(results, 99):.1f}ms")

    # 목표:
    # P50 < 20ms
    # P95 < 50ms
    # P99 < 100ms
```

---

## 9. 의존성 및 우선순위

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          태스크 의존성 그래프                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Phase 1 (Instacart)     Phase 2 (SelF)         Phase 3 (Price)            │
│  ┌──────────────┐        ┌──────────────┐       ┌──────────────┐           │
│  │ Task 1.1     │        │ Task 2.1     │       │ Task 3.1     │           │
│  │ 데이터 탐색  │        │ 데이터 탐색  │       │ 데이터 탐색  │           │
│  └──────┬───────┘        └──────┬───────┘       └──────┬───────┘           │
│         │                       │                      │                    │
│         ▼                       ▼                      ▼                    │
│  ┌──────────────┐        ┌──────────────┐       ┌──────────────┐           │
│  │ Task 1.2     │        │ Task 2.2     │       │ Task 3.2     │           │
│  │ 시간패턴분석 │        │ SVD 학습     │       │ Z-Score분석  │           │
│  └──────┬───────┘        └──────┬───────┘       └──────┬───────┘           │
│         │                       │                      │                    │
│         ▼                       ▼                      ▼                    │
│  ┌──────────────┐        ┌──────────────┐       ┌──────────────┐           │
│  │ Task 1.3     │        │ Task 2.3     │       │ Task 3.3     │           │
│  │ 카테고리매핑 │        │ 임베딩 검증  │       │ 모델 평가    │           │
│  └──────┬───────┘        └──────┬───────┘       └──────┬───────┘           │
│         │                       │                      │                    │
│         ▼                       ▼                      ▼                    │
│  ┌──────────────┐        ┌──────────────┐       ┌──────────────┐           │
│  │ Task 1.4     │        │ Task 2.4     │       │ Task 3.4     │           │
│  │ Pickle생성   │        │ Pickle생성   │       │ Pickle생성   │           │
│  └──────┬───────┘        └──────┬───────┘       └──────┬───────┘           │
│         │                       │                      │                    │
│         └───────────────────────┼──────────────────────┘                    │
│                                 │                                           │
│                                 ▼                                           │
│                    ┌───────────────────────────┐                           │
│                    │       Phase 4             │                           │
│                    │ Adaptive Blending 구현   │                           │
│                    └───────────────┬───────────┘                           │
│                                    │                                        │
│                                    ▼                                        │
│                    ┌───────────────────────────┐                           │
│                    │       Phase 5             │                           │
│                    │ 배치작업/모니터링 구현   │                           │
│                    └───────────────┬───────────┘                           │
│                                    │                                        │
│                                    ▼                                        │
│                    ┌───────────────────────────┐                           │
│                    │       Phase 6             │                           │
│                    │ 통합 테스트              │                           │
│                    └───────────────────────────┘                           │
│                                                                             │
│  우선순위:                                                                  │
│  1. Phase 1, 2, 3은 병렬 진행 가능                                         │
│  2. Phase 4는 1, 2, 3 완료 후 진행                                        │
│  3. Phase 5, 6은 순차 진행                                                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 10. 예상 일정 (참고용)

| Phase | 태스크 | 예상 복잡도 |
|-------|--------|-------------|
| 1 | Instacart 데이터 전처리 | 중 |
| 1 | Instacart Pickle 생성 | 중 |
| 2 | SelF SVD 모델 학습 | 높음 |
| 2 | 임베딩 품질 검증 | 중 |
| 3 | Price Anomaly 통계 계산 | 낮음 |
| 4 | Adaptive Blending 구현 | 높음 |
| 5 | 배치 작업 구현 | 중 |
| 6 | 통합 테스트 | 중 |

---

## 11. 리스크 및 대응 방안

### 11.1 데이터 리스크

| 리스크 | 영향 | 대응 |
|--------|------|------|
| Instacart 데이터 없음 | Phase 1 불가 | Mock 데이터로 구조만 검증 |
| user_product_stats 데이터 부족 | SVD 품질 저하 | 시뮬레이션 데이터 생성 |
| price_history 테이블 비어있음 | 시계열 분석 불가 | products 테이블 활용 |

### 11.2 성능 리스크

| 리스크 | 영향 | 대응 |
|--------|------|------|
| SVD 학습 시간 초과 | 배치 지연 | 증분 학습 또는 ALS 사용 |
| Pickle 파일 너무 큼 | 로드 시간 증가 | 압축 또는 분할 |
| 블렌딩 연산 느림 | 응답 지연 | Precompute 확대 |

---

## 12. 결론

이 계획서를 따라 단계별로 진행하면:

1. **Phase 1-3**: 3개 모델 모두 Pickle 기반 프로덕션 모드로 동작
2. **Phase 4**: 동적 가중치 블렌딩으로 Cold Start → Self-Learning 자연스러운 전환
3. **Phase 5-6**: 배치 자동화 및 품질 보장

Recipe 모델처럼 **노트북 기반 검증 → Pickle 생성 → 코드 통합** 프로세스를 따르면 한치의 오차 없이 구현 가능합니다.

---

*문서 끝*
