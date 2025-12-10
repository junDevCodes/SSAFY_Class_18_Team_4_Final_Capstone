"""
홈플러스 크롤링 서비스

카테고리 맵 조회 → 쌀/잡곡 카테고리 식별 → 상품 리스트 페이징 수집 →
ProductData 매핑 → CrawlBatch 생성/저장을 담당한다.
"""

import os
from datetime import datetime
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backend.data_pipeline.schemas import CrawlBatch, ProductData
from crawler.alert import AlertClient
from crawler.config import AppConfig
from crawler.homeplus.client import HomeplusClient
from crawler.homeplus.filters import FilterCollector
from crawler.homeplus.mappers import map_item_to_product
from crawler.homeplus.parsers import GrainCategory, extract_grain_categories
from crawler.s3_uploader import S3Uploader
from crawler.raw_storage import RawStorage


class BatchWriter:
    """배치 JSON 저장기"""

    def __init__(self, base_dir: Optional[str] = None):
        project_root = Path(__file__).parent.parent.parent
        docker_data_path = Path("/app/data")
        if docker_data_path.exists():
            data_root = docker_data_path
        else:
            data_root = project_root / "data"

        self.base_dir = Path(base_dir) if base_dir else data_root / "json"
        self.processed_dir = self.base_dir / "processed"
        self.meta_dir = self.base_dir / "meta"
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        self.meta_dir.mkdir(parents=True, exist_ok=True)

    def save(self, batch: CrawlBatch) -> Path:
        """CrawlBatch를 processed 폴더에 JSON으로 저장"""
        filename = f"{batch.source}_{batch.batch_id.split('_', 1)[1]}.json"
        path = self.processed_dir / filename
        with open(path, "w", encoding="utf-8") as f:
            f.write(batch.to_json(indent=2))
        return path


