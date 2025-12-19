<template>
  <main class="bg-gray-50 min-h-screen pt-28 pb-16">
    <section class="max-w-6xl mx-auto px-4 space-y-10">
      <header class="space-y-4">
        <p class="text-sm font-semibold text-brand-600">신상품</p>
        <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div class="space-y-2">
            <h1 class="text-3xl font-display font-bold text-gray-900">따끈한 신상, 막 들어왔어요</h1>
            <p class="text-gray-600">최근 입고된 상품을 빠르게 둘러보세요. 매주 다른 조합으로 준비했어요.</p>
          </div>
          <label class="inline-flex items-center gap-2 text-sm text-gray-700">
            <input
              type="checkbox"
              class="rounded border-gray-300 text-brand-600 focus:ring-brand-500"
              v-model="only7Days"
            />
            최근 7일만 보기
          </label>
        </div>
      </header>

      <div
        class="relative overflow-hidden rounded-2xl bg-gradient-to-r from-[#5a1f8c] via-[#7a4bd8] to-[#7ee0c0] text-white p-8 shadow-lg"
      >
        <div class="absolute inset-0 bg-black/10"></div>
        <div class="relative max-w-xl space-y-2">
          <p class="text-sm font-semibold uppercase tracking-widest text-white/85">New Arrival</p>
          <h2 class="text-3xl font-display font-bold">이번주도 새롭게 더 Fresh 하게</h2>
          <p class="text-white/85 text-sm">플래터, 샐러드, 밀키트까지 바로 즐길 신선한 구성을 모았어요.</p>
        </div>
        <div class="absolute -right-10 -bottom-10 w-48 h-48 bg-white/20 rounded-full blur-3xl"></div>
      </div>

      <div v-if="pagedProducts.length" class="grid gap-6 md:gap-8 grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
        <ProductCard
          v-for="product in pagedProducts"
          :key="product.id"
          :product="product"
          label="NEW"
          :best-label="product.isBest ? 'BEST' : ''"
        />
      </div>
      <div v-else class="flex items-center justify-center h-40 rounded-xl bg-white shadow">
        <p class="text-gray-600">최근 7일 상품이 없어요. 필터를 해제해 보세요.</p>
      </div>

      <div v-if="totalPages > 1" class="flex items-center justify-center gap-2 pt-4">
        <button
          class="px-4 py-2 rounded-lg bg-white shadow text-sm font-semibold text-gray-700 hover:bg-gray-100 disabled:opacity-50"
          :disabled="currentPage === 1"
          @click="goToPage(currentPage - 1)"
        >
          이전
        </button>
        <button
          v-for="page in totalPages"
          :key="page"
          class="w-10 h-10 rounded-lg text-sm font-semibold"
          :class="page === currentPage ? 'bg-brand-600 text-white shadow' : 'bg-white text-gray-700 hover:bg-gray-100 shadow'"
          @click="goToPage(page)"
        >
          {{ page }}
        </button>
        <button
          class="px-4 py-2 rounded-lg bg-white shadow text-sm font-semibold text-gray-700 hover:bg-gray-100 disabled:opacity-50"
          :disabled="currentPage === totalPages"
          @click="goToPage(currentPage + 1)"
        >
          다음
        </button>
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { Product } from '@/types/product'
import ProductCard from '@/components/ui/ProductCard.vue'
import { createMockProduct } from './mallMock'

type NewProduct = Product & {
  daysSinceRelease: number
  isBest?: boolean
}

type ProductSeed = {
  slug: string
  name: string
  price: number
  category_name: string
  main_image: string
  average_rating: number
  review_count: number
  isBest?: boolean
}

const pageSize = 8
const only7Days = ref(false)
const currentPage = ref(1)

const releasePattern = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 14]

