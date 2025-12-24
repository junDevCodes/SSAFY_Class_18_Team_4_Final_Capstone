"""
Django 프로젝트 초기화

Django 시작 시 Celery 앱을 함께 로드합니다.
이를 통해 @shared_task 데코레이터가 정상 작동합니다.

Celery가 설치되지 않은 환경에서도 Django는 정상 동작합니다.
"""
try:
    from .celery import app as celery_app
    __all__ = ('celery_app',)
    
    # Celery CLI(-A project_self)가 project_self.celery 를 찾는 경우 대비
    import project_self.celery as celery  # noqa: F401

    __all__ = ("celery_app", "celery")
except ImportError:
    # Celery가 설치되지 않은 환경 (로컬 개발 등)
    celery_app = None
    __all__ = ()
