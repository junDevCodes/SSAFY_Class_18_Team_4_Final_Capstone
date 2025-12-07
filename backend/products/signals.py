"""
Product 모델 시그널 핸들러

Product 생성 시 관련 테이블(ProductStats, ProductDetail, ProductInventory)을
자동으로 생성하여 상품 조회 시 발생하는 에러를 방지합니다.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Product, ProductStats, ProductDetail, ProductInventory


@receiver(post_save, sender=Product)
def create_product_related_models(sender, instance, created, **kwargs):
    """
    상품 생성 시 관련 테이블 자동 생성

    OneToOne 관계인 ProductStats, ProductDetail, ProductInventory는
    Product가 생성될 때 반드시 함께 생성되어야 합니다.
    get_or_create를 사용하여 중복 생성을 방지합니다.

    Args:
        sender: 시그널을 보낸 모델 클래스 (Product)
        instance: 저장된 Product 인스턴스
        created: 새로 생성된 경우 True, 업데이트된 경우 False
        **kwargs: 추가 키워드 인수
    """
    if created:
        # ProductStats 생성 (통계 정보)
        ProductStats.objects.get_or_create(product=instance)

        # ProductDetail 생성 (상세 정보)
        ProductDetail.objects.get_or_create(product=instance)

        # ProductInventory 생성 (재고 정보, 기본값 설정)
        ProductInventory.objects.get_or_create(
            product=instance,
            defaults={
                'stock_quantity': 0,
                'safe_stock_level': 10
            }
        )
