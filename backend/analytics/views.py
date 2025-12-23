"""
Admin 분석용 API 뷰

Top Line 대시보드에서 사용할 일간 비즈니스 집계 데이터를 제공한다.
"""

from __future__ import annotations

from datetime import datetime

from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from analytics.models import AdminBizDaily, AdminRecoDaily, AdminCategoryDaily, UserSegment
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

        # ----- KPI 요약 지표 구성 (Top Line) -----
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

        # ----- 추천 KPI (홈 기준) 구성 -----
        reco_qs = AdminRecoDaily.objects.filter(
            date__range=(start_date, end_date),
            user_segment=segment,
            placement="home",
        )

        total_impressions = 0
        total_clicks = 0
        total_attr_orders = 0
        total_attr_gmv = 0

        for reco in reco_qs:
            total_impressions += int(reco.reco_impressions)
            total_clicks += int(reco.reco_clicks)
            total_attr_orders += int(reco.reco_attributed_orders)
            total_attr_gmv += int(reco.reco_attributed_gmv)

        if total_impressions > 0:
            home_ctr = (total_clicks / total_impressions) * 100.0
        else:
            home_ctr = 0.0

        if total_clicks > 0:
            home_purchase_conv = (total_attr_orders / total_clicks) * 100.0
        else:
            home_purchase_conv = 0.0

        if total_gmv > 0:
            home_reco_gmv_share = (total_attr_gmv / total_gmv) * 100.0
        else:
            home_reco_gmv_share = 0.0

        kpis.extend(
            [
                {
                    "label": "홈 추천 CTR",
                    "value": float(round(home_ctr, 2)),
                    "delta": 0.0,
                    "unit": "%",
                },
                {
                    "label": "홈 추천 구매 전환율",
                    "value": float(round(home_purchase_conv, 2)),
                    "delta": 0.0,
                    "unit": "%",
                },
                {
                    "label": "홈 추천 기여 GMV 비율",
                    "value": float(round(home_reco_gmv_share, 2)),
                    "delta": 0.0,
                    "unit": "%",
                },
            ]
        )

        # ----- 카테고리별 성과 분해 (CategoryDaily) -----
        cat_qs = AdminCategoryDaily.objects.filter(
            date__range=(start_date, end_date),
            user_segment=segment,
        )
        category_breakdown: list[dict] = []
        if cat_qs.exists():
            agg_by_cat: dict[str, dict] = {}
            for row in cat_qs:
                bucket = agg_by_cat.setdefault(
                    row.category_name,
                    {"sessions": 0, "orders": 0, "gmv": 0},
                )
                bucket["sessions"] += int(row.sessions)
                bucket["orders"] += int(row.orders)
                bucket["gmv"] += int(row.gmv)

            for name, bucket in agg_by_cat.items():
                sessions = bucket["sessions"]
                orders = bucket["orders"]
                gmv = bucket["gmv"]
                if sessions > 0:
                    conversion = (orders / sessions) * 100.0
                else:
                    conversion = 0.0
                category_breakdown.append(
                    {
                        "name": name,
                        "sessions": sessions,
                        "orders": orders,
                        "conversion": float(round(conversion, 2)),
                        "revenue": float(gmv),
                    }
                )

        overview = {
            "kpis": kpis,
            "trend": {
                "source": trend_source,
            },
            "breakdown": {
                "product": category_breakdown,
            },
            "heatmap": [],
            "keywords": [],
        }

        return overview


class AdminRecommendationTrendView(APIView):
    """
    관리자용 추천 성과 추이 API

    - 경로: /api/admin/analytics/recommendation/trend/
    - 기능: AdminRecoDaily + AdminBizDaily 를 기반으로 홈 추천 CTR/구매 전환율/기여 GMV 비율 일간 추이를 반환
    """

    def get(self, request, *args, **kwargs):
        """추천 성과 일간 추이를 반환 (placement 필터 지원)"""
        params = request.query_params
        raw_start = params.get("start_date")
        raw_end = params.get("end_date")
        segment = params.get("segment", UserSegment.ALL)
        _granularity = params.get("granularity", "daily")
        placement = params.get("placement", "home")

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

        # 현재는 일간 집계만 지원 (granularity 는 향후 확장용 파라미터)
        series = self._build_daily_series(start_date, end_date, segment, placement)
        return Response({"series": series})

    def _build_daily_series(
        self, start_date, end_date, segment: str, placement: str
    ) -> list[dict]:
        """일 단위로 추천/비즈니스 집계를 결합해 추이 시계열을 생성

        placement:
            - 'home': 홈 추천 기준
            - 'all': 모든 placement 집계
            - 기타: 해당 placement 만 필터링 (price_model, personalized, gapfill 등)
        """
        # 날짜별 전체 GMV 맵 생성 (추천 기여 비율 계산용)
        biz_qs = AdminBizDaily.objects.filter(
            date__range=(start_date, end_date),
            user_segment=segment,
        ).values("date", "gmv")
        gmv_by_date: dict = {row["date"]: int(row["gmv"]) for row in biz_qs}

        # 추천 집계
        reco_qs = AdminRecoDaily.objects.filter(
            date__range=(start_date, end_date),
            user_segment=segment,
        )
        if placement != "all":
            reco_qs = reco_qs.filter(placement=placement)

        # 날짜별로 합산
        stats_by_date: dict = {}
        for reco in reco_qs:
            bucket = stats_by_date.setdefault(
                reco.date,
                {
                    "impressions": 0,
                    "clicks": 0,
                    "attributed_orders": 0,
                    "attributed_gmv": 0,
                },
            )
            bucket["impressions"] += int(reco.reco_impressions)
            bucket["clicks"] += int(reco.reco_clicks)
            bucket["attributed_orders"] += int(reco.reco_attributed_orders)
            bucket["attributed_gmv"] += int(reco.reco_attributed_gmv)

        series: list[dict] = []

        for day in sorted(stats_by_date.keys()):
            bucket = stats_by_date[day]
            impressions = bucket["impressions"]
            clicks = bucket["clicks"]
            attr_orders = bucket["attributed_orders"]
            attr_gmv = bucket["attributed_gmv"]

            if impressions > 0:
                ctr = (clicks / impressions) * 100.0
            else:
                ctr = 0.0

            if clicks > 0:
                purchase_conv = (attr_orders / clicks) * 100.0
            else:
                purchase_conv = 0.0

            total_gmv_for_date = gmv_by_date.get(day, 0)
            if total_gmv_for_date > 0:
                gmv_share = (attr_gmv / total_gmv_for_date) * 100.0
            else:
                gmv_share = 0.0

            series.append(
                {
                    "date": day.isoformat(),
                    "impressions": impressions,
                    "clicks": clicks,
                    "attributed_orders": attr_orders,
                    "attributed_gmv": attr_gmv,
                    "ctr": float(round(ctr, 2)),
                    "purchase_conversion": float(round(purchase_conv, 2)),
                    "gmv_share": float(round(gmv_share, 2)),
                    "total_gmv": int(total_gmv_for_date),
                }
            )

        return series


