"""
랭킹 알고리즘 유틸리티

추천 결과 순위화 및 다양성 보장
"""

from typing import Any, Callable, Dict, List, Optional, Set
import numpy as np

from core.logging import get_logger
from ml.utils.similarity import cosine_similarity

logger = get_logger(__name__)


def mmr_rerank(
    candidates: List[Dict],
    query_embedding: Optional[np.ndarray] = None,
    lambda_param: float = 0.7,
    top_k: int = 20,
    embedding_key: str = "embedding",
    score_key: str = "score",
) -> List[Dict]:
    """Maximal Marginal Relevance (MMR) 기반 재순위화

    관련성과 다양성의 균형을 맞춘 결과 반환

    MMR(Di) = λ * Rel(Di) - (1-λ) * max(Sim(Di, Dj)) for Dj in S

    Args:
        candidates: 후보 아이템 목록 (embedding, score 포함)
        query_embedding: 쿼리 임베딩 (선택적)
        lambda_param: 관련성 vs 다양성 균형 (0.0~1.0, 높을수록 관련성 중시)
        top_k: 반환할 개수
        embedding_key: 임베딩 필드명
        score_key: 점수 필드명

    Returns:
        재순위화된 아이템 목록
    """
    if not candidates:
        return []

    if len(candidates) <= top_k:
        return candidates

    # 임베딩이 없으면 점수 기반으로만 반환
    has_embeddings = all(
        embedding_key in c and c[embedding_key] is not None
        for c in candidates
    )

    if not has_embeddings:
        return sorted(
            candidates,
            key=lambda x: x.get(score_key, 0),
            reverse=True,
        )[:top_k]

    # MMR 알고리즘
    selected: List[Dict] = []
    remaining = candidates.copy()

    for _ in range(min(top_k, len(candidates))):
        if not remaining:
            break

        best_item = None
        best_score = float("-inf")

        for item in remaining:
            # 관련성 점수 (원래 점수)
            relevance = item.get(score_key, 0)

            # 다양성 점수 (선택된 항목들과의 최대 유사도)
            max_similarity = 0.0
            if selected:
                item_emb = item[embedding_key]
                for sel in selected:
                    sel_emb = sel[embedding_key]
                    sim = cosine_similarity(item_emb, sel_emb)
                    max_similarity = max(max_similarity, sim)

            # MMR 점수
            mmr_score = lambda_param * relevance - (1 - lambda_param) * max_similarity

            if mmr_score > best_score:
                best_score = mmr_score
                best_item = item

        if best_item:
            selected.append(best_item)
            remaining.remove(best_item)

    return selected


def category_diversify(
    items: List[Dict],
    top_k: int = 20,
    max_per_category: int = 5,
    category_key: str = "category_id",
    score_key: str = "score",
) -> List[Dict]:
    """카테고리 기반 다양성 보장

    각 카테고리에서 최대 max_per_category개만 선택

    Args:
        items: 아이템 목록
        top_k: 반환할 개수
        max_per_category: 카테고리당 최대 개수
        category_key: 카테고리 ID 필드명
        score_key: 점수 필드명

    Returns:
        다양화된 아이템 목록
    """
    if not items:
        return []

    # 점수순 정렬
    sorted_items = sorted(
        items,
        key=lambda x: x.get(score_key, 0),
        reverse=True,
    )

    result: List[Dict] = []
    category_counts: Dict[Any, int] = {}

    for item in sorted_items:
        if len(result) >= top_k:
            break

        category = item.get(category_key)
        current_count = category_counts.get(category, 0)

        if current_count < max_per_category:
            result.append(item)
            category_counts[category] = current_count + 1

    return result


