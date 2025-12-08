# Generated manually for is_unlimited field
# 크롤링 상품(product_type='main')은 재고 추적이 불가능하므로 무제한 재고로 설정

from django.db import migrations, models


def set_unlimited_for_crawled_products(apps, schema_editor):
    """기존 크롤링 상품(product_type='main')의 is_unlimited를 True로 설정"""
    Product = apps.get_model('products', 'Product')
    ProductInventory = apps.get_model('products', 'ProductInventory')

    # product_type='main'인 상품의 inventory를 무제한으로 설정
    crawled_product_ids = Product.objects.filter(
        product_type='main'
    ).values_list('id', flat=True)

    updated_count = ProductInventory.objects.filter(
        product_id__in=list(crawled_product_ids)
    ).update(is_unlimited=True)

    print(f"\n크롤링 상품 {updated_count}개의 재고를 무제한으로 설정했습니다.")


def reverse_unlimited(apps, schema_editor):
    """롤백: 모든 is_unlimited를 False로 복원"""
    ProductInventory = apps.get_model('products', 'ProductInventory')
    ProductInventory.objects.all().update(is_unlimited=False)


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0004_optimize_price_history'),
    ]

    operations = [
        # 1. is_unlimited 필드 추가
        migrations.AddField(
            model_name='productinventory',
            name='is_unlimited',
            field=models.BooleanField(
                default=False,
                help_text='크롤링 상품 등 재고 추적이 불가능한 상품은 True',
                verbose_name='무제한 재고',
            ),
        ),
        # 2. 기존 크롤링 상품 데이터 업데이트
        migrations.RunPython(
            set_unlimited_for_crawled_products,
            reverse_unlimited,
        ),
    ]
