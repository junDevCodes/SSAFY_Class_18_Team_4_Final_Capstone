<template>
  <section class="py-20 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
    <div class="flex flex-col md:flex-row justify-between items-start md:items-end mb-10 gap-4">
      <div>
        <h3 class="text-3xl font-display font-bold text-gray-900 mb-3">
          검색 결과
        </h3>
        <p class="text-gray-500">
          <span v-if="searchText">키워드: "{{ searchText }}"</span>
          <span v-if="categoryName" class="ml-2">카테고리: {{ categoryName }}</span>
          <span v-if="!searchText && !categoryName">전체 상품 목록</span>
        </p>
      </div>
      <div class="flex items-center gap-3">
        <label class="text-sm text-gray-600">정렬</label>
        <select class="border rounded-md text-sm px-2 py-1" v-model="sort" @change="applySort">
          <option value="">기본순</option>
          <option value="price_asc">가격 낮은순</option>
          <option value="price_desc">가격 높은순</option>
          <option value="discount_desc">할인율 높은순</option>
        </select>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-4 gap-10">
      <!-- Filters -->
      <aside class="hidden lg:block">
        <div class="sticky top-24 space-y-6">
          <div>
            <h4 class="text-sm font-bold text-gray-900 mb-3">카테고리</h4>
            <div class="max-h-72 overflow-auto pr-2 space-y-2">
              <button
                class="block w-full text-left text-sm px-2 py-1 rounded hover:bg-gray-50"
                :class="!categoryId ? 'text-brand-600 font-semibold' : 'text-gray-700'"
                @click="updateQuery({ category: undefined, page: 1 })"
              >
                전체
              </button>
              <button
                v-for="cat in productStore.categories"
                :key="cat.id"
                class="block w-full text-left text-sm px-2 py-1 rounded hover:bg-gray-50"
                :class="categoryId === cat.id ? 'text-brand-600 font-semibold' : 'text-gray-700'"
                @click="updateQuery({ category: cat.id, page: 1 })"
              >
                {{ cat.name === '과일' ? '과일/견과' : cat.name }}
              </button>
            </div>
          </div>
          <div class="border-t pt-4">
            <h4 class="text-sm font-bold text-gray-900 mb-3">필터</h4>
            <label class="flex items-center gap-2 text-sm text-gray-700">
              <input type="checkbox" class="rounded" v-model="bestOnly" @change="applyBest" />
              베스트만 보기
            </label>
            <label class="flex items-center gap-2 text-sm text-gray-700 mt-2">
              <input type="checkbox" class="rounded" v-model="discountOnly" @change="applyDiscount" />
              할인 상품만
            </label>
          </div>
        </div>
      </aside>

      <!-- Results -->
      <div class="lg:col-span-3">
        <div v-if="productStore.loading" class="flex justify-center items-center py-20">
          <div class="text-gray-500">로딩 중...</div>
        </div>

        <div v-else-if="productStore.error" class="flex justify-center items-center py-20">
          <div class="text-red-500">{{ productStore.error }}</div>
        </div>

        <div v-else>
          <div class="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-x-6 gap-y-12">
            <ProductCard
              v-for="product in displayedProducts"
              :key="product.id"
              :product="product"
            />
          </div>

          <!-- Pagination -->
          <div class="mt-10 flex items-center justify-center gap-2">
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
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useProductStore } from '@/stores/products'
import ProductCard from '@/components/ui/ProductCard.vue'

const route = useRoute()
const router = useRouter()
const productStore = useProductStore()

const searchText = computed(() => (route.query.q as string) || '')
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

const pageSize = 24
const totalCount = ref(0)
const totalPages = computed(() => Math.max(1, Math.ceil(totalCount.value / pageSize)))

const categoryName = computed(() => {
  if (!categoryId.value) return ''
  const cat = productStore.categories.find(c => c.id === categoryId.value)
  return cat ? (cat.name === '과일' ? '과일/견과' : cat.name) : ''
})

