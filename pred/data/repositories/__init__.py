"""
Repository 패키지

데이터 접근 계층의 모든 Repository를 제공합니다.
"""

from data.repositories.base import (
    BaseRepository,
    ReadOnlyRepository,
    WritableRepository,
)
from data.repositories.product_repo import (
    ProductRepository,
    ProductStatsRepository,
)
from data.repositories.user_repo import (
    UserRepository,
    UserInteractionRepository,
)
from data.repositories.price_repo import (
    PriceHistoryRepository,
    PriceAnomalyCacheRepository,
)
from data.repositories.instacart_repo import (
    InstacartTimePatternRepository,
    InstacartCategoryMappingRepository,
    InstacartProductMappingRepository,
    InstacartItemSimilarityRepository,
)
from data.repositories.recipe_repo import (
    RecipeRepository,
    RecipeIngredientRepository,
    IngredientProductRepository,
    RecipeGapFillingRepository,
)
from data.repositories.cache_repo import (
    RecommendationCacheRepository,
    EmbeddingCacheRepository,
    UserEmbeddingRepository,
)

__all__ = [
    # Base
    "BaseRepository",
    "ReadOnlyRepository",
    "WritableRepository",
    # Product
    "ProductRepository",
    "ProductStatsRepository",
    # User
    "UserRepository",
    "UserInteractionRepository",
    # Price
    "PriceHistoryRepository",
    "PriceAnomalyCacheRepository",
    # Instacart
    "InstacartTimePatternRepository",
    "InstacartCategoryMappingRepository",
    "InstacartProductMappingRepository",
    "InstacartItemSimilarityRepository",
    # Recipe
    "RecipeRepository",
    "RecipeIngredientRepository",
    "IngredientProductRepository",
    "RecipeGapFillingRepository",
    # Cache
    "RecommendationCacheRepository",
    "EmbeddingCacheRepository",
    "UserEmbeddingRepository",
]
