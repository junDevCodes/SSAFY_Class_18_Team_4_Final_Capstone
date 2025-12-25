"""
Products 앱 설정

서버 시작 시:
1. JSON 데이터 파이프라인 자동 확인 및 처리
2. GMS 재료 추출 미처리 상품 확인 및 Celery 태스크 발행
"""
import sys
import logging
from django.apps import AppConfig
from django.conf import settings

logger = logging.getLogger(__name__)


class ProductsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'products'

    def ready(self):
        """앱 초기화 시 실행 (runserver/gunicorn 시작 시)"""
        # 마이그레이션 중이거나 다른 명령어 실행 중이면 스킵
        skip_commands = [
            'migrate', 'makemigrations', 'shell', 'createsuperuser',
            'import_products', 'process_json_data', 'watch_pipeline',
            'batch_extract_ingredients', 'collectstatic', 'check',
        ]
        if any(cmd in sys.argv for cmd in skip_commands):
            return

        # runserver 또는 gunicorn(wsgi) 실행 시에만 동작
        is_runserver = 'runserver' in sys.argv
        is_gunicorn = 'gunicorn' in sys.argv[0] if sys.argv else False

        if not (is_runserver or is_gunicorn):
            return

        # 환경변수로 자동 처리 비활성화 가능
        if not getattr(settings, 'PIPELINE_ENABLED', True):
            return

        # DB 접근을 지연시키기 위해 별도 스레드에서 실행
        import threading
        thread = threading.Thread(target=self._startup_health_check)
        thread.daemon = True
        thread.start()

    def _startup_health_check(self):
        """서버 시작 시 전체 상태 점검 및 자동 처리"""
        import time
        import os

        # Django 앱이 완전히 초기화될 때까지 대기
        initial_delay = int(os.getenv('PIPELINE_INITIAL_DELAY', 5))
        time.sleep(initial_delay)

        try:
            self._print_header("서버 시작 상태 점검")

            # 1. 파이프라인 상태 확인 및 처리
            pipeline_result = self._process_pipeline()

            # 2. GMS 추출 상태 확인 및 태스크 발행
            self._check_gms_extraction_status(pipeline_result)

            self._print_footer()

        except Exception as e:
            logger.error(f"서버 시작 상태 점검 중 오류: {e}")
            import traceback
            traceback.print_exc()

    def _process_pipeline(self) -> dict:
        """JSON 파이프라인 처리 및 결과 반환"""
        from products.models import Product
        from data_pipeline.processor import DataProcessor

        product_count = Product.objects.count()
        processor = DataProcessor()

        new_files = processor.check_new_files()
        pending_files = processor.get_pending_files()
        total_pending = len(new_files) + len(pending_files)

        print(f"[파이프라인] 상태")
        print(f"  - 현재 DB 상품 수: {product_count:,}개")
        print(f"  - processed 폴더: {len(new_files)}개")
        print(f"  - incoming 폴더: {len(pending_files)}개")

        result = {
            'processed': False,
            'new_products': 0,
            'new_product_ids': [],
        }

        if total_pending > 0:
            print(f"\n[파이프라인] {total_pending}개 파일 처리 시작...")

            pipeline_result = processor.process_all(dry_run=False, auto_move=True)

            print(f"[파이프라인] 처리 완료")
            print(f"  - 처리된 파일: {pipeline_result['processed_files']}개")
            print(f"  - 신규 상품: {pipeline_result['new_products']}개")
            print(f"  - 업데이트: {pipeline_result['updated_products']}개")

            if pipeline_result['failed_files'] > 0:
                print(f"  - 실패: {pipeline_result['failed_files']}개")

            result['processed'] = True
            result['new_products'] = pipeline_result['new_products']
            result['new_product_ids'] = pipeline_result.get('new_product_ids', [])
        else:
            print(f"[파이프라인] 처리할 파일 없음")

        return result

    def _check_gms_extraction_status(self, pipeline_result: dict):
        """GMS 재료 추출 상태 확인 및 미처리 상품 처리"""
        from products.models import Product

        print(f"\n[GMS 추출] 상태 확인")

        # 미처리 상품 수 조회
        null_count = Product.objects.filter(
            parsed_ingredients__isnull=True,
            status='active',
        ).count()

        # 저신뢰도 상품 수 조회 (Python 레벨 필터링)
        low_confidence_count = self._count_low_confidence_products()

        total_count = Product.objects.filter(status='active').count()
        extracted_count = total_count - null_count

        print(f"  - 전체 활성 상품: {total_count:,}개")
        print(f"  - 추출 완료: {extracted_count:,}개 ({100*extracted_count//total_count if total_count else 0}%)")
        print(f"  - 미처리 (NULL): {null_count:,}개")
        print(f"  - 저신뢰도 (<0.7): {low_confidence_count:,}개")

        # 파이프라인에서 신규 상품이 추가된 경우 검증
        if pipeline_result.get('new_product_ids'):
            new_ids = pipeline_result['new_product_ids']
            self._verify_gms_task_dispatch(new_ids)

        # 미처리 상품이 있으면 Celery 태스크 발행
        if null_count > 0:
            self._trigger_pending_extraction(null_count)

    def _count_low_confidence_products(self) -> int:
        """저신뢰도 상품 수 카운트 (Python 레벨)"""
        from products.models import Product

        low_count = 0
        min_confidence = getattr(settings, 'GMS_EXTRACTION_MIN_CONFIDENCE', 0.7)

        # 배치로 조회하여 메모리 효율성 확보
        products = Product.objects.exclude(
            parsed_ingredients__isnull=True
        ).values_list('parsed_ingredients', flat=True)[:5000]

        for parsed in products:
            if isinstance(parsed, dict):
                confidence = parsed.get('confidence', 0)
                if confidence < min_confidence:
                    low_count += 1

        return low_count

    def _verify_gms_task_dispatch(self, new_product_ids: list):
        """파이프라인 신규 상품의 GMS 태스크 발행 검증"""
        from products.models import Product

        print(f"\n[GMS 추출] 파이프라인 신규 상품 검증")
        print(f"  - 신규 상품 ID: {len(new_product_ids)}개")

        # 신규 상품 중 아직 추출되지 않은 것 확인
        pending = Product.objects.filter(
            id__in=new_product_ids,
            parsed_ingredients__isnull=True,
        ).count()

        already_done = len(new_product_ids) - pending

        print(f"  - 이미 추출됨: {already_done}개 (중복 상품)")
        print(f"  - 추출 대기: {pending}개")

        if pending > 0:
            print(f"  → GMS 태스크가 이미 발행되었거나 곧 처리될 예정입니다.")

    def _trigger_pending_extraction(self, null_count: int):
        """미처리 상품에 대한 GMS 추출 태스크 발행"""
        import os

        # 환경변수로 자동 발행 비활성화 가능
        auto_trigger = os.getenv('GMS_AUTO_TRIGGER_ON_STARTUP', 'true').lower() == 'true'

        if not auto_trigger:
            print(f"\n[GMS 추출] 자동 발행 비활성화됨 (GMS_AUTO_TRIGGER_ON_STARTUP=false)")
            print(f"  → Celery Beat가 매시 정각에 자동 처리합니다.")
            return

        # Celery가 사용 가능한지 확인
        try:
            from products.tasks import process_pending_extractions

            # 서버 시작 시 최대 발행 수 (환경변수로 조정 가능, 기본값 1000)
            max_startup_batch = int(os.getenv('GMS_STARTUP_BATCH_SIZE', 1000))
            batch_size = min(null_count, max_startup_batch)

            print(f"\n[GMS 추출] 미처리 상품 {batch_size}개에 대해 태스크 발행")

            # 비동기로 태스크 발행 (low_priority 큐)
            result = process_pending_extractions.apply_async(
                kwargs={
                    'batch_size': batch_size,
                    'use_fallback': True,
                },
                queue='low_priority',
            )

            print(f"  → 태스크 발행 완료: task_id={result.id}")

            if null_count > batch_size:
                remaining = null_count - batch_size
                print(f"  → 나머지 {remaining:,}개는 Celery Beat가 매시 정각에 처리합니다.")

        except ImportError:
            print(f"\n[GMS 추출] Celery 미설치 - 자동 발행 생략")
            print(f"  → python manage.py batch_extract_ingredients 명령어로 수동 처리하세요.")
        except Exception as e:
            logger.warning(f"GMS 태스크 발행 실패: {e}")
            print(f"\n[GMS 추출] 태스크 발행 실패: {e}")
            print(f"  → Redis 연결 상태를 확인하세요.")

    def _print_header(self, title: str):
        """헤더 출력"""
        print(f"\n{'='*60}")
        print(f"[SelF] {title}")
        print(f"{'='*60}")

    def _print_footer(self):
        """푸터 출력"""
        print(f"{'='*60}\n")
