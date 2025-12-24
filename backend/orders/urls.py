"""
주문 관련 URL 설정

- /api/orders/                      : 주문 CRUD
- /api/orders/guest/                : 비회원 주문
- /api/orders/payments/             : PG 결제 (토스페이먼츠)
- /api/orders/webhooks/toss/        : 토스 웹훅
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import OrderViewSet, GuestOrderViewSet
from .payment_views import PaymentViewSet
from .webhooks import toss_webhook

# Router 설정
router = DefaultRouter()
router.register(r"guest", GuestOrderViewSet, basename="guest-order")
router.register(r"payments", PaymentViewSet, basename="payment")
router.register(r"", OrderViewSet, basename="order")

urlpatterns = [
    # 웹훅 (라우터 앞에 배치하여 우선 매칭)
    path("webhooks/toss/", toss_webhook, name="toss-webhook"),
    # 라우터
    path("", include(router.urls)),
]
