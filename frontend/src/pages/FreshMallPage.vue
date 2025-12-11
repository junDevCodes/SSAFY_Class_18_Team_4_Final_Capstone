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

        <div class="space-y-3">
          <div class="flex flex-wrap gap-2">
            <button v-for="opt in deliveryOptions" :key="opt" class="chip" :class="chipDelivery(opt)" @click="toggleDelivery(opt)">
              {{ opt }}
            </button>
            <button v-for="opt in tempOptions" :key="opt" class="chip" :class="chipTemp(opt)" @click="toggleTemp(opt)">
              {{ opt }}
            </button>
            <button v-for="opt in originOptions" :key="opt" class="chip" :class="chipOrigin(opt)" @click="toggleOrigin(opt)">
              {{ opt }}
            </button>
            <button v-for="opt in sellerTypeOptions" :key="opt" class="chip" :class="chipSellerType(opt)" @click="toggleSellerType(opt)">
              {{ opt }}
            </button>
          </div>
        </div>
      </header>

      <section class="space-y-4">
        <div class="flex items-center justify-between">
          <h2 class="text-xl font-bold text-gray-900">셀러 스토리</h2>
          <button class="text-sm font-semibold text-brand-700 hover:text-brand-800">모두 보기</button>
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

      <div class="grid gap-6 grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
        <ProductCard
          v-for="product in filteredFreshProducts"
          :key="product.id"
          :product="product"
          label="FRESH"
          :meta="product.deliveryTag"
          :badges="[product.tempTag, product.originTag].filter((t): t is string => Boolean(t))"
          :seller="product.seller"
        />
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, ref, type Ref } from 'vue'
import type { Product } from '@/types/product'
import ProductCard from '@/components/ui/ProductCard.vue'
import { createMockProduct, type SellerBadge } from './mallMock'

type FreshProduct = Product & {
  deliveryTag?: string
  tempTag?: string
  originTag?: string
  seller?: SellerBadge
  sellerType?: string
  distanceKm?: number
}

const sortOptions = ['신규 셀러', '판매순', '리뷰순', '거리순']
const deliveryOptions = ['새벽배송', '당일배송', '택배']
const tempOptions = ['냉장', '냉동', '상온']
const originOptions = ['국내산', '수입산']
const sellerTypeOptions = ['로컬 농가', '수산 셀러', '정육 셀러', '수제 식품']

const sortOption = ref('신규 셀러')
const deliveryFilters = ref<string[]>([])
const tempFilters = ref<string[]>([])
const originFilters = ref<string[]>([])
const sellerTypeFilters = ref<string[]>([])

const sellerStories = ref([
  { id: 's1', name: '완주 로컬 농가', desc: '새벽에 수확한 채소를 바로 포장합니다.', cover: 'https://images.unsplash.com/photo-1582719478248-54e9f2b2d1c5' },
  { id: 's2', name: '통영 수산 셀러', desc: '산지 직송 해산물을 빠르게 배송.', cover: 'https://images.unsplash.com/photo-1526379879527-8559ecfcaec0' },
  { id: 's3', name: '정육 셀렉션', desc: '초신선 숙성 한우를 소량으로 준비.', cover: 'https://images.unsplash.com/photo-1604908177453-7462950a6a0d' },
  { id: 's4', name: '비건 수제식품', desc: '첨가물 없이 수제로 만드는 비건 간식.', cover: 'https://images.unsplash.com/photo-1499636136210-6f4ee915583e' }
])

