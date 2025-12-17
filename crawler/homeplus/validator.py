"""
홈플러스 크롤링 결과 검증 유틸

`backend.data_pipeline.schemas.CrawlBatch` 구조의 JSON을 입력으로 받아
필수 필드/카테고리/이미지 URL 등의 기본 품질을 검증한다.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
import os
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse

from backend.data_pipeline.schemas import CrawlBatch, ProductData
from crawler.homeplus.mappers import _service_category_display_name


@dataclass
class ValidationIssue:
    """검증 결과 이슈 단위"""

    level: str  # "error" 또는 "warn"
    code: str
    message: str
    product_index: Optional[int] = None
    source_url: Optional[str] = None


def _is_http_url(value: Optional[str]) -> bool:
    """HTTP/HTTPS URL 형식인지 간단히 검사"""
    if not value:
        return False
    parsed = urlparse(value)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def _known_service_categories() -> List[str]:
    """알려진 서비스 카테고리 코드 목록"""
    # `_service_category_display_name` 이 관리하는 코드 목록을 그대로 사용
    codes: List[str] = []
    for code in (
        "GRAIN",
        "NOODLE_FLOUR",
        "VEGETABLE",
        "FRUIT",
        "BEAN_EGG",
        "MEAT",
        "SEAFOOD",
        "DAIRY",
        "KIMCHI_SIDE",
        "SEASONING_SAUCE_OIL",
        "NUT_DRY_ETC",
        "DRINK",
        "INSTANT_FOOD",
    ):
        if _service_category_display_name(code) is not None:
            codes.append(code)
    return codes


_SERVICE_CATEGORY_CODES = set(_known_service_categories())


def _is_price_tracking_mode() -> bool:
    """가격 추적 전용 검증 모드 여부를 판별

    PRICE_TRACKING_MODE=true 인 경우에만 활성화된다.
    이 모드에서는 가격 추적에 필요한 최소 필드만 에러로 취급하고,
    나머지 필드는 경고 수준으로 완화한다.
    """
    return os.getenv("PRICE_TRACKING_MODE", "false").lower() in ("1", "true", "yes")


def validate_product(index: int, product: ProductData) -> List[ValidationIssue]:
    """단일 상품 수준 검증"""
    issues: List[ValidationIssue] = []
    price_mode = _is_price_tracking_mode()

    # 필수 필드 존재 여부
    if not product.name:
        # 가격 추적 모드에서도 name 은 기본 식별을 위해 유지
        issues.append(
            ValidationIssue(
                level="error",
                code="MISSING_NAME",
                message="상품명(name)이 비어 있습니다.",
                product_index=index,
                source_url=product.source_url,
            )
        )
    if product.price is None or product.price <= 0:
        issues.append(
            ValidationIssue(
                level="error",
                code="INVALID_PRICE",
                message="가격(price)이 0 이하이거나 누락되었습니다.",
                product_index=index,
                source_url=product.source_url,
            )
        )
    if not product.source_url:
        issues.append(
            ValidationIssue(
                level="error",
                code="MISSING_SOURCE_URL",
                message="source_url 이 비어 있습니다.",
                product_index=index,
                source_url=None,
            )
        )
    elif not _is_http_url(product.source_url):
        issues.append(
            ValidationIssue(
                level="error",
                code="INVALID_SOURCE_URL",
                message="source_url 형식이 잘못되었습니다.",
                product_index=index,
                source_url=product.source_url,
            )
        )

    # 서비스 카테고리 코드/표시명 일관성
    if not product.service_category:
        # 가격 추적 모드에서는 서비스 카테고리 누락을 경고로 완화
        level = "warn" if price_mode else "error"
        issues.append(
            ValidationIssue(
                level=level,
                code="MISSING_SERVICE_CATEGORY",
                message="service_category 가 비어 있습니다.",
                product_index=index,
                source_url=product.source_url,
            )
        )
    else:
        if product.service_category not in _SERVICE_CATEGORY_CODES:
            level = "warn" if price_mode else "error"
            issues.append(
                ValidationIssue(
                    level=level,
                    code="UNKNOWN_SERVICE_CATEGORY",
                    message=f"알 수 없는 service_category 코드입니다: {product.service_category}",
                    product_index=index,
                    source_url=product.source_url,
                )
            )
        expected_name = _service_category_display_name(product.service_category)
        if expected_name and product.category_name != expected_name:
            issues.append(
                ValidationIssue(
                    level="warn",
                    code="CATEGORY_NAME_MISMATCH",
                    message=(
                        f"category_name 이 서비스 카테고리 표시명과 일치하지 않습니다. "
                        f"expected={expected_name} actual={product.category_name}"
                    ),
                    product_index=index,
                    source_url=product.source_url,
                )
            )

    # 대표 이미지 검증
    if not product.images:
        # 가격 추적 모드에서는 이미지 누락을 경고로만 처리 (가격 추적에는 필수 아님)
        level = "warn" if price_mode else "error"
        issues.append(
            ValidationIssue(
                level=level,
                code="MISSING_IMAGES",
                message="대표 이미지(images)가 비어 있습니다.",
                product_index=index,
                source_url=product.source_url,
            )
        )
    else:
        for img in product.images:
            if not _is_http_url(img.image_url):
                level = "warn" if price_mode else "error"
                issues.append(
                    ValidationIssue(
                        level=level,
                        code="INVALID_IMAGE_URL",
                        message="대표 이미지 URL 형식이 잘못되었습니다.",
                        product_index=index,
                        source_url=product.source_url,
                    )
                )
                break

    # 상세 이미지 검증
    if product.full_image_description:
        for url in product.full_image_description:
            level = "warn" if price_mode else "error"
            if not _is_http_url(url):
                issues.append(
                    ValidationIssue(
                        level=level,
                        code="INVALID_FULL_IMAGE_URL",
                        message="full_image_description 내 URL 형식이 잘못되었습니다.",
                        product_index=index,
                        source_url=product.source_url,
                    )
                )
                break

    return issues


def validate_batch(batch: CrawlBatch) -> List[ValidationIssue]:
    """배치 단위 검증"""
    issues: List[ValidationIssue] = []

    # 기본 메타 검증
    if not batch.batch_id:
        issues.append(
            ValidationIssue(
                level="error",
                code="MISSING_BATCH_ID",
                message="batch_id 가 비어 있습니다.",
            )
        )
    if batch.total_count != len(batch.products):
        issues.append(
            ValidationIssue(
                level="warn",
                code="TOTAL_COUNT_MISMATCH",
                message=(
                    f"total_count({batch.total_count}) 와 products 길이({len(batch.products)})가 일치하지 않습니다."
                ),
            )
        )

    # 상품 단위 검증
    for idx, product in enumerate(batch.products):
        issues.extend(validate_product(idx, product))

    return issues


def _iter_homeplus_batches_in_dir(root: Path) -> List[Path]:
    """지정한 디렉터리에서 홈플러스 배치 JSON 리스트를 찾는다"""
    if not root.exists():
        return []
    return sorted(root.glob("homeplus_*.json"))


def _find_latest_homeplus_batch() -> Optional[Path]:
    """가장 최근 홈플러스 배치 JSON 파일을 찾는다 (processed 기준)"""
    candidates = _iter_homeplus_batches_in_dir(Path("data/json/processed"))
    if not candidates:
        return None
    return candidates[-1]


def main(argv: Optional[List[str]] = None) -> int:
    """CLI 진입점

    사용 예:
        python -m crawler.homeplus.validator              # 최신 processed/homeplus_*.json 1개 검증
        python -m crawler.homeplus.validator path/to.json # 특정 파일 1개 검증
        python -m crawler.homeplus.validator path/to/dir  # 디렉터리 내 homeplus_*.json 전체 검증
        python -m crawler.homeplus.validator --all        # processed/backup 전체 homeplus_*.json 검증
    """
    args = list(argv) if argv is not None else sys.argv[1:]

    # --all 옵션: processed / backup 전체 검증
    if args and args[0] in ("--all", "-a"):
        roots = [Path("data/json/processed"), Path("data/json/backup")]
        files: List[Path] = []
        for root in roots:
            files.extend(_iter_homeplus_batches_in_dir(root))
        if not files:
            print("[VALIDATION] processed/backup 에서 homeplus_*.json 파일을 찾을 수 없습니다.", file=sys.stderr)
            return 1

        total_errors = 0
        total_warns = 0
        for path in files:
            data = path.read_text(encoding="utf-8")
            batch = CrawlBatch.from_json(data)
            issues = validate_batch(batch)
            error_count = sum(1 for i in issues if i.level == "error")
            warn_count = sum(1 for i in issues if i.level == "warn")
            total_errors += error_count
            total_warns += warn_count

            print(f"[VALIDATION] file={path} errors={error_count} warns={warn_count}")
        print(f"[VALIDATION] summary: files={len(files)} errors={total_errors} warns={total_warns}")
        return 0 if total_errors == 0 else 2

    # 단일 인자: 파일 또는 디렉터리
    if args:
        target = Path(args[0])
        if target.is_dir():
            files = _iter_homeplus_batches_in_dir(target)
            if not files:
                print(f"[VALIDATION] 디렉터리에서 homeplus_*.json 파일을 찾을 수 없습니다: {target}", file=sys.stderr)
                return 1
        else:
            files = [target]
    else:
        latest = _find_latest_homeplus_batch()
        if not latest:
            print("[VALIDATION] 최신 homeplus 배치 JSON 파일을 찾을 수 없습니다.", file=sys.stderr)
            return 1
        files = [latest]

    total_errors = 0
    total_warns = 0
    for path in files:
        if not path.is_file():
            print(f"[VALIDATION] homeplus 배치 JSON 파일을 찾을 수 없습니다: {path}", file=sys.stderr)
            continue
        data = path.read_text(encoding="utf-8")
        batch = CrawlBatch.from_json(data)
        issues = validate_batch(batch)

        error_count = sum(1 for i in issues if i.level == "error")
        warn_count = sum(1 for i in issues if i.level == "warn")
        total_errors += error_count
        total_warns += warn_count

        print(f"[VALIDATION] file={path} errors={error_count} warns={warn_count}")
        for issue in issues:
            loc = f" idx={issue.product_index}" if issue.product_index is not None else ""
            url = f" url={issue.source_url}" if issue.source_url else ""
            print(f"[{issue.level.upper()}] code={issue.code}{loc}{url} - {issue.message}")

    if len(files) > 1:
        print(f"[VALIDATION] summary: files={len(files)} errors={total_errors} warns={total_warns}")

    # 에러가 있으면 비정상 종료 코드
    return 0 if total_errors == 0 else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())


