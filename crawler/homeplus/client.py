"""
홈플러스 API 클라이언트

카테고리 맵 및 상품 리스트/필터 API 호출을 담당한다.
"""

from typing import Any, Dict, Optional

from crawler.config import AppConfig
from crawler.homeplus import BASE_URL
from crawler.homeplus.categories import (
    CATEGORY_MAP_ENDPOINT,
    DEFAULT_STORE_ID,
    DEFAULT_STORE_KIND,
    DEFAULT_STORE_TYPE,
    DEFAULT_ITEM_SHIP_METHOD,
    FILTER_ENDPOINT,
    ITEM_LIST_ENDPOINT,
    build_url,
)
from crawler.http_client import HttpClient


class HomeplusClient:
    """홈플러스 전용 API 클라이언트"""

    def __init__(self, config: Optional[AppConfig] = None, http_client: Optional[HttpClient] = None):
        self.config = config or AppConfig.load()
        self.http = http_client or HttpClient()
        self.base_url = BASE_URL

    def fetch_category_map(self) -> Dict[str, Any]:
        """카테고리 트리 맵을 조회한다."""
        url = build_url(CATEGORY_MAP_ENDPOINT)
        return self.http.get_json(url)

    def fetch_item_list(
        self,
        category_depth: int,
        category_id: int,
        page: int = 1,
        per_page: int = 20,
        add_sub_category: Optional[str] = None,
        search_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """상품 리스트를 조회한다."""
        params: Dict[str, Any] = {
            "categoryDepth": category_depth,
            "categoryId": category_id,
            "page": page,
            "perPage": per_page,
            "sort": "RANK",
            "storeId": self.config.store.store_id or DEFAULT_STORE_ID,
            "storeType": self.config.store.store_type or DEFAULT_STORE_TYPE,
            "storeKind": self.config.store.store_kind or DEFAULT_STORE_KIND,
            "itemShipMethod": self.config.store.item_ship_method or DEFAULT_ITEM_SHIP_METHOD,
        }
        if add_sub_category:
            params["addSubCategoryYn"] = add_sub_category
        if search_type:
            params["searchType"] = search_type

        url = build_url(ITEM_LIST_ENDPOINT)
        return self.http.get_json(url, params=params)

    def fetch_filter_meta(
        self,
        category_depth: int,
        category_id: int,
        page: int = 1,
        per_page: int = 20,
        add_sub_category: Optional[str] = None,
        search_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """필터/패싯 메타 정보를 조회한다."""
        params: Dict[str, Any] = {
            "categoryDepth": category_depth,
            "categoryId": category_id,
            "page": page,
            "perPage": per_page,
            "sort": "RANK",
            "storeId": self.config.store.store_id or DEFAULT_STORE_ID,
            "storeType": self.config.store.store_type or DEFAULT_STORE_TYPE,
            "storeKind": self.config.store.store_kind or DEFAULT_STORE_KIND,
            "itemShipMethod": self.config.store.item_ship_method or DEFAULT_ITEM_SHIP_METHOD,
        }
        if add_sub_category:
            params["addSubCategoryYn"] = add_sub_category
        if search_type:
            params["searchType"] = search_type

        url = build_url(FILTER_ENDPOINT)
        return self.http.get_json(url, params=params)

    def fetch_detail_html(self, item_no: Any) -> str:
        """상품 상세 HTML 페이지를 조회한다."""
        url = f"{BASE_URL}/item"
        params = {
            "itemNo": item_no,
            "storeType": self.config.store.store_type or DEFAULT_STORE_TYPE,
            "storeId": self.config.store.store_id or DEFAULT_STORE_ID,
        }
        resp = self.http._client.get(url, params=params)
        resp.raise_for_status()
        return resp.text
