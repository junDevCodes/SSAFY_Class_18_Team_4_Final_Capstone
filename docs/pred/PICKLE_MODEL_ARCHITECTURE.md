# Pickle 기반 ML 모델 배포 아키텍처

## 개요

프로덕션 환경에서 Docker 컨테이너 내 pred 서비스가 사전 학습된 ML 모델을 pickle 파일로 로드하여 추천 서비스를 제공하는 아키텍처입니다.

```
[로컬 개발 환경]                    [프로덕션 환경 (Docker)]
┌─────────────────────┐            ┌─────────────────────────┐
│  Jupyter Notebook   │            │     pred 서비스          │
│  ├── 데이터 전처리   │  ──────►  │  ├── ModelLoader        │
│  ├── 모델 학습       │  .pkl     │  ├── models/*.pkl       │
│  └── 모델 저장       │            │  └── 추천 API 서빙      │
└─────────────────────┘            └─────────────────────────┘
```

## 디렉토리 구조

```
SSAFY_Class_18_Team_4_Final_Capstone/
├── notebooks/                          # 로컬 학습용 노트북
│   ├── 01_data_exploration.ipynb       # 데이터 탐색
│   ├── 02_self_personalized_train.ipynb # 개인화 모델 학습
│   ├── 03_price_anomaly_train.ipynb    # 가격 이상치 모델 학습
│   ├── 04_collaborative_filtering.ipynb # 협업 필터링 모델 학습
│   ├── 05_model_evaluation.ipynb       # 모델 평가 및 비교
│   └── utils/                          # 노트북 유틸리티
│       ├── __init__.py
│       ├── data_loader.py              # DB 데이터 로딩
│       └── model_exporter.py           # pickle 저장 헬퍼
│
├── pred/
│   ├── models/                         # pickle 모델 저장 경로
│   │   ├── .gitkeep
│   │   ├── self_personalized_v1.pkl    # 개인화 모델
│   │   ├── price_anomaly_v1.pkl        # 가격 이상치 모델
│   │   ├── user_embeddings.pkl         # 사용자 임베딩
│   │   ├── product_embeddings.pkl      # 상품 임베딩
│   │   ├── category_stats.pkl          # 카테고리 통계
│   │   └── model_metadata.json         # 모델 메타데이터
│   │
│   ├── ml/
│   │   ├── model_loader.py             # pickle 모델 로더
│   │   ├── base.py                     # 기본 클래스 (수정)
│   │   └── models/
│   │       ├── self_personalized.py    # pickle 호환 수정
│   │       └── price_anomaly.py        # pickle 호환 수정
│   │
│   └── ...
│
└── docker-compose.yml                  # 볼륨 마운트 설정
```

## 모델별 Pickle 구조

### 1. SelfPersonalizedModel (self_personalized_v1.pkl)

```python
{
    "model_name": "self_personalized",
    "version": "1.0.0",
    "created_at": "2024-12-10T00:00:00",
    "components": {
        # 사용자-상품 상호작용 행렬 (scipy sparse matrix)
        "user_product_matrix": <scipy.sparse.csr_matrix>,

        # 사용자 임베딩 (numpy array)
        "user_embeddings": <np.ndarray shape=(n_users, embedding_dim)>,

        # 상품 임베딩 (numpy array)
        "product_embeddings": <np.ndarray shape=(n_products, embedding_dim)>,

        # ID 매핑
        "user_id_to_idx": {user_id: idx, ...},
        "idx_to_user_id": {idx: user_id, ...},
        "product_id_to_idx": {product_id: idx, ...},
        "idx_to_product_id": {idx: product_id, ...},

        # 카테고리별 인기 상품 (cold start용)
        "category_popular": {
            category_id: [product_id1, product_id2, ...],
            ...
        },

        # 전체 인기 상품 (cold start용)
        "global_popular": [product_id1, product_id2, ...],
    },
    "hyperparameters": {
        "embedding_dim": 64,
        "similarity_metric": "cosine",
        "min_interactions": 5,
    },
    "metrics": {
        "precision@10": 0.15,
        "recall@10": 0.08,
        "ndcg@10": 0.12,
    }
}
```

### 2. PriceAnomalyModel (price_anomaly_v1.pkl)

