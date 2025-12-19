<template>
  <main class="bg-gray-50 min-h-screen pt-28 pb-16">
    <section class="max-w-6xl mx-auto px-4 space-y-8">
      <header class="space-y-6">
        <div class="space-y-3">
          <p class="text-sm font-semibold text-brand-600">베스트</p>
          <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div class="space-y-2">
              <h1 class="text-3xl font-display font-bold text-gray-900">지금 가장 인기 있는 셀렉션</h1>
              <p class="text-gray-600">판매, 리뷰, 평점을 기준으로 엄선한 베스트 모음을 둘러보세요.</p>
            </div>
            <div class="flex flex-wrap gap-2">
              <button
                v-for="opt in sortOptions"
                :key="opt"
                class="px-4 py-2 rounded-full border text-sm font-semibold transition-colors"
                :class="opt === selectedSort ? 'bg-brand-600 text-white border-brand-600 shadow-sm' : 'bg-white text-gray-700 border-gray-200 hover:border-brand-200 hover:text-brand-600'"
                @click="handleSortChange(opt)"
              >
                {{ opt }}
              </button>
            </div>
          </div>
        </div>
      </header>

      <div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 space-y-6">
        <div class="grid gap-6 grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
          <ProductCard v-for="product in paginatedBest" :key="product.id" :product="product" />
        </div>

        <div class="flex flex-col items-center justify-center gap-3 pt-2">
          <span class="text-sm text-gray-500">총 {{ totalPages }}페이지 · {{ bestProducts.length }}개 상품</span>
          <div class="flex items-center gap-2">
            <button
              class="px-3 py-2 rounded-full border text-sm font-medium text-gray-700 hover:text-brand-600 hover:border-brand-200 disabled:opacity-40"
              :disabled="currentPage === 1"
              @click="goToPage(currentPage - 1)"
            >
              이전
            </button>
            <button
              v-for="page in totalPages"
              :key="page"
              class="w-10 h-10 rounded-full border text-sm font-semibold transition-colors"
              :class="page === currentPage ? 'bg-brand-600 text-white border-brand-600 shadow-sm' : 'bg-white text-gray-700 border-gray-200 hover:border-brand-200 hover:text-brand-600'"
              @click="goToPage(page)"
            >
              {{ page }}
            </button>
            <button
              class="px-3 py-2 rounded-full border text-sm font-medium text-gray-700 hover:text-brand-600 hover:border-brand-200 disabled:opacity-40"
              :disabled="currentPage === totalPages"
              @click="goToPage(currentPage + 1)"
            >
              다음
            </button>
          </div>
        </div>
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { Product } from '@/types/product'
import ProductCard from '@/components/ui/ProductCard.vue'
import { createMockProduct } from './mallMock'

type BestProduct = Product & { categoryTag: string }
type SortOption = '판매순' | '리뷰순' | '평점순'

const pageSize = 8
const sortOptions: SortOption[] = ['판매순', '리뷰순', '평점순']
const selectedSort = ref<SortOption>('판매순')
const currentPage = ref(1)

const heroImages = [
  'https://images.unsplash.com/photo-1504674900247-0877df9cc836?auto=format&fit=crop&w=1200&q=80',
  'https://images.unsplash.com/photo-1529006557810-274b9b2fc783?auto=format&fit=crop&w=1200&q=80',
  'https://images.unsplash.com/photo-1504674761085-54f48f0af0ee?auto=format&fit=crop&w=1200&q=80',
  'https://images.unsplash.com/photo-1481931098730-318b6f776db0?auto=format&fit=crop&w=1200&q=80',
  'https://images.unsplash.com/photo-1604908177453-7462950a6a0d?auto=format&fit=crop&w=1200&q=80',
  'https://images.unsplash.com/photo-1467003909585-2f8a72700288?auto=format&fit=crop&w=1200&q=80'
]

const bestProducts = ref<BestProduct[]>(
  Array.from({ length: 40 }, (_, idx) => {
    const rank = 40 - idx
    const ratingBase = 4.1 + rank * 0.02
    const product = createMockProduct({
      id: idx + 1,
      slug: `best-item-${idx + 1}`,
      name: `베스트 셀렉션 ${idx + 1}`,
      price: 7900 + (idx % 6) * 700,
      category_name: '베스트',
      main_image: heroImages[idx % heroImages.length],
      review_count: 60 + rank * 4,
      average_rating: Math.min(5, Number(ratingBase.toFixed(1))),
      view_count: 500 + rank * 35,
      wishlist_count: Math.round(rank * 0.6),
      quality_score: 0
    })

    return {
      ...product,
      categoryTag: `셀렉션 ${Math.floor(idx / pageSize) + 1}`
    }
  })
)

const sortedBest = computed(() => {
  const sorted = [...bestProducts.value]
  if (selectedSort.value === '리뷰순') {
    return sorted.sort((a, b) => b.review_count - a.review_count)
  }
  if (selectedSort.value === '평점순') {
    return sorted.sort((a, b) => b.average_rating - a.average_rating || b.review_count - a.review_count)
  }
  return sorted.sort((a, b) => (b.view_count || 0) - (a.view_count || 0))
})

const totalPages = computed(() => Math.max(1, Math.ceil(sortedBest.value.length / pageSize)))
const paginatedBest = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  return sortedBest.value.slice(start, start + pageSize)
})

const handleSortChange = (opt: SortOption) => {
  selectedSort.value = opt
  currentPage.value = 1
}

const goToPage = (page: number) => {
  const next = Math.min(totalPages.value, Math.max(1, page))
  currentPage.value = next
}
</script>
