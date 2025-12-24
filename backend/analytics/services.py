"""
Admin 분석용 집계 서비스

주문/결제 데이터를 기반으로 일 단위 비즈니스 지표를 집계한다.
"""

from __future__ import annotations

from datetime import date

from django.db import transaction
from django.db.models import Q, Sum
from django.db.models.functions import Coalesce

from analytics.models import AdminBizDaily, UserSegment
from authentication.models import UserRole
from orders.models import Order, OrderStatus, Payment, PaymentStatus


def _get_segmented_order_queryset(target_date: date) -> dict[UserSegment, "Order"].values:
    """
    특정 날짜의 유효 주문을 세그먼트별로 나눈다.

    - all: consumer + seller + 게스트, admin 은 제외
    - consumer: user.role 이 일반회원/guest 이거나 user 가 없는 주문
    - seller: user.role 이 seller 인 주문
    """
    base_qs = (
        Order.objects.filter(
            created_at__date=target_date,
            status__in=[
                OrderStatus.PAID,
                OrderStatus.PROCESSING,
                OrderStatus.SHIPPED,
                OrderStatus.DELIVERED,
            ],
        )
        .select_related("user")
        .exclude(user__role=UserRole.ADMIN)
    )

    consumer_qs = base_qs.filter(
        Q(user__isnull=True)
        | Q(
            user__role__in=[
                UserRole.USER,
                UserRole.GUEST,
            ]
        )
    )
    seller_qs = base_qs.filter(user__role=UserRole.SELLER)

    return {
        UserSegment.ALL: base_qs,
        UserSegment.CONSUMER: consumer_qs,
        UserSegment.SELLER: seller_qs,
    }


def _count_unique_buyers(qs: "Order".values) -> int:
    """
    주문 집합에서 유니크 구매자 수를 계산한다.

    - 회원: user 기준 distinct
    - 비회원: guest_email 기준 distinct
    """
    registered = (
        qs.filter(user__isnull=False)
        .values("user_id")
        .distinct()
        .count()
    )
    guest = (
        qs.filter(user__isnull=True)
        .exclude(guest_email__isnull=True)
        .values("guest_email")
        .distinct()
        .count()
    )
    return registered + guest


def _sum_success_payments(qs: "Order".values) -> int:
    """
    주문 집합에 대해 성공 결제 금액 합계를 계산한다.

    - Payment.status 가 SUCCESS 인 레코드만 포함
    """
    if not qs.exists():
        return 0

    agg = Payment.objects.filter(
        order__in=qs,
        status=PaymentStatus.SUCCESS,
    ).aggregate(total=Coalesce(Sum("amount"), 0))
    return int(agg["total"] or 0)


@transaction.atomic
def aggregate_biz_daily_for_date(target_date: date) -> None:
    """
    특정 날짜에 대한 비즈니스 일간 집계를 수행한다.

    - 주문/결제 테이블에서 유효 주문만 필터링
    - 세그먼트별(AdminBizDaily)로 upsert 수행
    """
    segmented = _get_segmented_order_queryset(target_date)

    # 날짜 기준 기존 집계는 모두 삭제 후 다시 채운다
    AdminBizDaily.objects.filter(date=target_date).delete()

    for segment, qs in segmented.items():
        if not qs.exists():
            # 해당 세그먼트에 주문이 없으면 레코드를 만들지 않는다
            continue

        unique_buyers = _count_unique_buyers(qs)
        total_orders = qs.count()
        total_gmv = _sum_success_payments(qs)

        AdminBizDaily.objects.update_or_create(
            date=target_date,
            user_segment=segment,
            defaults={
                "sessions": 0,  # 세션 로그 도입 전까지는 0 유지
                "unique_buyers": unique_buyers,
                "orders": total_orders,
                "gmv": total_gmv,
                "cart_adds": 0,  # 장바구니 이벤트 집계는 후속 단계에서 구현
            },
        )


def aggregate_biz_daily_for_range(start_date: date, end_date: date) -> None:
    """
    시작/종료 날짜 범위에 대해 비즈니스 일간 집계를 수행한다.

    - 양 끝 날짜를 포함하여 순차적으로 집계
    """
    current = start_date
    while current <= end_date:
        aggregate_biz_daily_for_date(current)
        current = date.fromordinal(current.toordinal() + 1)


