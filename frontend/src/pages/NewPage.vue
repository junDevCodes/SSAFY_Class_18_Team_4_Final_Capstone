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

      <div v-if="loading" class="flex items-center justify-center h-40 rounded-xl bg-white shadow">
        <p class="text-gray-600">???? ???? ????...</p>
      </div>
      <div v-else-if="pagedProducts.length" class="grid gap-6 md:gap-8 grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
        <ProductCard
          v-for="product in pagedProducts"
          :key="product.id"
          :product="product"
          label="NEW"
        />
      </div>
      <div v-else class="flex items-center justify-center h-40 rounded-xl bg-white shadow">
        <p class="text-gray-600">?? 7? ??? ???. ??? ??? ???.</p>
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
import { computed, onMounted, ref, watch } from 'vue'
import type { NewProductSummary, Product } from '@/types/product'
import ProductCard from '@/components/ui/ProductCard.vue'
import { productsAPI } from '@/services/api'
import { createMockProduct } from './mallMock'

const pageSize = 8
const only7Days = ref(false)
const currentPage = ref(1)
const loading = ref(false)
const products = ref<Product[]>([])

const mapNewProduct = (item: NewProductSummary): Product => {
  return createMockProduct({
    id: item.id,
    slug: item.slug,
    name: item.name,
    price: item.price,
    original_price: item.original_price ?? null,
    main_image: item.main_image ?? null,
    category_name: item.category_name ?? null,
    created_at: item.created_at,
  })
}

const fetchNewProducts = async () => {
  loading.value = true
  try {
    const { data } = await productsAPI.getNewProductList()
    products.value = (data.results ?? []).map(mapNewProduct)
  } catch (err) {
    console.error('Failed to load new products:', err)
    products.value = []
  } finally {
    loading.value = false
  }
}

const isWithin7Days = (createdAt: string) => {
  const created = Date.parse(createdAt)
  if (Number.isNaN(created)) return false
  const sevenDaysMs = 7 * 24 * 60 * 60 * 1000
  return Date.now() - created <= sevenDaysMs
}

const sortedProducts = computed(() => {
  const base = only7Days.value
    ? products.value.filter((product) => isWithin7Days(product.created_at))
    : products.value

  return [...base].sort((a, b) => {
    const aTime = Date.parse(a.created_at)
    const bTime = Date.parse(b.created_at)
    return (Number.isNaN(bTime) ? 0 : bTime) - (Number.isNaN(aTime) ? 0 : aTime)
  })
})

const totalPages = computed(() => Math.max(1, Math.ceil(sortedProducts.value.length / pageSize)))

const pagedProducts = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  return sortedProducts.value.slice(start, start + pageSize)
})

const goToPage = (page: number) => {
  if (page < 1 || page > totalPages.value) return
  currentPage.value = page
}

watch(only7Days, () => {
  currentPage.value = 1
})

watch(sortedProducts, () => {
  const maxPage = Math.max(1, Math.ceil(sortedProducts.value.length / pageSize))
  if (currentPage.value > maxPage) {
    currentPage.value = maxPage
  }
})

onMounted(fetchNewProducts)
</script>

