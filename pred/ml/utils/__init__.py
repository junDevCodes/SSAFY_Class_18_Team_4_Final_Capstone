"""
ML 유틸리티 패키지

유사도 계산, 랭킹 알고리즘, numpy 호환성 레이어 제공
"""

from ml.utils.similarity import (
    cosine_similarity,
    cosine_similarity_batch,
    euclidean_distance,
    calculate_product_similarity,
    find_similar_items,
    calculate_jaccard_similarity,
    calculate_category_similarity,
)
from ml.utils.ranking import (
    mmr_rerank,
    category_diversify,
    weighted_score_fusion,
    reciprocal_rank_fusion,
    popularity_boost,
    filter_seen_items,
    apply_business_rules,
)
from ml.utils.numpy_compat import (
    load_numpy_compatible,
    save_numpy_compatible,
    is_compatible_format,
)

__all__ = [
    # Similarity
    "cosine_similarity",
    "cosine_similarity_batch",
    "euclidean_distance",
    "calculate_product_similarity",
    "find_similar_items",
    "calculate_jaccard_similarity",
    "calculate_category_similarity",
    # Ranking
    "mmr_rerank",
    "category_diversify",
    "weighted_score_fusion",
    "reciprocal_rank_fusion",
    "popularity_boost",
    "filter_seen_items",
    "apply_business_rules",
    # Numpy compatibility
    "load_numpy_compatible",
    "save_numpy_compatible",
    "is_compatible_format",
]
