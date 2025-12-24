"""
비즈니스 일간 집계 실행 커맨드

예시:
    python manage.py aggregate_biz_daily --date 2025-03-01
    python manage.py aggregate_biz_daily --start-date 2025-03-01 --end-date 2025-03-07

날짜가 주어지지 않으면 어제 날짜를 기준으로 집계한다.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from analytics.services import aggregate_biz_daily_for_date, aggregate_biz_daily_for_range


class Command(BaseCommand):
    """비즈니스 일간 집계를 실행하는 management command"""

    help = "주문/결제 데이터를 기반으로 Admin 비즈니스 일간 집계를 수행합니다."

    def add_arguments(self, parser) -> None:
        """커맨드 인자 정의"""
        parser.add_argument(
            "--date",
            type=str,
            help="집계할 날짜 (YYYY-MM-DD). 지정하지 않으면 어제 날짜를 사용.",
        )
        parser.add_argument(
            "--start-date",
            type=str,
            help="집계 시작 날짜 (YYYY-MM-DD, 범위 집계용).",
        )
        parser.add_argument(
            "--end-date",
            type=str,
            help="집계 종료 날짜 (YYYY-MM-DD, 범위 집계용).",
        )

    def handle(self, *args, **options) -> None:
        """입력 인자를 해석하여 적절한 집계 함수를 호출"""
        raw_date = options.get("date")
        raw_start = options.get("start_date")
        raw_end = options.get("end_date")

        # date 와 start/end 를 동시에 사용할 수 없도록 방어
        if raw_date and (raw_start or raw_end):
            raise CommandError("`--date`와 `--start-date/--end-date`는 동시에 사용할 수 없습니다.")

        # 단일 날짜 집계
        if raw_date:
            target = self._parse_date(raw_date, flag_name="--date")
            self.stdout.write(self.style.NOTICE(f"[집계 시작] {target} 비즈니스 일간 집계 실행"))
            aggregate_biz_daily_for_date(target)
            self.stdout.write(self.style.SUCCESS(f"[집계 완료] {target} 비즈니스 일간 집계가 완료되었습니다."))
            return

        # 범위 집계
        if raw_start or raw_end:
            if not (raw_start and raw_end):
                raise CommandError("범위 집계를 위해서는 `--start-date`와 `--end-date`를 모두 지정해야 합니다.")
            start = self._parse_date(raw_start, flag_name="--start-date")
            end = self._parse_date(raw_end, flag_name="--end-date")
            if start > end:
                raise CommandError("`--start-date`는 `--end-date`보다 이후일 수 없습니다.")

            self.stdout.write(
                self.style.NOTICE(
                    f"[집계 시작] {start} ~ {end} 비즈니스 일간 집계 실행",
                )
            )
            aggregate_biz_daily_for_range(start, end)
            self.stdout.write(
                self.style.SUCCESS(
                    f"[집계 완료] {start} ~ {end} 비즈니스 일간 집계가 완료되었습니다.",
                )
            )
            return

        # 아무 인자도 없는 경우: 어제 날짜 기준으로 집계
        yesterday = timezone.localdate() - timedelta(days=1)
        self.stdout.write(self.style.NOTICE(f"[집계 시작] 인자가 없어 어제 날짜({yesterday})로 집계를 수행합니다."))
        aggregate_biz_daily_for_date(yesterday)
        self.stdout.write(self.style.SUCCESS(f"[집계 완료] {yesterday} 비즈니스 일간 집계가 완료되었습니다."))

    def _parse_date(self, value: str, flag_name: str) -> date:
        """YYYY-MM-DD 형식 문자열을 date 객체로 변환"""
        try:
            dt = datetime.strptime(value, "%Y-%m-%d")
            return dt.date()
        except ValueError as exc:
            raise CommandError(f"{flag_name} 값이 올바른 날짜 형식이 아닙니다. (예: 2025-03-01)") from exc


