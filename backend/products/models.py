"""
제품 관련 모델 (ERD V2.1 정확 구현)

Group 3: Product Domain
Group 5: Interactions (carts, wishlists, seller_follows)
Group 6: Reviews
Group 7: Recommendation & Analytics
"""
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


# ============================================================================
# Enums (ERD V2.1)
# ============================================================================

class ProductStatus(models.TextChoices):
    """상품 상태 (product_status enum)"""
    DRAFT = "draft", "임시저장"
    ACTIVE = "active", "판매중"
    INACTIVE = "inactive", "판매중지"
    OUT_OF_STOCK = "out_of_stock", "품절"
    DISCONTINUED = "discontinued", "단종"


class ProductType(models.TextChoices):
    """상품 유형 (product_type enum)"""
    MAIN = "main", "메인 상품"
    SELLER = "seller", "판매자 상품"


class ReviewStatus(models.TextChoices):
    """리뷰 상태"""
    VISIBLE = "visible", "공개"
    HIDDEN = "hidden", "숨김"
    REPORTED = "reported", "신고됨"
    DELETED = "deleted", "삭제됨"


# ============================================================================
# Group 3: Product Domain (ERD V2.1)
# ============================================================================

class Category(models.Model):
    """계층형 카테고리 (ERD: categories)"""

    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name="상위 카테고리",
    )

    name = models.CharField(
        max_length=100,
        verbose_name="카테고리명",
    )
    slug = models.SlugField(
        max_length=100,
        unique=True,
        verbose_name="슬러그",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일시")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일시")

    class Meta:
        db_table = 'categories'
        verbose_name = '카테고리'
        verbose_name_plural = '카테고리'
        indexes = [
            models.Index(fields=['parent'], name='ix_categories_parent'),
        ]

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name


class Product(models.Model):
    """상품 기본 스펙/가격/단위/배송 정보 (ERD: products)"""

    seller = models.ForeignKey(
        'sellers.Seller',
        on_delete=models.CASCADE,
        related_name='products',
        verbose_name="판매자",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products',
        verbose_name="카테고리",
    )

    # 크롤링 메타데이터
    source_site = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="출처 사이트",
        help_text="초기 CSV/크롤링 출처 사이트 이름",
    )
    source_url = models.TextField(
        null=True,
        blank=True,
        verbose_name="출처 URL",
        help_text="초기 CSV/크롤링 원본 상품 URL",
    )
    crawled_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="크롤링 시각",
        help_text="원본 데이터를 가져온 시각",
    )

    # 기본 정보
    name = models.CharField(
        max_length=500,
        verbose_name="상품명",
    )
    slug = models.SlugField(
        max_length=500,
        unique=True,
        verbose_name="슬러그",
    )

    # 가격
    price = models.IntegerField(
        validators=[MinValueValidator(0)],
        verbose_name="가격",
    )
    original_price = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        verbose_name="원가",
    )

    # 상태/유형
    status = models.CharField(
        max_length=20,
        choices=ProductStatus.choices,
        default=ProductStatus.ACTIVE,
        verbose_name="상태",
    )
    product_type = models.CharField(
        max_length=20,
        choices=ProductType.choices,
        default=ProductType.MAIN,
        verbose_name="상품 유형",
    )

    # 단위
    unit = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="단위",
    )
    unit_quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=1.00,
        verbose_name="단위 수량",
    )

    # 배송 정보
    shipping_required = models.BooleanField(
        default=True,
        verbose_name="배송 필요",
    )
    shipping_fee = models.IntegerField(
        default=0,
        verbose_name="배송비",
    )
    free_shipping_threshold = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="무료 배송 기준 금액",
    )
    estimated_delivery_days = models.SmallIntegerField(
        null=True,
        blank=True,
        verbose_name="예상 배송 일수",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일시")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일시")

    class Meta:
        db_table = 'products'
        verbose_name = '상품'
        verbose_name_plural = '상품'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['seller'], name='ix_products_seller'),
            models.Index(fields=['category'], name='ix_products_category'),
            models.Index(fields=['status'], name='ix_products_status'),
            models.Index(fields=['product_type'], name='ix_products_type'),
            models.Index(fields=['slug'], name='ix_products_slug'),
            models.Index(fields=['created_at'], name='ix_products_created'),
        ]

    def __str__(self):
        return self.name


