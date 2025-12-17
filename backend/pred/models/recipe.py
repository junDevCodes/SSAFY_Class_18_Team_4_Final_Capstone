"""
레시피 데이터 모델

만개의레시피 크롤링 데이터를 저장합니다.
레시피 갭필링 추천에 활용됩니다.
"""

from django.db import models
from products.models import Product


class DifficultyChoices(models.TextChoices):
    """난이도 선택"""
    EASY = 'easy', '쉬움'
    MEDIUM = 'medium', '보통'
    HARD = 'hard', '어려움'


class PredRecipe(models.Model):
    """레시피 마스터

    약 50,000건 (만개의레시피 크롤링)
    """

    # 출처 정보
    source_site = models.CharField(
        max_length=50,
        default='10000recipe',
        verbose_name='출처 사이트'
    )
    source_id = models.CharField(
        max_length=50,
        verbose_name='원본 ID',
        help_text='원본 사이트의 레시피 ID'
    )
    source_url = models.TextField(
        blank=True,
        default='',
        verbose_name='원본 URL'
    )

    # 레시피 정보
    name = models.CharField(
        max_length=200,
        verbose_name='레시피명'
    )
    name_normalized = models.CharField(
        max_length=200,
        verbose_name='정규화된 레시피명',
        help_text='검색용 정규화 이름'
    )
    description = models.TextField(
        blank=True,
        default='',
        verbose_name='설명'
    )

    # 이미지
    thumbnail_url = models.TextField(
        blank=True,
        default='',
        verbose_name='썸네일 URL'
    )

    # 메타데이터
    cooking_time_min = models.SmallIntegerField(
        null=True,
        blank=True,
        verbose_name='조리 시간 (분)'
    )
    servings = models.SmallIntegerField(
        null=True,
        blank=True,
        verbose_name='인분'
    )
    difficulty = models.CharField(
        max_length=20,
        choices=DifficultyChoices.choices,
        blank=True,
        default='',
        verbose_name='난이도'
    )

    # 인기도 지표
    view_count = models.IntegerField(
        default=0,
        verbose_name='조회수'
    )
    like_count = models.IntegerField(
        default=0,
        verbose_name='좋아요 수'
    )
    rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0,
        verbose_name='평점'
    )
    rating_count = models.IntegerField(
        default=0,
        verbose_name='평점 수'
    )

    # 카테고리
    category_main = models.CharField(
        max_length=50,
        blank=True,
        default='',
        verbose_name='대분류',
        help_text='한식, 양식, 중식 등'
    )
    category_sub = models.CharField(
        max_length=50,
        blank=True,
        default='',
        verbose_name='소분류',
        help_text='찌개, 볶음, 구이 등'
    )

    # 상태
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
        db_table = 'pred_recipes'
        verbose_name = '레시피'
        verbose_name_plural = '레시피들'
        unique_together = [['source_site', 'source_id']]
        indexes = [
            models.Index(
                fields=['name_normalized'],
                name='ix_recipes_name'
            ),
            models.Index(
                fields=['category_main', 'category_sub'],
                name='ix_recipes_category'
            ),
            models.Index(
                fields=['-rating', '-like_count'],
                name='ix_recipes_popularity'
            ),
        ]

    def __str__(self):
        return self.name


class IngredientCategoryChoices(models.TextChoices):
    """재료 카테고리"""
    VEGETABLE = '채소', '채소'
    MEAT = '육류', '육류'
    SEAFOOD = '수산물', '수산물'
    SEASONING = '양념', '양념'
    DAIRY = '유제품', '유제품'
    GRAIN = '곡류', '곡류'
    OTHER = '기타', '기타'


