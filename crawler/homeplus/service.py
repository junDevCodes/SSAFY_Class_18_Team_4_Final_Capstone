"""
홈플러스 크롤링 서비스

카테고리 맵 조회 → 쌀/잡곡 카테고리 식별 → 상품 리스트 페이징 수집 →
ProductData 매핑 → CrawlBatch 생성/저장을 담당한다.
"""

import os
import logging
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
from crawler.homeplus.mappers import (
    map_item_to_product,
    SkipProduct,
    _map_service_category_for_category_node,
    _service_category_display_name,
)
from crawler.homeplus.parsers import CategoryNode, extract_categories
from crawler.homeplus.validator import validate_product
from crawler.s3_uploader import S3Uploader
from crawler.raw_storage import RawStorage
import re
import re


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


logger = logging.getLogger(__name__)


class HomeplusService:
    """홈플러스 크롤링 서비스"""

    def __init__(
        self,
        config: Optional[AppConfig] = None,
        client: Optional[HomeplusClient] = None,
        raw_storage: Optional[RawStorage] = None,
        s3_uploader: Optional[S3Uploader] = None,
    ):
        self.config = config or AppConfig.load()
        self.client = client or HomeplusClient(self.config)
        self.writer = BatchWriter()
        self.filter_collector = FilterCollector(self.config, self.client)
        self.alert_client = AlertClient(self.config.alert)
        self.s3 = s3_uploader or (S3Uploader(self.config) if self.config.crawl.s3_upload_enabled else None)
        self.raw_storage = raw_storage or RawStorage()
        self.current_batch_id: Optional[str] = None
        self.validation_skipped_count: int = 0

    def collect_categories(self) -> List[CategoryNode]:
        """카테고리 맵을 조회하고 유효 카테고리 노드를 반환

        홈플러스 전체 카테고리 트리에서 SelF 서비스에서 사용할
        식품 관련 상위 카테고리만 필터링한다.
        `docs/CATEGORY_MAPPING_HOMEPLUS.md` / `docs/CATEGORY_STANDARD.md` 를 기준으로 한다.
        """
        category_map = self.client.fetch_category_map()
        all_categories = extract_categories(category_map)

        # 서비스 표준 카테고리 코드 필터 (예: "GRAIN,VEGETABLE"), 없으면 전체 사용
        raw_service_filter = self.config.crawl.service_category_filter
        allowed_service_cats = None
        if raw_service_filter:
            allowed_service_cats = {
                code.strip().upper()
                for code in raw_service_filter.split(",")
                if code.strip()
            }

        filtered: List[CategoryNode] = []
        for cate in all_categories:
            # Depth+ID + 이름 기반 매핑으로 서비스 카테고리 결정
            service_cat = _map_service_category_for_category_node(
                cate.lcateNm,
                cate.mcateNm,
                cate.scateNm,
                cate.rcateNm,
                cate.lcateCd,
                cate.mcateCd,
                cate.scateCd,
            )
            # 인식 불가(비식품) 카테고리는 건너뜀
            if service_cat is None:
                continue
            # 서비스 표준 카테고리 코드 기준 필터 (선택)
            if allowed_service_cats is not None and service_cat not in allowed_service_cats:
                continue

            filtered.append(cate)

        logger.info(
            "카테고리 필터링 적용: 전체 %d개 중 %d개만 수집 대상으로 사용합니다. service_filter=%s",
            len(all_categories),
            len(filtered),
            ",".join(sorted(allowed_service_cats)) if allowed_service_cats else "ALL",
        )
        return filtered

    def collect_products_for_category(self, cate: CategoryNode) -> List[ProductData]:
        """단일 카테고리의 상품 리스트를 페이징 수집"""
        products: List[ProductData] = []
        # 이 카테고리가 어떤 SelF 서비스 카테고리에 속하는지 Depth/ID 규칙을 기준으로 한 번 더 계산
        # 이 값은 아래에서 상품 레벨의 service_category/category_name 을 강제 일관화하는 데 사용
        forced_service_cat = _map_service_category_for_category_node(
            cate.lcateNm,
            cate.mcateNm,
            cate.scateNm,
            cate.rcateNm,
            cate.lcateCd,
            cate.mcateCd,
            cate.scateCd,
        )
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

        # 샘플링 모드: 카테고리당 지정된 개수만 수집
        sample_limit = self.config.crawl.sample_per_category

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
        # 첫 페이지에서 샘플링 상한을 고려해 매핑
        if sample_limit:
            # 이미 수집된 상품 수를 고려해 남은 슬롯 계산
            remaining = sample_limit - len(products)
            if remaining <= 0:
                return products[:sample_limit]
            page_products = self._map_items(items, max_items=remaining, forced_service_category=forced_service_cat)
        else:
            page_products = self._map_items(items, forced_service_category=forced_service_cat)

        # 카테고리 노드 단위로 결정된 서비스 카테고리를 상품 레벨에 강제 반영
        if forced_service_cat:
            display_name = _service_category_display_name(forced_service_cat)
            for p in page_products:
                p.service_category = forced_service_cat
                if display_name:
                    p.category_name = display_name

        products.extend(page_products)

        # 샘플링 모드이고 이미 충분한 상품을 수집했다면 중단
        if sample_limit and len(products) >= sample_limit:
            return products[:sample_limit]

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
            if sample_limit:
                remaining = sample_limit - len(products)
                if remaining <= 0:
                    return products[:sample_limit]
                page_products = self._map_items(page_items, max_items=remaining, forced_service_category=forced_service_cat)
            else:
                page_products = self._map_items(page_items, forced_service_category=forced_service_cat)

            # 카테고리 단위 서비스 카테고리를 상품 레벨에 반영
            if forced_service_cat:
                display_name = _service_category_display_name(forced_service_cat)
                for p in page_products:
                    p.service_category = forced_service_cat
                    if display_name:
                        p.category_name = display_name

            products.extend(page_products)
            
            # 샘플링 모드이고 충분한 상품을 수집했다면 중단
            if sample_limit and len(products) >= sample_limit:
                return products[:sample_limit]
            
            if self.config.crawl.delay_ms > 0:
                time.sleep(self.config.crawl.delay_ms / 1000)

        return products

    def _map_items(
        self,
        items: List[Dict[str, Any]],
        max_items: Optional[int] = None,
        forced_service_category: Optional[str] = None,
    ) -> List[ProductData]:
        """상품 리스트를 ProductData로 매핑

        Args:
            items: 홈플러스 상품 리스트 JSON 아이템 배열
            max_items: 이 함수에서 생성할 최대 ProductData 개수
                (샘플링 모드에서 카테고리당 상세 조회 수를 제한하기 위해 사용)
        """
        mapped: List[ProductData] = []
        for item in items:
            # 샘플링 상한에 도달하면 조기 종료
            if max_items is not None and len(mapped) >= max_items:
                break
            item_no = item.get("itemNo")
            # 판매/노출 불가 상품 및 item_no 누락 스킵
            doc_disp = str(item.get("docDispYn", "Y")).upper()
            sold_out = str(item.get("soldOutYn", "N")).upper()
            item_sold_out = str(item.get("itemSoldOutYn", "N")).upper()
            if not item_no:
                logger.info("item_no가 없어 스킵합니다: %s", item)
                continue
            if doc_disp == "N" or sold_out == "Y" or item_sold_out == "Y":
                logger.info("품절/비노출 상품 스킵: item_no=%s docDispYn=%s soldOutYn=%s itemSoldOutYn=%s", item_no, doc_disp, sold_out, item_sold_out)
                continue
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
            try:
                product = map_item_to_product(
                    item,
                    self.config.store,
                    detail_html=detail_html,
                    store_html=self.config.crawl.store_html,
                    forced_service_category=forced_service_category,
                )
            except SkipProduct as exc:
                logger.info("판매중지/제외 상품 스킵: item_no=%s reason=%s", item_no, exc)
                continue
            # S3 업로드 시 presigned URL로 교체
            if self.s3 and self.config.crawl.s3_upload_enabled and product.images:
                new_images = []
                for idx, img in enumerate(product.images):
                    new_url = self.s3.upload_and_presign(
                        img.image_url,
                        self.current_batch_id or self.config.crawl.target,
                        item.get("itemNo"),
                        idx,
                        image_type="thumbnail",  # 대표 이미지는 thumbnail prefix 사용
                    )
                    new_images.append(type(img)(image_url=new_url, display_order=img.display_order))
                product.images = new_images
            
            # full_image_description 이미지도 S3 업로드
            if self.s3 and self.config.crawl.s3_upload_enabled and product.full_image_description:
                new_desc_images = []
                for idx, desc_url in enumerate(product.full_image_description):
                    new_url = self.s3.upload_and_presign(
                        desc_url,
                        self.current_batch_id or self.config.crawl.target,
                        item.get("itemNo"),
                        idx,
                        image_type="product_detail",  # 상세 설명 이미지는 product_detail prefix 사용
                    )
                    new_desc_images.append(new_url)
                product.full_image_description = new_desc_images
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
            # 검증 실패(에러 레벨 이슈) 상품은 배치에서 제외
            issues = validate_product(len(mapped), product)
            error_codes = {i.code for i in issues if i.level == "error"}
            if error_codes:
                logger.info("검증 실패로 상품 스킵: item_no=%s codes=%s", item_no, ",".join(sorted(error_codes)))
                continue

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

    def run_price_refresh(self) -> Path:
        """가격 추적 모드: 필수 필드만 수집하여 가격 업데이트"""
        start_ts = datetime.utcnow()
        pid_suffix = os.getpid()
        self.current_batch_id = f"{self.config.crawl.target}_price_{start_ts.strftime('%Y%m%d_%H%M%S')}_{pid_suffix}"
        
        # 가격 추적 대상 로드
        if self.config.crawl.price_refresh_mode == "sample":
            if not self.config.crawl.price_sample_input:
                raise ValueError("PRICE_REFRESH_MODE=sample일 때 PRICE_SAMPLE_INPUT이 필요합니다.")
            price_targets = _load_price_targets(self.config.crawl.price_sample_input)
        else:  # full mode
            # TODO: DB에서 전체 상품 source_url 로드
            raise NotImplementedError("PRICE_REFRESH_MODE=full은 아직 구현되지 않았습니다.")
        
        if not price_targets:
            logger.warning("가격 추적 대상이 없습니다.")
            # 빈 배치 생성
            batch = self.build_batch([], total_count=0)
            batch_path = self.writer.save(batch)
            return batch_path
        
        products: List[ProductData] = []
        errors: List[str] = []
        
        for target in price_targets:
            item_no = target.get("item_no")
            source_url = target.get("source_url")
            service_category = target.get("service_category")
            
            if not item_no:
                errors.append(f"item_no 누락: {target}")
                continue
            
            try:
                # 상품 리스트 API에서 해당 itemNo 찾기 (가격 정보 포함)
                # 또는 상세 API에서 가격만 가져오기
                # 간단하게 상세 HTML에서 가격 정보 추출
                detail_html = self.client.fetch_detail_html(item_no)
                detail_json = None
                
                # 상세 JSON 추출
                from crawler.homeplus.mappers import _extract_detail_json
                detail_json = _extract_detail_json(detail_html)
                
                if not detail_json:
                    errors.append(f"상세 JSON 추출 실패: item_no={item_no}")
                    continue
                
                # 가격 정보 추출
                data_item = (detail_json.get("data") or {}).get("item") or {}
                sale = data_item.get("sale") or {}
                dc_price = sale.get("dcPrice") or 0
                sale_price = sale.get("salePrice") or 0
                
                # 가격 계산 (mappers.py와 동일한 로직)
                from crawler.homeplus.mappers import _to_int
                dc_price_int = _to_int(dc_price)
                sale_price_int = _to_int(sale_price)
                price = dc_price_int if dc_price_int is not None and dc_price_int > 0 else (sale_price_int or 0)
                original_price = sale_price_int if dc_price_int is not None and dc_price_int > 0 else None
                
                # 최소 필드만으로 ProductData 생성
                if not source_url:
                    source_url = f"https://mfront.homeplus.co.kr/item?itemNo={item_no}&storeType={self.config.store.store_type}&storeId={self.config.store.store_id}"
                
                # 이미지 1개 이상 필요 (검증 통과용)
                img_block = data_item.get("img") or {}
                main_imgs = img_block.get("mainList") or []
                image_url = None
                if main_imgs and len(main_imgs) > 0:
                    img_url = main_imgs[0].get("url") if isinstance(main_imgs[0], dict) else str(main_imgs[0])
                    from crawler.homeplus.mappers import _normalize_img_url
                    image_url = _normalize_img_url(img_url) if img_url else None
                
                # 최소 필드만으로 ProductData 생성
                product = ProductData(
                    name=f"가격추적_{item_no}",  # 스키마 필수이지만 실제 미사용
                    price=price,
                    source_site=self.config.crawl.target,  # 스키마 필수이지만 실제 미사용
                    source_url=source_url,
                    crawled_at=datetime.utcnow().isoformat(),
                    original_price=original_price,
                    service_category=service_category,
                    images=[ProductImage(image_url=image_url, display_order=0)] if image_url else [],
                )
                
                products.append(product)
                
                if self.config.crawl.delay_ms > 0:
                    time.sleep(self.config.crawl.delay_ms / 1000)
                    
            except Exception as exc:
                errors.append(f"item_no={item_no} 처리 실패: {exc}")
                logger.error("가격 추적 실패: item_no=%s error=%s", item_no, exc)
                continue
        
        # 배치 생성 및 저장
        batch = self.build_batch(products, total_count=len(products))
        batch_path = self.writer.save(batch)
        
        # 요약 로그
        status = "FAILED" if len(errors) > len(products) * 0.1 else "OK"
        summary = (
            f"[PRICE-REFRESH-SUMMARY] source=homeplus status={status} "
            f"mode={self.config.crawl.price_refresh_mode} "
            f"total={len(products)} errors={len(errors)} batch={batch_path.name}"
        )
        print(summary)
        logger.info(summary)
        self.alert_client.notify(summary)
        
        return batch_path

    def run(self) -> Path:
        """전체 배치를 수집하고 JSON으로 저장"""
        # 가격 추적 모드 분기 처리
        if self.config.crawl.mode == "price_refresh":
            return self.run_price_refresh()
        
        # 일반 크롤링 모드
        start_ts = datetime.utcnow()
        self.current_batch_id = f"{self.config.crawl.target}_{start_ts.strftime('%Y%m%d_%H%M%S')}"
        errors: List[str] = []
        failed_cates: List[Dict[str, Any]] = []
        try:
            categories = self.collect_categories()
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
        # 서비스 카테고리 필터(있다면) 요약용 문자열
        service_filter = self.config.crawl.service_category_filter or "ALL"
        summary = (
            f"[CRAWL-SUMMARY] source=homeplus status={status} "
            f"service_category_filter={service_filter} "
            f"total={len(batch_products)} errors={len(errors)} batch={batch_path.name}"
        )
        print(summary)
        # 크롤 실행 결과를 슬랙으로 통지(성공/실패 공통)
        self.alert_client.notify(summary)
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


