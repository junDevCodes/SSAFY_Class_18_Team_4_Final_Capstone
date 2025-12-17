"""
API 라우터 패키지

모든 API 라우터를 제공합니다.
"""

from api.routes.recommendation import router as recommendation_router
from api.routes.price import router as price_router
from api.routes.recipe import router as recipe_router
from api.routes.health import router as health_router

__all__ = [
    "recommendation_router",
    "price_router",
    "recipe_router",
    "health_router",
]
