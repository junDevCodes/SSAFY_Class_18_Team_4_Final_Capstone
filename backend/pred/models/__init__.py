"""
추천 시스템 데이터 모델

Instacart, Recipe, Embedding, Cache 관련 모델을 정의합니다.
"""

from .instacart import (
    PredInstacartDepartment,
    PredInstacartAisle,
    PredInstacartProduct,
    PredInstacartOrder,
    PredInstacartOrderItem,
)
from .aggregation import (
    PredInstacartTimePattern,
    PredInstacartCategoryMapping,
    PredProductMapping,
    PredItemSimilarity,
)
from .recipe import (
    PredRecipe,
    PredIngredient,
    PredRecipeIngredient,
    PredIngredientProduct,
)
from .embedding import (
    PredProductEmbedding,
    PredUserEmbedding,
)
from .cache import (
    PredRecommendationCache,
    PredPriceAnomalyCache,
)

__all__ = [
    # Instacart 원본
    'PredInstacartDepartment',
    'PredInstacartAisle',
    'PredInstacartProduct',
    'PredInstacartOrder',
    'PredInstacartOrderItem',
    # Instacart 집계
    'PredInstacartTimePattern',
    'PredInstacartCategoryMapping',
    'PredProductMapping',
    'PredItemSimilarity',
    # Recipe
    'PredRecipe',
    'PredIngredient',
    'PredRecipeIngredient',
    'PredIngredientProduct',
    # Embedding
    'PredProductEmbedding',
    'PredUserEmbedding',
    # Cache
    'PredRecommendationCache',
    'PredPriceAnomalyCache',
]
