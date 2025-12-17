"""
SelF 추천 시스템 API

FastAPI 기반 추천 서비스 메인 엔트리포인트
"""

from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import (
    recommendation_router,
    init_dependencies,
    close_dependencies,
)
from api.routes import price_router, recipe_router, health_router
from api.schemas import HealthResponse
from core.config import settings
from core.logging import setup_logging, get_logger

# 로깅 설정
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 생명주기 관리"""
    # 시작 시
    logger.info(
        "추천 서비스 시작",
        service=settings.service_name,
        version=settings.service_version,
        debug=settings.debug,
    )

    try:
        await init_dependencies()
        logger.info("의존성 초기화 완료")
    except Exception as e:
        logger.error("의존성 초기화 실패", error=str(e))
        # 초기화 실패해도 서비스는 시작 (헬스체크 등 기본 기능 제공)

    yield

    # 종료 시
    logger.info("추천 서비스 종료 중...")
    await close_dependencies()
    logger.info("추천 서비스 종료 완료")


# FastAPI 애플리케이션 생성
app = FastAPI(
    title=settings.service_name,
    version=settings.service_version,
    description="SelF 이커머스 플랫폼 추천 시스템 API",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(recommendation_router, prefix="/api/v1")
app.include_router(price_router, prefix="/api/v1")
app.include_router(recipe_router, prefix="/api/v1")
app.include_router(health_router, prefix="/api/v1")


# ============================================================================
# 기본 엔드포인트
# ============================================================================

@app.get("/")
async def read_root():
    """루트 경로 응답"""
    return {
        "service": settings.service_name,
        "version": settings.service_version,
        "status": "running",
        "docs": "/docs" if settings.debug else None,
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """헬스 체크 엔드포인트

    서비스, 데이터베이스, 캐시 상태 확인
    """
    from api.dependencies import _db, _cache

    db_status = "connected" if _db and _db._pool else "disconnected"
    cache_status = "connected" if _cache and _cache._client else "disconnected"

    return HealthResponse(
        status="healthy" if db_status == "connected" else "degraded",
        version=settings.service_version,
        database=db_status,
        cache=cache_status,
        timestamp=datetime.now(),
    )


@app.get("/ready")
async def readiness_check():
    """준비 상태 체크 (Kubernetes readiness probe용)"""
    from api.dependencies import _db, _cache, _orchestrator

    is_ready = all([
        _db and _db._pool,
        _orchestrator is not None,
    ])

    if is_ready:
        return {"status": "ready"}
    else:
        return {"status": "not_ready"}, 503


# ============================================================================
# 레거시 엔드포인트 (하위 호환성)
# ============================================================================

@app.post("/api/recommend")
async def recommend_products_legacy():
    """추천 API (레거시) - /api/v1/recommendations 사용 권장"""
    return {
        "status": "deprecated",
        "message": "이 엔드포인트는 deprecated됩니다. /api/v1/recommendations를 사용하세요.",
    }


@app.post("/api/predict-price")
async def predict_price_legacy():
    """가격 예측 API (레거시)"""
    return {
        "status": "deprecated",
        "message": "이 엔드포인트는 deprecated됩니다. /api/v1/recommendations/deals를 사용하세요.",
    }


# ============================================================================
# 직접 실행 시
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
