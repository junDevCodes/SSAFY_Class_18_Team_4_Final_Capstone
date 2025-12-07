"""
판매자 관련 시그널 핸들러

판매자 상태 변경 시 연관 데이터 자동 처리를 담당합니다.
"""
from django.db.models.signals import pre_save
from django.dispatch import receiver

from sellers.models import Seller, SellerStatus


@receiver(pre_save, sender=Seller)
def deactivate_products_on_seller_status_change(sender, instance, **kwargs):
    """
    판매자가 INACTIVE 또는 SUSPENDED 상태로 변경되면 해당 판매자의 모든 상품을 비활성화합니다.

    비즈니스 로직:
    - 판매자가 비활성화(INACTIVE)되면 상품 판매가 불가능해야 함
    - 판매자가 정지(SUSPENDED)되면 상품 판매가 중단되어야 함
    - 물리적 삭제 대신 상태 변경으로 데이터 보존

    주의:
    - 새로 생성되는 판매자(pk가 없는 경우)는 처리하지 않음
    - 상태가 ACTIVE로 변경되어도 상품은 자동 활성화하지 않음 (수동 검토 필요)
    """
    # 새로 생성되는 인스턴스는 처리하지 않음
    if not instance.pk:
        return

    # 현재 DB에 저장된 상태 조회
    try:
        old_instance = Seller.objects.get(pk=instance.pk)
    except Seller.DoesNotExist:
        return

    old_status = old_instance.status
    new_status = instance.status

    # 상태가 변경되지 않았으면 처리하지 않음
    if old_status == new_status:
        return

    # INACTIVE 또는 SUSPENDED로 변경된 경우에만 상품 비활성화
    inactive_statuses = [SellerStatus.INACTIVE, SellerStatus.SUSPENDED]

    if new_status in inactive_statuses and old_status not in inactive_statuses:
        # 지연 임포트로 순환 참조 방지
        from products.models import Product, ProductStatus

        # 해당 판매자의 활성 상품들을 모두 비활성화
        updated_count = Product.objects.filter(
            seller=instance,
            status=ProductStatus.ACTIVE
        ).update(status=ProductStatus.INACTIVE)

        if updated_count > 0:
            # 로깅 (운영 환경에서는 적절한 로거 사용 권장)
            import logging
            logger = logging.getLogger(__name__)
            logger.info(
                f"판매자 '{instance.brand_name}'(ID: {instance.pk}) 상태 변경 "
                f"({old_status} → {new_status}): {updated_count}개 상품 비활성화"
            )