class ProductDetail(models.Model):
    """상품 상세 설명 및 SEO 메타 정보 (ERD: product_details)"""

    product = models.OneToOneField(
        Product,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='detail',
        verbose_name="상품",
    )

    short_description = models.TextField(
        null=True,
        blank=True,
        verbose_name="짧은 설명",
    )
    full_description = models.TextField(
        null=True,
        blank=True,
        verbose_name="상세 설명",
    )

    meta_title = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        verbose_name="SEO 제목",
    )
    meta_keywords = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        verbose_name="SEO 키워드",
    )

    class Meta:
        db_table = 'product_details'
        verbose_name = '상품 상세'
        verbose_name_plural = '상품 상세'

    def __str__(self):
        return f"{self.product.name} 상세"


class ProductInventory(models.Model):
    """상품 재고 정보 (ERD: product_inventories)

    재고 부족 여부는 stock_quantity와 safe_stock_level로 계산.
    """

    product = models.OneToOneField(
        Product,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='inventory',
        verbose_name="상품",
    )

    stock_quantity = models.IntegerField(
        default=0,
        verbose_name="재고 수량",
    )
    safe_stock_level = models.IntegerField(
        default=10,
        verbose_name="안전 재고 수준",
    )

    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일시")

    class Meta:
        db_table = 'product_inventories'
        verbose_name = '상품 재고'
        verbose_name_plural = '상품 재고'

    def __str__(self):
        return f"{self.product.name} 재고: {self.stock_quantity}"

    @property
    def is_low_stock(self):
        """재고 부족 여부"""
        return self.stock_quantity <= self.safe_stock_level


class ProductPriceHistory(models.Model):
    """상품 가격 변동 이력 (사용자 요청 추가)

    상품의 가격 변화를 누적 기록하여 가격 추이를 추적.
    예: 1번 상품이 1000원 → 900원 → 1100원으로 변경된 이력 저장
    """

    product = models.ForeignKey(
        'Product',
        on_delete=models.CASCADE,
        related_name='price_histories',
        verbose_name="상품",
    )

    price = models.IntegerField(
        verbose_name="가격",
        help_text="해당 시점의 가격",
    )
    original_price = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="원가",
        help_text="해당 시점의 원가 (할인 전 가격)",
    )

    recorded_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="기록 시각",
        help_text="가격이 기록된 시각",
    )
    source = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="변경 출처",
        help_text="가격 변경 출처 (import, manual, crawl 등)",
    )

    class Meta:
        db_table = 'product_price_histories'
        verbose_name = '상품 가격 이력'
        verbose_name_plural = '상품 가격 이력'
        ordering = ['product', '-recorded_at']
        indexes = [
            models.Index(fields=['product', '-recorded_at'], name='ix_price_history_product'),
            models.Index(fields=['recorded_at'], name='ix_price_history_recorded'),
        ]

    def __str__(self):
        return f"{self.product.name}: {self.price}원 ({self.recorded_at.strftime('%Y-%m-%d %H:%M')})"


