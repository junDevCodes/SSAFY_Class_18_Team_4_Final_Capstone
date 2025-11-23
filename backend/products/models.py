"""
제품 관련 모델
"""
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class Category(models.Model):
    """카테고리 모델"""
    name = models.CharField(max_length=100, unique=True, verbose_name="카테고리명")
    slug = models.SlugField(max_length=100, unique=True, verbose_name="슬러그")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일시")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일시")

    class Meta:
        db_table = 'categories'
        verbose_name = '카테고리'
        verbose_name_plural = '카테고리'
        ordering = ['name']

    def __str__(self):
        return self.name


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
