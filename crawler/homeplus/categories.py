"""
홈플러스 카테고리 엔드포인트 정의

카테고리 트리와 상품 목록/필터 조회에 사용되는 URL과 파라미터 기본값을 관리한다.
"""

from crawler.homeplus import BASE_URL

# 카테고리/상품 관련 엔드포인트
CATEGORY_MAP_ENDPOINT = "/category/mobile/getMap.json"
ITEM_LIST_ENDPOINT = "/category/item.json"
FILTER_ENDPOINT = "/category/filter.json"

# 기본 스토어 파라미터 (환경변수로 오버라이드)
DEFAULT_STORE_ID = 37
DEFAULT_STORE_TYPE = "HYPER"
DEFAULT_STORE_KIND = "NOR"
DEFAULT_ITEM_SHIP_METHOD = "TD_DRCT"


def build_url(path: str) -> str:
    """BASE_URL과 상대 경로를 합쳐 완전한 URL을 반환한다."""
    return f"{BASE_URL}{path}"