```python
{
    "model_name": "price_anomaly",
    "version": "1.0.0",
    "created_at": "2024-12-10T00:00:00",
    "components": {
        # 카테고리별 가격 통계
        "category_price_stats": {
            category_id: {
                "mean": float,
                "std": float,
                "median": float,
                "q1": float,
                "q3": float,
                "min": float,
                "max": float,
            },
            ...
        },

        # 상품별 가격 이력 통계
        "product_price_history": {
            product_id: {
                "avg_price_30d": float,
                "min_price_30d": float,
                "max_price_30d": float,
                "price_volatility": float,
            },
            ...
        },

        # 현재 베스트 딜 목록 (사전 계산)
        "best_deals": [
            {"product_id": int, "discount_rate": float, "z_score": float},
            ...
        ],
    },
    "hyperparameters": {
        "z_threshold": 2.0,
        "min_discount_rate": 10.0,
    },
}
```

### 3. 협업 필터링 모델 (collaborative_v1.pkl)

```python
{
    "model_name": "collaborative_filtering",
    "version": "1.0.0",
    "created_at": "2024-12-10T00:00:00",
    "components": {
        # 유사 사용자 매트릭스 (사전 계산된 top-k)
        "similar_users": {
            user_id: [(similar_user_id, similarity_score), ...],
            ...
        },

        # 유사 상품 매트릭스 (사전 계산된 top-k)
        "similar_products": {
            product_id: [(similar_product_id, similarity_score), ...],
            ...
        },

        # 사용자별 구매/조회 이력 (실시간 업데이트용 기준)
        "user_interactions": {
            user_id: set([product_id1, product_id2, ...]),
            ...
        },
    },
    "hyperparameters": {
        "k_neighbors": 50,
        "similarity_metric": "cosine",
    },
}
```

## Jupyter 노트북 워크플로우

### 1. 데이터 탐색 (01_data_exploration.ipynb)

```python
# 셀 1: DB 연결 및 데이터 로딩
import pandas as pd
from sqlalchemy import create_engine

DATABASE_URL = "postgresql://selfuser:selfpass@localhost:5432/selfdb"
engine = create_engine(DATABASE_URL)

# 사용자 상호작용 데이터
user_stats = pd.read_sql("""
    SELECT user_id, product_id, view_count, cart_add_count,
           purchase_count, last_interaction_at
    FROM user_product_stats
""", engine)

# 상품 데이터
products = pd.read_sql("""
    SELECT id, name, price, original_price, category_id, seller_id
    FROM products WHERE status = 'active'
""", engine)

# 상품 통계
product_stats = pd.read_sql("""
    SELECT product_id, view_event_count, cart_event_count, order_event_count
    FROM product_stats
""", engine)
```

```python
# 셀 2: EDA
print(f"총 사용자 수: {user_stats['user_id'].nunique()}")
print(f"총 상품 수: {products['id'].nunique()}")
print(f"총 상호작용 수: {len(user_stats)}")

# 사용자 유형 분류 기준 확인
interaction_counts = user_stats.groupby('user_id').size()
print(f"Cold (0-2): {(interaction_counts <= 2).sum()}")
print(f"Lukewarm (3-9): {((interaction_counts > 2) & (interaction_counts < 10)).sum()}")
print(f"Warm (10+): {(interaction_counts >= 10).sum()}")
```

### 2. 개인화 모델 학습 (02_self_personalized_train.ipynb)

```python
# 셀 1: 데이터 준비
import numpy as np
from scipy.sparse import csr_matrix
from sklearn.decomposition import TruncatedSVD
import pickle
from datetime import datetime

# 상호작용 가중치 계산
user_stats['interaction_score'] = (
    user_stats['view_count'] * 1 +
    user_stats['cart_add_count'] * 3 +
    user_stats['purchase_count'] * 5
)

# ID 매핑 생성
user_ids = user_stats['user_id'].unique()
product_ids = user_stats['product_id'].unique()

user_id_to_idx = {uid: idx for idx, uid in enumerate(user_ids)}
idx_to_user_id = {idx: uid for uid, idx in user_id_to_idx.items()}
product_id_to_idx = {pid: idx for idx, pid in enumerate(product_ids)}
idx_to_product_id = {idx: pid for pid, idx in product_id_to_idx.items()}
```

