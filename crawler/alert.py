"""
알림 유틸

Slack 웹훅/봇 토큰 기반 알림을 전송한다.
"""

from typing import Optional

import httpx

from crawler.config import AlertConfig


class AlertClient:
    """Slack 알림 클라이언트"""

    def __init__(self, config: AlertConfig):
        self.config = config

    def send_slack(self, message: str) -> None:
        """Slack 웹훅 또는 봇 토큰으로 메시지 전송"""
        if not self.config.slack_webhook_url and not self.config.slack_bot_token:
            return
        try:
            if self.config.slack_webhook_url:
                httpx.post(self.config.slack_webhook_url, json={"text": message}, timeout=5.0)
                return
            if self.config.slack_bot_token:
                # 기본 채널이 별도 주어지지 않았으므로 봇 토큰만 있을 때는 스킵
                return
        except Exception:
            # 알림 실패는 크롤 실패를 막지 않도록 무시
            return

    def notify(self, message: str) -> None:
        """알림 전송"""
        self.send_slack(message)
