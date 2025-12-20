<template>
  <Transition name="slide-fade">
    <aside
      v-if="shouldShow"
      :class="['hidden xl:block z-[120] drop-shadow-2xl', placementClass]"
      :style="placementStyle"
      aria-label="최근 본 상품 바"
    >
      <div class="w-24 rounded-2xl border border-gray-200 bg-white/95 backdrop-blur-md px-3 py-2.5 shadow-lg">
        <div class="flex items-center justify-between gap-2 text-[10px] font-semibold text-gray-700">
          <span class="whitespace-nowrap">최근본상품</span>
          <button
            type="button"
            class="text-gray-400 transition-colors hover:text-brand-600 disabled:opacity-50"
            :disabled="isLoading"
            @click="refresh"
            aria-label="최근 본 상품 새로고침"
          >
            <RotateCw :size="14" :class="isLoading ? 'animate-spin' : ''" />
          </button>
        </div>

        <div v-if="isLoading" class="mt-2.5 flex flex-col gap-1.5">
          <div v-for="n in 4" :key="n" class="aspect-[3/4] w-full rounded-lg bg-gray-100 animate-pulse" />
        </div>

        <div v-else class="mt-2.5 flex flex-col gap-1.5">
          <button
            v-for="product in limitedProducts"
            :key="product.id"
            type="button"
            class="group flex flex-col items-center gap-1"
            @click="goToDetail(product.slug)"
          >
            <div
              class="relative aspect-[3/4] w-full overflow-hidden rounded-lg border border-gray-100 bg-gradient-to-b from-gray-50 to-white shadow-sm transition-transform duration-200 group-hover:-translate-y-1"
            >
              <img
                :src="getProductImage(product)"
                :alt="product.name"
                class="h-full w-full object-cover"
                loading="lazy"
              />
              <div class="absolute inset-0 rounded-xl ring-2 ring-transparent transition-all duration-200 group-hover:ring-brand-500/40" />
            </div>
          </button>
        </div>
      </div>
    </aside>
  </Transition>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { RotateCw } from 'lucide-vue-next'
import { useRecentProducts } from '@/composables/useRecentProducts'
import { getProductImage } from '@/types/product'

const router = useRouter()
const { recentProducts, isLoading, error, refresh } = useRecentProducts(4)
const props = withDefaults(
  defineProps<{
    placementClass?: string
    placementStyle?: Record<string, string>
    lockSelector?: string
    lockOffset?: number
    fallbackTop?: number
  }>(),
  {
    placementClass: 'fixed right-6 top-44',
    placementStyle: () => ({}),
    lockSelector: '#sticky-nav',
    lockOffset: 40,
    fallbackTop: 92
  }
)
const placementClass = computed(() => props.placementClass)
const lockedTop = ref<number>(props.fallbackTop)

const updateLockedTop = () => {
  const target = document.querySelector(props.lockSelector) as HTMLElement | null
  if (!target) {
    lockedTop.value = props.fallbackTop
    return
  }
  const rect = target.getBoundingClientRect()
  lockedTop.value = rect.bottom + props.lockOffset
}

onMounted(() => {
  updateLockedTop()
  window.addEventListener('scroll', updateLockedTop, { passive: true })
  window.addEventListener('resize', updateLockedTop)
})

onBeforeUnmount(() => {
  window.removeEventListener('scroll', updateLockedTop)
  window.removeEventListener('resize', updateLockedTop)
})

const placementStyle = computed(() => ({
  ...props.placementStyle,
  top: `${lockedTop.value}px`
}))

const isUnauthorized = computed(() => {
  const err = error.value as any
  return !!(err?.response?.status === 401)
})

const limitedProducts = computed(() => recentProducts.value.slice(0, 4))
const shouldShow = computed(() => (isLoading.value || limitedProducts.value.length > 0) && !isUnauthorized.value)

const goToDetail = (slug: string) => {
  router.push({ name: 'product-detail', params: { slug } })
}
</script>

<style scoped>
.slide-fade-enter-active,
.slide-fade-leave-active {
  transition: all 0.25s ease;
}

.slide-fade-enter-from,
.slide-fade-leave-to {
  opacity: 0;
  transform: translateX(10px);
}
</style>
