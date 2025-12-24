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