```python
# 셀 2: 희소 행렬 생성
rows = [user_id_to_idx[uid] for uid in user_stats['user_id']]
cols = [product_id_to_idx[pid] for pid in user_stats['product_id']]
data = user_stats['interaction_score'].values

user_product_matrix = csr_matrix(
    (data, (rows, cols)),
    shape=(len(user_ids), len(product_ids))
)

print(f"Matrix shape: {user_product_matrix.shape}")
print(f"Sparsity: {1 - user_product_matrix.nnz / np.prod(user_product_matrix.shape):.4f}")
```

```python
# 셀 3: SVD로 임베딩 학습
EMBEDDING_DIM = 64

svd = TruncatedSVD(n_components=EMBEDDING_DIM, random_state=42)
user_embeddings = svd.fit_transform(user_product_matrix)
product_embeddings = svd.components_.T

print(f"User embeddings shape: {user_embeddings.shape}")
print(f"Product embeddings shape: {product_embeddings.shape}")
print(f"Explained variance ratio: {svd.explained_variance_ratio_.sum():.4f}")
```

```python
# 셀 4: Cold start용 인기 상품 계산
# 카테고리별 인기 상품
category_popular = {}
for cat_id in products['category_id'].unique():
    cat_products = products[products['category_id'] == cat_id]['id'].tolist()
    cat_stats = product_stats[product_stats['product_id'].isin(cat_products)]
    cat_stats = cat_stats.sort_values('order_event_count', ascending=False)
    category_popular[int(cat_id)] = cat_stats['product_id'].head(50).tolist()

# 전체 인기 상품
global_popular = product_stats.sort_values(
    'order_event_count', ascending=False
)['product_id'].head(100).tolist()
```

```python
# 셀 5: 모델 저장
model_data = {
    "model_name": "self_personalized",
    "version": "1.0.0",
    "created_at": datetime.now().isoformat(),
    "components": {
        "user_product_matrix": user_product_matrix,
        "user_embeddings": user_embeddings,
        "product_embeddings": product_embeddings,
        "user_id_to_idx": user_id_to_idx,
        "idx_to_user_id": idx_to_user_id,
        "product_id_to_idx": product_id_to_idx,
        "idx_to_product_id": idx_to_product_id,
        "category_popular": category_popular,
        "global_popular": global_popular,
    },
    "hyperparameters": {
        "embedding_dim": EMBEDDING_DIM,
        "similarity_metric": "cosine",
        "min_interactions": 5,
    },
}

# pickle 저장
with open('../pred/models/self_personalized_v1.pkl', 'wb') as f:
    pickle.dump(model_data, f, protocol=pickle.HIGHEST_PROTOCOL)

print("모델 저장 완료!")
```

### 3. 가격 이상치 모델 학습 (03_price_anomaly_train.ipynb)

```python
# 셀 1: 카테고리별 가격 통계 계산
category_price_stats = {}

for cat_id in products['category_id'].unique():
    cat_prices = products[products['category_id'] == cat_id]['price']

    category_price_stats[int(cat_id)] = {
        "mean": float(cat_prices.mean()),
        "std": float(cat_prices.std()),
        "median": float(cat_prices.median()),
        "q1": float(cat_prices.quantile(0.25)),
        "q3": float(cat_prices.quantile(0.75)),
        "min": float(cat_prices.min()),
        "max": float(cat_prices.max()),
    }
```

```python
# 셀 2: 할인 상품 탐지 (Z-score 기반)
Z_THRESHOLD = 2.0
MIN_DISCOUNT_RATE = 10.0

best_deals = []

for _, product in products.iterrows():
    cat_stats = category_price_stats.get(product['category_id'])
    if not cat_stats or cat_stats['std'] == 0:
        continue

    # Z-score 계산
    z_score = (product['price'] - cat_stats['mean']) / cat_stats['std']

    # 할인율 계산
    if product['original_price'] and product['original_price'] > 0:
        discount_rate = (1 - product['price'] / product['original_price']) * 100
    else:
        discount_rate = 0

    # 이상치 판정 (평균 이하 가격)
    if z_score < -Z_THRESHOLD or discount_rate >= MIN_DISCOUNT_RATE:
        best_deals.append({
            "product_id": int(product['id']),
            "discount_rate": round(discount_rate, 2),
            "z_score": round(z_score, 3),
            "category_id": int(product['category_id']),
        })

# 할인율 기준 정렬
best_deals = sorted(best_deals, key=lambda x: x['discount_rate'], reverse=True)[:500]
print(f"발견된 베스트 딜: {len(best_deals)}개")
```

