<template>
  <Transition name="drawer-backdrop">
    <div
      v-if="uiStore.isRecentOpen"
      class="fixed inset-0 bg-black/40 backdrop-blur-sm z-[100]"
      @click="uiStore.closeRecent"
    />
  </Transition>

  <Transition name="drawer-slide">
    <div
      v-if="uiStore.isRecentOpen"
      class="fixed top-0 right-0 h-full w-full sm:w-[380px] bg-white z-[101] shadow-2xl flex flex-col"
    >
      <div class="h-14 px-4 sm:px-5 flex items-center justify-between border-b border-gray-100 bg-white">
        <div class="flex items-center gap-2">
          <Clock3 :size="18" class="text-brand-600" />
          <div class="flex items-center gap-2">
            <h2 class="font-bold text-base text-gray-900">최근 본 상품</h2>
            <span v-if="recentProducts.length" class="text-[11px] font-semibold text-gray-400">
              {{ recentProducts.length }}개
            </span>
          </div>
        </div>
        <div class="flex items-center gap-2">
          <button
            class="p-1.5 rounded-lg text-gray-500 hover:text-gray-900 hover:bg-gray-50 transition-colors disabled:opacity-50"
            @click="refresh"
            :disabled="isLoading"
          >
            <RotateCw :size="18" :class="isLoading ? 'animate-spin' : ''" />
          </button>
          <button class="p-1.5 rounded-lg text-gray-400 hover:text-gray-700 hover:bg-gray-50" @click="uiStore.closeRecent">
            <X :size="20" />
          </button>
        </div>
      </div>

      <div class="flex-1 overflow-y-auto bg-gray-50 p-4 sm:p-5 space-y-3">
        <div v-if="isLoading" class="space-y-3">
          <div
            v-for="n in 6"
            :key="n"
            class="bg-white rounded-xl border border-gray-100 p-3 flex gap-3 animate-pulse"
          >
            <div class="w-20 h-24 rounded-lg bg-gray-200" />
            <div class="flex-1 space-y-2">
              <div class="h-3 w-3/4 bg-gray-200 rounded" />
              <div class="h-3 w-1/2 bg-gray-200 rounded" />
              <div class="h-4 w-1/3 bg-gray-200 rounded" />
            </div>
          </div>
        </div>

        <div v-else-if="error && !isUnauthorized" class="flex flex-col items-center justify-center gap-3 py-8">
          <div class="flex items-center gap-2 text-red-500 font-semibold">
            <AlertCircle :size="18" />
            <span>최근 본 상품을 불러오지 못했어요.</span>
          </div>
          <button
            class="px-4 py-2 text-sm font-semibold text-white bg-brand-600 rounded-lg hover:bg-brand-700"
            @click="refresh"
          >
            다시 시도
          </button>
        </div>

        <div v-else-if="!recentProducts.length || isUnauthorized" class="flex flex-col items-center justify-center gap-3 py-10 text-gray-500">
          <Clock3 :size="32" class="text-gray-300" />
          <p class="text-sm font-semibold">아직 최근 본 상품이 없어요.</p>
          <button
            class="text-xs bg-white border border-gray-300 px-4 py-2 rounded-lg hover:bg-gray-100 text-gray-700 font-medium"
            @click="goToProducts"
          >
            상품 둘러보기
          </button>
        </div>

        <div v-else class="space-y-3">
          <div
            v-for="product in recentProducts"
            :key="product.id"
            class="bg-white p-3 rounded-xl border border-gray-100 shadow-[0_2px_10px_rgba(0,0,0,0.03)] flex gap-3 hover:-translate-y-0.5 transition-transform cursor-pointer"
            @click="goToProduct(product)"
          >
            <img
              :src="getProductImage(product)"
              :alt="product.name"
              class="w-20 h-24 object-cover rounded-lg bg-gray-100 flex-shrink-0"
              @error="onImgError"
            />
            <div class="flex-1 flex flex-col justify-between py-0.5">
              <div class="space-y-1">
                <p class="text-[11px] text-brand-600 font-bold" v-if="product.category_name">{{ product.category_name }}</p>
                <h4 class="text-sm text-gray-800 font-semibold leading-tight line-clamp-2">{{ product.name }}</h4>
              </div>
              <div class="flex items-center justify-between">
                <span class="font-bold text-base text-gray-900">{{ formatPrice(product.price) }}</span>
                <span v-if="product.average_rating" class="text-xs text-gray-500">
                  ★ {{ product.average_rating.toFixed(1) }} ({{ product.review_count ?? 0 }})
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="p-4 border-t border-gray-100 bg-white shadow-[0_-4px_20px_rgba(0,0,0,0.03)]">
        <button
          class="w-full bg-brand-600 text-white font-bold text-base h-11 rounded-lg hover:bg-brand-700 transition-colors flex items-center justify-center gap-2"
          @click="goToProducts"
        >
          전체 상품 보러가기
        </button>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { Clock3, RotateCw, X, AlertCircle } from 'lucide-vue-next'
import { useUIStore } from '@/stores/ui'
import { useRecentProducts } from '@/composables/useRecentProducts'
import { getProductImage } from '@/types/product'
import { formatPrice } from '@/utils/formatters'
import type { Product } from '@/types/product'

const router = useRouter()
const uiStore = useUIStore()
const { recentProducts, isLoading, error, refresh } = useRecentProducts(20)
const isUnauthorized = computed(() => {
  const err = error.value as any
  return !!(err?.response?.status === 401)
})

const goToProduct = (product: Product) => {
  uiStore.closeRecent()
  router.push({
    name: 'product-detail',
    params: { slug: product.slug ?? product.id }
  })
}

const goToProducts = () => {
  uiStore.closeRecent()
  router.push({ name: 'products' })
}

const onImgError = (e: Event) => {
  const el = e.target as HTMLImageElement
  el.src = 'https://via.placeholder.com/80x96.png?text=No+Image'
}
</script>
