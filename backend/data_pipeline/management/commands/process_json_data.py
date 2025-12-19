"""
JSON 데이터 처리 커맨드

크롤러가 processed 폴더에 저장한 JSON 파일을 감지하여
DB로 적용하고 backup으로 이동합니다.

처리 흐름:
1. processed 폴더에서 새 JSON 파일 감지
2. 새 파일을 incoming 폴더로 이동
3. incoming 폴더의 파일을 DB로 처리
4. 처리 완료된 파일을 backup 폴더로 이동

사용법:
    python manage.py process_json_data [--dry-run] [--show-details]

예시:
    # 시뮬레이션 실행
    python manage.py process_json_data --dry-run

    # 실제 처리 실행
    python manage.py process_json_data

    # 상세 로그 출력
    python manage.py process_json_data --show-details
"""

from django.core.management.base import BaseCommand, CommandError

from data_pipeline.processor import DataProcessor


class Command(BaseCommand):
    help = 'processed 폴더의 JSON 크롤링 데이터를 DB로 처리합니다. (processed → incoming → DB → backup)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='실제 DB 작업 없이 시뮬레이션만 수행'
        )

        parser.add_argument(
            '--show-details',
            action='store_true',
            help='상세 로그 출력'
        )

        parser.add_argument(
            '--base-dir',
            type=str,
            default=None,
            help='JSON 데이터 폴더 경로 (기본: data/json)'
        )

        parser.add_argument(
            '--no-auto-move',
            action='store_true',
            help='processed → incoming 자동 이동 비활성화 (incoming만 처리)'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        verbose = options['show_details']
        auto_move = not options['no_auto_move']

        if dry_run:
            self.stdout.write(self.style.WARNING(
                "\n[시뮬레이션 모드] 실제 DB 작업은 수행하지 않습니다.\n"
            ))

        # 프로세서 생성
        processor = DataProcessor(base_dir=options['base_dir'])

        # 1. processed 폴더의 새 파일 확인
        new_files = processor.check_new_files()
        if new_files:
            self.stdout.write(f"[정보] processed 폴더 새 파일: {len(new_files)}개")
            if verbose:
                for f in new_files:
                    self.stdout.write(f"  - {f.name}")

        # 2. incoming 폴더의 기존 파일 확인
        pending_files = processor.get_pending_files()
        if pending_files:
            self.stdout.write(f"[정보] incoming 폴더 대기 파일: {len(pending_files)}개")
            if verbose:
                for f in pending_files:
                    self.stdout.write(f"  - {f.name}")

        # 처리할 파일이 없으면 종료
        total_files = len(new_files) + len(pending_files)
        if total_files == 0:
            self.stdout.write(self.style.SUCCESS(
                "[정보] 처리할 파일이 없습니다."
            ))
            return

        # 3. 처리 실행
        results = processor.process_all(dry_run=dry_run, auto_move=auto_move)

        # 결과 출력
        self.stdout.write("\n" + "=" * 40)
        self.stdout.write("처리 결과")
        self.stdout.write("=" * 40)

        self.stdout.write(f"총 파일: {results['total_files']}개")

        if results['processed_files'] > 0:
            self.stdout.write(self.style.SUCCESS(
                f"성공: {results['processed_files']}개"
            ))

        if results['failed_files'] > 0:
            self.stdout.write(self.style.ERROR(
                f"실패: {results['failed_files']}개"
            ))

        self.stdout.write(f"\n총 상품: {results['total_products']}개")
        self.stdout.write(f"  - 신규: {results['new_products']}개")
        self.stdout.write(f"  - 업데이트: {results['updated_products']}개")
        self.stdout.write(f"  - 건너뜀: {results['skipped_products']}개")

        if results['errors']:
            self.stdout.write(self.style.ERROR("\n[오류 목록]"))
            for err in results['errors']:
                self.stdout.write(f"  - {err['file']}: {err['error']}")

        if not dry_run and results['processed_files'] > 0:
            self.stdout.write(self.style.SUCCESS(
                "\n[완료] 처리된 파일이 backup 폴더로 이동되었습니다."
            ))
