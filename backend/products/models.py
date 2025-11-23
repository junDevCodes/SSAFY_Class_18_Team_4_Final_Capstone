"""
제품 관련 모델
"""
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class Category(models.Model):
    """카테고리 모델 (계층 구조 지원)"""
    name = models.CharField(max_length=100, verbose_name="카테고리명")
    slug = models.SlugField(max_length=100, verbose_name="슬러그")

    # 계층 구조 필드
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name="상위 카테고리"
    )
    path = models.CharField(
        max_length=500,
        editable=False,
        db_index=True,
        null=True,
        blank=True,
        verbose_name="경로"
    )
    level = models.SmallIntegerField(
        default=0,
        editable=False,
        db_index=True,
        verbose_name="레벨"
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일시")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일시")

    class Meta:
        db_table = 'categories'
        verbose_name = '카테고리'
        verbose_name_plural = '카테고리'
        ordering = ['path']
        unique_together = [['parent', 'name']]  # 같은 부모 아래에서만 이름 고유

    def __str__(self):
        return self.get_full_path()

    def save(self, *args, **kwargs):
        """path와 level 자동 계산"""
        if self.parent:
            self.level = self.parent.level + 1
            self.path = f"{self.parent.path}/{self.slug}"
        else:
            self.level = 0
            self.path = self.slug

        super().save(*args, **kwargs)

        # 하위 카테고리들의 path 업데이트
        for child in self.children.all():
            child.save()

    def get_full_path(self):
        """전체 경로를 이름으로 반환 (예: '과일 > 사과 > 홍옥')"""
        if self.parent:
            return f"{self.parent.get_full_path()} > {self.name}"
        return self.name

    def get_ancestors(self):
        """모든 상위 카테고리 반환"""
        ancestors = []
        current = self.parent
        while current:
            ancestors.insert(0, current)
            current = current.parent
        return ancestors

    def get_descendants(self):
        """모든 하위 카테고리 반환 (재귀적)"""
        descendants = list(self.children.all())
        for child in self.children.all():
            descendants.extend(child.get_descendants())
        return descendants

    def is_root(self):
        """최상위 카테고리인지 확인"""
        return self.parent is None

    def is_leaf(self):
        """하위 카테고리가 없는지 확인"""
        return not self.children.exists()


class Product(models.Model):
    """제품 모델"""
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products',
        verbose_name="카테고리"
    )

    # CSV 필드
    site_name = models.CharField(max_length=100, null=True, blank=True, verbose_name="출처")
    name = models.CharField(max_length=500, verbose_name="제품명")
    price = models.IntegerField(
        validators=[MinValueValidator(0)],
        verbose_name="가격"
    )
    unit = models.CharField(max_length=50, null=True, blank=True, verbose_name="단위")
    description = models.TextField(null=True, blank=True, verbose_name="설명")
    product_url = models.TextField(null=True, blank=True, verbose_name="제품 URL")
    image_url = models.TextField(verbose_name="이미지 URL")
    detail_info = models.TextField(null=True, blank=True, verbose_name="상세정보")
    crawled_at = models.DateTimeField(null=True, blank=True, verbose_name="크롤링 시간")

    # 추가 필드
    original_price = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        verbose_name="원가"
    )
    discount = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="할인율"
    )
    is_best = models.BooleanField(default=False, verbose_name="베스트")

    # 메타데이터
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일시")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일시")

    class Meta:
        db_table = 'products'
        verbose_name = '제품'
        verbose_name_plural = '제품'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['category']),
            models.Index(fields=['price']),
            models.Index(fields=['name']),
        ]

    def __str__(self):
        return self.name
