"""
제품 관련 Serializer (ERD V2.1)

ERD V2.1: ProductDetail, ProductInventory, ProductStats 분리 테이블 지원
"""
from rest_framework import serializers
from .models import (
    Category, Product, ProductImage, Wishlist, Cart,
    ProductDetail, ProductInventory, ProductStats,
    Review, ReviewImage
)


class CategorySerializer(serializers.ModelSerializer):
    """카테고리 Serializer (ERD V2.1)"""

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class ProductImageSerializer(serializers.ModelSerializer):
    """상품 이미지 Serializer (ERD V2.1)"""

    class Meta:
        model = ProductImage
        fields = ['id', 'image_url', 'display_order', 'created_at']
        read_only_fields = ['id', 'created_at']


class ProductSerializer(serializers.ModelSerializer):
    """제품 Serializer (ERD V2.1)"""
    # 카테고리 정보를 nested로 포함 (읽기용)
    category = CategorySerializer(read_only=True)
    # 카테고리 ID를 받을 수 있도록 추가 (쓰기용)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source='category',
        write_only=True,
        required=False,
        allow_null=True
    )

    class Meta:
        model = Product
        fields = [
            'id',
            'seller',
            'category',
            'category_id',
            'source_site',
            'source_url',
            'crawled_at',
            'name',
            'slug',
            'price',
            'original_price',
            'status',
            'product_type',
            'unit',
            'unit_quantity',
            'shipping_required',
            'shipping_fee',
            'free_shipping_threshold',
            'estimated_delivery_days',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ProductListSerializer(serializers.ModelSerializer):
    """상품 목록용 Serializer (간소화) - ERD V2.1"""

    category = CategorySerializer(read_only=True)
    category_name = serializers.SerializerMethodField()
    main_image = serializers.SerializerMethodField()
    wishlist_count = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id',
            'slug',
            'name',
            'price',
            'original_price',
            'unit',
            'main_image',
            'category',
            'category_name',
            'status',
            'product_type',
            'wishlist_count',
            'created_at',
        ]

    def get_category_name(self, obj):
        """카테고리명 반환 (null 안전)"""
        if obj.category:
            return obj.category.name
        return None

    def get_main_image(self, obj):
        """메인 이미지 URL 반환 (ProductImage 테이블에서, display_order 기준)"""
        first_image = obj.images.order_by('display_order').first()
        if first_image:
            return first_image.image_url
        return None

    def get_wishlist_count(self, obj):
        """해당 상품을 찜한 수"""
        return obj.wishlisted_by.count()


class SellerProductListSerializer(serializers.ModelSerializer):
    """판매자 상품 목록/상세용 Serializer

    Seller 대시보드/상품 관리 화면에서 사용하는 DTO 구조를 제공합니다.
    """

    short_description = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    discount_rate = serializers.SerializerMethodField()
    category_id = serializers.SerializerMethodField()
    main_image_url = serializers.SerializerMethodField()
    stock_quantity = serializers.SerializerMethodField()
    low_stock_threshold = serializers.SerializerMethodField()
    is_low_stock = serializers.SerializerMethodField()
    view_count = serializers.SerializerMethodField()
    order_count = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id',
            'name',
            'slug',
            'short_description',
            'description',
            'price',
            'original_price',
            'discount_rate',
            'category_id',
            'main_image_url',
            'unit',
            'unit_quantity',
            'stock_quantity',
            'low_stock_threshold',
            'shipping_fee',
            'free_shipping_threshold',
            'status',
            'is_low_stock',
            'view_count',
            'order_count',
            'created_at',
            'updated_at',
        ]

    def get_short_description(self, obj):
        """ProductDetail.short_description 매핑"""
        if hasattr(obj, 'detail') and obj.detail:
            return obj.detail.short_description
        return None

    def get_description(self, obj):
        """상세 설명(full_description) 매핑"""
        if hasattr(obj, 'detail') and obj.detail:
            return obj.detail.full_description
        return None

    def get_discount_rate(self, obj):
        """정가 대비 할인율 계산"""
        original = obj.original_price
        price = obj.price
        try:
            if original and original > 0 and price is not None and price < original:
                rate = round(float((original - price) / original * 100))
                return int(rate)
        except Exception:
            pass
        return 0

    def get_category_id(self, obj):
        """카테고리 ID 반환"""
        return obj.category_id

    def get_main_image_url(self, obj):
        """대표 이미지 URL (ProductImage.display_order 기준)"""
        first_image = obj.images.order_by('display_order').first()
        if first_image:
            return first_image.image_url
        return None

    def get_stock_quantity(self, obj):
        """재고 수량 (ProductInventory.stock_quantity)"""
        if hasattr(obj, 'inventory') and obj.inventory:
            return obj.inventory.stock_quantity
        return 0

    def get_low_stock_threshold(self, obj):
        """안전 재고 수준 (ProductInventory.safe_stock_level)"""
        if hasattr(obj, 'inventory') and obj.inventory:
            return obj.inventory.safe_stock_level
        return 0

    def get_is_low_stock(self, obj):
        """재고 부족 여부"""
        if hasattr(obj, 'inventory') and obj.inventory:
            return obj.inventory.is_low_stock
        return False

    def get_view_count(self, obj):
        """조회수 (ProductStats.view_count)"""
        if hasattr(obj, 'stats') and obj.stats:
            return obj.stats.view_count
        return 0

    def get_order_count(self, obj):
        """주문 이벤트 수 (ProductStats.order_event_count)"""
        if hasattr(obj, 'stats') and obj.stats:
            return obj.stats.order_event_count
        return 0


