<template>
  <section class="bg-white border border-gray-100 rounded-xl shadow-sm">
    <div class="flex items-start justify-between px-4 pt-4">
      <div class="space-y-1">
        <p class="text-[11px] font-semibold text-brand-600 tracking-tight uppercase">상품 추천</p>
        <p class="text-sm text-gray-600">고객 취향을 바탕으로 골라봤어요</p>
      </div>
      <div class="flex items-center gap-2">
        <button
          type="button"
          :aria-label="'이전 추천 보기'"
          class="p-2 rounded-full border border-gray-200 text-gray-500 hover:text-gray-800 hover:border-gray-300 disabled:opacity-40 disabled:cursor-not-allowed transition-colors bg-white"
          :disabled="!hasPrev || loading"
          @click="goPrev"
        >
          <ChevronLeft :size="18" />
        </button>
        <button
          type="button"
          :aria-label="'다음 추천 보기'"
          class="p-2 rounded-full border border-gray-200 text-gray-500 hover:text-gray-800 hover:border-gray-300 disabled:opacity-40 disabled:cursor-not-allowed transition-colors bg-white"
          :disabled="!hasNext || loading"
          @click="goNext"
        >
          <ChevronRight :size="18" />
        </button>
      </div>
    </div>

    <div class="px-4 pb-4">
      <div v-if="loading" class="grid grid-cols-3 gap-3 mt-4">
        <div v-for="n in 3" :key="`skeleton-${n}`" class="h-[150px] rounded-lg bg-gray-100 border border-gray-200 animate-pulse" />
      </div>

      <div v-else-if="error" class="mt-4 flex items-center justify-between text-xs text-gray-500">
        <span>{{ error }}</span>
        <button type="button" class="text-brand-600 font-semibold hover:text-brand-500" @click="fetchRecommendations">
          다시 시도
        </button>
      </div>

      <div v-else-if="visibleItems.length === 0" class="mt-4 text-xs text-gray-400">
        추천 상품을 준비 중이에요.
      </div>

      <div v-else class="mt-4">
        <div class="grid grid-cols-3 gap-3">
          <article
            v-for="product in visibleItems"
            :key="product.id"
            class="group relative rounded-lg bg-gray-50 border border-gray-200 hover:border-brand-500 hover:shadow-md transition-all overflow-hidden cursor-pointer"
            role="button"
            tabindex="0"
            @click="goProduct(product)"
            @keydown.enter.prevent="goProduct(product)"
          >
            <div class="aspect-square overflow-hidden bg-white">
              <img
                :src="getProductImage(product)"
                :alt="product.name"
                loading="lazy"
                class="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
              />
            </div>
            <div class="p-2 space-y-2">
              <p class="text-[11px] text-gray-700 leading-snug line-clamp-2">{{ product.name }}</p>
              <div class="flex items-center justify-between">
                <span class="font-bold text-sm text-gray-900">{{ formatPrice(product.price) }}</span>
                <button
                  type="button"
                  class="w-8 h-8 inline-flex items-center justify-center rounded-full bg-white border border-gray-200 text-brand-600 hover:border-brand-500 hover:bg-brand-50 transition-colors"
                  :class="isAdding(product.id) ? 'opacity-60 cursor-not-allowed' : ''"
                  :disabled="isAdding(product.id)"
                  @click.stop="addItem(product)"
                >
                  <Plus :size="16" stroke-width="2.5" />
                </button>
              </div>
            </div>
          </article>
        </div>
        <div class="flex justify-center gap-1.5 mt-4">
          <span
            v-for="(_, idx) in chunks"
            :key="`dot-${idx}`"
            class="h-1.5 w-1.5 rounded-full"
            :class="idx === currentSlide ? 'bg-brand-600' : 'bg-gray-200'"
          />
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ChevronLeft, ChevronRight, Plus } from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { productsAPI } from '@/services/api'
import { useCartStore } from '@/stores/cart'
import { useUIStore } from '@/stores/ui'
import { formatPrice } from '@/utils/formatters'
import { getProductImage, type Product } from '@/types/product'

const props = defineProps<{
  limit?: number
}>()

const router = useRouter()
const cartStore = useCartStore()
const uiStore = useUIStore()

const loading = ref(false)
const addingIds = ref<string[]>([])
const error = ref<string | null>(null)
const recommendations = ref<Product[]>([])
const currentSlide = ref(0)
const groupSize = 3

const chunks = computed(() => {
  const source = recommendations.value
  const grouped: Product[][] = []
  for (let i = 0; i < source.length; i += groupSize) {
    grouped.push(source.slice(i, i + groupSize))
  }
  return grouped
})

const visibleItems = computed(() => {
  return chunks.value[currentSlide.value] ?? []
})

const hasPrev = computed(() => currentSlide.value > 0)
const hasNext = computed(() => currentSlide.value < chunks.value.length - 1)

const fetchRecommendations = async () => {
  loading.value = true
  error.value = null
  try {
    const { data } = await productsAPI.getBestProducts(props.limit ?? 9)
    recommendations.value = data.results || []
    currentSlide.value = 0
    if (recommendations.value.length === 0) {
      const fallback = await productsAPI.getFeaturedProducts(props.limit ?? 9)
      recommendations.value = fallback.data.results || []
    }
  } catch (err) {
    console.error('추천 상품 불러오기 실패:', err)
    error.value = '추천을 불러오지 못했어요.'
  } finally {
    loading.value = false
  }
}

const goNext = () => {
  if (hasNext.value) {
    currentSlide.value += 1
  }
}

const goPrev = () => {
  if (hasPrev.value) {
    currentSlide.value -= 1
  }
}

const goProduct = (product: Product) => {
  router.push({ name: 'product-detail', params: { slug: product.slug } })
}

const addItem = async (product: Product) => {
  const productId = product?.id
  if (!productId || product.price == null) {
    uiStore.showToast('상품 정보가 부족해 담지 못했어요.')
    return
  }

  const idKey = String(productId)
  if (addingIds.value.includes(idKey)) return
  addingIds.value = [...addingIds.value, idKey]

  try {
    await cartStore.addToCart(product, 1)
    const message = cartStore.isGuest
      ? '담겼어요. 로그인하면 서버 장바구니와 동기화됩니다.'
      : '장바구니에 담았어요!'
    uiStore.showToast(message)
  } catch (err) {
    console.error('추천 상품 장바구니 추가 실패:', err)
    uiStore.showToast('장바구니 담기에 실패했어요. 잠시 후 다시 시도해주세요.')
  } finally {
    addingIds.value = addingIds.value.filter(id => id !== idKey)
  }
}

const isAdding = (id: number | string) => addingIds.value.includes(String(id))

onMounted(fetchRecommendations)
</script>