// Filters
const bestOnly = ref(route.query.best === '1' || route.query.best === 'true')
const discountOnly = ref(route.query.discount === '1' || route.query.discount === 'true')
const sort = ref((route.query.sort as string) || '')

const fetchResults = async () => {
  await ensureCategories()
  // v2.1: is_best 필터 대신 quality_score로 베스트 상품 필터링 (프론트에서 처리)
  const res = await productStore.fetchProducts({
    search: searchText.value || undefined,
    category: categoryId.value,
    page: currentPage.value,
    page_size: pageSize,
  })
  totalCount.value = res?.count || 0
}

const ensureCategories = async () => {
  if (productStore.categories.length === 0) {
    try {
      await productStore.fetchCategories()
    } catch {
      // ignore
    }
  }
}

onMounted(fetchResults)

watch(
  () => route.query,
  () => {
    bestOnly.value = route.query.best === '1' || route.query.best === 'true'
    discountOnly.value = route.query.discount === '1' || route.query.discount === 'true'
    sort.value = (route.query.sort as string) || ''
    fetchResults()
  }
)

// Derived results with client-side filters/sort
// v2.1: discount 필드 대신 original_price와 price로 할인율 계산
const calculateDiscountRate = (p: { price: number; original_price: number | null }) => {
  if (!p.original_price || p.original_price <= p.price) return 0
  return Math.round(((p.original_price - p.price) / p.original_price) * 100)
}

const displayedProducts = computed(() => {
  let list = [...productStore.products]
  // v2.1: bestOnly 필터는 quality_score 80 이상인 상품만 표시
  if (bestOnly.value) {
    list = list.filter(p => p.quality_score >= 80)
  }
  // v2.1: discountOnly 필터는 original_price가 있고 price보다 큰 상품만 표시
  if (discountOnly.value) {
    list = list.filter(p => calculateDiscountRate(p) > 0)
  }
  if (sort.value === 'price_asc') {
    list.sort((a, b) => a.price - b.price)
  } else if (sort.value === 'price_desc') {
    list.sort((a, b) => b.price - a.price)
  } else if (sort.value === 'discount_desc') {
    list.sort((a, b) => calculateDiscountRate(b) - calculateDiscountRate(a))
  }
  return list
})

// Pagination helpers
const pageButtons = computed(() => {
  const maxButtons = 5
  const half = Math.floor(maxButtons / 2)
  let start = Math.max(1, currentPage.value - half)
  let end = Math.min(totalPages.value, start + maxButtons - 1)
  if (end - start + 1 < maxButtons) {
    start = Math.max(1, end - maxButtons + 1)
  }
  const arr: number[] = []
  for (let i = start; i <= end; i++) arr.push(i)
  return arr
})

const goToPage = (page: number) => {
  updateQuery({ page })
}

const applyBest = () => {
  updateQuery({ best: bestOnly.value ? 1 : undefined, page: 1 })
}

const applyDiscount = () => {
  updateQuery({ discount: discountOnly.value ? 1 : undefined, page: 1 })
}

const applySort = () => {
  updateQuery({ sort: sort.value || undefined })
}

type QueryUpdate = {
  page?: number
  category?: number | undefined
  best?: number | undefined
  discount?: number | undefined
  sort?: string | undefined
}

const updateQuery = (update: QueryUpdate) => {
  const next = {
    q: searchText.value || undefined,
    category: update.category !== undefined ? update.category : categoryId.value,
    page: update.page ?? currentPage.value,
    best: update.best !== undefined ? update.best : (bestOnly.value ? 1 : undefined),
    discount: update.discount !== undefined ? update.discount : (discountOnly.value ? 1 : undefined),
    sort: update.sort !== undefined ? update.sort : (sort.value || undefined),
  } as Record<string, string | number | undefined>

  router.push({ name: 'search', query: next })
}
</script>


