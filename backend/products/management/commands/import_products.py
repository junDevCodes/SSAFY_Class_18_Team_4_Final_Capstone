"""
CSV 파일에서 제품 데이터를 임포트하는 관리 커맨드
"""
import csv
import os
from datetime import datetime
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

    def handle(self, *args, **options):
        """커맨드 실행"""
        csv_file_path = options['csv_file']

        # CSV 파일 존재 여부 확인
        if not os.path.exists(csv_file_path):
            raise CommandError(f'CSV 파일을 찾을 수 없습니다: {csv_file_path}')

        # 기존 데이터 삭제
        self.stdout.write('기존 데이터를 삭제합니다...')
        Product.objects.all().delete()
        Category.objects.all().delete()

        # 카테고리 캐시 (중복 방지)
        category_cache = {}

        # CSV 파일 읽기 및 임포트
        products_created = 0

        with open(csv_file_path, 'r', encoding='utf-8-sig') as csvfile:
            reader = csv.DictReader(csvfile)

            for row in reader:
                try:
                    # 카테고리 가져오기 또는 생성
                    category_name = row['category'].strip()

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

                    # 크롤링 시간 파싱 (있는 경우)
                    crawled_at = None
                    if row.get('crawled_at') and row['crawled_at'].strip():
                        try:
                            naive_dt = datetime.strptime(
                                row['crawled_at'].strip(),
                                '%Y-%m-%d %H:%M:%S'
                            )
                            # Timezone-aware datetime으로 변환
                            crawled_at = timezone.make_aware(naive_dt)
                        except ValueError:
                            # 파싱 실패 시 None으로 유지
                            pass

                    # 제품 생성
                    Product.objects.create(
                        category=category,
                        site_name=row.get('site_name', '').strip() or None,
                        name=row['product_name'].strip(),
                        price=int(row['price']),
                        unit=row.get('unit', '').strip() or None,
                        description=row.get('description', '').strip() or None,
                        product_url=row.get('product_url', '').strip() or None,
                        image_url=row['image_url'].strip(),
                        detail_info=row.get('detail_info', '').strip() or None,
                        crawled_at=crawled_at,
                    )
                    products_created += 1

                except Exception as e:
                    self.stderr.write(
                        self.style.WARNING(
                            f'제품 임포트 실패 (행 건너뜀): {row.get("product_name", "알 수 없음")} - {str(e)}'
                        )
                    )
                    continue

        # 완료 메시지
        self.stdout.write(
            self.style.SUCCESS(
                f'성공적으로 임포트되었습니다: {products_created}개 제품, {len(category_cache)}개 카테고리'
            )
        )
