"""
홈플러스 원문 카테고리 → SelF 표준 카테고리 매핑 모듈

`docs/CATEGORY_MAPPING_HOMEPLUS.md` 규칙에 따라 서비스 카테고리를 결정한다.
"""

from datetime import datetime, timezone
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


def _parse_detail_html(detail_html: Optional[str]) -> (List[ProductImage], Optional[str], Optional[str]):
    """상세 HTML에서 이미지와 본문을 추출"""
    if not detail_html:
        return [], None, None
    unescaped = html.unescape(detail_html)

    primary: Optional[str] = None
    carousel: List[str] = []
    # 제품 상세 썸네일 영역 우선 추출
    carousel = re.findall(
        r'prodDetailThumb.*?<img[^>]+src=[\"\\\']([^\"\\\']+)',
        unescaped,
        flags=re.IGNORECASE | re.DOTALL,
    )

    og_match = re.search(r'<meta[^>]+property=["\\\']og:image["\\\'][^>]+content=["\\\']([^"\\\']+)["\\\']', unescaped, flags=re.IGNORECASE)
    if og_match:
        primary = og_match.group(1)

    raw_imgs = re.findall(r'<img[^>]+src=[\"\\\']([^\"\\\']+)', unescaped, flags=re.IGNORECASE)
    filtered = []
    for url in raw_imgs:
        if not url.startswith("http"):
            continue
        if "facebook.com" in url or "default_logo.svg" in url:
            continue
        filtered.append(url)

    ordered_urls: List[str] = []
    for url in carousel:
        if url not in ordered_urls:
            ordered_urls.append(url)
    if primary:
        ordered_urls.append(primary)
    for url in filtered:
        if url not in ordered_urls:
            ordered_urls.append(url)

    images = [ProductImage(image_url=url, display_order=idx) for idx, url in enumerate(ordered_urls)]
    text_desc = re.sub(r"<[^>]+>", " ", unescaped)
    text_desc = " ".join(text_desc.split())
    return images, unescaped, text_desc


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

    detail_images, detail_full_desc, detail_text = _parse_detail_html(detail_html)
    image_url = item.get("imageUrl") or item.get("imgUrl") or item.get("image_url")
    images: List[ProductImage] = []
    # 상세 HTML에서 추출한 대표 이미지를 우선 사용
    if detail_images:
        images.append(detail_images[0])
        for extra in detail_images[1:]:
            if extra.image_url not in {img.image_url for img in images}:
                images.append(extra)
    elif image_url:
        images.append(ProductImage(image_url=image_url, display_order=0))

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

    return ProductData(
        name=str(item.get("itemNm", "")).strip(),
        price=price,
        source_site="homeplus",
        source_url=_build_source_url(item_no, store),
        crawled_at=datetime.now(timezone.utc).isoformat(),
        category_name=scate_nm or mcate_nm or lcate_nm,
        unit=unit,
        short_description=item.get("recomMsg") or item.get("itemAttrTop"),
        full_description=detail_full_desc,  # HTML 전체
        full_image_description="\n".join([img.image_url for img in detail_images]) if detail_images else None,
        full_text_description=detail_text or item.get("itemDtlDscr"),
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
