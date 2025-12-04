<template>
  <!-- Backdrop -->
  <Transition name="drawer-backdrop">
    <div v-if="uiStore.isCartOpen" class="fixed inset-0 bg-black/40 backdrop-blur-sm z-[100]" @click="uiStore.closeCart"></div>
  </Transition>

  <!-- Drawer -->
  <Transition name="drawer-slide">
    <div v-if="uiStore.isCartOpen" class="fixed top-0 right-0 h-full w-full sm:w-[400px] bg-white z-[101] shadow-2xl flex flex-col">
      <div class="h-14 px-5 flex items-center justify-between border-b border-gray-100 bg-white">
        <h2 class="font-bold text-lg text-gray-900">장바구니</h2>
        <button @click="uiStore.closeCart" class="p-2 -mr-2 text-gray-400 hover:text-gray-900">
          <X :size="24" />
        </button>
      </div>
      
      <div class="flex-1 overflow-y-auto p-5 bg-gray-50">
        <div v-if="cartStore.items.length === 0" class="h-full flex flex-col items-center justify-center text-gray-400 space-y-3">
          <ShoppingBag :size="48" class="opacity-20" />
          <p class="text-sm font-medium">담긴 상품이 없습니다.</p>
          <button @click="uiStore.closeCart" class="text-xs bg-white border border-gray-300 px-4 py-2 rounded hover:bg-gray-100 text-gray-700 font-medium">쇼핑 계속하기</button>
        </div>
        
        <div v-else class="space-y-3">
          <div v-for="item in cartStore.items" :key="item.id" class="bg-white p-4 rounded-lg border border-gray-100 shadow-sm flex gap-4 relative">
            <img :src="getProductImage(item.product)" :alt="item.product.name" class="w-20 h-24 object-cover rounded bg-gray-50" @error="onImgError">
            <div class="flex-1 flex flex-col justify-between py-0.5">
              <div>
                <div class="text-[10px] text-brand-600 font-bold mb-1">샛별배송</div>
                <h4 class="text-sm text-gray-800 font-medium line-clamp-2 leading-tight">{{ item.product.name }}</h4>
              </div>
              <div class="flex items-center justify-between mt-2">
                <div class="flex items-center border border-gray-200 rounded bg-white h-7">
                  <button @click="cartStore.decreaseQty(item.id)" class="w-7 h-full flex items-center justify-center text-gray-500 hover:bg-gray-50">-</button>
                  <span class="w-8 text-center text-xs font-bold">{{ item.quantity }}</span>
                  <button @click="cartStore.increaseQty(item.id)" class="w-7 h-full flex items-center justify-center text-gray-500 hover:bg-gray-50">+</button>
                </div>
                <span class="font-bold text-sm">{{ formatPrice(item.subtotal || item.product.price * item.quantity) }}</span>
              </div>
            </div>
            <button @click="cartStore.removeItem(item.id)" class="absolute top-3 right-3 text-gray-300 hover:text-gray-500">
              <X :size="16" />
            </button>
          </div>
        </div>
      </div>

      <div class="bg-white p-5 border-t border-gray-100 shadow-[0_-4px_20px_rgba(0,0,0,0.03)]">
        <div class="flex justify-between items-center mb-4 text-sm">
          <span class="text-gray-600">총 결제 예정 금액</span>
          <span class="text-xl font-bold text-gray-900">{{ formatPrice(cartStore.total) }}</span>
        </div>
        <div class="flex gap-2 text-[11px] text-gray-500 mb-4 bg-gray-50 p-2 rounded">
          <span class="text-brand-500 font-bold">적립</span>
          <span>구매 시 {{ formatPrice(cartStore.total * 0.05) }} (5%) 적립 예정</span>
        </div>
        <button
          @click="handleCheckout"
          :disabled="cartStore.items.length === 0"
          class="w-full bg-brand-500 text-white font-bold text-base h-12 rounded-lg hover:bg-brand-600 transition-colors shadow-lg shadow-brand-500/20 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          주문하기
        </button>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { X, ShoppingBag } from 'lucide-vue-next'
import { useRouter } from 'vue-router'
import { useUIStore } from '@/stores/ui'
import { useCartStore } from '@/stores/cart'
import { useAuthStore } from '@/stores/auth'
import { formatPrice } from '@/utils/formatters'
import { getProductImage } from '@/types/product'

const router = useRouter()
const uiStore = useUIStore()
const cartStore = useCartStore()
const authStore = useAuthStore()

const onImgError = (e: Event) => {
  const el = e.target as HTMLImageElement
  el.src = 'https://via.placeholder.com/80x96.png?text=No+Image'
}

// 주문하기 버튼 클릭 핸들러
const handleCheckout = () => {
  // 장바구니 닫기
  uiStore.closeCart()

  // 로그인 여부 확인
  if (!authStore.isAuthenticated) {
    // 비회원인 경우 비회원 주문 페이지로 이동
    router.push({
      name: 'checkout',
      query: {
        guest: 'true',
        items: cartStore.items.map(item => item.id).join(',')
      }
    })
    return
  }

  // 회원인 경우 모든 장바구니 항목으로 주문
  router.push({
    name: 'checkout',
    query: {
      items: cartStore.items.map(item => item.id).join(',')
    }
  })
}
</script>

