"""
Admin 분석용 API 뷰

Top Line 대시보드에서 사용할 일간 비즈니스 집계 데이터를 제공한다.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from analytics.models import AdminBizDaily, AdminRecoDaily, AdminCategoryDaily, UserSegment
from analytics.serializers import (
    AnalyticsOverviewSerializer,
    BehaviorOverviewSerializer,
    OpsOverviewSerializer,
)
from analytics.ops_metrics import get_ops_timeseries
from drf_spectacular.utils import extend_schema


def _parse_data_mode(raw: str | None) -> str:
    """
    테스트/실데이터 포함 범위를 해석한다.

    - all: 테스트 + 실데이터
    - real: 실데이터만 (is_test=False)
    """
    if raw not in {"all", "real"}:
        return "all"
    return raw


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
        data_mode = _parse_data_mode(params.get("data_mode"))
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

        overview_data = self._build_overview(
            start_date, end_date, segment, include_test=(data_mode == "all")
        )
        serializer = AnalyticsOverviewSerializer(overview_data)
        return Response(serializer.data)

    def _build_overview(
        self, start_date, end_date, segment: str, include_test: bool
    ) -> dict:
        """
        AdminBizDaily 데이터를 기반으로 AnalyticsOverview 응답을 구성

        - 현재는 Top Line 지표만 채우고 breakdown/heatmap/keywords 는 비워둔다.
        """
        qs = AdminBizDaily.objects.filter(
            date__range=(start_date, end_date),
            user_segment=segment,
        )
        if not include_test:
            qs = qs.filter(is_test=False)
        qs = qs.order_by("date")

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
        total_cart_adds = 0

        for row in qs:
            total_orders += int(row.orders)
            total_gmv += int(row.gmv)
            total_buyers += int(row.unique_buyers)
            total_cart_adds += int(row.cart_adds)

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
        # 전체 기간 기준으로 AOV/전환율/장바구니 전환율을 계산
        if total_orders > 0:
            aov = total_gmv / total_orders
        else:
            aov = 0.0

        if total_buyers > 0:
            conv_rate = (total_orders / total_buyers) * 100.0
        else:
            conv_rate = 0.0

        if total_cart_adds > 0:
            cart_conversion_rate = (total_orders / total_cart_adds) * 100.0
        else:
            cart_conversion_rate = 0.0

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
            {
                "label": "장바구니→구매 전환율",
                "value": float(round(cart_conversion_rate, 2)),
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
        if not include_test:
            reco_qs = reco_qs.filter(is_test=False)

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
        if not include_test:
            cat_qs = cat_qs.filter(is_test=False)
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


class AdminBehaviorOverviewView(APIView):
    """
    관리자용 유저 행동(Behavior) 지표 API

    - 경로: /api/admin/analytics/behavior/
    - 기능: AdminBizDaily 집계를 기반으로 DAU/MAU, 장바구니 전환율 등 행동 지표를 제공
    """

    def get(self, request, *args, **kwargs):
        params = request.query_params
        raw_start = params.get("start_date")
        raw_end = params.get("end_date")
        segment = params.get("segment", UserSegment.ALL)
        data_mode = _parse_data_mode(params.get("data_mode"))

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

        qs = AdminBizDaily.objects.filter(
            date__range=(start_date, end_date),
            user_segment=segment,
        )
        if data_mode == "real":
            qs = qs.filter(is_test=False)
        qs = qs.order_by("date")

        if not qs.exists():
            empty_payload = {
                "kpis": [],
                "trend": [],
                "funnels": [],
                "cohorts": [],
            }
            serializer = BehaviorOverviewSerializer(empty_payload)
            return Response(serializer.data)

        trend = []
        total_sessions = 0
        total_buyers = 0
        total_cart_adds = 0
        total_orders = 0
        num_days = 0

        for row in qs:
            sessions = int(row.sessions)
            buyers = int(row.unique_buyers)
            cart_adds = int(row.cart_adds)
            orders = int(row.orders)

            num_days += 1
            total_sessions += sessions
            total_buyers += buyers
            total_cart_adds += cart_adds
            total_orders += orders

            if cart_adds > 0:
                cart_to_order_rate = (orders / cart_adds) * 100.0
            else:
                cart_to_order_rate = 0.0

            trend.append(
                {
                    "date": row.date.isoformat(),
                    "buyers": buyers,
                    "cart_adds": cart_adds,
                    "orders": orders,
                    "cart_to_order_rate": float(round(cart_to_order_rate, 2)),
                    "sessions": sessions,
                }
            )

        # 집계 기준 KPI 계산 (단순 합/평균 기반, 전기간 대비 증감률은 0으로 둔다)
        if num_days > 0:
            dau_estimate = total_buyers / num_days
        else:
            dau_estimate = 0.0

        mau_estimate = float(total_buyers)

        if total_cart_adds > 0:
            cart_to_order_conversion = (total_orders / total_cart_adds) * 100.0
        else:
            cart_to_order_conversion = 0.0

        cart_abandon_rate = max(0.0, 100.0 - cart_to_order_conversion)

        kpis = [
            {
                "label": "구매 DAU(추정)",
                "value": float(round(dau_estimate, 2)),
                "delta": 0.0,
                "unit": "명",
            },
            {
                "label": "구매 MAU(합산 기준 추정)",
                "value": float(round(mau_estimate, 2)),
                "delta": 0.0,
                "unit": "명",
            },
            {
                "label": "장바구니→구매 전환율",
                "value": float(round(cart_to_order_conversion, 2)),
                "delta": 0.0,
                "unit": "%",
            },
            {
                "label": "장바구니 포기율(추정)",
                "value": float(round(cart_abandon_rate, 2)),
                "delta": 0.0,
                "unit": "%",
            },
        ]

        funnels = []
        if total_sessions > 0 or total_cart_adds > 0 or total_orders > 0:
            funnels.append(
                {
                    "name": "세션",
                    "value": int(total_sessions),
                    "rate": None,
                }
            )
            funnels.append(
                {
                    "name": "장바구니 담기",
                    "value": int(total_cart_adds),
                    "rate": float(
                        round(
                            (total_cart_adds / total_sessions) * 100.0,
                            2,
                        )
                    )
                    if total_sessions > 0
                    else 0.0,
                }
            )
            funnels.append(
                {
                    "name": "구매 완료",
                    "value": int(total_orders),
                    "rate": float(
                        round(
                            (total_orders / max(total_cart_adds, 1)) * 100.0,
                            2,
                        )
                    )
                    if total_cart_adds > 0
                    else 0.0,
                }
            )

        payload = {
            "kpis": kpis,
            "trend": trend,
            "funnels": funnels,
            "cohorts": [],
        }
        serializer = BehaviorOverviewSerializer(payload)
        return Response(serializer.data)


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
        data_mode = _parse_data_mode(params.get("data_mode"))

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
        series = self._build_daily_series(
            start_date, end_date, segment, placement, data_mode
        )
        return Response({"series": series})

    def _build_daily_series(
        self, start_date, end_date, segment: str, placement: str, data_mode: str
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
        )
        if data_mode == "real":
            biz_qs = biz_qs.filter(is_test=False)
        biz_qs = biz_qs.values("date", "gmv")
        gmv_by_date: dict = {row["date"]: int(row["gmv"]) for row in biz_qs}

        # 추천 집계
        reco_qs = AdminRecoDaily.objects.filter(
            date__range=(start_date, end_date),
            user_segment=segment,
        )
        if placement != "all":
            reco_qs = reco_qs.filter(placement=placement)
        if data_mode == "real":
            reco_qs = reco_qs.filter(is_test=False)

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
        data_mode = _parse_data_mode(params.get("data_mode"))

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

        payload = self._build_summary(start_date, end_date, segment, data_mode)
        return Response(payload)

    def _build_summary(
        self, start_date, end_date, segment: str, data_mode: str
    ) -> dict:
        """기간/세그먼트 기준 placement 별 집계 결과 생성"""
        # 총 GMV (해당 세그먼트) 집계
        biz_qs = AdminBizDaily.objects.filter(
            date__range=(start_date, end_date),
            user_segment=segment,
        )
        if data_mode == "real":
            biz_qs = biz_qs.filter(is_test=False)
        total_gmv = 0
        for row in biz_qs:
            total_gmv += int(row.gmv)

        # 추천 집계 (home placement 는 제외하고 알고리즘별 placement 만 집계)
        reco_qs = AdminRecoDaily.objects.filter(
            date__range=(start_date, end_date),
            user_segment=segment,
        ).exclude(placement="home")
        if data_mode == "real":
            reco_qs = reco_qs.filter(is_test=False)

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


class AdminOpsOverviewView(APIView):
    """
    운영 건강도 요약 API (초기 버전은 mock 데이터 반환)

    - 경로: /api/admin/analytics/ops/
    - 기능: 크롤링 성공률, API 응답시간, 에러율, 가용성 등의 지표를 요약
    """

    def get(self, request, *args, **kwargs):
        # 쿼리 파라미터 (날짜/시스템/범위 필터)
        raw_start = request.query_params.get("start_date")
        raw_end = request.query_params.get("end_date")
        range_key = request.query_params.get("range")
        system_filter = request.query_params.get("system", "all")

        now = timezone.now()

        # range 파라미터가 있으면 우선 사용 (최근 1시간 / 7일 / 30일)
        if range_key in {"1h", "7d", "30d"}:
            if range_key == "1h":
                start_dt = now - timedelta(hours=1)
            elif range_key == "7d":
                start_dt = now - timedelta(days=7)
            else:  # "30d"
                start_dt = now - timedelta(days=30)
            end_dt = now
        else:
            # 날짜 파싱 (없으면 최근 7일)
            try:
                if raw_start and raw_end:
                    start_date = datetime.strptime(raw_start, "%Y-%m-%d").date()
                    end_date = datetime.strptime(raw_end, "%Y-%m-%d").date()
                else:
                    today = timezone.localdate()
                    end_date = today
                    start_date = today - timedelta(days=6)
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

            start_dt = timezone.make_aware(
                datetime.combine(start_date, datetime.min.time())
            )
            end_dt = timezone.make_aware(
                datetime.combine(end_date, datetime.max.time())
            )

        # 운영 지표 시계열 (환경 기반: mock / cloudwatch)
        timeseries, backend_used = get_ops_timeseries(start_dt, end_dt)
        if not timeseries:
            return Response(
                {"detail": "운영 지표를 조회할 수 없습니다."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        latest = timeseries[-1]

        kpis = [
            {
                "label": "크롤링 성공률",
                "value": latest["crawling_success_rate"],
                "delta": 0.0,
                "unit": "%",
            },
            {
                "label": "EC2 CPU 사용률",
                "value": latest["api_p95_ms"],
                "delta": 0.0,
                "unit": "%",
            },
            {
                "label": "네트워크 트래픽 (In)",
                "value": latest["error_rate"],
                "delta": 0.0,
                "unit": "bps",
            },
            {
                "label": "서비스 가용성",
                "value": latest["availability"],
                "delta": 0.0,
                "unit": "%",
            },
        ]

        # 메트릭 기반 Incident 동적 생성 (EC2 모니터링 기준)
        incidents: list[dict] = []

        # 시계열 데이터에서 이상 패턴 탐지 (최근 7일 이상의 데이터가 있을 경우)
        if len(timeseries) >= 7:
            # 평균값 계산 (전체 기간)
            avg_cpu = sum(p["api_p95_ms"] for p in timeseries) / len(timeseries)
            avg_network = sum(p["error_rate"] for p in timeseries) / len(timeseries)
            avg_crawl = sum(p["crawling_success_rate"] for p in timeseries) / len(timeseries)
            avg_avail = sum(p["availability"] for p in timeseries) / len(timeseries)

            # 1. CPU 과부하 장애 (90% 이상 지속 구간 탐지)
            cpu_high_windows = []
            for i, point in enumerate(timeseries):
                if point["api_p95_ms"] >= 90.0:
                    cpu_high_windows.append((i, point))

            if len(cpu_high_windows) >= 2:  # 2포인트 이상 연속 고부하
                first_idx, first_point = cpu_high_windows[0]
                last_idx, last_point = cpu_high_windows[-1]

                # 연속된 구간인지 확인 (인덱스 차이가 윈도우 크기 이내)
                if last_idx - first_idx <= len(cpu_high_windows):
                    inc_id = f"INC-CPU-{int(first_point['timestamp'].timestamp())}"
                    incidents.append({
                        "id": inc_id,
                        "severity": "high",
                        "category": "infra",
                        "code": "INC_EC2_CPU_OVERLOAD",
                        "service": "ec2_instance",
                        "title": "EC2 CPU 과부하 장애",
                        "description": f"EC2 인스턴스 CPU 사용률이 90% 이상으로 {len(cpu_high_windows)}개 구간 동안 지속되었습니다. 트래픽 급증 또는 배치 작업 이슈로 추정됩니다.",
                        "started_at": first_point["timestamp"],
                        "resolved_at": last_point["timestamp"] if last_point["api_p95_ms"] < 80.0 else None,
                    })

            # 2. 네트워크 트래픽 급증 (평균 대비 3배 이상)
            if avg_network > 0:
                network_spike_windows = []
                for i, point in enumerate(timeseries):
                    if point["error_rate"] >= avg_network * 3.0:
                        network_spike_windows.append((i, point))

                if len(network_spike_windows) >= 1:
                    first_idx, first_point = network_spike_windows[0]
                    last_idx, last_point = network_spike_windows[-1]

                    inc_id = f"INC-NET-{int(first_point['timestamp'].timestamp())}"

                    # bps -> MB/s 변환
                    spike_mbps = last_point["error_rate"] / (8.0 * 1024 * 1024)

                    incidents.append({
                        "id": inc_id,
                        "severity": "medium",
                        "category": "infra",
                        "code": "INC_NETWORK_TRAFFIC_SPIKE",
                        "service": "ec2_network",
                        "title": "네트워크 트래픽 급증",
                        "description": f"EC2 네트워크 In 트래픽이 평균 대비 {(last_point['error_rate'] / avg_network):.1f}배 급증했습니다 (최대: {spike_mbps:.1f} MB/s). DDoS 공격, 크롤러 배치 작업, 또는 대용량 파일 전송 등을 점검하세요.",
                        "started_at": first_point["timestamp"],
                        "resolved_at": last_point["timestamp"] if last_point["error_rate"] < avg_network * 2.0 else None,
                    })

            # 3. 크롤링 성공률 저하 (95% 미만 지속)
            crawl_low_windows = []
            for i, point in enumerate(timeseries):
                if point["crawling_success_rate"] < 95.0:
                    crawl_low_windows.append((i, point))

            if len(crawl_low_windows) >= 2:
                first_idx, first_point = crawl_low_windows[0]
                last_idx, last_point = crawl_low_windows[-1]

                inc_id = f"INC-CRAWL-{int(first_point['timestamp'].timestamp())}"
                incidents.append({
                    "id": inc_id,
                    "severity": "high",
                    "category": "crawler",
                    "code": "INC_CRAWLER_SUCCESS_LOW",
                    "service": "crawler_service",
                    "title": "크롤링 성공률 저하",
                    "description": f"크롤링 성공률이 {last_point['crawling_success_rate']:.1f}%로 하락했습니다. 외부 사이트 차단, 응답 지연, 또는 크롤러 로직 오류가 발생했을 가능성이 있습니다.",
                    "started_at": first_point["timestamp"],
                    "resolved_at": last_point["timestamp"] if last_point["crawling_success_rate"] >= 97.0 else None,
                })

            # 4. 서비스 가용성 저하 (98% 미만)
            avail_low_windows = []
            for i, point in enumerate(timeseries):
                if point["availability"] < 98.0:
                    avail_low_windows.append((i, point))

            if len(avail_low_windows) >= 1:
                first_idx, first_point = avail_low_windows[0]
                last_idx, last_point = avail_low_windows[-1]

                inc_id = f"INC-AVAIL-{int(first_point['timestamp'].timestamp())}"
                incidents.append({
                    "id": inc_id,
                    "severity": "high",
                    "category": "infra",
                    "code": "INC_AVAILABILITY_DEGRADED",
                    "service": "platform",
                    "title": "서비스 가용성 저하",
                    "description": f"서비스 가용성이 {last_point['availability']:.2f}%로 하락했습니다. 배포, 인프라 장애, 또는 외부 의존성 이슈를 점검하세요.",
                    "started_at": first_point["timestamp"],
                    "resolved_at": last_point["timestamp"] if last_point["availability"] >= 99.5 else None,
                })

        # 데이터가 부족하거나 이상 패턴이 없는 경우 빈 리스트 유지

        # 리스크 알림 및 To-do 규칙 구성 (metric/incident 기반 정규화 로직)
        alerts: list[dict] = []
        todos: list[dict] = []

        metric_snapshot = {
            "crawling_success_rate": latest["crawling_success_rate"],
            "api_p95_ms": latest["api_p95_ms"],
            "error_rate": latest["error_rate"],
            "availability": latest["availability"],
        }

        # 메트릭 기반 알림 규칙 정의 (EC2 + 크롤링 지표 기준)
        metric_alert_rules: list[dict] = [
            {
                "id": "crawl-success-low",
                "code": "ALERT_CRAWLER_SUCCESS_LOW",
                "category": "crawler",
                "metric_key": "crawling_success_rate",
                "metric_unit": "%",
                "metric_format": "percent_2",
                "title": "크롤링 성공률 저하",
                "description": "크롤링 실패율이 증가하고 있습니다. 크롤러 로그와 외부 사이트 상태를 점검하세요.",
                "severities": [
                    {"name": "high", "operator": "lt", "threshold": 97.0},
                    {"name": "medium", "operator": "lt", "threshold": 98.0},
                ],
                "todo": {
                    "id": "todo-crawl-check",
                    "code": "TODO_CRAWLER_CHECK",
                    "title": "크롤러 실패 구간 점검",
                    "description": "실패율이 높은 소스/카테고리를 확인하고, 차단/응답 지연 여부를 점검합니다.",
                    "meta": "담당: 데이터 엔지니어 · 우선순위: 상",
                    "priority": "high",
                },
            },
            {
                "id": "ec2-cpu-high",
                "code": "ALERT_EC2_CPU_HIGH",
                "category": "infra",
                "metric_key": "api_p95_ms",  # EC2 CPUUtilization(%) 으로 매핑됨
                "metric_unit": "%",
                "metric_format": "percent_1",
                "title": "EC2 CPU 사용률 상승",
                "description": "EC2 인스턴스 CPU 사용률이 높습니다. 스케일 아웃 또는 쿼리/태스크 튜닝을 검토하세요.",
                "severities": [
                    {"name": "high", "operator": "gt", "threshold": 80.0},
                    {"name": "medium", "operator": "gt", "threshold": 60.0},
                ],
                "todo": {
                    "id": "todo-ec2-cpu-review",
                    "code": "TODO_EC2_CPU_REVIEW",
                    "title": "EC2 CPU 부하 분석",
                    "description": "CPU가 많이 사용되는 시간대와 프로세스를 파악하고, 스케일 아웃 또는 튜닝 방안을 검토합니다.",
                    "meta": "담당: 백엔드/Infra · 우선순위: 중",
                    "priority": "medium",
                },
            },
            {
                "id": "network-traffic-high",
                "code": "ALERT_NETWORK_IN_HIGH",
                "category": "infra",
                "metric_key": "error_rate",  # NetworkIn Bytes 로 매핑됨
                "metric_unit": "Bytes",
                "metric_format": "bytes_auto",
                "title": "네트워크 트래픽 과다",
                "description": "EC2 인스턴스의 네트워크 In 트래픽이 평소보다 높습니다. 이상 호출 또는 배치 작업 여부를 점검하세요.",
                "severities": [
                    # 평균 8MB 이상이면 high, 4MB 이상이면 medium (대략적인 기준)
                    {
                        "name": "high",
                        "operator": "gt",
                        "threshold": float(8 * 1024 * 1024),
                    },
                    {
                        "name": "medium",
                        "operator": "gt",
                        "threshold": float(4 * 1024 * 1024),
                    },
                ],
                "todo": {
                    "id": "todo-network-traffic-review",
                    "code": "TODO_NETWORK_TRAFFIC_REVIEW",
                    "title": "네트워크 트래픽 분석",
                    "description": "해당 시간대의 트래픽 소스(IP/엔드포인트/배치 작업)를 분석하고, 비정상 패턴 여부를 점검합니다.",
                    "meta": "담당: 백엔드/Infra · 우선순위: 중",
                    "priority": "medium",
                },
            },
            {
                "id": "availability-low",
                "code": "ALERT_AVAILABILITY_LOW",
                "category": "infra",
                "metric_key": "availability",
                "metric_unit": "%",
                "metric_format": "percent_3",
                "title": "서비스 가용성 경고",
                "description": "최근 서비스 가용성이 낮아지고 있습니다. 장애 이력과 배포 일정을 점검하세요.",
                "severities": [
                    {"name": "high", "operator": "lt", "threshold": 99.0},
                    {"name": "medium", "operator": "lt", "threshold": 99.5},
                ],
                "todo": {
                    "id": "todo-availability-review",
                    "code": "TODO_AVAILABILITY_REVIEW",
                    "title": "가용성 저하 원인 분석",
                    "description": "장애 구간과 영향 범위를 정리하고 재발 방지 대책을 수립합니다.",
                    "meta": "담당: SRE/Infra · 우선순위: 중",
                    "priority": "medium",
                },
            },
        ]

        def _format_metric(value: float, fmt: str, unit: str) -> str:
            if fmt == "percent_2":
                return f"{value:.2f}%"
            if fmt == "percent_3":
                return f"{value:.3f}%"
            if fmt == "percent_1":
                return f"{value:.1f}%"
            if fmt == "ms_0":
                return f"{value:.0f}ms"
            if fmt == "bytes_auto":
                abs_v = abs(value)
                if abs_v >= 1024 * 1024 * 1024:
                    return f"{value / (1024 * 1024 * 1024):.2f} GB"
                if abs_v >= 1024 * 1024:
                    return f"{value / (1024 * 1024):.2f} MB"
                if abs_v >= 1024:
                    return f"{value / 1024:.2f} KB"
                return f"{value:.0f} B"
            return f"{value}{unit}"

        def _evaluate_severity(rule: dict, value: float) -> str | None:
            for spec in rule.get("severities", []):
                name = spec.get("name")
                op = spec.get("operator")
                threshold = spec.get("threshold")
                if name is None or op not in {"lt", "gt"} or threshold is None:
                    continue
                if op == "lt" and value < threshold:
                    return name
                if op == "gt" and value > threshold:
                    return name
            return None

        # 메트릭 스냅샷 기반으로 공통 규칙 평가
        for rule in metric_alert_rules:
            metric_key = rule["metric_key"]
            value = metric_snapshot.get(metric_key)
            if value is None:
                continue

            severity = _evaluate_severity(rule, float(value))
            if not severity:
                continue

            alert_id = rule["id"]
            metric_unit = rule.get("metric_unit") or ""
            metric_format = rule.get("metric_format", "")
            alerts.append(
                {
                    "id": alert_id,
                    "severity": severity,
                    "category": rule.get("category"),
                    "code": rule.get("code"),
                    "title": rule["title"],
                    "description": rule["description"],
                    "metric": _format_metric(float(value), metric_format, metric_unit),
                    "metric_value": float(value),
                    "metric_unit": metric_unit or None,
                    "related_metric_key": metric_key,
                    "source_type": "metric",
                    "source_id": metric_key,
                }
            )

            todo_cfg = rule.get("todo")
            if todo_cfg:
                todos.append(
                    {
                        "id": todo_cfg["id"],
                        "title": todo_cfg["title"],
                        "description": todo_cfg["description"],
                        "meta": todo_cfg["meta"],
                        "related_alert_id": alert_id,
                        "priority": todo_cfg["priority"],
                        "category": rule.get("category"),
                        "source_type": "alert",
                        "source_id": alert_id,
                        "code": todo_cfg.get("code"),
                    }
                )

        # 인시던트 기반 공통 To-do 생성 (사건 회고/원인 분석용)
        for inc in incidents:
            todos.append(
                {
                    "id": f"todo-postmortem-{inc['id']}",
                    "title": f"{inc['title']} 회고",
                    "description": "장애 원인, 영향 범위, 재발 방지 대책을 정리하는 포스트모텀을 작성합니다.",
                    "meta": f"사건 ID: {inc['id']} · 담당: SRE/Owner · 우선순위: 중",
                    "related_alert_id": None,
                    "priority": "medium"
                    if inc.get("severity") in {"medium", "low"}
                    else "high",
                    "category": inc.get("category"),
                    "source_type": "incident",
                    "source_id": inc["id"],
                    "code": "TODO_INCIDENT_POSTMORTEM",
                }
            )

        def _filter_by_system(items: list[dict], system: str) -> list[dict]:
            if system == "all":
                return items
            return [i for i in items if i.get("category") == system]

        filtered_incidents = _filter_by_system(incidents, system_filter)
        filtered_alerts = _filter_by_system(alerts, system_filter)
        filtered_todos = _filter_by_system(todos, system_filter)

        payload = {
            "kpis": kpis,
            "timeseries": timeseries,
            "incidents": filtered_incidents,
            "alerts": filtered_alerts,
            "todos": filtered_todos,
            "meta": {
                "backend": backend_used,
                "start": start_dt,
                "end": end_dt,
            },
        }
        serializer = OpsOverviewSerializer(payload)
        return Response(serializer.data)


@extend_schema(
    tags=['판매자'],
    summary='판매자 통계 분석',
    description='판매자의 주문/상품 통계 데이터를 기반으로 분석 지표를 반환합니다.',
)
class SellerAnalyticsOverviewView(APIView):
    """
    판매자용 통합 지표 조회 API

    - 경로: /api/seller/analytics/overview/
    - 기능: 판매자의 주문/상품 통계 데이터를 기반으로 분석 지표를 반환
    """

    permission_classes = []  # IsSeller는 아래에서 체크

    def get(self, request, *args, **kwargs):
        """쿼리 파라미터를 해석하고 집계 결과를 반환"""
        from sellers.permissions import IsSeller

        # 판매자 권한 체크
        if not IsSeller().has_permission(request, self):
            return Response(
                {"detail": "판매자 권한이 필요합니다."},
                status=status.HTTP_403_FORBIDDEN,
            )

        seller = request.user.seller_profile

        params = request.query_params
        raw_start = params.get("start_date")
        raw_end = params.get("end_date")
        _granularity = params.get("granularity", "daily")
        _tab = params.get("tab", "source")
        _device = params.get("device", "all")
        _region = params.get("region", "all")

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

        overview_data = self._build_overview(
            seller, start_date, end_date, _granularity, _tab
        )
        serializer = AnalyticsOverviewSerializer(overview_data)
        return Response(serializer.data)

    def _build_overview(
        self, seller, start_date, end_date, granularity: str, tab: str
    ) -> dict:
        """
        판매자의 OrderItem/ProductStats 데이터를 기반으로 AnalyticsOverview 응답을 구성
        """
        from products.models import Product, ProductStats
        from orders.models import OrderItem, OrderItemStatus, OrderStatus, Shipment
        from django.db.models import Sum, Avg, F, IntegerField, Count, Q
        from django.db.models.functions import ExtractHour
        from django.utils import timezone
        from collections import defaultdict

        # 판매자 상품 조회
        products = Product.objects.filter(seller=seller)
        product_ids = list(products.values_list("id", flat=True))

        # 유효한 주문 상태
        valid_order_statuses = [
            OrderStatus.PAID,
            OrderStatus.PROCESSING,
            OrderStatus.SHIPPED,
            OrderStatus.DELIVERED,
        ]

        # 기간 내 주문 아이템 필터링
        order_items_base = OrderItem.objects.filter(
            seller=seller,
            order__status__in=valid_order_statuses,
            created_at__date__range=(start_date, end_date),
        ).exclude(status__in=[OrderItemStatus.CANCELLED, OrderItemStatus.REFUNDED])

        # 이전 기간 데이터 (delta 계산용)
        prev_start = start_date - (end_date - start_date) - timedelta(days=1)
        prev_end = start_date - timedelta(days=1)
        prev_order_items = OrderItem.objects.filter(
            seller=seller,
            order__status__in=valid_order_statuses,
            created_at__date__range=(prev_start, prev_end),
        ).exclude(status__in=[OrderItemStatus.CANCELLED, OrderItemStatus.REFUNDED])

        # ----- KPI 계산 -----
        # 현재 기간 통계
        revenue_expr = F("unit_price_snapshot") * F("quantity") - F("discount_amount")
        current_revenue = (
            order_items_base.aggregate(total=Sum(revenue_expr, output_field=IntegerField()))[
                "total"
            ]
            or 0
        )
        current_orders = order_items_base.count()

        # 세션 수는 ProductStats의 view_count 합으로 근사
        # 실제로는 세션 로그가 있어야 정확하지만, 현재는 view_count로 근사
        stats_qs = ProductStats.objects.filter(product_id__in=product_ids)
        current_sessions = stats_qs.aggregate(total=Sum("view_count"))["total"] or 0
        # 세션이 없으면 주문 수 * 10으로 근사 (전환율 10% 가정)
        if current_sessions == 0:
            current_sessions = current_orders * 10

        # 전환율 계산
        current_conversion = (
            (current_orders / current_sessions * 100) if current_sessions > 0 else 0.0
        )

        # 객단가 (AOV)
        current_aov = (current_revenue / current_orders) if current_orders > 0 else 0

        # 재방문율 (고유 구매자 수 기반 근사)
        unique_buyers = (
            order_items_base.values("order__user")
            .distinct()
            .exclude(order__user__isnull=True)
            .count()
        )
        # 단순화: 재방문율은 전체 구매자 대비 2회 이상 구매자 비율로 근사
        repeat_buyers = (
            order_items_base.values("order__user")
            .annotate(order_count=Count("order", distinct=True))
            .filter(order_count__gt=1)
            .exclude(order__user__isnull=True)
            .count()
        )
        current_return_rate = (
            (repeat_buyers / unique_buyers * 100) if unique_buyers > 0 else 0.0
        )

        # 이전 기간 통계 (delta 계산용)
        prev_revenue = (
            prev_order_items.aggregate(
                total=Sum(revenue_expr, output_field=IntegerField())
            )["total"]
            or 0
        )
        prev_orders = prev_order_items.count()
        # 이전 기간 세션도 동일하게 계산
        prev_sessions = prev_orders * 10 if prev_orders > 0 else 0
        prev_conversion = (
            (prev_orders / prev_sessions * 100) if prev_sessions > 0 else 0.0
        )
        prev_aov = (prev_revenue / prev_orders) if prev_orders > 0 else 0

        # Delta 계산
        def calc_delta(current, prev):
            if prev == 0:
                return 0.0 if current == 0 else 100.0
            return ((current - prev) / prev) * 100.0

        kpis = [
            {
                "label": "세션수",
                "value": float(current_sessions),
                "delta": calc_delta(current_sessions, prev_sessions),
                "unit": None,
            },
            {
                "label": "주문수",
                "value": float(current_orders),
                "delta": calc_delta(current_orders, prev_orders),
                "unit": None,
            },
            {
                "label": "전환율",
                "value": round(current_conversion, 1),
                "delta": round(current_conversion - prev_conversion, 1),
                "unit": "%",
            },
            {
                "label": "매출",
                "value": float(current_revenue),
                "delta": calc_delta(current_revenue, prev_revenue),
                "unit": "원",
            },
            {
                "label": "객단가",
                "value": float(round(current_aov)),
                "delta": calc_delta(current_aov, prev_aov),
                "unit": "원",
            },
            {
                "label": "재방문율",
                "value": round(current_return_rate, 1),
                "delta": 0.0,  # 재방문율 delta는 복잡하므로 0으로 설정
                "unit": "%",
            },
        ]

        # ----- Trend 데이터 (일별 추이) -----
        trend_data = []
        current_date = start_date
        while current_date <= end_date:
            day_items = order_items_base.filter(created_at__date=current_date)
            day_revenue = (
                day_items.aggregate(total=Sum(revenue_expr, output_field=IntegerField()))[
                    "total"
                ]
                or 0
            )
            day_orders = day_items.count()
            # 일별 세션은 일별 주문 수에 비례하여 계산 (전환율 기준)
            day_sessions = (
                day_orders * 10 if day_orders > 0 else 0
            )  # 전환율 10% 가정
            day_conversion = (day_orders / day_sessions * 100) if day_sessions > 0 else 0.0

            trend_data.append(
                {
                    "date": current_date.strftime("%m-%d"),
                    "sessions": day_sessions,
                    "orders": day_orders,
                    "conversion": round(day_conversion, 1),
                    "revenue": float(day_revenue),
                }
            )
            current_date += timedelta(days=1)

        # ----- Breakdown 데이터 (상품별) -----
        product_breakdown = []
        product_stats = (
            order_items_base.values("product_id", "product__name")
            .annotate(
                orders=Count("id"),
                revenue=Sum(revenue_expr, output_field=IntegerField()),
            )
            .order_by("-revenue")[:10]
        )

        for item in product_stats:
            prod_id = item["product_id"]
            prod_stats = ProductStats.objects.filter(product_id=prod_id).first()
            prod_sessions = prod_stats.view_count if prod_stats else 0
            prod_conversion = (
                (item["orders"] / prod_sessions * 100) if prod_sessions > 0 else 0.0
            )

            product_breakdown.append(
                {
                    "name": item["product__name"] or f"상품 {prod_id}",
                    "sessions": prod_sessions,
                    "orders": item["orders"],
                    "conversion": round(prod_conversion, 1),
                    "revenue": float(item["revenue"] or 0),
                }
            )

        # ----- Breakdown 데이터 (시간대별) -----
        time_breakdown = []
        time_stats = (
            order_items_base.annotate(hour=ExtractHour("created_at"))
            .values("hour")
            .annotate(
                orders=Count("id"),
                revenue=Sum(revenue_expr, output_field=IntegerField()),
            )
            .order_by("hour")
        )

        for item in time_stats:
            hour = item["hour"]
            hour_orders = item["orders"]
            hour_revenue = item["revenue"] or 0
            # 시간대별 세션은 주문 수 기반으로 근사
            hour_sessions = hour_orders * 10 if hour_orders > 0 else 0
            hour_conversion = (
                (hour_orders / hour_sessions * 100) if hour_sessions > 0 else 0.0
            )

            time_breakdown.append(
                {
                    "name": f"{hour}시",
                    "sessions": hour_sessions,
                    "orders": hour_orders,
                    "conversion": round(hour_conversion, 1),
                    "revenue": float(hour_revenue),
                }
            )

        # ----- Breakdown 데이터 (지역별) -----
        region_breakdown = []
        # Shipment를 통해 지역 추출
        order_ids = order_items_base.values_list("order_id", flat=True).distinct()
        shipments = Shipment.objects.filter(order_id__in=order_ids).select_related("order")

        # 주소에서 지역 추출 (간단히 첫 번째 단어나 시/도 추출)
        region_map = defaultdict(lambda: {"orders": 0, "revenue": 0, "order_ids": set()})
        for shipment in shipments:
            address = shipment.address_full
            # 주소에서 지역명 추출 (예: "서울시", "경기도" 등)
            region_name = "기타"
            if address:
                # 시/도 추출 시도
                if "서울" in address:
                    region_name = "서울"
                elif "경기" in address:
                    region_name = "경기"
                elif "부산" in address:
                    region_name = "부산"
                elif "인천" in address:
                    region_name = "인천"
                elif "대구" in address:
                    region_name = "대구"
                elif "광주" in address:
                    region_name = "광주"
                elif "대전" in address:
                    region_name = "대전"
                elif "울산" in address:
                    region_name = "울산"
                elif "세종" in address:
                    region_name = "세종"
                elif "강원" in address:
                    region_name = "강원"
                elif "충북" in address or "충청북도" in address:
                    region_name = "충북"
                elif "충남" in address or "충청남도" in address:
                    region_name = "충남"
                elif "전북" in address or "전라북도" in address:
                    region_name = "전북"
                elif "전남" in address or "전라남도" in address:
                    region_name = "전남"
                elif "경북" in address or "경상북도" in address:
                    region_name = "경북"
                elif "경남" in address or "경상남도" in address:
                    region_name = "경남"
                elif "제주" in address:
                    region_name = "제주"

            region_map[region_name]["order_ids"].add(shipment.order_id)

        # OrderItem과 매칭하여 매출 계산
        for region_name, region_data in region_map.items():
            region_order_ids = region_data["order_ids"]
            region_order_items = order_items_base.filter(order_id__in=region_order_ids)
            region_orders = region_order_items.count()
            region_revenue = (
                region_order_items.aggregate(
                    total=Sum(revenue_expr, output_field=IntegerField())
                )["total"]
                or 0
            )
            region_sessions = region_orders * 10 if region_orders > 0 else 0
            region_conversion = (
                (region_orders / region_sessions * 100) if region_sessions > 0 else 0.0
            )

            region_breakdown.append(
                {
                    "name": region_name,
                    "sessions": region_sessions,
                    "orders": region_orders,
                    "conversion": round(region_conversion, 1),
                    "revenue": float(region_revenue),
                }
            )

        region_breakdown.sort(key=lambda x: x["revenue"], reverse=True)

        # ----- Breakdown 데이터 (신규/재방문) -----
        retention_breakdown = []
        # 고유 구매자별 주문 횟수 집계
        user_order_counts = (
            order_items_base.values("order__user_id")
            .annotate(order_count=Count("order_id", distinct=True))
            .exclude(order__user_id__isnull=True)
        )

        new_buyers = user_order_counts.filter(order_count=1).count()
        returning_buyers = user_order_counts.filter(order_count__gt=1).count()

        # 신규 구매자 데이터
        new_buyer_order_items = order_items_base.filter(
            order__user_id__in=user_order_counts.filter(order_count=1).values_list(
                "order__user_id", flat=True
            )
        )
        new_revenue = (
            new_buyer_order_items.aggregate(
                total=Sum(revenue_expr, output_field=IntegerField())
            )["total"]
            or 0
        )
        new_orders = new_buyer_order_items.count()
        new_sessions = new_orders * 10 if new_orders > 0 else 0
        new_conversion = (
            (new_orders / new_sessions * 100) if new_sessions > 0 else 0.0
        )

        retention_breakdown.append(
            {
                "name": "신규",
                "sessions": new_sessions,
                "orders": new_orders,
                "conversion": round(new_conversion, 1),
                "revenue": float(new_revenue),
            }
        )

        # 재방문 구매자 데이터
        returning_buyer_order_items = order_items_base.filter(
            order__user_id__in=user_order_counts.filter(order_count__gt=1).values_list(
                "order__user_id", flat=True
            )
        )
        returning_revenue = (
            returning_buyer_order_items.aggregate(
                total=Sum(revenue_expr, output_field=IntegerField())
            )["total"]
            or 0
        )
        returning_orders = returning_buyer_order_items.count()
        returning_sessions = returning_orders * 10 if returning_orders > 0 else 0
        returning_conversion = (
            (returning_orders / returning_sessions * 100)
            if returning_sessions > 0
            else 0.0
        )

        retention_breakdown.append(
            {
                "name": "재방문",
                "sessions": returning_sessions,
                "orders": returning_orders,
                "conversion": round(returning_conversion, 1),
                "revenue": float(returning_revenue),
            }
        )

        # ----- Breakdown 데이터 (디바이스별) -----
        # 실제 디바이스 데이터가 없으므로 빈 배열 반환
        # 향후 User-Agent 분석 또는 별도 로그가 있다면 추가 가능
        device_breakdown = []

        # 기본 breakdown 데이터
        breakdown = {
            "source": [],  # 유입경로별은 데이터가 없으므로 빈 리스트
            "product": product_breakdown,
            "keyword": [],  # 검색어 데이터 없음
            "time": time_breakdown,
            "device": device_breakdown,
            "region": region_breakdown,
            "retention": retention_breakdown,
        }

        # Trend 데이터 (모든 탭에 대해 동일하게)
        trend = {
            "source": trend_data,
            "product": trend_data,
            "keyword": trend_data,
            "time": trend_data,
            "device": trend_data,
            "region": trend_data,
            "retention": trend_data,
        }

        # Heatmap (시간대별 유입) - 간단한 mock 데이터 구조
        heatmap = []

        # Keywords (빈 리스트)
        keywords = []

        return {
            "kpis": kpis,
            "breakdown": breakdown,
            "trend": trend,
            "heatmap": heatmap,
            "keywords": keywords,
        }