def _extract_item_no_from_url(url: str) -> Optional[str]:
    """URL에서 itemNo를 추출합니다."""
    match = re.search(r"itemNo=(\d+)", url)
    if match:
        return match.group(1)
    return None


def _load_price_targets(input_file: Path) -> List[Dict[str, str]]:
    """가격 추적 대상 파일을 읽어서 item_no 리스트를 반환합니다."""
    if not input_file.exists():
        logger.error("가격 추적 대상 파일이 없습니다: %s", input_file)
        return []

    try:
        with open(input_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        items = data.get("items", [])
        result = []
        for item in items:
            item_no = item.get("item_no")
            source_url = item.get("source_url")
            service_category = item.get("service_category")

            if item_no:
                result.append({
                    "source": item.get("source", "homeplus"),
                    "item_no": item_no,
                    "source_url": source_url,
                    "service_category": service_category
                })
            elif source_url:
                extracted_item_no = _extract_item_no_from_url(source_url)
                if extracted_item_no:
                    result.append({
                        "source": item.get("source", "homeplus"),
                        "item_no": extracted_item_no,
                        "source_url": source_url,
                        "service_category": service_category
                    })
                else:
                    logger.warning("source_url에서 itemNo 추출 실패: %s", source_url)
        logger.info("가격 추적 대상 %d개 로드 완료: %s", len(result), input_file)
        return result
    except Exception as exc:
        logger.error("가격 추적 대상 파일 읽기 실패: %s error=%s", input_file, exc)
        return []
