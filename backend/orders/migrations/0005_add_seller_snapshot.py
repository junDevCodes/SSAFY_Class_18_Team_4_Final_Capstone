# Generated manually for HIGH-007: OrderItem seller snapshot fields
"""
OrderItem에 판매자 스냅샷 필드 추가

주문 시점의 판매자 정보를 보존하여:
- 판매자 정보 변경 시에도 과거 주문 기록 유지
- 판매자 탈퇴/삭제 시에도 주문 내역에서 판매자명 확인 가능
- 정산/분쟁 처리를 위한 증빙 자료 보존
"""

from django.db import migrations, models
import django.db.models.deletion


def populate_seller_snapshot(apps, schema_editor):
    """기존 OrderItem에 판매자 스냅샷 데이터 채우기 (데이터 마이그레이션)"""
    OrderItem = apps.get_model('orders', 'OrderItem')

    for order_item in OrderItem.objects.select_related('product__seller').iterator():
        if order_item.product and order_item.product.seller:
            order_item.seller_id = order_item.product.seller_id
            order_item.seller_name_snapshot = order_item.product.seller.brand_name
            order_item.save(update_fields=['seller_id', 'seller_name_snapshot'])


def reverse_populate(apps, schema_editor):
    """역방향 마이그레이션: 필드 값 초기화"""
    OrderItem = apps.get_model('orders', 'OrderItem')
    OrderItem.objects.update(seller_id=None, seller_name_snapshot=None)


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0004_add_inventory_deducted'),
        ('sellers', '0001_initial'),
    ]

    operations = [
        # 1) seller FK 필드 추가
        migrations.AddField(
            model_name='orderitem',
            name='seller',
            field=models.ForeignKey(
                blank=True,
                help_text='판매자 참조 (정산/쿼리용, 삭제 시 NULL)',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='order_items',
                to='sellers.seller',
                verbose_name='판매자',
            ),
        ),
        # 2) seller_name_snapshot 필드 추가
        migrations.AddField(
            model_name='orderitem',
            name='seller_name_snapshot',
            field=models.CharField(
                blank=True,
                help_text='주문 시점의 브랜드명 (판매자 정보 변경/삭제되어도 유지)',
                max_length=200,
                null=True,
                verbose_name='판매자명 스냅샷',
            ),
        ),
        # 3) seller 인덱스 추가
        migrations.AddIndex(
            model_name='orderitem',
            index=models.Index(fields=['seller'], name='ix_order_items_seller'),
        ),
        # 4) 기존 데이터에 판매자 정보 채우기
        migrations.RunPython(populate_seller_snapshot, reverse_populate),
    ]
