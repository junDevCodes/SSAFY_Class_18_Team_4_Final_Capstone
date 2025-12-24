<template>
  <section v-if="!loading && timeDealProducts.length > 0" class="py-20 border-b border-gray-100">
    <div class="max-w-7xl mx-auto">
      <div class="px-4 sm:px-6 lg:px-8 mb-8 flex justify-between items-end">
        <div>
          <div class="text-brand-600 font-bold text-sm mb-2 tracking-wider uppercase">PriceScout</div>
          <h3 class="text-3xl font-display font-bold text-gray-900">지금이 구매 타이밍!</h3>
        </div>
        <div class="flex items-center gap-4">
          <div class="flex items-center gap-2 text-2xl font-bold text-gray-900 font-mono bg-gray-100 px-4 py-2 rounded-lg">
            <Timer :size="20" class="text-brand-600" />
            <span>{{ timer.hours }}:{{ timer.minutes }}:{{ timer.seconds }}</span>
          </div>
          <!-- 좌우 스크롤 버튼 -->
          <div class="hidden sm:flex items-center gap-2">
            <button
              @click="scrollToPrev"
              class="p-2 rounded-full bg-gray-100 hover:bg-gray-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              :disabled="!canScrollLeft"
            >
              <ChevronLeft :size="20" class="text-gray-600" />
            </button>
            <button
              @click="scrollToNext"
              class="p-2 rounded-full bg-gray-100 hover:bg-gray-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              :disabled="!canScrollRight"
            >
              <ChevronRight :size="20" class="text-gray-600" />
            </button>
          </div>
        </div>
      </div>

      <div
        ref="scrollContainer"
        class="overflow-x-auto no-scrollbar px-4 sm:px-6 lg:px-8 pb-8 -mx-4 sm:mx-0 scroll-smooth"
        @scroll="updateScrollState"
      >
        <div class="flex gap-6 w-max">
          <router-link
            v-for="product in timeDealProducts"
            :key="product.product_id"
            :to="`/products/${product.slug || product.product_id}`"
            class="w-[220px] group cursor-pointer flex-shrink-0"
          >
            <div class="relative aspect-[4/5] rounded-xl overflow-hidden bg-gray-100 mb-4 shadow-sm">
              <img
                :src="product.main_image || '/placeholder-product.png'"
                :alt="product.name"
                class="w-full h-full object-cover transition-transform duration-700 group-hover:scale-110"
              >
              <!-- 할인율 배지 -->
              <div
                v-if="getDiscountRate(product) > 0"
                class="absolute top-3 left-3 bg-red-500 text-white text-xs font-bold px-2 py-1 rounded"
              >
                -{{ getDiscountRate(product) }}%
              </div>
              <!-- 우측 상단: 역대 최저가 > 특가(모델 추천) > 할인(폴백) -->
              <div
                v-if="product.is_lowest_ever"
                class="absolute top-3 right-3 bg-gradient-to-r from-red-500 to-red-600 text-white text-xs font-bold px-2 py-1 rounded shadow-lg animate-pulse flex items-center gap-1"
              >
                <Flame :size="12" />
                역대 최저가
              </div>
              <!-- 모델 추천 상품 (가격 이력 기반): 특가 배지 -->
              <div
                v-else-if="isPriceHistoryBased(product)"
                class="absolute top-3 right-3 bg-red-600 text-white text-xs font-bold px-2 py-1 rounded"
              >
                특가
              </div>
              <!-- 폴백 상품 (할인 상품): 할인 배지 -->
              <div
                v-else
                class="absolute top-3 right-3 bg-orange-500 text-white text-xs font-bold px-2 py-1 rounded"
              >
                할인
              </div>
              <!-- 호버 시 좋아요/장바구니 버튼 -->
              <div
                class="absolute bottom-3 right-3 flex items-center gap-2 opacity-0 translate-y-4 group-hover:opacity-100 group-hover:translate-y-0 transition-all duration-300 z-10"
              >
                <button
                  @click="handleToggleWishlist($event, product)"
                  class="w-8 h-8 bg-white/90 backdrop-blur rounded-full shadow flex items-center justify-center hover:bg-gray-100 transition-colors"
                  :title="authStore.isAuthenticated ? (isWishlisted(product.product_id) ? '찜취소' : '찜하기') : '로그인 필요'"
                >
                  <Heart :size="16" :class="isWishlisted(product.product_id) ? 'text-red-500 fill-red-500' : 'text-gray-700'" />
                </button>
                <button
                  @click="handleAddToCart($event, product)"
                  class="w-10 h-10 bg-white/90 backdrop-blur text-gray-900 rounded-full shadow-lg flex items-center justify-center hover:bg-brand-600 hover:text-white transition-colors"
                  title="장바구니 담기"
                >
                  <Plus :size="20" />
                </button>
              </div>
            </div>
            <h4 class="text-base font-medium text-gray-900 mb-1 line-clamp-1 group-hover:text-brand-600 transition-colors">
              {{ product.name }}
            </h4>
            <div class="flex items-baseline gap-2 mb-1">
              <span class="font-bold text-lg">{{ formatPrice(product.price) }}</span>
              <span
                v-if="product.original_price && product.original_price > product.price"
                class="text-sm text-gray-400 line-through"
              >
                {{ formatPrice(product.original_price) }}
              </span>
            </div>
            <!-- 모델 추천 상품 (가격 이력 기반): 평균가 대비 변동률 표시 -->
            <div v-if="isPriceHistoryBased(product)" class="flex items-center gap-1 text-xs">
              <!-- 하락 시 -->
              <template v-if="product.price_change_rate < 0">
                <TrendingDown :size="14" class="text-green-600" />
                <span class="font-medium text-green-600">
                  평균가 대비 {{ Math.abs(product.price_change_rate).toFixed(1) }}% 하락
                </span>
              </template>
              <!-- 안정 또는 상승 시 -->
              <template v-else>
                <TrendingUp :size="14" class="text-blue-500" />
                <span class="font-medium text-blue-500">
                  평균가 대비 {{ product.price_change_rate > 0 ? '+' : '' }}{{ product.price_change_rate.toFixed(1) }}%
                </span>
              </template>
            </div>
            <!-- 폴백 상품 (할인 상품): 절감액 표시 -->
            <div v-else-if="product.savings > 0" class="flex items-center gap-1 text-xs">
              <Tag :size="14" class="text-orange-500" />
              <span class="text-gray-600">
                {{ product.savings.toLocaleString() }}원 절감
              </span>
            </div>
          </router-link>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { Timer, ChevronLeft, ChevronRight, TrendingDown, TrendingUp, Tag, Flame, Heart, Plus } from 'lucide-vue-next'
