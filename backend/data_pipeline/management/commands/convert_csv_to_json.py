"""
CSV → JSON 변환 커맨드

사용법:
    python manage.py convert_csv_to_json [csv_path] [--output-dir=...] [--source=...]

예시:
    # 기본 CSV 파일 변환
    python manage.py convert_csv_to_json

    # 특정 CSV 파일 변환
    python manage.py convert_csv_to_json data/my_data.csv

    # 소스 지정
    python manage.py convert_csv_to_json data/my_data.csv --source=coupang
"""

from django.core.management.base import BaseCommand, CommandError
from pathlib import Path

from data_pipeline.converter import CSVToJSONConverter


class Command(BaseCommand):
    help = 'CSV 크롤링 데이터를 JSON 형식으로 변환합니다.'

    def add_arguments(self, parser):
        # 위치 인자: CSV 파일 경로 (선택)
        parser.add_argument(
            'csv_path',
            nargs='?',
            type=str,
            default=None,
            help='변환할 CSV 파일 경로 (기본: data/merged_all_naver.csv)'
        )

        # 옵션 인자
        parser.add_argument(
            '--output-dir',
            type=str,
            default=None,
            help='JSON 파일 출력 디렉토리 (기본: data/json/incoming)'
        )

        parser.add_argument(
            '--source',
            type=str,
            default=None,
            help='데이터 소스명 (예: naver, coupang). 기본값은 파일명에서 추출'
        )

        parser.add_argument(
            '--daily',
            action='store_true',
            help='날짜별로 분할된 JSON 파일 생성'
        )

    def handle(self, *args, **options):
        # CSV 파일 경로 결정
        csv_path = options['csv_path']
        if csv_path is None:
            # 기본 CSV 파일 사용
            # Docker 환경 확인
            docker_data_path = Path('/app/data')
            if docker_data_path.exists():
                csv_path = docker_data_path / 'merged_all_naver.csv'
            else:
                project_root = Path(__file__).parent.parent.parent.parent.parent
                csv_path = project_root / 'data' / 'merged_all_naver.csv'
        else:
            csv_path = Path(csv_path)

        if not csv_path.exists():
            raise CommandError(f"CSV 파일을 찾을 수 없습니다: {csv_path}")

        self.stdout.write(f"CSV 파일: {csv_path}")

        # 변환기 생성
        converter = CSVToJSONConverter(output_dir=options['output_dir'])

        try:
            if options['daily']:
                # 날짜별 분할 변환
                output_paths = converter.convert_csv_to_daily_jsons(
                    str(csv_path),
                    source=options['source']
                )
                self.stdout.write(self.style.SUCCESS(
                    f"\n[성공] {len(output_paths)}개의 JSON 파일 생성 완료:"
                ))
                for path in output_paths:
                    self.stdout.write(f"  - {path}")
            else:
                # 단일 파일 변환
                output_path = converter.convert_csv_to_json(
                    str(csv_path),
                    source=options['source']
                )
                self.stdout.write(self.style.SUCCESS(
                    f"\n[성공] JSON 파일 생성 완료: {output_path}"
                ))

        except Exception as e:
            raise CommandError(f"변환 실패: {e}")
