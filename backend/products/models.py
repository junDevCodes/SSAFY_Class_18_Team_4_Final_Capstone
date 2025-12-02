"""
제품 관련 모델
"""
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class Category(models.Model):
    """카테고리 모델 (계층 구조 지원)"""
    name = models.CharField(max_length=100, unique=True, verbose_name="카테고리명")
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
    """제품 모델 (메인 상품 + 판매자 상품 통합)"""

    PRODUCT_TYPE_CHOICES = [
        ('main', '메인 상품'),      # 크롤링/관리자 등록
        ('seller', '판매자 상품'),   # 판매자 등록
    ]

    STATUS_CHOICES = [
        ('draft', '임시저장'),
        ('active', '판매중'),
        ('inactive', '판매중지'),
        ('out_of_stock', '품절'),
        ('discontinued', '단종'),
    ]

    # 상품 유형
    product_type = models.CharField(
        max_length=20,
        choices=PRODUCT_TYPE_CHOICES,
        default='main',
        verbose_name="상품 유형"
    )

    # 관계
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products',
        verbose_name="카테고리"
    )
    seller = models.ForeignKey(
        'sellers.Seller',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='products',
        verbose_name="판매자",
        help_text="product_type='seller'일 때만 필수"
    )

    # 크롤링 메타데이터 (main 상품용)
    source_site = models.CharField(max_length=100, null=True, blank=True, verbose_name="출처 사이트")
    source_url = models.TextField(null=True, blank=True, verbose_name="출처 URL")
    crawled_at = models.DateTimeField(null=True, blank=True, verbose_name="크롤링 시간")

    # 기본 정보
    name = models.CharField(max_length=500, verbose_name="제품명")
    slug = models.SlugField(max_length=500, null=True, blank=True, unique=True, verbose_name="슬러그")
    short_description = models.TextField(null=True, blank=True, verbose_name="간단 설명")
    description = models.TextField(null=True, blank=True, verbose_name="상세 설명")

    # 가격 정보
    price = models.IntegerField(validators=[MinValueValidator(0)], verbose_name="가격")
    original_price = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        verbose_name="원가"
    )
    discount_rate = models.SmallIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="할인율"
    )
    cost_price = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        verbose_name="원가 (판매자용)"
    )

    # 단위
    unit = models.CharField(max_length=50, null=True, blank=True, verbose_name="단위")
    unit_quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=1.00,
        verbose_name="단위 수량"
    )

    # 재고 (판매자 상품만 사용)
    stock_quantity = models.IntegerField(default=0, verbose_name="재고 수량")
    low_stock_threshold = models.IntegerField(default=10, verbose_name="낮은 재고 기준")
    is_in_stock = models.BooleanField(default=True, verbose_name="재고 있음")

    # 이미지
    main_image_url = models.TextField(null=True, blank=True, verbose_name="메인 이미지 URL")

    # DEPRECATED: 이전 CSV 필드 (마이그레이션 후 삭제 예정)
    image_url = models.TextField(null=True, blank=True, verbose_name="[DEPRECATED] 이미지 URL")
    site_name = models.CharField(max_length=100, null=True, blank=True, verbose_name="[DEPRECATED] 출처")
    product_url = models.TextField(null=True, blank=True, verbose_name="[DEPRECATED] 제품 URL")
    detail_info = models.TextField(null=True, blank=True, verbose_name="[DEPRECATED] 상세정보")
    discount = models.IntegerField(
        default=0,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="[DEPRECATED] 할인율"
    )

    # 상품 품질 점수 (추천 알고리즘용)
    quality_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=50.00,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="품질 점수",
        help_text="이미지 품질, 설명 완성도, CTR 등을 종합"
    )
    image_quality_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=50.00,
        verbose_name="이미지 품질 점수"
    )
    content_quality_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=50.00,
        verbose_name="콘텐츠 품질 점수"
    )

    # 통계 (비정규화 - 성능 최적화)
    view_count = models.IntegerField(default=0, verbose_name="조회수")
    click_count = models.IntegerField(default=0, verbose_name="클릭수")
    cart_count = models.IntegerField(default=0, verbose_name="장바구니 추가수")
    wishlist_count = models.IntegerField(default=0, verbose_name="찜 수")
    purchase_count = models.IntegerField(default=0, verbose_name="구매수")
    review_count = models.IntegerField(default=0, verbose_name="리뷰수")
    average_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.00,
        verbose_name="평균 평점"
    )

    # CTR (Click-Through Rate)
    ctr = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=0.0000,
        verbose_name="CTR",
        help_text="click_count / view_count"
    )

    # 배송 정보
    shipping_required = models.BooleanField(default=True, verbose_name="배송 필요")
    shipping_fee = models.IntegerField(default=0, verbose_name="배송비")
    free_shipping_threshold = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="무료 배송 기준 금액"
    )
    estimated_delivery_days = models.SmallIntegerField(
        null=True,
        blank=True,
        verbose_name="예상 배송 일수"
    )

    # 상태
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        verbose_name="상태"
    )
    is_featured = models.BooleanField(default=False, verbose_name="추천 상품")
    is_best = models.BooleanField(default=False, verbose_name="베스트 상품")
    is_new = models.BooleanField(default=False, verbose_name="신상품")
    is_on_sale = models.BooleanField(default=False, verbose_name="할인 중")

    # 메타데이터
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일시")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일시")
    published_at = models.DateTimeField(null=True, blank=True, verbose_name="게시일시")

    # SEO
    meta_title = models.CharField(max_length=200, null=True, blank=True, verbose_name="SEO 제목")
    meta_description = models.TextField(null=True, blank=True, verbose_name="SEO 설명")
    meta_keywords = models.CharField(max_length=500, null=True, blank=True, verbose_name="SEO 키워드")

    class Meta:
        db_table = 'products'
        verbose_name = '제품'
        verbose_name_plural = '제품'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['product_type']),
            models.Index(fields=['category']),
            models.Index(fields=['seller']),
            models.Index(fields=['status']),
            models.Index(fields=['-quality_score']),
            models.Index(fields=['-view_count']),
            models.Index(fields=['-ctr']),
            models.Index(fields=['-created_at']),
            models.Index(fields=['is_featured', 'status']),
            models.Index(fields=['is_best', 'status']),
            models.Index(fields=['slug']),
            # 복합 인덱스 (추천 알고리즘용)
            models.Index(fields=['product_type', 'status', '-quality_score', '-ctr']),
            models.Index(fields=['category', 'status', '-quality_score']),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """CTR 자동 계산"""
        if self.view_count > 0:
            self.ctr = round(self.click_count / self.view_count, 4)
        else:
            self.ctr = 0.0000
        super().save(*args, **kwargs)

    def update_quality_score(self):
        """품질 점수 재계산 (이미지 품질 + 콘텐츠 품질 + CTR)"""
        # 가중 평균: 이미지 30%, 콘텐츠 30%, CTR 40%
        ctr_score = min(float(self.ctr) * 100, 100.00)  # CTR을 0-100 스케일로 변환
        self.quality_score = round(
            (self.image_quality_score * 0.3 +
             self.content_quality_score * 0.3 +
             ctr_score * 0.4),
            2
        )
        self.save(update_fields=['quality_score'])

    @property
    def final_price(self):
        """할인 적용된 최종 가격"""
        if self.discount_rate > 0:
            return int(self.price * (100 - self.discount_rate) / 100)
        return self.price

    @property
    def is_low_stock(self):
        """재고 부족 여부"""
        return self.stock_quantity <= self.low_stock_threshold


