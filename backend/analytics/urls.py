"""
Admin 분석용 API URL 설정
"""

from django.urls import path

from analytics.views import AdminAnalyticsOverviewView

urlpatterns = [
    path("overview/", AdminAnalyticsOverviewView.as_view(), name="admin-analytics-overview"),
]


