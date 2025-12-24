"""
결제 게이트웨이 공통 인터페이스

모든 PG 구현체가 따라야 하는 추상 인터페이스를 정의합니다.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any


@dataclass
class PaymentPrepareResult:
    """결제 준비 결과

    프론트엔드에서 결제 SDK를 초기화하기 위한 데이터.
    """

    success: bool
    order_id: str  # PG용 주문 ID (orderId)
    amount: int
    client_key: str  # 프론트엔드용 클라이언트 키
    error_message: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PaymentConfirmResult:
    """결제 승인 결과

    PG에서 결제 승인 후 반환되는 데이터.
    """

    success: bool
    payment_key: str  # PG 결제 키 (paymentKey, pg_tid로 저장)
    amount: int
    method_type: str  # card, virtualAccount, transfer, mobilePhone
    status: str  # DONE, WAITING_FOR_DEPOSIT, CANCELED, ...
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    raw_response: Optional[Dict[str, Any]] = None
    # 카드 결제 정보
    card_info: Optional[Dict[str, Any]] = None
    # 가상계좌 정보
    virtual_account_info: Optional[Dict[str, Any]] = None


@dataclass
class PaymentCancelResult:
    """결제 취소 결과"""

    success: bool
    cancel_amount: int
    refund_status: str  # DONE, PARTIAL_CANCELED, ...
    error_code: Optional[str] = None
    error_message: Optional[str] = None


class PaymentGateway(ABC):
    """결제 게이트웨이 추상 인터페이스

    모든 PG 구현체(데모, 토스페이먼츠 등)가 구현해야 하는 메서드를 정의합니다.
    """

    @abstractmethod
    def prepare_payment(
        self,
        order_no: str,
        amount: int,
        order_name: str,
        customer_email: Optional[str] = None,
        customer_name: Optional[str] = None,
    ) -> PaymentPrepareResult:
        """결제 준비

        프론트엔드 SDK 초기화를 위한 데이터를 생성합니다.

        Args:
            order_no: 내부 주문번호
            amount: 결제 금액
            order_name: 주문명 (예: "상품명 외 2건")
            customer_email: 고객 이메일 (선택)
            customer_name: 고객 이름 (선택)

        Returns:
            PaymentPrepareResult: 결제 준비 결과
        """
        pass

    @abstractmethod
    def confirm_payment(
        self,
        payment_key: str,
        order_id: str,
        amount: int,
    ) -> PaymentConfirmResult:
        """결제 승인

        프론트엔드에서 PG 결제 완료 후 호출합니다.
        토스페이먼츠의 경우 paymentKey, orderId, amount를 전달받아 승인 API를 호출합니다.

        Args:
            payment_key: PG 결제 키 (토스: paymentKey)
            order_id: PG 주문 ID (토스: orderId)
            amount: 결제 금액

        Returns:
            PaymentConfirmResult: 결제 승인 결과
        """
        pass

    @abstractmethod
    def cancel_payment(
        self,
        payment_key: str,
        cancel_reason: str,
        cancel_amount: Optional[int] = None,
    ) -> PaymentCancelResult:
        """결제 취소/환불

        결제 취소 또는 부분 환불을 처리합니다.
        현재는 전체 취소만 지원합니다.

        Args:
            payment_key: PG 결제 키
            cancel_reason: 취소 사유
            cancel_amount: 취소 금액 (None이면 전체 취소)

        Returns:
            PaymentCancelResult: 취소 결과
        """
        pass

    @abstractmethod
    def verify_webhook(
        self,
        payload: bytes,
        signature: str,
    ) -> bool:
        """웹훅 시그니처 검증

        PG에서 전송한 웹훅의 시그니처를 검증합니다.

        Args:
            payload: 웹훅 요청 본문 (bytes)
            signature: 시그니처 헤더 값

        Returns:
            bool: 검증 성공 여부
        """
        pass
