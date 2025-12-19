"""
파이프라인 자동 감시 커맨드

processed 폴더를 감시하다가 새 JSON 파일이 감지되면
자동으로 파이프라인을 실행합니다.

사용법:
    python manage.py watch_pipeline [--interval SECONDS]

예시:
    # 기본 5초 간격으로 감시
    python manage.py watch_pipeline

    # 10초 간격으로 감시
    python manage.py watch_pipeline --interval 10

    # 1초 간격으로 감시 (빠른 반응)
    python manage.py watch_pipeline --interval 1
"""

from django.core.management.base import BaseCommand

from data_pipeline.processor import PipelineWatcher


class Command(BaseCommand):
    help = 'processed 폴더를 감시하고 새 JSON 파일 감지 시 자동으로 파이프라인을 실행합니다.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--interval',
            type=int,
            default=5,
            help='폴더 감시 주기 (초, 기본: 5)'
        )

        parser.add_argument(
            '--base-dir',
            type=str,
            default=None,
            help='JSON 데이터 폴더 경로 (기본: data/json)'
        )

    def handle(self, *args, **options):
        interval = options['interval']
        base_dir = options['base_dir']

        self.stdout.write(self.style.SUCCESS(
            f"\n파이프라인 자동 감시를 시작합니다. (간격: {interval}초)"
        ))
        self.stdout.write(
            "종료하려면 Ctrl+C를 누르세요.\n"
        )

        try:
            watcher = PipelineWatcher(base_dir=base_dir, interval=interval)
            watcher.start()
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING(
                "\n감시가 중단되었습니다."
            ))
