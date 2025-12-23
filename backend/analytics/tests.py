"""
Admin 분석용 집계 모델 테스트

기본값과 제약조건이 의도한 대로 동작하는지 검증한다.
"""

from datetime import date

from django.test import TestCase

from analytics.models import AdminBizDaily, AdminRecoDaily, UserSegment
from analytics.services import aggregate_biz_daily_for_date
from authentication.models import User, UserRole
from orders.models import Order, OrderStatus, Payment, PaymentStatus


class AdminAnalyticsModelTests(TestCase):
    """Admin 집계 테이블 모델에 대한 기본 동작 테스트"""

    def test_admin_biz_daily_defaults_are_zero(self) -> None:
        """비즈니스 집계 기본값이 0으로 초기화되어야 한다"""
        # Arrange: 최소 필수 필드로 레코드 생성
        obj = AdminBizDaily.objects.create(
            date=date(2025, 1, 1),
            user_segment=UserSegment.ALL,
        )

        # Assert: 각 수치 필드가 0으로 세팅되는지 확인
        self.assertEqual(obj.sessions, 0)
        self.assertEqual(obj.unique_buyers, 0)
        self.assertEqual(obj.orders, 0)
        self.assertEqual(obj.gmv, 0)
        self.assertEqual(obj.cart_adds, 0)

    def test_admin_reco_daily_defaults_are_zero(self) -> None:
        """추천 집계 기본값이 0으로 초기화되어야 한다"""
        # Arrange
        obj = AdminRecoDaily.objects.create(
            date=date(2025, 1, 1),
            placement="home",
            user_segment=UserSegment.ALL,
        )

        # Assert
        self.assertEqual(obj.reco_impressions, 0)
        self.assertEqual(obj.reco_clicks, 0)
        self.assertEqual(obj.reco_attributed_orders, 0)
        self.assertEqual(obj.reco_attributed_gmv, 0)


class AdminBizDailyAggregationTests(TestCase):
    """주문/결제를 기반으로 한 비즈니스 일간 집계 테스트"""

    def setUp(self) -> None:
        """테스트용 사용자와 주문/결제 데이터를 준비"""
        # 날짜는 하나의 기준일로 고정
        self.target_date = date(2025, 3, 1)

        # 유저 생성: consumer, seller, admin
        self.consumer = User.objects.create(
            email="consumer@example.com",
            username="consumer1",
            role=UserRole.USER,
        )
        self.seller_user = User.objects.create(
            email="seller@example.com",
            username="seller1",
            role=UserRole.SELLER,
        )
        self.admin_user = User.objects.create(
            email="admin@example.com",
            username="admin1",
            role=UserRole.ADMIN,
        )

        # 소비자 주문 (로그인 사용자)
        self.consumer_order = Order.objects.create(
            user=self.consumer,
            status=OrderStatus.PAID,
        )
        Order.objects.filter(pk=self.consumer_order.pk).update(
            created_at=self._at_target_date(),
        )
        self.consumer_order.refresh_from_db()
        Payment.objects.create(
            order=self.consumer_order,
            amount=10_000,
            status=PaymentStatus.SUCCESS,
        )

        # 게스트 주문 (비회원)
        self.guest_order = Order.objects.create(
            user=None,
            guest_email="guest@example.com",
            status=OrderStatus.DELIVERED,
        )
        Order.objects.filter(pk=self.guest_order.pk).update(
            created_at=self._at_target_date(),
        )
        self.guest_order.refresh_from_db()
        Payment.objects.create(
            order=self.guest_order,
            amount=20_000,
            status=PaymentStatus.SUCCESS,
        )

        # 판매자 주문 (seller role)
        self.seller_order = Order.objects.create(
            user=self.seller_user,
            status=OrderStatus.PAID,
        )
        Order.objects.filter(pk=self.seller_order.pk).update(
            created_at=self._at_target_date(),
        )
        self.seller_order.refresh_from_db()
        Payment.objects.create(
            order=self.seller_order,
            amount=30_000,
            status=PaymentStatus.SUCCESS,
        )

        # 관리자 주문 (집계에서 제외되어야 함)
        self.admin_order = Order.objects.create(
            user=self.admin_user,
            status=OrderStatus.PAID,
        )
        Order.objects.filter(pk=self.admin_order.pk).update(
            created_at=self._at_target_date(),
        )
        self.admin_order.refresh_from_db()
        Payment.objects.create(
            order=self.admin_order,
            amount=999_999,
            status=PaymentStatus.SUCCESS,
        )

        # 다른 날짜 주문 (집계 대상 날짜와 다르므로 제외)
        other_date_order = Order.objects.create(
            user=self.consumer,
            status=OrderStatus.PAID,
        )
        Order.objects.filter(pk=other_date_order.pk).update(
            created_at=self._at_target_date(offset_days=1),
        )
        Payment.objects.create(
            order=other_date_order,
            amount=50_000,
            status=PaymentStatus.SUCCESS,
        )

    def _at_target_date(self, offset_days: int = 0):
        """테스트용으로 날짜 오프셋을 적용한 datetime 생성"""
        # auto_now_add 필드를 우회하기 위해 created_at 을 직접 지정
        from datetime import datetime, timedelta

        base = datetime(self.target_date.year, self.target_date.month, self.target_date.day, 10, 0, 0)
        return base + timedelta(days=offset_days)

    def test_aggregate_biz_daily_for_date_creates_segment_rows(self) -> None:
        """하루 집계 실행 시 all/consumer/seller 세그먼트 데이터가 생성되어야 한다"""
        # Act: 타겟 날짜에 대한 집계 실행
        aggregate_biz_daily_for_date(self.target_date)

        # Assert: 세그먼트별 레코드 존재 여부
        rows = AdminBizDaily.objects.filter(date=self.target_date)
        segments = set(rows.values_list("user_segment", flat=True))
        self.assertEqual(segments, {UserSegment.ALL, UserSegment.CONSUMER, UserSegment.SELLER})

        # all 세그먼트: consumer + seller + 게스트 (admin, 다른 날짜 주문 제외)
        all_row = rows.get(user_segment=UserSegment.ALL)
        self.assertEqual(all_row.orders, 3)  # consumer, guest, seller
        self.assertEqual(all_row.gmv, 10_000 + 20_000 + 30_000)
        self.assertEqual(all_row.unique_buyers, 3)  # consumer, guest, seller

        # consumer 세그먼트: consumer + 게스트만 포함
        consumer_row = rows.get(user_segment=UserSegment.CONSUMER)
        self.assertEqual(consumer_row.orders, 2)  # consumer, guest
        self.assertEqual(consumer_row.gmv, 10_000 + 20_000)
        self.assertEqual(consumer_row.unique_buyers, 2)

        # seller 세그먼트: seller 주문만 포함
        seller_row = rows.get(user_segment=UserSegment.SELLER)
        self.assertEqual(seller_row.orders, 1)
        self.assertEqual(seller_row.gmv, 30_000)
        self.assertEqual(seller_row.unique_buyers, 1)

