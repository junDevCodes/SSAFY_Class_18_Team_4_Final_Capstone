<template>
  <main class="bg-gray-50 min-h-screen pt-28 pb-16">
    <section class="max-w-6xl mx-auto px-4 space-y-8">
      <div class="relative overflow-hidden rounded-2xl bg-gradient-to-r from-indigo-900 via-brand-700 to-brand-500 text-white p-10 shadow-xl">
        <div class="space-y-3 max-w-2xl">
          <p class="text-sm font-semibold uppercase tracking-widest text-white/80">SelF Mall</p>
          <h1 class="text-3xl font-display font-bold">SelF Mall 만의 Fresh 함을 골라보세요</h1>
          <div class="flex flex-wrap gap-3">
            <button class="px-4 py-2 rounded-full border border-white/60 text-white font-semibold hover:bg-white/10 transition-colors" @click="selectAll">전체보기</button>
            <button class="px-4 py-2 rounded-full border border-white/60 text-white hover:bg-white/10 transition-colors" @click="selectWeekly">주간 특가</button>
          </div>
        </div>
        <div class="absolute -right-10 -bottom-16 w-72 h-72 bg-white/10 rounded-full blur-3xl"></div>
      </div>

      <div class="flex flex-wrap gap-2">
        <button
          v-for="tag in pbTags"
          :key="tag"
          class="px-4 py-2 rounded-full border text-sm font-medium transition-colors"
          :class="tag === selectedTag ? 'bg-brand-50 text-brand-700 border-brand-200' : 'bg-white text-gray-700 border-gray-200 hover:border-brand-200 hover:text-brand-600'"
          @click="selectedTag = tag"
        >
          {{ tag }}
        </button>
      </div>

      <div class="grid gap-6 grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
        <ProductCard
          v-for="product in filteredPB"
          :key="product.id"
          :product="product"
          label="주간 특가"
          best-label="BEST"
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

type PBProduct = Product & { pbTag: string; badges: string[]; isWeekly?: boolean }

const pbTags = ['전체', '번들', '베이커리', '키친', '건강', '주간 특가']
const selectedTag = ref('전체')

const selfProducts = ref<PBProduct[]>([
  {
    ...createMockProduct({
      id: 201,
      slug: 'pb-salad',
      name: 'PB 샐러드 밀박스',
      price: 9900,
      category_name: '간편식',
      main_image: 'https://images.unsplash.com/photo-1552332386-f8dd00dc2f85',
      review_count: 142,
      average_rating: 4.7
    }),
    pbTag: '번들',
    badges: ['2~3인분', '드레싱 포함'],
    isWeekly: true
  },
  {
    ...createMockProduct({
      id: 202,
      slug: 'pb-bread',
      name: '천연발효 브레드 3종',
      price: 12900,
      category_name: '베이커리',
      main_image: 'https://images.unsplash.com/photo-1512058564366-18510be2db19',
      review_count: 88,
      average_rating: 4.6
    }),
    pbTag: '베이커리',
    badges: ['무설탕', '당일 생산'],
    isWeekly: false
  },
  {
    ...createMockProduct({
      id: 203,
      slug: 'pb-kimchi',
      name: '직접 담근 포기김치',
      price: 14900,
      category_name: '반찬',
      main_image: 'https://images.unsplash.com/photo-1592910459359-911943b6aa56',
      review_count: 71,
      average_rating: 4.8
    }),
    pbTag: '키친',
    badges: ['냉장', '김장 레시피'],
    isWeekly: true
  },
  {
    ...createMockProduct({
      id: 204,
      slug: 'pb-protein',
      name: '단백질 쉐이크 팩',
      price: 8900,
      category_name: '건강',
      main_image: 'https://images.unsplash.com/photo-1467003909585-2f8a72700288',
      review_count: 54,
      average_rating: 4.5
    }),
    pbTag: '건강',
    badges: ['단백질 20g', '상온'],
    isWeekly: false
  },
  {
    ...createMockProduct({
      id: 205,
      slug: 'pb-soup',
      name: '한우 사골 곰탕',
      price: 10900,
      category_name: '간편식',
      main_image: 'https://images.unsplash.com/photo-1604908177453-7462950a6a0d',
      review_count: 63,
      average_rating: 4.7
    }),
    pbTag: '키친',
    badges: ['냉동', '6팩'],
    isWeekly: false
  },
  {
    ...createMockProduct({
      id: 206,
      slug: 'pb-cookie',
      name: '씨앗 가득 쿠키',
      price: 6900,
      category_name: '베이커리',
      main_image: 'https://images.unsplash.com/photo-1499636136210-6f4ee915583e',
      review_count: 47,
      average_rating: 4.4
    }),
    pbTag: '베이커리',
    badges: ['글루텐 프리', '비건'],
    isWeekly: true
  }
])

const selectAll = () => {
  selectedTag.value = '전체'
}

const selectWeekly = () => {
  selectedTag.value = '주간 특가'
}

const filteredPB = computed(() => {
  if (selectedTag.value === '전체') return selfProducts.value
  if (selectedTag.value === '주간 특가') return selfProducts.value.filter((p) => p.isWeekly)
  return selfProducts.value.filter((p) => p.pbTag === selectedTag.value)
})
</script>
