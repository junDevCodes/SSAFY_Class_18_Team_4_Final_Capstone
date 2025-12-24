<template>
  <div
    class="group relative flex flex-col cursor-pointer"
    @click="goToDetail"
  >
    <div class="relative aspect-[3/4] bg-gray-50 rounded-lg overflow-hidden mb-5">
      <img
        :src="getProductImage(product)"
        :alt="product.name"
        class="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
        :class="{ 'grayscale opacity-80': !!statusLabel }"
      >

      <div
        v-if="statusLabel"
        class="absolute inset-0 bg-gray-900/50 backdrop-blur-[1px] flex items-center justify-center text-white z-10"
      >
        <span class="px-3 py-1 rounded-full bg-black/60 text-sm font-semibold">
          {{ statusLabel }}
        </span>
      </div>

      <div class="absolute top-3 left-3 flex flex-wrap gap-2 z-10">
        <span v-if="label" class="inline-flex items-center px-3 py-1 text-[11px] font-bold uppercase tracking-wide rounded-full bg-brand-600 text-white shadow-sm">
          {{ label }}
        </span>
        <span v-if="meta" class="inline-flex items-center px-3 py-1 text-[11px] font-semibold rounded-full bg-orange-500 text-white shadow-sm">
          {{ meta }}
        </span>
        <span
          v-for="(badge, idx) in badges"
          :key="`${badge}-${idx}`"
          class="inline-flex items-center px-3 py-1 text-[11px] font-semibold rounded-full bg-white/85 text-gray-800 shadow"
        >
          {{ badge }}
        </span>
      </div>
      <div v-if="bestLabel" class="absolute top-3 right-3 inline-flex items-center px-3 py-1 text-[11px] font-bold uppercase tracking-wide rounded-full bg-gray-800 text-white shadow-sm z-10">
        {{ bestLabel }}
      </div>

      <!-- Bottom-right actions: heart (smaller) + cart (+) -->
      <div
        class="absolute bottom-4 right-4 flex items-center gap-2 opacity-0 translate-y-4 group-hover:opacity-100 group-hover:translate-y-0 transition-all duration-300 z-10"
        :class="{ 'pointer-events-none opacity-30 !translate-y-0': !isActive }"
      >
        <button
          @click.stop="handleToggleWishlist"
          class="w-8 h-8 bg-white/90 backdrop-blur rounded-full shadow flex items-center justify-center hover:bg-gray-100 transition-colors"
          :title="authStore.isAuthenticated ? (isWishlisted ? '찜취소' : '찜하기') : '로그인 필요'"
        >
          <Heart :size="16" :class="isWishlisted ? 'text-red-500' : 'text-gray-700'" />
        </button>

        <button
          @click.stop="handleAddToCart"
          class="w-12 h-12 bg-white/90 backdrop-blur text-gray-900 rounded-full shadow-lg flex items-center justify-center hover:bg-brand-600 hover:text-white transition-colors"
        >
          <Plus :size="24" />
        </button>
      </div>
    </div>

    <div>
      <div class="text-xs text-gray-500 mb-1 font-medium">{{ product.category_name || product.category?.name || '' }}</div>
      <h4 class="text-lg font-normal text-gray-900 mb-2 line-clamp-1 leading-tight group-hover:text-brand-600 transition-colors">{{ product.name }}</h4>
      <div v-if="showPrice" class="flex items-center gap-2">
        <span v-if="discountRate > 0" class="text-red-500 font-bold">{{ discountRate }}%</span>
        <span class="font-bold text-xl text-gray-900">{{ formatPrice(product.price) }}</span>

        <div class="ml-auto flex items-center gap-1 text-xs text-gray-500">
          <Heart :size="12" class="text-red-500" />
          <span>{{ localWishlistCount }}</span>
        </div>
      </div>

      <div v-else class="flex items-center justify-end gap-1 text-xs text-gray-500">
        <Heart :size="12" class="text-red-500" />
        <span>{{ localWishlistCount }}</span>
      </div>

      <div v-if="seller?.name" class="flex items-center gap-3 mt-3 text-sm text-gray-700">
        <img v-if="seller.avatar" :src="seller.avatar" alt="" class="w-8 h-8 rounded-full object-cover">
        <div class="flex flex-col">
          <span class="font-semibold">{{ seller.name }}</span>
          <span v-if="seller.rating" class="text-xs text-gray-500">★ {{ seller.rating }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Plus, Heart } from 'lucide-vue-next'
import { useRouter } from 'vue-router'
import { ref, watch, computed } from 'vue'
import type { Product } from '@/types/product'
import { useCartStore } from '@/stores/cart'
import { useUIStore } from '@/stores/ui'
import { useWishlistStore } from '@/stores/wishlist'
import { useAuthStore } from '@/stores/auth'
import { formatPrice } from '@/utils/formatters'
import { getProductImage, calculateDiscountRate } from '@/types/product'

type SellerInfo = {
  name?: string
  avatar?: string
  rating?: number | null
}

interface Props {
  product: Product
  label?: string
  meta?: string
  badges?: string[]
  bestLabel?: string
  seller?: SellerInfo
  showPrice?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  label: '',
  meta: '',
  badges: () => [],
  bestLabel: '',
  seller: () => ({}),
  showPrice: true
})
const router = useRouter()
const cartStore = useCartStore()
const uiStore = useUIStore()
const wishlistStore = useWishlistStore()
const authStore = useAuthStore()

const isActive = computed(() => props.product.status === 'active')
const statusLabel = computed(() => {
  switch (props.product.status) {
    case 'inactive':
      return '판매 일시정지'
    case 'draft':
      return '판매 준비중'
    case 'out_of_stock':
      return '품절'
    case 'discontinued':
      return '단종'
    default:
      return ''
  }
})

const goToDetail = () => {
  router.push({ name: 'product-detail', params: { slug: props.product.slug } })
}

const localWishlistCount = ref<number>(props.product.wishlist_count ?? 0)
watch(
  () => props.product.wishlist_count,
  (val) => {
    if (typeof val === 'number') localWishlistCount.value = val
  }
)

const discountRate = computed(() => {
  return calculateDiscountRate(props.product.original_price ?? 0, props.product.price)
})

const isWishlisted = computed(() => {
  if (!authStore.isAuthenticated) return false
  return wishlistStore.isWishlisted(props.product.id)
})

const handleAddToCart = async () => {
  if (!isActive.value) {
    uiStore.showToast('현재 판매가 일시정지된 상품입니다.')
    return
  }
  try {
    await cartStore.addToCart(props.product, 1)
    const message = cartStore.isGuest
      ? '장바구니에 담았어요! 로그인 후 주문가능해요!'
      : '장바구니에 담았어요!'
    uiStore.showToast(message)
  } catch {
    uiStore.showToast('장바구니 담기에 실패했어요. 잠시 후 다시 시도해주세요.')
  }
}

const handleToggleWishlist = async () => {
  if (!isActive.value) {
    uiStore.showToast('판매 중인 상품만 찜이 가능해요.')
    return
  }
  if (!authStore.isAuthenticated) {
    window.dispatchEvent(new CustomEvent('auth:required'))
    uiStore.showToast('로그인이 필요해요.')
    return
  }

  try {
    const result = await wishlistStore.toggleWishlist(props.product as any)
    localWishlistCount.value = result.wishlistCount
  } catch {
    uiStore.showToast('찜 처리에 실패했어요.')
  }
}
</script>
