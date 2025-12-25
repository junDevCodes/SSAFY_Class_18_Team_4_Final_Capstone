"""
상품 조회 로그 정리 명령어

오래된 조회 로그를 삭제하여 데이터베이스 크기를 관리합니다.
쿨타임(2분)보다 충분히 긴 시간이 지난 로그는 삭제해도 무방합니다.

사용법:
    # 기본값 (1일 이상 된 로그 삭제)
    python manage.py cleanup_view_logs

    # 커스텀 보관 기간 (7일)
    python manage.py cleanup_view_logs --days 7

    # 드라이런 (실제 삭제 없이 삭제 대상 확인)
    python manage.py cleanup_view_logs --dry-run

권장 크론 설정:
    # 매일 새벽 3시에 1일 이상 된 로그 정리
    0 3 * * * /path/to/venv/bin/python /path/to/manage.py cleanup_view_logs
"""
from django.core.management.base import BaseCommand, CommandError

from products.services import ViewCountService


class Command(BaseCommand):
    help = '오래된 상품 조회 로그를 정리합니다.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=1,
            help='보관 기간 (일). 기본값: 1일',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='실제 삭제 없이 삭제 대상 수만 출력합니다.',
        )

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']

        if days < 0:
            raise CommandError('보관 기간은 0 이상이어야 합니다.')

        if dry_run:
            from datetime import timedelta
            from django.utils import timezone
            from products.models import ProductViewLog

            threshold = timezone.now() - timedelta(days=days)
            count = ProductViewLog.objects.filter(viewed_at__lt=threshold).count()

            self.stdout.write(
                self.style.WARNING(
                    f'[드라이런] 삭제 대상: {count}건 ({days}일 이전 로그)'
                )
            )
            return

        deleted_count = ViewCountService.cleanup_old_logs(days=days)

        if deleted_count > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f'조회 로그 정리 완료: {deleted_count}건 삭제 ({days}일 이전)'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'삭제할 로그가 없습니다. ({days}일 이전 로그 없음)'
                )
            )
