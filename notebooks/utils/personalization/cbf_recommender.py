"""
콘텐츠 기반 필터링 (Content-Based Filtering) 추천 모듈

Cold Start 사용자 및 아이템을 위한 콘텐츠 기반 추천 시스템.
아이템 속성(카테고리, 가격대, 브랜드 등)을 활용하여 유사도 기반 추천 제공.

학술적 근거:
- Lops, P., de Gemmis, M., & Semeraro, G. (2011).
  "Content-based Recommender Systems: State of the Art and Trends."
- Pazzani, M. J., & Billsus, D. (2007).
  "Content-Based Recommendation Systems."
- Burke, R. (2002).
  "Hybrid Recommender Systems: Survey and Experiments."

핵심 기법:
1. TF-IDF 벡터화 for 텍스트 속성
2. One-Hot 인코딩 for 카테고리 속성
3. 가격 정규화 for 수치 속성
4. 코사인 유사도 for 아이템 유사도 계산
5. 사용자 프로파일 = 상호작용 아이템의 가중 평균 벡터
"""

from __future__ import annotations

import pickle
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any

import numpy as np
from scipy import sparse
from scipy.sparse import csr_matrix

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.preprocessing import OneHotEncoder, MinMaxScaler
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

from .weight_config import (
    INTERACTION_WEIGHTS,
    TIME_DECAY_WEIGHTS,
    compute_interaction_score,
)


# ============================================================================
# 카테고리 유사도 매트릭스
# ============================================================================