```python
# 셀 3: 모델 저장
price_model_data = {
    "model_name": "price_anomaly",
    "version": "1.0.0",
    "created_at": datetime.now().isoformat(),
    "components": {
        "category_price_stats": category_price_stats,
        "best_deals": best_deals,
    },
    "hyperparameters": {
        "z_threshold": Z_THRESHOLD,
        "min_discount_rate": MIN_DISCOUNT_RATE,
    },
}

with open('../pred/models/price_anomaly_v1.pkl', 'wb') as f:
    pickle.dump(price_model_data, f, protocol=pickle.HIGHEST_PROTOCOL)

print("가격 이상치 모델 저장 완료!")
```

## ModelLoader 구현

### pred/ml/model_loader.py

```python
"""
Pickle 기반 ML 모델 로더

사전 학습된 모델을 pickle 파일에서 로드하여 추천 서비스에 제공
"""

import os
import pickle
import json
from typing import Any, Dict, Optional
from pathlib import Path
from datetime import datetime

from core.logging import get_logger

logger = get_logger(__name__)


class ModelLoader:
    """Pickle 모델 로더

    싱글톤 패턴으로 모델을 한 번만 로드하여 메모리에 유지
    """

    _instance = None
    _models: Dict[str, Dict[str, Any]] = {}
    _metadata: Dict[str, Any] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self.models_dir = Path(os.getenv("MODELS_DIR", "/app/models"))
        self._loaded = False

    async def load_all_models(self) -> None:
        """모든 모델 로드"""
        if self._loaded:
            logger.info("모델이 이미 로드됨")
            return

        logger.info(f"모델 로딩 시작: {self.models_dir}")

        # 메타데이터 로드
        metadata_path = self.models_dir / "model_metadata.json"
        if metadata_path.exists():
            with open(metadata_path, 'r') as f:
                self._metadata = json.load(f)

        # pickle 모델들 로드
        model_files = list(self.models_dir.glob("*.pkl"))

        for model_file in model_files:
            try:
                model_name = model_file.stem  # 확장자 제외 파일명
                with open(model_file, 'rb') as f:
                    model_data = pickle.load(f)

                self._models[model_name] = model_data
                logger.info(
                    f"모델 로드 완료: {model_name}",
                    version=model_data.get("version", "unknown"),
                    created_at=model_data.get("created_at", "unknown"),
                )
            except Exception as e:
                logger.error(f"모델 로드 실패: {model_file}", error=str(e))

        self._loaded = True
        logger.info(f"총 {len(self._models)}개 모델 로드 완료")

    def get_model(self, model_name: str) -> Optional[Dict[str, Any]]:
        """특정 모델 조회"""
        # 버전 접미사 제거하여 검색
        for key in self._models:
            if key.startswith(model_name):
                return self._models[key]
        return None

    def get_component(
        self,
        model_name: str,
        component_name: str,
    ) -> Optional[Any]:
        """모델의 특정 컴포넌트 조회"""
        model = self.get_model(model_name)
        if model and "components" in model:
            return model["components"].get(component_name)
        return None

    def get_hyperparameter(
        self,
        model_name: str,
        param_name: str,
    ) -> Optional[Any]:
        """모델의 하이퍼파라미터 조회"""
        model = self.get_model(model_name)
        if model and "hyperparameters" in model:
            return model["hyperparameters"].get(param_name)
        return None

    @property
    def loaded_models(self) -> list:
        """로드된 모델 목록"""
        return list(self._models.keys())

    @property
    def is_loaded(self) -> bool:
        """로드 완료 여부"""
        return self._loaded


# 전역 인스턴스
model_loader = ModelLoader()
```

## 수정된 모델 클래스

### pred/ml/models/self_personalized.py (수정)

