<template>
  <div class="group relative flex flex-col cursor-pointer">
    <div class="relative aspect-[3/4] bg-gray-50 rounded-lg overflow-hidden mb-5">
      <img :src="getProductImage(product)" :alt="product.name" class="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105">

      <!-- Bottom-right actions: heart (smaller) + cart (+) -->
      <div class="absolute bottom-4 right-4 flex items-center gap-2 opacity-0 translate-y-4 group-hover:opacity-100 group-hover:translate-y-0 transition-all duration-300 z-10">
        <button
          @click.stop="handleToggleWishlist"
          class="w-8 h-8 bg-white/90 backdrop-blur rounded-full shadow flex items-center justify-center hover:bg-gray-100 transition-colors"
          :title="authStore.isAuthenticated ? (isWishlisted ? '찜 취소' : '찜하기') : '로그인 필요'"
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

      <div v-if="product.is_best" class="absolute top-0 left-0 bg-gray-900 text-white text-[10px] font-bold px-3 py-1.5 uppercase tracking-wider">Best</div>
    </div>

    <div>
      <div class="text-xs text-gray-500 mb-1 font-medium">{{ product.description || product.category?.name || '' }}</div>
      <h4 class="text-lg font-normal text-gray-900 mb-2 line-clamp-1 leading-tight group-hover:text-brand-600 transition-colors">{{ product.name }}</h4>
      <div class="flex items-center gap-2">
        <span v-if="product.discount > 0" class="text-red-500 font-bold">{{ product.discount }}%</span>
        <span class="font-bold text-xl text-gray-900">{{ formatPrice(product.price) }}</span>

        <!-- Wishlist count (moved from overlay to reduce image cover) -->
        <div class="ml-auto flex items-center gap-1 text-xs text-gray-500">
          <Heart :size="12" class="text-red-500" />
          <span>{{ localWishlistCount }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Plus, Heart } from 'lucide-vue-next'
import type { Product } from '@/types/product'
import { useCartStore } from '@/stores/cart'
import { useUIStore } from '@/stores/ui'
import { useWishlistStore } from '@/stores/wishlist'
import { useAuthStore } from '@/stores/auth'
import { formatPrice } from '@/utils/formatters'
import { getProductImage } from '@/types/product'
import { ref, watch, computed } from 'vue'

interface Props {
  product: Product
}

const props = defineProps<Props>()
const cartStore = useCartStore()
const uiStore = useUIStore()
const wishlistStore = useWishlistStore()
const authStore = useAuthStore()

const localWishlistCount = ref<number>(props.product.wishlist_count ?? 0)
watch(
  () => props.product.wishlist_count,
  (val) => {
    if (typeof val === 'number') localWishlistCount.value = val
  }
)

const isWishlisted = computed(() => {
  if (!authStore.isAuthenticated) return false
  return wishlistStore.isWishlisted(props.product.id)
})

const handleAddToCart = () => {
  cartStore.addItem(props.product)
  uiStore.showToast('장바구니에 담았습니다.')
}

const handleToggleWishlist = async () => {
  if (!authStore.isAuthenticated) {
    window.dispatchEvent(new CustomEvent('auth:required'))
    return
  }

  try {
    const nowWishlisted = await wishlistStore.toggleWishlist(props.product as any)
    if (nowWishlisted) {
      localWishlistCount.value = (localWishlistCount.value || 0) + 1
    } else {
      localWishlistCount.value = Math.max(0, (localWishlistCount.value || 0) - 1)
    }
  } catch {
    uiStore.showToast('찜 처리에 실패했습니다.')
  }
}
</script>

