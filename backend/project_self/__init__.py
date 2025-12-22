"""
Django 프로젝트 초기화

Django 시작 시 Celery 앱을 함께 로드합니다.
이를 통해 @shared_task 데코레이터가 정상 작동합니다.
"""
from .celery import app as celery_app

__all__ = ('celery_app',)