```python
"""
Self Personalized 추천 모델 (Pickle 기반)
"""

from typing import Any, Dict, List, Optional
import numpy as np
from scipy.sparse import csr_matrix

from ml.base import HybridModel, RecommendationContext
from ml.model_loader import model_loader
from core.database import Database
from core.cache import CacheManager
from core.logging import get_logger

logger = get_logger(__name__)


class SelfPersonalizedModel(HybridModel):
    """SelF 개인화 추천 모델 (Pickle 기반)

    사전 학습된 임베딩과 유사도를 활용한 추천
    """

    def __init__(
        self,
        db: Database,
        cache: Optional[CacheManager] = None,
    ):
        super().__init__(db, cache)
        self._model_data = None

    @property
    def model_name(self) -> str:
        return "self_personalized"

    @property
    def model_version(self) -> str:
        if self._model_data:
            return self._model_data.get("version", "1.0.0")
        return "1.0.0"

    async def initialize(self) -> None:
        """모델 초기화 - pickle에서 로드"""
        self._model_data = model_loader.get_model("self_personalized")

        if not self._model_data:
            logger.warning("self_personalized 모델 파일 없음, 폴백 모드로 동작")
        else:
            logger.info(
                "self_personalized 모델 로드 완료",
                version=self.model_version,
            )

        self._initialized = True

    async def _recommend(
        self,
        context: RecommendationContext,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """추천 로직"""

        # 모델이 로드되지 않은 경우 DB 폴백
        if not self._model_data:
            return await self._fallback_recommend(context, limit)

        components = self._model_data.get("components", {})

        # Cold user: 인기 상품 기반
        if context.user_type == "cold":
            return await self._recommend_cold(context, limit, components)

        # Warm/Lukewarm user: 임베딩 기반 유사도
        return await self._recommend_personalized(context, limit, components)

    async def _recommend_cold(
        self,
        context: RecommendationContext,
        limit: int,
        components: Dict,
    ) -> List[Dict[str, Any]]:
        """Cold user 추천 (사전 계산된 인기 상품)"""

        # 카테고리 지정 시 카테고리 인기 상품
        if context.category_id:
            category_popular = components.get("category_popular", {})
            product_ids = category_popular.get(context.category_id, [])[:limit]
        else:
            # 전체 인기 상품
            product_ids = components.get("global_popular", [])[:limit]

        return await self._fetch_products_by_ids(product_ids)

    async def _recommend_personalized(
        self,
        context: RecommendationContext,
        limit: int,
        components: Dict,
    ) -> List[Dict[str, Any]]:
        """개인화 추천 (임베딩 유사도 기반)"""

        user_embeddings = components.get("user_embeddings")
        product_embeddings = components.get("product_embeddings")
        user_id_to_idx = components.get("user_id_to_idx", {})
        idx_to_product_id = components.get("idx_to_product_id", {})

        # 사용자 인덱스 조회
        user_idx = user_id_to_idx.get(context.user_id)

        if user_idx is None:
            # 사용자 임베딩 없으면 cold start
            return await self._recommend_cold(context, limit, components)

        # 사용자 임베딩
        user_vec = user_embeddings[user_idx]

        # 모든 상품과의 유사도 계산 (코사인 유사도)
        scores = np.dot(product_embeddings, user_vec)
        scores = scores / (
            np.linalg.norm(product_embeddings, axis=1) *
            np.linalg.norm(user_vec) + 1e-8
        )

        # 이미 구매한 상품 제외 (선택적)
        user_matrix = components.get("user_product_matrix")
        if user_matrix is not None:
            purchased = user_matrix[user_idx].toarray().flatten()
            scores[purchased > 0] = -np.inf

        # Top-K 추출
        top_indices = np.argsort(scores)[::-1][:limit]
        product_ids = [idx_to_product_id.get(idx) for idx in top_indices]
        product_ids = [pid for pid in product_ids if pid is not None]

        products = await self._fetch_products_by_ids(product_ids)

        # 점수 추가
        for i, product in enumerate(products):
            if i < len(top_indices):
                product["recommendation_score"] = float(scores[top_indices[i]])
            product["recommendation_source"] = "embedding_similarity"

        return products

    async def _fetch_products_by_ids(
        self,
        product_ids: List[int],
    ) -> List[Dict[str, Any]]:
        """상품 ID로 상품 정보 조회"""
        if not product_ids:
            return []

        placeholders = ", ".join(f"${i+1}" for i in range(len(product_ids)))
        query = f"""
            SELECT p.id AS product_id, p.name, p.price, p.original_price,
                   p.category_id, p.seller_id,
                   COALESCE(ps.order_event_count, 0) AS order_count
            FROM products p
            LEFT JOIN product_stats ps ON p.id = ps.product_id
            WHERE p.id IN ({placeholders})
              AND p.status = 'active'
        """

        records = await self.db.fetch_all(query, *product_ids)

        # 원래 순서 유지
        product_map = {r["product_id"]: dict(r) for r in records}
        return [product_map[pid] for pid in product_ids if pid in product_map]

    async def _fallback_recommend(
        self,
        context: RecommendationContext,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """DB 기반 폴백 추천"""
        query = """
            SELECT p.id AS product_id, p.name, p.price, p.original_price,
                   p.category_id, p.seller_id,
                   COALESCE(ps.order_event_count, 0) AS order_count
            FROM products p
            LEFT JOIN product_stats ps ON p.id = ps.product_id
            WHERE p.status = 'active'
        """
        params = []

        if context.category_id:
            query += f" AND p.category_id = ${len(params)+1}"
            params.append(context.category_id)

        query += f" ORDER BY COALESCE(ps.order_event_count, 0) DESC LIMIT ${len(params)+1}"
        params.append(limit)

        records = await self.db.fetch_all(query, *params)

        products = []
        for record in records:
            product = dict(record)
            product["recommendation_score"] = float(product.get("order_count", 0))
            product["recommendation_source"] = "popularity_fallback"
            products.append(product)

        return products
```

