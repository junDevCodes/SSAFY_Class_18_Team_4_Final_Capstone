"""
데이터 파이프라인 앱 설정

서버 시작 시 백그라운드 스케줄러를 실행하여
매 시간마다 JSON 파일을 감지하고 DB로 처리합니다.
"""
import os
import sys
import threading
import time
import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class DataPipelineConfig(AppConfig):
    """데이터 파이프라인 앱 설정"""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'data_pipeline'
    verbose_name = '데이터 파이프라인'

    def ready(self):
        """앱 준비 완료 시 백그라운드 스케줄러 시작"""
        # runserver 또는 gunicorn 메인 프로세스에서만 실행
        # --noreload 없이 실행 시 자식 프로세스 중복 방지
        if self._should_start_scheduler():
            self._start_background_scheduler()

    def _should_start_scheduler(self) -> bool:
        """스케줄러를 시작해야 하는지 확인

        조건:
        1. 메인 프로세스에서만 (RUN_MAIN 환경변수 체크)
        2. migrate, shell 등 관리 명령이 아닌 경우
        3. 테스트 실행이 아닌 경우
        """
        # Django autoreload: 자식 프로세스에서는 RUN_MAIN='true'
        # 부모 프로세스에서만 스케줄러 시작 (중복 방지)
        run_main = os.environ.get('RUN_MAIN')

        # runserver --noreload 또는 gunicorn의 경우 RUN_MAIN이 없음
        # 이 경우 메인 프로세스로 간주
        if run_main == 'true':
            # autoreload 자식 프로세스 - 여기서 실행
            pass
        elif run_main is None:
            # gunicorn 또는 --noreload - 메인 프로세스
            pass
        else:
            return False

        # 관리 명령 확인 (migrate, shell, test 등에서는 실행 안 함)
        if len(sys.argv) > 1:
            command = sys.argv[1]
            skip_commands = [
                'migrate', 'makemigrations', 'shell', 'dbshell',
                'createsuperuser', 'collectstatic', 'test',
                'check', 'showmigrations', 'sqlmigrate',
                'flush', 'loaddata', 'dumpdata',
            ]
            if command in skip_commands:
                return False

        return True

    def _start_background_scheduler(self):
        """백그라운드 스케줄러 스레드 시작"""
        # 이미 실행 중인지 확인 (중복 방지)
        scheduler_flag = getattr(self, '_scheduler_started', False)
        if scheduler_flag:
            return

        self._scheduler_started = True

        # 데몬 스레드로 실행 (메인 프로세스 종료 시 자동 종료)
        scheduler_thread = threading.Thread(
            target=self._run_scheduler,
            name='DataPipelineScheduler',
            daemon=True,
        )
        scheduler_thread.start()
        logger.info("[데이터 파이프라인] 백그라운드 스케줄러 시작됨 (매 시간 실행)")

    def _run_scheduler(self):
        """스케줄러 메인 루프

        1. 서버 시작 후 초기 대기 (DB 준비 시간)
        2. 첫 실행
        3. 이후 설정된 간격마다 실행

        환경변수:
        - PIPELINE_INITIAL_DELAY: 초기 대기 시간 (초, 기본: 30)
        - PIPELINE_INTERVAL: 실행 간격 (초, 기본: 3600 = 1시간)
        - PIPELINE_ENABLED: 스케줄러 활성화 여부 (기본: true)
        """
        # 스케줄러 비활성화 확인
        if os.environ.get('PIPELINE_ENABLED', 'true').lower() == 'false':
            logger.info("[데이터 파이프라인] 스케줄러 비활성화됨 (PIPELINE_ENABLED=false)")
            return

        # 초기 대기 시간 (기본: 30초)
        initial_delay = int(os.environ.get('PIPELINE_INITIAL_DELAY', '30'))
        time.sleep(initial_delay)

        # 스케줄 간격 (기본: 1시간 = 3600초)
        interval = int(os.environ.get('PIPELINE_INTERVAL', '3600'))

        while True:
            try:
                self._process_pipeline()
            except Exception as e:
                logger.error(f"[데이터 파이프라인] 처리 중 오류: {e}")

            # 다음 실행까지 대기
            time.sleep(interval)

    def _process_pipeline(self):
        """파이프라인 처리 실행"""
        from data_pipeline.processor import DataProcessor

        logger.info("[데이터 파이프라인] 스케줄 실행 시작...")

        processor = DataProcessor()

        # 새 파일 확인
        new_files = processor.check_new_files()
        pending_files = processor.get_pending_files()

        total_files = len(new_files) + len(pending_files)

        if total_files == 0:
            logger.info("[데이터 파이프라인] 처리할 파일 없음")
            return

        logger.info(f"[데이터 파이프라인] {total_files}개 파일 발견 (새 파일: {len(new_files)}, 대기: {len(pending_files)})")

        # 처리 실행
        results = processor.process_all(dry_run=False, auto_move=True)

        logger.info(
            f"[데이터 파이프라인] 처리 완료 - "
            f"파일: {results['processed_files']}/{results['total_files']}, "
            f"상품: 신규 {results['new_products']}, "
            f"업데이트 {results['updated_products']}, "
            f"스킵 {results['skipped_products']}"
        )

        if results['errors']:
            for err in results['errors']:
                logger.warning(f"[데이터 파이프라인] 오류: {err['file']} - {err['error']}")
