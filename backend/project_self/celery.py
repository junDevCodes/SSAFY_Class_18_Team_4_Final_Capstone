"""
Celery 앱 설정

GMS 재료 추출 등 비동기 태스크 처리를 위한 Celery 설정입니다.

사용법:
    # Worker 실행
    celery -A project_self worker -l info

    # Beat 스케줄러 실행 (주기적 태스크)
    celery -A project_self beat -l info

    # Worker + Beat 동시 실행 (개발용)
    celery -A project_self worker -B -l info
"""
import os
from celery import Celery
from celery.schedules import crontab

# Django 설정 모듈 지정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project_self.settings')

# Celery 앱 생성
app = Celery('project_self')

# Django settings에서 CELERY_ 접두사로 시작하는 설정 로드
app.config_from_object('django.conf:settings', namespace='CELERY')

# 등록된 Django 앱에서 tasks.py 자동 검색
app.autodiscover_tasks()


# Celery Beat 스케줄 설정
app.conf.beat_schedule = {
    # 매시간: 미처리 상품 GMS 추출 (parsed_ingredients가 null인 상품)
    'gms-extract-pending-hourly': {
        'task': 'products.tasks.process_pending_extractions',
        'schedule': crontab(minute=0),  # 매시 정각
        'kwargs': {
            'batch_size': 100,
            'use_fallback': True,
        },
    },

    # 매일 새벽 3시: 저신뢰도 상품 재처리 (confidence < 0.7)
    'gms-reprocess-low-confidence-daily': {
        'task': 'products.tasks.reprocess_low_confidence',
        'schedule': crontab(hour=3, minute=0),
        'kwargs': {
            'min_confidence': 0.7,
            'batch_size': 200,
        },
    },

    # 매일 새벽 4시: 실패한 태스크 재시도
    'gms-retry-failed-daily': {
        'task': 'products.tasks.retry_failed_extractions',
        'schedule': crontab(hour=4, minute=0),
        'kwargs': {
            'max_retries': 3,
        },
    },
}

# 태스크 라우팅 설정 (우선순위 큐)
app.conf.task_routes = {
    # 높은 우선순위: 판매자 직접 등록 상품
    'products.tasks.extract_single_product': {'queue': 'high_priority'},

    # 중간 우선순위: 크롤링 배치 처리
    'products.tasks.extract_batch_products': {'queue': 'default'},
    'products.tasks.process_pipeline_batch': {'queue': 'default'},

    # 낮은 우선순위: 스케줄 재처리
    'products.tasks.process_pending_extractions': {'queue': 'low_priority'},
    'products.tasks.reprocess_low_confidence': {'queue': 'low_priority'},
    'products.tasks.retry_failed_extractions': {'queue': 'low_priority'},
}

# 기본 큐 설정
app.conf.task_default_queue = 'default'


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """디버그용 태스크"""
    print(f'Request: {self.request!r}')
