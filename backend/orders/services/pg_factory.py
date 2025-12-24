"""
PG 팩토리

환경 설정에 따라 적절한 결제 게이트웨이를 반환합니다.
- PAYMENT_MODE=demo: DemoPaymentGateway
- PAYMENT_MODE=production: TossPaymentGateway
"""

from django.conf import settings

from .pg_base import PaymentGateway
from .pg_demo import DemoPaymentGateway
from .pg_tosspayments import TossPaymentGateway


def get_payment_gateway() -> PaymentGateway:
    """설정에 따라 적절한 PG를 반환

    환경 변수 PAYMENT_MODE에 따라 PG를 선택합니다.
    - 'production': 토스페이먼츠 실제 연동
    - 그 외 (기본값): 데모 모드

    Returns:
        PaymentGateway: 결제 게이트웨이 인스턴스
    """
    mode = getattr(settings, "PAYMENT_MODE", "demo")

    if mode == "production":
        return TossPaymentGateway()
    else:
        return DemoPaymentGateway()


def is_demo_mode() -> bool:
    """현재 데모 모드인지 확인

    Returns:
        bool: 데모 모드이면 True
    """
    mode = getattr(settings, "PAYMENT_MODE", "demo")
    return mode != "production"
