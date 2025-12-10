"""
크롤러 환경설정 로더

환경변수 값을 읽어 크롤 설정, 스토어/배송, 알림, S3 업로드 설정을 구성한다.
"""

import os
from dataclasses import dataclass
from typing import Optional


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
    scope: str = "full"
    fetch_detail: bool = True
    s3_upload_enabled: bool = False

    @classmethod
    def from_env(cls) -> "CrawlConfig":
        """환경변수에서 설정을 로드한다."""
        return cls(
            target=os.getenv("CRAWL_TARGET", "homeplus"),
            concurrency=_get_int_env("CRAWL_CONCURRENCY", 1),
            delay_ms=_get_int_env("CRAWL_DELAY_MS", 500),
            scope=os.getenv("CRAWL_SCOPE", "full"),
            fetch_detail=os.getenv("FETCH_DETAIL", "true").lower() in ("1", "true", "yes"),
            s3_upload_enabled=os.getenv("S3_UPLOAD_ENABLED", "false").lower() in ("1", "true", "yes"),
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
    region: Optional[str] = None
    presign_expires: int = 3600

    @classmethod
    def from_env(cls) -> "S3Config":
        """환경변수에서 설정을 로드한다."""
        return cls(
            bucket=os.getenv("S3_BUCKET"),
            prefix=os.getenv("S3_PREFIX", "homeplus/raw/{YYYY}/{MM}/{batch_id}/"),
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
        return cls(
            crawl=CrawlConfig.from_env(),
            store=StoreConfig.from_env(),
            alert=AlertConfig.from_env(),
            s3=S3Config.from_env(),
        )