class SellerBriefSerializer(serializers.Serializer):
    """판매자 간단 정보 (ProductDetailSerializer용)"""

    id = serializers.IntegerField()
    brand_name = serializers.CharField()
    brand_slug = serializers.CharField()


class ProductDetailInfoSerializer(serializers.ModelSerializer):
    """상품 상세 정보 Serializer (ERD V2.1)

    ProductDetail 테이블의 데이터를 직렬화합니다.
    """

    class Meta:
        model = ProductDetail
        fields = [
            'short_description',
            'full_description',
            'full_image_description',
            'full_text_description',
            'meta_title',
            'meta_keywords',
        ]


class ProductInventorySerializer(serializers.ModelSerializer):
    """상품 재고 정보 Serializer (ERD V2.1)

    ProductInventory 테이블의 데이터를 직렬화합니다.
    - is_unlimited: 무제한 재고 여부 (크롤링 상품 등)
    """
    is_low_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = ProductInventory
        fields = ['stock_quantity', 'safe_stock_level', 'is_unlimited', 'is_low_stock', 'updated_at']


class ProductStatsSerializer(serializers.ModelSerializer):
    """상품 통계 정보 Serializer (ERD V2.1)

    ProductStats 테이블의 데이터를 직렬화합니다.
    """

    class Meta:
        model = ProductStats
        fields = [
            'view_count',
            'recommend_clicked_count',
            'cart_event_count',
            'order_event_count',
            'wishlist_count',
            'review_count',
            'average_rating',
            'photo_review_count',
            'quality_score',
            'last_updated',
        ]