class ProductImage(models.Model):
    """상품 이미지 (ERD: product_images)

    가장 낮은 display_order를 대표 이미지로 사용.
    """

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name="상품",
    )

    image_url = models.TextField(
        verbose_name="이미지 URL",
    )
    display_order = models.IntegerField(
        default=0,
        verbose_name="표시 순서",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일시")

    class Meta:
        db_table = 'product_images'
        verbose_name = '상품 이미지'
        verbose_name_plural = '상품 이미지'
        ordering = ['product', 'display_order']
        indexes = [
            models.Index(fields=['product', 'display_order'], name='ix_product_images_order'),
        ]

    def __str__(self):
        return f"{self.product.name} - 이미지 {self.display_order}"


# ============================================================================
# Group 5: Interactions (ERD V2.1)
# ============================================================================

class Cart(models.Model):
    """장바구니 (ERD: carts)

    가격은 order_items 스냅샷으로만 관리.
    """

    user = models.ForeignKey(
        'authentication.User',
        on_delete=models.CASCADE,
        related_name='cart_items',
        verbose_name="사용자",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='in_carts',
        verbose_name="상품",
    )

    quantity = models.IntegerField(
        default=1,
        verbose_name="수량",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일시")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일시")

    class Meta:
        db_table = 'carts'
        verbose_name = '장바구니'
        verbose_name_plural = '장바구니'
        unique_together = [['user', 'product']]
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at'], name='ix_carts_user'),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.product.name} x {self.quantity}"

    @property
    def subtotal(self):
        """소계 계산 (상품 가격 * 수량)"""
        if self.product and self.product.price:
            return self.product.price * self.quantity
        return 0


class Wishlist(models.Model):
    """찜 목록 (ERD: wishlists)"""

    user = models.ForeignKey(
        'authentication.User',
        on_delete=models.CASCADE,
        related_name='wishlists',
        verbose_name="사용자",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='wishlisted_by',
        verbose_name="상품",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="추가일시")

    class Meta:
        db_table = 'wishlists'
        verbose_name = '찜 목록'
        verbose_name_plural = '찜 목록'
        unique_together = [['user', 'product']]
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at'], name='ix_wishlists_user'),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.product.name}"


class SellerFollow(models.Model):
    """판매자 팔로우 (ERD: seller_follows)

    소비자(user)가 판매자(seller)를 팔로우하는 관계.
    셀러가 유저를 팔로우하는 기능은 제공하지 않으며,
    애플리케이션에서 user.role이 일반 사용자일 때만 생성 허용.
    """

    user = models.ForeignKey(
        'authentication.User',
        on_delete=models.CASCADE,
        related_name='following_sellers',
        verbose_name="사용자",
    )
    seller = models.ForeignKey(
        'sellers.Seller',
        on_delete=models.CASCADE,
        related_name='followers',
        verbose_name="판매자",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="팔로우 시각")

    class Meta:
        db_table = 'seller_follows'
        verbose_name = '판매자 팔로우'
        verbose_name_plural = '판매자 팔로우'
        unique_together = [['user', 'seller']]
        indexes = [
            models.Index(fields=['user', 'seller'], name='ix_seller_follows_pair'),
            models.Index(fields=['user'], name='ix_seller_follows_user'),
            models.Index(fields=['seller'], name='ix_seller_follows_seller'),
        ]

    def __str__(self):
        return f"{self.user.username} → {self.seller.brand_name}"


# ============================================================================
# Group 6: Reviews (ERD V2.1)
# ============================================================================

class Review(models.Model):
    """상품 리뷰 (ERD: reviews)

    order_item_id를 통해 실제 구매 기반 리뷰인지 검증할 수 있고,
    사진 리뷰 여부(has_photos)로 사진 후기 비율 계산 가능.
    """

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name="상품",
    )
    user = models.ForeignKey(
        'authentication.User',
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name="작성자",
    )
    order_item = models.ForeignKey(
        'orders.OrderItem',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviews',
        verbose_name="주문 품목",
    )

    rating = models.SmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name="평점",
    )
    content = models.TextField(
        verbose_name="리뷰 내용",
    )

    has_photos = models.BooleanField(
        default=False,
        verbose_name="사진 리뷰 여부",
    )

    status = models.CharField(
        max_length=20,
        choices=ReviewStatus.choices,
        default=ReviewStatus.VISIBLE,
        verbose_name="상태",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일시")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일시")

    class Meta:
        db_table = 'reviews'
        verbose_name = '리뷰'
        verbose_name_plural = '리뷰'
        indexes = [
            models.Index(fields=['product'], name='ix_reviews_product'),
            models.Index(fields=['user'], name='ix_reviews_user'),
            models.Index(fields=['order_item'], name='ix_reviews_order_item'),
        ]

    def __str__(self):
        return f"{self.product.name} - {self.user.username} ({self.rating}점)"


