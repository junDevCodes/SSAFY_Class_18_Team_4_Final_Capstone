"""
Instacart 집계 및 매핑 모델

사전 집계된 시간대별 패턴, 카테고리 매핑, 상품 유사도 테이블입니다.
32M 레코드를 실시간 쿼리하지 않고 이 테이블을 활용합니다.
"""

from django.db import models
from products.models import Product, Category


class TimeSlotChoices(models.TextChoices):
    """시간대 선택"""
    MORNING = 'morning', '아침 (6-10시)'
    LUNCH = 'lunch', '점심 (11-14시)'
    DINNER = 'dinner', '저녁 (17-21시)'
    NIGHT = 'night', '야간 (기타)'


class DayTypeChoices(models.TextChoices):
    """요일 타입 선택"""
    WEEKDAY = 'weekday', '평일'
    WEEKEND = 'weekend', '주말'


class PredInstacartTimePattern(models.Model):
    """시간대/요일별 카테고리 인기도 사전 집계

    약 168행 (4시간대 × 2요일타입 × 21부서)
    32M 레코드를 실시간 조회하지 않고 이 테이블 사용
    """

    time_slot = models.CharField(
        max_length=20,
        choices=TimeSlotChoices.choices,
        verbose_name='시간대'
    )
    day_type = models.CharField(
        max_length=20,
        choices=DayTypeChoices.choices,
        verbose_name='요일 타입'
    )
    instacart_department = models.ForeignKey(
        'pred.PredInstacartDepartment',
        on_delete=models.CASCADE,
        related_name='time_patterns',
        verbose_name='Instacart 부서'
    )
    self_category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='instacart_time_patterns',
        verbose_name='매핑된 SelF 카테고리'
    )

    # 집계 통계
    popularity_score = models.BigIntegerField(
        verbose_name='인기도 점수',
        help_text='해당 시간대/요일의 총 주문 횟수'
    )
    reorder_rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        verbose_name='평균 재주문율'
    )

    aggregated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='집계 일시'
    )

    class Meta:
        db_table = 'pred_instacart_time_patterns'
        verbose_name = '시간대별 인기 패턴'
        verbose_name_plural = '시간대별 인기 패턴들'
        unique_together = [['time_slot', 'day_type', 'instacart_department']]
        indexes = [
            models.Index(
                fields=['time_slot', 'day_type', '-popularity_score'],
                name='ix_time_patterns_lookup'
            ),
            models.Index(
                fields=['self_category'],
                name='ix_time_patterns_self_cat'
            ),
        ]

    def __str__(self):
        return f"{self.time_slot}/{self.day_type} - {self.instacart_department.name}"


class PredInstacartCategoryMapping(models.Model):
    """Instacart→SelF 카테고리 매핑 (수동 관리)

    부서/통로 → SelF 카테고리 매핑
    """

    instacart_department = models.ForeignKey(
        'pred.PredInstacartDepartment',
        on_delete=models.CASCADE,
        related_name='category_mappings',
        verbose_name='Instacart 부서'
    )
    instacart_aisle = models.ForeignKey(
        'pred.PredInstacartAisle',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='category_mappings',
        verbose_name='Instacart 통로',
        help_text='NULL이면 부서 전체 매핑'
    )
    self_category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='instacart_mappings',
        verbose_name='SelF 카테고리'
    )

    # 매핑 신뢰도
    confidence_score = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=1.0,
        verbose_name='신뢰도',
        help_text='0.00~1.00'
    )
    mapping_note = models.CharField(
        max_length=200,
        blank=True,
        default='',
        verbose_name='매핑 메모'
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name='활성화 여부'
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
        db_table = 'pred_instacart_category_mapping'
        verbose_name = '카테고리 매핑'
        verbose_name_plural = '카테고리 매핑들'
        unique_together = [['instacart_department', 'instacart_aisle', 'self_category']]
        indexes = [
            models.Index(
                fields=['instacart_department'],
                name='ix_cat_mapping_dept'
            ),
            models.Index(
                fields=['self_category'],
                name='ix_cat_mapping_self'
            ),
        ]

    def __str__(self):
        aisle_part = f" > {self.instacart_aisle.name}" if self.instacart_aisle else ""
        return f"{self.instacart_department.name}{aisle_part} → {self.self_category.name}"


class MappingMethodChoices(models.TextChoices):
    """매핑 방법"""
    CATEGORY = 'category', '카테고리 기반'
    TEXT = 'text', '텍스트 유사도'
    MANUAL = 'manual', '수동 매핑'


class PredProductMapping(models.Model):
    """SelF ↔ Instacart 상품 매핑

    선택적 사용 (카테고리 수준 매핑이 우선)
    """

    self_product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='instacart_mappings',
        verbose_name='SelF 상품'
    )
    instacart_product = models.ForeignKey(
        'pred.PredInstacartProduct',
        on_delete=models.CASCADE,
        related_name='self_mappings',
        verbose_name='Instacart 상품'
    )

    # 매핑 신뢰도
    similarity_score = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        verbose_name='유사도 점수',
        help_text='0.0000~1.0000'
    )
    mapping_method = models.CharField(
        max_length=50,
        choices=MappingMethodChoices.choices,
        verbose_name='매핑 방법'
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name='활성화 여부'
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
        db_table = 'pred_product_mapping'
        verbose_name = '상품 매핑'
        verbose_name_plural = '상품 매핑들'
        unique_together = [['self_product', 'instacart_product']]
        indexes = [
            models.Index(
                fields=['self_product'],
                name='ix_prod_mapping_self'
            ),
            models.Index(
                fields=['instacart_product'],
                name='ix_prod_mapping_inst'
            ),
            models.Index(
                fields=['-similarity_score'],
                name='ix_prod_mapping_score'
            ),
        ]

    def __str__(self):
        return f"{self.self_product.name} ↔ {self.instacart_product.name}"


class SimilarityTypeChoices(models.TextChoices):
    """유사도 타입"""
    EMBEDDING = 'embedding', '임베딩 코사인'
    COPURCHASE = 'copurchase', '동시 구매'
    CATEGORY = 'category', '카테고리 기반'


class PredItemSimilarity(models.Model):
    """상품-상품 유사도 (사전 계산)

    상품당 Top 100 유사 상품 저장
    배치로 일 1회 갱신
    """

    source_product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='similar_items_as_source',
        verbose_name='기준 상품'
    )
    target_product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='similar_items_as_target',
        verbose_name='유사 상품'
    )

    similarity_score = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        verbose_name='유사도 점수',
        help_text='0.0000~1.0000'
    )
    similarity_type = models.CharField(
        max_length=20,
        choices=SimilarityTypeChoices.choices,
        verbose_name='유사도 타입'
    )

    calculated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='계산 일시'
    )

    class Meta:
        db_table = 'pred_item_similarity'
        verbose_name = '상품 유사도'
        verbose_name_plural = '상품 유사도들'
        unique_together = [['source_product', 'target_product', 'similarity_type']]
        constraints = [
            models.CheckConstraint(
                check=~models.Q(source_product=models.F('target_product')),
                name='check_different_products'
            )
        ]
        indexes = [
            models.Index(
                fields=['source_product', '-similarity_score'],
                name='ix_item_sim_source'
            ),
            models.Index(
                fields=['target_product'],
                name='ix_item_sim_target'
            ),
            models.Index(
                fields=['source_product', 'similarity_type', '-similarity_score'],
                name='ix_item_sim_src_type'
            ),
        ]

    def __str__(self):
        return f"{self.source_product.name} → {self.target_product.name} ({self.similarity_score})"
