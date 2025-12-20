<template>
  <main class="bg-gray-50 min-h-screen pt-28 pb-16">
    <section class="max-w-6xl mx-auto px-4 space-y-10">
      <header class="space-y-4">
        <p class="text-sm font-semibold text-brand-600">Fresh 몰</p>
        <div class="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div class="space-y-2">
            <h1 class="text-3xl font-display font-bold text-gray-900">동네 셀러의 신선식품을 한눈에</h1>
            <p class="text-gray-600">배송/온도/원산지 필터와 셀러 스토리로 신뢰도를 확인하세요.</p>
          </div>
          <div class="flex flex-wrap gap-2">
            <button
              v-for="opt in sortOptions"
              :key="opt"
              class="px-4 py-2 rounded-full border text-sm font-semibold transition-colors"
              :class="opt === sortOption ? 'bg-brand-600 text-white border-brand-600' : 'bg-white text-gray-700 border-gray-200 hover:border-brand-200 hover:text-brand-600'"
              @click="sortOption = opt"
            >
              {{ opt }}
            </button>
          </div>
        </div>
      </header>

      <section class="space-y-4">
        <div class="flex items-center justify-between">
          <h2 class="text-xl font-bold text-gray-900">셀러 스토리</h2>
          <button class="text-sm font-semibold text-brand-700 hover:text-brand-800" @click="goToAllSellerProducts">모두 보기</button>
        </div>
        <div class="story-row">
          <article
            v-for="story in sellerStories"
            :key="story.id"
            class="story-card"
          >
            <img :src="story.cover" :alt="story.name" class="w-full h-28 object-cover rounded-lg mb-3">
            <p class="text-sm font-semibold text-gray-900">{{ story.name }}</p>
            <p class="text-xs text-gray-600 line-clamp-2">{{ story.desc }}</p>
            <button class="mt-3 text-xs font-semibold text-brand-700 hover:text-brand-800">스토어 보기</button>
          </article>
        </div>
      </section>

      <div v-if="loading" class="flex items-center justify-center py-16 text-gray-500">로딩 중...</div>
      <div v-else-if="fetchError" class="flex items-center justify-center py-16 text-red-500">{{ fetchError }}</div>
      <div v-else-if="!visibleProducts.length" class="flex items-center justify-center py-16 text-gray-500">
        등록된 상품이 없습니다.
      </div>
      <div v-else class="grid gap-6 grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
        <ProductCard
          v-for="product in visibleProducts"
          :key="product.id"
          :product="product"
          label="FRESH"
        />
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import type { Product } from '@/types/product'
import ProductCard from '@/components/ui/ProductCard.vue'
import { productsAPI } from '@/services/api'

const router = useRouter()

type FreshProduct = Product

const sortOptions = ['신규 셀러', '판매순', '리뷰순']
const sortOption = ref('신규 셀러')

const sellerStories = ref([
  { id: 's1', name: '완주 로컬 농가', desc: '새벽에 수확한 채소를 바로 포장합니다.', cover: 'https://images.unsplash.com/photo-1582719478248-54e9f2b2d1c5' },
  { id: 's2', name: '통영 수산 셀러', desc: '산지 직송 해산물을 빠르게 배송.', cover: 'https://images.unsplash.com/photo-1526379879527-8559ecfcaec0' },
  { id: 's3', name: '정육 셀렉션', desc: '초신선 숙성 한우를 소량으로 준비.', cover: 'https://images.unsplash.com/photo-1604908177453-7462950a6a0d' },
  { id: 's4', name: '비건 수제식품', desc: '첨가물 없이 수제로 만드는 비건 간식.', cover: 'https://images.unsplash.com/photo-1499636136210-6f4ee915583e' }
])

const freshProducts = ref<FreshProduct[]>([])
const loading = ref(false)
const fetchError = ref<string | null>(null)

const sortedProducts = computed(() => {
  const recentFirst = (a: FreshProduct, b: FreshProduct) =>
    new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  const oneMonthAgo = (() => {
    const base = new Date()
    base.setMonth(base.getMonth() - 1)
    return base.getTime()
  })()

  if (sortOption.value === '신규 셀러') {
    return freshProducts.value
      .filter((p) => {
        const created = new Date(p.created_at).getTime()
        return !Number.isNaN(created) && created >= oneMonthAgo
      })
      .sort(recentFirst)
  }

  if (sortOption.value === '판매순') {
    return [...freshProducts.value].sort((a, b) => {
      const salesDiff = (b.view_count || 0) - (a.view_count || 0)
      if (salesDiff !== 0) return salesDiff
      return recentFirst(a, b)
    })
  }
  if (sortOption.value === '리뷰순') {
    return [...freshProducts.value].sort((a, b) => {
      const reviewDiff = (b.review_count || 0) - (a.review_count || 0)
      if (reviewDiff !== 0) return reviewDiff
      return recentFirst(a, b)
    })
  }
  // 신규 셀러: 최근 등록 순
  return [...freshProducts.value].sort(recentFirst)
})

const visibleProducts = computed(() => sortedProducts.value.slice(0, 8))

const goToAllSellerProducts = () => {
  router.push({ name: 'products', query: { product_type: 'seller' } })
}

const fetchFreshProducts = async () => {
  loading.value = true
  fetchError.value = null
  try {
    const { data } = await productsAPI.getProducts({
      product_type: 'seller',
      page_size: 24,
      ordering: '-created_at',
    })
    freshProducts.value = data.results
  } catch (error) {
    console.error('Failed to load seller products:', error)
    fetchError.value = '상품을 불러오는 데 실패했습니다.'
    freshProducts.value = []
  } finally {
    loading.value = false
  }
}

onMounted(fetchFreshProducts)
</script>

<style scoped>
.chip {
  @apply px-4 py-2 rounded-full border text-sm font-medium transition-colors;
}
.story-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
}
.story-card {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 12px;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.04);
}
</style>
