"""
Pred API 클라이언트

ML 추천 서비스(pred)와 통신하는 클라이언트
"""

import json
import logging
from typing import Optional

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def _build_base_url() -> str:
    """Pred API 기본 URL을 슬래시 없이 반환"""
    return settings.ML_API_URL.rstrip("/")


def fetch_pred_health() -> dict:
    """Pred API 헬스 엔드포인트 호출"""
    base_url = _build_base_url()
    response = requests.get(f"{base_url}/health", timeout=5)
    response.raise_for_status()
    return response.json()


def request_recommendations(
    user_id: Optional[int] = None,
    page_type: str = "home",
    category_id: Optional[int] = None,
    product_id: Optional[int] = None,
    cart_product_ids: Optional[list] = None,
    limit: int = 10,
) -> dict:
    """Pred API 추천 엔드포인트 호출

    Args:
        user_id: 사용자 ID (없으면 Cold Start)
        page_type: 페이지 타입 (home, category, product_detail, cart, search)
        category_id: 카테고리 ID (카테고리 페이지일 때)
        product_id: 상품 ID (상품 상세 페이지일 때)
        cart_product_ids: 장바구니 상품 ID 목록
        limit: 추천 개수

    Returns:
        추천 응답 dict
    """
    base_url = _build_base_url()

    payload = {
        "user_id": user_id,
        "page_type": page_type,
        "limit": limit,
    }

    if category_id:
        payload["category_id"] = category_id
    if product_id:
        payload["product_id"] = product_id
    if cart_product_ids:
        payload["cart_product_ids"] = cart_product_ids

    try:
        response = requests.post(
            f"{base_url}/api/v1/recommendations/",
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.warning(f"Pred API 호출 실패: {e}")
        return {"success": False, "recommendations": [], "error": str(e)}


def get_home_recommendations(user_id: Optional[int] = None, limit: int = 10) -> dict:
    """홈 페이지 추천"""
    base_url = _build_base_url()

    params = {"limit": limit}
    if user_id:
        params["user_id"] = user_id

    try:
        response = requests.get(
            f"{base_url}/api/v1/recommendations/home",
            params=params,
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.warning(f"홈 추천 API 호출 실패: {e}")
        return {"success": False, "recommendations": [], "error": str(e)}


def get_product_recommendations(
    product_id: int,
    user_id: Optional[int] = None,
    limit: int = 10,
) -> dict:
    """상품 상세 페이지 추천 (연관 상품)"""
    base_url = _build_base_url()

    params = {"limit": limit}
    if user_id:
        params["user_id"] = user_id

    try:
        response = requests.get(
            f"{base_url}/api/v1/recommendations/product/{product_id}",
            params=params,
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.warning(f"상품 추천 API 호출 실패: {e}")
        return {"success": False, "recommendations": [], "error": str(e)}


def get_deal_recommendations(
    user_id: Optional[int] = None,
    category_id: Optional[int] = None,
    limit: int = 10,
) -> dict:
    """할인 상품 추천 (TimeDeal용)"""
    base_url = _build_base_url()

    params = {"limit": limit}
    if user_id:
        params["user_id"] = user_id
    if category_id:
        params["category_id"] = category_id

    try:
        response = requests.get(
            f"{base_url}/api/v1/recommendations/deals",
            params=params,
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.warning(f"할인 추천 API 호출 실패: {e}")
        return {"success": False, "recommendations": [], "error": str(e)}


# ============================================================
# 장바구니 통합 추천 API (레시피 > 개인화 > Instacart)
# ============================================================


def get_cart_unified_recommendations(
    user_id: Optional[int] = None,
    cart_product_ids: Optional[list] = None,
    limit: int = 9,
) -> dict:
    """장바구니 통합 추천

    추천 우선순위:
    1. 레시피 기반 추천 (요리명 포함) - 장바구니 재료로 만들 수 있는 레시피의 부족 재료
    2. 개인화 추천 (로그인 사용자) - SVD 임베딩 기반
    3. Instacart 추천 (비로그인/신규) - 시간대별 인기 상품

    Args:
        user_id: 사용자 ID (없으면 Cold Start)
        cart_product_ids: 장바구니 상품 ID 목록
        limit: 추천 개수 (기본 9개)

    Returns:
        {
            "success": bool,
            "recommendations": [
                {
                    "product_id": int,
                    "name": str,
                    "price": int,
                    "image_url": str | None,
                    "source": "recipe" | "personalized" | "instacart",
                    "recipe_name": str | None,  # 레시피 추천 시 요리명
                    "ingredient_name": str | None,  # 레시피 추천 시 재료명
                }
            ],
            "total_count": int,
            "recipe_count": int,
            "personalized_count": int,
            "instacart_count": int,
            "user_type": "cold" | "lukewarm" | "warm",
            "processing_time_ms": float,
            "message": str | None,
        }
    """
    base_url = _build_base_url()

    payload = {
        "user_id": user_id,
        "cart_product_ids": cart_product_ids or [],
        "limit": limit,
    }

    try:
        response = requests.post(
            f"{base_url}/api/v1/recommendations/cart/unified",
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=15,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.warning(f"장바구니 통합 추천 API 호출 실패: {e}")
        return {
            "success": False,
            "recommendations": [],
            "total_count": 0,
            "recipe_count": 0,
            "personalized_count": 0,
            "instacart_count": 0,
            "user_type": "cold",
            "processing_time_ms": 0,
            "message": f"추천 서비스 연결 실패: {str(e)}",
        }


# ============================================================
# 레시피 GapFilling 추천 API
# ============================================================


def get_cart_recipe_recommendations(
    cart_product_ids: list,
    limit: int = 3,
) -> dict:
    """장바구니 기반 레시피 추천

    장바구니에 담긴 상품을 분석하여 만들 수 있는 레시피를 추천하고,
    부족한 재료에 해당하는 상품을 추천합니다.

    Args:
        cart_product_ids: 장바구니 상품 ID 목록
        limit: 추천 레시피 개수 (기본 3개)

    Returns:
        {
            "success": bool,
            "recipes": [
                {
                    "recipe_id": int,
                    "name": str,  # 요리명 (CKG_NM)
                    "title": str | None,  # 레시피 제목
                    "match_ratio": float,  # 재료 매칭률 (0-1)
                    "gap_count": int,  # 부족한 재료 수
                    "gap_ingredients": [str],  # 부족한 재료 목록
                    "matched_ingredients": [str],  # 매칭된 재료 목록
                    "recommended_products": [
                        {
                            "product_id": int,
                            "name": str,
                            "price": int,
                            "original_price": int | None,
                            "main_image": str | None,
                            "ingredient": str,  # 해당 재료명
                        }
                    ],
                    "view_count": int,
                }
            ],
            "cart_ingredients": [str],  # 인식된 재료 목록
            "total_gap_count": int,
            "processing_time_ms": float,
            "message": str | None,
        }
    """
    base_url = _build_base_url()

    if not cart_product_ids:
        return {
            "success": False,
            "recipes": [],
            "cart_ingredients": [],
            "total_gap_count": 0,
            "processing_time_ms": 0,
            "message": "장바구니가 비어있습니다",
        }

    payload = {
        "cart_product_ids": cart_product_ids,
        "limit": limit,
    }

    try:
        response = requests.post(
            f"{base_url}/api/v1/recipe/cart-recommendations",
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=15,  # 레시피 분석은 시간이 더 걸릴 수 있음
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.warning(f"장바구니 레시피 추천 API 호출 실패: {e}")
        return {
            "success": False,
            "recipes": [],
            "cart_ingredients": [],
            "total_gap_count": 0,
            "processing_time_ms": 0,
            "message": f"레시피 추천 서비스 연결 실패: {str(e)}",
        }


def get_recipe_detail(recipe_id: int) -> dict:
    """레시피 상세 정보 조회

    Args:
        recipe_id: 레시피 ID

    Returns:
        {
            "recipe": {...},
            "ingredients": [...]
        }
    """
    base_url = _build_base_url()

    try:
        response = requests.get(
            f"{base_url}/api/v1/recipe/{recipe_id}",
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.warning(f"레시피 상세 조회 API 호출 실패: {e}")
        return {"recipe": None, "ingredients": [], "error": str(e)}


def search_recipes(
    query: str,
    category: Optional[str] = None,
    limit: int = 20,
) -> dict:
    """레시피 검색

    Args:
        query: 검색어
        category: 카테고리 필터
        limit: 결과 개수

    Returns:
        {
            "recipes": [...],
            "total_count": int,
            "query": str,
            "category": str | None
        }
    """
    base_url = _build_base_url()

    params = {
        "query": query,
        "limit": limit,
    }
    if category:
        params["category"] = category

    try:
        response = requests.get(
            f"{base_url}/api/v1/recipe/search",
            params=params,
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.warning(f"레시피 검색 API 호출 실패: {e}")
        return {"recipes": [], "total_count": 0, "query": query, "error": str(e)}
