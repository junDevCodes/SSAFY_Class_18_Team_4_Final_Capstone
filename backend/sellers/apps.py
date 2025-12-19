from django.apps import AppConfig


class SellersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'sellers'
    verbose_name = '판매자 관리'

    def ready(self):
        """앱 초기화 시 시그널 핸들러 등록"""
        import sellers.signals  # noqa: F401
