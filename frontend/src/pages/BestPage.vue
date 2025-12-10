<template>
  <main class="bg-gray-50 min-h-screen pt-28 pb-16">
    <section class="max-w-6xl mx-auto px-4 space-y-8">
      <header class="space-y-4">
        <p class="text-sm font-semibold text-brand-600">베스트</p>
        <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div class="space-y-2">
            <h1 class="text-3xl font-display font-bold text-gray-900">지금 가장 인기 있는 셀렉션</h1>
            <p class="text-gray-600">판매, 리뷰, 평점 기준으로 매일 업데이트돼요.</p>
          </div>
          <div class="flex flex-wrap gap-2">
            <button
              v-for="opt in sortOptions"
              :key="opt"
              class="px-4 py-2 rounded-full border text-sm font-semibold transition-colors"
              :class="opt === selectedSort ? 'bg-brand-600 text-white border-brand-600' : 'bg-white text-gray-700 border-gray-200 hover:border-brand-200 hover:text-brand-600'"
              @click="selectedSort = opt"
            >
              {{ opt }}
            </button>
          </div>
        </div>

        <div class="flex flex-wrap gap-2">
          <button
            v-for="cat in categories"
            :key="cat"
            class="px-4 py-2 rounded-full border text-sm font-medium transition-colors"
            :class="cat === selectedCategory ? 'bg-brand-50 text-brand-700 border-brand-200' : 'bg-white text-gray-700 border-gray-200 hover:border-brand-200 hover:text-brand-600'"
            @click="selectedCategory = cat"
          >
            {{ cat }}
          </button>
        </div>
      </header>

      <div class="grid gap-6 grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
        <ProductCard
          v-for="product in filteredBest"
          :key="product.id"
          :product="product"
          label="BEST"
          :meta="product.categoryTag"
          :badges="['리뷰 ' + product.review_count]"
        />
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

const categories = ['전체', '간편식', '신선', '간식', '음료']
const sortOptions = ['판매순', '리뷰순', '평점순']

const selectedCategory = ref('전체')
const selectedSort = ref('판매순')

const bestProducts = ref<BestProduct[]>([
  { ...createMockProduct({ id: 1, slug: 'granola', name: '아침 그래놀라 볼', price: 12900, category_name: '간편식', main_image: 'https://images.unsplash.com/photo-1505253758473-96b7015fcd40', review_count: 182, average_rating: 4.8 }), categoryTag: '간편식', view_count: 950 },
  { ...createMockProduct({ id: 2, slug: 'egg-pack', name: '평창 유정란 15구', price: 8900, category_name: '신선', main_image: 'https://images.unsplash.com/photo-1576402187878-974f70c890a5', review_count: 254, average_rating: 4.9 }), categoryTag: '신선', view_count: 1400 },
  { ...createMockProduct({ id: 3, slug: 'dumpling', name: '든든한 만두 세트', price: 10900, category_name: '간편식', main_image: 'https://images.unsplash.com/photo-1504674900247-0877df9cc836', review_count: 321, average_rating: 4.7 }), categoryTag: '간편식', view_count: 1800 },
  { ...createMockProduct({ id: 4, slug: 'snack-pack', name: '고소한 넛츠 믹스', price: 5900, category_name: '간식', main_image: 'https://images.unsplash.com/photo-1504674900247-0877df9cc836', review_count: 120, average_rating: 4.5 }), categoryTag: '간식', view_count: 760 },
  { ...createMockProduct({ id: 5, slug: 'steak-cut', name: '프리미엄 스테이크 컷', price: 23900, category_name: '신선', main_image: 'https://images.unsplash.com/photo-1604908177453-7462950a6a0d', review_count: 88, average_rating: 4.6 }), categoryTag: '신선', view_count: 640 },
  { ...createMockProduct({ id: 6, slug: 'juice-cold', name: '콜드프레스 주스 3종', price: 11900, category_name: '음료', main_image: 'https://images.unsplash.com/photo-1467003909585-2f8a72700288', review_count: 70, average_rating: 4.4 }), categoryTag: '음료', view_count: 530 },
  { ...createMockProduct({ id: 7, slug: 'cookie-box', name: '홈메이드 쿠키 박스', price: 9900, category_name: '간식', main_image: 'https://images.unsplash.com/photo-1499636136210-6f4ee915583e', review_count: 96, average_rating: 4.6 }), categoryTag: '간식', view_count: 840 },
  { ...createMockProduct({ id: 8, slug: 'salad-bowl', name: '프레시 샐러드 볼', price: 8900, category_name: '신선', main_image: 'https://images.unsplash.com/photo-1552332386-f8dd00dc2f85', review_count: 210, average_rating: 4.8 }), categoryTag: '신선', view_count: 1650 }
])

const filteredBest = computed(() => {
  const filtered =
    selectedCategory.value === '전체'
      ? bestProducts.value
      : bestProducts.value.filter((p) => p.categoryTag === selectedCategory.value)

  const sorted = [...filtered]
  if (selectedSort.value === '리뷰순') {
    return sorted.sort((a, b) => b.review_count - a.review_count)
  }
  if (selectedSort.value === '평점순') {
    return sorted.sort((a, b) => b.average_rating - a.average_rating)
  }
  return sorted.sort((a, b) => (b.view_count || 0) - (a.view_count || 0))
})
</script>
