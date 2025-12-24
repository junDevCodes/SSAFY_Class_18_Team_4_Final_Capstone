"""
Pred API 클라이언트

ML 추천 서버(pred)와의 통신을 담당합니다.
"""

import json
from typing import List, Optional

import requests
from django.conf import settings


def _build_base_url() -> str:
    """Pred API 기본 URL을 슬래시 없이 반환"""
    return settings.ML_API_URL.rstrip("/")


def fetch_pred_health() -> dict:
    """Pred API 헬스 엔드포인트 호출"""
    base_url = _build_base_url()
    response = requests.get(f"{base_url}/health", timeout=5)
    response.raise_for_status()
    return response.json()


def request_recommendations(payload: dict) -> dict:
    """Pred API 추천 엔드포인트 호출"""
    base_url = _build_base_url()
    response = requests.post(
        f"{base_url}/api/recommend",
        data=json.dumps(payload),
        headers={"Content-Type": "application/json"},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def request_cart_recommendations(product_ids: List[int], limit: int = 20) -> dict:
    """장바구니 기반 상품 추천 API 호출

    장바구니에 담긴 상품들의 재료를 분석하여
    레시피 Gap Filling 모델로 추천 상품을 반환합니다.

    Args:
        product_ids: 장바구니 상품 ID 목록
        limit: 추천 상품 개수 (기본 20, 최대 50)

    Returns:
        {
            'products': [상품 목록],
            'cart_ingredients': [인식된 재료],
            'model_version': 'v2',
            'total_count': int,
        }

    Raises:
        requests.RequestException: API 호출 실패 시
    """
    base_url = _build_base_url()
    payload = {
        "product_ids": product_ids,
        "limit": limit,
    }
    response = requests.post(
        f"{base_url}/api/cart-recommendations",
        json=payload,
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def request_time_deal_products(
    limit: int = 10,
    category_id: Optional[int] = None,
) -> dict:
    """타임세일 가성비 상품 API 호출

    self_price_analyzer_v1.pkl 모델과 PriceScout 점수 기반으로
    가성비 상품을 추천합니다.

    - 인증 불필요: 회원/비회원 모두 사용 가능
    - 가격 하락 상품 우선 추천
    - ABNORMAL 상품 제외
    - 폴백: 할인 상품(original_price > price)으로 대체

    Args:
        limit: 조회할 상품 수 (기본 10, 최대 50)
        category_id: 카테고리 ID (선택적 필터)

    Returns:
        {
            'products': [가성비 상품 목록],
            'model_version': 'v1',
            'total_count': int,
        }

    Raises:
        requests.RequestException: API 호출 실패 시
    """
    base_url = _build_base_url()
    params = {"limit": limit}
    if category_id is not None:
        params["category_id"] = category_id

    response = requests.get(
        f"{base_url}/api/time-deal-products",
        params=params,
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def request_price_history(
    product_id: int,
    days: int = 30,
) -> dict:
    """상품 가격 히스토리 API 호출

    상품의 가격 변동 이력을 조회합니다.
    폴센트(Pollcent) 스타일의 가격 추적 그래프용 데이터를 제공합니다.

    Args:
        product_id: 상품 ID
        days: 조회 기간 (기본 30일, 7~365일)

    Returns:
        {
            'product_id': int,
            'product_name': str,
            'history': [가격 이력 목록],
            'statistics': {가격 통계},
        }

    Raises:
        requests.RequestException: API 호출 실패 시
    """
    base_url = _build_base_url()
    params = {"days": days}

    response = requests.get(
        f"{base_url}/api/price-history/{product_id}",
        params=params,
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def request_personalized_recommendations(
    user_id: int,
    limit: int = 8,
    page_type: str = "home",
    category_id: Optional[int] = None,
    cart_product_ids: Optional[List[int]] = None,
) -> dict:
    """개인화 추천 API 호출

    로그인 사용자를 위한 개인화 추천을 요청합니다.

    - 장바구니 상품 제외: cart_product_ids 전달
    - 가중치 적용: order > cart + 시간 감쇠
    - 항상 limit개 반환: 부족하면 인기 상품으로 채움

    Args:
        user_id: 사용자 ID
        limit: 추천 상품 개수 (기본 8, 최대 50)
        page_type: 페이지 타입 (home, category, product_detail)
        category_id: 카테고리 ID (선택적)
        cart_product_ids: 장바구니 상품 ID 목록 (제외용)

    Returns:
        {
            'products': [상품 목록],
            'user_type': 'warm',
            'model_version': 'v2',
            'total_count': int,
            'metadata': {...},
        }

    Raises:
        requests.RequestException: API 호출 실패 시
    """
    base_url = _build_base_url()
    payload = {
        "user_id": user_id,
        "limit": limit,
        "page_type": page_type,
        "cart_product_ids": cart_product_ids or [],
    }
    if category_id is not None:
        payload["category_id"] = category_id

    response = requests.post(
        f"{base_url}/api/personalized-recommendations",
        json=payload,
        timeout=10,
    )
    response.raise_for_status()
    return response.json()
