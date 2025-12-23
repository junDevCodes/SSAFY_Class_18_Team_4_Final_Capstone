"""
Admin 분석용 API 뷰

Top Line 대시보드에서 사용할 일간 비즈니스 집계 데이터를 제공한다.
"""

from __future__ import annotations

from datetime import datetime

from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from analytics.models import AdminBizDaily, UserSegment
from analytics.serializers import AnalyticsOverviewSerializer


class AdminAnalyticsOverviewView(APIView):
    """
    관리자용 통합 지표 조회 API

    - 경로: /api/admin/analytics/overview/
    - 기능: AdminBizDaily 집계 테이블을 기반으로 Top Line 지표를 반환
    """

    def get(self, request, *args, **kwargs):
        """쿼리 파라미터를 해석하고 집계 결과를 반환"""
        params = request.query_params
        raw_start = params.get("start_date")
        raw_end = params.get("end_date")
        segment = params.get("segment", UserSegment.ALL)
        # granularity, region 등은 현재 구현에서 직접 사용하지 않지만
        # 향후 확장을 위해 파라미터로만 받아둔다.
        _granularity = params.get("granularity", "daily")
        _region = params.get("region")

        if not raw_start or not raw_end:
            return Response(
                {"detail": "start_date와 end_date를 모두 지정해야 합니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            start_date = datetime.strptime(raw_start, "%Y-%m-%d").date()
            end_date = datetime.strptime(raw_end, "%Y-%m-%d").date()
        except ValueError:
            return Response(
                {"detail": "날짜 형식이 올바르지 않습니다. YYYY-MM-DD 형식을 사용하세요."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if start_date > end_date:
            return Response(
                {"detail": "start_date는 end_date보다 이후일 수 없습니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 세그먼트 값이 유효하지 않은 경우 기본값(all)로 강제
        if segment not in {UserSegment.ALL, UserSegment.CONSUMER, UserSegment.SELLER}:
            segment = UserSegment.ALL

        overview_data = self._build_overview(start_date, end_date, segment)
        serializer = AnalyticsOverviewSerializer(overview_data)
        return Response(serializer.data)

    def _build_overview(self, start_date, end_date, segment: str) -> dict:
        """
        AdminBizDaily 데이터를 기반으로 AnalyticsOverview 응답을 구성

        - 현재는 Top Line 지표만 채우고 breakdown/heatmap/keywords 는 비워둔다.
        """
        qs = (
            AdminBizDaily.objects.filter(
                date__range=(start_date, end_date),
                user_segment=segment,
            )
            .order_by("date")
        )

        # 비어 있는 경우에도 API 스키마는 유지
        if not qs.exists():
            return {
                "kpis": [],
                "trend": {"source": []},
                "breakdown": {"product": []},
                "heatmap": [],
                "keywords": [],
            }

        # ----- Trend: 일 단위 추이 데이터 구성 -----
        trend_source = []
        total_orders = 0
        total_gmv = 0
        total_buyers = 0

        for row in qs:
            total_orders += int(row.orders)
            total_gmv += int(row.gmv)
            total_buyers += int(row.unique_buyers)

            # 세션 로그가 아직 없으므로 conversion 은 구매자 수 기준 근사치로 계산
            buyers = row.unique_buyers or 0
            if buyers > 0:
                conversion = (row.orders / buyers) * 100.0
            else:
                conversion = 0.0

            trend_source.append(
                {
                    "date": row.date.isoformat(),
                    "sessions": int(row.sessions),
                    "orders": int(row.orders),
                    "conversion": float(round(conversion, 2)),
                    "revenue": int(row.gmv),
                }
            )

        # ----- KPI 요약 지표 구성 -----
        # 전체 기간 기준으로 AOV/전환율을 계산
        if total_orders > 0:
            aov = total_gmv / total_orders
        else:
            aov = 0.0

        if total_buyers > 0:
            conv_rate = (total_orders / total_buyers) * 100.0
        else:
            conv_rate = 0.0

        kpis = [
            {
                "label": "총 매출(GMV)",
                "value": float(total_gmv),
                "delta": 0.0,
                "unit": "원",
            },
            {
                "label": "주문 수",
                "value": float(total_orders),
                "delta": 0.0,
                "unit": None,
            },
            {
                "label": "객단가(AOV)",
                "value": float(round(aov, 2)),
                "delta": 0.0,
                "unit": "원",
            },
            {
                "label": "전환율",
                "value": float(round(conv_rate, 2)),
                "delta": 0.0,
                "unit": "%",
            },
        ]

        # breakdown/trend 의 다른 탭은 추후 확장을 위해 비워둔다.
        overview = {
            "kpis": kpis,
            "trend": {
                "source": trend_source,
            },
            "breakdown": {
                "product": [],
            },
            "heatmap": [],
            "keywords": [],
        }

        return overview