import { useTimer } from '@/composables/useTimer'
import { formatPrice } from '@/utils/formatters'
import { recommendationsAPI, type TimeDealProduct } from '@/services/api'
import { useCartStore } from '@/stores/cart'
import { useUIStore } from '@/stores/ui'
import { useWishlistStore } from '@/stores/wishlist'
import { useAuthStore } from '@/stores/auth'

const { timer } = useTimer()
const timeDealProducts = ref<TimeDealProduct[]>([])
const loading = ref(false)

// 스토어
const cartStore = useCartStore()
const uiStore = useUIStore()
const wishlistStore = useWishlistStore()
const authStore = useAuthStore()

// 스크롤 관련 상태
const scrollContainer = ref<HTMLElement | null>(null)
const canScrollLeft = ref(false)
const canScrollRight = ref(true)

// 상품 카드 너비 + gap (220px + 24px gap)
const CARD_WIDTH = 244

// 화면에 보이는 상품 개수 계산
const visibleCardCount = computed(() => {
  if (!scrollContainer.value) return 4
  const containerWidth = scrollContainer.value.clientWidth
  return Math.floor(containerWidth / CARD_WIDTH) || 1
})

// 모델 추천 상품인지 확인 (previous_price가 있으면 가격 이력 기반 = 모델 추천)
const isPriceHistoryBased = (product: TimeDealProduct): boolean => {
  return product.previous_price !== null
}

