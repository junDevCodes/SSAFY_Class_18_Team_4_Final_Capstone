import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { CartItem, Product } from '@/types/product'

// 장바구니 스토어
export const useCartStore = defineStore('cart', () => {
  const items = ref<CartItem[]>([])

  // 장바구니 총 개수
  const count = computed(() => {
    return items.value.reduce((acc, item) => acc + item.qty, 0)
  })

  // 장바구니 총 금액
  const total = computed(() => {
    return items.value.reduce((acc, item) => acc + (item.price * item.qty), 0)
  })

  // 상품 추가
  const addItem = (product: Product) => {
    const existing = items.value.find(item => item.id === product.id)
    if (existing) {
      existing.qty++
    } else {
      items.value.push({ ...product, qty: 1 })
    }
  }

  // 상품 제거
  const removeItem = (id: number) => {
    const index = items.value.findIndex(item => item.id === id)
    if (index > -1) {
      items.value.splice(index, 1)
    }
  }

  // 수량 증가
  const increaseQty = (id: number) => {
    const item = items.value.find(item => item.id === id)
    if (item) {
      item.qty++
    }
  }

  // 수량 감소
  const decreaseQty = (id: number) => {
    const item = items.value.find(item => item.id === id)
    if (item && item.qty > 1) {
      item.qty--
    }
  }

  return {
    items,
    count,
    total,
    addItem,
    removeItem,
    increaseQty,
    decreaseQty
  }
})

