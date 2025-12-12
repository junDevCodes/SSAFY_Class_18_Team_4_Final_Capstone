<template>
  <section :class="['recent-products-section max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10', wrapperClass]">
    <div class="flex items-center justify-between gap-3 mb-5">
      <div class="flex items-center gap-2">
        <Clock3 :size="20" class="text-brand-600" />
        <h2 class="text-xl font-bold text-gray-900">{{ title }}</h2>
        <span v-if="recentProducts.length" class="text-xs text-gray-400">
          {{ recentProducts.length }}개
        </span>
      </div>
      <button
        type="button"
        class="inline-flex items-center gap-1 text-xs font-semibold text-brand-600 hover:text-brand-700 disabled:opacity-50"
        @click="refresh"
        :disabled="isLoading"
      >
        <RotateCw :size="16" :class="isLoading ? 'animate-spin' : ''" />
        새로고침
      </button>
    </div>

    <div v-if="isLoading" class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
      <div
        v-for="n in skeletonCount"
        :key="n"
        class="bg-white/60 rounded-xl border border-gray-100 shadow-sm p-3 animate-pulse space-y-3"
      >
        <div class="aspect-[3/4] w-full rounded-lg bg-gray-200" />
        <div class="h-3 w-3/4 bg-gray-200 rounded" />
        <div class="h-4 w-1/2 bg-gray-200 rounded" />
      </div>
    </div>

    <div
      v-else-if="error && !isUnauthorized"
      class="flex flex-col items-center justify-center gap-3 bg-white rounded-xl border border-red-100 py-8"
    >
      <div class="flex items-center gap-2 text-red-500 font-semibold">
        <AlertCircle :size="18" />
        <span>최근 본 상품을 불러오지 못했어요.</span>
      </div>
      <button
        type="button"
        class="px-4 py-2 text-sm font-semibold text-white bg-brand-600 rounded-lg hover:bg-brand-700"
        @click="refresh"
      >
        다시 시도
      </button>
    </div>

    <div
      v-else-if="!recentProducts.length || isUnauthorized"
      class="flex flex-col items-center justify-center gap-3 bg-white rounded-xl border border-dashed border-gray-200 py-10 text-gray-500"
    >
      <span class="text-sm font-semibold">아직 최근 본 상품이 없어요.</span>
      <p class="text-xs text-gray-400">상품을 둘러보면 여기에서 바로 확인할 수 있어요.</p>
    </div>

    <div v-else class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
      <ProductCard
        v-for="product in recentProducts"
        :key="product.id"
        :product="product"
      />
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Clock3, RotateCw, AlertCircle } from 'lucide-vue-next'
import { useRecentProducts } from '@/composables/useRecentProducts'
import ProductCard from '@/components/ui/ProductCard.vue'

const props = withDefaults(
  defineProps<{
    title?: string
    limit?: number
    wrapperClass?: string
  }>(),
  {
    title: '최근 본 상품',
    limit: 10,
    wrapperClass: ''
  }
)

const { recentProducts, isLoading, error, refresh } = useRecentProducts(props.limit)

const skeletonCount = computed(() => Math.min(Math.max(props.limit, 4), 8))
const isUnauthorized = computed(() => {
  const err = error.value as any
  return !!(err?.response?.status === 401)
})
</script>