class ProductDetailSerializer(serializers.ModelSerializer):
    """상품 상세 Serializer (ERD V2.1)"""

    category = CategorySerializer(read_only=True)
    seller = SellerBriefSerializer(read_only=True, allow_null=True)
    images = ProductImageSerializer(many=True, read_only=True)

    # 추가 정보
    is_wishlist = serializers.SerializerMethodField()
    related_products = serializers.SerializerMethodField()
    wishlist_count = serializers.SerializerMethodField()
    main_image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id',
            'seller',
            'category',
            'source_site',
            'source_url',
            'crawled_at',
            'name',
            'slug',
            'price',
            'original_price',
            'status',
            'product_type',
            'unit',
            'unit_quantity',
            'shipping_required',
            'shipping_fee',
            'free_shipping_threshold',
            'estimated_delivery_days',
            'main_image',
            'images',
            'is_wishlist',
            'wishlist_count',
            'related_products',
            'created_at',
            'updated_at',
        ]

    def get_is_wishlist(self, obj):
        """찜 여부 확인"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Wishlist.objects.filter(user=request.user, product=obj).exists()
        return False

    def get_main_image(self, obj):
        """메인 이미지 URL 반환 (ProductImage 테이블에서, display_order 기준)"""
        first_image = obj.images.order_by('display_order').first()
        if first_image:
            return first_image.image_url
        return None

    def get_related_products(self, obj):
        """관련 상품 추천 (같은 카테고리)"""
        if not obj.category:
            return []

        related = Product.objects.filter(
            category=obj.category,
            status='active'
        ).exclude(id=obj.id).select_related('category')[:6]

        return ProductListSerializer(related, many=True, context=self.context).data

    def get_wishlist_count(self, obj):
        """해당 상품을 찜한 수"""
        return obj.wishlisted_by.count()


class WishlistSerializer(serializers.ModelSerializer):
    """찜 목록 Serializer (ERD V2.1)"""

    product = ProductListSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        source='product',
        write_only=True
    )

    class Meta:
        model = Wishlist
        fields = ['id', 'product', 'product_id', 'created_at']
        read_only_fields = ['id', 'created_at']


class CartSerializer(serializers.ModelSerializer):
    """장바구니 Serializer (ERD V2.1)"""

    product = ProductListSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        source='product',
        write_only=True
    )
    subtotal = serializers.ReadOnlyField()

    class Meta:
        model = Cart
        fields = ['id', 'product', 'product_id', 'quantity', 'subtotal', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_quantity(self, value):
        """수량 검증"""
        if value < 1:
            raise serializers.ValidationError('수량은 1 이상이어야 합니다.')
        if value > 999:
            raise serializers.ValidationError('수량은 999 이하여야 합니다.')
        return value


# ========================= v2.1 신규 Serializer =========================

class NewProductListSerializer(serializers.ModelSerializer):
    """신상품 목록용 Serializer

    신상품 페이지에서 사용하는 간소화된 Serializer입니다.
    프론트엔드에서 7일 필터링을 위해 created_at 필드를 포함합니다.
    """
    category_name = serializers.SerializerMethodField()
    main_image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id',
            'slug',
            'name',
            'price',
            'original_price',
            'main_image',
            'category_name',
            'created_at',
        ]

    def get_category_name(self, obj):
        """카테고리명 반환 (null 안전)"""
        if obj.category:
            return obj.category.name
        return None

    def get_main_image(self, obj):
        """메인 이미지 URL 반환 (ProductImage 테이블에서, display_order 기준)"""
        first_image = obj.images.order_by('display_order').first()
        if first_image:
            return first_image.image_url
        return None


class BestProductListSerializer(serializers.ModelSerializer):
    """베스트 상품 목록용 Serializer

    베스트 상품 페이지에서 사용하는 Serializer입니다.
    일일 판매량, 누적 판매량, 리뷰 정보를 포함합니다.
    판매자 상품(product_type='seller') 중 판매량 기준 상위 40개에 사용됩니다.
    """
    category_name = serializers.SerializerMethodField()
    main_image = serializers.SerializerMethodField()

    # 통계 정보 (ProductStats에서)
    review_count = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()

    # 판매량 정보 (annotated fields - View에서 annotate로 추가됨)
    daily_order_count = serializers.IntegerField(read_only=True)
    total_order_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Product
        fields = [
            'id',
            'slug',
            'name',
            'price',
            'original_price',
            'main_image',
            'category_name',
            'review_count',
            'average_rating',
            'daily_order_count',
            'total_order_count',
            'created_at',
        ]

    def get_category_name(self, obj):
        """카테고리명 반환 (null 안전)"""
        if obj.category:
            return obj.category.name
        return None

    def get_main_image(self, obj):
        """메인 이미지 URL 반환 (ProductImage 테이블에서, display_order 기준)"""
        first_image = obj.images.order_by('display_order').first()
        if first_image:
            return first_image.image_url
        return None

    def get_review_count(self, obj):
        """리뷰 수 (ProductStats에서)"""
        if hasattr(obj, 'stats') and obj.stats:
            return obj.stats.review_count
        return 0

    def get_average_rating(self, obj):
        """평균 평점 (ProductStats에서)"""
        if hasattr(obj, 'stats') and obj.stats:
            return str(obj.stats.average_rating)
        return '0.00'


class ProductListSerializerV2(serializers.ModelSerializer):
    """상품 목록용 Serializer v2.1 (v2.1 테이블 포함)

    ProductStats에서 통계 데이터를 가져옵니다.
    """
    category = CategorySerializer(read_only=True)
    category_name = serializers.SerializerMethodField()
    main_image = serializers.SerializerMethodField()

    # v2.1 통계 정보
    view_count = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()
    order_event_count = serializers.SerializerMethodField()
    wishlist_count = serializers.SerializerMethodField()
    quality_score = serializers.SerializerMethodField()

    # 재고 정보
    stock_quantity = serializers.SerializerMethodField()

    # GMS 재료 추출 정보
    main_ingredient = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id',
            'slug',
            'name',
            'price',
            'original_price',
            'unit',
            'main_image',
            'category',
            'category_name',
            'status',
            'product_type',
            'view_count',
            'average_rating',
            'review_count',
            'order_event_count',
            'wishlist_count',
            'quality_score',
            'stock_quantity',
            'main_ingredient',
            'created_at',
        ]

    def get_category_name(self, obj):
        """카테고리명 반환 (null 안전)"""
        if obj.category:
            return obj.category.name
        return None

    def get_main_image(self, obj):
        """메인 이미지 URL 반환 (ProductImage 테이블에서, display_order 기준)"""
        first_image = obj.images.order_by('display_order').first()
        if first_image:
            return first_image.image_url
        return None

    def get_view_count(self, obj):
        """조회수 (ProductStats에서)"""
        if hasattr(obj, 'stats') and obj.stats:
            return obj.stats.view_count
        return 0

    def get_average_rating(self, obj):
        """평균 평점 (ProductStats에서)"""
        if hasattr(obj, 'stats') and obj.stats:
            return obj.stats.average_rating
        return 0

    def get_review_count(self, obj):
        """리뷰 수 (ProductStats에서)"""
        if hasattr(obj, 'stats') and obj.stats:
            return obj.stats.review_count
        return 0

    def get_order_event_count(self, obj):
        """주문 이벤트 수 (ProductStats에서)"""
        if hasattr(obj, 'stats') and obj.stats:
            return obj.stats.order_event_count
        return 0

    def get_wishlist_count(self, obj):
        """찜 수 (ProductStats에서)"""
        if hasattr(obj, 'stats') and obj.stats:
            return obj.stats.wishlist_count
        return 0

    def get_quality_score(self, obj):
        """품질 점수 (ProductStats에서)"""
        if hasattr(obj, 'stats') and obj.stats:
            return obj.stats.quality_score
        return 50.00

    def get_stock_quantity(self, obj):
        """재고 수량 (ProductInventory에서, 없으면 null = 무제한)"""
        if hasattr(obj, 'inventory') and obj.inventory:
            return obj.inventory.stock_quantity
        return None

    def get_main_ingredient(self, obj):
        """주요 재료명 반환 (GMS 추출 결과에서)"""
        if obj.parsed_ingredients:
            return obj.parsed_ingredients.get('main_ingredient')
        return None


class ProductDetailSerializerV2(serializers.ModelSerializer):
    """상품 상세 Serializer v2.1 (분리된 테이블 포함)

    ProductDetail, ProductInventory, ProductStats 정보를 포함합니다.
    """
    category = CategorySerializer(read_only=True)
    seller = SellerBriefSerializer(read_only=True, allow_null=True)
    images = ProductImageSerializer(many=True, read_only=True)

    # ERD V2.1 분리 테이블
    detail = ProductDetailInfoSerializer(read_only=True)
    inventory = ProductInventorySerializer(read_only=True)
    stats = ProductStatsSerializer(read_only=True)

    # 추가 정보
    is_wishlist = serializers.SerializerMethodField()
    related_products = serializers.SerializerMethodField()
    main_image = serializers.SerializerMethodField()

    # GMS 재료 추출 정보
    parsed_ingredients = serializers.JSONField(read_only=True)
    main_ingredient = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            # 기본 정보
            'id',
            'slug',
            'name',
            'price',
            'original_price',
            'unit',
            'category',
            'seller',
            'product_type',
            'status',
            # 이미지
            'main_image',
            'images',
            # ERD V2.1 분리 테이블
            'detail',
            'inventory',
            'stats',
            # 배송 정보
            'shipping_required',
            'shipping_fee',
            'free_shipping_threshold',
            'estimated_delivery_days',
            # GMS 재료 추출 정보
            'parsed_ingredients',
            'main_ingredient',
            # 추가 정보
            'is_wishlist',
            'related_products',
            # 메타데이터
            'source_site',
            'source_url',
            'crawled_at',
            'created_at',
            'updated_at',
        ]

    def get_is_wishlist(self, obj):
        """찜 여부 확인"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Wishlist.objects.filter(user=request.user, product=obj).exists()
        return False

    def get_main_image(self, obj):
        """메인 이미지 URL 반환 (ProductImage 테이블에서, display_order 기준)"""
        first_image = obj.images.order_by('display_order').first()
        if first_image:
            return first_image.image_url
        return None

    def get_main_ingredient(self, obj):
        """주요 재료명 반환 (GMS 추출 결과에서)"""
        if obj.parsed_ingredients:
            return obj.parsed_ingredients.get('main_ingredient')
        return None

    def get_related_products(self, obj):
        """관련 상품 추천 (같은 카테고리)"""
        if not obj.category:
            return []

        related = Product.objects.filter(
            category=obj.category,
            status='active'
        ).exclude(id=obj.id).select_related('category', 'stats')[:6]

        return ProductListSerializerV2(related, many=True, context=self.context).data


