"""
기존 상품에 대해 GMS 재료 추출을 배치로 실행하는 관리 커맨드

사용 예시:
    # 기본 실행 (parsed_ingredients가 없는 상품만, 100개씩)
    python manage.py batch_extract_ingredients

    # 1000개 제한, 딜레이 1초
    python manage.py batch_extract_ingredients --limit=1000 --delay=1.0

    # dry-run (테스트)
    python manage.py batch_extract_ingredients --dry-run

    # 신뢰도 낮은 상품 재처리
    python manage.py batch_extract_ingredients --reprocess --min-confidence=0.7

    # 특정 상품 ID부터 시작
    python manage.py batch_extract_ingredients --start-id=1000

    # 특정 카테고리만 처리
    python manage.py batch_extract_ingredients --category=채소
"""
import time
import logging
from django.core.management.base import BaseCommand
from django.db.models import Q
from products.models import Product

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'GMS를 사용하여 기존 상품의 재료 정보를 배치로 추출합니다'

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='한 번에 처리할 상품 수 (기본: 100)'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='최대 처리할 상품 수 (기본: 전체)'
        )
        parser.add_argument(
            '--delay',
            type=float,
            default=0.5,
            help='API 호출 간 딜레이 (초, 기본: 0.5)'
        )
        parser.add_argument(
            '--reprocess',
            action='store_true',
            help='이미 추출된 상품도 재처리'
        )
        parser.add_argument(
            '--min-confidence',
            type=float,
            default=0.0,
            help='재처리 시 최소 신뢰도 이하만 재처리 (기본: 0.0 = 전체)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='실제 저장하지 않고 테스트만 수행'
        )
        parser.add_argument(
            '--start-id',
            type=int,
            default=None,
            help='시작 상품 ID (이 ID 이상의 상품만 처리)'
        )
        parser.add_argument(
            '--category',
            type=str,
            default=None,
            help='특정 카테고리명의 상품만 처리'
        )
        parser.add_argument(
            '--status',
            type=str,
            default='active',
            choices=['active', 'draft', 'inactive', 'all'],
            help='처리할 상품 상태 (기본: active)'
        )
        parser.add_argument(
            '--use-fallback',
            action='store_true',
            help='GMS 실패 시 규칙 기반 폴백 사용'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='상세 로그 출력'
        )

    def handle(self, *args, **options):
        batch_size = options['batch_size']
        limit = options['limit']
        delay = options['delay']
        reprocess = options['reprocess']
        min_confidence = options['min_confidence']
        dry_run = options['dry_run']
        start_id = options['start_id']
        category = options['category']
        status = options['status']
        use_fallback = options['use_fallback']
        verbose = options['verbose']

        # GMS 추출기 초기화
        try:
            from products.services import get_gms_extractor
            extractor = get_gms_extractor()
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'GMS 추출기 초기화 실패: {e}'))
            return

        # 처리 대상 쿼리 구성
        queryset = Product.objects.all()

        # 상태 필터
        if status != 'all':
            queryset = queryset.filter(status=status)

        # 카테고리 필터
        if category:
            queryset = queryset.filter(category__name__icontains=category)

        # 시작 ID 필터
        if start_id:
            queryset = queryset.filter(id__gte=start_id)

        # 재처리 여부에 따른 필터
        if not reprocess:
            # parsed_ingredients가 없는 상품만
            queryset = queryset.filter(parsed_ingredients__isnull=True)
        elif reprocess and min_confidence > 0:
            # 재처리 모드 + min_confidence: parsed_ingredients가 있는 상품도 포함
            # Python 레벨에서 confidence 필터링 (DB 호환성)
            pass  # 아래에서 Python 필터링
        # reprocess=True이고 min_confidence=0이면 전체 상품 대상

        # ID 순으로 정렬 (일관성 있는 처리)
        queryset = queryset.order_by('id')

        # 상품 목록 조회 (재처리 시 parsed_ingredients도 필요)
        if reprocess and min_confidence > 0:
            products_qs = list(queryset.values_list('id', 'name', 'parsed_ingredients'))
            # Python 레벨에서 신뢰도 필터링
            products = []
            for product_id, product_name, parsed in products_qs:
                if parsed is None:
                    # parsed_ingredients가 없는 경우 포함
                    products.append((product_id, product_name))
                elif isinstance(parsed, dict):
                    # 신뢰도가 min_confidence 미만인 경우만 포함
                    confidence = parsed.get('confidence', 0)
                    if confidence < min_confidence:
                        products.append((product_id, product_name))
                # limit 적용
                if limit and len(products) >= limit:
                    break
        else:
            # 제한 적용
            if limit:
                queryset = queryset[:limit]
            products = list(queryset.values_list('id', 'name'))

        total = len(products)

        if total == 0:
            self.stdout.write(self.style.WARNING('처리할 상품이 없습니다.'))
            return

        self.stdout.write(f'처리 대상: {total}개 상품')
        self.stdout.write(f'설정: batch_size={batch_size}, delay={delay}s, dry_run={dry_run}')

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY-RUN 모드: 실제 저장하지 않음'))

        # 통계
        stats = {
            'success': 0,
            'failed': 0,
            'skipped': 0,
        }

        start_time = time.time()

        for i, (product_id, product_name) in enumerate(products):
            try:
                # GMS 추출
                if use_fallback:
                    parsed = extractor.extract_with_fallback(product_name)
                else:
                    parsed = extractor.extract_sync(product_name)

                if parsed:
                    if not dry_run:
                        Product.objects.filter(id=product_id).update(
                            parsed_ingredients=parsed.to_dict()
                        )
                    stats['success'] += 1

                    if verbose or (i + 1) % 10 == 0:
                        self.stdout.write(
                            f"[{i+1}/{total}] {product_name[:40]}... → "
                            f"{parsed.main_ingredient} ({parsed.confidence:.2f})"
                        )
                else:
                    stats['skipped'] += 1
                    if verbose:
                        self.stdout.write(
                            self.style.WARNING(f"[{i+1}/{total}] 스킵: {product_name[:40]}")
                        )

            except Exception as e:
                stats['failed'] += 1
                self.stderr.write(f"실패 (id={product_id}): {e}")

            # Rate limiting
            if delay > 0:
                time.sleep(delay)

            # 진행 상황 출력 (배치 단위)
            if (i + 1) % batch_size == 0:
                elapsed = time.time() - start_time
                rate = (i + 1) / elapsed if elapsed > 0 else 0
                eta = (total - i - 1) / rate if rate > 0 else 0

                self.stdout.write(
                    f"진행: {i+1}/{total} ({100*(i+1)//total}%) | "
                    f"성공: {stats['success']}, 실패: {stats['failed']} | "
                    f"속도: {rate:.1f}/s | ETA: {eta/60:.1f}분"
                )

        # 최종 결과
        elapsed_total = time.time() - start_time
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('배치 추출 완료!'))
        self.stdout.write(f"성공: {stats['success']}")
        self.stdout.write(f"실패: {stats['failed']}")
        self.stdout.write(f"스킵: {stats['skipped']}")
        self.stdout.write(f"소요 시간: {elapsed_total/60:.1f}분 ({elapsed_total:.0f}초)")
        if stats['success'] > 0:
            avg_time = elapsed_total / stats['success']
            self.stdout.write(f"평균 처리 시간: {avg_time:.2f}초/상품")
        self.stdout.write('=' * 60)
