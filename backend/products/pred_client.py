"""
Pred API 클라이언트

ML 추천 서버(pred)와의 통신을 담당합니다.
"""

import json
from typing import List

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
