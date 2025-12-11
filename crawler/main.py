"""
크롤러 실행 진입점

환경 설정을 로드하고, 홈플러스 크롤 배치를 실행한다.
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
    service.run()


if __name__ == "__main__":
    main()