// 할인율 계산
const getDiscountRate = (product: TimeDealProduct): number => {
  if (!product.original_price || product.original_price <= product.price) return 0
  return Math.round(((product.original_price - product.price) / product.original_price) * 100)
}

// 찜 여부 확인
const isWishlisted = (productId: number): boolean => {
  if (!authStore.isAuthenticated) return false
  return wishlistStore.isWishlisted(productId)
}

// 장바구니 추가
const handleAddToCart = async (event: Event, product: TimeDealProduct) => {
  event.preventDefault()
  event.stopPropagation()

  try {
    // TimeDealProduct를 Product 형식으로 변환
    const cartProduct = {
      id: product.product_id,
      slug: product.slug || `product-${product.product_id}`,
      name: product.name,
      price: product.price,
      original_price: product.original_price,
      main_image: product.main_image,
      status: 'active' as const,
    }
    await cartStore.addToCart(cartProduct as any, 1)
    const message = cartStore.isGuest
      ? '장바구니에 담았어요! 로그인 후 주문가능해요!'
      : '장바구니에 담았어요!'
    uiStore.showToast(message)
  } catch {
    uiStore.showToast('장바구니 담기에 실패했어요. 잠시 후 다시 시도해주세요.')
  }
}

// 찜하기/취소
const handleToggleWishlist = async (event: Event, product: TimeDealProduct) => {
  event.preventDefault()
  event.stopPropagation()

  if (!authStore.isAuthenticated) {
    window.dispatchEvent(new CustomEvent('auth:required'))
    uiStore.showToast('로그인이 필요해요.')
    return
  }

  try {
    // TimeDealProduct를 Product 형식으로 변환
    const wishlistProduct = {
      id: product.product_id,
      slug: product.slug || `product-${product.product_id}`,
      name: product.name,
      price: product.price,
      original_price: product.original_price,
      main_image: product.main_image,
    }
    await wishlistStore.toggleWishlist(wishlistProduct as any)
  } catch {
    uiStore.showToast('찜 처리에 실패했어요.')
  }
}

// 스크롤 상태 업데이트
const updateScrollState = () => {
  if (!scrollContainer.value) return
  const { scrollLeft, scrollWidth, clientWidth } = scrollContainer.value
  canScrollLeft.value = scrollLeft > 0
  canScrollRight.value = scrollLeft + clientWidth < scrollWidth - 10
}

// 이전 페이지로 스크롤 (보이는 상품 개수만큼)
const scrollToPrev = () => {
  if (!scrollContainer.value) return
  const scrollAmount = visibleCardCount.value * CARD_WIDTH
  scrollContainer.value.scrollBy({ left: -scrollAmount, behavior: 'smooth' })
}

// 다음 페이지로 스크롤 (보이는 상품 개수만큼)
const scrollToNext = () => {
  if (!scrollContainer.value) return
  const scrollAmount = visibleCardCount.value * CARD_WIDTH
  scrollContainer.value.scrollBy({ left: scrollAmount, behavior: 'smooth' })
}

// 타임세일 상품 로드
onMounted(async () => {
  loading.value = true
  try {
    const { data } = await recommendationsAPI.getTimeDealProducts({ limit: 10 })
    timeDealProducts.value = data.products
    // 초기 스크롤 상태 업데이트
    setTimeout(updateScrollState, 100)
  } catch (e) {
    console.error('타임세일 상품 조회 실패:', e)
    timeDealProducts.value = []
  } finally {
    loading.value = false
  }
})

// 윈도우 리사이즈 시 스크롤 상태 업데이트
onMounted(() => {
  window.addEventListener('resize', updateScrollState)
})

onUnmounted(() => {
  window.removeEventListener('resize', updateScrollState)
})
</script>