@dataclass
class CategorySimilarity:
    """
    카테고리 간 의미적 유사도 계산

    식료품 도메인 특화:
    - 대체재 관계 (우유 ↔ 두유)
    - 보완재 관계 (빵 → 잼)
    - 계절성 상관관계

    학술 근거:
    - Taxonomy-based similarity (Wu & Palmer, 1994)
    - Domain-specific ontology (Cantador et al., 2011)
    """

    # 카테고리 계층 구조 (대분류 → 중분류 → 소분류)
    # SelF 상품 카테고리 기준
    CATEGORY_HIERARCHY: Dict[str, Dict[str, List[str]]] = field(default_factory=lambda: {
        "신선식품": {
            "과일": ["사과", "배", "감귤", "딸기", "포도", "바나나", "수박", "참외"],
            "채소": ["배추", "무", "양파", "감자", "당근", "토마토", "오이", "상추"],
            "육류": ["소고기", "돼지고기", "닭고기", "양고기", "오리고기"],
            "수산물": ["생선", "조개", "새우", "오징어", "해조류"],
        },
        "가공식품": {
            "유제품": ["우유", "치즈", "요거트", "버터", "아이스크림"],
            "빵/과자": ["식빵", "케이크", "쿠키", "크래커", "스낵"],
            "면류": ["라면", "냉동면", "생면", "파스타"],
            "통조림": ["참치캔", "옥수수캔", "콩캔", "과일캔"],
        },
        "음료": {
            "생수/음료": ["생수", "탄산음료", "주스", "커피", "차"],
            "주류": ["맥주", "소주", "와인", "막걸리"],
        },
        "간편식": {
            "즉석식품": ["즉석밥", "레토르트", "냉동식품", "도시락"],
            "반찬류": ["김치", "젓갈", "장아찌", "샐러드"],
        },
    })

    # 대체재 관계 (교환 가능한 상품들)
    SUBSTITUTE_PAIRS: List[Tuple[str, str, float]] = field(default_factory=lambda: [
        ("우유", "두유", 0.8),
        ("소고기", "돼지고기", 0.6),
        ("사과", "배", 0.7),
        ("라면", "냉동면", 0.5),
        ("생수", "탄산음료", 0.3),
        ("닭고기", "오리고기", 0.7),
        ("버터", "마가린", 0.8),
        ("설탕", "올리고당", 0.6),
    ])

    # 보완재 관계 (함께 구매되는 상품들)
    COMPLEMENT_PAIRS: List[Tuple[str, str, float]] = field(default_factory=lambda: [
        ("빵", "잼", 0.9),
        ("빵", "버터", 0.85),
        ("라면", "김치", 0.8),
        ("우유", "시리얼", 0.85),
        ("고기", "쌈채소", 0.9),
        ("파스타", "소스", 0.9),
        ("생선", "레몬", 0.7),
        ("삼겹살", "상추", 0.95),
    ])

    similarity_matrix: Optional[np.ndarray] = None
    category_to_idx: Dict[str, int] = field(default_factory=dict)

    def build_similarity_matrix(self, categories: List[str]) -> np.ndarray:
        """
        카테고리 간 유사도 행렬 생성

        Args:
            categories: 카테고리 목록

        Returns:
            similarity_matrix: (n_categories, n_categories) 유사도 행렬
        """
        n_categories = len(categories)
        self.category_to_idx = {cat: idx for idx, cat in enumerate(categories)}

        # 기본 유사도 = Identity (자기 자신 = 1.0)
        similarity = np.eye(n_categories, dtype=np.float32)

        # 같은 대분류 내 카테고리는 기본 유사도 0.3
        for major, sub_cats in self.CATEGORY_HIERARCHY.items():
            all_cats_in_major = []
            for sub_cat_list in sub_cats.values():
                all_cats_in_major.extend(sub_cat_list)

            for cat1 in all_cats_in_major:
                if cat1 not in self.category_to_idx:
                    continue
                for cat2 in all_cats_in_major:
                    if cat2 not in self.category_to_idx or cat1 == cat2:
                        continue
                    idx1, idx2 = self.category_to_idx[cat1], self.category_to_idx[cat2]
                    similarity[idx1, idx2] = max(similarity[idx1, idx2], 0.3)

        # 같은 중분류 내 카테고리는 유사도 0.6
        for major, sub_dict in self.CATEGORY_HIERARCHY.items():
            for sub_name, sub_cats in sub_dict.items():
                for cat1 in sub_cats:
                    if cat1 not in self.category_to_idx:
                        continue
                    for cat2 in sub_cats:
                        if cat2 not in self.category_to_idx or cat1 == cat2:
                            continue
                        idx1, idx2 = self.category_to_idx[cat1], self.category_to_idx[cat2]
                        similarity[idx1, idx2] = max(similarity[idx1, idx2], 0.6)

        # 대체재 관계 반영
        for cat1, cat2, sim in self.SUBSTITUTE_PAIRS:
            if cat1 in self.category_to_idx and cat2 in self.category_to_idx:
                idx1, idx2 = self.category_to_idx[cat1], self.category_to_idx[cat2]
                similarity[idx1, idx2] = max(similarity[idx1, idx2], sim)
                similarity[idx2, idx1] = max(similarity[idx2, idx1], sim)

        # 보완재 관계는 유사도에 약간만 반영 (0.3 정도)
        for cat1, cat2, sim in self.COMPLEMENT_PAIRS:
            if cat1 in self.category_to_idx and cat2 in self.category_to_idx:
                idx1, idx2 = self.category_to_idx[cat1], self.category_to_idx[cat2]
                boost = sim * 0.3  # 보완재는 약하게 반영
                similarity[idx1, idx2] = max(similarity[idx1, idx2], boost)
                similarity[idx2, idx1] = max(similarity[idx2, idx1], boost)

        self.similarity_matrix = similarity
        return similarity

    def get_similarity(self, cat1: str, cat2: str) -> float:
        """두 카테고리 간 유사도 조회"""
        if self.similarity_matrix is None:
            return 1.0 if cat1 == cat2 else 0.0

        idx1 = self.category_to_idx.get(cat1)
        idx2 = self.category_to_idx.get(cat2)

        if idx1 is None or idx2 is None:
            return 1.0 if cat1 == cat2 else 0.0

        return float(self.similarity_matrix[idx1, idx2])

    def get_similar_categories(
        self,
        category: str,
        top_k: int = 5,
        min_similarity: float = 0.3
    ) -> List[Tuple[str, float]]:
        """유사한 카테고리 목록 조회"""
        if self.similarity_matrix is None or category not in self.category_to_idx:
            return []

        idx = self.category_to_idx[category]
        similarities = self.similarity_matrix[idx]

        # 인덱스 → 카테고리명 역매핑
        idx_to_cat = {v: k for k, v in self.category_to_idx.items()}

        # 유사도 순 정렬 (자기 자신 제외)
        similar = [
            (idx_to_cat[i], float(similarities[i]))
            for i in np.argsort(similarities)[::-1]
            if i != idx and similarities[i] >= min_similarity
        ]

        return similar[:top_k]


