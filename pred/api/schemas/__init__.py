"""
API 스키마 패키지

모든 Pydantic 모델을 제공합니다.
"""

from api.schemas.recommendation import (
    # Enums
    PageType,
    UserType,
    TimeContext,
    CartRecommendationSource,
    # Request schemas
    RecommendationRequest,
    RecipeSuggestionRequest,
    ShoppingListRequest,
    PriceAnalysisRequest,
    CartRecommendationRequest,
    # Response schemas
    ProductRecommendation,
    ModelResult,
    RecommendationResponse,
    RecipeInfo,
    MissingIngredient,
    RecipeSuggestion,
    RecipeSuggestionResponse,
    PriceAnalysisResponse,
    CartProductRecommendation,
    CartRecommendationResponse,
    ErrorResponse,
    HealthResponse,
)

__all__ = [
    # Enums
    "PageType",
    "UserType",
    "TimeContext",
    "CartRecommendationSource",
    # Request schemas
    "RecommendationRequest",
    "RecipeSuggestionRequest",
    "ShoppingListRequest",
    "PriceAnalysisRequest",
    "CartRecommendationRequest",
    # Response schemas
    "ProductRecommendation",
    "ModelResult",
    "RecommendationResponse",
    "RecipeInfo",
    "MissingIngredient",
    "RecipeSuggestion",
    "RecipeSuggestionResponse",
    "PriceAnalysisResponse",
    "CartProductRecommendation",
    "CartRecommendationResponse",
    "ErrorResponse",
    "HealthResponse",
]
