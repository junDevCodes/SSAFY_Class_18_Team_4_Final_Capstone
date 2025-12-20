"""
크롤러 실행 진입점

환경 설정을 로드하고, 홈플러스 크롤 배치를 실행한다.
필요한 경우 배치가 끝난 직후 간단한 검증(validation)도 함께 수행한다.
"""

import logging
import os
import sys
import django
from pathlib import Path

# Django 설정 초기화 (DB 접근이 필요한 경우)
# PYTHONPATH에 backend 디렉토리가 포함되어 있어야 함
backend_path = Path(__file__).parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

# 작업 디렉토리를 backend로 변경 (Django 앱 인식을 위해)
original_cwd = os.getcwd()
try:
    os.chdir(str(backend_path))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project_self.settings')
    # 인코딩 문제 방지를 위해 환경 변수 설정
    import locale
    if sys.platform == 'win32':
        # Windows에서 UTF-8 강제 설정
        os.environ['PYTHONIOENCODING'] = 'utf-8'
    django.setup()
finally:
    os.chdir(original_cwd)

from backend.data_pipeline.schemas import CrawlBatch
from crawler.config import AppConfig
from crawler.homeplus.service import HomeplusService
from crawler.homeplus.validator import validate_batch

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("crawler")


def main() -> None:
    """크롤러 실행 메인 함수"""
    config = AppConfig.load()
    logger.info("크롤 타깃 %s", config.crawl.target)
    logger.info(
        "스토어 설정: id=%s type=%s kind=%s ship=%s",
        config.store.store_id,
        config.store.store_type,
        config.store.store_kind,
        config.store.item_ship_method,
    )
    logger.info("동시 실행 수: %s, 요청 지연(ms): %s", config.crawl.concurrency, config.crawl.delay_ms)
    if config.alert.slack_webhook_url or config.alert.slack_bot_token:
        logger.info("Slack 알림이 활성화되었습니다.")
    if config.alert.alert_email:
        logger.info("이메일 알림 수신자: %s", config.alert.alert_email)
    if config.s3.bucket:
        logger.info("S3 업로드 대상 버킷: %s, 프리픽스: %s", config.s3.bucket, config.s3.prefix)
    logger.info("크롤러가 초기화되었습니다.")

    service = HomeplusService(config=config)
    # 배치 실행
    batch_path = service.run()

    # 배치 실행 직후 기본 검증 수행 (옵션)
    # CRAWL_RUN_VALIDATION=true 일 때만 동작하며, 현재는 homeplus 전용으로 사용한다.
    run_validation = os.getenv("CRAWL_RUN_VALIDATION", "false").lower() in ("1", "true", "yes")
    if run_validation and config.crawl.target == "homeplus":
        try:
            raw = batch_path.read_text(encoding="utf-8")
            batch = CrawlBatch.from_json(raw)
            issues = validate_batch(batch)
            error_count = sum(1 for i in issues if i.level == "error")
            warn_count = sum(1 for i in issues if i.level == "warn")
            logger.info("홈플러스 배치 검증 결과: errors=%s warns=%s file=%s", error_count, warn_count, batch_path.name)
        except Exception as exc:  # pragma: no cover
            # 검증 자체가 실패해도 크롤링 결과는 남기고, 로그만 남긴다.
            logger.error("홈플러스 배치 검증 중 예외 발생: %s", exc)


if __name__ == "__main__":
    main()
