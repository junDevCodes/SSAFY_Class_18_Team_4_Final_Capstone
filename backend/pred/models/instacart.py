"""
Instacart 원본 데이터 모델

Kaggle Instacart 데이터셋을 저장하는 테이블입니다.
콜드스타트 추천에 활용됩니다.
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class PredInstacartDepartment(models.Model):
    """Instacart 부서(대분류) 마스터

    약 21개 레코드 (frozen, bakery, produce 등)
    """

    id = models.SmallIntegerField(
        primary_key=True,
        verbose_name='Instacart 부서 ID'
    )
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='부서명'
    )
    description = models.CharField(
        max_length=255,
        blank=True,
        default='',
        verbose_name='설명'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='생성일시'
    )

    class Meta:
        db_table = 'pred_instacart_departments'
        verbose_name = 'Instacart 부서'
        verbose_name_plural = 'Instacart 부서들'

    def __str__(self):
        return self.name


class PredInstacartAisle(models.Model):
    """Instacart 통로(소분류) 마스터

    약 134개 레코드
    """

    id = models.SmallIntegerField(
        primary_key=True,
        verbose_name='Instacart 통로 ID'
    )
    department = models.ForeignKey(
        PredInstacartDepartment,
        on_delete=models.CASCADE,
        related_name='aisles',
        verbose_name='소속 부서'
    )
    name = models.CharField(
        max_length=100,
        verbose_name='통로명'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='생성일시'
    )

    class Meta:
        db_table = 'pred_instacart_aisles'
        verbose_name = 'Instacart 통로'
        verbose_name_plural = 'Instacart 통로들'
        unique_together = [['department', 'name']]
        indexes = [
            models.Index(fields=['department'], name='ix_inst_aisles_dept'),
        ]

    def __str__(self):
        return f"{self.department.name} > {self.name}"


class PredInstacartProduct(models.Model):
    """Instacart 상품 마스터

    약 49,688건
    """

    id = models.IntegerField(
        primary_key=True,
        verbose_name='Instacart 상품 ID'
    )
    aisle = models.ForeignKey(
        PredInstacartAisle,
        on_delete=models.CASCADE,
        related_name='products',
        verbose_name='소속 통로'
    )
    name = models.CharField(
        max_length=300,
        verbose_name='상품명'
    )
    name_normalized = models.CharField(
        max_length=300,
        verbose_name='정규화된 상품명',
        help_text='소문자 변환, 특수문자 제거된 상품명'
    )

    # 집계 통계 (배치 갱신)
    order_count = models.IntegerField(
        default=0,
        verbose_name='총 주문 횟수'
    )
    reorder_count = models.IntegerField(
        default=0,
        verbose_name='재주문 횟수'
    )
    reorder_rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=0,
        verbose_name='재주문율',
        help_text='0.0000~1.0000'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='생성일시'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='수정일시'
    )

    class Meta:
        db_table = 'pred_instacart_products'
        verbose_name = 'Instacart 상품'
        verbose_name_plural = 'Instacart 상품들'
        indexes = [
            models.Index(fields=['aisle'], name='ix_inst_products_aisle'),
            models.Index(fields=['name_normalized'], name='ix_inst_products_name'),
            models.Index(fields=['-order_count'], name='ix_inst_products_pop'),
        ]

    def __str__(self):
        return self.name


class EvalSetChoices(models.TextChoices):
    """주문 데이터셋 타입"""
    PRIOR = 'prior', '이전 주문'
    TRAIN = 'train', '학습용'
    TEST = 'test', '테스트용'


class PredInstacartOrder(models.Model):
    """Instacart 주문 데이터

    약 3.4M건
    eval_set별로 논리적으로 분리됩니다.
    """

    id = models.IntegerField(
        primary_key=True,
        verbose_name='Instacart 주문 ID'
    )
    user_id = models.IntegerField(
        verbose_name='Instacart 사용자 ID',
        help_text='SelF users 테이블과 무관한 Instacart 내부 ID'
    )
    order_number = models.SmallIntegerField(
        verbose_name='주문 순서',
        help_text='해당 사용자의 N번째 주문'
    )
    order_dow = models.SmallIntegerField(
        verbose_name='주문 요일',
        validators=[MinValueValidator(0), MaxValueValidator(6)],
        help_text='0=일요일, 6=토요일'
    )
    order_hour_of_day = models.SmallIntegerField(
        verbose_name='주문 시간',
        validators=[MinValueValidator(0), MaxValueValidator(23)],
        help_text='0-23'
    )
    days_since_prior_order = models.SmallIntegerField(
        null=True,
        blank=True,
        verbose_name='이전 주문 후 경과일'
    )
    eval_set = models.CharField(
        max_length=10,
        choices=EvalSetChoices.choices,
        verbose_name='데이터셋 타입'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='생성일시'
    )

    class Meta:
        db_table = 'pred_instacart_orders'
        verbose_name = 'Instacart 주문'
        verbose_name_plural = 'Instacart 주문들'
        indexes = [
            models.Index(fields=['user_id'], name='ix_inst_orders_user'),
            models.Index(fields=['eval_set'], name='ix_inst_orders_eval'),
            models.Index(
                fields=['eval_set', 'order_dow', 'order_hour_of_day'],
                name='ix_inst_orders_time'
            ),
            models.Index(
                fields=['user_id', 'order_number'],
                name='ix_inst_orders_user_seq'
            ),
        ]

    def __str__(self):
        return f"Order #{self.id} (User: {self.user_id})"


class PredInstacartOrderItem(models.Model):
    """Instacart 주문-상품 관계

    약 32M건
    """

    order = models.ForeignKey(
        PredInstacartOrder,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='주문'
    )
    product = models.ForeignKey(
        PredInstacartProduct,
        on_delete=models.CASCADE,
        related_name='order_items',
        verbose_name='상품'
    )
    add_to_cart_order = models.SmallIntegerField(
        verbose_name='장바구니 추가 순서',
        help_text='1부터 시작'
    )
    is_reordered = models.BooleanField(
        default=False,
        verbose_name='재주문 여부'
    )

    class Meta:
        db_table = 'pred_instacart_order_items'
        verbose_name = 'Instacart 주문 상품'
        verbose_name_plural = 'Instacart 주문 상품들'
        unique_together = [['order', 'product']]
        indexes = [
            models.Index(fields=['order'], name='ix_inst_oi_order'),
            models.Index(fields=['product'], name='ix_inst_oi_product'),
            models.Index(
                fields=['product', 'is_reordered'],
                name='ix_inst_oi_prod_reord'
            ),
        ]

    def __str__(self):
        return f"{self.order_id} - {self.product.name}"
