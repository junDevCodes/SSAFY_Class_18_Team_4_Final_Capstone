"""
추천 모델 오케스트레이터

맥락에 따라 적절한 모델 조합을 선택하고 결과를 병합합니다.
"""

import asyncio
import hashlib
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from core.cache import CacheKeys, CacheManager
from core.config import settings
from core.database import Database
from core.exceptions import ModelTimeoutError
from core.logging import get_logger

logger = get_logger(__name__)


# 페이지/사용자 타입별 모델 가중치 설정
# 모델별 역할:
# - self: 개인화 추천 (SVD 임베딩 기반, warm/lukewarm 사용자)
# - instacart: Cold Start 추천 (시간대별 인기 상품, cold 사용자)
# - price: 가격 이상치/할인 추천 (Modified Z-Score 기반)
# - recipe: 레시피 갭필링 (장바구니 기반 레시피 추천)
MODEL_WEIGHTS = {
    "home": {
        # warm: 개인화 60% + 할인 40%
        "warm": {"self": 0.6, "price": 0.4},
        # lukewarm: 개인화 40% + 시간대 30% + 할인 30%
        "lukewarm": {"self": 0.4, "instacart": 0.3, "price": 0.3},
        # cold: 시간대 50% + 할인 50% (개인화 불가)
        "cold": {"instacart": 0.5, "price": 0.5},
    },
    "category": {
        "warm": {"self": 0.6, "price": 0.4},
        "lukewarm": {"self": 0.4, "instacart": 0.3, "price": 0.3},
        "cold": {"instacart": 0.5, "price": 0.5},
    },
    "product_detail": {
        # 상품 상세: 개인화 위주 (유사 상품)
        "warm": {"self": 0.8, "price": 0.2},
        "lukewarm": {"self": 0.5, "instacart": 0.3, "price": 0.2},
        "cold": {"instacart": 0.6, "price": 0.4},
    },
    "cart": {
        # 장바구니: 개인화 + 레시피 갭필링
        "warm": {"self": 0.5, "recipe": 0.3, "price": 0.2},
        "lukewarm": {"self": 0.4, "recipe": 0.3, "instacart": 0.2, "price": 0.1},
        "cold": {"recipe": 0.4, "instacart": 0.4, "price": 0.2},
    },
    "search": {
        # 검색: 할인 위주 (검색 결과 보완)
        "warm": {"self": 0.4, "price": 0.6},
        "lukewarm": {"self": 0.3, "instacart": 0.2, "price": 0.5},
        "cold": {"instacart": 0.3, "price": 0.7},
    },
    "timedeal": {
        # 타임딜: 가격 이상치만 사용
        "warm": {"price": 1.0},
        "lukewarm": {"price": 1.0},
        "cold": {"price": 1.0},
    },
}


def get_time_slot(hour: int) -> str:
    """시간대 분류

    Args:
        hour: 시간 (0-23)

    Returns:
        시간대 ('morning', 'lunch', 'dinner', 'night')
    """
    if 6 <= hour <= 10:
        return "morning"
    elif 11 <= hour <= 14:
        return "lunch"
    elif 17 <= hour <= 21:
        return "dinner"
    else:
        return "night"


def get_day_type(weekday: int) -> str:
    """요일 타입 분류

    Args:
        weekday: 요일 (0=월요일, 6=일요일)

    Returns:
        요일 타입 ('weekday', 'weekend')
    """
    return "weekend" if weekday >= 5 else "weekday"


def get_current_context() -> Dict[str, Any]:
    """현재 시간 컨텍스트 반환"""
    now = datetime.now()
    return {
        "time_slot": get_time_slot(now.hour),
        "day_type": get_day_type(now.weekday()),
        "hour": now.hour,
        "weekday": now.weekday(),
    }


def generate_context_hash(
    user_id: Optional[int],
    page_type: str,
    category_id: Optional[int],
    product_id: Optional[int],
    cart_items: List[int],
    time_slot: str,
    day_type: str,
) -> str:
    """컨텍스트 해시 생성

    캐시 키 생성에 사용됩니다.
    """
    context_data = {
        "user_id": user_id,
        "page_type": page_type,
        "category_id": category_id,
        "product_id": product_id,
        "cart_items": sorted(cart_items),
        "time_slot": time_slot,
        "day_type": day_type,
    }
    context_str = json.dumps(context_data, sort_keys=True)
    return hashlib.sha256(context_str.encode()).hexdigest()[:16]