const productSeeds: ProductSeed[] = [
  {
    slug: 'seasonal-fruit-box',
    name: '계절 과일 번들',
    price: 15900,
    category_name: '신선',
    main_image: 'https://images.unsplash.com/photo-1506801310323-534be5e7f004',
    average_rating: 4.7,
    review_count: 52,
    isBest: true
  },
  {
    slug: 'vegan-salad-box',
    name: '비건 샐러드 박스',
    price: 11900,
    category_name: '샐러드',
    main_image: 'https://images.unsplash.com/photo-1552332386-f8dd00dc2f85',
    average_rating: 4.6,
    review_count: 34
  },
  {
    slug: 'dongchimi-noodle-kit',
    name: '동치미 물냉면 킷',
    price: 12900,
    category_name: '간편식',
    main_image: 'https://images.unsplash.com/photo-1625944525734-1846fc03e12d',
    average_rating: 4.5,
    review_count: 26
  },
  {
    slug: 'fresh-abalone',
    name: '완도 활전복 1kg',
    price: 32900,
    category_name: '신선',
    main_image: 'https://images.unsplash.com/photo-1504674900247-0877df9cc836',
    average_rating: 4.8,
    review_count: 41,
    isBest: true
  },
  {
    slug: 'cold-pressed-juice',
    name: '콜드프레스 주스 4팩',
    price: 13900,
    category_name: '음료',
    main_image: 'https://images.unsplash.com/photo-1467003909585-2f8a72700288',
    average_rating: 4.4,
    review_count: 19
  },
  {
    slug: 'chef-steak-kit',
    name: '셰프 스테이크 밀키트',
    price: 19900,
    category_name: '간편식',
    main_image: 'https://images.unsplash.com/photo-1546069901-eacef0df6022',
    average_rating: 4.7,
    review_count: 28,
    isBest: true
  },
  {
    slug: 'grain-bowl',
    name: '그레인 보울 세트',
    price: 10900,
    category_name: '샐러드',
    main_image: 'https://images.unsplash.com/photo-1528697203043-733bfd8fddc5',
    average_rating: 4.3,
    review_count: 17
  },
  {
    slug: 'artisan-bread',
    name: '천연발효 브레드 3종',
    price: 9900,
    category_name: '베이커리',
    main_image: 'https://images.unsplash.com/photo-1481391032119-d89fee407e44',
    average_rating: 4.2,
    review_count: 22
  },
  {
    slug: 'single-origin-coffee',
    name: '싱글오리진 원두 200g',
    price: 8900,
    category_name: '커피/티',
    main_image: 'https://images.unsplash.com/photo-1509042239860-f550ce710b93',
    average_rating: 4.5,
    review_count: 35
  },
  {
    slug: 'dessert-box',
    name: '수제 디저트 박스',
    price: 15900,
    category_name: '디저트',
    main_image: 'https://images.unsplash.com/photo-1505253758473-96b7015fcd40',
    average_rating: 4.9,
    review_count: 48,
    isBest: true
  }
]

const newProducts = ref<NewProduct[]>(generateMockProducts())

function generateMockProducts(): NewProduct[] {
  return Array.from({ length: 40 }, (_, index) => {
    const seed = productSeeds[index % productSeeds.length]
    const daysSinceRelease = releasePattern[index % releasePattern.length]
    const createdAt = createCreatedAt(daysSinceRelease)
    const variation = index % 4
    const price = seed.price + variation * 500

    return {
      ...createMockProduct({
        id: 1000 + index,
        slug: `${seed.slug}-${index + 1}`,
        name: `${seed.name} ${index + 1}`,
        price,
        category_name: seed.category_name,
        main_image: `${seed.main_image}?auto=format&fit=crop&w=800&q=80`,
        original_price: price + 1200,
        created_at: createdAt,
        average_rating: parseFloat((seed.average_rating + variation * 0.1).toFixed(1)),
        review_count: seed.review_count + variation * 3,
        wishlist_count: 20 + (index % 9)
      }),
      daysSinceRelease,
      isBest: seed.isBest || index % 6 === 0
    }
  })
}

function createCreatedAt(daysAgo: number) {
  const date = new Date()
  date.setDate(date.getDate() - daysAgo)
  return date.toISOString()
}

const filteredNewProducts = computed(() => {
  const filtered = only7Days.value
    ? newProducts.value.filter((product) => product.daysSinceRelease <= 7)
    : newProducts.value
  return [...filtered].sort((a, b) => a.daysSinceRelease - b.daysSinceRelease || a.id - b.id)
})

const totalPages = computed(() => Math.max(1, Math.ceil(filteredNewProducts.value.length / pageSize)))

const pagedProducts = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  return filteredNewProducts.value.slice(start, start + pageSize)
})

const goToPage = (page: number) => {
  if (page < 1 || page > totalPages.value) return
  currentPage.value = page
}

watch(only7Days, () => {
  currentPage.value = 1
})

watch(filteredNewProducts, () => {
  const maxPage = Math.max(1, Math.ceil(filteredNewProducts.value.length / pageSize))
  if (currentPage.value > maxPage) {
    currentPage.value = maxPage
  }
})
</script>
