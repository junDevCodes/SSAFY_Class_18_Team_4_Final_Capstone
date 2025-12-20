<template>
  <section class="py-12 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
    <div class="relative">
      <button
        type="button"
        class="absolute left-0 top-1/2 -translate-y-1/2 z-10 w-10 h-10 flex items-center justify-center rounded-full bg-white border border-gray-200 shadow-md transition hover:shadow-lg disabled:opacity-30 disabled:cursor-not-allowed"
        :disabled="!canScrollLeft"
        aria-label="이전 카테고리"
        @click="scrollByStep(-1)"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
        </svg>
      </button>

      <div
        ref="scroller"
        class="category-scroll flex flex-nowrap items-start justify-start gap-4 sm:gap-5 overflow-x-auto scroll-smooth pl-10 pr-16 sm:pl-12 sm:pr-20"
      >
        <div
          v-for="cat in categories"
          :key="cat.id"
          class="flex flex-col items-center gap-2 cursor-pointer group flex-none w-24 sm:w-28"
          @click="goToCategory(cat.id)"
        >
          <div class="w-14 h-14 sm:w-16 sm:h-16 rounded-full overflow-hidden border border-gray-100 shadow-sm group-hover:shadow-md group-hover:border-brand-200 transition-all duration-300 relative bg-gray-50">
            <img :src="getCategoryImage(cat.name)" :alt="displayName(cat.name)" class="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110">
          </div>
          <span class="mt-2 text-xs sm:text-[13px] text-gray-600 font-medium group-hover:text-brand-700 transition-colors text-center leading-snug w-full">
            {{ displayName(cat.name) }}
          </span>
        </div>
      </div>

      <button
        type="button"
        class="absolute right-[-12px] sm:right-[-16px] top-1/2 -translate-y-1/2 z-10 w-10 h-10 flex items-center justify-center rounded-full bg-white border border-gray-200 shadow-md transition hover:shadow-lg disabled:opacity-30 disabled:cursor-not-allowed"
        :disabled="!canScrollRight"
        aria-label="다음 카테고리"
        @click="scrollByStep(1)"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
        </svg>
      </button>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, computed, ref, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useProductStore } from '@/stores/products'
import { getCategoryImage } from '@/utils/constants'

const router = useRouter()
const productStore = useProductStore()

const categories = computed(() => productStore.categories)
const scroller = ref<HTMLDivElement | null>(null)
const canScrollLeft = ref(false)
const canScrollRight = ref(false)

const updateScrollState = () => {
  const el = scroller.value
  if (!el) return
  const { scrollLeft, scrollWidth, clientWidth } = el
  canScrollLeft.value = scrollLeft > 0
  canScrollRight.value = scrollLeft + clientWidth < scrollWidth - 1
}

const scrollByStep = (direction: number) => {
  const el = scroller.value
  if (!el) return
  const step = 160
  el.scrollBy({ left: direction * step, behavior: 'smooth' })
}

const displayName = (name: string) => {
  return name === '怨쇱씪' ? '怨쇱씪/寃ш낵' : name
}

const goToCategory = (id: number) => {
  router.push({ name: 'search', query: { category: id } })
}

onMounted(async () => {
  if (productStore.categories.length === 0) {
    try {
      await productStore.fetchCategories()
    } catch {
      // ignore
    }
  }
  const el = scroller.value
  el?.addEventListener('scroll', updateScrollState, { passive: true })
  nextTick(updateScrollState)
})

onUnmounted(() => {
  const el = scroller.value
  el?.removeEventListener('scroll', updateScrollState)
})

watch(
  () => categories.value,
  () => nextTick(updateScrollState)
)
</script>

<style scoped>
.category-scroll::-webkit-scrollbar {
  display: none;
}

.category-scroll {
  -ms-overflow-style: none;
  scrollbar-width: none;
}
</style>
