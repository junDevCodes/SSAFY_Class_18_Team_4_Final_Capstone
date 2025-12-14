"""
크롤러 환경설정 로더

환경변수 값을 읽어 크롤 설정, 스토어/배송, 알림, S3 업로드 설정을 구성한다.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv  # type: ignore
except ImportError:  # pragma: no cover
    load_dotenv = None


_ENV_LOADED = False


def _load_env() -> None:
    """환경 변수 파일(.env/backed/.env) 로드"""
    global _ENV_LOADED
    if _ENV_LOADED or load_dotenv is None:
        return
    for cand in (Path(".env"), Path("backend/.env")):
        if cand.exists():
            load_dotenv(dotenv_path=cand)
            _ENV_LOADED = True
            break


def _get_int_env(key: str, default: int) -> int:
    """정수형 환경변수를 안전하게 파싱한다."""
    raw = os.getenv(key)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass
class CrawlConfig:
    """크롤 타깃 및 실행 파라미터 설정"""

    target: str = "homeplus"
    concurrency: int = 1
    delay_ms: int = 500
    # 크롤링 모드: full(전체 카탈로그), price_refresh(가격/상태만 갱신) 등으로 확장 예정
    mode: str = "full"
    # 서비스 표준 카테고리 필터 (예: "GRAIN,VEGETABLE"), 없으면 전체 식품 카테고리 대상
    service_category_filter: Optional[str] = None
    scope: str = "full"
    fetch_detail: bool = True
    s3_upload_enabled: bool = False
    store_html: bool = False
    sample_per_category: Optional[int] = None
    price_refresh_mode: Optional[str] = None  # "sample" or "full"
    price_sample_input: Optional[Path] = None  # 샘플 대상 파일 경로

    @classmethod
    def from_env(cls) -> "CrawlConfig":
        """환경변수에서 설정을 로드한다."""
        mode = os.getenv("CRAWL_MODE", "full")
        sample_per_cat = os.getenv("CRAWL_SAMPLE_PER_CATEGORY")
        service_cat_filter = os.getenv("CRAWL_SERVICE_CATEGORY_FILTER")
        s3_env = os.getenv("S3_UPLOAD_ENABLED")
        # 가격 추적 모드에서는 S3 업로드를 비활성화하고, 그 외 모드에서는 기본적으로 활성화
        if mode == "price_refresh":
            s3_upload = False
        else:
            s3_upload = s3_env.lower() in ("1", "true", "yes") if s3_env else True
        return cls(
            target=os.getenv("CRAWL_TARGET", "homeplus"),
            concurrency=_get_int_env("CRAWL_CONCURRENCY", 1),
            delay_ms=_get_int_env("CRAWL_DELAY_MS", 500),
            mode=mode,
            scope=os.getenv("CRAWL_SCOPE", "full"),
            fetch_detail=os.getenv("FETCH_DETAIL", "true").lower() in ("1", "true", "yes"),
            s3_upload_enabled=s3_upload,
            store_html=os.getenv("CRAWL_STORE_HTML", "false").lower() in ("1", "true", "yes"),
            sample_per_category=_get_int_env("CRAWL_SAMPLE_PER_CATEGORY", 0) if sample_per_cat else None,
            service_category_filter=service_cat_filter,
            price_refresh_mode=os.getenv("PRICE_REFRESH_MODE"),
            price_sample_input=Path(os.getenv("PRICE_SAMPLE_INPUT")) if os.getenv("PRICE_SAMPLE_INPUT") else None,
        )


@dataclass
class StoreConfig:
    """홈플러스 스토어/배송 설정"""

    store_id: int = 37
    store_type: str = "HYPER"
    store_kind: str = "NOR"
    item_ship_method: str = "TD_DRCT"

    @classmethod
    def from_env(cls) -> "StoreConfig":
        """환경변수에서 설정을 로드한다."""
        return cls(
            store_id=_get_int_env("STORE_ID", 37),
            store_type=os.getenv("STORE_TYPE", "HYPER"),
            store_kind=os.getenv("STORE_KIND", "NOR"),
            item_ship_method=os.getenv("ITEM_SHIP_METHOD", "TD_DRCT"),
        )


@dataclass
class AlertConfig:
    """알림 설정"""

    slack_webhook_url: Optional[str] = None
    slack_bot_token: Optional[str] = None
    alert_email: Optional[str] = None

    @classmethod
    def from_env(cls) -> "AlertConfig":
        """환경변수에서 설정을 로드한다."""
        return cls(
            slack_webhook_url=os.getenv("SLACK_WEBHOOK_URL"),
            slack_bot_token=os.getenv("SLACK_BOT_TOKEN"),
            alert_email=os.getenv("ALERT_EMAIL"),
        )


@dataclass
class S3Config:
    """S3 업로드 설정"""

    bucket: Optional[str] = None
    prefix: str = "homeplus/raw/{YYYY}/{MM}/{batch_id}/"
    thumbnail_prefix: str = "homeplus/thumbnail/{YYYY}/{MM}/{batch_id}/"
    product_detail_prefix: str = "homeplus/product_detail/{YYYY}/{MM}/{batch_id}/"
    region: Optional[str] = None
    presign_expires: int = 3600

    @classmethod
    def from_env(cls) -> "S3Config":
        """환경변수에서 설정을 로드한다."""
        return cls(
            bucket=os.getenv("S3_BUCKET"),
            prefix=os.getenv("S3_PREFIX", "homeplus/raw/{YYYY}/{MM}/{batch_id}/"),
            thumbnail_prefix=os.getenv("S3_THUMBNAIL_PREFIX", "homeplus/thumbnail/{YYYY}/{MM}/{batch_id}/"),
            product_detail_prefix=os.getenv("S3_PRODUCT_DETAIL_PREFIX", "homeplus/product_detail/{YYYY}/{MM}/{batch_id}/"),
            region=os.getenv("S3_REGION"),
            presign_expires=_get_int_env("S3_PRESIGN_EXPIRES", 3600),
        )


@dataclass
class AppConfig:
    """크롤러 전체 설정 집합"""

    crawl: CrawlConfig
    store: StoreConfig
    alert: AlertConfig
    s3: S3Config

    @classmethod
    def load(cls) -> "AppConfig":
        """환경변수에서 모든 설정을 로드한다."""
        _load_env()
        return cls(
            crawl=CrawlConfig.from_env(),
            store=StoreConfig.from_env(),
            alert=AlertConfig.from_env(),
            s3=S3Config.from_env(),
        )
