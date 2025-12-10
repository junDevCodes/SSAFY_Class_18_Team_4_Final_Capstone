<template>
  <main class="bg-gray-50 min-h-screen">
    <section class="bg-gradient-to-r from-indigo-950 via-purple-900 to-fuchsia-800 text-white">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 space-y-3">
        <p class="text-xs uppercase tracking-[0.18em] text-white/70">All Products</p>
        <h1 class="text-4xl font-display font-bold">모든 상품 둘러보기</h1>
        <p class="text-white/80">카테고리, 할인, 정렬 필터로 원하는 상품을 빠르게 찾아보세요.</p>
      </div>
    </section>

    <section class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 grid grid-cols-1 lg:grid-cols-[260px_1fr] gap-10">
      <!-- Filters -->
      <aside class="lg:sticky lg:top-24 space-y-6 bg-white border border-gray-100 rounded-xl shadow-sm p-5">
        <div>
          <div class="flex items-center justify-between mb-3">
            <h2 class="text-sm font-bold text-gray-900">카테고리</h2>
            <button
              class="text-xs text-gray-500 hover:text-brand-600"
              @click="updateQuery({ category: undefined, page: 1 })"
            >
              전체
            </button>
          </div>
          <div class="space-y-2 max-h-72 overflow-auto pr-1">
            <button
              v-for="cat in productStore.categories"
              :key="cat.id"
              class="w-full text-left text-sm px-2 py-1 rounded hover:bg-gray-50"
              :class="categoryId === cat.id ? 'text-brand-600 font-semibold bg-brand-50/60' : 'text-gray-700'"
              @click="updateQuery({ category: cat.id, page: 1 })"
            >
              {{ cat.name }}
            </button>
          </div>
        </div>

        <div class="border-t pt-4 space-y-3">
          <label class="flex items-center gap-2 text-sm text-gray-800">
            <input type="checkbox" class="rounded" v-model="bestOnly" @change="applyBest" />
            베스트만 보기
          </label>
          <label class="flex items-center gap-2 text-sm text-gray-800">
            <input type="checkbox" class="rounded" v-model="saleOnly" @change="applySale" />
            할인중만 보기
          </label>
        </div>
      </aside>

      <!-- Content -->
      <div>
        <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
          <div>
            <p class="text-xs text-gray-500 uppercase tracking-wide">Total</p>
            <h2 class="text-2xl font-bold text-gray-900">{{ totalCount }}개 상품</h2>
          </div>
          <div class="flex items-center gap-3">
            <label class="text-sm text-gray-600">정렬</label>
            <select class="border rounded-md text-sm px-3 py-2" v-model="sort" @change="applySort">
              <option value="recent">신상품순</option>
              <option value="price_asc">낮은 가격순</option>
              <option value="price_desc">높은 가격순</option>
              <option value="popular">인기순</option>
            </select>
          </div>
        </div>

        <div v-if="productStore.loading" class="flex justify-center items-center py-20 text-gray-500">
          로딩 중...
        </div>

        <div v-else-if="productStore.error" class="flex justify-center items-center py-20 text-red-500">
          {{ productStore.error }}
        </div>

        <div v-else class="space-y-10">
          <div class="grid grid-cols-2 lg:grid-cols-4 gap-x-6 gap-y-12">
            <ProductCard
              v-for="product in productStore.products"
              :key="product.id"
              :product="product"
            />
          </div>

          <div class="flex items-center justify-center gap-2">
            <button
              class="px-3 py-2 text-sm rounded border"
              :class="currentPage > 1 ? 'text-gray-700 hover:bg-gray-50' : 'text-gray-300 cursor-not-allowed'"
              :disabled="currentPage <= 1"
              @click="goToPage(currentPage - 1)"
            >
              이전
            </button>

            <button
              v-for="p in pageButtons"
              :key="p"
              class="w-9 h-9 rounded text-sm"
              :class="p === currentPage ? 'bg-gray-900 text-white' : 'text-gray-700 border hover:bg-gray-50'"
              @click="goToPage(p)"
            >
              {{ p }}
            </button>

            <button
              class="px-3 py-2 text-sm rounded border"
              :class="currentPage < totalPages ? 'text-gray-700 hover:bg-gray-50' : 'text-gray-300 cursor-not-allowed'"
              :disabled="currentPage >= totalPages"
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
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import ProductCard from '@/components/ui/ProductCard.vue'
import { useProductStore } from '@/stores/products'