class HomeplusService:
    """홈플러스 크롤링 서비스"""

    def __init__(
        self,
        config: Optional[AppConfig] = None,
        client: Optional[HomeplusClient] = None,
        raw_storage: Optional[RawStorage] = None,
    ):
        self.config = config or AppConfig.load()
        self.client = client or HomeplusClient(self.config)
        self.writer = BatchWriter()
        self.filter_collector = FilterCollector(self.config, self.client)
        self.alert_client = AlertClient(self.config.alert)
        self.s3 = S3Uploader(self.config) if self.config.crawl.s3_upload_enabled else None
        self.raw_storage = raw_storage or RawStorage()
        self.current_batch_id: Optional[str] = None

    def collect_grain_categories(self) -> List[GrainCategory]:
        """카테고리 맵을 조회하고 쌀/잡곡 관련 노드를 반환"""
        category_map = self.client.fetch_category_map()
        return extract_grain_categories(category_map)

    def collect_products_for_category(self, cate: GrainCategory) -> List[ProductData]:
        """단일 쌀/잡곡 카테고리의 상품 리스트를 페이징 수집"""
        products: List[ProductData] = []
        # depth 결정: mcateCd 존재 시 2, scateCd 존재 시 3
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

        # 1페이지 조회 후 totalPage 파악
        first = self.client.fetch_item_list(
            category_depth=depth,
            category_id=cate_id,
            page=1,
            per_page=20,
            add_sub_category=add_sub,
            search_type=search_type,
        )
        items, total_page, _ = _parse_item_list(first)
        products.extend(self._map_items(items))

        for page in range(2, total_page + 1):
            resp = self.client.fetch_item_list(
                category_depth=depth,
                category_id=cate_id,
                page=page,
                per_page=20,
                add_sub_category=add_sub,
                search_type=search_type,
            )
            page_items, _, _ = _parse_item_list(resp)
            products.extend(self._map_items(page_items))
            if self.config.crawl.delay_ms > 0:
                time.sleep(self.config.crawl.delay_ms / 1000)

        return products

    def _map_items(self, items: List[Dict[str, Any]]) -> List[ProductData]:
        """상품 리스트를 ProductData로 매핑"""
        mapped: List[ProductData] = []
        for item in items:
            detail_html = None
            if self.config.crawl.fetch_detail:
                try:
                    detail_html = self.client.fetch_detail_html(item.get("itemNo"))
                except Exception as exc:
                    if self.config.crawl.store_html and self.raw_storage:
                        self.raw_storage.save_error(
                            self.current_batch_id or "adhoc",
                            str(item.get("itemNo") or "unknown"),
                            "detail_fetch_failure",
                            {"error": str(exc)},
                        )
                    detail_html = None
            product = map_item_to_product(item, self.config.store, detail_html=detail_html)
            # S3 업로드 시 presigned URL로 교체
            if self.s3 and self.config.crawl.s3_upload_enabled and product.images:
                new_images = []
                for idx, img in enumerate(product.images):
                    new_url = self.s3.upload_and_presign(img.image_url, self.config.crawl.target, item.get("itemNo"), idx)
                    new_images.append(type(img)(image_url=new_url, display_order=img.display_order))
                product.images = new_images
            if (
                self.config.crawl.store_html
                and self.raw_storage
                and (not product.images or product.price is None or not product.name)
            ):
                if detail_html:
                    self.raw_storage.save_html(
                        self.current_batch_id or "adhoc",
                        str(item.get("itemNo") or "unknown"),
                        detail_html,
                    )
                else:
                    self.raw_storage.save_error(
                        self.current_batch_id or "adhoc",
                        str(item.get("itemNo") or "unknown"),
                        "missing_required_fields",
                        {"item": item},
                    )
            mapped.append(product)
        return mapped

    def build_batch(self, products: List[ProductData], total_count: Optional[int] = None) -> CrawlBatch:
        """상품 리스트로 CrawlBatch 생성"""
        if not self.current_batch_id:
            self.current_batch_id = f"{self.config.crawl.target}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        batch_id = self.current_batch_id
        return CrawlBatch(
            batch_id=batch_id,
            source=self.config.crawl.target,
            crawled_at=datetime.utcnow().isoformat(),
            total_count=total_count if total_count is not None else len(products),
            products=products,
        )

    def run(self) -> Path:
        """전체 쌀/잡곡 배치를 수집하고 JSON으로 저장"""
        start_ts = datetime.utcnow()
        self.current_batch_id = f"{self.config.crawl.target}_{start_ts.strftime('%Y%m%d_%H%M%S')}"
        errors: List[str] = []
        failed_cates: List[Dict[str, Any]] = []
        try:
            categories = self.collect_grain_categories()
            if self.config.crawl.scope == "sample":
                categories = categories[:1]
        except Exception as exc:
            errors.append(f"카테고리 맵 조회 실패: {exc}")
            self.alert_client.notify(f"[CRAWL-ERROR] source=homeplus error={exc}")
            raise

        all_products: List[ProductData] = []
        total_count_acc: int = 0
        for cate in categories:
            try:
                items = self.collect_products_for_category(cate)
                all_products.extend(items)
                total_count_acc += len(items)
            except Exception as exc:
                errors.append(f"{cate.lcateNm}/{cate.mcateNm}/{cate.scateNm} 수집 실패: {exc}")
                failed_cates.append(
                    {
                        "lcateNm": cate.lcateNm,
                        "mcateNm": cate.mcateNm,
                        "scateNm": cate.scateNm,
                        "lcateCd": cate.lcateCd,
                        "mcateCd": cate.mcateCd,
                        "scateCd": cate.scateCd,
                        "error": str(exc),
                    }
                )
                continue

        # source_url 기준 중복 제거 (동일 상품 중복 수집 방지)
        unique_products: Dict[str, ProductData] = {}
        for p in all_products:
            key = p.source_url or f"{p.brand_name}:{p.name}"
            unique_products[key] = p

        batch_products = list(unique_products.values())
        batch = self.build_batch(batch_products, total_count=len(batch_products))
        batch_path = self.writer.save(batch)

        # 필터/패싯 메타를 별도 파일로 저장 (필터 데이터가 있을 때만)
        filter_path = None
        filters = self.filter_collector.collect_all(categories)
        if filters:
            filter_path = self.filter_collector.save(filters, out_dir=self.writer.meta_dir)

        # 요약 로그 및 알림
        failure_ratio = (len(failed_cates) / len(categories)) if categories else 0
        status = "FAILED" if failure_ratio >= 0.1 else "OK"
        summary = (
            f"[CRAWL-SUMMARY] source=homeplus status={status} "
            f"total={len(batch_products)} errors={len(errors)} batch={batch_path.name}"
        )
        print(summary)
        if errors:
            err_text = "; ".join(errors)
            self.alert_client.notify(f"{summary} details={err_text}")
        # 실패 카테고리 로그 파일
        if failed_cates:
            fail_log = self.writer.meta_dir / f"homeplus_failed_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
            with open(fail_log, "w", encoding="utf-8") as f:
                json.dump({"source": "homeplus", "failed": failed_cates}, f, ensure_ascii=False, indent=2)

        # 구조화 로그 저장(모니터링 연동용)
        log_payload = {
            "source": "homeplus",
            "status": status,
            "total_products": len(batch_products),
            "failed_categories": len(failed_cates),
            "category_count": len(categories),
            "batch_file": batch_path.name,
            "filter_file": filter_path.name if filter_path else None,
            "started_at": start_ts.isoformat(),
            "finished_at": datetime.utcnow().isoformat(),
        }
        log_path = self.writer.meta_dir / f"homeplus_log_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(log_payload, f, ensure_ascii=False, indent=2)

        return batch_path


def _parse_item_list(resp: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], int, Optional[int]]:
    """상품 리스트 응답에서 item 리스트와 totalPage, totalCount를 추출"""
    items = []
    total_page = 1
    total_count: Optional[int] = None

    # 아이템 리스트
    for key in ("items", "itemList", "list", "dataList"):
        if key in resp and isinstance(resp[key], list):
            items = resp[key]
            break
    if not items:
        data = resp.get("data")
        if isinstance(data, dict):
            if isinstance(data.get("list"), list):
                items = data["list"]
            elif isinstance(data.get("dataList"), list):
                items = data["dataList"]

    # 페이지 정보
    pagination = resp.get("pagination") or {}
    total_page = pagination.get("totalPage") or pagination.get("total_page") or total_page
    total_count = pagination.get("totalCount") or pagination.get("total_count") or total_count
    if total_count is None:
        data = resp.get("data")
        if isinstance(data, dict) and data.get("totalCount") is not None:
            total_count = data.get("totalCount")
    try:
        total_page = int(total_page)
    except (TypeError, ValueError):
        total_page = 1

    try:
        total_count = int(total_count) if total_count is not None else None
    except (TypeError, ValueError):
        total_count = None

    return items, total_page, total_count
