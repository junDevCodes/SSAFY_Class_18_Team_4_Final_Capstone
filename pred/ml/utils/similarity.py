"""
유사도 계산 유틸리티

상품/사용자 임베딩 기반 유사도 계산
"""

from typing import Dict, List, Optional, Tuple
import numpy as np

from core.logging import get_logger

logger = get_logger(__name__)


def cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    """코사인 유사도 계산

    Args:
        vec_a: 벡터 A
        vec_b: 벡터 B

    Returns:
        유사도 값 (-1.0 ~ 1.0)
    """
    norm_a = np.linalg.norm(vec_a)
    norm_b = np.linalg.norm(vec_b)

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return float(np.dot(vec_a, vec_b) / (norm_a * norm_b))


def cosine_similarity_batch(
    query_vec: np.ndarray,
    candidate_vecs: np.ndarray,
) -> np.ndarray:
    """배치 코사인 유사도 계산

    Args:
        query_vec: 쿼리 벡터 (1D)
        candidate_vecs: 후보 벡터들 (2D: N x D)

    Returns:
        유사도 배열 (N,)
    """
    query_norm = np.linalg.norm(query_vec)
    if query_norm == 0:
        return np.zeros(len(candidate_vecs))

    candidate_norms = np.linalg.norm(candidate_vecs, axis=1)
    # 0으로 나누기 방지
    candidate_norms[candidate_norms == 0] = 1.0

    similarities = np.dot(candidate_vecs, query_vec) / (candidate_norms * query_norm)
    return similarities


def euclidean_distance(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    """유클리드 거리 계산

    Args:
        vec_a: 벡터 A
        vec_b: 벡터 B

    Returns:
        거리 값 (0.0 ~ inf)
    """
    return float(np.linalg.norm(vec_a - vec_b))


def calculate_product_similarity(
    product_a: Dict,
    product_b: Dict,
    embedding_a: Optional[np.ndarray] = None,
    embedding_b: Optional[np.ndarray] = None,
) -> float:
    """두 상품 간 유사도 계산

    방법:
    1. 코사인 유사도 (임베딩 벡터)
    2. 같은 카테고리 보너스 (+0.1)
    3. 가격대 유사도 보너스 (±20% 이내 +0.05)

    Args:
        product_a: 상품 A 정보
        product_b: 상품 B 정보
        embedding_a: 상품 A 임베딩 (선택적)
        embedding_b: 상품 B 임베딩 (선택적)

    Returns:
        유사도 값 (0.0 ~ 1.0)
    """
    base_similarity = 0.0

    # 1. 임베딩 코사인 유사도
    if embedding_a is not None and embedding_b is not None:
        base_similarity = cosine_similarity(embedding_a, embedding_b)
        # -1 ~ 1을 0 ~ 1로 정규화
        base_similarity = (base_similarity + 1) / 2

    # 2. 카테고리 보너스
    category_bonus = 0.0
    if (product_a.get("category_id") and product_b.get("category_id") and
            product_a["category_id"] == product_b["category_id"]):
        category_bonus = 0.1

    # 3. 가격대 유사도 보너스
    price_bonus = 0.0
    price_a = product_a.get("price", 0)
    price_b = product_b.get("price", 0)

    if price_a > 0 and price_b > 0:
        price_ratio = min(price_a, price_b) / max(price_a, price_b)
        if price_ratio >= 0.8:  # ±20% 이내
            price_bonus = 0.05

    total_similarity = base_similarity + category_bonus + price_bonus
    return min(total_similarity, 1.0)


def find_similar_items(
    query_embedding: np.ndarray,
    item_embeddings: Dict[int, np.ndarray],
    top_k: int = 20,
    exclude_ids: Optional[List[int]] = None,
) -> List[Tuple[int, float]]:
    """유사 아이템 검색

    Args:
        query_embedding: 쿼리 임베딩
        item_embeddings: 아이템 ID → 임베딩 매핑
        top_k: 반환할 상위 개수
        exclude_ids: 제외할 아이템 ID 목록

    Returns:
        (아이템 ID, 유사도) 튜플 목록
    """
    exclude_ids = set(exclude_ids or [])

    # 후보 필터링
    candidates = [
        (item_id, emb)
        for item_id, emb in item_embeddings.items()
        if item_id not in exclude_ids
    ]

    if not candidates:
        return []

    # 유사도 계산
    item_ids = [c[0] for c in candidates]
    embeddings = np.array([c[1] for c in candidates])

    similarities = cosine_similarity_batch(query_embedding, embeddings)

    # 상위 K개 선택
    top_indices = np.argsort(similarities)[::-1][:top_k]

    results = [
        (item_ids[idx], float(similarities[idx]))
        for idx in top_indices
        if similarities[idx] > 0
    ]

    return results


def calculate_jaccard_similarity(set_a: set, set_b: set) -> float:
    """자카드 유사도 계산

    Args:
        set_a: 집합 A
        set_b: 집합 B

    Returns:
        자카드 유사도 (0.0 ~ 1.0)
    """
    if not set_a and not set_b:
        return 0.0

    intersection = len(set_a & set_b)
    union = len(set_a | set_b)

    return intersection / union if union > 0 else 0.0


def calculate_category_similarity(
    category_a: Optional[int],
    category_b: Optional[int],
    category_hierarchy: Optional[Dict[int, int]] = None,
) -> float:
    """카테고리 유사도 계산

    Args:
        category_a: 카테고리 A ID
        category_b: 카테고리 B ID
        category_hierarchy: 카테고리 → 상위 카테고리 매핑

    Returns:
        유사도 (0.0, 0.5, 1.0)
    """
    if not category_a or not category_b:
        return 0.0

    # 같은 카테고리
    if category_a == category_b:
        return 1.0

    # 계층 정보가 있으면 부모 카테고리 비교
    if category_hierarchy:
        parent_a = category_hierarchy.get(category_a)
        parent_b = category_hierarchy.get(category_b)

        # 같은 부모 카테고리
        if parent_a and parent_b and parent_a == parent_b:
            return 0.5

        # 한쪽이 다른쪽의 부모
        if parent_a == category_b or parent_b == category_a:
            return 0.5

    return 0.0
