<template>
  <main class="bg-gray-50 min-h-screen pt-28 pb-16">
    <section class="max-w-6xl mx-auto px-4 space-y-8">
      <header class="space-y-4">
        <p class="text-sm font-semibold text-brand-600">신상품</p>
        <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div class="space-y-2">
            <h1 class="text-3xl font-display font-bold text-gray-900">따끈한 신상, 막 들어왔어요</h1>
            <p class="text-gray-600">최근 입고된 상품을 빠르게 둘러보세요.</p>
          </div>
          <label class="inline-flex items-center gap-2 text-sm text-gray-700">
            <input type="checkbox" class="rounded" v-model="only7Days" />
            최근 7일만 보기
          </label>
        </div>
      </header>

      <div class="relative overflow-hidden rounded-2xl bg-gradient-to-r from-[#5a1f8c] via-[#7a4bd8] to-[#7ee0c0] text-white p-8 shadow-lg">
        <div class="absolute inset-0 bg-black/10"></div>
        <div class="relative max-w-xl space-y-2">
          <p class="text-sm font-semibold uppercase tracking-widest text-white/85">New Arrival</p>
          <h2 class="text-3xl font-display font-bold">이번주도 새롭게 더 Fresh 하게</h2>
        </div>
        <div class="absolute -right-10 -bottom-10 w-48 h-48 bg-white/20 rounded-full blur-3xl"></div>
      </div>

      <div class="grid gap-6 grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
        <ProductCard
          v-for="product in filteredNewProducts"
          :key="product.id"
          :product="product"
          label="NEW"
          :best-label="product.isBest ? 'BEST' : ''"
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

type NewProduct = Product & {
  daysSinceRelease: number
  isBest?: boolean
}

const only7Days = ref(false)

const newProducts = ref<NewProduct[]>([
  {
    ...createMockProduct({
      id: 101,
      slug: 'vegan-salad',
      name: '비건 샐러드 박스',
      price: 11900,
      category_name: '신선',
      main_image: 'https://images.unsplash.com/photo-1552332386-f8dd00dc2f85',
      average_rating: 4.7,
      review_count: 32
    }),
    daysSinceRelease: 2,
    isBest: true
  },
  {
    ...createMockProduct({
      id: 102,
      slug: 'cold-noodle',
      name: '동치미 물냉면 킷',
      price: 12900,
      category_name: '간편식',
      main_image: 'https://images.unsplash.com/photo-1625944525734-1846fc03e12d',
      average_rating: 4.6,
      review_count: 21
    }),
    daysSinceRelease: 3
  },
  {
    ...createMockProduct({
      id: 103,
      slug: 'fruit-bundle',
      name: '제철 과일 번들',
      price: 15900,
      category_name: '신선',
      main_image: 'https://images.unsplash.com/photo-1506801310323-534be5e7f004',
      average_rating: 4.9,
      review_count: 54
    }),
    daysSinceRelease: 1,
    isBest: true
  },
  {
    ...createMockProduct({
      id: 104,
      slug: 'granola-bar',
      name: '통곡물 그래놀라 바',
      price: 6900,
      category_name: '간식',
      main_image: 'https://images.unsplash.com/photo-1499636136210-6f4ee915583e',
      average_rating: 4.5,
      review_count: 18
    }),
    daysSinceRelease: 6
  },
  {
    ...createMockProduct({
      id: 105,
      slug: 'cold-pressed',
      name: '콜드프레스 주스 4종',
      price: 13900,
      category_name: '음료',
      main_image: 'https://images.unsplash.com/photo-1467003909585-2f8a72700288',
      average_rating: 4.4,
      review_count: 12
    }),
    daysSinceRelease: 8
  },
  {
    ...createMockProduct({
      id: 106,
      slug: 'fresh-seafood',
      name: '완도 활전복 1kg',
      price: 32900,
      category_name: '신선',
      main_image: 'https://images.unsplash.com/photo-1504674900247-0877df9cc836',
      average_rating: 4.8,
      review_count: 41
    }),
    daysSinceRelease: 5,
    isBest: true
  }
])

const filteredNewProducts = computed(() => {
  const filtered = only7Days.value
    ? newProducts.value.filter((p) => p.daysSinceRelease <= 7)
    : newProducts.value
  return [...filtered].sort((a, b) => a.daysSinceRelease - b.daysSinceRelease)
})
</script>