def weighted_score_fusion(
    result_lists: List[List[Dict]],
    weights: List[float],
    id_key: str = "product_id",
    score_key: str = "score",
) -> List[Dict]:
    """가중 점수 퓨전

    여러 추천 결과 목록을 가중치 기반으로 병합

    Args:
        result_lists: 결과 목록들
        weights: 각 결과 목록의 가중치
        id_key: 아이템 ID 필드명
        score_key: 점수 필드명

    Returns:
        병합된 결과 목록
    """
    if not result_lists:
        return []

    # 아이템별 점수 집계
    fused_scores: Dict[Any, Dict] = {}

    for results, weight in zip(result_lists, weights):
        for rank, item in enumerate(results):
            item_id = item.get(id_key)
            if item_id is None:
                continue

            # 순위 기반 점수 (1위: 1.0, 하위로 갈수록 감소)
            rank_score = 1.0 / (rank + 1)
            weighted_score = rank_score * weight

            if item_id not in fused_scores:
                fused_scores[item_id] = {
                    **item,
                    score_key: 0.0,
                    "_sources": [],
                }

            fused_scores[item_id][score_key] += weighted_score
            fused_scores[item_id]["_sources"].append(weight)

    # 점수순 정렬
    result = sorted(
        fused_scores.values(),
        key=lambda x: x[score_key],
        reverse=True,
    )

    # 임시 필드 제거
    for item in result:
        if "_sources" in item:
            del item["_sources"]

    return result


def reciprocal_rank_fusion(
    result_lists: List[List[Dict]],
    k: int = 60,
    id_key: str = "product_id",
) -> List[Dict]:
    """Reciprocal Rank Fusion (RRF)

    여러 결과 목록을 RRF 알고리즘으로 병합

    RRF(d) = Σ 1/(k + rank(d))

    Args:
        result_lists: 결과 목록들
        k: RRF 상수 (기본 60)
        id_key: 아이템 ID 필드명

    Returns:
        병합된 결과 목록
    """
    if not result_lists:
        return []

    rrf_scores: Dict[Any, Dict] = {}

    for results in result_lists:
        for rank, item in enumerate(results):
            item_id = item.get(id_key)
            if item_id is None:
                continue

            rrf_score = 1.0 / (k + rank + 1)

            if item_id not in rrf_scores:
                rrf_scores[item_id] = {
                    **item,
                    "rrf_score": 0.0,
                }

            rrf_scores[item_id]["rrf_score"] += rrf_score

    return sorted(
        rrf_scores.values(),
        key=lambda x: x["rrf_score"],
        reverse=True,
    )


def popularity_boost(
    items: List[Dict],
    popularity_key: str = "order_count",
    score_key: str = "score",
    boost_factor: float = 0.1,
) -> List[Dict]:
    """인기도 부스트

    인기도에 따라 점수 보정

    Args:
        items: 아이템 목록
        popularity_key: 인기도 필드명
        score_key: 점수 필드명
        boost_factor: 부스트 강도 (0.0~1.0)

    Returns:
        부스트된 아이템 목록
    """
    if not items:
        return []

    # 인기도 정규화
    popularities = [item.get(popularity_key, 0) or 0 for item in items]
    max_popularity = max(popularities) if popularities else 1

    result = []
    for item, popularity in zip(items, popularities):
        boosted_item = item.copy()
        original_score = item.get(score_key, 0)

        if max_popularity > 0:
            normalized_popularity = popularity / max_popularity
            boost = boost_factor * normalized_popularity
            boosted_item[score_key] = original_score * (1 + boost)
        else:
            boosted_item[score_key] = original_score

        result.append(boosted_item)

    return sorted(result, key=lambda x: x[score_key], reverse=True)


def filter_seen_items(
    items: List[Dict],
    seen_item_ids: Set[int],
    id_key: str = "product_id",
) -> List[Dict]:
    """이미 본 아이템 필터링

    Args:
        items: 아이템 목록
        seen_item_ids: 이미 본 아이템 ID 집합
        id_key: 아이템 ID 필드명

    Returns:
        필터링된 아이템 목록
    """
    return [
        item for item in items
        if item.get(id_key) not in seen_item_ids
    ]


def apply_business_rules(
    items: List[Dict],
    rules: List[Callable[[Dict], bool]],
) -> List[Dict]:
    """비즈니스 규칙 적용

    Args:
        items: 아이템 목록
        rules: 적용할 규칙 함수 목록 (True를 반환하면 포함)

    Returns:
        규칙이 적용된 아이템 목록
    """
    result = items.copy()

    for rule in rules:
        result = [item for item in result if rule(item)]

    return result