const freshProducts = ref<FreshProduct[]>([
  {
    ...createMockProduct({ id: 301, slug: 'lettuce', name: '아침 수확 상추', price: 4900, category_name: '신선', main_image: 'https://images.unsplash.com/photo-1505253758473-96b7015fcd40', review_count: 52, average_rating: 4.8 }),
    deliveryTag: '새벽배송',
    tempTag: '냉장',
    originTag: '국내산',
    sellerType: '로컬 농가',
    distanceKm: 6,
    seller: { name: '로컬 농가 김씨', avatar: 'https://images.unsplash.com/photo-1527980965255-d3b416303d12', rating: 4.8, type: '로컬 농가' }
  },
  {
    ...createMockProduct({ id: 302, slug: 'salmon', name: '노르웨이 연어 필렛', price: 18900, category_name: '수산', main_image: 'https://images.unsplash.com/photo-1467003909585-2f8a72700288', review_count: 71, average_rating: 4.7 }),
    deliveryTag: '당일배송',
    tempTag: '냉장',
    originTag: '수입산',
    sellerType: '수산 셀러',
    distanceKm: 18,
    seller: { name: '해류 셀러', avatar: 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e', rating: 4.6, type: '수산 셀러' }
  },
  {
    ...createMockProduct({ id: 303, slug: 'pork-belly', name: '도톰한 삼겹살 600g', price: 15900, category_name: '정육', main_image: 'https://images.unsplash.com/photo-1604908177453-7462950a6a0d', review_count: 89, average_rating: 4.5 }),
    deliveryTag: '택배',
    tempTag: '냉동',
    originTag: '국내산',
    sellerType: '정육 셀러',
    distanceKm: 24,
    seller: { name: '한우길 정육', avatar: 'https://images.unsplash.com/photo-1523475472560-d2df97ec485c', rating: 4.7, type: '정육 셀러' }
  },
  {
    ...createMockProduct({ id: 304, slug: 'kimchi', name: '수제 백김치 1kg', price: 11900, category_name: '반찬', main_image: 'https://images.unsplash.com/photo-1592910459359-911943b6aa56', review_count: 38, average_rating: 4.6 }),
    deliveryTag: '당일배송',
    tempTag: '냉장',
    originTag: '국내산',
    sellerType: '수제 식품',
    distanceKm: 8,
    seller: { name: '어머님 수제방', avatar: 'https://images.unsplash.com/photo-1521572267360-ee0c2909d518', rating: 4.9, type: '수제 식품' }
  },
  {
    ...createMockProduct({ id: 305, slug: 'frozen-dumpling', name: '새우 가득 만두', price: 9900, category_name: '간편식', main_image: 'https://images.unsplash.com/photo-1504674900247-0877df9cc836', review_count: 64, average_rating: 4.4 }),
    deliveryTag: '택배',
    tempTag: '냉동',
    originTag: '국내산',
    sellerType: '수제 식품',
    distanceKm: 12,
    seller: { name: '만두 공방', avatar: 'https://images.unsplash.com/photo-1523475472560-d2df97ec485c', rating: 4.5, type: '수제 식품' }
  },
  {
    ...createMockProduct({ id: 306, slug: 'fruit-box', name: '오늘 수확 과일 박스', price: 13900, category_name: '신선', main_image: 'https://images.unsplash.com/photo-1506801310323-534be5e7f004', review_count: 57, average_rating: 4.8 }),
    deliveryTag: '새벽배송',
    tempTag: '상온',
    originTag: '국내산',
    sellerType: '로컬 농가',
    distanceKm: 5,
    seller: { name: '산들 농원', avatar: 'https://images.unsplash.com/photo-1527980965255-d3b416303d12', rating: 4.9, type: '로컬 농가' }
  }
])

const toggleRef = (listRef: Ref<string[]>, value: string) => {
  const next = new Set(listRef.value)
  if (next.has(value)) {
    next.delete(value)
  } else {
    next.add(value)
  }
  listRef.value = Array.from(next)
}

const chipRef = (listRef: Ref<string[]>, value: string) => {
  const isActive = listRef.value.includes(value)
  return isActive
    ? 'bg-brand-50 text-brand-700 border-brand-200'
    : 'bg-white text-gray-700 border-gray-200 hover:border-brand-200 hover:text-brand-600'
}

const toggleDelivery = (value: string) => toggleRef(deliveryFilters, value)
const toggleTemp = (value: string) => toggleRef(tempFilters, value)
const toggleOrigin = (value: string) => toggleRef(originFilters, value)
const toggleSellerType = (value: string) => toggleRef(sellerTypeFilters, value)

const chipDelivery = (value: string) => chipRef(deliveryFilters, value)
const chipTemp = (value: string) => chipRef(tempFilters, value)
const chipOrigin = (value: string) => chipRef(originFilters, value)
const chipSellerType = (value: string) => chipRef(sellerTypeFilters, value)

const filteredFreshProducts = computed(() => {
  const matchesFilter = (value: string | undefined, filters: string[]) =>
    filters.length === 0 || (value && filters.includes(value))

  const filtered = freshProducts.value.filter(
    (p) =>
      matchesFilter(p.deliveryTag, deliveryFilters.value) &&
      matchesFilter(p.tempTag, tempFilters.value) &&
      matchesFilter(p.originTag, originFilters.value) &&
      matchesFilter(p.sellerType, sellerTypeFilters.value)
  )

  const sorted = [...filtered]
  if (sortOption.value === '판매순') {
    return sorted.sort((a, b) => (b.view_count || 0) - (a.view_count || 0))
  }
  if (sortOption.value === '리뷰순') {
    return sorted.sort((a, b) => (b.review_count || 0) - (a.review_count || 0))
  }
  if (sortOption.value === '거리순') {
    return sorted.sort((a, b) => (a.distanceKm || 0) - (b.distanceKm || 0))
  }
  return sorted
})
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