class ReviewImage(models.Model):
    """사진 리뷰용 이미지 (ERD: review_images)

    한 리뷰에 여러 장의 사진을 연결할 수 있음.
    """

    review = models.ForeignKey(
        Review,
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name="리뷰",
    )

    image_url = models.TextField(
        verbose_name="이미지 URL",
    )
    display_order = models.IntegerField(
        default=0,
        verbose_name="표시 순서",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일시")

    class Meta:
        db_table = 'review_images'
        verbose_name = '리뷰 이미지'
        verbose_name_plural = '리뷰 이미지'
        indexes = [
            models.Index(fields=['review', 'display_order'], name='ix_review_images_order'),
        ]

    def __str__(self):
        return f"리뷰 {self.review.id} 이미지 {self.display_order}"


# ============================================================================
# Group 7: Recommendation & Analytics (ERD V2.1)
# ============================================================================

class ProductStats(models.Model):
    """상품별 집계/품질 피처 (ERD: product_stats)

    view/cart/order/wishlist/review 로그를 배치/스트림으로 모아 정기적으로 갱신하고,
    추천/정렬/대시보드 피처의 재료로 사용.
    """

    product = models.OneToOneField(
        Product,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='stats',
        verbose_name="상품",
    )

    # 기본 집계 카운트
    view_count = models.BigIntegerField(default=0, verbose_name="조회수")
    recommend_clicked_count = models.BigIntegerField(default=0, verbose_name="추천 클릭수")
    cart_event_count = models.BigIntegerField(default=0, verbose_name="장바구니 이벤트 수")
    order_event_count = models.BigIntegerField(default=0, verbose_name="주문 이벤트 수")
    wishlist_count = models.BigIntegerField(default=0, verbose_name="찜 수")

    # 리뷰 기반 집계
    review_count = models.BigIntegerField(default=0, verbose_name="리뷰 수")
    average_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.00,
        verbose_name="평균 평점",
    )
    photo_review_count = models.BigIntegerField(default=0, verbose_name="사진 리뷰 수")

    # 감성/타이밍 피처
    sentiment_score_avg = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        verbose_name="감성 점수 평균",
    )
    first_review_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="첫 리뷰 시각",
    )

    # 품질 점수
    quality_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=50.00,
        verbose_name="품질 점수",
    )
    image_quality_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=50.00,
        verbose_name="이미지 품질 점수",
    )
    content_quality_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=50.00,
        verbose_name="콘텐츠 품질 점수",
    )

    last_updated = models.DateTimeField(auto_now=True, verbose_name="갱신 시각")

    class Meta:
        db_table = 'product_stats'
        verbose_name = '상품 통계'
        verbose_name_plural = '상품 통계'

    def __str__(self):
        return f"{self.product.name} 통계"


class UserProductStats(models.Model):
    """유저 × 상품별 집계 피처 (ERD: user_product_stats)

    개인화 추천/재방문 리마인드 등에 사용.
    """

    user = models.ForeignKey(
        'authentication.User',
        on_delete=models.CASCADE,
        related_name='product_stats',
        verbose_name="사용자",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='user_stats',
        verbose_name="상품",
    )

    view_count = models.BigIntegerField(default=0, verbose_name="조회수")
    cart_event_count = models.BigIntegerField(default=0, verbose_name="장바구니 이벤트 수")
    order_event_count = models.BigIntegerField(default=0, verbose_name="주문 이벤트 수")

    last_interacted_at = models.DateTimeField(auto_now=True, verbose_name="마지막 상호작용 시각")

    class Meta:
        db_table = 'user_product_stats'
        verbose_name = '유저별 상품 통계'
        verbose_name_plural = '유저별 상품 통계'
        unique_together = [['user', 'product']]
        indexes = [
            models.Index(fields=['user', 'product'], name='ix_user_product_stats_pair'),
            models.Index(fields=['user'], name='ix_user_product_stats_user'),
            models.Index(fields=['product'], name='ix_user_product_stats_product'),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.product.name} 통계"
