/**
 * Cart Store - 백엔드 API 연동 + 비회원 로컬 장바구니 지원
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { cartAPI } from '@/services/api'
import type { Product } from '@/types/product'

// 로컬 스토리지 키
const LOCAL_CART_KEY = 'guest_cart'

export interface CartItem {
  id: number
  product: Product
  quantity: number
  subtotal: number
  created_at: string
  updated_at: string
}

// 비회원 장바구니 아이템 (로컬용)
export interface LocalCartItem {
  id: number  // 로컬에서는 product.id를 사용
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
  const isGuest = ref(false)  // 비회원 모드 여부

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

  // 로컬 장바구니 저장
  const saveLocalCart = () => {
    localStorage.setItem(LOCAL_CART_KEY, JSON.stringify(items.value))
    updateLocalSummary()
  }

  // 로컬 장바구니 로드
  const loadLocalCart = () => {
    const saved = localStorage.getItem(LOCAL_CART_KEY)
    if (saved) {
      try {
        items.value = JSON.parse(saved)
      } catch {
        items.value = []
      }
    }
    updateLocalSummary()
  }

  // 로컬 요약 정보 업데이트
  const updateLocalSummary = () => {
    // subtotal이 없거나 0인 경우 product.price * quantity로 계산
    const totalPrice = items.value.reduce((sum, item) => {
      const itemSubtotal = item.subtotal || (item.product?.price || 0) * item.quantity
      return sum + itemSubtotal
    }, 0)
    const totalQty = items.value.reduce((sum, item) => sum + item.quantity, 0)
    summary.value = {
      total: totalPrice,
      count: items.value.length,
      total_quantity: totalQty
    }
  }

  // 장바구니 로드 (로그인 상태에 따라 분기)
  const loadCart = async () => {
    loading.value = true
    error.value = null

    // 로그인 여부 확인
    const accessToken = localStorage.getItem('access_token')

    if (!accessToken) {
      // 비회원: 로컬 장바구니 사용
      isGuest.value = true
      loadLocalCart()
      loading.value = false
      return
    }

    // 회원: API 호출
    isGuest.value = false
    try {
      const response = await cartAPI.getCart({ page_size: 100 })
      const cartData = response.data.results || response.data

      // subtotal이 없는 경우 직접 계산
      items.value = cartData.map((item: CartItem) => ({
        ...item,
        subtotal: item.subtotal || (item.product?.price || 0) * item.quantity
      }))

      // 요약 정보도 로드
      await loadSummary()
    } catch (err: any) {
      // 401 에러는 로그인 안 된 상태이므로 로컬 장바구니로 전환
      if (err.response?.status === 401) {
        isGuest.value = true
        loadLocalCart()
      } else {
        error.value = err.response?.data?.message || '장바구니를 불러오는데 실패했습니다.'
        console.error('장바구니 로드 실패:', err)
      }
    } finally {
      loading.value = false
    }
  }

  // 장바구니 요약 로드
  const loadSummary = async () => {
    if (isGuest.value) {
      updateLocalSummary()
      return
    }

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
      if (err.response?.status === 401) {
        isGuest.value = true
        loadLocalCart()
      } else {
        console.error('장바구니 요약 로드 실패:', err)
      }
    }
  }

  // 장바구니 추가 (백엔드: 이미 있으면 수량 증가)
  const addToCart = async (product: Product, quantity: number = 1) => {
    loading.value = true
    error.value = null

    // 로그인 여부 확인
    const accessToken = localStorage.getItem('access_token')

    if (!accessToken) {
      // 비회원: 로컬 장바구니에 추가
      isGuest.value = true
      addToLocalCart(product, quantity)
      loading.value = false
      return
    }

    // 회원: API 호출
    try {
      await cartAPI.addToCart({
        product_id: product.id,
        quantity
      })

      // 장바구니 다시 로드
      await loadCart()
    } catch (err: any) {
      // 401 에러 시 로컬 장바구니로 전환
      if (err.response?.status === 401) {
        isGuest.value = true
        addToLocalCart(product, quantity)
      } else {
        error.value = err.response?.data?.message || '장바구니 추가에 실패했습니다.'
        console.error('장바구니 추가 실패:', err)
        throw err
      }
    } finally {
      loading.value = false
    }
  }

  // 비회원 로컬 장바구니에 추가
  const addToLocalCart = (product: Product, quantity: number = 1) => {
    const existingIndex = items.value.findIndex(item => item.product.id === product.id)
    const now = new Date().toISOString()

    if (existingIndex >= 0) {
      // 이미 있으면 수량 증가
      items.value[existingIndex].quantity += quantity
      items.value[existingIndex].subtotal = items.value[existingIndex].product.price * items.value[existingIndex].quantity
      items.value[existingIndex].updated_at = now
    } else {
      // 새로 추가 (id는 음수로 설정하여 서버 ID와 구분)
      const newItem: CartItem = {
        id: -Date.now(),  // 음수로 로컬 ID 생성
        product,
        quantity,
        subtotal: product.price * quantity,
        created_at: now,
        updated_at: now
      }
      items.value.push(newItem)
    }

    saveLocalCart()
  }

  // 수량 변경
  const updateQuantity = async (id: number, quantity: number) => {
    if (quantity < 1) {
      // 수량이 1 미만이면 삭제
      return removeFromCart(id)
    }

    loading.value = true
    error.value = null

    // 비회원: 로컬 장바구니 업데이트
    if (isGuest.value) {
      const item = items.value.find(i => i.id === id)
      if (item) {
        item.quantity = quantity
        item.subtotal = item.product.price * quantity
        item.updated_at = new Date().toISOString()
      }
      saveLocalCart()
      loading.value = false
      return
    }

    // 회원: API 호출
    try {
      await cartAPI.updateCartItem(id, quantity)

      // 로컬 상태 업데이트
      const item = items.value.find(i => i.id === id)
      if (item) {
        item.quantity = quantity
        // v2.1: discount_rate가 없으므로 price를 직접 사용 (price가 이미 최종 가격)
        item.subtotal = item.product.price * quantity
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

    // 비회원: 로컬 장바구니에서 삭제
    if (isGuest.value) {
      items.value = items.value.filter(item => item.id !== id)
      saveLocalCart()
      loading.value = false
      return
    }

    // 회원: API 호출
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

    // 비회원: 로컬 장바구니 비우기
    if (isGuest.value) {
      items.value = []
      summary.value = { total: 0, count: 0, total_quantity: 0 }
      localStorage.removeItem(LOCAL_CART_KEY)
      loading.value = false
      return
    }

    // 회원: API 호출
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
    isGuest.value = false
  }

  // 비회원 장바구니를 서버로 동기화 (로그인 후)
  const syncGuestCartToServer = async () => {
    const guestCart = localStorage.getItem(LOCAL_CART_KEY)
    if (!guestCart) return

    try {
      const guestItems: CartItem[] = JSON.parse(guestCart)
      for (const item of guestItems) {
        await cartAPI.addToCart({
          product_id: item.product.id,
          quantity: item.quantity
        })
      }
      // 동기화 완료 후 로컬 장바구니 삭제
      localStorage.removeItem(LOCAL_CART_KEY)
      // 서버 장바구니 다시 로드
      await loadCart()
    } catch (err) {
      console.error('비회원 장바구니 동기화 실패:', err)
    }
  }

  // 비회원 장바구니 비우기 (로컬만)
  const clearGuestCart = () => {
    localStorage.removeItem(LOCAL_CART_KEY)
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
    isGuest,
    loadCart,
    loadSummary,
    addToCart,
    addToLocalCart,
    updateQuantity,
    increaseQuantity,
    decreaseQuantity,
    removeFromCart,
    clearCart,
    reset,
    syncGuestCartToServer,
    clearGuestCart,
    // 레거시 별칭
    addItem,
    removeItem,
    increaseQty,
    decreaseQty,
  }
})
