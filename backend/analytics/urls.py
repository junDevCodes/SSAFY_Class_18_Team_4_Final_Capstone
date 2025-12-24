"""
Admin 분석용 API URL 설정
"""

from django.urls import path

from analytics.views import (
    AdminAnalyticsOverviewView,
    AdminRecommendationTrendView,
    AdminRecommendationPlacementSummaryView,
    AdminBehaviorOverviewView,
    AdminOpsOverviewView,
)

urlpatterns = [
    # Admin 분석 API
    path(
        "overview/",
        AdminAnalyticsOverviewView.as_view(),
        name="admin-analytics-overview",
    ),
    path(
        "recommendation/trend/",
        AdminRecommendationTrendView.as_view(),
        name="admin-recommendation-trend",
    ),
    path(
        "recommendation/placement-summary/",
        AdminRecommendationPlacementSummaryView.as_view(),
        name="admin-recommendation-placement-summary",
    ),
    path(
        "behavior/",
        AdminBehaviorOverviewView.as_view(),
        name="admin-analytics-behavior-overview",
    ),
    path(
        "ops/",
        AdminOpsOverviewView.as_view(),
        name="admin-analytics-ops-overview",
    ),
]


