"""
Admin 대시보드 확인용 샘플 데이터 생성 커맨드

주의:
    - 로컬/개발 환경에서만 사용해야 한다.
    - 실제 운영 데이터는 건드리지 않고, admin-demo-* 이메일을 가진 사용자와
      해당 사용자/게스트의 주문/결제만 생성/정리한다.

예시:
    python manage.py seed_admin_analytics_sample
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from analytics.models import AdminBizDaily
from analytics.services import aggregate_biz_daily_for_range
from authentication.models import User, UserRole
from orders.models import Order, OrderStatus, Payment, PaymentStatus


class Command(BaseCommand):
    """Admin 대시보드용 샘플 주문/결제 데이터를 생성하는 커맨드"""

    help = "Admin 분석 대시보드 확인을 위해 샘플 유저/주문/결제/집계 데이터를 생성합니다."

    def add_arguments(self, parser) -> None:
        """샘플 기간 인자 정의"""
        parser.add_argument(
            "--days",
            type=int,
            default=14,
            help="최근 며칠 치 데이터를 생성할지 지정 (기본값: 14일)",
        )

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        """샘플 데이터 생성 및 집계 실행"""
        days = options.get("days", 14)
        if days <= 0:
            self.stdout.write(self.style.WARNING("days 값이 0 이하라서 기본값 14로 대체합니다."))
            days = 14

        today = timezone.localdate()
        start_date = today - timedelta(days=days - 1)
        end_date = today

        self.stdout.write(
            self.style.NOTICE(
                f"[샘플 생성 시작] {start_date} ~ {end_date} 기간에 대한 Admin 데모 데이터를 생성합니다.",
            )
        )

        # 1. 기존 데모 데이터 정리
        self._cleanup_demo_data()

        # 2. 데모용 사용자 생성
        consumer, seller = self._ensure_demo_users()

        # 3. 일자별로 간단한 주문/결제 생성
        total_orders = self._create_sample_orders_for_range(
            start_date=start_date,
            end_date=end_date,
            consumer=consumer,
            seller=seller,
        )

        # 4. 집계 테이블 생성
        aggregate_biz_daily_for_range(start_date, end_date)

        count_biz_rows = AdminBizDaily.objects.filter(
            date__range=(start_date, end_date)
        ).count()

        self.stdout.write(
            self.style.SUCCESS(
                f"[샘플 생성 완료] 주문 {total_orders}건 생성, "
                f"AdminBizDaily {count_biz_rows}행 집계되었습니다.",
            )
        )

    def _cleanup_demo_data(self) -> None:
        """기존 데모용 데이터 정리

        - admin-demo-* 이메일을 가진 사용자들의 주문/결제를 제거
        - 데모용 게스트 이메일에 해당하는 주문/결제를 제거
        - 관련 AdminBizDaily 집계도 함께 삭제
        """
        demo_emails = [
            "admin-demo-consumer@example.com",
            "admin-demo-seller@example.com",
        ]
        guest_email = "admin-demo-guest@example.com"

        # 데모용 사용자/게스트가 관여한 주문만 선택
        demo_users = User.objects.filter(email__in=demo_emails)
        demo_orders = Order.objects.filter(user__in=demo_users) | Order.objects.filter(
            guest_email=guest_email
        )
        order_ids = list(demo_orders.values_list("id", flat=True))

        if order_ids:
            Payment.objects.filter(order_id__in=order_ids).delete()
            demo_orders.delete()

        # AdminBizDaily 에서 데모 기간 행은 모두 삭제 (안전하게 전체 삭제)
        AdminBizDaily.objects.all().delete()

    def _ensure_demo_users(self) -> tuple[User, User]:
        """데모용 consumer/seller 사용자 생성 또는 조회"""
        consumer, _ = User.objects.get_or_create(
            email="admin-demo-consumer@example.com",
            defaults={
                "username": "admin-demo-consumer",
                "role": UserRole.USER,
            },
        )
        seller, _ = User.objects.get_or_create(
            email="admin-demo-seller@example.com",
            defaults={
                "username": "admin-demo-seller",
                "role": UserRole.SELLER,
            },
        )
        return consumer, seller

    def _create_sample_orders_for_range(
        self,
        start_date: date,
        end_date: date,
        consumer: User,
        seller: User,
    ) -> int:
        """기간 내 매일 간단한 패턴의 주문/결제를 생성"""
        total_orders = 0
        current = start_date
        guest_email = "admin-demo-guest@example.com"

        while current <= end_date:
            # 날짜별로 금액 패턴을 조금씩 다르게 준다
            day_index = (current - start_date).days
            base_amount = 10_000 + (day_index * 1_000)

            # 1) consumer 주문 1건
            consumer_order = Order.objects.create(
                user=consumer,
                status=OrderStatus.PAID,
            )
            self._force_created_at(consumer_order, current)
            Payment.objects.create(
                order=consumer_order,
                amount=base_amount,
                status=PaymentStatus.SUCCESS,
            )
            total_orders += 1

            # 2) seller 주문 1건
            seller_order = Order.objects.create(
                user=seller,
                status=OrderStatus.PAID,
            )
            self._force_created_at(seller_order, current)
            Payment.objects.create(
                order=seller_order,
                amount=base_amount + 5_000,
                status=PaymentStatus.SUCCESS,
            )
            total_orders += 1

            # 3) guest 주문 0~1건 (짝수 날에만 생성)
            if day_index % 2 == 0:
                guest_order = Order.objects.create(
                    user=None,
                    guest_email=guest_email,
                    status=OrderStatus.DELIVERED,
                )
                self._force_created_at(guest_order, current)
                Payment.objects.create(
                    order=guest_order,
                    amount=base_amount + 2_000,
                    status=PaymentStatus.SUCCESS,
                )
                total_orders += 1

            current = current + timedelta(days=1)

        return total_orders

    def _force_created_at(self, order: Order, target_date: date) -> None:
        """auto_now_add 필드를 가진 created_at 값을 강제로 지정"""
        naive_dt = datetime(
            target_date.year,
            target_date.month,
            target_date.day,
            10,
            0,
            0,
        )
        # timezone.is_naive/aware 를 구분하지 않고, DB에는 naive datetime 이 저장되어도
        # 테스트/데모 용도에서는 크게 문제되지 않으므로 단순 처리한다.
        Order.objects.filter(pk=order.pk).update(created_at=naive_dt)
        order.refresh_from_db()


