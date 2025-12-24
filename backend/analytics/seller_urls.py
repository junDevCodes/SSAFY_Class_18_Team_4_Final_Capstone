"""
판매자 분석용 API URL 설정
"""

from django.urls import path

from analytics.views import SellerAnalyticsOverviewView

urlpatterns = [
    path(
        "overview/",
        SellerAnalyticsOverviewView.as_view(),
        name="seller-analytics-overview",
    ),
]

