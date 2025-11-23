/**
 * Cart Store - 백엔드 API 연동
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { cartAPI } from '@/services/api'
import type { Product } from '@/types/product'

export interface CartItem {
  id: number
  product: Product
  quantity: number
  subtotal: number
  created_at: string
  updated_at: string
}

export const useCartStore = defineStore('cart', () => {
  const items = ref<CartItem[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  // 요약 정보
  const summary = ref({
    total: 0,
    count: 0,
    total_quantity: 0
  })

  // Computed
  const count = computed(() => summary.value.count)
  const totalQuantity = computed(() => summary.value.total_quantity)
  const total = computed(() => summary.value.total)

  // 장바구니 로드
  const loadCart = async () => {
    loading.value = true
    error.value = null

    try {
      const response = await cartAPI.getCart({ page_size: 100 })
      items.value = response.data.results || response.data

      // 요약 정보도 로드
      await loadSummary()
    } catch (err: any) {
      // 401 에러는 로그인 안 된 상태이므로 무시
      if (err.response?.status !== 401) {
        error.value = err.response?.data?.message || '장바구니를 불러오는데 실패했습니다.'
        console.error('장바구니 로드 실패:', err)
      }
    } finally {
      loading.value = false
    }
  }

  // 장바구니 요약 로드
  const loadSummary = async () => {
    try {
      const response = await cartAPI.getCartSummary()
      summary.value = {
        total: response.data.total || 0,
        count: response.data.count || 0,
        total_quantity: response.data.total_quantity || 0
      }
      // 요약에서 items도 반환되면 업데이트
      if (response.data.items) {
        items.value = response.data.items
      }
    } catch (err: any) {
      if (err.response?.status !== 401) {
        console.error('장바구니 요약 로드 실패:', err)
      }
    }
  }

  // 장바구니 추가 (백엔드: 이미 있으면 수량 증가)
  const addToCart = async (product: Product, quantity: number = 1) => {
    loading.value = true
    error.value = null

    try {
      await cartAPI.addToCart({
        product_id: product.id,
        quantity
      })

      // 장바구니 다시 로드
      await loadCart()
    } catch (err: any) {
      error.value = err.response?.data?.message || '장바구니 추가에 실패했습니다.'
      console.error('장바구니 추가 실패:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  // 수량 변경
  const updateQuantity = async (id: number, quantity: number) => {
    if (quantity < 1) {
      // 수량이 1 미만이면 삭제
      return removeFromCart(id)
    }

    loading.value = true
    error.value = null

    try {
      await cartAPI.updateCartItem(id, quantity)

      // 로컬 상태 업데이트
      const item = items.value.find(i => i.id === id)
      if (item) {
        item.quantity = quantity
        const unitPrice = item.product.discount_rate > 0
          ? Math.round(item.product.price * (100 - item.product.discount_rate) / 100)
          : item.product.price
        item.subtotal = unitPrice * quantity
      }

      // 요약 정보 다시 로드
      await loadSummary()
    } catch (err: any) {
      error.value = err.response?.data?.message || '수량 변경에 실패했습니다.'
      console.error('수량 변경 실패:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  // 수량 증가
  const increaseQuantity = async (id: number) => {
    const item = items.value.find(i => i.id === id)
    if (item) {
      await updateQuantity(id, item.quantity + 1)
    }
  }

  // 수량 감소
  const decreaseQuantity = async (id: number) => {
    const item = items.value.find(i => i.id === id)
    if (item) {
      await updateQuantity(id, item.quantity - 1)
    }
  }

  // 장바구니에서 삭제
  const removeFromCart = async (id: number) => {
    loading.value = true
    error.value = null

    try {
      await cartAPI.removeFromCart(id)

      // 로컬 상태 업데이트
      items.value = items.value.filter(item => item.id !== id)

      // 요약 정보 다시 로드
      await loadSummary()
    } catch (err: any) {
      error.value = err.response?.data?.message || '장바구니 삭제에 실패했습니다.'
      console.error('장바구니 삭제 실패:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  // 장바구니 비우기
  const clearCart = async () => {
    loading.value = true
    error.value = null

    try {
      await cartAPI.clearCart()

      // 로컬 상태 초기화
      items.value = []
      summary.value = { total: 0, count: 0, total_quantity: 0 }
    } catch (err: any) {
      error.value = err.response?.data?.message || '장바구니 비우기에 실패했습니다.'
      console.error('장바구니 비우기 실패:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  // 초기화 (로그아웃 시)
  const reset = () => {
    items.value = []
    summary.value = { total: 0, count: 0, total_quantity: 0 }
    loading.value = false
    error.value = null
  }

  // 레거시 호환성을 위한 별칭
  const addItem = addToCart
  const removeItem = removeFromCart
  const increaseQty = increaseQuantity
  const decreaseQty = decreaseQuantity

  return {
    items,
    loading,
    error,
    summary,
    count,
    totalQuantity,
    total,
    loadCart,
    loadSummary,
    addToCart,
    updateQuantity,
    increaseQuantity,
    decreaseQuantity,
    removeFromCart,
    clearCart,
    reset,
    // 레거시 별칭
    addItem,
    removeItem,
    increaseQty,
    decreaseQty,
  }
})
