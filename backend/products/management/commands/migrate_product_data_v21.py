"""
Product 데이터 v2.1 마이그레이션 커맨드

기존 Product 테이블의 데이터를 신규 분리 테이블로 마이그레이션합니다.

사용법:
    python manage.py migrate_product_data_v21 [--dry-run]

예시:
    # 시뮬레이션 실행
    python manage.py migrate_product_data_v21 --dry-run

    # 실제 마이그레이션 실행
    python manage.py migrate_product_data_v21
"""

from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = '기존 Product 데이터를 v2.1 분리 테이블(detail, inventory, stats)로 마이그레이션합니다.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='실제 DB 작업 없이 시뮬레이션만 수행'
        )

    def handle(self, *args, **options):
        from products.models import (
            Product, ProductDetail, ProductInventory, ProductStats
        )

        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING(
                "\n[시뮬레이션 모드] 실제 DB 작업은 수행하지 않습니다.\n"
            ))

        products = Product.objects.all()
        total = products.count()

        self.stdout.write(f"[정보] 총 상품 수: {total}개")

        # 기존 분리 테이블 데이터 카운트
        detail_count = ProductDetail.objects.count()
        inventory_count = ProductInventory.objects.count()
        stats_count = ProductStats.objects.count()

        self.stdout.write(f"[정보] 기존 ProductDetail: {detail_count}개")
        self.stdout.write(f"[정보] 기존 ProductInventory: {inventory_count}개")
        self.stdout.write(f"[정보] 기존 ProductStats: {stats_count}개")

        migrated_detail = 0
        migrated_inventory = 0
        migrated_stats = 0

        if not dry_run:
            with transaction.atomic():
                for product in products:
                    # ProductDetail 생성 (없는 경우만)
                    if not hasattr(product, 'detail') or product.detail is None:
                        try:
                            ProductDetail.objects.get(product=product)
                        except ProductDetail.DoesNotExist:
                            ProductDetail.objects.create(
                                product=product,
                                short_description=product.short_description,
                                full_description=product.description,
                                meta_title=product.meta_title,
                                meta_keywords=product.meta_keywords,
                            )
                            migrated_detail += 1

                    # ProductInventory 생성 (없는 경우만)
                    if not hasattr(product, 'inventory') or product.inventory is None:
                        try:
                            ProductInventory.objects.get(product=product)
                        except ProductInventory.DoesNotExist:
                            ProductInventory.objects.create(
                                product=product,
                                stock_quantity=product.stock_quantity,
                                safe_stock_level=product.low_stock_threshold,
                            )
                            migrated_inventory += 1

                    # ProductStats 생성 (없는 경우만)
                    if not hasattr(product, 'stats') or product.stats is None:
                        try:
                            ProductStats.objects.get(product=product)
                        except ProductStats.DoesNotExist:
                            ProductStats.objects.create(
                                product=product,
                                view_count=product.view_count,
                                cart_event_count=product.cart_count,
                                order_event_count=product.purchase_count,
                                wishlist_count=product.wishlist_count,
                                review_count=product.review_count,
                                average_rating=product.average_rating,
                                quality_score=product.quality_score,
                                image_quality_score=product.image_quality_score,
                                content_quality_score=product.content_quality_score,
                            )
                            migrated_stats += 1
        else:
            # 시뮬레이션: 마이그레이션 대상 카운트
            for product in products:
                if not ProductDetail.objects.filter(product=product).exists():
                    migrated_detail += 1
                if not ProductInventory.objects.filter(product=product).exists():
                    migrated_inventory += 1
                if not ProductStats.objects.filter(product=product).exists():
                    migrated_stats += 1

        self.stdout.write("\n" + "=" * 40)
        self.stdout.write("마이그레이션 결과")
        self.stdout.write("=" * 40)

        self.stdout.write(self.style.SUCCESS(
            f"ProductDetail 마이그레이션: {migrated_detail}개"
        ))
        self.stdout.write(self.style.SUCCESS(
            f"ProductInventory 마이그레이션: {migrated_inventory}개"
        ))
        self.stdout.write(self.style.SUCCESS(
            f"ProductStats 마이그레이션: {migrated_stats}개"
        ))

        if dry_run:
            self.stdout.write(self.style.WARNING(
                "\n[시뮬레이션 완료] --dry-run 옵션을 제거하고 다시 실행하세요."
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                "\n[완료] 데이터 마이그레이션이 완료되었습니다."
            ))
