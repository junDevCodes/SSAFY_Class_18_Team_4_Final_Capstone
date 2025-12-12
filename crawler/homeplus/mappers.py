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


def _map_service_category_by_depth_id(
    category_depth: Optional[int],
    category_id: Optional[int],
) -> Optional[str]:
    """categoryDepth + categoryId 기반 서비스 카테고리 매핑

    `docs/CATEGORY_MAPPING_HOMEPLUS.md` 3장 규칙을 반영한다.
    제외 규칙을 먼저 체크하고, 그 다음 포함 규칙을 체크한다.

    Args:
        category_depth: 카테고리 깊이 (0=루트, 2=중분류, 3=소분류)
        category_id: 카테고리 ID

    Returns:
        서비스 카테고리 코드 또는 None (매핑 실패 시)
    """
    if category_depth is None or category_id is None:
        return None

    # 제외 규칙 (다른 카테고리로 재매핑)
    exclusion_rules: Dict[Tuple[int, int], str] = {
        # FRUIT에서 제외 → NUT_DRY_ETC
        (3, 300020): "NUT_DRY_ETC",
        (3, 300021): "NUT_DRY_ETC",
        # MEAT에서 제외 → BEAN_EGG
        (2, 200048): "BEAN_EGG",
        # KIMCHI_SIDE에서 제외 → BEAN_EGG
        (2, 200063): "BEAN_EGG",
        # NOODLE_FLOUR에서 제외 → SEASONING_SAUCE_OIL
        (2, 200125): "SEASONING_SAUCE_OIL",
        # SEASONING_SAUCE_OIL에서 제외 → NOODLE_FLOUR
        (2, 200077): "NOODLE_FLOUR",
        (2, 200082): "NOODLE_FLOUR",
    }

    # 제외 규칙 우선 체크
    key = (category_depth, category_id)
    if key in exclusion_rules:
        return exclusion_rules[key]

    # 포함 규칙 (서비스 카테고리별 포함 대상)
    inclusion_rules: Dict[str, List[Tuple[int, int]]] = {
        "FRUIT": [
            (0, 1),  # 과일 루트 전체
        ],
        "GRAIN": [
            (0, 2),
        ],
        "VEGETABLE": [
            (0, 3),
        ],
        "NUT_DRY_ETC": [
            (0, 4),
            (3, 300020),  # FRUIT에서 제외된 하위
            (3, 300021),  # FRUIT에서 제외된 하위
            (0, 14),
        ],
        "SEAFOOD": [
            (0, 5),
        ],
        "MEAT": [
            (0, 6),
            (2, 200068),
        ],
        "BEAN_EGG": [
            (2, 200063),
            (2, 200048),  # MEAT에서 제외된 하위
        ],
        "DAIRY": [
            (0, 9),
        ],
        "DRINK": [
            (0, 12),
            (0, 13),
        ],
        "NOODLE_FLOUR": [
            (0, 15),
            (2, 200077),  # SEASONING_SAUCE_OIL에서 제외된 하위
            (2, 200082),  # SEASONING_SAUCE_OIL에서 제외된 하위
        ],
        "KIMCHI_SIDE": [
            (0, 11),
        ],
        "SEASONING_SAUCE_OIL": [
            (0, 17),
            (2, 200125),  # NOODLE_FLOUR에서 제외된 하위
        ],
        "INSTANT_FOOD": [
            (0, 10),
            (0, 16),
        ],
    }

    # 포함 규칙 체크
    for service_cat, rules in inclusion_rules.items():
        if key in rules:
            return service_cat

    return None


