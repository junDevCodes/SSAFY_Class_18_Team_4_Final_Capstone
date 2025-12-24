"""
고급 Admin 대시보드 확인용 시나리오 기반 더미 데이터 생성 커맨드

기본 샘플 데이터(seed_admin_analytics_sample)를 생성한 뒤,
Behavior/Recommendation/Top Line 대시보드가 모두 풍부하게 보이도록
일간 집계(AdminBizDaily)를 시나리오별로 보정한다.

주의:
    - 로컬/개발 환경에서만 사용해야 한다.
    - 실제 운영 데이터는 건드리지 않고, seed_admin_analytics_sample 과 동일한
      데모 유저/주문/집계 데이터 위에 추가적인 패턴을 입힌다.

예시:
    python manage.py seed_admin_analytics_scenarios --days 14
"""

from __future__ import annotations

from datetime import date, timedelta

from django.core.management import BaseCommand, call_command
from django.db import transaction
from django.utils import timezone

from analytics.models import AdminBizDaily, UserSegment


class Command(BaseCommand):
    help = "Admin 분석 대시보드용 시나리오 기반 더미 데이터를 생성합니다."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--days",
            type=int,
            default=14,
            help="최근 며칠 치 데이터를 생성할지 지정 (기본값: 14일)",
        )

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        days = options.get("days", 14)
        if days <= 0:
            self.stdout.write(self.style.WARNING("days 값이 0 이하라서 기본값 14로 대체합니다."))
            days = 14

        today = timezone.localdate()
        start_date = today - timedelta(days=days - 1)
        end_date = today

        self.stdout.write(
            self.style.NOTICE(
                f"[시나리오 샘플 생성 시작] {start_date} ~ {end_date} 기간에 대한 "
                "기본 샘플 + 시나리오 보정 데이터를 생성합니다.",
            )
        )

        # 1. 기본 샘플 데이터 생성 (주문/결제/집계/추천/카테고리)
        call_command("seed_admin_analytics_sample", days=days)

        # 2. Behavior 대시보드용 세션/장바구니 이벤트 시나리오 보정
        self._enrich_behavior_fields(start_date, end_date)

        self.stdout.write(self.style.SUCCESS("[시나리오 샘플 생성 완료]"))

    def _enrich_behavior_fields(self, start_date: date, end_date: date) -> None:
        """
        AdminBizDaily.sessions / cart_adds 를 시나리오별 패턴으로 채운다.

        시나리오 예시 (날짜 기준):
            - 0, 1, 2일차: 기본 건강한 유저풀 (baseline)
            - 3, 4, 5일차: 프로모션/트래픽 스파이크 (promo)
            - 6, 7, 8일차: 장바구니 포기율 증가 구간 (high_abandon)
            - 9일차 이후: 충성 고객/재구매 중심 구간 (loyal)
        """

        current = start_date
        while current <= end_date:
            day_index = (current - start_date).days
            if day_index <= 2:
                scenario = "baseline"
            elif day_index <= 5:
                scenario = "promo"
            elif day_index <= 8:
                scenario = "high_abandon"
            else:
                scenario = "loyal"

            for segment in (UserSegment.ALL, UserSegment.CONSUMER, UserSegment.SELLER):
                try:
                    biz = AdminBizDaily.objects.get(date=current, user_segment=segment)
                except AdminBizDaily.DoesNotExist:
                    continue

                orders = int(biz.orders or 0)
                buyers = int(biz.unique_buyers or 0)

                if orders == 0 and buyers == 0:
                    continue

                # 기본 세션/장바구니 기준값 설정
                base_sessions = max(orders * 10, buyers * 12) + 60
                base_cart_adds = max(orders * 2, buyers)  # 최소한 주문 수 이상은 담기

                if scenario == "baseline":
                    sessions = int(base_sessions * 1.0)
                    cart_adds = int(base_cart_adds * 1.5)
                elif scenario == "promo":
                    # 프로모션: 트래픽와 장바구니 증가, 전환도 양호
                    sessions = int(base_sessions * 1.4)
                    cart_adds = int(base_cart_adds * 2.2)
                elif scenario == "high_abandon":
                    # 장바구니 포기: 장바구니는 많으나 주문은 그대로 → 전환/퍼널 악화
                    sessions = int(base_sessions * 1.6)
                    cart_adds = int(base_cart_adds * 3.8)
                else:  # loyal
                    # 충성 고객: 세션/장바구니 대비 주문 효율이 높은 구간
                    sessions = int(base_sessions * 0.9)
                    cart_adds = int(base_cart_adds * 1.3)

                # 세그먼트별로 약간의 가중치 차이 부여
                if segment == UserSegment.CONSUMER:
                    cart_adds = int(cart_adds * 1.1)
                elif segment == UserSegment.SELLER:
                    sessions = int(sessions * 0.85)

                # 시나리오 패턴이 적용된 레코드는 테스트 플래그 및 시나리오 태그를 함께 기록
                AdminBizDaily.objects.filter(pk=biz.pk).update(
                    sessions=max(sessions, 0),
                    cart_adds=max(cart_adds, 0),
                    is_test=True,
                    scenario=scenario,
                )

            current = current + timedelta(days=1)


