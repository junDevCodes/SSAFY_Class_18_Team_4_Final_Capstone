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


