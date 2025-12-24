"""
데모 결제 게이트웨이

토스페이먼츠 테스트 환경을 사용하여 결제 흐름을 테스트합니다.
- 토스페이먼츠 테스트 키를 사용하여 실제 API를 호출합니다.
- 실제 결제가 발생하지 않지만, 모든 결제 흐름을 동일하게 테스트할 수 있습니다.
- 결제 수단(카드, 간편결제, 계좌이체 등)이 정확하게 기록됩니다.

참고: 데모 모드에서도 토스페이먼츠 결제위젯 SDK와 API를 사용하므로,
      실제 토스페이먼츠 테스트 키를 사용해야 합니다.
"""

import base64
import uuid
import logging
from typing import Optional

import requests
from django.conf import settings

from .pg_base import (
    PaymentGateway,
    PaymentPrepareResult,
    PaymentConfirmResult,
    PaymentCancelResult,
)


logger = logging.getLogger(__name__)


class DemoPaymentGateway(PaymentGateway):
    """데모 모드 결제 게이트웨이

    토스페이먼츠 테스트 환경을 사용하여 결제 흐름을 테스트합니다.
    - 결제 준비: 토스페이먼츠 테스트 키로 위젯 렌더링
    - 결제 승인: 토스페이먼츠 테스트 API 호출 (실제 결제 없음)
    - 결제 취소: 토스페이먼츠 테스트 API 호출

    주의: 결제위젯 렌더링 및 API 호출을 위해 실제 토스페이먼츠 테스트 키를 사용합니다.
    """

    # 요청 타임아웃 (초)
    REQUEST_TIMEOUT = 30

    def __init__(self):
        # 환경 변수에서 토스페이먼츠 테스트 키 가져오기
        self.client_key = getattr(settings, "TOSS_CLIENT_KEY", "test_gck_docs_Ovk5rk1EwkEbP0W43n07xlzm")
        self.secret_key = getattr(settings, "TOSS_SECRET_KEY", "test_gsk_docs_OaPz8L5KdmQXkzRz3y47BMw6")
        self.api_url = getattr(settings, "TOSS_API_URL", "https://api.tosspayments.com/v1")

    def _get_auth_header(self) -> dict:
        """Basic Auth 헤더 생성"""
        credentials = base64.b64encode(f"{self.secret_key}:".encode()).decode()
        return {
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/json",
        }

    def prepare_payment(
        self,
        order_no: str,
        amount: int,
        order_name: str,
        customer_email: Optional[str] = None,
        customer_name: Optional[str] = None,
    ) -> PaymentPrepareResult:
        """데모 결제 준비

        토스페이먼츠 형식의 order_id를 생성합니다.
        """
        # 토스 형식 모방: 주문번호_랜덤8자리
        order_id = f"DEMO_{order_no}_{uuid.uuid4().hex[:8].upper()}"

        return PaymentPrepareResult(
            success=True,
            order_id=order_id,
            amount=amount,
            client_key=self.client_key,
            extra={
                "order_name": order_name,
                "customer_email": customer_email,
                "customer_name": customer_name,
                "is_demo": True,
            },
        )

    def confirm_payment(
        self,
        payment_key: str,
        order_id: str,
        amount: int,
    ) -> PaymentConfirmResult:
        """데모 결제 승인

        토스페이먼츠 테스트 API를 호출하여 결제를 승인합니다.
        테스트 키를 사용하므로 실제 결제가 발생하지 않습니다.
        """
        url = f"{self.api_url}/payments/confirm"
        payload = {
            "paymentKey": payment_key,
            "orderId": order_id,
            "amount": amount,
        }

        try:
            response = requests.post(
                url,
                json=payload,
                headers=self._get_auth_header(),
                timeout=self.REQUEST_TIMEOUT,
            )
            data = response.json()

            if response.status_code == 200:
                # 결제 성공
                card_info = None
                virtual_account_info = None

                # 카드 결제 정보
                if data.get("card"):
                    card = data["card"]
                    card_info = {
                        "company": card.get("company"),
                        "number": card.get("number"),
                        "installmentPlanMonths": card.get("installmentPlanMonths", 0),
                        "isInterestFree": card.get("isInterestFree", False),
                    }

                # 가상계좌 정보
                if data.get("virtualAccount"):
                    va = data["virtualAccount"]
                    virtual_account_info = {
                        "accountNumber": va.get("accountNumber"),
                        "bank": va.get("bank"),
                        "customerName": va.get("customerName"),
                        "dueDate": va.get("dueDate"),
                    }

                # 결제 수단 매핑
                method = data.get("method", "")
                method_type = self._map_method_type(method)

                # 데모 모드 표시를 위해 raw_response에 is_demo 추가
                raw_response = data.copy()
                raw_response["is_demo"] = True

                return PaymentConfirmResult(
                    success=True,
                    payment_key=data["paymentKey"],
                    amount=data["totalAmount"],
                    method_type=method_type,
                    status=data["status"],
                    raw_response=raw_response,
                    card_info=card_info,
                    virtual_account_info=virtual_account_info,
                )
            else:
                # 결제 실패
                logger.error(f"[데모] 토스페이먼츠 결제 승인 실패: {data}")
                return PaymentConfirmResult(
                    success=False,
                    payment_key=payment_key,
                    amount=amount,
                    method_type="unknown",
                    status="FAILED",
                    error_code=data.get("code"),
                    error_message=data.get("message"),
                    raw_response=data,
                )

        except requests.RequestException as e:
            logger.exception(f"[데모] 토스페이먼츠 API 요청 실패: {e}")
            return PaymentConfirmResult(
                success=False,
                payment_key=payment_key,
                amount=amount,
                method_type="unknown",
                status="ERROR",
                error_code="NETWORK_ERROR",
                error_message=str(e),
            )

    def cancel_payment(
        self,
        payment_key: str,
        cancel_reason: str,
        cancel_amount: Optional[int] = None,
    ) -> PaymentCancelResult:
        """데모 결제 취소

        토스페이먼츠 테스트 API를 호출하여 결제를 취소합니다.
        """
        url = f"{self.api_url}/payments/{payment_key}/cancel"
        payload = {"cancelReason": cancel_reason}

        if cancel_amount:
            payload["cancelAmount"] = cancel_amount

        try:
            response = requests.post(
                url,
                json=payload,
                headers=self._get_auth_header(),
                timeout=self.REQUEST_TIMEOUT,
            )
            data = response.json()

            if response.status_code == 200:
                # 취소 성공
                cancels = data.get("cancels", [])
                total_cancel = sum(c.get("cancelAmount", 0) for c in cancels)
                return PaymentCancelResult(
                    success=True,
                    cancel_amount=total_cancel,
                    refund_status=data.get("status", "CANCELED"),
                )
            else:
                # 취소 실패
                logger.error(f"[데모] 토스페이먼츠 결제 취소 실패: {data}")
                return PaymentCancelResult(
                    success=False,
                    cancel_amount=0,
                    refund_status="FAILED",
                    error_code=data.get("code"),
                    error_message=data.get("message"),
                )

        except requests.RequestException as e:
            logger.exception(f"[데모] 토스페이먼츠 취소 API 요청 실패: {e}")
            return PaymentCancelResult(
                success=False,
                cancel_amount=0,
                refund_status="ERROR",
                error_code="NETWORK_ERROR",
                error_message=str(e),
            )

    def verify_webhook(
        self,
        payload: bytes,
        signature: str,
    ) -> bool:
        """데모 웹훅 검증

        데모 모드에서는 항상 True를 반환합니다.
        (테스트 환경에서는 웹훅 시그니처 검증을 건너뜁니다)
        """
        return True

    def _map_method_type(self, method: str) -> str:
        """토스 결제 수단을 내부 타입으로 매핑

        토스페이먼츠 결제 수단:
        - 카드: 신용/체크카드
        - 가상계좌: 무통장입금
        - 계좌이체: 실시간 계좌이체
        - 휴대폰: 휴대폰 소액결제
        - 간편결제: 카카오페이, 네이버페이, 토스페이, 페이코 등
        - 상품권: 문화상품권, 도서상품권 등
        """
        mapping = {
            "카드": "card",
            "가상계좌": "virtual_account",
            "계좌이체": "bank_transfer",
            "휴대폰": "mobile",
            "간편결제": "easy_pay",
            "상품권": "gift_card",
            "문화상품권": "gift_card",
            "도서문화상품권": "gift_card",
            "게임문화상품권": "gift_card",
        }
        return mapping.get(method, method or "other")
