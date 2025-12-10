"""
크롤러 실행 진입점

환경설정을 로드하고, 추후 크롤링 파이프라인을 실행할 예정이다.
"""

import logging

from crawler.config import AppConfig
from crawler.homeplus.service import HomeplusService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("crawler")


def main() -> None:
    """크롤러 실행 메인 함수"""
    config = AppConfig.load()
    logger.info("크롤 타깃: %s", config.crawl.target)
    logger.info(
        "스토어 설정: id=%s type=%s kind=%s ship=%s",
        config.store.store_id,
        config.store.store_type,
        config.store.store_kind,
        config.store.item_ship_method,
    )
    logger.info("동시 실행 수: %s, 요청 지연(ms): %s", config.crawl.concurrency, config.crawl.delay_ms)
    if config.alert.slack_webhook_url or config.alert.slack_bot_token:
        logger.info("Slack 알림이 활성화됩니다.")
    if config.alert.alert_email:
        logger.info("이메일 알림 수신자: %s", config.alert.alert_email)
    if config.s3.bucket:
        logger.info("S3 업로드 대상 버킷: %s, 프리픽스: %s", config.s3.bucket, config.s3.prefix)
    logger.info("크롤러 초기화가 완료되었습니다.")

    service = HomeplusService(config=config)
    # 실제 크롤 호출은 네트워크 환경에서 실행해야 하므로 여기서는 초기화만 수행
    # 필요한 경우 service.run() 호출로 배치 수집 가능


if __name__ == "__main__":
    main()
