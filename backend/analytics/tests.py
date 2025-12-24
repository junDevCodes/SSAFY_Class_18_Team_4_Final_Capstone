"""
Admin 분석용 집계 모델 테스트

기본값과 제약조건이 의도한 대로 동작하는지 검증한다.
"""

from datetime import date

from django.test import TestCase
from rest_framework.test import APIClient

from analytics.models import AdminBizDaily, AdminRecoDaily, AdminCategoryDaily, UserSegment
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


class AdminAnalyticsOverviewAPITests(TestCase):
    """Admin Analytics Overview API 동작 테스트"""

    def setUp(self) -> None:
        """테스트용 데이터와 API 클라이언트 준비"""
        self.client = APIClient()
        self.target_date = date(2025, 3, 1)

        # 유저 생성
        self.consumer = User.objects.create(
            email="overview-consumer@example.com",
            username="overview-consumer",
            role=UserRole.USER,
        )
        self.seller_user = User.objects.create(
            email="overview-seller@example.com",
            username="overview-seller",
            role=UserRole.SELLER,
        )
        guest_email = "overview-guest@example.com"

        # consumer 주문 1건 (10,000원)
        consumer_order = Order.objects.create(
            user=self.consumer,
            status=OrderStatus.PAID,
        )
        self._force_created_at(consumer_order, self.target_date)
        Payment.objects.create(
            order=consumer_order,
            amount=10_000,
            status=PaymentStatus.SUCCESS,
        )

        # guest 주문 1건 (20,000원)
        guest_order = Order.objects.create(
            user=None,
            guest_email=guest_email,
            status=OrderStatus.DELIVERED,
        )
        self._force_created_at(guest_order, self.target_date)
        Payment.objects.create(
            order=guest_order,
            amount=20_000,
            status=PaymentStatus.SUCCESS,
        )

        # seller 주문 1건 (30,000원)
        seller_order = Order.objects.create(
            user=self.seller_user,
            status=OrderStatus.PAID,
        )
        self._force_created_at(seller_order, self.target_date)
        Payment.objects.create(
            order=seller_order,
            amount=30_000,
            status=PaymentStatus.SUCCESS,
        )

        # Admin 집계 실행
        aggregate_biz_daily_for_date(self.target_date)

        # 추천 집계 샘플 데이터 (홈 추천 기준)
        # - 노출 1,000회, 클릭 100회 → CTR 10%
        # - 추천 기여 주문 10건, 기여 GMV 20,000원
        AdminRecoDaily.objects.create(
            date=self.target_date,
            placement="home",
            user_segment=UserSegment.ALL,
            reco_impressions=1_000,
            reco_clicks=100,
            reco_attributed_orders=10,
            reco_attributed_gmv=20_000,
        )

    def _force_created_at(self, order: Order, target_date: date) -> None:
        """auto_now_add 필드를 가진 created_at 값을 강제로 지정"""
        from datetime import datetime

        naive_dt = datetime(
            target_date.year,
            target_date.month,
            target_date.day,
            10,
            0,
            0,
        )
        Order.objects.filter(pk=order.pk).update(created_at=naive_dt)
        order.refresh_from_db()

    def test_overview_returns_topline_kpis_and_trend(self) -> None:
        """Overview API가 Top Line KPI와 추이 데이터를 반환해야 한다"""
        response = self.client.get(
            "/api/admin/analytics/overview/",
            {
                "start_date": self.target_date.isoformat(),
                "end_date": self.target_date.isoformat(),
                "granularity": "daily",
                "segment": "all",
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()

        # 상단 KPI 존재 여부 확인
        self.assertIn("kpis", data)
        self.assertGreater(len(data["kpis"]), 0)

        # 총 매출/주문 수 KPI 값 검증
        gmvs = [k for k in data["kpis"] if k["label"].startswith("총 매출")]
        self.assertTrue(gmvs)
        self.assertEqual(gmvs[0]["value"], 60_000.0)

        orders_kpi = [k for k in data["kpis"] if k["label"].startswith("주문 수")]
        self.assertTrue(orders_kpi)
        self.assertEqual(orders_kpi[0]["value"], 3.0)

        # 추이 데이터 검증
        self.assertIn("trend", data)
        self.assertIn("source", data["trend"])
        trend = data["trend"]["source"]
        self.assertEqual(len(trend), 1)
        self.assertEqual(trend[0]["date"], self.target_date.isoformat())
        self.assertEqual(trend[0]["revenue"], 60_000)
        self.assertEqual(trend[0]["orders"], 3)

        # 추천 KPI (홈 추천) 검증
        home_ctr_kpi = [k for k in data["kpis"] if k["label"].startswith("홈 추천 CTR")]
        self.assertTrue(home_ctr_kpi)
        self.assertAlmostEqual(home_ctr_kpi[0]["value"], 10.0, places=2)

        home_share_kpi = [
            k for k in data["kpis"] if k["label"].startswith("홈 추천 기여 GMV 비율")
        ]
        self.assertTrue(home_share_kpi)
        # 총 GMV 60,000 중 추천 기여 20,000 → 33.33%
        self.assertAlmostEqual(home_share_kpi[0]["value"], 33.33, places=2)

    def test_overview_includes_category_breakdown_when_available(self) -> None:
        """카테고리 집계가 존재하는 경우 breakdown.product 에 반영되어야 한다"""
        AdminCategoryDaily.objects.create(
            date=self.target_date,
            user_segment=UserSegment.ALL,
            category_name="과일·채소",
            sessions=0,
            orders=2,
            gmv=15_000,
        )
        AdminCategoryDaily.objects.create(
            date=self.target_date,
            user_segment=UserSegment.ALL,
            category_name="축산·계란",
            sessions=0,
            orders=1,
            gmv=10_000,
        )

        response = self.client.get(
            "/api/admin/analytics/overview/",
            {
                "start_date": self.target_date.isoformat(),
                "end_date": self.target_date.isoformat(),
                "granularity": "daily",
                "segment": "all",
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertIn("breakdown", data)
        self.assertIn("product", data["breakdown"])
        products = data["breakdown"]["product"]
        self.assertGreaterEqual(len(products), 2)


class AdminRecommendationTrendAPITests(TestCase):
    """추천 성과 추이 API 동작 테스트"""

    def setUp(self) -> None:
        """비즈니스/추천 집계 데이터를 준비"""
        self.client = APIClient()
        self.target_date = date(2025, 3, 1)

        # 유저 및 주문/결제 데이터는 기존 집계 테스트와 동일 패턴으로 구성
        consumer = User.objects.create(
            email="reco-consumer@example.com",
            username="reco-consumer",
            role=UserRole.USER,
        )
        seller_user = User.objects.create(
            email="reco-seller@example.com",
            username="reco-seller",
            role=UserRole.SELLER,
        )

        # consumer 주문 1건 (10,000원)
        consumer_order = Order.objects.create(
            user=consumer,
            status=OrderStatus.PAID,
        )
        self._force_created_at(consumer_order, self.target_date)
        Payment.objects.create(
            order=consumer_order,
            amount=10_000,
            status=PaymentStatus.SUCCESS,
        )

        # seller 주문 1건 (30,000원)
        seller_order = Order.objects.create(
            user=seller_user,
            status=OrderStatus.PAID,
        )
        self._force_created_at(seller_order, self.target_date)
        Payment.objects.create(
            order=seller_order,
            amount=30_000,
            status=PaymentStatus.SUCCESS,
        )

        # 집계 실행 (총 GMV 40,000)
        aggregate_biz_daily_for_date(self.target_date)

        # 추천 집계: 노출 1,000 / 클릭 100 / 주문 10 / 추천 기여 GMV 20,000
        AdminRecoDaily.objects.create(
            date=self.target_date,
            placement="home",
            user_segment=UserSegment.ALL,
            reco_impressions=1_000,
            reco_clicks=100,
            reco_attributed_orders=10,
            reco_attributed_gmv=20_000,
        )

    def _force_created_at(self, order: Order, target_date: date) -> None:
        """auto_now_add 필드를 가진 created_at 값을 강제로 지정"""
        from datetime import datetime

        naive_dt = datetime(
            target_date.year,
            target_date.month,
            target_date.day,
            10,
            0,
            0,
        )
        Order.objects.filter(pk=order.pk).update(created_at=naive_dt)
        order.refresh_from_db()

    def test_recommendation_trend_returns_daily_metrics(self) -> None:
        """홈 추천 기준 CTR/구매 전환율/기여 GMV 비율 일간 추이를 반환해야 한다"""
        response = self.client.get(
            "/api/admin/analytics/recommendation/trend/",
            {
                "start_date": self.target_date.isoformat(),
                "end_date": self.target_date.isoformat(),
                "granularity": "daily",
                "segment": "all",
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertIn("series", data)
        self.assertEqual(len(data["series"]), 1)

        point = data["series"][0]
        self.assertEqual(point["date"], self.target_date.isoformat())

        # 원시 수치 검증
        self.assertEqual(point["impressions"], 1_000)
        self.assertEqual(point["clicks"], 100)
        self.assertEqual(point["attributed_orders"], 10)
        self.assertEqual(point["attributed_gmv"], 20_000)

        # 파생 지표 검증
        # CTR: 100 / 1,000 = 10%
        self.assertAlmostEqual(point["ctr"], 10.0, places=2)
        # 구매 전환율: 10 / 100 = 10%
        self.assertAlmostEqual(point["purchase_conversion"], 10.0, places=2)
        # 추천 기여 GMV 비율: 20,000 / 40,000 = 50%
        self.assertAlmostEqual(point["gmv_share"], 50.0, places=2)


class AdminRecommendationPlacementSummaryAPITests(TestCase):
    """추천 placement 별 집계 API 동작 테스트"""

    def setUp(self) -> None:
        """간단한 BizDaily/RecoDaily 데이터를 직접 생성"""
        self.client = APIClient()
        self.start_date = date(2025, 3, 1)
        self.end_date = date(2025, 3, 2)

        # 전체 세그먼트 기준 총 GMV: 2일 * 100,000 = 200,000
        for day in [self.start_date, self.end_date]:
            AdminBizDaily.objects.create(
                date=day,
                user_segment=UserSegment.ALL,
                gmv=100_000,
            )

        # price_model: 2일 동안
        # - 노출: 1,000 * 2 = 2,000
        # - 클릭: 100 * 2 = 200
        # - 추천 기여 주문: 20 * 2 = 40
        # - 추천 기여 GMV: 20,000 * 2 = 40,000 → GMV 비율 20%
        for day in [self.start_date, self.end_date]:
            AdminRecoDaily.objects.create(
                date=day,
                placement="price_model",
                user_segment=UserSegment.ALL,
                reco_impressions=1_000,
                reco_clicks=100,
                reco_attributed_orders=20,
                reco_attributed_gmv=20_000,
            )

        # personalized: 2일 동안
        # - 노출: 500 * 2 = 1,000
        # - 클릭: 50 * 2 = 100
        # - 추천 기여 주문: 5 * 2 = 10
        # - 추천 기여 GMV: 10,000 * 2 = 20,000 → GMV 비율 10%
        for day in [self.start_date, self.end_date]:
            AdminRecoDaily.objects.create(
                date=day,
                placement="personalized",
                user_segment=UserSegment.ALL,
                reco_impressions=500,
                reco_clicks=50,
                reco_attributed_orders=5,
                reco_attributed_gmv=10_000,
            )

    def test_placement_summary_returns_expected_metrics(self) -> None:
        """placement 별 CTR/구매 전환율/기여 GMV 비율을 올바르게 반환해야 한다"""
        response = self.client.get(
            "/api/admin/analytics/recommendation/placement-summary/",
            {
                "start_date": self.start_date.isoformat(),
                "end_date": self.end_date.isoformat(),
                "granularity": "daily",
                "segment": "all",
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertIn("placements", data)
        placements = data["placements"]

        # price_model 행 검증
        price_rows = [p for p in placements if p["placement"] == "price_model"]
        self.assertEqual(len(price_rows), 1)
        price = price_rows[0]
        self.assertEqual(price["impressions"], 2_000)
        self.assertEqual(price["clicks"], 200)
        self.assertEqual(price["attributed_orders"], 40)
        self.assertEqual(price["attributed_gmv"], 40_000)
        # CTR: 200 / 2,000 = 10%
        self.assertAlmostEqual(price["ctr"], 10.0, places=2)
        # 구매 전환율: 40 / 200 = 20%
        self.assertAlmostEqual(price["purchase_conversion"], 20.0, places=2)
        # 기여 GMV 비율: 40,000 / 200,000 = 20%
        self.assertAlmostEqual(price["gmv_share"], 20.0, places=2)

        # 통합(all) 행 존재 여부 확인
        all_rows = [p for p in placements if p["placement"] == "all"]
        self.assertEqual(len(all_rows), 1)
