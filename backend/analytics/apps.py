from django.apps import AppConfig


class AnalyticsConfig(AppConfig):
    """Admin 분석/집계용 앱 설정"""

    default_auto_field = "django.db.models.BigAutoField"
    name = "analytics"
    verbose_name = "Admin 분석/집계"


