"""
API 레이어 패키지

FastAPI 라우터와 의존성을 제공합니다.
"""

from api.routes import recommendation_router
from api.dependencies import (
    init_dependencies,
    close_dependencies,
    get_db,
    get_cache,
    get_orchestrator,
    get_time_context,
)

__all__ = [
    # Routers
    "recommendation_router",
    # Dependencies
    "init_dependencies",
    "close_dependencies",
    "get_db",
    "get_cache",
    "get_orchestrator",
    "get_time_context",
]
