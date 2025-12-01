# Generated migration to populate product slugs

from django.db import migrations
from django.utils.text import slugify


def populate_slugs(apps, schema_editor):
    """기존 Product들의 slug 자동 생성"""
    Product = apps.get_model('products', 'Product')

    for product in Product.objects.filter(slug__isnull=True):
        base_slug = slugify(product.name, allow_unicode=True)
        slug = base_slug
        counter = 1

        # 중복 방지
        while Product.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        product.slug = slug
        product.save(update_fields=['slug'])


def reverse_populate(apps, schema_editor):
    """되돌리기: slug를 NULL로 설정"""
    Product = apps.get_model('products', 'Product')
    Product.objects.all().update(slug=None)


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0007_productview'),
    ]

    operations = [
        migrations.RunPython(populate_slugs, reverse_populate),
    ]