# ========================= 리뷰 Serializers =========================

class ReviewImageSerializer(serializers.ModelSerializer):
    """리뷰 이미지 Serializer"""

    class Meta:
        model = ReviewImage
        fields = ['id', 'image_url', 'display_order']
        read_only_fields = ['id']


class ReviewSerializer(serializers.ModelSerializer):
    """리뷰 Serializer (조회용)"""
    user_name = serializers.CharField(source='user.username', read_only=True)
    images = ReviewImageSerializer(many=True, read_only=True)

    class Meta:
        model = Review
        fields = [
            'id', 'product', 'user', 'user_name', 'order_item',
            'rating', 'content', 'has_photos', 'status',
            'images', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'has_photos', 'status', 'created_at', 'updated_at']


class ReviewCreateSerializer(serializers.ModelSerializer):
    """리뷰 생성 Serializer"""
    image_urls = serializers.ListField(
        child=serializers.URLField(),
        required=False,
        write_only=True,
        help_text="리뷰 이미지 URL 목록"
    )

    class Meta:
        model = Review
        fields = ['product', 'order_item', 'rating', 'content', 'image_urls']

    def validate_rating(self, value):
        """평점 유효성 검사 (1-5)"""
        if value < 1 or value > 5:
            raise serializers.ValidationError("평점은 1~5 사이여야 합니다.")
        return value

    def validate(self, attrs):
        """중복 리뷰 방지"""
        request = self.context.get('request')
        product = attrs.get('product')

        # 같은 상품에 이미 리뷰를 작성했는지 확인
        if Review.objects.filter(user=request.user, product=product).exists():
            raise serializers.ValidationError("이미 이 상품에 리뷰를 작성하셨습니다.")

        return attrs

    def create(self, validated_data):
        """리뷰 생성 + 이미지 처리"""
        image_urls = validated_data.pop('image_urls', [])
        request = self.context.get('request')

        # has_photos 자동 설정
        validated_data['has_photos'] = len(image_urls) > 0
        validated_data['user'] = request.user

        review = Review.objects.create(**validated_data)

        # 이미지 생성
        for i, url in enumerate(image_urls):
            ReviewImage.objects.create(
                review=review,
                image_url=url,
                display_order=i
            )

        return review