def _map_service_category_for_category_node(
    lcate_nm: Optional[str],
    mcate_nm: Optional[str],
    scate_nm: Optional[str],
    rcate_nm: Optional[str],
    lcate_cd: Optional[int],
    mcate_cd: Optional[int],
    scate_cd: Optional[int],
) -> Optional[str]:
    """카테고리 트리 노드 전용 서비스 카테고리 매핑 헬퍼

    - Depth+ID 규칙(0/2/3 레벨)을 가능한 한 먼저 적용
    - 어떤 depth+id 조합에도 매핑되지 않으면, 이름 기반 `_map_service_category` 로 폴백
    """
    # 가장 구체적인 depth(S → M → L) 순서로 검사
    depth_id_pairs: List[Tuple[int, int]] = []
    if scate_cd:
        depth_id_pairs.append((3, scate_cd))
    if mcate_cd:
        depth_id_pairs.append((2, mcate_cd))
    if lcate_cd:
        depth_id_pairs.append((0, lcate_cd))

    for depth, cid in depth_id_pairs:
        code = _map_service_category_by_depth_id(depth, cid)
        if code:
            return code

    # Depth+ID 룰에 없으면 문자열 기반 규칙으로 매핑
    code, _ = _map_service_category(
        lcate_nm,
        mcate_nm,
        scate_nm,
        rcate_nm,
    )
    return code