const route = useRoute()
const router = useRouter()
const productStore = useProductStore()

const pageSize = 24
const totalCount = ref(0)
const totalPages = computed(() => Math.max(1, Math.ceil(totalCount.value / pageSize)))

const categoryId = computed(() => {
  const raw = route.query.category
  if (!raw) return undefined
  const parsed = parseInt(String(raw), 10)
  return Number.isFinite(parsed) ? parsed : undefined
})

const currentPage = computed(() => {
  const raw = route.query.page
  const parsed = parseInt(String(raw || '1'), 10)
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 1
})

const sort = ref((route.query.sort as string) || 'recent')
const bestOnly = ref(route.query.best === '1' || route.query.best === 'true')
const saleOnly = ref(route.query.sale === '1' || route.query.sale === 'true')

const mapSort = (value: string): string | undefined => {
  switch (value) {
    case 'price_asc':
      return 'price'
    case 'price_desc':
      return '-price'
    case 'popular':
      return '-quality_score'
    default:
      return '-created_at'
  }
}

const ensureCategories = async () => {
  if (productStore.categories.length === 0) {
    try {
      await productStore.fetchCategories()
    } catch {
      // ignore: 카테고리 로드 실패 시에도 상품 목록은 표시
    }
  }
}

const fetchAll = async () => {
  await ensureCategories()
  const res = await productStore.fetchProducts({
    page: currentPage.value,
    page_size: pageSize,
    category: categoryId.value,
    is_best: bestOnly.value || undefined,
    is_on_sale: saleOnly.value || undefined,
    ordering: mapSort(sort.value),
  })
  totalCount.value = res?.count || 0
}

onMounted(fetchAll)

watch(
  () => route.query,
  () => {
    bestOnly.value = route.query.best === '1' || route.query.best === 'true'
    saleOnly.value = route.query.sale === '1' || route.query.sale === 'true'
    sort.value = (route.query.sort as string) || 'recent'
    fetchAll()
  }
)

const pageButtons = computed(() => {
  const maxButtons = 5
  const half = Math.floor(maxButtons / 2)
  let start = Math.max(1, currentPage.value - half)
  let end = Math.min(totalPages.value, start + maxButtons - 1)
  if (end - start + 1 < maxButtons) start = Math.max(1, end - maxButtons + 1)
  const arr: number[] = []
  for (let i = start; i <= end; i++) arr.push(i)
  return arr
})

const goToPage = (page: number) => updateQuery({ page })
const applyBest = () => updateQuery({ best: bestOnly.value ? 1 : undefined, page: 1 })
const applySale = () => updateQuery({ sale: saleOnly.value ? 1 : undefined, page: 1 })
const applySort = () => updateQuery({ sort: sort.value })

type QueryUpdate = {
  page?: number
  category?: number | undefined
  best?: number | undefined
  sale?: number | undefined
  sort?: string | undefined
}

const updateQuery = (update: QueryUpdate) => {
  router.push({
    name: 'products',
    query: {
      category: update.category !== undefined ? update.category : categoryId.value,
      page: update.page ?? currentPage.value,
      best: update.best !== undefined ? update.best : (bestOnly.value ? 1 : undefined),
      sale: update.sale !== undefined ? update.sale : (saleOnly.value ? 1 : undefined),
      sort: update.sort !== undefined ? update.sort : sort.value,
    },
  })
}
</script>
