"""
결제 게이트웨이 서비스 모듈

토스페이먼츠 PG 연동을 위한 서비스 레이어.
- pg_base: 추상 인터페이스
- pg_demo: 데모 모드 (시뮬레이션)
- pg_tosspayments: 토스페이먼츠 실제 연동
- pg_factory: 팩토리 패턴으로 PG 선택
"""

from .pg_base import (
    PaymentGateway,
    PaymentPrepareResult,
    PaymentConfirmResult,
    PaymentCancelResult,
)
from .pg_factory import get_payment_gateway

__all__ = [
    "PaymentGateway",
    "PaymentPrepareResult",
    "PaymentConfirmResult",
    "PaymentCancelResult",
    "get_payment_gateway",
]