class ProductImage(models.Model):
    """상품 이미지 모델"""

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name="상품"
    )
    image_url = models.TextField(verbose_name="이미지 URL")
    alt_text = models.CharField(max_length=255, null=True, blank=True, verbose_name="대체 텍스트")
    display_order = models.IntegerField(default=0, verbose_name="표시 순서")

    # 이미지 메타데이터
    width = models.IntegerField(null=True, blank=True, verbose_name="너비")
    height = models.IntegerField(null=True, blank=True, verbose_name="높이")
    file_size = models.IntegerField(null=True, blank=True, verbose_name="파일 크기 (bytes)")
    format = models.CharField(max_length=10, null=True, blank=True, verbose_name="형식")  # 'jpg', 'png', 'webp'

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일시")

    class Meta:
        db_table = 'product_images'
        verbose_name = '상품 이미지'
        verbose_name_plural = '상품 이미지'
        ordering = ['product', 'display_order']
        indexes = [
            models.Index(fields=['product', 'display_order']),
        ]

    def __str__(self):
        return f"{self.product.name} - 이미지 {self.display_order}"


class ProductView(models.Model):
    """상품 조회 로그 (추천 알고리즘용)"""

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='views',
        verbose_name="상품"
    )
    user = models.ForeignKey(
        'authentication.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='product_views',
        verbose_name="사용자"
    )

    # 세션 기반 추적 (비로그인 사용자)
    session_id = models.CharField(max_length=255, null=True, blank=True, verbose_name="세션 ID")

    # 메타데이터
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="IP 주소")
    user_agent = models.TextField(null=True, blank=True, verbose_name="User Agent")
    referrer = models.TextField(null=True, blank=True, verbose_name="Referrer")

    # 시간
    viewed_at = models.DateTimeField(auto_now_add=True, verbose_name="조회 시간")

    class Meta:
        db_table = 'product_views'
        verbose_name = '상품 조회 로그'
        verbose_name_plural = '상품 조회 로그'
        indexes = [
            models.Index(fields=['product', '-viewed_at']),
            models.Index(fields=['user', '-viewed_at']),
            models.Index(fields=['session_id', '-viewed_at']),
        ]

    def __str__(self):
        user_info = self.user.username if self.user else f"세션:{self.session_id[:8] if self.session_id else 'unknown'}"
        return f"{self.product.name} - {user_info}"


class Wishlist(models.Model):
    """찜 목록"""

    user = models.ForeignKey(
        'authentication.User',
        on_delete=models.CASCADE,
        related_name='wishlists',
        verbose_name="사용자"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='wishlisted_by',
        verbose_name="상품"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="추가일시")

    class Meta:
        db_table = 'wishlists'
        verbose_name = '찜 목록'
        verbose_name_plural = '찜 목록'
        unique_together = [['user', 'product']]
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.product.name}"


class Cart(models.Model):
    """장바구니"""

    user = models.ForeignKey(
        'authentication.User',
        on_delete=models.CASCADE,
        related_name='cart_items',
        verbose_name="사용자"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='in_carts',
        verbose_name="상품"
    )
    quantity = models.PositiveIntegerField(default=1, verbose_name="수량")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="추가일시")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일시")

    class Meta:
        db_table = 'carts'
        verbose_name = '장바구니'
        verbose_name_plural = '장바구니'
        unique_together = [['user', 'product']]
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.product.name} x {self.quantity}"

    @property
    def subtotal(self):
        """소계 (할인 적용)"""
        return self.product.final_price * self.quantity
