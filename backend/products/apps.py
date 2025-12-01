import os
from django.apps import AppConfig
from django.conf import settings


class ProductsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'products'

    def ready(self):
        """앱 초기화 시 실행 (runserver 시작 시)"""
        # 마이그레이션 중이거나 다른 명령어 실행 중이면 스킵
        import sys
        skip_commands = ['migrate', 'makemigrations', 'shell', 'createsuperuser', 'import_products']
        if any(cmd in sys.argv for cmd in skip_commands):
            return

        # runserver일 때만 실행
        if 'runserver' not in sys.argv:
            return

        # 개발 환경에서만 자동 임포트 실행
        if settings.DEBUG:
            # DB 접근을 지연시키기 위해 별도 스레드에서 실행
            import threading
            thread = threading.Thread(target=self._auto_import_csv_data)
            thread.daemon = True
            thread.start()

    def _auto_import_csv_data(self):
        """서버 시작 시 CSV 데이터 자동 임포트"""
        import time
        from django.core.management import call_command
        from products.models import Product
        import csv

        # Django 앱이 완전히 초기화될 때까지 대기
        time.sleep(2)

        # 이미 데이터가 있으면 스킵
        try:
            if Product.objects.exists():
                print(f"[AUTO-IMPORT] 제품 데이터 {Product.objects.count()}개 존재 - CSV 임포트 스킵")
                return
        except Exception:
            # 마이그레이션이 안 된 경우 등 무시
            return

        # data/ 폴더에서 CSV 파일 찾기
        base_dir = settings.BASE_DIR.parent  # backend의 상위 디렉토리
        data_dir = base_dir / 'data'

        if not data_dir.exists():
            print(f"[AUTO-IMPORT] WARNING: data/ 폴더를 찾을 수 없습니다: {data_dir}")
            return

        # CSV 파일 검색 (우선순위: merged_all_naver.csv > 기타 .csv)
        csv_files = list(data_dir.glob('*.csv'))

        if not csv_files:
            print(f"[AUTO-IMPORT] WARNING: data/ 폴더에 CSV 파일이 없습니다: {data_dir}")
            return

        # merged_all_naver.csv를 우선 사용
        target_csv = None
        for csv_file in csv_files:
            if 'merged_all_naver' in csv_file.name:
                target_csv = csv_file
                break

        # 없으면 첫 번째 CSV 사용
        if not target_csv:
            target_csv = csv_files[0]

        print(f"\n{'='*60}")
        print(f"[AUTO-IMPORT] CSV 임포트 시작: {target_csv.name}")
        print(f"{'='*60}\n")

        try:
            # import_products 커맨드 실행
            call_command('import_products', str(target_csv))
            print(f"\n[AUTO-IMPORT] CSV 임포트 완료!")
        except Exception as e:
            print(f"\n[AUTO-IMPORT] ERROR: CSV 임포트 실패: {str(e)}")
            import traceback
            traceback.print_exc()
