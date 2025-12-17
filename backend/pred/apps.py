"""
추천 시스템 앱 설정
"""

from django.apps import AppConfig


class PredConfig(AppConfig):
    """추천 시스템 데이터 모델 앱 설정"""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'pred'
    verbose_name = '추천 시스템'
