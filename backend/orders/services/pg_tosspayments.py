"""
토스페이먼츠 결제 게이트웨이

토스페이먼츠 API를 연동하여 실제 결제를 처리합니다.
- 결제 승인: /v1/payments/confirm
- 결제 취소: /v1/payments/{paymentKey}/cancel
- 웹훅 검증: HMAC-SHA256
"""

import base64
import hmac
import hashlib
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


class TossPaymentGateway(PaymentGateway):
    """토스페이먼츠 결제 게이트웨이

    토스페이먼츠 API를 연동합니다.
    - API 문서: https://docs.tosspayments.com/reference
    """

    # 요청 타임아웃 (초)
    REQUEST_TIMEOUT = 30

    def __init__(self):
        self.client_key = getattr(settings, "TOSS_CLIENT_KEY", "")
        self.secret_key = getattr(settings, "TOSS_SECRET_KEY", "")
        self.api_url = getattr(settings, "TOSS_API_URL", "https://api.tosspayments.com/v1")
        self.webhook_secret = getattr(settings, "TOSS_WEBHOOK_SECRET", "")

    def _get_auth_header(self) -> dict:
        """Basic Auth 헤더 생성

        토스페이먼츠 API는 시크릿 키를 Base64로 인코딩하여 Authorization 헤더에 전달합니다.
        시크릿 키 뒤에 ':'를 추가해야 합니다.
        """
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
        """결제 준비

        토스페이먼츠는 프론트엔드 SDK에서 직접 결제창을 호출하므로,
        백엔드에서는 클라이언트 키와 주문 정보만 전달합니다.
        """
        # 토스 형식 order_id: 주문번호_랜덤8자리 (영문+숫자, 최대 64자)
        order_id = f"{order_no}_{uuid.uuid4().hex[:8].upper()}"

        # 프론트엔드에서 사용할 리다이렉트 URL
        success_url = getattr(settings, "PAYMENT_SUCCESS_URL", "")
        fail_url = getattr(settings, "PAYMENT_FAIL_URL", "")

        return PaymentPrepareResult(
            success=True,
            order_id=order_id,
            amount=amount,
            client_key=self.client_key,
            extra={
                "order_name": order_name,
                "customer_email": customer_email,
                "customer_name": customer_name,
                "success_url": success_url,
                "fail_url": fail_url,
                "is_demo": False,
            },
        )

    def confirm_payment(
        self,
        payment_key: str,
        order_id: str,
        amount: int,
    ) -> PaymentConfirmResult:
        """결제 승인

        토스페이먼츠 결제 승인 API를 호출합니다.
        https://docs.tosspayments.com/reference#%EA%B2%B0%EC%A0%9C-%EC%8A%B9%EC%9D%B8
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

                return PaymentConfirmResult(
                    success=True,
                    payment_key=data["paymentKey"],
                    amount=data["totalAmount"],
                    method_type=method_type,
                    status=data["status"],
                    raw_response=data,
                    card_info=card_info,
                    virtual_account_info=virtual_account_info,
                )
            else:
                # 결제 실패
                logger.error(f"토스페이먼츠 결제 승인 실패: {data}")
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
            logger.exception(f"토스페이먼츠 API 요청 실패: {e}")
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
        """결제 취소

        토스페이먼츠 결제 취소 API를 호출합니다.
        https://docs.tosspayments.com/reference#%EA%B2%B0%EC%A0%9C-%EC%B7%A8%EC%86%8C
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
                logger.error(f"토스페이먼츠 결제 취소 실패: {data}")
                return PaymentCancelResult(
                    success=False,
                    cancel_amount=0,
                    refund_status="FAILED",
                    error_code=data.get("code"),
                    error_message=data.get("message"),
                )

        except requests.RequestException as e:
            logger.exception(f"토스페이먼츠 취소 API 요청 실패: {e}")
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
        """웹훅 시그니처 검증

        HMAC-SHA256으로 서명을 검증합니다.
        """
        if not self.webhook_secret:
            logger.warning("TOSS_WEBHOOK_SECRET이 설정되지 않았습니다.")
            return False

        expected_signature = hmac.new(
            self.webhook_secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected_signature, signature)

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