# ========================= 판매자 상품 이미지 업로드 Serializers =========================

class ProductImageUploadSerializer(serializers.Serializer):
    """상품 메인 이미지 업로드 Serializer (파일 업로드)

    multipart/form-data로 이미지 파일을 받아 S3에 업로드합니다.
    """
    images = serializers.ListField(
        child=serializers.ImageField(),
        required=True,
        help_text="업로드할 이미지 파일 목록 (최대 10개)",
    )

    def validate_images(self, value):
        """이미지 파일 유효성 검사"""
        if len(value) > 10:
            raise serializers.ValidationError("이미지는 최대 10개까지 업로드할 수 있습니다.")

        allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
        max_size = 5 * 1024 * 1024  # 5MB

        for img in value:
            if img.content_type not in allowed_types:
                raise serializers.ValidationError(
                    f"지원하지 않는 이미지 형식입니다: {img.content_type}. "
                    f"허용 형식: JPEG, PNG, GIF, WebP"
                )
            if img.size > max_size:
                raise serializers.ValidationError(
                    f"이미지 크기가 너무 큽니다: {img.name}. 최대 5MB까지 업로드 가능합니다."
                )

        return value


class ProductDetailImageUploadSerializer(serializers.Serializer):
    """상품 상세 설명 이미지 업로드 Serializer

    상세 페이지 본문에 표시되는 이미지들을 업로드합니다.
    """
    images = serializers.ListField(
        child=serializers.ImageField(),
        required=True,
        help_text="업로드할 상세 설명 이미지 파일 목록 (최대 20개)",
    )

    def validate_images(self, value):
        """이미지 파일 유효성 검사"""
        if len(value) > 20:
            raise serializers.ValidationError("상세 이미지는 최대 20개까지 업로드할 수 있습니다.")

        allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
        max_size = 10 * 1024 * 1024  # 10MB (상세 이미지는 더 클 수 있음)

        for img in value:
            if img.content_type not in allowed_types:
                raise serializers.ValidationError(
                    f"지원하지 않는 이미지 형식입니다: {img.content_type}"
                )
            if img.size > max_size:
                raise serializers.ValidationError(
                    f"이미지 크기가 너무 큽니다: {img.name}. 최대 10MB까지 업로드 가능합니다."
                )

        return value


