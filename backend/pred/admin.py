"""
추천 시스템 어드민 설정
"""

from django.contrib import admin
from .models import (
    PredInstacartDepartment,
    PredInstacartAisle,
    PredInstacartProduct,
    PredInstacartOrder,
    PredInstacartOrderItem,
    PredInstacartTimePattern,
    PredInstacartCategoryMapping,
    PredProductMapping,
    PredItemSimilarity,
    PredRecipe,
    PredIngredient,
    PredRecipeIngredient,
    PredIngredientProduct,
    PredProductEmbedding,
    PredUserEmbedding,
    PredRecommendationCache,
    PredPriceAnomalyCache,
)


# ===================================
# Instacart 관련 어드민
# ===================================

@admin.register(PredInstacartDepartment)
class PredInstacartDepartmentAdmin(admin.ModelAdmin):
    """Instacart 부서 어드민"""
    list_display = ['id', 'name', 'created_at']
    search_fields = ['name']
    ordering = ['id']


@admin.register(PredInstacartAisle)
class PredInstacartAisleAdmin(admin.ModelAdmin):
    """Instacart 통로 어드민"""
    list_display = ['id', 'department', 'name', 'created_at']
    list_filter = ['department']
    search_fields = ['name']
    ordering = ['department', 'id']


@admin.register(PredInstacartProduct)
class PredInstacartProductAdmin(admin.ModelAdmin):
    """Instacart 상품 어드민"""
    list_display = ['id', 'name', 'aisle', 'order_count', 'reorder_rate']
    list_filter = ['aisle__department']
    search_fields = ['name', 'name_normalized']
    ordering = ['-order_count']


@admin.register(PredInstacartTimePattern)
class PredInstacartTimePatternAdmin(admin.ModelAdmin):
    """시간대별 패턴 어드민"""
    list_display = ['time_slot', 'day_type', 'instacart_department', 'self_category', 'popularity_score']
    list_filter = ['time_slot', 'day_type']
    ordering = ['-popularity_score']


@admin.register(PredInstacartCategoryMapping)
class PredInstacartCategoryMappingAdmin(admin.ModelAdmin):
    """카테고리 매핑 어드민"""
    list_display = ['instacart_department', 'instacart_aisle', 'self_category', 'confidence_score', 'is_active']
    list_filter = ['is_active', 'instacart_department']
    search_fields = ['self_category__name']


# ===================================
# Recipe 관련 어드민
# ===================================

@admin.register(PredRecipe)
class PredRecipeAdmin(admin.ModelAdmin):
    """레시피 어드민"""
    list_display = ['id', 'name', 'category_main', 'category_sub', 'rating', 'is_active']
    list_filter = ['category_main', 'is_active']
    search_fields = ['name', 'name_normalized']
    ordering = ['-rating']


@admin.register(PredIngredient)
class PredIngredientAdmin(admin.ModelAdmin):
    """재료 어드민"""
    list_display = ['id', 'name', 'category', 'is_processed']
    list_filter = ['category', 'is_processed']
    search_fields = ['name', 'name_normalized']


@admin.register(PredRecipeIngredient)
class PredRecipeIngredientAdmin(admin.ModelAdmin):
    """레시피-재료 관계 어드민"""
    list_display = ['recipe', 'ingredient', 'quantity_text', 'is_required', 'is_main']
    list_filter = ['is_required', 'is_main']
    search_fields = ['recipe__name', 'ingredient__name']


@admin.register(PredIngredientProduct)
class PredIngredientProductAdmin(admin.ModelAdmin):
    """재료-상품 매핑 어드민"""
    list_display = ['ingredient', 'product', 'similarity_score', 'mapping_method', 'is_active']
    list_filter = ['mapping_method', 'is_active']
    search_fields = ['ingredient__name', 'product__name']


# ===================================
# Embedding 관련 어드민
# ===================================

@admin.register(PredProductEmbedding)
class PredProductEmbeddingAdmin(admin.ModelAdmin):
    """상품 임베딩 어드민"""
    list_display = ['product', 'bert_version', 'bert_updated_at', 'has_embedding']
    list_filter = ['bert_version']
    search_fields = ['product__name']

    def has_embedding(self, obj):
        return obj.has_embedding
    has_embedding.boolean = True
    has_embedding.short_description = '임베딩 존재'


@admin.register(PredUserEmbedding)
class PredUserEmbeddingAdmin(admin.ModelAdmin):
    """사용자 임베딩 어드민"""
    list_display = ['user', 'user_type', 'interaction_count', 'updated_at', 'has_embedding']
    list_filter = ['user_type']
    search_fields = ['user__username', 'user__email']

    def has_embedding(self, obj):
        return obj.has_embedding
    has_embedding.boolean = True
    has_embedding.short_description = '임베딩 존재'


# ===================================
# Cache 관련 어드민
# ===================================

@admin.register(PredRecommendationCache)
class PredRecommendationCacheAdmin(admin.ModelAdmin):
    """추천 캐시 어드민"""
    list_display = ['user', 'page_type', 'expires_at', 'is_expired', 'created_at']
    list_filter = ['page_type']
    search_fields = ['user__username']
    readonly_fields = ['recommendations']

    def is_expired(self, obj):
        return obj.is_expired
    is_expired.boolean = True
    is_expired.short_description = '만료됨'


@admin.register(PredPriceAnomalyCache)
class PredPriceAnommalyCacheAdmin(admin.ModelAdmin):
    """가격 이상치 캐시 어드민"""
    list_display = ['product', 'current_price', 'price_change_rate', 'anomaly_score', 'detection_methods', 'expires_at']
    list_filter = ['detection_methods']
    search_fields = ['product__name']
    ordering = ['-anomaly_score']
