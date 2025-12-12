"""
홈플러스 상품 카테고리 → SelF 서비스 카테고리 매핑 모듈

`docs/CATEGORY_MAPPING_HOMEPLUS.md` 규칙에 따라 서비스 카테고리를 결정한다.
"""

from datetime import datetime, timezone
import html
import json
import re
from typing import Any, Dict, List, Optional, Tuple
from html.parser import HTMLParser
from urllib.parse import urlparse

from backend.data_pipeline.schemas import ProductData, ProductImage
from crawler.config import StoreConfig


class SkipProduct(Exception):
    """수집 대상에서 제외할 상품을 나타내는 예외"""


def _to_int(value: Any) -> Optional[int]:
    """정수 변환 래퍼"""
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


def _deduplicate(items: List[str]) -> List[str]:
    """리스트 중복 제거(순서 유지)"""
    seen = set()
    ordered: List[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def _dedup_product_images(images: List[ProductImage]) -> List[ProductImage]:
    """이미지 중복 제거(순서 유지). 파일명(UUID) 단위로도 중복 판단."""
    seen = set()
    unique: List[ProductImage] = []
    for img in images:
        if not img.image_url:
            continue
        # 파일명(마지막 path 세그먼트) 기준으로 중복 판단
        path_name = img.image_url.rstrip("/").split("/")[-1]
        key = path_name or img.image_url
        if key in seen:
            continue
        seen.add(key)
        unique.append(img)
    return unique


def _strip_tags(value: Optional[str]) -> Optional[str]:
    """HTML 태그 제거 후 공백 정리"""
    if value is None:
        return None
    # HTML 엔티티 해제 후 태그 제거
    unescaped = html.unescape(value)
    # 이중으로 남은 &nbsp; 텍스트도 공백으로 치환
    unescaped = unescaped.replace("&nbsp;", " ")
    plain = re.sub(r"<[^>]+>", " ", unescaped)
    plain = plain.replace("\xa0", " ")
    plain = " ".join(plain.split())
    # 구두점 앞 공백 제거
    plain = re.sub(r"\s+([.,!?])", r"\1", plain)
    # 괄호 주변 공백 정리
    plain = re.sub(r"\(\s+", "(", plain)
    plain = re.sub(r"\s+\)", ")", plain)
    # 하이픈 앞뒤 과도한 공백 정리
    plain = re.sub(r"\s+-\s+", " - ", plain)
    return plain.strip()


def _extract_detail_json(detail_html: str) -> Optional[Dict[str, Any]]:
    """상세 페이지 내 스크립트(JSON)에서 상품 상세 JSON을 추출"""
    # id 명시된 스크립트 우선
    patterns = [
        r'<script[^>]*id="/item/getItemDetail\\.json"[^>]*>(.*?)</script>',
        r'<script[^>]*type="application/json"[^>]*>(.*?)</script>',
    ]
    for pat in patterns:
        for m in re.finditer(pat, detail_html, flags=re.DOTALL):
            body = m.group(1)
            if "returnCode" not in body:
                continue
            try:
                return json.loads(body)
            except Exception:
                continue
    return None


def _normalize_img_url(url: str) -> str:
    """상대/스킴 없는 이미지를 절대 URL로 변환하고 쿼리스트링을 제거 (무효 시 None)"""
    if not url:
        return None
    candidate = url.strip()
    if candidate.startswith("//"):
        candidate = "https:" + candidate
    if candidate.startswith("/"):
        candidate = f"https://image.homeplus.kr{candidate}"
    parsed = urlparse(candidate)
    if not parsed.scheme or not parsed.netloc:
        return None
    # 경로가 빈 경우(예: https://image.homeplus.kr) 무효 처리
    if parsed.path in ("", "/"):
        return None
    # 쿼리/프래그먼트 제거해 정규화
    normalized = parsed._replace(query="", fragment="")
    return normalized.geturl()


def _parse_detail_html(detail_html: Optional[str]) -> Tuple[List[ProductImage], List[str], Optional[str], Optional[str]]:
    """
    상세 HTML에서 썸네일 영역 이미지, 설명 영역 이미지를 분리 추출한다.

    Returns:
        carousel_images: 썸네일 슬라이더 이미지 리스트
        desc_images: 본문(설명) 이미지 URL 리스트
        full_html: 원본 HTML
        text_desc: 태그 제거된 본문 텍스트
    """
    if not detail_html:
        return [], [], None, None

    unescaped = html.unescape(detail_html)

    # 썸네일(대표) 영역 추출: prodDetailThumb DIV 내부 img src 수집
    class CarouselParser(HTMLParser):
        def __init__(self) -> None:
            super().__init__()
            self.in_thumb = False
            self.depth = 0
            self.images: List[str] = []

        def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
            if tag == "div":
                class_value = next((v for k, v in attrs if k == "class"), "") or ""
                if not self.in_thumb and "prodDetailThumb" in class_value:
                    self.in_thumb = True
                    self.depth = 1
                    return
                if self.in_thumb:
                    self.depth += 1
            if tag == "img" and self.in_thumb:
                src = next((v for k, v in attrs if k == "src"), None)
                if src:
                    self.images.append(src)

        def handle_endtag(self, tag: str) -> None:
            if tag == "div" and self.in_thumb:
                self.depth -= 1
                if self.depth <= 0:
                    self.in_thumb = False

    parser = CarouselParser()
    parser.feed(unescaped)
    carousel_urls = parser.images

    normalized_carousel = []
    for url in carousel_urls:
        norm = _normalize_img_url(url)
        if norm:
            normalized_carousel.append(norm)
    normalized_carousel = _deduplicate(normalized_carousel)
    carousel_images = [ProductImage(image_url=url, display_order=idx) for idx, url in enumerate(normalized_carousel)]

    # 본문(설명) 영역 이미지 추출
    desc_urls = re.findall(r'<img[^>]+(?:data-src|src)=[\"\\\']([^\"\\\']+)', unescaped, flags=re.IGNORECASE)
    filtered_desc = []
    for url in desc_urls:
        norm = _normalize_img_url(url)
        if not norm:
            continue
        if "facebook.com" in norm or "default_logo.svg" in norm:
            continue
        if norm in normalized_carousel:
            continue
        filtered_desc.append(norm)
    desc_urls = _deduplicate(filtered_desc)

    # 캐러셀이 비어 있으면 OG/preload/JSON 기반 이미지로 대표 이미지 보강
    if not carousel_images:
        fallback_urls: List[str] = []
        og_match = re.search(
            r'<meta[^>]+property=["\\\']og:image["\\\'][^>]+content=["\\\']([^"\\\']+)["\\\']',
            unescaped,
            flags=re.IGNORECASE,
        )
        if og_match:
            fallback_urls.append(og_match.group(1))

        preload_urls = re.findall(
            r'<link[^>]+rel=["\\\']preload["\\\'][^>]+as=["\\\']image["\\\'][^>]+href=["\\\']([^"\\\']+)["\\\']',
            unescaped,
            flags=re.IGNORECASE,
        )
        fallback_urls.extend(preload_urls)

        json_img_paths = re.findall(r'"url"\s*:\s*"(?:\\/)?(/td/[^"\\\']+)"', unescaped)
        for path in json_img_paths:
            fallback_urls.append(f"https://image.homeplus.kr{path}")

        normalized_fallback = []
        for url in fallback_urls:
            norm = _normalize_img_url(url)
            if norm:
                normalized_fallback.append(norm)
        normalized_fallback = _deduplicate(normalized_fallback)

        carousel_images = [ProductImage(image_url=url, display_order=idx) for idx, url in enumerate(normalized_fallback)]

    text_desc = _strip_tags(unescaped)
    return carousel_images, desc_urls, unescaped, text_desc


def _detect_processing_level(name: str, category: Optional[str]) -> Optional[str]:
    """가공도 추출"""
    text = f"{name} {category or ''}"
    processed_keywords = ["즉석", "즉석밥", "밥", "요리완제품", "즉석조리"]
    for kw in processed_keywords:
        if kw in text:
            return "processed"
    return "raw"


def _map_service_category(lcate: Optional[str], rcate: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """홈플러스 상위 카테고리 기준으로 표준 카테고리 매핑 (1depth만 사용)"""
    cat = lcate or rcate or ""
    if cat.startswith("쌀/잡곡"):
        return "GRAIN", None
    if cat.startswith("채소"):
        return "VEGETABLE", None
    if cat.startswith("과일"):
        return "FRUIT", None
    if cat.startswith("버섯") or cat.startswith("나물"):
        return "MUSHROOM_HERB", None
    if cat.startswith("두부") or cat.startswith("콩") or "계란" in cat:
        return "BEAN_EGG", None
    if cat.startswith("정육") or cat.startswith("축산"):
        return "MEAT", None
    if cat.startswith("수산") or cat.startswith("건어물") or cat.startswith("해산"):
        return "SEAFOOD", None
    if cat.startswith("우유") or cat.startswith("유제품"):
        return "DAIRY", None
    if cat.startswith("김치") or cat.startswith("반찬"):
        return "KIMCHI_SIDE", None
    if "양념" in cat or "오일" in cat or "소스" in cat or "장류" in cat:
        return "SEASONING_SAUCE_OIL", None
    if "면" in cat or "밀가루" in cat or "가루" in cat or "베이킹" in cat:
        return "NOODLE_FLOUR", None
    # 기본 기타
    return "NUT_DRY_ETC", None


def map_item_to_product(
    item: Dict[str, Any],
    store: StoreConfig,
    detail_html: Optional[str] = None,
    store_html: bool = False,
) -> ProductData:
    """상품 JSON을 ProductData로 변환"""
    item_no = item.get("itemNo")
    dc_price = _to_int(item.get("dcPrice"))
    sale_price = _to_int(item.get("salePrice"))
    price = dc_price if dc_price is not None else (sale_price or 0)

    original_price = sale_price if dc_price is not None else None

    detail_images, desc_image_urls, detail_full_desc, detail_text = _parse_detail_html(detail_html)

    # 상세 요약 문구: 우선 상세 JSON의 positiveReviewSummary, 없으면 HTML summaryContent
    summary_text = None

    # 상세 JSON 파싱 (이미지 보강 및 판매중지 감지)
    detail_json = _extract_detail_json(detail_html) if detail_html else None
    if not detail_json and detail_html:
        if "현재 판매중인 상품이 아닙니다" in detail_html or "\"returnCode\":\"1007\"" in detail_html:
            raise SkipProduct("판매중지/오류 상품")
    if detail_json:
        return_code = detail_json.get("returnCode")
        if return_code and return_code != "SUCCESS":
            raise SkipProduct("판매중지/오류 상품")
        data_item = (detail_json.get("data") or {}).get("item") or {}
        basic = data_item.get("basic") or {}
        sale = data_item.get("sale") or {}
        item_status = str(basic.get("itemStatus", "A")).upper()
        sold_out_flag = str(sale.get("itemSoldOutYn", "N")).upper()
        stop_deal = str(sale.get("stopDealYn", "N")).upper()
        if item_status not in ("A", "") or sold_out_flag == "Y" or stop_deal == "Y":
            raise SkipProduct("판매중지/품절 상품")

        # 상세 JSON의 이미지(메인/라벨) 보강
        img_block = data_item.get("img") or {}
        json_imgs: List[str] = []
        for key in ("mainList", "labelList"):
            for img in img_block.get(key) or []:
                url = img.get("url")
                norm = _normalize_img_url(url) if url else None
                if norm:
                    json_imgs.append(norm)
        if json_imgs:
            json_imgs = _deduplicate(json_imgs)
            if not detail_images:
                detail_images = [ProductImage(image_url=u, display_order=i) for i, u in enumerate(json_imgs)]
            else:
                # 기존 썸네일 뒤에 JSON 기반 이미지를 보조로 추가
                offset = len(detail_images)
                for i, u in enumerate(json_imgs):
                    detail_images.append(ProductImage(image_url=u, display_order=offset + i))

        # 상세 설명 텍스트: itemDesc 기준으로 갱신 (전체 HTML이 아닌 설명 영역 텍스트만)
        item_desc = basic.get("itemDesc")
        if item_desc:
            detail_text = _strip_tags(item_desc)
            # 상세 JSON에 요약(positiveReviewSummary)이 있으면 short_description 기본값으로 사용
            if not summary_text:
                summary_text = sale.get("positiveReviewSummary") or basic.get("itemPrMessage")

    # HTML에서 summaryContent 추출 (JSON에 없을 때 보조)
    if detail_html and not summary_text:
        summary_match = re.search(
            r'<p[^>]*class=["\\\']summaryContent["\\\'][^>]*>(.*?)</p>',
            detail_html,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if summary_match:
            summary_text = _strip_tags(summary_match.group(1))
    image_url = item.get("imageUrl") or item.get("imgUrl") or item.get("image_url")
    images: List[ProductImage] = []
    # 썸네일 슬라이더가 있으면 우선 사용, 없으면 리스트 이미지를 대체 사용
    if detail_images:
        images = detail_images
    elif image_url:
        images.append(ProductImage(image_url=image_url, display_order=0))

    images = _dedup_product_images(images)

    unit = _build_unit(item)

    rcate_nm = item.get("rcateNm")
    lcate_nm = item.get("lcateNm")
    mcate_nm = item.get("mcateNm")
    scate_nm = item.get("scateNm")
    source_category_path = None
    if lcate_nm and mcate_nm and scate_nm:
        source_category_path = f"{lcate_nm} > {mcate_nm} > {scate_nm}"

    # 서비스 카테고리 매핑 (1depth 표준 카테고리만 사용)
    service_category, service_subcategory = _map_service_category(lcate_nm, rcate_nm)

    processing_level = _detect_processing_level(str(item.get("itemNm", "")), scate_nm)

    fallback_text = _strip_tags(item.get("itemDtlDscr"))
    short_description = summary_text or item.get("recomMsg") or item.get("itemAttrTop")
    # 본문 이미지 리스트 (리스트 그대로)
    full_image_description = desc_image_urls if desc_image_urls else None

    return ProductData(
        name=str(item.get("itemNm", "")).strip(),
        price=price,
        source_site="homeplus",
        source_url=_build_source_url(item_no, store),
        crawled_at=datetime.now(timezone.utc).isoformat(),
    category_name=lcate_nm or rcate_nm or mcate_nm or scate_nm,
        unit=unit,
        short_description=short_description,
        full_description=detail_full_desc if store_html else None,  # HTML 원문은 옵션 저장
        full_image_description=full_image_description,
        full_text_description=detail_text or fallback_text,
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
