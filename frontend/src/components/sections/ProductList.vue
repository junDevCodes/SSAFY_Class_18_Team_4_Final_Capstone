<template>
  <section
    id="recommend"
    class="pt-0 pb-16 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8"
  >
    <div class="flex flex-col md:flex-row justify-between items-start md:items-end mb-4 gap-4">
      <div>
        <!-- 로그인 여부에 따라 타이틀 변경 -->
        <h3 class="text-3xl font-display font-bold text-gray-900 mb-3">
          {{ isAuthenticated ? '나를 위한 추천' : "MD's Pick" }}
        </h3>
        <p class="text-gray-500">
          {{ isAuthenticated ? 'AI가 분석한 맞춤 상품' : '전문 MD가 엄선한 가장 신선한 제철 상품' }}
        </p>
      </div>
      <RouterLink
        :to="{ name: 'products' }"
        class="text-sm font-bold border-b border-gray-900 pb-0.5 hover:text-brand-600 hover:border-brand-600 transition-colors"
      >
        전체보기
      </RouterLink>
    </div>

    <!-- 로딩 상태 -->
    <div v-if="loading" class="flex justify-center items-center py-20">
      <div class="text-gray-500">로딩 중...</div>
    </div>

    <!-- 에러 상태 -->
    <div v-else-if="error" class="flex justify-center items-center py-20">
      <div class="text-red-500">{{ error }}</div>
    </div>

    <!-- 상품 그리드 -->
    <div v-else class="grid grid-cols-2 lg:grid-cols-4 gap-x-6 gap-y-12">
      <ProductCard
        v-for="product in displayProducts"
        :key="product.id"
        :product="product"
      />
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useProductStore } from '@/stores/products'
import { recommendationsAPI, type PersonalizedProduct } from '@/services/api'
import ProductCard from '@/components/ui/ProductCard.vue'
import type { Product } from '@/types/product'

const authStore = useAuthStore()
const productStore = useProductStore()

// 상태
const personalizedProducts = ref<PersonalizedProduct[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const isPersonalized = ref(false)

// Computed
const isAuthenticated = computed(() => authStore.isAuthenticated)

/**
 * 표시할 상품 목록
 * 로그인 사용자: 개인화 추천 상품을 Product 형식으로 변환
 * 비로그인/실패: 기존 상품 목록
 */
const displayProducts = computed<Product[]>(() => {
  if (isAuthenticated.value && isPersonalized.value && personalizedProducts.value.length > 0) {
    // 개인화 추천 상품을 Product 형식으로 변환
    return personalizedProducts.value.map(p => ({
      id: p.product_id,
      slug: p.slug || `product-${p.product_id}`,
      name: p.name,
      price: p.price,
      original_price: p.original_price,
      unit: null,
      main_image: p.main_image,
      category: null,
      category_name: p.category_name,
      status: 'active' as const,
      product_type: 'main' as const,
      created_at: '',
      view_count: p.view_count,
      average_rating: p.average_rating,
      review_count: 0,
      wishlist_count: p.wishlist_count,
      quality_score: p.recommendation_score,
    }))
  }
  // 비로그인 또는 개인화 추천 실패 시 기존 상품 목록
  return productStore.products
})

/**
 * 개인화 추천 가져오기
 * ALS 32차원 모델 기반 개인화 추천
 */
const fetchPersonalizedRecommendations = async () => {
  loading.value = true
  error.value = null
  isPersonalized.value = false

  try {
    const { data } = await recommendationsAPI.getPersonalizedRecommendations({
      limit: 8,
      page_type: 'home',
    })
    personalizedProducts.value = data.products
    isPersonalized.value = true
  } catch (err) {
    console.error('개인화 추천 실패, 폴백으로 전환:', err)
    // 폴백: 일반 상품 목록
    await fetchFallbackProducts()
  } finally {
    loading.value = false
  }
}

/**
 * 폴백: 일반 상품 목록
 * 개인화 추천 실패 또는 비로그인 시
 */
const fetchFallbackProducts = async () => {
  loading.value = true
  error.value = null
  isPersonalized.value = false

  try {
    await productStore.fetchProducts({ page_size: 8 })
  } catch (err) {
    error.value = '상품 목록을 불러오는 데 실패했습니다.'
    console.error('Failed to fetch products:', err)
  } finally {
    loading.value = false
  }
}

/**
 * 데이터 로딩
 * 로그인 여부에 따라 개인화 추천 또는 일반 상품 목록
 */
const loadData = async () => {
  if (isAuthenticated.value) {
    // 로그인 사용자: 개인화 추천
    await fetchPersonalizedRecommendations()
  } else {
    // 비로그인: 일반 상품 목록
    await fetchFallbackProducts()
  }
}

// 마운트 시 데이터 로딩
onMounted(loadData)

// 로그인 상태 변경 시 데이터 재로딩
watch(isAuthenticated, (newValue, oldValue) => {
  if (newValue !== oldValue) {
    loadData()
  }
})
</script>
