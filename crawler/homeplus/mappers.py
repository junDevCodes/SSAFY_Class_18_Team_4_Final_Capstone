"""
홈플러스 원문 카테고리 → SelF 표준 카테고리 매핑 모듈

`docs/CATEGORY_MAPPING_HOMEPLUS.md` 규칙에 따라 서비스 카테고리를 결정한다.
"""

from datetime import datetime
import html
import re
from typing import Any, Dict, List, Optional

from backend.data_pipeline.schemas import ProductData, ProductImage
from crawler.config import StoreConfig


def _to_int(value: Any) -> Optional[int]:
    """정수 변환 헬퍼"""
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _build_unit(item: Dict[str, Any]) -> Optional[str]:
    """단위 문자열 생성"""
    total_qty = item.get("totalUnitQty")
    unit_measure = item.get("unitMeasure")
    if total_qty and unit_measure:
        return f"{total_qty}{unit_measure}"
    sale_unit = item.get("saleUnit")
    if sale_unit:
        return f"1{sale_unit}"
    return None


def _build_source_url(item_no: Any, store: StoreConfig) -> str:
    """모바일 상세 페이지 URL 생성"""
    return (
        f"https://mfront.homeplus.co.kr/item?itemNo={item_no}"
        f"&storeType={store.store_type}&storeId={store.store_id}"
    )


def _parse_detail_html(detail_html: Optional[str]) -> (List[ProductImage], Optional[str]):
    """상세 HTML에서 이미지와 본문을 추출"""
    if not detail_html:
        return [], None
    unescaped = html.unescape(detail_html)
    raw_imgs = re.findall(r'<img[^>]+src=[\"\\\']([^\"\\\']+)', unescaped, flags=re.IGNORECASE)
    filtered = []
    for url in raw_imgs:
        if not url.startswith("http"):
            continue
        if "facebook.com" in url or "default_logo.svg" in url:
            continue
        filtered.append(url)
    images = [ProductImage(image_url=url, display_order=idx) for idx, url in enumerate(filtered)]
    return images, unescaped


def _detect_processing_level(name: str, category: Optional[str]) -> Optional[str]:
    """가공도 추론"""
    text = f"{name} {category or ''}"
    processed_keywords = ["즉석", "즉석밥", "죽", "시리얼", "즉석조리"]
    for kw in processed_keywords:
        if kw in text:
            return "processed"
    return "raw"


def map_item_to_product(item: Dict[str, Any], store: StoreConfig, detail_html: Optional[str] = None) -> ProductData:
    """상품 JSON을 ProductData로 변환"""
    item_no = item.get("itemNo")
    dc_price = _to_int(item.get("dcPrice"))
    sale_price = _to_int(item.get("salePrice"))
    price = dc_price if dc_price is not None else (sale_price or 0)

    original_price = sale_price if dc_price is not None else None

    detail_images, detail_full_desc = _parse_detail_html(detail_html)
    image_url = item.get("imageUrl") or item.get("imgUrl") or item.get("image_url")
    images: List[ProductImage] = []
    # 대표 이미지 우선: 리스트 응답의 메인 이미지 사용
    if image_url:
        images.append(ProductImage(image_url=image_url, display_order=0))
    # 상세 이미지 모두 추가 (display_order 연속)
    for idx, img in enumerate(detail_images, start=len(images)):
        # 중복 제거
        if all(img.image_url != existing.image_url for existing in images):
            images.append(ProductImage(image_url=img.image_url, display_order=idx))

    unit = _build_unit(item)

    lcate_nm = item.get("lcateNm")
    mcate_nm = item.get("mcateNm")
    scate_nm = item.get("scateNm")
    source_category_path = None
    if lcate_nm and mcate_nm and scate_nm:
        source_category_path = f"{lcate_nm} > {mcate_nm} > {scate_nm}"

    # 서비스 카테고리 매핑 (쌀/잡곡 전용)
    service_category = None
    service_subcategory = None
    if lcate_nm == "쌀/잡곡":
        service_category = "GRAIN"
        service_subcategory = mcate_nm

    processing_level = _detect_processing_level(str(item.get("itemNm", "")), scate_nm)
    text_desc = None
    if detail_full_desc:
        text_desc = re.sub(r"<[^>]+>", " ", detail_full_desc)
        text_desc = " ".join(text_desc.split())

    return ProductData(
        name=str(item.get("itemNm", "")).strip(),
        price=price,
        source_site="homeplus",
        source_url=_build_source_url(item_no, store),
        crawled_at=datetime.utcnow().isoformat(),
        category_name=lcate_nm or mcate_nm or scate_nm,
        unit=unit,
        short_description=item.get("recomMsg") or item.get("itemAttrTop"),
        full_description=None,  # 호환 필드는 비워두고 확장 필드 사용
        full_image_description=detail_full_desc or item.get("itemDtlDscr"),
        full_text_description=text_desc or item.get("itemDtlDscr"),
        images=images,
        original_price=original_price,
        brand_name=item.get("brandNm"),
        source_category_path=source_category_path,
        source_category_l1=lcate_nm,
        source_category_l2=mcate_nm,
        source_category_l3=scate_nm,
        service_category=service_category,
        service_subcategory=service_subcategory,
        storage_type="ambient",
        processing_level=processing_level,
    )
