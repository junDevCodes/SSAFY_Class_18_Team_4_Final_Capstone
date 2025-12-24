"""
Admin 분석용 API serializer 정의

프론트엔드의 AnalyticsOverview 타입과 최대한 유사한 형태로 응답을 구성한다.
"""

from rest_framework import serializers


class KpiSerializer(serializers.Serializer):
    """상단 KPI 카드용 지표"""

    label = serializers.CharField()
    value = serializers.FloatField()
    delta = serializers.FloatField()
    unit = serializers.CharField(allow_null=True, required=False)


class ChannelBreakdownSerializer(serializers.Serializer):
    """카테고리/채널별 성과 분해용 데이터"""

    name = serializers.CharField()
    sessions = serializers.IntegerField()
    orders = serializers.IntegerField()
    conversion = serializers.FloatField()
    revenue = serializers.FloatField()


class TimeBucketSerializer(serializers.Serializer):
    """시간 단위(일/월/년) 추이 데이터"""

    date = serializers.CharField()
    sessions = serializers.IntegerField()
    orders = serializers.IntegerField()
    conversion = serializers.FloatField()
    revenue = serializers.FloatField()


class AnalyticsOverviewSerializer(serializers.Serializer):
    """
    Admin 대시보드 통합 응답 스키마

    - kpis: 상단 핵심 지표 카드
    - trend: 탭(source/product/...)별 추이 데이터
    - breakdown: 탭별 Top N 분해 데이터
    - heatmap/keywords: 추후 확장을 위한 필드 (초기에는 빈 리스트)
    """

    kpis = KpiSerializer(many=True)
    breakdown = serializers.DictField(child=ChannelBreakdownSerializer(many=True))
    trend = serializers.DictField(child=TimeBucketSerializer(many=True))
    heatmap = serializers.ListField(child=serializers.DictField(), default=list)
    keywords = serializers.ListField(child=serializers.DictField(), default=list)


class BehaviorTrendPointSerializer(serializers.Serializer):
    """유저 행동 지표용 일 단위 추이 데이터"""

    date = serializers.CharField()
    buyers = serializers.IntegerField()
    cart_adds = serializers.IntegerField()
    orders = serializers.IntegerField()
    cart_to_order_rate = serializers.FloatField()
    sessions = serializers.IntegerField()


class BehaviorFunnelStepSerializer(serializers.Serializer):
    """세션 → 장바구니 → 구매 퍼널 단계"""

    name = serializers.CharField()
    value = serializers.IntegerField()
    rate = serializers.FloatField(required=False)


class BehaviorOverviewSerializer(serializers.Serializer):
    """
    유저 행동(Behavior) 대시보드용 응답 스키마

    - kpis: DAU/MAU, 장바구니 전환율 등 핵심 지표
    - trend: 일 단위 buyers/cart_adds/orders 추이
    - funnels: 세션 → 장바구니 → 구매 퍼널 단계 요약
    - cohorts: 코호트/잔존 분석 (초기에는 빈 리스트)
    """

    kpis = KpiSerializer(many=True)
    trend = BehaviorTrendPointSerializer(many=True)
    funnels = BehaviorFunnelStepSerializer(many=True)
    cohorts = serializers.ListField(child=serializers.DictField(), default=list)


class OpsMetricPointSerializer(serializers.Serializer):
    """운영/시스템 건강도 시계열 포인트"""

    timestamp = serializers.DateTimeField()
    crawling_success_rate = serializers.FloatField()
    api_p95_ms = serializers.FloatField()
    error_rate = serializers.FloatField()
    availability = serializers.FloatField()


class OpsIncidentSerializer(serializers.Serializer):
    """장애/이벤트 이력"""

    id = serializers.CharField()
    severity = serializers.CharField()
    service = serializers.CharField()
    title = serializers.CharField()
    description = serializers.CharField()
    started_at = serializers.DateTimeField()
    resolved_at = serializers.DateTimeField(allow_null=True)


class OpsAlertSerializer(serializers.Serializer):
    """운영 리스크 알림"""

    id = serializers.CharField()
    severity = serializers.CharField()
    title = serializers.CharField()
    description = serializers.CharField()
    metric = serializers.CharField()
    metric_value = serializers.FloatField(allow_null=True, required=False)
    metric_unit = serializers.CharField(allow_null=True, required=False)
    related_metric_key = serializers.CharField(allow_null=True, required=False)


class OpsTodoSerializer(serializers.Serializer):
    """운영 To-do 아이템"""

    id = serializers.CharField()
    title = serializers.CharField()
    description = serializers.CharField()
    meta = serializers.CharField()
    related_alert_id = serializers.CharField(allow_null=True, required=False)
    priority = serializers.CharField()


class OpsOverviewSerializer(serializers.Serializer):
    """
    운영 지표(Operational) 대시보드용 응답 스키마

    - kpis: 크롤링 성공률, 에러율, 가용성 등 요약 카드
    - timeseries: 운영 지표 시계열
    - incidents: 최근 장애/알림 이력
    - alerts: 리스크 알림 목록
    - todos: 운영 To-do 목록
    """

    kpis = KpiSerializer(many=True)
    timeseries = OpsMetricPointSerializer(many=True)
    incidents = OpsIncidentSerializer(many=True)
    alerts = OpsAlertSerializer(many=True)
    todos = OpsTodoSerializer(many=True)

