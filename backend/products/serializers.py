"""
제품 관련 Serializer
"""
from rest_framework import serializers
from .models import Category, Product, ProductImage, Wishlist, Cart


class CategorySerializer(serializers.ModelSerializer):
    """카테고리 Serializer"""

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class ProductSerializer(serializers.ModelSerializer):
    """제품 Serializer"""
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
            'category',
            'category_id',
            'site_name',
            'name',
            'price',
            'unit',
            'description',
            'product_url',
            'image_url',
            'detail_info',
            'crawled_at',
            'original_price',
            'discount',
            'is_best',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ProductImageSerializer(serializers.ModelSerializer):
    """상품 이미지 Serializer"""

    class Meta:
        model = ProductImage
        fields = ['id', 'image_url', 'alt_text', 'display_order', 'width', 'height', 'format']


class ProductListSerializer(serializers.ModelSerializer):
    """상품 목록용 Serializer (간소화)"""

    category_name = serializers.CharField(source='category.name', read_only=True)
    main_image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id',
            'slug',
            'name',
            'price',
            'original_price',
            'discount_rate',
            'unit',
            'main_image',
            'category_name',
            'is_featured',
            'is_best',
            'is_new',
            'is_on_sale',
            'quality_score',
            'view_count',
            'average_rating',
            'review_count',
        ]

    def get_main_image(self, obj):
        """메인 이미지 URL 반환"""
        return obj.main_image_url or obj.image_url


class SellerBriefSerializer(serializers.Serializer):
    """판매자 간단 정보 (ProductDetailSerializer용)"""

    brand_name = serializers.CharField()
    brand_slug = serializers.CharField()
    average_rating = serializers.DecimalField(max_digits=3, decimal_places=2)
    total_products = serializers.IntegerField()


class ProductDetailSerializer(serializers.ModelSerializer):
    """상품 상세 Serializer"""

    category = CategorySerializer(read_only=True)
    seller = SellerBriefSerializer(read_only=True, allow_null=True)
    images = ProductImageSerializer(many=True, read_only=True)

    # 추가 정보
    is_wishlist = serializers.SerializerMethodField()
    related_products = serializers.SerializerMethodField()
    final_price = serializers.IntegerField(read_only=True)

    class Meta:
        model = Product
        fields = '__all__'

    def get_is_wishlist(self, obj):
        """찜 여부 확인"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Wishlist.objects.filter(user=request.user, product=obj).exists()
        return False

    def get_related_products(self, obj):
        """관련 상품 추천 (같은 카테고리)"""
        related = Product.objects.filter(
            category=obj.category,
            status='active'
        ).exclude(id=obj.id).order_by('-quality_score')[:6]

        return ProductListSerializer(related, many=True, context=self.context).data


class WishlistSerializer(serializers.ModelSerializer):
    """찜 목록 Serializer"""

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
    """장바구니 Serializer"""

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
