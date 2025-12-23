"""
로깅 설정 모듈

structlog를 사용한 구조화된 로깅 설정
"""

import logging
import sys
from typing import Any, Dict

try:
    import structlog
except ModuleNotFoundError:  # pragma: no cover
    structlog = None

from core.config import settings


def setup_logging() -> None:
    """로깅 설정 초기화"""

    # 로그 레벨 설정
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # 표준 라이브러리 로거 설정
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    # 외부 라이브러리 로그 레벨 조정
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("asyncpg").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    # 테스트/로컬 환경에서 structlog 의존성이 없으면 표준 logging만 사용
    if structlog is None:
        return

    # structlog 프로세서 설정
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_logger_name,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if settings.debug:
        # 개발 환경: 컬러풀한 콘솔 출력
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True)
        ]
    else:
        # 운영 환경: JSON 형식 출력
        processors = shared_processors + [
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(ensure_ascii=False),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = __name__) -> Any:
    """로거 인스턴스 반환

    Args:
        name: 로거 이름 (일반적으로 __name__ 사용)

    Returns:
        structlog BoundLogger 또는 표준 logging.Logger 인스턴스
    """
    if structlog is None:
        return logging.getLogger(name)
    return structlog.get_logger(name)


class LogContext:
    """로그 컨텍스트 관리 유틸리티

    요청 처리 중 로그에 추가 정보를 바인딩하는 데 사용
    """

    @staticmethod
    def bind(**kwargs: Any) -> None:
        """현재 컨텍스트에 로그 변수 바인딩

        Args:
            **kwargs: 바인딩할 키-값 쌍
        """
        if structlog is None:
            return
        structlog.contextvars.bind_contextvars(**kwargs)

    @staticmethod
    def unbind(*keys: str) -> None:
        """현재 컨텍스트에서 로그 변수 제거

        Args:
            *keys: 제거할 키들
        """
        if structlog is None:
            return
        structlog.contextvars.unbind_contextvars(*keys)

    @staticmethod
    def clear() -> None:
        """현재 컨텍스트의 모든 로그 변수 제거"""
        if structlog is None:
            return
        structlog.contextvars.clear_contextvars()

    @staticmethod
    def bind_request(
        request_id: str,
        user_id: int | None = None,
        page_type: str | None = None,
    ) -> None:
        """요청 정보 바인딩

        Args:
            request_id: 요청 ID
            user_id: 사용자 ID (선택적)
            page_type: 페이지 타입 (선택적)
        """
        if structlog is None:
            return
        context: Dict[str, Any] = {"request_id": request_id}
        if user_id is not None:
            context["user_id"] = user_id
        if page_type is not None:
            context["page_type"] = page_type
        structlog.contextvars.bind_contextvars(**context)


# 기본 로거 인스턴스
logger = get_logger("pred")
