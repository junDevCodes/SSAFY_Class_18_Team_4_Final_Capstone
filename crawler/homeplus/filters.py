"""
홈플러스 필터/패싯 수집기

카테고리별 필터 메타를 수집하여 별도 JSON으로 저장한다.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from crawler.config import AppConfig
from crawler.homeplus.client import HomeplusClient
from crawler.homeplus.parsers import CategoryNode


class FilterCollector:
    """필터/패싯 메타 수집기"""

    def __init__(self, config: Optional[AppConfig] = None, client: Optional[HomeplusClient] = None):
        self.config = config or AppConfig.load()
        self.client = client or HomeplusClient(self.config)
        project_root = Path(__file__).parent.parent.parent
        docker_data_path = Path("/app/data")
        data_root = docker_data_path if docker_data_path.exists() else project_root / "data"
        self.processed_dir = data_root / "json" / "processed"
        self.processed_dir.mkdir(parents=True, exist_ok=True)

    def collect_for_category(self, cate: CategoryNode) -> Dict[str, Any]:
        """단일 카테고리에 대한 필터 메타 수집"""
        if cate.scateCd:
            depth = 3
            cate_id = cate.scateCd
            add_sub = "Y"
            search_type = "NONE"
        else:
            depth = 2
            cate_id = cate.mcateCd or cate.lcateCd
            add_sub = None
            search_type = None

        resp = self.client.fetch_filter_meta(
            category_depth=depth,
            category_id=cate_id,
            page=1,
            per_page=20,
            add_sub_category=add_sub,
            search_type=search_type,
        )

        filters = {
            "attributeList": resp.get("attributeList") or resp.get("attributes"),
            "brandList": resp.get("brandList") or resp.get("brands"),
            "partnerList": resp.get("partnerList") or resp.get("partners"),
            "priceRangeList": resp.get("priceRangeList") or resp.get("priceRanges"),
            "benefitList": resp.get("benefitList") or resp.get("benefits"),
        }

        category_path = " > ".join(filter(None, [cate.lcateNm, cate.mcateNm, cate.scateNm]))

        return {
            "source": self.config.crawl.target,
            "category_path": category_path,
            "categoryId": cate_id,
            "categoryDepth": depth,
            "storeId": self.config.store.store_id,
            "storeType": self.config.store.store_type,
            "storeKind": self.config.store.store_kind,
            "itemShipMethod": self.config.store.item_ship_method,
            "filters": filters,
        }

    def collect_all(self, categories: List[CategoryNode]) -> List[Dict[str, Any]]:
        """여러 카테고리에 대한 필터 메타 수집"""
        results: List[Dict[str, Any]] = []
        for cate in categories:
            results.append(self.collect_for_category(cate))
        return results

    def save(self, data: List[Dict[str, Any]], out_dir: Optional[Path] = None) -> Path:
        """필터 메타를 JSON 파일로 저장"""
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"homeplus_filters_{ts}.json"
        target_dir = out_dir if out_dir else self.processed_dir
        target_dir.mkdir(parents=True, exist_ok=True)
        path = target_dir / filename
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return path
