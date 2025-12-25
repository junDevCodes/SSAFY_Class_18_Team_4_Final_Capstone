"""
심사용 Fixtures 데이터 로드 커맨드

data/fixtures/ 폴더의 CSV 파일을 DB에 로드합니다.
프로덕션 서비스에 영향을 주지 않으며, 수동 실행만 가능합니다.

사용법:
    python manage.py load_fixtures                    # 기본 로드 (기존 데이터 있으면 스킵)
    python manage.py load_fixtures --clear            # 기존 데이터 삭제 후 로드
    python manage.py load_fixtures --dry-run          # 검증만 수행
    python manage.py load_fixtures --skip-if-exists   # 데이터 존재 시 완전 스킵
"""
import csv
import json
import os
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model

from products.models import (
    Category,
    Product,
    ProductDetail,
    ProductInventory,
    ProductImage,
    ProductPriceHistory,
    ProductStats,
)
from sellers.models import Seller


User = get_user_model()


class Command(BaseCommand):
    """심사용 Fixtures 데이터 로드 커맨드"""

    help = '심사용 fixtures 데이터를 DB에 로드합니다'

    @staticmethod
    def get_default_fixtures_dir() -> Path:
        """기본 fixtures 폴더 경로 반환 (Docker/로컬 환경 자동 감지)"""
        # Docker 환경: /app/data/fixtures
        docker_path = Path('/app/data/fixtures')
        if docker_path.exists():
            return docker_path

        # 로컬 환경: BASE_DIR/../data/fixtures
        local_path = Path(settings.BASE_DIR).parent / 'data' / 'fixtures'
        if local_path.exists():
            return local_path

        # 둘 다 없으면 로컬 경로 반환 (에러 메시지용)
        return local_path

    # 로드 순서 및 파일 매핑 (의존성 순서)
    FIXTURE_FILES = {
        'categories': 'categories_*.csv',
        'products': 'products_*.csv',
        'product_details': 'product_details_*.csv',
        'product_inventories': 'product_inventories_*.csv',
        'product_images': 'product_images_*.csv',
        'product_price_histories': 'product_price_histories_*.csv',
        'product_stats': 'product_stats_*.csv',
    }

    def add_arguments(self, parser):
        """커맨드 인자 정의"""
        parser.add_argument(
            '--clear',
            action='store_true',
            help='기존 상품 관련 데이터 삭제 후 로드 (심사용)',
        )
        parser.add_argument(
            '--skip-if-exists',
            action='store_true',
            help='상품 데이터가 이미 존재하면 로드 스킵',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='실제 DB 삽입 없이 검증만 수행',
        )
        parser.add_argument(
            '--fixtures-dir',
            type=str,
            help='fixtures 폴더 경로 (기본값: data/fixtures/)',
        )

    def get_fixture_file(self, pattern: str) -> Path | None:
        """패턴에 맞는 fixture 파일 찾기 (가장 최근 파일)"""
        import glob

        search_path = self.fixtures_dir / pattern
        files = glob.glob(str(search_path))

        if not files:
            return None

        # 가장 최근 파일 반환 (파일명에 타임스탬프 포함 가정)
        return Path(sorted(files, reverse=True)[0])

    def parse_datetime(self, value: str) -> datetime | None:
        """날짜/시간 문자열 파싱"""
        if not value or value.strip() == '':
            return None

        formats = [
            '%Y-%m-%d %H:%M:%S.%f %z',
            '%Y-%m-%d %H:%M:%S %z',
            '%Y-%m-%d %H:%M:%S.%f',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d',
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(value.strip(), fmt)
                if dt.tzinfo is None:
                    dt = timezone.make_aware(dt)
                return dt
            except ValueError:
                continue

        return None

    def parse_int(self, value: str, default: int = 0) -> int:
        """정수 파싱"""
        if not value or value.strip() == '':
            return default
        try:
            return int(value)
        except ValueError:
            return default

    def parse_decimal(self, value: str, default: str = '0.00') -> Decimal:
        """Decimal 파싱"""
        if not value or value.strip() == '':
            return Decimal(default)
        try:
            return Decimal(value)
        except InvalidOperation:
            return Decimal(default)

    def parse_bool(self, value: str, default: bool = False) -> bool:
        """Boolean 파싱"""
        if not value or value.strip() == '':
            return default
        return value.lower() in ('true', '1', 't', 'yes')

    def parse_json(self, value: str) -> dict | list | None:
        """JSON 파싱"""
        if not value or value.strip() == '':
            return None
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return None

    def get_or_create_default_seller(self) -> Seller:
        """기본 판매자 생성 또는 가져오기 (id=1 보장)"""
        # 먼저 id=1인 seller가 있는지 확인
        seller = Seller.objects.filter(id=1).first()
        if seller:
            return seller

        # 기본 사용자 생성/가져오기
        default_email = "system@fixtures.local"
        user, _ = User.objects.get_or_create(
            email=default_email,
            defaults={
                'username': 'fixtures_system',
                'is_active': True,
            }
        )

        # id=1로 seller 생성 (기존 seller가 없는 경우만)
        if not Seller.objects.exists():
            seller = Seller.objects.create(
                id=1,
                user=user,
                brand_name='홈플러스',
                brand_slug='homeplus',
                status='active',
            )
        else:
            # 기존 seller가 있지만 id=1이 없는 경우
            seller, _ = Seller.objects.get_or_create(
                user=user,
                defaults={
                    'brand_name': '홈플러스',
                    'brand_slug': 'homeplus',
                    'status': 'active',
                }
            )

        return seller

    def load_categories(self, file_path: Path, dry_run: bool = False) -> dict:
        """카테고리 로드"""
        stats = {'loaded': 0, 'skipped': 0, 'failed': 0}
        id_mapping = {}  # CSV id -> DB id 매핑

        with open(file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)

            for row in reader:
                try:
                    csv_id = self.parse_int(row.get('id'))
                    parent_id = self.parse_int(row.get('parent_id')) or None

                    if dry_run:
                        stats['loaded'] += 1
                        continue

                    # 카테고리 생성 (ID 유지)
                    category, created = Category.objects.update_or_create(
                        id=csv_id,
                        defaults={
                            'name': row.get('name', '').strip(),
                            'slug': row.get('slug', '').strip(),
                            'parent_id': parent_id,
                        }
                    )
                    id_mapping[csv_id] = category.id

                    if created:
                        stats['loaded'] += 1
                    else:
                        stats['skipped'] += 1

                except Exception as e:
                    stats['failed'] += 1
                    self.stderr.write(f"  카테고리 로드 실패 (id={row.get('id')}): {e}")

        return stats

    def load_products(self, file_path: Path, seller: Seller, dry_run: bool = False) -> dict:
        """상품 로드"""
        stats = {'loaded': 0, 'skipped': 0, 'failed': 0}
        batch_size = 500
        products_to_create = []
        products_to_update = []

        with open(file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)

            for row in reader:
                try:
                    csv_id = self.parse_int(row.get('id'))
                    category_id = self.parse_int(row.get('category_id')) or None

                    if dry_run:
                        stats['loaded'] += 1
                        continue

                    # parsed_ingredients JSON 파싱
                    parsed_ingredients = self.parse_json(row.get('parsed_ingredients'))

                    product_data = {
                        'id': csv_id,
                        'seller_id': seller.id,
                        'category_id': category_id,
                        'source_site': row.get('source_site', '').strip() or None,
                        'source_url': row.get('source_url', '').strip() or None,
                        'crawled_at': self.parse_datetime(row.get('crawled_at')),
                        'name': row.get('name', '').strip(),
                        'slug': row.get('slug', '').strip(),
                        'price': self.parse_int(row.get('price')),
                        'original_price': self.parse_int(row.get('original_price')) or None,
                        'status': row.get('status', 'active').strip(),
                        'product_type': row.get('product_type', 'main').strip(),
                        'unit': row.get('unit', '').strip() or None,
                        'unit_quantity': self.parse_decimal(row.get('unit_quantity'), '1.00'),
                        'shipping_required': self.parse_bool(row.get('shipping_required'), True),
                        'shipping_fee': self.parse_int(row.get('shipping_fee')),
                        'free_shipping_threshold': self.parse_int(row.get('free_shipping_threshold')) or None,
                        'estimated_delivery_days': self.parse_int(row.get('estimated_delivery_days')) or None,
                        'parsed_ingredients': parsed_ingredients,
                    }

                    # 기존 상품 확인
                    existing = Product.objects.filter(id=csv_id).first()
                    if existing:
                        for key, value in product_data.items():
                            if key != 'id':
                                setattr(existing, key, value)
                        products_to_update.append(existing)
                        stats['skipped'] += 1
                    else:
                        products_to_create.append(Product(**product_data))
                        stats['loaded'] += 1

                    # 배치 처리
                    if len(products_to_create) >= batch_size:
                        Product.objects.bulk_create(products_to_create, ignore_conflicts=True)
                        products_to_create = []
                        self.stdout.write(f"    진행 중... {stats['loaded']}개 로드됨")

                    if len(products_to_update) >= batch_size:
                        Product.objects.bulk_update(
                            products_to_update,
                            fields=['seller_id', 'category_id', 'source_site', 'source_url',
                                   'crawled_at', 'name', 'slug', 'price', 'original_price',
                                   'status', 'product_type', 'unit', 'unit_quantity',
                                   'shipping_required', 'shipping_fee', 'free_shipping_threshold',
                                   'estimated_delivery_days', 'parsed_ingredients']
                        )
                        products_to_update = []

                except Exception as e:
                    stats['failed'] += 1
                    self.stderr.write(f"  상품 로드 실패 (id={row.get('id')}): {e}")

        # 남은 배치 처리
        if products_to_create:
            Product.objects.bulk_create(products_to_create, ignore_conflicts=True)
        if products_to_update:
            Product.objects.bulk_update(
                products_to_update,
                fields=['seller_id', 'category_id', 'source_site', 'source_url',
                       'crawled_at', 'name', 'slug', 'price', 'original_price',
                       'status', 'product_type', 'unit', 'unit_quantity',
                       'shipping_required', 'shipping_fee', 'free_shipping_threshold',
                       'estimated_delivery_days', 'parsed_ingredients']
            )

        return stats

    def load_product_details(self, file_path: Path, dry_run: bool = False) -> dict:
        """상품 상세 로드"""
        stats = {'loaded': 0, 'skipped': 0, 'failed': 0}
        batch = []
        batch_size = 500

        with open(file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)

            for row in reader:
                try:
                    product_id = self.parse_int(row.get('product_id'))

                    if dry_run:
                        stats['loaded'] += 1
                        continue

                    # 상품 존재 확인
                    if not Product.objects.filter(id=product_id).exists():
                        stats['skipped'] += 1
                        continue

                    # full_image_description JSON 파싱
                    full_image_desc = self.parse_json(row.get('full_image_description'))

                    detail_data = {
                        'product_id': product_id,
                        'short_description': row.get('short_description', '').strip() or None,
                        'full_description': row.get('full_description', '').strip() or None,
                        'full_image_description': full_image_desc or [],
                        'full_text_description': row.get('full_text_description', '').strip() or None,
                        'meta_title': row.get('meta_title', '').strip() or None,
                        'meta_keywords': row.get('meta_keywords', '').strip() or None,
                    }

                    batch.append(ProductDetail(**detail_data))
                    stats['loaded'] += 1

                    if len(batch) >= batch_size:
                        ProductDetail.objects.bulk_create(
                            batch,
                            update_conflicts=True,
                            unique_fields=['product_id'],
                            update_fields=['short_description', 'full_description',
                                          'full_image_description', 'full_text_description',
                                          'meta_title', 'meta_keywords']
                        )
                        batch = []

                except Exception as e:
                    stats['failed'] += 1
                    self.stderr.write(f"  상세 로드 실패 (product_id={row.get('product_id')}): {e}")

        if batch:
            ProductDetail.objects.bulk_create(
                batch,
                update_conflicts=True,
                unique_fields=['product_id'],
                update_fields=['short_description', 'full_description',
                              'full_image_description', 'full_text_description',
                              'meta_title', 'meta_keywords']
            )

        return stats

    def load_product_inventories(self, file_path: Path, dry_run: bool = False) -> dict:
        """재고 정보 로드"""
        stats = {'loaded': 0, 'skipped': 0, 'failed': 0}
        batch = []
        batch_size = 500

        with open(file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)

            for row in reader:
                try:
                    product_id = self.parse_int(row.get('product_id'))

                    if dry_run:
                        stats['loaded'] += 1
                        continue

                    if not Product.objects.filter(id=product_id).exists():
                        stats['skipped'] += 1
                        continue

                    inventory_data = {
                        'product_id': product_id,
                        'stock_quantity': self.parse_int(row.get('stock_quantity')),
                        'safe_stock_level': self.parse_int(row.get('safe_stock_level'), 10),
                        'is_unlimited': self.parse_bool(row.get('is_unlimited')),
                    }

                    batch.append(ProductInventory(**inventory_data))
                    stats['loaded'] += 1

                    if len(batch) >= batch_size:
                        ProductInventory.objects.bulk_create(
                            batch,
                            update_conflicts=True,
                            unique_fields=['product_id'],
                            update_fields=['stock_quantity', 'safe_stock_level', 'is_unlimited']
                        )
                        batch = []

                except Exception as e:
                    stats['failed'] += 1
                    self.stderr.write(f"  재고 로드 실패 (product_id={row.get('product_id')}): {e}")

        if batch:
            ProductInventory.objects.bulk_create(
                batch,
                update_conflicts=True,
                unique_fields=['product_id'],
                update_fields=['stock_quantity', 'safe_stock_level', 'is_unlimited']
            )

        return stats

    def load_product_images(self, file_path: Path, dry_run: bool = False) -> dict:
        """상품 이미지 로드"""
        stats = {'loaded': 0, 'skipped': 0, 'failed': 0}
        batch = []
        batch_size = 1000

        # 기존 이미지 ID 수집 (중복 방지)
        existing_ids = set(ProductImage.objects.values_list('id', flat=True))

        with open(file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)

            for row in reader:
                try:
                    image_id = self.parse_int(row.get('id'))
                    product_id = self.parse_int(row.get('product_id'))

                    if dry_run:
                        stats['loaded'] += 1
                        continue

                    if image_id in existing_ids:
                        stats['skipped'] += 1
                        continue

                    if not Product.objects.filter(id=product_id).exists():
                        stats['skipped'] += 1
                        continue

                    image_data = {
                        'id': image_id,
                        'product_id': product_id,
                        'image_url': row.get('image_url', '').strip(),
                        'display_order': self.parse_int(row.get('display_order')),
                    }

                    batch.append(ProductImage(**image_data))
                    stats['loaded'] += 1

                    if len(batch) >= batch_size:
                        ProductImage.objects.bulk_create(batch, ignore_conflicts=True)
                        batch = []
                        self.stdout.write(f"    진행 중... {stats['loaded']}개 로드됨")

                except Exception as e:
                    stats['failed'] += 1
                    self.stderr.write(f"  이미지 로드 실패 (id={row.get('id')}): {e}")

        if batch:
            ProductImage.objects.bulk_create(batch, ignore_conflicts=True)

        return stats

    def load_product_price_histories(self, file_path: Path, dry_run: bool = False) -> dict:
        """가격 이력 로드"""
        stats = {'loaded': 0, 'skipped': 0, 'failed': 0}
        batch = []
        batch_size = 1000

        existing_ids = set(ProductPriceHistory.objects.values_list('id', flat=True))

        with open(file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)

            for row in reader:
                try:
                    history_id = self.parse_int(row.get('id'))
                    product_id = self.parse_int(row.get('product_id'))

                    if dry_run:
                        stats['loaded'] += 1
                        continue

                    if history_id in existing_ids:
                        stats['skipped'] += 1
                        continue

                    if not Product.objects.filter(id=product_id).exists():
                        stats['skipped'] += 1
                        continue

                    history_data = {
                        'id': history_id,
                        'product_id': product_id,
                        'price': self.parse_int(row.get('price')),
                        'original_price': self.parse_int(row.get('original_price')) or None,
                        'previous_price': self.parse_int(row.get('previous_price')) or None,
                        'price_change': self.parse_int(row.get('price_change')) or None,
                        'price_change_rate': self.parse_decimal(row.get('price_change_rate')) if row.get('price_change_rate') else None,
                        'is_current': self.parse_bool(row.get('is_current')),
                        'source': row.get('source', '').strip() or None,
                    }

                    batch.append(ProductPriceHistory(**history_data))
                    stats['loaded'] += 1

                    if len(batch) >= batch_size:
                        ProductPriceHistory.objects.bulk_create(batch, ignore_conflicts=True)
                        batch = []

                except Exception as e:
                    stats['failed'] += 1
                    self.stderr.write(f"  가격이력 로드 실패 (id={row.get('id')}): {e}")

        if batch:
            ProductPriceHistory.objects.bulk_create(batch, ignore_conflicts=True)

        return stats

    def load_product_stats(self, file_path: Path, dry_run: bool = False) -> dict:
        """상품 통계 로드"""
        stats = {'loaded': 0, 'skipped': 0, 'failed': 0}
        batch = []
        batch_size = 500

        with open(file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)

            for row in reader:
                try:
                    product_id = self.parse_int(row.get('product_id'))

                    if dry_run:
                        stats['loaded'] += 1
                        continue

                    if not Product.objects.filter(id=product_id).exists():
                        stats['skipped'] += 1
                        continue

                    stats_data = {
                        'product_id': product_id,
                        'view_count': self.parse_int(row.get('view_count')),
                        'recommend_clicked_count': self.parse_int(row.get('recommend_clicked_count')),
                        'cart_event_count': self.parse_int(row.get('cart_event_count')),
                        'order_event_count': self.parse_int(row.get('order_event_count')),
                        'wishlist_count': self.parse_int(row.get('wishlist_count')),
                        'review_count': self.parse_int(row.get('review_count')),
                        'average_rating': self.parse_decimal(row.get('average_rating'), '0.00'),
                        'photo_review_count': self.parse_int(row.get('photo_review_count')),
                        'sentiment_score_avg': self.parse_decimal(row.get('sentiment_score_avg'), '0.00'),
                        'first_review_at': self.parse_datetime(row.get('first_review_at')),
                        'quality_score': self.parse_decimal(row.get('quality_score'), '50.00'),
                        'image_quality_score': self.parse_decimal(row.get('image_quality_score'), '50.00'),
                        'content_quality_score': self.parse_decimal(row.get('content_quality_score'), '50.00'),
                    }

                    batch.append(ProductStats(**stats_data))
                    stats['loaded'] += 1

                    if len(batch) >= batch_size:
                        ProductStats.objects.bulk_create(
                            batch,
                            update_conflicts=True,
                            unique_fields=['product_id'],
                            update_fields=['view_count', 'recommend_clicked_count', 'cart_event_count',
                                          'order_event_count', 'wishlist_count', 'review_count',
                                          'average_rating', 'photo_review_count', 'sentiment_score_avg',
                                          'first_review_at', 'quality_score', 'image_quality_score',
                                          'content_quality_score']
                        )
                        batch = []

                except Exception as e:
                    stats['failed'] += 1
                    self.stderr.write(f"  통계 로드 실패 (product_id={row.get('product_id')}): {e}")

        if batch:
            ProductStats.objects.bulk_create(
                batch,
                update_conflicts=True,
                unique_fields=['product_id'],
                update_fields=['view_count', 'recommend_clicked_count', 'cart_event_count',
                              'order_event_count', 'wishlist_count', 'review_count',
                              'average_rating', 'photo_review_count', 'sentiment_score_avg',
                              'first_review_at', 'quality_score', 'image_quality_score',
                              'content_quality_score']
            )

        return stats

    def clear_existing_data(self):
        """기존 상품 관련 데이터 삭제"""
        self.stdout.write(self.style.WARNING('기존 데이터를 삭제합니다...'))

        # 의존성 역순으로 삭제
        deleted_counts = {
            'ProductStats': ProductStats.objects.all().delete()[0],
            'ProductPriceHistory': ProductPriceHistory.objects.all().delete()[0],
            'ProductImage': ProductImage.objects.all().delete()[0],
            'ProductInventory': ProductInventory.objects.all().delete()[0],
            'ProductDetail': ProductDetail.objects.all().delete()[0],
            'Product': Product.objects.all().delete()[0],
            'Category': Category.objects.all().delete()[0],
        }

        for model, count in deleted_counts.items():
            self.stdout.write(f"  {model}: {count}개 삭제됨")

    def handle(self, *args, **options):
        """커맨드 실행"""
        clear = options.get('clear', False)
        skip_if_exists = options.get('skip_if_exists', False)
        dry_run = options.get('dry_run', False)
        fixtures_dir = options.get('fixtures_dir')

        # fixtures 폴더 설정 (Docker/로컬 환경 자동 감지)
        if fixtures_dir:
            self.fixtures_dir = Path(fixtures_dir)
        else:
            self.fixtures_dir = self.get_default_fixtures_dir()

        # fixtures 폴더 존재 확인
        if not self.fixtures_dir.exists():
            raise CommandError(f'fixtures 폴더를 찾을 수 없습니다: {self.fixtures_dir}')

        self.stdout.write('=' * 60)
        self.stdout.write(self.style.SUCCESS('심사용 Fixtures 데이터 로드'))
        self.stdout.write('=' * 60)
        self.stdout.write(f'Fixtures 폴더: {self.fixtures_dir}')

        if dry_run:
            self.stdout.write(self.style.WARNING('[DRY-RUN 모드] 실제 DB 변경 없음'))

        # 데이터 존재 확인
        if skip_if_exists and Product.objects.exists():
            product_count = Product.objects.count()
            self.stdout.write(
                self.style.SUCCESS(f'[SKIP] 상품 데이터가 이미 존재합니다 ({product_count}개)')
            )
            return

        # fixture 파일 확인
        self.stdout.write('\n파일 확인 중...')
        fixture_files = {}
        for key, pattern in self.FIXTURE_FILES.items():
            file_path = self.get_fixture_file(pattern)
            if file_path:
                fixture_files[key] = file_path
                self.stdout.write(f"  [OK] {key}: {file_path.name}")
            else:
                self.stdout.write(self.style.WARNING(f"  [MISSING] {key}: {pattern}"))

        if 'products' not in fixture_files:
            raise CommandError('products CSV 파일이 필수입니다')

        # 트랜잭션 내에서 로드
        try:
            with transaction.atomic():
                if dry_run:
                    # dry-run 모드에서는 트랜잭션 롤백을 위해 savepoint 사용
                    pass

                # 기존 데이터 삭제 (옵션)
                if clear and not dry_run:
                    self.clear_existing_data()

                # 1. 기본 Seller 생성
                self.stdout.write('\n[1/7] 기본 판매자 설정...')
                if not dry_run:
                    seller = self.get_or_create_default_seller()
                    self.stdout.write(f"  판매자: {seller.brand_name} (id={seller.id})")
                else:
                    seller = None
                    self.stdout.write("  [DRY-RUN] 판매자 생성 스킵")

                # 2. Categories 로드
                if 'categories' in fixture_files:
                    self.stdout.write('\n[2/7] 카테고리 로드...')
                    stats = self.load_categories(fixture_files['categories'], dry_run)
                    self.stdout.write(f"  로드: {stats['loaded']}, 스킵: {stats['skipped']}, 실패: {stats['failed']}")

                # 3. Products 로드
                self.stdout.write('\n[3/7] 상품 로드...')
                stats = self.load_products(fixture_files['products'], seller, dry_run)
                self.stdout.write(f"  로드: {stats['loaded']}, 업데이트: {stats['skipped']}, 실패: {stats['failed']}")

                # 4. Product Details 로드
                if 'product_details' in fixture_files:
                    self.stdout.write('\n[4/7] 상품 상세 로드...')
                    stats = self.load_product_details(fixture_files['product_details'], dry_run)
                    self.stdout.write(f"  로드: {stats['loaded']}, 스킵: {stats['skipped']}, 실패: {stats['failed']}")

                # 5. Product Inventories 로드
                if 'product_inventories' in fixture_files:
                    self.stdout.write('\n[5/7] 재고 정보 로드...')
                    stats = self.load_product_inventories(fixture_files['product_inventories'], dry_run)
                    self.stdout.write(f"  로드: {stats['loaded']}, 스킵: {stats['skipped']}, 실패: {stats['failed']}")

                # 6. Product Images 로드
                if 'product_images' in fixture_files:
                    self.stdout.write('\n[6/7] 상품 이미지 로드...')
                    stats = self.load_product_images(fixture_files['product_images'], dry_run)
                    self.stdout.write(f"  로드: {stats['loaded']}, 스킵: {stats['skipped']}, 실패: {stats['failed']}")

                # 7. Product Price Histories 로드
                if 'product_price_histories' in fixture_files:
                    self.stdout.write('\n[7/7] 가격 이력 로드...')
                    stats = self.load_product_price_histories(fixture_files['product_price_histories'], dry_run)
                    self.stdout.write(f"  로드: {stats['loaded']}, 스킵: {stats['skipped']}, 실패: {stats['failed']}")

                # 8. Product Stats 로드 (추가)
                if 'product_stats' in fixture_files:
                    self.stdout.write('\n[+] 상품 통계 로드...')
                    stats = self.load_product_stats(fixture_files['product_stats'], dry_run)
                    self.stdout.write(f"  로드: {stats['loaded']}, 스킵: {stats['skipped']}, 실패: {stats['failed']}")

                if dry_run:
                    # dry-run 모드: 롤백
                    raise CommandError('[DRY-RUN] 검증 완료 - 롤백됨')

        except CommandError:
            if dry_run:
                self.stdout.write(self.style.SUCCESS('\n[DRY-RUN] 검증 완료!'))
                return
            raise

        # 최종 통계 출력
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('로드 완료!'))
        self.stdout.write('=' * 60)
        self.stdout.write(f'카테고리: {Category.objects.count()}개')
        self.stdout.write(f'상품: {Product.objects.count()}개')
        self.stdout.write(f'상품 상세: {ProductDetail.objects.count()}개')
        self.stdout.write(f'재고: {ProductInventory.objects.count()}개')
        self.stdout.write(f'이미지: {ProductImage.objects.count()}개')
        self.stdout.write(f'가격 이력: {ProductPriceHistory.objects.count()}개')
        self.stdout.write(f'상품 통계: {ProductStats.objects.count()}개')
        self.stdout.write('=' * 60)
