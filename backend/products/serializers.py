"""
제품 관련 Serializer
"""
from rest_framework import serializers
from .models import Category, Product


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
