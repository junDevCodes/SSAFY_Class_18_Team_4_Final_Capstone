from __future__ import annotations

from django.urls import path

from .views import AdminUserListView, AdminUserDetailView, AdminUserSummaryView

urlpatterns = [
    path("", AdminUserListView.as_view(), name="admin-user-list"),
    path("summary/", AdminUserSummaryView.as_view(), name="admin-user-summary"),
    path("<int:pk>/", AdminUserDetailView.as_view(), name="admin-user-detail"),
]