def _map_service_category(
    lcate: Optional[str],
    mcate: Optional[str],
    scate: Optional[str],
    rcate: Optional[str],
    category_depth: Optional[int] = None,
    category_id: Optional[int] = None,
) -> Tuple[Optional[str], Optional[str]]:
    """홈플러스 카테고리 → SelF 표준 카테고리 매핑

    기준:
        - 1depth 표준 카테고리 13개(`docs/CATEGORY_STANDARD.md`) 로 귀결
        - 인식 가능한 식품 카테고리가 아니면 (None, None)을 반환해 완전히 제외
        - Depth+ID 기반 매핑을 우선 시도하고, 실패 시 문자열 기반 매핑 사용
        - `docs/CATEGORY_MAPPING_HOMEPLUS.md` 의 규칙 테이블을 가능한 한 그대로 반영
        - `정육/계란`, `두부/김치/반찬` 처럼 상위에 여러 개념이 섞인 경우에는
          l1+l2+l3 조합을 이용해 세부 매핑 (예: 냉장장류는 양념/장류, 계란/알류는 BEAN_EGG 등)
    """
    # Depth+ID 기반 매핑 우선 시도
    if category_depth is not None and category_id is not None:
        service_cat = _map_service_category_by_depth_id(category_depth, category_id)
        if service_cat:
            return service_cat, None

    root = (rcate or "").strip() if rcate else ""
    cat_l1 = (lcate or rcate or "").strip() if (lcate or rcate) else ""
    cat_l2 = (mcate or "").strip() if mcate else ""
    cat_l3 = (scate or "").strip() if scate else ""
    full_text = f"{cat_l1} {cat_l2} {cat_l3}"

    if not cat_l1 and not cat_l2 and not cat_l3:
        return None, None

    # -----------------------------
    # 루트 카테고리 기준 1차 필터링
    # -----------------------------
    # 홈플러스 전체 카테고리 중 "식품"이 아닌 루트(생활용품/가전/패션/문구/여행 등)는
    # SelF 식재료 13개 표준 카테고리 대상에서 제외한다.
    if root and "식품" not in root:
        return None, None

    # -----------------------------
    # 특정 L1+L2 조합 우선 매핑 (문서 상 예외 규칙)
    # -----------------------------

    # 두부/김치/반찬 하위의 냉장장류/장류는 장류 카테고리로 취급
    #   예: 두부/김치/반찬 -> 냉장장류 -> 냉장장류  (된장/고추장/쌈장 등)
    if cat_l1.startswith("두부/김치/반찬") and any(
        kw in f"{cat_l2} {cat_l3}" for kw in ("냉장장류", "장류")
    ):
        return "SEASONING_SAUCE_OIL", None

    # -----------------------------
    # 상위 카테고리 기준 기본 매핑
    # -----------------------------

    # 쌀/잡곡
    if cat_l1.startswith("쌀/잡곡"):
        return "GRAIN", None

    # 채소
    if cat_l1.startswith("채소"):
        return "VEGETABLE", None

    # 과일
    if cat_l1.startswith("과일"):
        return "FRUIT", None

    # 버섯/나물 (VEGETABLE로 통합)
    if cat_l1.startswith("버섯") or cat_l1.startswith("나물"):
        return "VEGETABLE", None

    # 정육/계란 (육류 + 계란이 섞여 있는 상위 카테고리)
    if cat_l1.startswith("정육/계란"):
        # 계란/알류 관련 중분류/소분류이면 BEAN_EGG
        egg_keywords = ("계란", "알류", "알", "유정란", "메추리알", "가공란")
        l2l3 = f"{cat_l2} {cat_l3}"
        if any(kw in l2l3 for kw in egg_keywords):
            return "BEAN_EGG", None
        # 그 외 한우/돼지고기/닭/오리/수입육/양념육/가공육 등은 MEAT
        return "MEAT", None

    # 수산물/건어물/해산물
    if cat_l1.startswith("수산") or cat_l1.startswith("건어물") or cat_l1.startswith("해산"):
        return "SEAFOOD", None

    # 우유/유제품
    if cat_l1.startswith("우유") or cat_l1.startswith("유제품"):
        return "DAIRY", None

    # 김치/반찬
    if cat_l1.startswith("김치") or cat_l1.startswith("반찬"):
        return "KIMCHI_SIDE", None

    # 양념/오일/소스/장류
    if "양념" in cat_l1 or "오일" in cat_l1 or "소스" in cat_l1 or "장류" in cat_l1:
        return "SEASONING_SAUCE_OIL", None

    # -----------------------------
    # 키워드 기반 보조 매핑 (상위명이 모호한 경우)
    # -----------------------------
    # 곡물 계열 (쌀/잡곡 등, 비쌀/잡곡 L1 에서 등장하는 경우)
    if any(kw in full_text for kw in ("쌀", "현미", "잡곡", "귀리", "수수", "조", "깨", "보리", "혼합곡", "수입잡곡")):
        return "GRAIN", None

    # 채소 계열
    if any(kw in full_text for kw in ("채소", "야채", "샐러드")):
        return "VEGETABLE", None

    # 과일 계열
    if any(kw in full_text for kw in ("과일", "사과", "배", "감귤", "만감", "딸기", "베리", "바나나", "포도", "오렌지", "자몽", "레몬", "키위", "망고")):
        return "FRUIT", None

    # 버섯/나물 계열 (VEGETABLE로 통합)
    if any(kw in full_text for kw in ("버섯", "표고", "새송이", "팽이", "느타리", "나물", "시금치", "고사리", "고구마순")):
        return "VEGETABLE", None

    # 수산물/해산물/건어물 계열
    # 주의: "김치" 와의 충돌을 피하기 위해 SEAFOOD 키워드에서는 단일 "김" 은 사용하지 않는다.
    if any(
        kw in full_text
        for kw in (
            "생선",
            "연어",
            "고등어",
            "갈치",
            "참치",
            "새우",
            "오징어",
            "문어",
            "낙지",
            "게",
            "조개",
            "미역",
            "다시마",
            "해조",
        )
    ):
        return "SEAFOOD", None

    # 유제품 계열
    if any(kw in full_text for kw in ("우유", "요거트", "치즈", "버터", "크림")):
        return "DAIRY", None

    # 김치/반찬/절임 계열
    if any(kw in full_text for kw in ("김치", "장아찌", "피클", "절임", "젓갈")):
        return "KIMCHI_SIDE", None

    # 양념/조미/소스/오일/장류 계열
    if any(
        kw in full_text
        for kw in (
            "소금",
            "설탕",
            "식초",
            "후추",
            "향신료",
            "소스",
            "드레싱",
            "케첩",
            "마요네즈",
            "식용유",
            "올리브유",
            "버터오일",
            "장류",
        )
    ):
        return "SEASONING_SAUCE_OIL", None

    # 면/가루/베이킹 (라면, 국수, 파스타 등)
    if any(kw in full_text for kw in ("면", "라면", "국수", "우동", "소면", "파스타", "스파게티")):
        return "NOODLE_FLOUR", None
    if any(kw in full_text for kw in ("밀가루", "가루", "믹스", "베이킹", "핫케익믹스", "케익믹스")):
        return "NOODLE_FLOUR", None

    # 견과/건과/씨앗 등 기타 식재료
    if any(kw in full_text for kw in ("견과", "견과류", "건과", "건과일", "씨앗", "해바라기씨", "아몬드", "호두")):
        return "NUT_DRY_ETC", None

    # 음료
    if any(kw in full_text for kw in ("음료", "생수", "탄산", "주스", "커피", "차", "음료수")):
        return "DRINK", None

    # 라면/간편식품/통조림
    if any(kw in full_text for kw in ("라면", "컵라면", "간편식", "통조림", "즉석", "레토르트", "파우치")):
        return "INSTANT_FOOD", None

    # 두부/콩/계란 관련 키워드 (정육/계란 이외에서 발견되는 경우)
    if any(kw in full_text for kw in ("두부", "콩나물", "콩", "계란", "알류", "유정란", "메추리알")):
        return "BEAN_EGG", None

    # 육류 관련 키워드 (정육/축산 등)
    if any(
        kw in full_text
        for kw in (
            "정육",
            "축산",
            "소고기",
            "쇠고기",
            "한우",
            "수입육",
            "돼지고기",
            "삼겹살",
            "목살",
            "갈비",
            "등심",
            "닭고기",
            "닭다리",
            "닭가슴살",
            "닭볶음탕",
            "오리고기",
            "양고기",
        )
    ):
        return "MEAT", None

    # 인식 불가 카테고리는 None 처리 (비식품 등)
    return None, None


