<template>
  <div class="group relative flex flex-col cursor-pointer">
    <div class="relative aspect-[3/4] bg-gray-50 rounded-lg overflow-hidden mb-5">
      <img :src="product.image_url" :alt="product.name" class="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105">

      <button
        @click.stop="handleAddToCart"
        class="absolute bottom-4 right-4 w-12 h-12 bg-white/90 backdrop-blur text-gray-900 rounded-full shadow-lg flex items-center justify-center opacity-0 translate-y-4 group-hover:opacity-100 group-hover:translate-y-0 hover:bg-brand-600 hover:text-white transition-all duration-300 z-10"
      >
        <Plus :size="24" />
      </button>

      <div v-if="product.is_best" class="absolute top-0 left-0 bg-gray-900 text-white text-[10px] font-bold px-3 py-1.5 uppercase tracking-wider">Best</div>
    </div>

    <div>
      <div class="text-xs text-gray-500 mb-1 font-medium">{{ product.description || product.category?.name || '' }}</div>
      <h4 class="text-lg font-normal text-gray-900 mb-2 line-clamp-1 leading-tight group-hover:text-brand-600 transition-colors">{{ product.name }}</h4>
      <div class="flex items-center gap-2">
        <span v-if="product.discount > 0" class="text-red-500 font-bold">{{ product.discount }}%</span>
        <span class="font-bold text-xl text-gray-900">{{ formatPrice(product.price) }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Plus } from 'lucide-vue-next'
import type { Product } from '@/types/product'
import { useCartStore } from '@/stores/cart'
import { useUIStore } from '@/stores/ui'
import { formatPrice } from '@/utils/formatters'

interface Props {
  product: Product
}

const props = defineProps<Props>()
const cartStore = useCartStore()
const uiStore = useUIStore()

const handleAddToCart = () => {
  cartStore.addItem(props.product)
  uiStore.showToast('장바구니에 담았습니다.')
}
</script>

