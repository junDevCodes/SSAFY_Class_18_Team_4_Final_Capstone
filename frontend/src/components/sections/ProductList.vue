<template>
  <section
    id="recommend"
    class="pt-0 pb-16 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8"
  >
    <div class="flex flex-col md:flex-row justify-between items-start md:items-end mb-4 gap-4">
      <div>
        <h3 class="text-3xl font-display font-bold text-gray-900 mb-3">MD's Pick</h3>
        <p class="text-gray-500">
          {{ sectionDescription }}
        </p>
      </div>
      <RouterLink
        :to="{ name: 'products' }"
        class="text-sm font-bold border-b border-gray-900 pb-0.5 hover:text-brand-600 hover:border-brand-600 transition-colors"
      >
        전체보기
      </RouterLink>
    </div>

    <div v-if="loading" class="flex justify-center items-center py-20">
      <div class="text-gray-500">로딩 중...</div>
    </div>

    <div v-else-if="error" class="flex justify-center items-center py-20">
      <div class="text-red-500">{{ error }}</div>
    </div>

    <div v-else class="grid grid-cols-2 lg:grid-cols-4 gap-x-6 gap-y-12">
      <ProductCard
        v-for="product in products"
        :key="product.id"
        :product="product"
      />
    </div>

    <!-- 디버그 정보 (개발 모드에서만 표시) -->
    <div v-if="isDev && modelInfo" class="mt-4 p-2 bg-gray-100 rounded text-xs text-gray-600">
      <span>추천 모델: {{ modelInfo.model_name }}</span>
      <span class="ml-4">사용자 타입: {{ modelInfo.user_type }}</span>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { recommendationApi } from '@/services/api/recommendations'
import { useProductStore } from '@/stores/products'
import ProductCard from '@/components/ui/ProductCard.vue'
import type { Product } from '@/types/product'

// 상태
const products = ref<Product[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const modelInfo = ref<{ model_name: string; user_type: string } | null>(null)

// 개발 모드 여부
const isDev = import.meta.env.DEV

// Fallback용 product store
const productStore = useProductStore()

// 섹션 설명 (추천 타입에 따라 동적 변경)
const sectionDescription = computed(() => {
  if (!modelInfo.value) {
    return '전문 MD가 엄선한 가장 신선한 제철 상품'
  }

  const { user_type, model_name } = modelInfo.value

  if (model_name === 'fallback') {
    return '전문 MD가 엄선한 가장 신선한 제철 상품'
  }

  if (user_type === 'warm' || user_type === 'hot') {
    return '회원님의 취향을 반영한 맞춤 추천 상품'
  }

  return '지금 가장 인기있는 추천 상품'
})

/**
 * 홈 추천 상품 가져오기
 * ML 추천 API 호출 후 실패 시 일반 상품 API로 fallback
 */
const fetchHomeRecommendations = async () => {
  loading.value = true
  error.value = null

  try {
    // ML 추천 API 호출
    const response = await recommendationApi.getHomeRecommendations(8)
    products.value = response.products
    modelInfo.value = {
      model_name: response.model_name,
      user_type: response.user_type,
    }

    // 추천 결과가 비어있으면 fallback
    if (products.value.length === 0) {
      console.warn('추천 결과 없음, fallback 사용')
      await fallbackToProducts()
    }
  } catch (err) {
    console.warn('추천 API 호출 실패, fallback 사용:', err)
    await fallbackToProducts()
  } finally {
    loading.value = false
  }
}

/**
 * 추천 실패 시 일반 상품 API로 fallback
 */
const fallbackToProducts = async () => {
  try {
    await productStore.fetchProducts({ page_size: 8 })
    products.value = productStore.products
    modelInfo.value = {
      model_name: 'fallback',
      user_type: 'cold',
    }
  } catch (fallbackErr) {
    error.value = '상품 목록을 불러오는 데 실패했습니다.'
    console.error('Fallback 실패:', fallbackErr)
  }
}

onMounted(() => {
  fetchHomeRecommendations()
})
</script>