# ============================================================================
# 콘텐츠 기반 추천기
# ============================================================================

class ContentBasedRecommender:
    """
    콘텐츠 기반 필터링 추천기

    Cold Start 문제 해결:
    - 신규 사용자: 인기 상품 + 카테고리 선호도 기반 추천
    - 신규 아이템: 속성 유사 아이템 기반 추천

    특징 벡터 구성:
    1. 카테고리 (One-Hot)
    2. 가격대 (정규화)
    3. 상품명 키워드 (TF-IDF, 선택적)
    4. 속성 태그 (Multi-Hot)

    학술 근거:
    - Lops et al. (2011): CBF State of the Art
    - 하이브리드 시스템에서 Cold Start 해결 핵심 컴포넌트
    """

    def __init__(
        self,
        use_tfidf: bool = True,
        min_category_items: int = 5,
        price_bins: int = 10,
    ):
        """
        Args:
            use_tfidf: 상품명 TF-IDF 사용 여부
            min_category_items: 카테고리 최소 상품 수 (미달시 병합)
            price_bins: 가격 구간 수
        """
        self.use_tfidf = use_tfidf and SKLEARN_AVAILABLE
        self.min_category_items = min_category_items
        self.price_bins = price_bins

        # 모델 컴포넌트
        self.item_features: Optional[np.ndarray] = None  # (n_items, n_features)
        self.item_similarity: Optional[np.ndarray] = None  # (n_items, n_items)
        self.category_similarity = CategorySimilarity()

        # 매핑 정보
        self.product_id_to_idx: Dict[int, int] = {}
        self.idx_to_product_id: Dict[int, int] = {}
        self.category_to_idx: Dict[str, int] = {}
        self.idx_to_category: Dict[int, str] = {}

        # 카테고리별 인기 상품 (Cold Start용)
        self.category_popular_items: Dict[str, List[int]] = {}
        self.global_popular_items: List[int] = []

        # 인코더 (sklearn 사용시)
        self.tfidf_vectorizer = None
        self.onehot_encoder = None
        self.price_scaler = None

        # 메타데이터
        self.n_items = 0
        self.n_features = 0
        self.feature_names: List[str] = []

    def fit(
        self,
        products: List[Dict[str, Any]],
        interactions: Optional[Dict[int, Dict[int, float]]] = None,
    ) -> 'ContentBasedRecommender':
        """
        상품 속성 기반 특징 벡터 생성

        Args:
            products: 상품 정보 리스트
                [{'product_id': int, 'name': str, 'category': str,
                  'price': float, 'tags': List[str]}, ...]
            interactions: {user_id: {product_id: score}} 상호작용 정보 (인기도 계산용)

        Returns:
            self
        """
        if not products:
            raise ValueError("products 리스트가 비어있습니다.")

        self.n_items = len(products)

        # 1. 상품 ID 매핑 생성
        self._build_product_mapping(products)

        # 2. 카테고리 매핑 생성
        categories = list(set(p.get('category', 'unknown') for p in products))
        self._build_category_mapping(categories)

        # 3. 특징 벡터 생성
        self._build_feature_vectors(products)

        # 4. 아이템 유사도 행렬 계산
        self._compute_item_similarity()

        # 5. 카테고리별/전역 인기 상품 계산
        if interactions:
            self._compute_popularity(products, interactions)
        else:
            self._compute_default_popularity(products)

        # 6. 카테고리 유사도 행렬 생성
        self.category_similarity.build_similarity_matrix(categories)

        return self

    def _build_product_mapping(self, products: List[Dict[str, Any]]) -> None:
        """상품 ID ↔ 인덱스 매핑 생성"""
        for idx, product in enumerate(products):
            product_id = product['product_id']
            self.product_id_to_idx[product_id] = idx
            self.idx_to_product_id[idx] = product_id

    def _build_category_mapping(self, categories: List[str]) -> None:
        """카테고리 ↔ 인덱스 매핑 생성"""
        for idx, category in enumerate(sorted(categories)):
            self.category_to_idx[category] = idx
            self.idx_to_category[idx] = category

    def _build_feature_vectors(self, products: List[Dict[str, Any]]) -> None:
        """
        상품별 특징 벡터 생성

        구성:
        - 카테고리 One-Hot: (n_categories,)
        - 가격 정규화: (1,)
        - TF-IDF (선택): (tfidf_dim,)
        - 태그 Multi-Hot: (n_tags,)
        """
        feature_parts = []
        self.feature_names = []

        # 1. 카테고리 One-Hot
        n_categories = len(self.category_to_idx)
        category_features = np.zeros((self.n_items, n_categories), dtype=np.float32)

        for idx, product in enumerate(products):
            cat = product.get('category', 'unknown')
            if cat in self.category_to_idx:
                category_features[idx, self.category_to_idx[cat]] = 1.0

        feature_parts.append(category_features)
        self.feature_names.extend([f"category_{c}" for c in self.idx_to_category.values()])

        # 2. 가격 정규화 (0~1)
        prices = np.array([p.get('price', 0.0) for p in products], dtype=np.float32)

        if prices.max() > prices.min():
            price_normalized = (prices - prices.min()) / (prices.max() - prices.min())
        else:
            price_normalized = np.zeros_like(prices)

        feature_parts.append(price_normalized.reshape(-1, 1))
        self.feature_names.append("price_normalized")

        # 3. TF-IDF (상품명 기반, sklearn 필요)
        if self.use_tfidf and SKLEARN_AVAILABLE:
            names = [p.get('name', '') for p in products]

            self.tfidf_vectorizer = TfidfVectorizer(
                max_features=100,  # 메모리 효율성
                min_df=2,
                max_df=0.95,
                ngram_range=(1, 2),
            )

            try:
                tfidf_features = self.tfidf_vectorizer.fit_transform(names).toarray()
                feature_parts.append(tfidf_features.astype(np.float32))
                self.feature_names.extend([
                    f"tfidf_{w}" for w in self.tfidf_vectorizer.get_feature_names_out()
                ])
            except ValueError:
                # 텍스트가 부족한 경우 스킵
                pass

        # 4. 태그 Multi-Hot
        all_tags: Set[str] = set()
        for product in products:
            tags = product.get('tags', [])
            if isinstance(tags, list):
                all_tags.update(tags)

        if all_tags:
            tag_to_idx = {tag: idx for idx, tag in enumerate(sorted(all_tags))}
            n_tags = len(tag_to_idx)
            tag_features = np.zeros((self.n_items, n_tags), dtype=np.float32)

            for idx, product in enumerate(products):
                tags = product.get('tags', [])
                if isinstance(tags, list):
                    for tag in tags:
                        if tag in tag_to_idx:
                            tag_features[idx, tag_to_idx[tag]] = 1.0

            feature_parts.append(tag_features)
            self.feature_names.extend([f"tag_{t}" for t in tag_to_idx.keys()])

        # 5. 특징 벡터 결합
        self.item_features = np.hstack(feature_parts)
        self.n_features = self.item_features.shape[1]

        # L2 정규화 (코사인 유사도 사전 계산용)
        norms = np.linalg.norm(self.item_features, axis=1, keepdims=True)
        norms[norms == 0] = 1.0  # 0-division 방지
        self.item_features = self.item_features / norms

    def _compute_item_similarity(self) -> None:
        """
        아이템 간 코사인 유사도 행렬 계산

        문제 해결:
        - 기존: 같은 카테고리 아이템들이 유사도 1.0으로 나옴 (변별력 없음)
        - 해결: Min-Max 스케일링으로 유사도 범위를 0~1로 재조정
        """
        if self.item_features is None:
            return

        # 정규화된 벡터의 내적 = 코사인 유사도
        # 메모리 효율성: 큰 데이터셋에서는 희소 형태 고려
        if self.n_items <= 10000:
            raw_similarity = self.item_features @ self.item_features.T

            # 유사도 스케일링 (변별력 향상)
            # 자기 자신(대각선)을 제외하고 min-max 정규화
            np.fill_diagonal(raw_similarity, 0)  # 대각선 임시 제거

            min_val = raw_similarity.min()
            max_val = raw_similarity.max()

            if max_val - min_val > 1e-8:
                # Min-Max 스케일링: 0 ~ 0.99 범위로 조정 (1.0은 자기 자신 전용)
                self.item_similarity = (raw_similarity - min_val) / (max_val - min_val) * 0.99
            else:
                self.item_similarity = raw_similarity

            # 대각선 복원 (자기 자신 = 1.0)
            np.fill_diagonal(self.item_similarity, 1.0)
        else:
            # 대규모 데이터: 유사도 행렬을 on-demand로 계산
            self.item_similarity = None

    def _compute_popularity(
        self,
        products: List[Dict[str, Any]],
        interactions: Dict[int, Dict[int, float]]
    ) -> None:
        """상호작용 기반 인기도 계산"""
        # 상품별 상호작용 점수 합산
        item_scores: Dict[int, float] = {}

        for user_id, user_interactions in interactions.items():
            for product_id, score in user_interactions.items():
                if product_id not in item_scores:
                    item_scores[product_id] = 0.0
                item_scores[product_id] += score

        # 카테고리별 인기 상품
        category_items: Dict[str, List[Tuple[int, float]]] = {}

        for product in products:
            product_id = product['product_id']
            category = product.get('category', 'unknown')
            score = item_scores.get(product_id, 0.0)

            if category not in category_items:
                category_items[category] = []
            category_items[category].append((product_id, score))

        # 카테고리별 정렬 (인기도 순)
        for category, items in category_items.items():
            sorted_items = sorted(items, key=lambda x: x[1], reverse=True)
            self.category_popular_items[category] = [pid for pid, _ in sorted_items[:100]]

        # 전역 인기 상품
        all_items_sorted = sorted(item_scores.items(), key=lambda x: x[1], reverse=True)
        self.global_popular_items = [pid for pid, _ in all_items_sorted[:200]]

    def _compute_default_popularity(self, products: List[Dict[str, Any]]) -> None:
        """상호작용 데이터 없을 때 기본 인기도 (상품 ID 순)"""
        category_items: Dict[str, List[int]] = {}

        for product in products:
            product_id = product['product_id']
            category = product.get('category', 'unknown')

            if category not in category_items:
                category_items[category] = []
            category_items[category].append(product_id)

        self.category_popular_items = category_items
        self.global_popular_items = [p['product_id'] for p in products]

    def get_similar_items(
        self,
        product_id: int,
        top_k: int = 10,
        exclude_self: bool = True
    ) -> List[Tuple[int, float]]:
        """
        유사 아이템 조회

        Args:
            product_id: 기준 상품 ID
            top_k: 반환할 아이템 수
            exclude_self: 자기 자신 제외 여부

        Returns:
            [(product_id, similarity_score), ...]
        """
        if product_id not in self.product_id_to_idx:
            return []

        idx = self.product_id_to_idx[product_id]

        if self.item_similarity is not None:
            # 사전 계산된 유사도 행렬 사용
            similarities = self.item_similarity[idx]
        else:
            # On-demand 계산
            if self.item_features is None:
                return []
            similarities = self.item_features @ self.item_features[idx]

        # 정렬
        sorted_indices = np.argsort(similarities)[::-1]

        results = []
        for i in sorted_indices:
            if exclude_self and i == idx:
                continue
            if len(results) >= top_k:
                break
            results.append((self.idx_to_product_id[i], float(similarities[i])))

        return results

    def recommend_for_user(
        self,
        user_interactions: Dict[int, float],
        top_k: int = 10,
        exclude_interacted: bool = False,
        category_filter: Optional[str] = None,
    ) -> List[Tuple[int, float]]:
        """
        사용자 프로파일 기반 추천

        사용자 프로파일 = 상호작용 아이템의 가중 평균 벡터

        Args:
            user_interactions: {product_id: interaction_score}
            top_k: 추천 수
            exclude_interacted: 이미 상호작용한 아이템 제외 (식료품은 False 권장)
            category_filter: 특정 카테고리만 필터링

        Returns:
            [(product_id, score), ...]
        """
        if not user_interactions:
            # Cold Start: 인기 상품 반환
            if category_filter and category_filter in self.category_popular_items:
                popular = self.category_popular_items[category_filter][:top_k]
            else:
                popular = self.global_popular_items[:top_k]
            return [(pid, 1.0 - i * 0.01) for i, pid in enumerate(popular)]

        if self.item_features is None:
            return []

        # 1. 사용자 프로파일 벡터 계산 (가중 평균)
        user_vector = np.zeros(self.n_features, dtype=np.float32)
        total_weight = 0.0

        for product_id, score in user_interactions.items():
            if product_id not in self.product_id_to_idx:
                continue
            idx = self.product_id_to_idx[product_id]
            user_vector += self.item_features[idx] * score
            total_weight += score

        if total_weight > 0:
            user_vector /= total_weight

        # L2 정규화
        norm = np.linalg.norm(user_vector)
        if norm > 0:
            user_vector /= norm

        # 2. 모든 아이템과의 유사도 계산
        similarities = self.item_features @ user_vector

        # 3. 필터링 및 정렬
        interacted_set = set(user_interactions.keys()) if exclude_interacted else set()

        results = []
        sorted_indices = np.argsort(similarities)[::-1]

        for idx in sorted_indices:
            product_id = self.idx_to_product_id[idx]

            # 제외 조건
            if product_id in interacted_set:
                continue

            # 카테고리 필터
            if category_filter:
                # 카테고리 정보 확인 필요 (products 저장 필요)
                pass  # TODO: 카테고리 필터 구현

            results.append((product_id, float(similarities[idx])))

            if len(results) >= top_k:
                break

        return results

    def recommend_cold_start(
        self,
        preferred_categories: Optional[List[str]] = None,
        top_k: int = 10,
    ) -> List[Tuple[int, float]]:
        """
        Cold Start 사용자를 위한 추천

        전략:
        1. 선호 카테고리가 있으면 해당 카테고리 인기 상품
        2. 없으면 전역 인기 상품
        3. 유사 카테고리도 포함

        Args:
            preferred_categories: 선호 카테고리 목록 (설문 등에서 수집)
            top_k: 추천 수

        Returns:
            [(product_id, score), ...]
        """
        if not preferred_categories:
            # 전역 인기 상품
            popular = self.global_popular_items[:top_k]
            return [(pid, 1.0 - i * 0.01) for i, pid in enumerate(popular)]

        results = []
        seen_products: Set[int] = set()

        # 각 선호 카테고리에서 상품 수집
        for category in preferred_categories:
            if category in self.category_popular_items:
                for pid in self.category_popular_items[category]:
                    if pid not in seen_products:
                        results.append(pid)
                        seen_products.add(pid)

            # 유사 카테고리도 추가
            similar_cats = self.category_similarity.get_similar_categories(
                category, top_k=3, min_similarity=0.5
            )
            for sim_cat, sim_score in similar_cats:
                if sim_cat in self.category_popular_items:
                    for pid in self.category_popular_items[sim_cat][:5]:
                        if pid not in seen_products:
                            results.append(pid)
                            seen_products.add(pid)

        # 부족하면 전역 인기 상품으로 채움
        for pid in self.global_popular_items:
            if pid not in seen_products:
                results.append(pid)
                seen_products.add(pid)
            if len(results) >= top_k:
                break

        return [(pid, 1.0 - i * 0.01) for i, pid in enumerate(results[:top_k])]

    def get_item_features(self, product_id: int) -> Optional[np.ndarray]:
        """특정 상품의 특징 벡터 조회"""
        if product_id not in self.product_id_to_idx or self.item_features is None:
            return None
        idx = self.product_id_to_idx[product_id]
        return self.item_features[idx].copy()

    def save(self, filepath: str) -> None:
        """모델 저장"""
        data = {
            'version': '1.0.0',
            'n_items': self.n_items,
            'n_features': self.n_features,
            'item_features': self.item_features,
            'item_similarity': self.item_similarity,
            'product_id_to_idx': self.product_id_to_idx,
            'idx_to_product_id': self.idx_to_product_id,
            'category_to_idx': self.category_to_idx,
            'idx_to_category': self.idx_to_category,
            'category_popular_items': self.category_popular_items,
            'global_popular_items': self.global_popular_items,
            'feature_names': self.feature_names,
            'category_similarity_matrix': self.category_similarity.similarity_matrix,
            'category_similarity_mapping': self.category_similarity.category_to_idx,
        }

        with open(filepath, 'wb') as f:
            pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)

    @classmethod
    def load(cls, filepath: str) -> 'ContentBasedRecommender':
        """모델 로드"""
        with open(filepath, 'rb') as f:
            data = pickle.load(f)

        recommender = cls()
        recommender.n_items = data['n_items']
        recommender.n_features = data['n_features']
        recommender.item_features = data['item_features']
        recommender.item_similarity = data['item_similarity']
        recommender.product_id_to_idx = data['product_id_to_idx']
        recommender.idx_to_product_id = data['idx_to_product_id']
        recommender.category_to_idx = data['category_to_idx']
        recommender.idx_to_category = data['idx_to_category']
        recommender.category_popular_items = data['category_popular_items']
        recommender.global_popular_items = data['global_popular_items']
        recommender.feature_names = data['feature_names']

        # CategorySimilarity 복원
        recommender.category_similarity = CategorySimilarity()
        recommender.category_similarity.similarity_matrix = data.get('category_similarity_matrix')
        recommender.category_similarity.category_to_idx = data.get('category_similarity_mapping', {})

        return recommender


