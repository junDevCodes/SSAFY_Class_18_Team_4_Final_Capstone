"""
가격 이상치 API 라우터

가격 이상치 탐지 및 할인 상품 조회 엔드포인트
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.dependencies import get_db, get_cache
from core.database import Database
from core.cache import CacheManager, CacheKeys
from core.logging import get_logger
from data.repositories import PriceHistoryRepository, PriceAnomalyCacheRepository

logger = get_logger(__name__)

router = APIRouter(prefix="/price", tags=["price"])


@router.get(
    "/anomalies",
    summary="가격 이상치 상품 조회",
    description="Z-Score, IQR, MA 기반 가격 급락 상품 탐지",
)
async def get_price_anomalies(
    category_id: Optional[int] = Query(None, description="카테고리 ID (선택적)"),
    limit: int = Query(20, ge=1, le=100, description="결과 개수"),
    db: Database = Depends(get_db),
    cache: CacheManager = Depends(get_cache),
):
    """가격 이상치 상품 조회

    캐시 우선 전략:
    1. Redis 캐시 조회
    2. 캐시 미스 시 DB 조회 후 캐시 저장
    """
    start_time = datetime.now()

    # 캐시 확인
    cache_key = CacheKeys.price_anomaly(category_id)
    cached = await cache.get_json(cache_key)

    if cached:
        return {
            **cached,
            "cached": True,
            "processing_time_ms": 0,
        }

    # DB 조회
    anomaly_repo = PriceAnomalyCacheRepository(db)
    anomalies = await anomaly_repo.get_best_deals(
        category_ids=[category_id] if category_id else None,
        limit=limit,
    )

    processing_time = (datetime.now() - start_time).total_seconds() * 1000

    result = {
        "anomalies": anomalies,
        "total_count": len(anomalies),
        "category_id": category_id,
        "cached": False,
        "processing_time_ms": processing_time,
    }

    # 캐시 저장 (30분)
    await cache.set_json(cache_key, result, ttl=1800)

    return result


@router.get(
    "/history/{product_id}",
    summary="상품 가격 이력 조회",
    description="특정 상품의 가격 변동 이력 조회",
)
async def get_price_history(
    product_id: int,
    days: int = Query(30, ge=1, le=365, description="조회 기간 (일)"),
    db: Database = Depends(get_db),
):
    """상품 가격 이력 조회"""
    price_repo = PriceHistoryRepository(db)

    history = await price_repo.get_price_history(
        product_id=product_id,
        days=days,
    )

    if not history:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"상품 {product_id}의 가격 이력을 찾을 수 없습니다",
        )

    # 통계 계산
    prices = [h["price"] for h in history]
    stats = {
        "min_price": min(prices),
        "max_price": max(prices),
        "avg_price": sum(prices) / len(prices),
        "current_price": prices[-1] if prices else 0,
        "price_change": prices[-1] - prices[0] if len(prices) >= 2 else 0,
    }

    return {
        "product_id": product_id,
        "history": history,
        "stats": stats,
        "days": days,
    }


@router.get(
    "/analysis/{product_id}",
    summary="상품 가격 분석",
    description="특정 상품의 가격 이상치 분석",
)
async def analyze_product_price(
    product_id: int,
    db: Database = Depends(get_db),
):
    """상품 가격 분석

    Z-Score, IQR, MA 기반 분석 결과 반환
    """
    price_repo = PriceHistoryRepository(db)

    # 30일 가격 이력 조회
    history = await price_repo.get_price_history(
        product_id=product_id,
        days=30,
    )

    if not history or len(history) < 3:
        return {
            "product_id": product_id,
            "is_anomaly": False,
            "message": "분석에 필요한 데이터가 부족합니다",
        }

    prices = [h["price"] for h in history]
    current_price = prices[-1]

    # 통계 계산
    import numpy as np

    prices_array = np.array(prices)
    mean_price = np.mean(prices_array)
    std_price = np.std(prices_array)
    q1 = np.percentile(prices_array, 25)
    q3 = np.percentile(prices_array, 75)
    iqr = q3 - q1

    # Z-Score
    z_score = (current_price - mean_price) / std_price if std_price > 0 else 0

    # IQR 하한
    iqr_lower = q1 - 1.5 * iqr

    # 7일 이동평균
    ma_7 = np.mean(prices_array[-7:]) if len(prices_array) >= 7 else mean_price

    # 이상치 판정
    detection_methods = []
    scores = []

    if z_score < -2.0:
        detection_methods.append("zscore")
        scores.append(min(abs(z_score) / 3, 1.0))

    if current_price < iqr_lower:
        detection_methods.append("iqr")
        if iqr > 0:
            scores.append(min((iqr_lower - current_price) / iqr, 1.0))

    if current_price < ma_7 * 0.85:  # MA 대비 15% 이상 하락
        detection_methods.append("ma")
        scores.append(min((ma_7 - current_price) / ma_7, 1.0))

    is_anomaly = len(detection_methods) > 0
    anomaly_score = sum(scores) / len(scores) * (1 + 0.1 * len(detection_methods)) if scores else 0

    return {
        "product_id": product_id,
        "is_anomaly": is_anomaly,
        "anomaly_score": min(anomaly_score, 1.0),
        "detection_methods": detection_methods,
        "analysis": {
            "current_price": current_price,
            "mean_price": float(mean_price),
            "std_price": float(std_price),
            "z_score": float(z_score),
            "iqr_lower": float(iqr_lower),
            "iqr_upper": float(q3 + 1.5 * iqr),
            "ma_7": float(ma_7),
        },
    }


@router.get(
    "/deals",
    summary="오늘의 특가 상품",
    description="가격 이상치 기반 할인 상품 목록",
)
async def get_daily_deals(
    category_id: Optional[int] = Query(None, description="카테고리 ID"),
    min_discount_rate: float = Query(10.0, ge=0, le=100, description="최소 할인율 (%)"),
    limit: int = Query(20, ge=1, le=100, description="결과 개수"),
    db: Database = Depends(get_db),
):
    """오늘의 특가 상품 조회"""
    price_repo = PriceHistoryRepository(db)

    deals = await price_repo.get_price_dropped_products(
        min_drop_rate=min_discount_rate,
        category_id=category_id,
        limit=limit,
    )

    return {
        "deals": deals,
        "total_count": len(deals),
        "category_id": category_id,
        "min_discount_rate": min_discount_rate,
    }
