"""
Products 앱 설정

서버 시작 시 JSON 데이터 파이프라인을 자동으로 확인하고
대기 중인 파일이 있으면 처리합니다.
"""
import sys
from django.apps import AppConfig
from django.conf import settings


class ProductsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'products'

    def ready(self):
        """앱 초기화 시 실행 (runserver 시작 시)"""
        # 시그널 핸들러 등록 (Product 생성 시 관련 모델 자동 생성)
        import products.signals  # noqa: F401

        # 마이그레이션 중이거나 다른 명령어 실행 중이면 스킵
        skip_commands = [
            'migrate', 'makemigrations', 'shell', 'createsuperuser',
            'import_products', 'process_json_data', 'watch_pipeline'
        ]
        if any(cmd in sys.argv for cmd in skip_commands):
            return

        # runserver일 때만 실행
        if 'runserver' not in sys.argv:
            return

        # 개발 환경에서만 자동 처리 실행
        if settings.DEBUG:
            # DB 접근을 지연시키기 위해 별도 스레드에서 실행
            import threading
            thread = threading.Thread(target=self._auto_process_json_data)
            thread.daemon = True
            thread.start()

    def _auto_process_json_data(self):
        """서버 시작 시 JSON 파이프라인 자동 처리"""
        import time

        # Django 앱이 완전히 초기화될 때까지 대기
        time.sleep(2)

        try:
            from products.models import Product
            from data_pipeline.processor import DataProcessor

            # 현재 제품 수 확인
            product_count = Product.objects.count()

            # 데이터 프로세서 초기화
            processor = DataProcessor()

            # processed 폴더에서 새 파일 확인
            new_files = processor.check_new_files()

            # incoming 폴더의 대기 파일 확인
            pending_files = processor.get_pending_files()

            total_pending = len(new_files) + len(pending_files)

            # 상태 출력
            print(f"\n{'='*60}")
            print(f"[JSON-PIPELINE] 데이터 파이프라인 상태 확인")
            print(f"{'='*60}")
            print(f"  현재 DB 제품 수: {product_count}개")
            print(f"  processed 폴더 새 파일: {len(new_files)}개")
            print(f"  incoming 폴더 대기 파일: {len(pending_files)}개")

            # 대기 파일이 있으면 처리
            if total_pending > 0:
                print(f"\n[JSON-PIPELINE] 대기 중인 파일 {total_pending}개 처리 시작...")

                # 파이프라인 실행 (processed → incoming → DB → backup)
                results = processor.process_all(dry_run=False, auto_move=True)

                # 결과 출력
                print(f"\n[JSON-PIPELINE] 처리 완료!")
                print(f"  - 처리된 파일: {results['processed_files']}개")
                print(f"  - 신규 상품: {results['new_products']}개")
                print(f"  - 업데이트: {results['updated_products']}개")

                if results['failed_files'] > 0:
                    print(f"  - 실패: {results['failed_files']}개")
                    for err in results['errors']:
                        print(f"    * {err['file']}: {err['error']}")
            else:
                if product_count > 0:
                    print(f"\n[JSON-PIPELINE] 처리할 파일 없음 - DB에 {product_count}개 제품 존재")
                else:
                    print(f"\n[JSON-PIPELINE] 처리할 파일 없음")
                    print(f"  크롤링된 JSON 파일을 data/json/processed/ 폴더에 넣어주세요.")

            print(f"{'='*60}\n")

        except Exception as e:
            # 마이그레이션이 안 된 경우, 테이블 없는 경우 등 무시
            import traceback
            print(f"\n[JSON-PIPELINE] 파이프라인 확인 중 오류 발생: {str(e)}")
            traceback.print_exc()