class AdminRecommendationPlacementSummaryView(APIView):
    """
    추천 placement 별 집계 요약 API

    - 경로: /api/admin/analytics/recommendation/placement-summary/
    - 기능: AdminRecoDaily + AdminBizDaily 를 기반으로
      placement 별 CTR/구매 전환율/기여 GMV 비율을 집계
    """

    def get(self, request, *args, **kwargs):
        params = request.query_params
        raw_start = params.get("start_date")
        raw_end = params.get("end_date")
        segment = params.get("segment", UserSegment.ALL)
        _granularity = params.get("granularity", "daily")

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

        if segment not in {UserSegment.ALL, UserSegment.CONSUMER, UserSegment.SELLER}:
            segment = UserSegment.ALL

        payload = self._build_summary(start_date, end_date, segment)
        return Response(payload)

    def _build_summary(self, start_date, end_date, segment: str) -> dict:
        """기간/세그먼트 기준 placement 별 집계 결과 생성"""
        # 총 GMV (해당 세그먼트) 집계
        biz_qs = AdminBizDaily.objects.filter(
            date__range=(start_date, end_date),
            user_segment=segment,
        )
        total_gmv = 0
        for row in biz_qs:
            total_gmv += int(row.gmv)

        # 추천 집계 (home placement 는 제외하고 알고리즘별 placement 만 집계)
        reco_qs = AdminRecoDaily.objects.filter(
            date__range=(start_date, end_date),
            user_segment=segment,
        ).exclude(placement="home")

        placement_stats: dict[str, dict] = {}
        for reco in reco_qs:
            key = reco.placement
            if key not in placement_stats:
                placement_stats[key] = {
                    "placement": key,
                    "impressions": 0,
                    "clicks": 0,
                    "attributed_orders": 0,
                    "attributed_gmv": 0,
                }
            bucket = placement_stats[key]
            bucket["impressions"] += int(reco.reco_impressions)
            bucket["clicks"] += int(reco.reco_clicks)
            bucket["attributed_orders"] += int(reco.reco_attributed_orders)
            bucket["attributed_gmv"] += int(reco.reco_attributed_gmv)

        # placement 별 파생 지표 계산
        results: list[dict] = []
        total_impr = 0
        total_clicks = 0
        total_attr_orders = 0
        total_attr_gmv = 0

        for key, bucket in placement_stats.items():
            impressions = bucket["impressions"]
            clicks = bucket["clicks"]
            attr_orders = bucket["attributed_orders"]
            attr_gmv = bucket["attributed_gmv"]

            total_impr += impressions
            total_clicks += clicks
            total_attr_orders += attr_orders
            total_attr_gmv += attr_gmv

            if impressions > 0:
                ctr = (clicks / impressions) * 100.0
            else:
                ctr = 0.0

            if clicks > 0:
                purchase_conv = (attr_orders / clicks) * 100.0
            else:
                purchase_conv = 0.0

            if total_gmv > 0:
                gmv_share = (attr_gmv / total_gmv) * 100.0
            else:
                gmv_share = 0.0

            results.append(
                {
                    "placement": key,
                    "impressions": impressions,
                    "clicks": clicks,
                    "attributed_orders": attr_orders,
                    "attributed_gmv": attr_gmv,
                    "ctr": float(round(ctr, 2)),
                    "purchase_conversion": float(round(purchase_conv, 2)),
                    "gmv_share": float(round(gmv_share, 2)),
                }
            )

        # placement 전체 통합(all) 행 추가
        if total_impr > 0:
            all_ctr = (total_clicks / total_impr) * 100.0
        else:
            all_ctr = 0.0

        if total_clicks > 0:
            all_purchase_conv = (total_attr_orders / total_clicks) * 100.0
        else:
            all_purchase_conv = 0.0

        if total_gmv > 0:
            all_gmv_share = (total_attr_gmv / total_gmv) * 100.0
        else:
            all_gmv_share = 0.0

        results.append(
            {
                "placement": "all",
                "impressions": total_impr,
                "clicks": total_clicks,
                "attributed_orders": total_attr_orders,
                "attributed_gmv": total_attr_gmv,
                "ctr": float(round(all_ctr, 2)),
                "purchase_conversion": float(round(all_purchase_conv, 2)),
                "gmv_share": float(round(all_gmv_share, 2)),
            }
        )

        return {"placements": results}


