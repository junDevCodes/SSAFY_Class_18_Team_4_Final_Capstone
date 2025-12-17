"""
헬스체크 및 메트릭스 API 라우터

서비스 상태 확인 및 모니터링 엔드포인트
"""

from datetime import datetime
from typing import Dict, Optional

from fastapi import APIRouter, Depends

from api.dependencies import get_db, get_cache
from core.database import Database
from core.cache import CacheManager
from core.config import settings
from core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    summary="헬스 체크",
    description="서비스 상태 확인",
)
async def health_check(
    db: Database = Depends(get_db),
    cache: CacheManager = Depends(get_cache),
):
    """헬스 체크 엔드포인트

    서비스, 데이터베이스, 캐시 상태 확인
    """
    # DB 상태 확인
    db_status = "unknown"
    db_latency_ms = 0
    try:
        start = datetime.now()
        await db.fetch_one("SELECT 1")
        db_latency_ms = (datetime.now() - start).total_seconds() * 1000
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    # 캐시 상태 확인
    cache_status = "unknown"
    cache_latency_ms = 0
    try:
        start = datetime.now()
        await cache.ping()
        cache_latency_ms = (datetime.now() - start).total_seconds() * 1000
        cache_status = "connected"
    except Exception as e:
        cache_status = f"error: {str(e)}"

    # 전체 상태 판단
    is_healthy = db_status == "connected"
    status = "healthy" if is_healthy else "degraded"

    return {
        "status": status,
        "version": settings.service_version,
        "timestamp": datetime.now().isoformat(),
        "components": {
            "database": {
                "status": db_status,
                "latency_ms": db_latency_ms,
            },
            "cache": {
                "status": cache_status,
                "latency_ms": cache_latency_ms,
            },
        },
    }


@router.get(
    "/ready",
    summary="준비 상태 체크",
    description="Kubernetes readiness probe용",
)
async def readiness_check(
    db: Database = Depends(get_db),
):
    """준비 상태 체크 (Kubernetes readiness probe용)"""
    try:
        await db.fetch_one("SELECT 1")
        return {"status": "ready"}
    except Exception:
        return {"status": "not_ready"}, 503


@router.get(
    "/live",
    summary="활성 상태 체크",
    description="Kubernetes liveness probe용",
)
async def liveness_check():
    """활성 상태 체크 (Kubernetes liveness probe용)"""
    return {"status": "alive"}


@router.get(
    "/metrics",
    summary="메트릭스 조회",
    description="서비스 메트릭스 조회",
)
async def get_metrics(
    db: Database = Depends(get_db),
    cache: CacheManager = Depends(get_cache),
):
    """서비스 메트릭스 조회"""
    metrics = {
        "service": {
            "name": settings.service_name,
            "version": settings.service_version,
            "uptime": "N/A",  # 실제 구현 시 프로세스 시작 시간 기록 필요
        },
        "database": {},
        "cache": {},
        "models": {},
    }

    # DB 메트릭스
    try:
        # 테이블별 레코드 수
        tables = [
            "pred_instacart_products",
            "pred_instacart_time_patterns",
            "pred_recipes",
            "pred_ingredients",
            "pred_recommendation_cache",
            "pred_price_anomaly_cache",
        ]

        for table in tables:
            try:
                result = await db.fetch_one(f"SELECT COUNT(*) as cnt FROM {table}")
                metrics["database"][table] = result["cnt"] if result else 0
            except Exception:
                metrics["database"][table] = "N/A"

    except Exception as e:
        metrics["database"]["error"] = str(e)

    # 캐시 메트릭스
    try:
        cache_info = await cache.info()
        metrics["cache"] = {
            "connected": True,
            "keys": cache_info.get("db0", {}).get("keys", 0) if cache_info else 0,
        }
    except Exception as e:
        metrics["cache"] = {"connected": False, "error": str(e)}

    return metrics


@router.get(
    "/config",
    summary="설정 조회",
    description="서비스 설정 조회 (민감 정보 제외)",
)
async def get_config():
    """서비스 설정 조회 (민감 정보 제외)"""
    return {
        "service_name": settings.service_name,
        "service_version": settings.service_version,
        "debug": settings.debug,
        "log_level": settings.log_level,
        "host": settings.host,
        "port": settings.port,
        "timeouts": {
            "coldstart_ms": settings.model_timeout_coldstart,
            "personalized_ms": settings.model_timeout_personalized,
            "price_ms": settings.model_timeout_price,
            "recipe_ms": settings.model_timeout_recipe,
            "api_ms": settings.api_timeout,
        },
        "cache_ttl": {
            "recommendation": settings.cache_ttl_recommendation,
            "price_anomaly": settings.cache_ttl_price_anomaly,
            "user_embedding": settings.cache_ttl_user_embedding,
        },
        "batch": {
            "chunk_size": settings.batch_chunk_size,
            "similarity_top_k": settings.batch_similarity_top_k,
        },
        "embedding": {
            "model": settings.bert_model_name,
            "dimension": settings.embedding_dimension,
        },
    }


@router.get(
    "/batch/status",
    summary="배치 작업 상태 조회",
    description="배치 작업 실행 상태 조회",
)
async def get_batch_status():
    """배치 작업 상태 조회"""
    try:
        from batch import scheduler

        return {
            "scheduler_running": scheduler._running,
            "jobs": scheduler.get_status(),
        }
    except Exception as e:
        return {
            "scheduler_running": False,
            "error": str(e),
        }