class SellerProductCreateSerializer(serializers.ModelSerializer):
    """판매자 상품 생성 Serializer

    상품 생성 시 ProductDetail, ProductInventory, ProductStats를 자동으로 생성합니다.

    요청 필드:
        - name (필수): 상품명
        - price (필수): 판매가
        - original_price (선택): 원가
        - category_id (선택): 카테고리 ID
        - unit (선택): 단위 (예: "1kg", "500g")
        - unit_quantity (선택): 단위 수량
        - shipping_required (선택): 배송 필요 여부 (기본: True)
        - shipping_fee (선택): 배송비
        - free_shipping_threshold (선택): 무료배송 기준금액
        - estimated_delivery_days (선택): 예상 배송일
        - stock_quantity (선택): 초기 재고 수량 (기본: 0)
        - short_description (선택): 짧은 설명
        - full_description (선택): 상세 설명
        - description (선택): full_description의 별칭

    응답 필드:
        - id: 생성된 상품 ID (이미지 업로드 등 후속 API 호출에 사용)
        - name, slug, price, original_price, unit, unit_quantity
        - shipping_required, shipping_fee, free_shipping_threshold, estimated_delivery_days
        - status: 상품 상태 (기본: 'draft')
        - product_type: 상품 유형 (기본: 'seller')
        - created_at, updated_at
    """
    # 요청 전용 필드
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source='category',
        write_only=True,
        required=False,
        allow_null=True,
        help_text="카테고리 ID"
    )

    # 재고 정보 (옵션)
    stock_quantity = serializers.IntegerField(
        write_only=True,
        required=False,
        default=0,
        help_text="초기 재고 수량"
    )

    # 상세 설명 (옵션)
    short_description = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        help_text="짧은 설명"
    )
    full_description = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        help_text="상세 설명"
    )
    # 프론트엔드 호환용 별칭 (description -> full_description)
    description = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        help_text="상세 설명 (full_description의 별칭)"
    )

    class Meta:
        model = Product
        fields = [
            # 응답 필드 (read_only)
            'id', 'status', 'product_type', 'created_at', 'updated_at',
            # 요청/응답 공통 필드
            'name', 'slug', 'price', 'original_price',
            'unit', 'unit_quantity',
            'shipping_required', 'shipping_fee',
            'free_shipping_threshold', 'estimated_delivery_days',
            # 요청 전용 필드 (write_only)
            'category_id', 'stock_quantity',
            'short_description', 'full_description', 'description'
        ]
        read_only_fields = ['id', 'status', 'product_type', 'created_at', 'updated_at']

    def validate_slug(self, value):
        """slug 중복 체크"""
        if value and Product.objects.filter(slug=value).exists():
            raise serializers.ValidationError("이미 사용 중인 슬러그입니다.")
        return value

    def validate(self, attrs):
        """description을 full_description으로 매핑"""
        # description 필드가 있고 full_description이 없으면 매핑
        description = attrs.pop('description', None)
        if description and not attrs.get('full_description'):
            attrs['full_description'] = description
        return attrs

    def _generate_unique_slug(self, name):
        """상품명 기반 고유 slug 생성"""
        from django.utils.text import slugify
        import uuid

        # 한글은 slugify로 처리 안되므로 그대로 사용하거나 UUID 추가
        base_slug = slugify(name, allow_unicode=True)
        if not base_slug:
            base_slug = 'product'

        # 고유성 보장을 위해 UUID 추가
        unique_slug = f"{base_slug}-{uuid.uuid4().hex[:8]}"

        # 만약 그래도 중복이면 재시도
        while Product.objects.filter(slug=unique_slug).exists():
            unique_slug = f"{base_slug}-{uuid.uuid4().hex[:8]}"

        return unique_slug

    def create(self, validated_data):
        """상품 생성 + 관련 테이블 자동 생성 + GMS 재료 추출"""
        import logging
        logger = logging.getLogger(__name__)

        # 추가 필드 추출
        stock_quantity = validated_data.pop('stock_quantity', 0)
        short_description = validated_data.pop('short_description', '')
        full_description = validated_data.pop('full_description', '')

        # slug가 없으면 자동 생성
        if not validated_data.get('slug'):
            validated_data['slug'] = self._generate_unique_slug(validated_data['name'])

        # 상품 생성
        product = Product.objects.create(**validated_data)

        # ProductDetail 생성
        ProductDetail.objects.create(
            product=product,
            short_description=short_description,
            full_description=full_description,
            full_image_description=[]  # 빈 배열로 초기화
        )

        # ProductInventory 생성
        ProductInventory.objects.create(
            product=product,
            stock_quantity=stock_quantity,
            safe_stock_level=10,
            is_unlimited=False
        )

        # ProductStats 생성
        ProductStats.objects.create(product=product)

        # GMS 재료 추출 (Celery 비동기 태스크로 처리)
        try:
            from products.tasks import extract_single_product
            extract_single_product.apply_async(
                args=[product.id],
                kwargs={'use_fallback': True},
                queue='high_priority',
            )
            logger.info(f"GMS 재료 추출 태스크 발행: product_id={product.id}")
        except ImportError:
            # Celery가 없는 환경에서는 동기 추출 시도
            try:
                from products.services import get_gms_extractor
                extractor = get_gms_extractor()
                parsed = extractor.extract_sync(product.name)
                if parsed:
                    product.parsed_ingredients = parsed.to_dict()
                    product.save(update_fields=['parsed_ingredients'])
                    logger.info(f"GMS 재료 추출 성공 (동기): product_id={product.id}")
            except Exception as e:
                logger.warning(f"GMS 재료 추출 실패 (product_id={product.id}): {e}")
        except Exception as e:
            logger.warning(f"GMS 태스크 발행 실패 (product_id={product.id}): {e}")

        return product
