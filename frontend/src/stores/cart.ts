/**
 * Cart Store - 백엔드 API 연동 + 비회원 로컬 장바구니 지원
 *
 * 기능:
 * - 회원/비회원 장바구니 관리
 * - 레시피 GapFilling 추천 (장바구니 기반)
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { cartAPI } from '@/services/api'
import { recommendationApi } from '@/services/api/recommendations'
import type { Product, RecipeRecommendation, CartRecipeResponse } from '@/types/product'

// 로컬 스토리지 키
const LOCAL_CART_KEY = 'guest_cart'

const generateLocalId = () => {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID()
  }
  return `local-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

export interface CartItem {
  id: number | string
  product: Product
  quantity: number
  subtotal: number
  created_at: string
  updated_at: string
  origin?: 'server' | 'local'
  clientId?: string
}

// 비회원 장바구니 아이템 (로컬용)
export interface LocalCartItem {
  id: string  // 로컬에서는 product.id를 사용
  product: Product
  quantity: number
  subtotal: number
  created_at: string
  updated_at: string
  origin: 'local'
  clientId: string
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

  const getLocalCartItems = (): LocalCartItem[] => {
    const saved = localStorage.getItem(LOCAL_CART_KEY)
    if (!saved) return []
    try {
      const parsed = JSON.parse(saved) as Partial<LocalCartItem>[]
      return parsed
        .filter(item => item?.product)
        .map((item) => {
          const clientId = item.clientId || (typeof item.id === 'string' ? item.id : generateLocalId())
          const quantity = item.quantity ?? 0
          const product = item.product as Product
          const subtotal = item.subtotal || (product?.price || 0) * quantity
          return {
            ...item,
            id: clientId,
            clientId,
            product,
            quantity,
            subtotal,
            created_at: item.created_at || new Date().toISOString(),
            updated_at: item.updated_at || new Date().toISOString(),
            origin: 'local'
          } as LocalCartItem
        })
    } catch {
      return []
    }
  }

  // 로컬 장바구니 저장
  const saveLocalCart = (localItems?: LocalCartItem[]) => {
    const itemsToSave = localItems ?? (items.value.filter(item => item.origin === 'local') as LocalCartItem[])
    localStorage.setItem(LOCAL_CART_KEY, JSON.stringify(itemsToSave))
    if (isGuest.value) {
      updateLocalSummary(itemsToSave)
    }
  }

  // 로컬 장바구니 로드
  const loadLocalCart = () => {
    const localItems = getLocalCartItems()
    items.value = localItems
    updateLocalSummary(localItems)
  }

  // 로컬 요약 정보 업데이트
  const updateLocalSummary = (source: CartItem[] = items.value) => {
    // subtotal이 없거나 0인 경우 product.price * quantity로 계산
    const totalPrice = source.reduce((sum, item) => {
      const itemSubtotal = item.subtotal || (item.product?.price || 0) * item.quantity
      return sum + itemSubtotal
    }, 0)
    const totalQty = source.reduce((sum, item) => sum + item.quantity, 0)
    summary.value = {
      total: totalPrice,
      count: source.length,
      total_quantity: totalQty
    }
  }

  // 장바구니 로드 (로그인 상태에 따라 분기)
  const loadCart = async () => {
    loading.value = true
    error.value = null

    // 로그인 여부 확인
    const accessToken = localStorage.getItem('access_token')
    const hasLocalGuestCart = !!localStorage.getItem(LOCAL_CART_KEY)

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
      if (hasLocalGuestCart) {
        try {
          await syncGuestCartToServer({ reload: false })
        } catch (syncError) {
          console.error('게스트 장바구니 동기화 중 오류:', syncError)
        }
      }

      const response = await cartAPI.getCart({ page_size: 100 })
      const cartData = response.data.results || response.data

      // subtotal이 없는 경우 직접 계산
      items.value = cartData.map((item: CartItem) => ({
        ...item,
        subtotal: item.subtotal || (item.product?.price || 0) * item.quantity,
        origin: 'server',
        clientId: item.clientId || String(item.id)
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
        items.value = response.data.items.map((item: CartItem) => ({
          ...item,
          subtotal: item.subtotal || (item.product?.price || 0) * item.quantity,
          origin: 'server',
          clientId: item.clientId || String(item.id)
        }))
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
      const existing = items.value[existingIndex]
      existing.quantity += quantity
      existing.subtotal = existing.product.price * existing.quantity
      existing.updated_at = now
      existing.origin = 'local'
      if (!existing.clientId) {
        existing.clientId = typeof existing.id === 'string' ? existing.id : generateLocalId()
      }
      existing.id = existing.clientId
    } else {
      // 새로 추가 (클라이언트 ID로 서버 ID와 구분)
      const clientId = generateLocalId()
      const newItem: LocalCartItem = {
        id: clientId,
        clientId,
        product,
        quantity,
        subtotal: product.price * quantity,
        created_at: now,
        updated_at: now,
        origin: 'local'
      }
      items.value.push(newItem)
    }

    saveLocalCart()
  }

  // 수량 변경
  const updateQuantity = async (id: number | string, quantity: number) => {
    if (quantity < 1) {
      // 수량이 1 미만이면 삭제
      return removeFromCart(id)
    }

    loading.value = true
    error.value = null

    const item = items.value.find(i => i.id === id)
    const isLocalItem = isGuest.value || item?.origin === 'local' || typeof id === 'string'

    // 비회원 또는 로컬 아이템은 로컬에서만 업데이트
    if (isLocalItem) {
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
      await cartAPI.updateCartItem(Number(id), quantity)

      // 로컬 상태 업데이트
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
  const increaseQuantity = async (id: number | string) => {
    const item = items.value.find(i => i.id === id)
    if (item) {
      await updateQuantity(id, item.quantity + 1)
    }
  }

  // 수량 감소
  const decreaseQuantity = async (id: number | string) => {
    const item = items.value.find(i => i.id === id)
    if (item) {
      await updateQuantity(id, item.quantity - 1)
    }
  }

  // 장바구니에서 삭제
  const removeFromCart = async (id: number | string) => {
    loading.value = true
    error.value = null

    const target = items.value.find(item => item.id === id)
    const isLocalItem = isGuest.value || target?.origin === 'local' || typeof id === 'string'

    // 비회원 또는 로컬 아이템: 로컬 장바구니에서 삭제
    if (isLocalItem) {
      items.value = items.value.filter(item => item.id !== id)
      saveLocalCart()
      loading.value = false
      return
    }

    // 회원: API 호출
    try {
      await cartAPI.removeFromCart(Number(id))

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
      localStorage.removeItem(LOCAL_CART_KEY)
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
  const syncGuestCartToServer = async (options: { reload?: boolean } = {}) => {
    const guestItems = getLocalCartItems()
    if (!guestItems.length) return { synced: 0, failed: 0 }

    const failedItems: LocalCartItem[] = []
    let syncedCount = 0

    for (const item of guestItems) {
      try {
        await cartAPI.addToCart({
          product_id: item.product.id,
          quantity: item.quantity
        })
        syncedCount += 1
      } catch (err) {
        console.error('비회원 장바구니 동기화 실패:', err)
        failedItems.push(item)
      }
    }

    if (failedItems.length === 0) {
      localStorage.removeItem(LOCAL_CART_KEY)
    } else {
      // 실패한 항목만 남겨서 재시도할 수 있게 유지
      saveLocalCart(failedItems)
    }

    if (options.reload) {
      await loadCart()
    }

    return { synced: syncedCount, failed: failedItems.length }
  }

  // 비회원 장바구니 비우기 (로컬만)
  const clearGuestCart = () => {
    localStorage.removeItem(LOCAL_CART_KEY)
  }

  // ============================================================
  // 레시피 GapFilling 추천
  // ============================================================

  // 레시피 추천 상태
  const recipeRecommendations = ref<RecipeRecommendation[]>([])
  const recipeLoading = ref(false)
  const recipeError = ref<string | null>(null)
  const cartIngredients = ref<string[]>([])  // 인식된 재료 목록
  const detectedDishes = ref<string[]>([])   // 검출된 요리명 목록 (예: ['삼계탕', '불고기'])
  const totalGapCount = ref(0)               // 전체 부족 재료 수
  const recipeProcessingTime = ref(0)        // 처리 시간 (ms)

  // 레시피 추천 활성화 여부 (UI 토글용)
  const recipeRecommendationEnabled = ref(true)

  // 현재 선택된 레시피 인덱스 (캐러셀용)
  const selectedRecipeIndex = ref(0)

  // Computed: 선택된 레시피
  const selectedRecipe = computed(() => {
    if (recipeRecommendations.value.length === 0) return null
    return recipeRecommendations.value[selectedRecipeIndex.value] || null
  })

  // Computed: 레시피 추천이 있는지 여부
  const hasRecipeRecommendations = computed(() => recipeRecommendations.value.length > 0)

  /**
   * 장바구니 기반 레시피 추천 요청
   *
   * 장바구니에 담긴 상품을 분석하여 만들 수 있는 레시피를 추천하고,
   * 부족한 재료에 해당하는 상품을 추천합니다.
   *
   * @param limit 추천 레시피 개수 (기본 3개)
   */
  const fetchRecipeRecommendations = async (limit: number = 3) => {
    // 추천 비활성화 상태면 스킵
    if (!recipeRecommendationEnabled.value) return

    // 장바구니가 비어있으면 추천 초기화
    if (items.value.length === 0) {
      recipeRecommendations.value = []
      cartIngredients.value = []
      detectedDishes.value = []
      totalGapCount.value = 0
      return
    }

    recipeLoading.value = true
    recipeError.value = null

    try {
      // 장바구니 상품 ID 추출
      const productIds = items.value.map(item => item.product.id)

      // API 호출
      const response: CartRecipeResponse = await recommendationApi.getCartRecipeRecommendations(
        productIds,
        limit
      )

      if (response.success) {
        recipeRecommendations.value = response.recipes
        cartIngredients.value = response.cart_ingredients
        detectedDishes.value = response.detected_dishes || []
        totalGapCount.value = response.total_gap_count
        recipeProcessingTime.value = response.processing_time_ms

        // 선택 인덱스 초기화
        selectedRecipeIndex.value = 0
      } else {
        // 실패 시 초기화
        recipeRecommendations.value = []
        cartIngredients.value = []
        detectedDishes.value = []
        recipeError.value = response.message || '레시피 추천을 불러오는데 실패했습니다.'
      }
    } catch (err: unknown) {
      console.error('레시피 추천 로드 실패:', err)
      recipeError.value = '레시피 추천 서비스에 연결할 수 없습니다.'
      recipeRecommendations.value = []
      detectedDishes.value = []
    } finally {
      recipeLoading.value = false
    }
  }

  /**
   * 레시피 선택 (캐러셀 네비게이션)
   */
  const selectRecipe = (index: number) => {
    if (index >= 0 && index < recipeRecommendations.value.length) {
      selectedRecipeIndex.value = index
    }
  }

  /**
   * 다음 레시피로 이동
   */
  const nextRecipe = () => {
    if (recipeRecommendations.value.length === 0) return
    selectedRecipeIndex.value = (selectedRecipeIndex.value + 1) % recipeRecommendations.value.length
  }

  /**
   * 이전 레시피로 이동
   */
  const prevRecipe = () => {
    if (recipeRecommendations.value.length === 0) return
    selectedRecipeIndex.value = selectedRecipeIndex.value === 0
      ? recipeRecommendations.value.length - 1
      : selectedRecipeIndex.value - 1
  }

  /**
   * 레시피 추천 활성화/비활성화 토글
   */
  const toggleRecipeRecommendation = () => {
    recipeRecommendationEnabled.value = !recipeRecommendationEnabled.value
    if (recipeRecommendationEnabled.value) {
      // 활성화 시 추천 새로고침
      fetchRecipeRecommendations()
    } else {
      // 비활성화 시 추천 초기화
      recipeRecommendations.value = []
      cartIngredients.value = []
      detectedDishes.value = []
    }
  }

  /**
   * 레시피 추천 초기화
   */
  const clearRecipeRecommendations = () => {
    recipeRecommendations.value = []
    cartIngredients.value = []
    detectedDishes.value = []
    totalGapCount.value = 0
    selectedRecipeIndex.value = 0
    recipeError.value = null
  }

  /**
   * Gap 상품을 장바구니에 추가
   *
   * @param productId 상품 ID
   * @param quantity 수량 (기본 1)
   */
  const addGapProductToCart = async (productId: number, quantity: number = 1) => {
    // 추천된 상품에서 Product 정보 찾기
    let gapProduct = null
    for (const recipe of recipeRecommendations.value) {
      const found = recipe.recommended_products.find(p => p.product_id === productId)
      if (found) {
        gapProduct = found
        break
      }
    }

    if (!gapProduct) {
      console.error('Gap 상품을 찾을 수 없습니다:', productId)
      return
    }

    // Product 형태로 변환하여 장바구니에 추가
    const product: Product = {
      id: gapProduct.product_id,
      name: gapProduct.name,
      price: gapProduct.price,
      original_price: gapProduct.original_price,
      main_image: gapProduct.main_image,
      slug: '',
      unit: null,
      category_name: null,
      status: 'active',
      product_type: 'main',
      created_at: new Date().toISOString(),
      view_count: 0,
      average_rating: 0,
      review_count: 0,
      wishlist_count: 0,
      quality_score: 0,
    }

    await addToCart(product, quantity)

    // 레시피 추천 새로고침 (디바운스 적용)
    setTimeout(() => {
      fetchRecipeRecommendations()
    }, 500)
  }

  // 레거시 호환성을 위한 별칭
  const addItem = addToCart
  const removeItem = removeFromCart
  const increaseQty = increaseQuantity
  const decreaseQty = decreaseQuantity

  return {
    // 장바구니 기본
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

    // 레시피 GapFilling 추천
    recipeRecommendations,
    recipeLoading,
    recipeError,
    cartIngredients,
    detectedDishes,
    totalGapCount,
    recipeProcessingTime,
    recipeRecommendationEnabled,
    selectedRecipeIndex,
    selectedRecipe,
    hasRecipeRecommendations,
    fetchRecipeRecommendations,
    selectRecipe,
    nextRecipe,
    prevRecipe,
    toggleRecipeRecommendation,
    clearRecipeRecommendations,
    addGapProductToCart,

    // 레거시 별칭
    addItem,
    removeItem,
    increaseQty,
    decreaseQty,
  }
})
