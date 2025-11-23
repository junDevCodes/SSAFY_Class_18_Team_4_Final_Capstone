"""
CSV 파일에서 제품 데이터를 임포트하는 관리 커맨드
"""
import csv
import os
import re
from datetime import datetime
from urllib.parse import urlparse
from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify
from django.utils import timezone
from products.models import Category, Product


class Command(BaseCommand):
    """CSV 파일에서 제품 데이터를 임포트"""
    help = 'CSV 파일에서 제품 데이터를 임포트합니다'

    def add_arguments(self, parser):
        """커맨드 인자 추가"""
        parser.add_argument(
            'csv_file',
            type=str,
            help='임포트할 CSV 파일 경로'
        )
        parser.add_argument(
            '--skip-duplicates',
            action='store_true',
            help='중복 상품 건너뛰기 (상품명 + 가격 조합으로 판단)'
        )
        parser.add_argument(
            '--validate-images',
            action='store_true',
            help='이미지 URL 유효성 검사 활성화'
        )
        parser.add_argument(
            '--clear-existing',
            action='store_true',
            help='기존 데이터 삭제 후 임포트'
        )

    def validate_image_url(self, url):
        """이미지 URL 유효성 검사"""
        if not url:
            return False

        # URL 형식 검증
        try:
            result = urlparse(url)
            if not all([result.scheme, result.netloc]):
                return False
        except Exception:
            return False

        # 이미지 확장자 검증
        valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']
        url_lower = url.lower()
        if not any(url_lower.endswith(ext) or ext in url_lower for ext in valid_extensions):
            # 확장자가 없거나 쿼리 파라미터에 포함된 경우도 허용
            if '?' not in url_lower:
                return False

        return True

    def is_duplicate(self, name, price, category):
        """중복 상품 체크 (상품명 + 가격 + 카테고리)"""
        return Product.objects.filter(
            name=name,
            price=price,
            category=category
        ).exists()

    def handle(self, *args, **options):
        """커맨드 실행"""
        csv_file_path = options['csv_file']
        skip_duplicates = options.get('skip_duplicates', False)
        validate_images = options.get('validate_images', False)
        clear_existing = True

        # CSV 파일 존재 여부 확인
        if not os.path.exists(csv_file_path):
            raise CommandError(f'CSV 파일을 찾을 수 없습니다: {csv_file_path}')

        # 기존 데이터 삭제 (옵션)
        if clear_existing:
            self.stdout.write(self.style.WARNING('기존 데이터를 삭제합니다...'))
            deleted_products = Product.objects.count()
            deleted_categories = Category.objects.count()
            Product.objects.all().delete()
            Category.objects.all().delete()
            self.stdout.write(f'삭제됨: {deleted_products}개 제품, {deleted_categories}개 카테고리')

        # 통계 변수
        stats = {
            'total_rows': 0,
            'created': 0,
            'skipped_duplicate': 0,
            'skipped_invalid_image': 0,
            'failed': 0,
        }

        # 카테고리 캐시 (중복 방지)
        category_cache = {}

        # CSV 파일 읽기 및 임포트
        self.stdout.write(f'CSV 파일 읽기 시작: {csv_file_path}')

        with open(csv_file_path, 'r', encoding='utf-8-sig') as csvfile:
            reader = csv.DictReader(csvfile)

            for row in reader:
                stats['total_rows'] += 1

                try:
                    # 필수 필드 검증
                    product_name = row.get('product_name', '').strip()
                    image_url = row.get('image_url', '').strip()
                    price_str = row.get('price', '').strip()

                    if not product_name or not image_url or not price_str:
                        stats['failed'] += 1
                        self.stderr.write(
                            self.style.WARNING(
                                f'필수 필드 누락 (행 {stats["total_rows"]}): {product_name or "이름 없음"}'
                            )
                        )
                        continue

                    # 가격 파싱
                    try:
                        price = int(price_str)
                    except ValueError:
                        stats['failed'] += 1
                        self.stderr.write(
                            self.style.WARNING(
                                f'잘못된 가격 형식 (행 {stats["total_rows"]}): {product_name} - {price_str}'
                            )
                        )
                        continue

                    # 이미지 URL 검증 (옵션)
                    if validate_images and not self.validate_image_url(image_url):
                        stats['skipped_invalid_image'] += 1
                        self.stderr.write(
                            self.style.WARNING(
                                f'잘못된 이미지 URL (행 {stats["total_rows"]}): {product_name} - {image_url[:50]}...'
                            )
                        )
                        continue

                    # 카테고리 가져오기 또는 생성
                    category_name = row.get('category', '').strip() or '미분류'

                    if category_name not in category_cache:
                        category, created = Category.objects.get_or_create(
                            name=category_name,
                            defaults={
                                'slug': slugify(category_name, allow_unicode=True)
                            }
                        )
                        category_cache[category_name] = category
                    else:
                        category = category_cache[category_name]

                    # 중복 체크 (옵션)
                    if skip_duplicates and self.is_duplicate(product_name, price, category):
                        stats['skipped_duplicate'] += 1
                        continue

                    # 크롤링 시간 파싱 (있는 경우)
                    crawled_at = None
                    if row.get('crawled_at') and row['crawled_at'].strip():
                        try:
                            naive_dt = datetime.strptime(
                                row['crawled_at'].strip(),
                                '%Y-%m-%d %H:%M:%S'
                            )
                            crawled_at = timezone.make_aware(naive_dt)
                        except ValueError:
                            pass

                    # 제품 생성 (새 필드 지원)
                    Product.objects.create(
                        category=category,
                        # 새 필드
                        product_type='main',
                        source_site=row.get('site_name', '').strip() or None,
                        source_url=row.get('product_url', '').strip() or None,
                        main_image_url=image_url,
                        # 기본 정보
                        name=product_name,
                        price=price,
                        unit=row.get('unit', '').strip() or None,
                        description=row.get('description', '').strip() or None,
                        crawled_at=crawled_at,
                        # 이전 필드 (DEPRECATED, 하위 호환성 유지)
                        site_name=row.get('site_name', '').strip() or None,
                        product_url=row.get('product_url', '').strip() or None,
                        image_url=image_url,
                        detail_info=row.get('detail_info', '').strip() or None,
                    )
                    stats['created'] += 1

                    # 진행상황 출력 (100개마다)
                    if stats['created'] % 100 == 0:
                        self.stdout.write(f'처리 중... {stats["created"]}개 생성됨')

                except Exception as e:
                    stats['failed'] += 1
                    self.stderr.write(
                        self.style.ERROR(
                            f'제품 임포트 실패 (행 {stats["total_rows"]}): {product_name} - {str(e)}'
                        )
                    )
                    continue

        # 완료 메시지 및 통계
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('임포트 완료!'))
        self.stdout.write(f'성공적으로 임포트: {stats["created"]}')
        self.stdout.write('='*60)
        self.stdout.write(f'총 행 수:           {stats["total_rows"]}')
        self.stdout.write(self.style.SUCCESS(f'생성됨:             {stats["created"]}'))
        if stats['skipped_duplicate'] > 0:
            self.stdout.write(self.style.WARNING(f'중복 건너뜀:        {stats["skipped_duplicate"]}'))
        if stats['skipped_invalid_image'] > 0:
            self.stdout.write(self.style.WARNING(f'잘못된 이미지:      {stats["skipped_invalid_image"]}'))
        if stats['failed'] > 0:
            self.stdout.write(self.style.ERROR(f'실패:               {stats["failed"]}'))
        self.stdout.write(f'카테고리 수:        {len(category_cache)}')
        self.stdout.write('='*60)