def _service_category_display_name(code: Optional[str]) -> Optional[str]:
    """서비스 표준 카테고리 코드 → 표시용 한글 이름 매핑

    `docs/CATEGORY_STANDARD.md` 의 정의를 따른다.
    """
    if not code:
        return None
    mapping = {
        "GRAIN": "쌀/잡곡",
        "NOODLE_FLOUR": "면/가루/베이커리/제빵",
        "VEGETABLE": "채소/샐러드/버섯/나물",
        "FRUIT": "과일",
        "BEAN_EGG": "두부/콩/계란",
        "MEAT": "육류",
        "SEAFOOD": "수산물/해산물/건어물",
        "DAIRY": "우유/유제품",
        "KIMCHI_SIDE": "김치/반찬/절임",
        "SEASONING_SAUCE_OIL": "양념/조미/소스/오일",
        "NUT_DRY_ETC": "견과/건과/간식",
        "DRINK": "음료",
        "INSTANT_FOOD": "라면/간편식품/통조림",
    }
    return mapping.get(code)


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
    # categoryDepth와 categoryId 계산
    category_depth = None
    category_id = None
    if scate_nm and item.get("scateCd"):
        category_depth = 3
        category_id = _to_int(item.get("scateCd"))
    elif mcate_nm and item.get("mcateCd"):
        category_depth = 2
        category_id = _to_int(item.get("mcateCd"))
    elif lcate_nm and item.get("lcateCd"):
        category_depth = 0
        category_id = _to_int(item.get("lcateCd"))

    service_category, service_subcategory = _map_service_category(
        lcate_nm,
        mcate_nm,
        scate_nm,
        rcate_nm,
        category_depth=category_depth,
        category_id=category_id,
    )

    processing_level = _detect_processing_level(str(item.get("itemNm", "")), scate_nm)

    fallback_text = _strip_tags(item.get("itemDtlDscr"))
    short_description = summary_text or item.get("recomMsg") or item.get("itemAttrTop")
    # 본문 이미지 리스트 (리스트 그대로)
    full_image_description = desc_image_urls if desc_image_urls else None

    # category_name 은 서비스 표준 카테고리 이름을 우선 사용
    display_category_name = _service_category_display_name(service_category)
    if not display_category_name:
        display_category_name = lcate_nm or rcate_nm or mcate_nm or scate_nm

    return ProductData(
        name=str(item.get("itemNm", "")).strip(),
        price=price,
        source_site="homeplus",
        source_url=_build_source_url(item_no, store),
        crawled_at=datetime.now(timezone.utc).isoformat(),
        category_name=display_category_name,
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
