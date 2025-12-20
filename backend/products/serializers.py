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
    wishlist_count = serializers.SerializerMethodField()
    quality_score = serializers.SerializerMethodField()

    # 재고 정보
    stock_quantity = serializers.SerializerMethodField()

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
            'wishlist_count',
            'quality_score',
            'stock_quantity',
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