async def classify_user(user_id: Optional[int], db: Database) -> str:
    """사용자 타입 분류

    Args:
        user_id: 사용자 ID
        db: 데이터베이스 인스턴스

    Returns:
        사용자 타입 ('cold', 'lukewarm', 'warm')
    """
    if user_id is None:
        return "cold"

    try:
        stats = await db.fetch_one(
            """
            SELECT
                COALESCE(SUM(order_event_count), 0) as order_count,
                COALESCE(SUM(cart_event_count), 0) as cart_count,
                COALESCE(SUM(view_count), 0) as view_count
            FROM user_product_stats
            WHERE user_id = $1
            """,
            user_id,
        )

        if not stats:
            return "cold"

        order_count = stats["order_count"] or 0
        cart_count = stats["cart_count"] or 0
        view_count = stats["view_count"] or 0

        # 구매 이력 1회 이상 → warm
        if order_count >= 1:
            return "warm"

        # 장바구니 3회 이상 → warm
        if cart_count >= 3:
            return "warm"

        # 조회 10회 이상 + 장바구니 1회 이상 → lukewarm
        if view_count >= 10 and cart_count >= 1:
            return "lukewarm"

        return "cold"

    except Exception as e:
        logger.warning("사용자 분류 실패, cold로 처리", user_id=user_id, error=str(e))
        return "cold"


def get_model_config(page_type: str, user_type: str) -> Dict[str, float]:
    """페이지/사용자 타입에 따른 모델 가중치 반환

    Args:
        page_type: 페이지 타입
        user_type: 사용자 타입

    Returns:
        모델별 가중치 딕셔너리
    """
    page_config = MODEL_WEIGHTS.get(page_type, MODEL_WEIGHTS["home"])
    return page_config.get(user_type, page_config["cold"])


