<template>
  <section
    v-if="shouldShow"
    id="onboarding-recommend"
    class="pt-0 pb-16 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8"
  >
    <div class="flex flex-col md:flex-row justify-between items-start md:items-end mb-4 gap-4">
      <div>
        <h3 class="text-3xl font-display font-bold text-gray-900 mb-3">
          나의 취향 추천
        </h3>
        <p class="text-gray-500">
          온보딩에서 선택한 취향 기반 인기 상품
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
import { recommendationsAPI, type OnboardingProduct } from '@/services/api'
import ProductCard from '@/components/ui/ProductCard.vue'
import type { Product } from '@/types/product'

const authStore = useAuthStore()

// 상태
const onboardingProducts = ref<OnboardingProduct[]>([])
const loading = ref(false)
const hasOnboarding = ref(false)

// Computed
const isAuthenticated = computed(() => authStore.isAuthenticated)

/**
 * 섹션 표시 여부
 * - 로그인 상태이고
 * - 온보딩 완료했고
 * - 추천 상품이 있을 때만 표시
 */
const shouldShow = computed(() => {
  return isAuthenticated.value && hasOnboarding.value && onboardingProducts.value.length > 0
})

/**
 * 표시할 상품 목록
 * 백엔드 응답 → Product 형식으로 변환
 */
const displayProducts = computed<Product[]>(() => {
  return onboardingProducts.value.map(p => ({
    id: p.id,
    slug: p.slug || `product-${p.id}`,
    name: p.name,
    price: p.price,
    original_price: p.original_price,
    unit: p.unit,
    main_image: p.main_image,
    // category는 Product 타입과 맞추기 위해 undefined로 설정 (category_name 사용)
    category: undefined,
    category_name: p.category_name,
    status: (p.status || 'active') as Product['status'],
    product_type: (p.product_type || 'main') as Product['product_type'],
    created_at: p.created_at || '',
    view_count: p.view_count || 0,
    average_rating: p.average_rating || 0,
    review_count: p.review_count || 0,
    wishlist_count: p.wishlist_count || 0,
    quality_score: p.quality_score ?? 0,
  }))
})

/**
 * 온보딩 기반 추천 상품 가져오기
 */
const fetchOnboardingRecommendations = async () => {
  if (!isAuthenticated.value) {
    hasOnboarding.value = false
    return
  }

  loading.value = true

  try {
    const { data } = await recommendationsAPI.getOnboardingRecommendations({ limit: 8 })
    onboardingProducts.value = data.products
    hasOnboarding.value = data.total_count > 0

    if (data.total_count > 0) {
      console.log(`온보딩 추천 완료: 상품 수=${data.total_count}`)
    }
  } catch (err) {
    // 401 에러 (미인증) 또는 온보딩 미완료는 조용히 처리
    console.debug('온보딩 추천 조회 실패 (미완료 또는 미인증):', err)
    hasOnboarding.value = false
  } finally {
    loading.value = false
  }
}

// 마운트 시 데이터 로딩
onMounted(fetchOnboardingRecommendations)

// 로그인 상태 변경 시 데이터 재로딩
watch(isAuthenticated, (newValue, oldValue) => {
  if (newValue !== oldValue) {
    if (newValue) {
      fetchOnboardingRecommendations()
    } else {
      // 로그아웃 시 초기화
      onboardingProducts.value = []
      hasOnboarding.value = false
    }
  }
})
</script>
