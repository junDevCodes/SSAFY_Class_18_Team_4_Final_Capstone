import json

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
