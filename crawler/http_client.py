"""
HTTP 클라이언트 유틸

httpx를 사용해 재시도·백오프 로직을 포함한 GET 요청 헬퍼를 제공한다.
"""

import logging
import time
from typing import Any, Dict, Optional

import httpx


logger = logging.getLogger(__name__)


class HttpClient:
    """재시도 가능한 간단한 HTTP 클라이언트"""

    def __init__(
        self,
        timeout: float = 15.0,
        max_retries: int = 3,
        backoff_seconds: Optional[list[int]] = None,
        user_agent: str = "SelF-Crawler/1.0",
    ):
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds or [1, 5, 15]
        self.user_agent = user_agent
        self._client = httpx.Client(timeout=self.timeout)

    def get_json(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """GET 요청을 보내고 JSON 응답을 반환한다."""
        merged_headers = {"User-Agent": self.user_agent}
        if headers:
            merged_headers.update(headers)

        last_error: Optional[Exception] = None

        for attempt in range(self.max_retries):
            try:
                start = time.perf_counter()
                response = self._client.get(url, params=params, headers=merged_headers)
                elapsed_ms = (time.perf_counter() - start) * 1000
                if 500 <= response.status_code < 600:
                    # 서버 오류는 재시도 대상
                    raise httpx.HTTPStatusError(
                        f"server error: {response.status_code}", request=response.request, response=response
                    )
                response.raise_for_status()
                logger.info("요청 완료: url=%s status=%s 시간_ms=%.1f", url, response.status_code, elapsed_ms)
                return response.json()
            except (httpx.RequestError, httpx.HTTPStatusError) as exc:
                last_error = exc
                if attempt < self.max_retries - 1:
                    delay = self.backoff_seconds[min(attempt, len(self.backoff_seconds) - 1)]
                    logger.warning("요청 재시도: url=%s 시도=%s 오류=%s", url, attempt + 1, exc)
                    time.sleep(delay)
                    continue
                break

        if last_error:
            raise last_error
        raise RuntimeError("요청 실패 원인을 확인할 수 없습니다.")