## Docker 설정 수정

### docker-compose.yml (수정)

```yaml
pred:
  build: ./pred
  container_name: self-pred
  environment:
    # ... 기존 환경변수 ...
    MODELS_DIR: /app/models  # 모델 디렉토리 경로
  volumes:
    # pickle 모델 파일 마운트
    - ./pred/models:/app/models:ro
  # ... 나머지 설정 ...
```

### pred/api/dependencies.py (수정)

```python
from ml.model_loader import model_loader

async def init_dependencies() -> None:
    """의존성 초기화"""
    global _db, _cache, _orchestrator

    # DB 연결
    _db = Database()
    await _db.connect()

    # Cache 연결
    _cache = CacheManager()
    await _cache.connect()

    # Pickle 모델 로드 (중요!)
    await model_loader.load_all_models()

    # ML 모델 인스턴스 초기화
    from ml.models.self_personalized import SelfPersonalizedModel
    from ml.models.price_anomaly import PriceAnomalyModel

    self_model = SelfPersonalizedModel(_db, _cache)
    await self_model.initialize()  # pickle에서 로드

    price_model = PriceAnomalyModel(_db, _cache)
    await price_model.initialize()  # pickle에서 로드

    # Orchestrator 초기화
    _orchestrator = RecommendationOrchestrator(
        db=_db,
        cache=_cache,
        self_model=self_model,
        price_model=price_model,
    )
```

## 모델 메타데이터 파일

### pred/models/model_metadata.json

```json
{
  "last_updated": "2024-12-10T00:00:00",
  "models": {
    "self_personalized_v1": {
      "file": "self_personalized_v1.pkl",
      "version": "1.0.0",
      "created_at": "2024-12-10T00:00:00",
      "metrics": {
        "precision@10": 0.15,
        "recall@10": 0.08
      }
    },
    "price_anomaly_v1": {
      "file": "price_anomaly_v1.pkl",
      "version": "1.0.0",
      "created_at": "2024-12-10T00:00:00"
    }
  },
  "active_models": {
    "self_personalized": "self_personalized_v1",
    "price_anomaly": "price_anomaly_v1"
  }
}
```

## 배포 워크플로우

```
1. 로컬 개발 환경에서 노트북 실행
   └── notebooks/*.ipynb

2. 데이터 로딩 및 전처리
   └── DB 연결 → pandas DataFrame

3. 모델 학습
   └── scikit-learn, numpy, scipy

4. 모델 평가
   └── 정밀도, 재현율, NDCG 계산

5. pickle 파일 저장
   └── pred/models/*.pkl

6. Git 커밋 (pickle 파일 포함 또는 별도 저장소)

7. Docker 빌드 & 배포
   └── docker-compose up --build

8. 모델 자동 로드
   └── ModelLoader가 시작 시 로드
```

## 주의사항

1. **pickle 파일 크기**: 큰 모델은 Git LFS 사용 권장
2. **버전 관리**: model_metadata.json으로 활성 모델 버전 관리
3. **롤백**: 이전 버전 pickle 파일 보관으로 빠른 롤백 가능
4. **보안**: pickle 파일은 신뢰할 수 있는 소스에서만 로드
5. **메모리**: 대용량 모델 시 서버 메모리 확인 필요
