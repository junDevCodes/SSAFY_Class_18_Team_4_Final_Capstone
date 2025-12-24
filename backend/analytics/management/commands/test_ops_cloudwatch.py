"""
EC2 기반 CloudWatch 운영 지표 연동 테스트 커맨드

예시:
    python manage.py test_ops_cloudwatch --range 1h
    python manage.py test_ops_cloudwatch --range 7d
"""

from __future__ import annotations

from datetime import datetime, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from analytics.ops_metrics import get_ops_timeseries


class Command(BaseCommand):
    help = "CloudWatch 설정이 올바른지 확인하기 위해 EC2 기반 운영 지표를 한번 조회해 봅니다."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--range",
            type=str,
            choices=["1h", "7d", "30d"],
            default="1h",
            help="조회 범위 (기본: 1h)",
        )

    def handle(self, *args, **options) -> None:
        range_key: str = options["range"]
        now = timezone.now()

        if range_key == "1h":
            start = now - timedelta(hours=1)
        elif range_key == "7d":
            start = now - timedelta(days=7)
        else:
            start = now - timedelta(days=30)

        self.stdout.write(
            self.style.NOTICE(
                f"[CloudWatch 테스트] 범위: {start.isoformat()} ~ {now.isoformat()}"
            )
        )

        timeseries, backend_used = get_ops_timeseries(start, now)

        self.stdout.write(self.style.SUCCESS(f"- 사용된 백엔드: {backend_used}"))
        self.stdout.write(self.style.SUCCESS(f"- 수신 포인트 수: {len(timeseries)}"))

        if not timeseries:
            self.stdout.write(self.style.WARNING("시계열 데이터가 비어 있습니다."))
            return

        # 앞/뒤 몇 개만 샘플로 출력
        head = timeseries[:3]
        tail = timeseries[-3:] if len(timeseries) > 3 else []

        def _fmt_point(p: dict) -> str:
            ts = p.get("timestamp")
            if isinstance(ts, datetime):
                ts_str = ts.isoformat()
            else:
                ts_str = str(ts)
            return (
                f"{ts_str} | crawl={p.get('crawling_success_rate')} "
                f"cpu={p.get('api_p95_ms')} "
                f"net={p.get('error_rate')} "
                f"avail={p.get('availability')}"
            )

        self.stdout.write(self.style.NOTICE("=== 앞쪽 샘플 ==="))
        for p in head:
            self.stdout.write(f"  { _fmt_point(p) }")

        if tail:
            self.stdout.write(self.style.NOTICE("=== 뒤쪽 샘플 ==="))
            for p in tail:
                self.stdout.write(f"  { _fmt_point(p) }")