# ============================================================================
# 유틸리티 함수
# ============================================================================

def create_cbf_from_dataframe(
    products_df,
    interactions_df=None,
    product_id_col: str = 'product_id',
    name_col: str = 'product_name',
    category_col: str = 'category',
    price_col: str = 'price',
) -> ContentBasedRecommender:
    """
    DataFrame에서 CBF 추천기 생성

    Args:
        products_df: 상품 DataFrame
        interactions_df: 상호작용 DataFrame (선택)
        product_id_col, name_col, category_col, price_col: 컬럼명

    Returns:
        학습된 ContentBasedRecommender
    """
    # 상품 리스트 생성
    products = []
    for _, row in products_df.iterrows():
        products.append({
            'product_id': int(row[product_id_col]),
            'name': str(row.get(name_col, '')),
            'category': str(row.get(category_col, 'unknown')),
            'price': float(row.get(price_col, 0.0)),
            'tags': [],  # TODO: 태그 컬럼 지원
        })

    # 상호작용 딕셔너리 생성
    interactions = None
    if interactions_df is not None:
        interactions = {}
        for _, row in interactions_df.iterrows():
            user_id = int(row['user_id'])
            product_id = int(row['product_id'])
            score = float(row.get('score', 1.0))

            if user_id not in interactions:
                interactions[user_id] = {}
            interactions[user_id][product_id] = score

    # 추천기 학습
    recommender = ContentBasedRecommender()
    recommender.fit(products, interactions)

    return recommender


__all__ = [
    'CategorySimilarity',
    'ContentBasedRecommender',
    'create_cbf_from_dataframe',
]