class PredIngredient(models.Model):
    """재료 마스터

    약 5,000건 (정규화된 재료명)
    """

    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='재료명'
    )
    name_normalized = models.CharField(
        max_length=100,
        verbose_name='정규화된 재료명',
        help_text='검색용 정규화 이름'
    )

    # 분류
    category = models.CharField(
        max_length=50,
        choices=IngredientCategoryChoices.choices,
        blank=True,
        default='',
        verbose_name='재료 분류'
    )

    # 대체재 그룹 (같은 그룹은 대체 가능)
    substitute_group_id = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='대체재 그룹 ID'
    )

    # 필수도 (레시피에서 얼마나 필수적인지)
    importance_score = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.5,
        verbose_name='중요도 점수'
    )

    # 가공식품 여부
    is_processed = models.BooleanField(
        default=False,
        verbose_name='가공식품 여부',
        help_text='고추장, 된장 등 가공식품'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='생성일시'
    )

    class Meta:
        db_table = 'pred_ingredients'
        verbose_name = '재료'
        verbose_name_plural = '재료들'
        indexes = [
            models.Index(
                fields=['name_normalized'],
                name='ix_ingredients_name'
            ),
            models.Index(
                fields=['category'],
                name='ix_ingredients_category'
            ),
        ]

    def __str__(self):
        return self.name


class PredRecipeIngredient(models.Model):
    """레시피-재료 관계

    약 500,000건
    """

    recipe = models.ForeignKey(
        PredRecipe,
        on_delete=models.CASCADE,
        related_name='ingredients',
        verbose_name='레시피'
    )
    ingredient = models.ForeignKey(
        PredIngredient,
        on_delete=models.CASCADE,
        related_name='recipes',
        verbose_name='재료'
    )

    # 재료 상세
    quantity_text = models.CharField(
        max_length=100,
        blank=True,
        default='',
        verbose_name='분량 텍스트',
        help_text='"1/2컵", "약간", "2개" 등'
    )
    quantity_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='파싱된 수량'
    )
    quantity_unit = models.CharField(
        max_length=20,
        blank=True,
        default='',
        verbose_name='파싱된 단위'
    )

    # 필수 여부
    is_required = models.BooleanField(
        default=True,
        verbose_name='필수 재료 여부'
    )
    is_main = models.BooleanField(
        default=False,
        verbose_name='주재료 여부'
    )

    # 표시 순서 (= 중요도 순)
    display_order = models.SmallIntegerField(
        default=0,
        verbose_name='표시 순서'
    )

    class Meta:
        db_table = 'pred_recipe_ingredients'
        verbose_name = '레시피 재료'
        verbose_name_plural = '레시피 재료들'
        unique_together = [['recipe', 'ingredient']]
        indexes = [
            models.Index(
                fields=['recipe'],
                name='ix_recipe_ing_recipe'
            ),
            models.Index(
                fields=['ingredient', 'recipe'],
                name='ix_recipe_ing_ingred'
            ),
            models.Index(
                fields=['recipe', '-is_main', '-is_required'],
                name='ix_recipe_ing_main'
            ),
        ]

    def __str__(self):
        return f"{self.recipe.name} - {self.ingredient.name}"


class IngredientMappingMethodChoices(models.TextChoices):
    """재료-상품 매핑 방법"""
    EXACT = 'exact', '정확 매칭'
    PARTIAL = 'partial', '부분 매칭'
    CATEGORY = 'category', '카테고리 매칭'


class PredIngredientProduct(models.Model):
    """재료-상품 매핑

    약 50,000건 (레시피 갭필링용)
    """

    ingredient = models.ForeignKey(
        PredIngredient,
        on_delete=models.CASCADE,
        related_name='products',
        verbose_name='재료'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='ingredient_mappings',
        verbose_name='상품'
    )

    # 매핑 신뢰도
    similarity_score = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        verbose_name='유사도 점수'
    )
    mapping_method = models.CharField(
        max_length=50,
        choices=IngredientMappingMethodChoices.choices,
        verbose_name='매핑 방법'
    )

    # 우선순위 (같은 재료에 여러 상품 매핑 시)
    priority = models.SmallIntegerField(
        default=0,
        verbose_name='우선순위'
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name='활성화 여부'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='생성일시'
    )

    class Meta:
        db_table = 'pred_ingredient_products'
        verbose_name = '재료-상품 매핑'
        verbose_name_plural = '재료-상품 매핑들'
        unique_together = [['ingredient', 'product']]
        indexes = [
            models.Index(
                fields=['ingredient'],
                name='ix_ing_prod_ingredient'
            ),
            models.Index(
                fields=['product'],
                name='ix_ing_prod_product'
            ),
        ]

    def __str__(self):
        return f"{self.ingredient.name} → {self.product.name}"