class RecommendationOrchestrator:
    """추천 모델 오케스트레이터

    여러 추천 모델을 조율하여 통합 추천 결과를 생성합니다.
    """

    def __init__(
        self,
        db: Database,
        cache: CacheManager,
        instacart_model=None,
        self_model=None,
        price_model=None,
        recipe_model=None,
    ):
        """
        Args:
            db: 데이터베이스 인스턴스
            cache: 캐시 매니저 인스턴스
            instacart_model: InstacartColdStart 모델 인스턴스
            self_model: SelfPersonalized 모델 인스턴스
            price_model: PriceAnomaly 모델 인스턴스
            recipe_model: RecipeGapFilling 모델 인스턴스
        """
        self.db = db
        self.cache = cache
        self.models = {
            "instacart": instacart_model,
            "self": self_model,
            "price": price_model,
            "recipe": recipe_model,
        }
        self.timeouts = settings.model_timeouts

    async def recommend(
        self,
        user_id: Optional[int],
        page_type: str,
        category_id: Optional[int] = None,
        product_id: Optional[int] = None,
        cart_items: Optional[List[int]] = None,
        limit: int = 20,
        context: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """통합 추천 생성

        Args:
            user_id: 사용자 ID
            page_type: 페이지 타입 ('home', 'category', 'product_detail', 'cart')
            category_id: 카테고리 ID (선택적)
            product_id: 상품 ID (선택적)
            cart_items: 장바구니 상품 ID 목록 (선택적)
            limit: 추천 개수 제한
            context: 시간 컨텍스트 (선택적)

        Returns:
            추천 결과 딕셔너리
        """
        import time

        start_time = time.time()
        cart_items = cart_items or []
        context = context or get_current_context()

        # 사용자 분류
        user_type = await classify_user(user_id, self.db)

        # 컨텍스트 해시 생성
        context_hash = generate_context_hash(
            user_id,
            page_type,
            category_id,
            product_id,
            cart_items,
            context.get("time_slot", ""),
            context.get("day_type", ""),
        )

        # 캐시 확인
        cache_key = CacheKeys.recommendation(user_id, page_type, context_hash)
        cached_result = await self.cache.get_json(cache_key)
        if cached_result:
            logger.debug("캐시 히트", cache_key=cache_key)
            cached_result["metadata"]["from_cache"] = True
            return cached_result

        # 모델 가중치 결정
        model_config = get_model_config(page_type, user_type)

        # context에 page_type과 user_type 추가
        context["page_type"] = page_type
        context["user_type"] = user_type

        # 모델 병렬 실행
        model_results = await self._execute_models_parallel(
            model_config=model_config,
            user_id=user_id,
            category_id=category_id,
            product_id=product_id,
            cart_items=cart_items,
            context=context,
        )

        # 결과 병합 및 순위화
        recommendations = self._merge_results(
            model_results, model_config, limit=limit
        )

        # 상품 정보 조회
        recommendations = await self._enrich_with_product_info(recommendations)

        processing_time_ms = int((time.time() - start_time) * 1000)

        result = {
            "recommendations": recommendations,
            "user_type": user_type,
            "metadata": {
                "user_type": user_type,
                "model_used": list(model_config.keys()),
                "processing_time_ms": processing_time_ms,
                "from_cache": False,
            },
        }

        # 캐시 저장 (비동기)
        asyncio.create_task(
            self.cache.set_json(
                cache_key, result, ttl=settings.cache_ttl_recommendation
            )
        )

        return result

    async def _execute_models_parallel(
        self,
        model_config: Dict[str, float],
        user_id: Optional[int],
        category_id: Optional[int],
        product_id: Optional[int],
        cart_items: List[int],
        context: Dict[str, str],
    ) -> Dict[str, List[Dict[str, Any]]]:
        """모델 병렬 실행

        Args:
            model_config: 모델별 가중치
            user_id: 사용자 ID
            category_id: 카테고리 ID
            product_id: 상품 ID
            cart_items: 장바구니 상품 목록
            context: 시간 컨텍스트

        Returns:
            모델별 추천 결과
        """
        tasks = {}
        results = {}

        for model_name, weight in model_config.items():
            if weight > 0 and self.models.get(model_name) is not None:
                tasks[model_name] = self._execute_with_timeout(
                    model_name=model_name,
                    user_id=user_id,
                    category_id=category_id,
                    product_id=product_id,
                    cart_items=cart_items,
                    context=context,
                )

        if not tasks:
            logger.warning("실행할 모델이 없습니다", available_models=[k for k, v in self.models.items() if v is not None])
            return {}

        logger.info(f"모델 실행 시작: {list(tasks.keys())}")

        # 병렬 실행
        task_results = await asyncio.gather(
            *tasks.values(), return_exceptions=True
        )

        for model_name, result in zip(tasks.keys(), task_results):
            if isinstance(result, Exception):
                logger.warning(
                    "모델 실행 실패",
                    model=model_name,
                    error=str(result),
                )
                results[model_name] = []
            else:
                results[model_name] = result
                logger.info(f"모델 {model_name} 결과: {len(result) if isinstance(result, list) else 'N/A'}개")

        return results

    async def _execute_with_timeout(
        self,
        model_name: str,
        user_id: Optional[int],
        category_id: Optional[int],
        product_id: Optional[int],
        cart_items: List[int],
        context: Dict[str, str],
    ) -> List[Dict[str, Any]]:
        """타임아웃과 함께 모델 실행

        Args:
            model_name: 모델 이름
            user_id: 사용자 ID
            category_id: 카테고리 ID
            product_id: 상품 ID
            cart_items: 장바구니 상품 목록
            context: 시간 컨텍스트

        Returns:
            추천 결과 목록

        Raises:
            ModelTimeoutError: 타임아웃 발생 시
        """
        from ml.base import RecommendationContext as MLContext

        model = self.models.get(model_name)
        if model is None:
            return []

        timeout = self.timeouts.get(model_name, 0.2)

        try:
            # 공통 컨텍스트 생성
            ml_context = MLContext(
                user_id=user_id or 0,
                page_type=context.get("page_type", "home"),
                category_id=category_id,
                product_id=product_id,
                cart_product_ids=cart_items or [],
                time_context=context.get("time_slot", "default"),
                user_type=context.get("user_type", "cold"),
            )

            # 모델 호출 (공통 인터페이스 사용)
            result = await asyncio.wait_for(
                model.recommend(ml_context, limit=20),
                timeout=timeout,
            )

            # RecommendationResult에서 products 추출
            if hasattr(result, 'products'):
                return result.products
            elif isinstance(result, list):
                return result
            else:
                return []

        except asyncio.TimeoutError:
            logger.warning(
                "모델 타임아웃",
                model=model_name,
                timeout_ms=int(timeout * 1000),
            )
            return []
        except Exception as e:
            logger.warning(
                "모델 실행 실패",
                model=model_name,
                error=str(e),
            )
            return []

    def _merge_results(
        self,
        model_results: Dict[str, List[Dict[str, Any]]],
        model_config: Dict[str, float],
        limit: int,
    ) -> List[Dict[str, Any]]:
        """모델 결과 병합 및 순위화

        Args:
            model_results: 모델별 추천 결과
            model_config: 모델별 가중치
            limit: 결과 개수 제한

        Returns:
            병합된 추천 목록
        """
        # 상품별 점수 집계
        product_scores: Dict[int, Dict[str, Any]] = {}

        for model_name, results in model_results.items():
            weight = model_config.get(model_name, 0)
            if not results:
                continue

            for idx, item in enumerate(results):
                product_id = item.get("product_id")
                if product_id is None:
                    continue

                # 순위 기반 점수 (1위: 1.0, 20위: 0.05)
                rank_score = 1.0 / (idx + 1)
                weighted_score = rank_score * weight

                # 이상치 점수나 유사도 점수가 있으면 추가 반영
                if "anomaly_score" in item:
                    weighted_score *= (1 + item["anomaly_score"])
                if "match_score" in item:
                    weighted_score *= (1 + item["match_score"])

                if product_id not in product_scores:
                    product_scores[product_id] = {
                        "product_id": product_id,
                        "score": 0,
                        "sources": [],
                        "reasons": [],
                    }

                product_scores[product_id]["score"] += weighted_score
                product_scores[product_id]["sources"].append(model_name)

                # 추천 이유 수집
                if "reason" in item:
                    product_scores[product_id]["reasons"].append(item["reason"])

                # 추가 정보 병합
                for key in ["price_info", "recipe_info"]:
                    if key in item:
                        product_scores[product_id][key] = item[key]

        # 점수순 정렬
        sorted_results = sorted(
            product_scores.values(),
            key=lambda x: x["score"],
            reverse=True,
        )[:limit]

        # 결과 정규화
        for item in sorted_results:
            item["sources"] = list(set(item["sources"]))
            item["source"] = item["sources"][0] if item["sources"] else "unknown"
            if item["reasons"]:
                item["reason"] = item["reasons"][0]
            del item["sources"]
            del item["reasons"]

        return sorted_results

    async def determine_user_type(self, user_id: Optional[int]) -> str:
        """사용자 타입 결정

        Args:
            user_id: 사용자 ID

        Returns:
            사용자 타입 ('cold', 'lukewarm', 'warm')
        """
        return await classify_user(user_id, self.db)

    async def _enrich_with_product_info(
        self,
        recommendations: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """추천 결과에 상품 정보 추가

        Args:
            recommendations: 추천 결과 목록

        Returns:
            상품 정보가 추가된 추천 목록
        """
        if not recommendations:
            return []

        # product_id 목록 추출
        product_ids = [r.get("product_id") for r in recommendations if r.get("product_id")]
        if not product_ids:
            return recommendations

        # 상품 정보 조회
        query = """
            SELECT p.id, p.name, p.price, p.original_price, p.category_id, p.seller_id,
                   COALESCE(ps.order_event_count, 0) AS order_event_count,
                   COALESCE(ps.view_count, 0) AS view_count,
                   COALESCE(ps.average_rating, 0) AS average_rating
            FROM products p
            LEFT JOIN product_stats ps ON p.id = ps.product_id
            WHERE p.id = ANY($1)
        """

        try:
            records = await self.db.fetch_all(query, product_ids)
            product_info = {r["id"]: dict(r) for r in records}

            # 추천 결과에 상품 정보 병합
            enriched = []
            for rec in recommendations:
                pid = rec.get("product_id")
                if pid and pid in product_info:
                    info = product_info[pid]
                    enriched.append({
                        "product_id": pid,
                        "name": info.get("name", ""),
                        "price": info.get("price", 0),
                        "original_price": info.get("original_price"),
                        "category_id": info.get("category_id"),
                        "seller_id": info.get("seller_id"),
                        "order_event_count": info.get("order_event_count", 0),
                        "view_count": info.get("view_count", 0),
                        "average_rating": info.get("average_rating", 0),
                        "recommendation_score": rec.get("score"),
                        "recommendation_source": rec.get("source"),
                    })
                else:
                    enriched.append(rec)

            return enriched

        except Exception as e:
            logger.warning(f"상품 정보 조회 실패: {e}")
            return recommendations
