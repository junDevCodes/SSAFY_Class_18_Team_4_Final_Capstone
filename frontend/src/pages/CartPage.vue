<template>
  <div class="cart-page">
    <div class="cart-container">
      <h1 class="page-title">장바구니</h1>

      <!-- 로딩 상태 -->
      <div v-if="cartStore.loading" class="loading">
        <p>장바구니를 불러오는 중...</p>
      </div>

      <!-- 에러 상태 -->
      <div v-else-if="cartStore.error" class="error-message">
        <p>{{ cartStore.error }}</p>
        <button @click="cartStore.loadCart()" class="btn-retry">다시 시도</button>
      </div>

      <!-- 빈 장바구니 -->
      <div v-else-if="cartStore.items.length === 0" class="empty-cart">
        <div class="empty-icon">🛒</div>
        <h2>장바구니가 비어있습니다</h2>
        <p>마음에 드는 상품을 담아보세요!</p>
        <button @click="$router.push('/')" class="btn-shopping">쇼핑 계속하기</button>
      </div>

      <!-- 장바구니 목록 -->
      <div v-else class="cart-content">
        <div class="cart-list">
          <!-- 전체 선택 -->
          <div class="select-all">
            <label>
              <input
                type="checkbox"
                v-model="selectAll"
                @change="toggleSelectAll"
              />
              전체 선택 ({{ selectedItems.length }}/{{ cartStore.items.length }})
            </label>
            <button
              @click="deleteSelectedItems"
              class="btn-delete-selected"
              :disabled="selectedItems.length === 0"
            >
              선택 삭제
            </button>
          </div>

          <!-- 장바구니 아이템 -->
          <div
            v-for="item in cartStore.items"
            :key="item.id"
            class="cart-item"
          >
            <div class="item-checkbox">
              <input
                type="checkbox"
                :value="item.id"
                v-model="selectedItems"
              />
            </div>

            <div class="item-image" @click="goToProduct(item.product)">
              <img
                :src="getProductImage(item.product)"
                :alt="item.product.name"
                @error="handleImageError"
              />
            </div>

            <div class="item-info">
              <h3 class="item-name" @click="goToProduct(item.product)">
                {{ item.product.name }}
              </h3>
              <p class="item-unit" v-if="item.product.unit">
                {{ item.product.unit }}
              </p>
              <div class="item-price">
                <span class="price">{{ formatPrice(item.product.price) }}</span>
                <span v-if="item.product.original_price" class="original-price">
                  {{ formatPrice(item.product.original_price) }}
                </span>
              </div>
            </div>

            <div class="item-quantity">
              <button
                @click="decreaseQuantity(item)"
                :disabled="item.quantity <= 1 || updating === item.id"
                class="qty-btn"
              >
                -
              </button>
              <input
                type="number"
                :value="item.quantity"
                @change="updateQuantity(item, $event)"
                min="1"
                max="999"
                :disabled="updating === item.id"
                class="qty-input"
              />
              <button
                @click="increaseQuantity(item)"
                :disabled="updating === item.id"
                class="qty-btn"
              >
                +
              </button>
            </div>

            <div class="item-subtotal">
              <p class="subtotal-label">소계</p>
              <p class="subtotal-price">{{ formatPrice(item.subtotal || item.product.price * item.quantity) }}</p>
            </div>

            <div class="item-actions">
              <button
                @click="removeItem(item)"
                :disabled="deleting === item.id"
                class="btn-remove"
              >
                {{ deleting === item.id ? '삭제 중...' : '삭제' }}
              </button>
            </div>
          </div>
        </div>

        <!-- 주문 요약 -->
        <div class="order-summary">
          <h2>주문 요약</h2>

          <div class="summary-row">
            <span>상품 금액</span>
            <span>{{ formatPrice(selectedSubtotal) }}</span>
          </div>

          <div class="summary-row">
            <span>배송비</span>
            <span>{{ formatPrice(shippingFee) }}</span>
          </div>

          <div v-if="shippingFee > 0 && freeShippingRemaining > 0" class="shipping-notice">
            <p>{{ formatPrice(freeShippingRemaining) }} 더 담으면 무료배송!</p>
          </div>

          <div class="summary-divider"></div>

          <div class="summary-row total">
            <span>총 결제금액</span>
            <span class="total-price">{{ formatPrice(totalPrice) }}</span>
          </div>

          <button
            @click="goToCheckout"
            :disabled="selectedItems.length === 0"
            class="btn-checkout"
          >
            {{ selectedItems.length > 0 ? `${selectedItems.length}개 상품 주문하기` : '상품을 선택해주세요' }}
          </button>

          <button
            @click="$router.push('/')"
            class="btn-continue-shopping"
          >
            쇼핑 계속하기
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useCartStore } from '@/stores/cart'
import { useAuthStore } from '@/stores/auth'
import { useUIStore } from '@/stores/ui'
import type { CartItem } from '@/stores/cart'
import { getProductImage, formatPrice, DEFAULT_PRODUCT_IMAGE, type Product } from '@/types/product'

const router = useRouter()
const cartStore = useCartStore()
const authStore = useAuthStore()
const uiStore = useUIStore()

const selectedItems = ref<Array<CartItem['id']>>([])
const updating = ref<CartItem['id'] | null>(null)
const deleting = ref<CartItem['id'] | null>(null)

// 전체 선택 체크박스
const selectAll = computed({
  get: () => selectedItems.value.length === cartStore.items.length && cartStore.items.length > 0,
  set: (value: boolean) => {
    if (value) {
      selectedItems.value = cartStore.items.map(item => item.id)
    } else {
      selectedItems.value = []
    }
  }
})

// 선택된 상품들의 소계
const selectedSubtotal = computed(() => {
  return cartStore.items
    .filter(item => selectedItems.value.includes(item.id))
    .reduce((sum, item) => sum + item.subtotal, 0)
})

// 배송비 (3만원 이상 무료배송)
const FREE_SHIPPING_THRESHOLD = 30000
const shippingFee = computed(() => {
  if (selectedSubtotal.value >= FREE_SHIPPING_THRESHOLD) {
    return 0
  }
  return selectedSubtotal.value > 0 ? 3000 : 0
})

// 무료배송까지 남은 금액
const freeShippingRemaining = computed(() => {
  return Math.max(0, FREE_SHIPPING_THRESHOLD - selectedSubtotal.value)
})

// 총 결제금액
const totalPrice = computed(() => {
  return selectedSubtotal.value + shippingFee.value
})

onMounted(async () => {
  await cartStore.loadCart()
  // 로드 완료 후 전체 선택
  if (cartStore.items.length > 0) {
    selectedItems.value = cartStore.items.map(item => item.id)
  }
})

function toggleSelectAll() {
  // computed setter에서 처리됨
}

async function increaseQuantity(item: CartItem) {
  updating.value = item.id
  try {
    await cartStore.increaseQuantity(item.id)
  } catch (err) {
    console.error('수량 증가 실패:', err)
  } finally {
    updating.value = null
  }
}

async function decreaseQuantity(item: CartItem) {
  updating.value = item.id
  try {
    await cartStore.decreaseQuantity(item.id)
  } catch (err) {
    console.error('수량 감소 실패:', err)
  } finally {
    updating.value = null
  }
}

async function updateQuantity(item: CartItem, event: Event) {
  const target = event.target as HTMLInputElement
  const newQuantity = parseInt(target.value)

  if (isNaN(newQuantity) || newQuantity < 1) {
    target.value = item.quantity.toString()
    return
  }

  updating.value = item.id
  try {
    await cartStore.updateQuantity(item.id, newQuantity)
  } catch (err) {
    console.error('수량 변경 실패:', err)
    target.value = item.quantity.toString()
  } finally {
    updating.value = null
  }
}

async function removeItem(item: CartItem) {
  if (!confirm('이 상품을 장바구니에서 삭제하시겠습니까?')) {
    return
  }

  deleting.value = item.id
  try {
    await cartStore.removeFromCart(item.id)
    // 선택 목록에서도 제거
    selectedItems.value = selectedItems.value.filter(id => id !== item.id)
  } catch (err) {
    console.error('삭제 실패:', err)
    alert('삭제에 실패했습니다.')
  } finally {
    deleting.value = null
  }
}

async function deleteSelectedItems() {
  if (selectedItems.value.length === 0) {
    return
  }

  if (!confirm(`선택한 ${selectedItems.value.length}개 상품을 삭제하시겠습니까?`)) {
    return
  }

  const itemsToDelete = [...selectedItems.value]

  for (const itemId of itemsToDelete) {
    try {
      await cartStore.removeFromCart(itemId)
    } catch (err) {
      console.error('삭제 실패:', itemId, err)
    }
  }

  selectedItems.value = []
}

function goToProduct(product: Product) {
  router.push(`/products/${product.slug}`)
}

function goToCheckout() {
  if (selectedItems.value.length === 0) {
    alert('주문할 상품을 선택해주세요.')
    return
  }

  // 비로그인 상태면 로그인 모달을 열고 리다이렉트 경로 저장
  if (!authStore.isAuthenticated) {
    uiStore.setRedirectPath('/checkout')
    uiStore.openLogin()
    return
  }

  // 선택된 장바구니 항목 ID를 쿼리로 전달
  router.push({
    name: 'checkout',
    query: {
      items: selectedItems.value.join(',')
    }
  })
}

function handleImageError(e: Event) {
  (e.target as HTMLImageElement).src = DEFAULT_PRODUCT_IMAGE
}
</script>

<style scoped>
.cart-page {
  min-height: 100vh;
  background: #f9f9f9;
  padding: 2rem 0;
}

.cart-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1rem;
}

.page-title {
  font-size: 2rem;
  margin-bottom: 2rem;
  color: #333;
}

/* 로딩 & 에러 */
.loading,
.error-message {
  text-align: center;
  padding: 3rem;
  background: white;
  border-radius: 8px;
}

.btn-retry {
  margin-top: 1rem;
  padding: 0.75rem 2rem;
  background: #2d5016;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-weight: bold;
}

/* 빈 장바구니 */
.empty-cart {
  text-align: center;
  padding: 5rem 2rem;
  background: white;
  border-radius: 8px;
}

.empty-icon {
  font-size: 5rem;
  margin-bottom: 1rem;
}

.empty-cart h2 {
  font-size: 1.5rem;
  margin-bottom: 0.5rem;
  color: #333;
}

.empty-cart p {
  color: #666;
  margin-bottom: 2rem;
}

.btn-shopping {
  padding: 1rem 3rem;
  background: #2d5016;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-weight: bold;
  font-size: 1rem;
}

/* 장바구니 컨텐츠 */
.cart-content {
  display: grid;
  grid-template-columns: 1fr 350px;
  gap: 2rem;
  align-items: start;
}

/* 장바구니 목록 */
.cart-list {
  background: white;
  border-radius: 8px;
  padding: 1.5rem;
}

.select-all {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 1rem;
  border-bottom: 2px solid #eee;
  margin-bottom: 1rem;
}

.select-all label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: bold;
  cursor: pointer;
}

.btn-delete-selected {
  padding: 0.5rem 1rem;
  background: white;
  border: 1px solid #ddd;
  border-radius: 4px;
  cursor: pointer;
  color: #666;
}

.btn-delete-selected:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 장바구니 아이템 */
.cart-item {
  display: grid;
  grid-template-columns: auto 100px 1fr auto auto auto;
  gap: 1.5rem;
  align-items: center;
  padding: 1.5rem 0;
  border-bottom: 1px solid #eee;
}

.cart-item:last-child {
  border-bottom: none;
}

.item-checkbox input {
  width: 20px;
  height: 20px;
  cursor: pointer;
}

.item-image {
  width: 100px;
  height: 100px;
  overflow: hidden;
  border-radius: 8px;
  cursor: pointer;
}

.item-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.item-info {
  flex: 1;
}

.item-name {
  font-size: 1rem;
  margin-bottom: 0.5rem;
  cursor: pointer;
  color: #333;
}

.item-name:hover {
  color: #2d5016;
}

.item-unit {
  font-size: 0.875rem;
  color: #666;
  margin-bottom: 0.5rem;
}

.item-price {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.item-price .price {
  font-weight: bold;
  font-size: 1.125rem;
  color: #2d5016;
}

.item-price .original-price {
  text-decoration: line-through;
  color: #999;
  font-size: 0.875rem;
}

/* 수량 조절 */
.item-quantity {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.qty-btn {
  width: 32px;
  height: 32px;
  border: 1px solid #ddd;
  background: white;
  cursor: pointer;
  border-radius: 4px;
  font-weight: bold;
}

.qty-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.qty-input {
  width: 60px;
  height: 32px;
  text-align: center;
  border: 1px solid #ddd;
  border-radius: 4px;
}

/* 소계 */
.item-subtotal {
  text-align: right;
}

.subtotal-label {
  font-size: 0.875rem;
  color: #666;
  margin-bottom: 0.25rem;
}

.subtotal-price {
  font-weight: bold;
  font-size: 1.125rem;
  color: #333;
}

/* 삭제 버튼 */
.btn-remove {
  padding: 0.5rem 1rem;
  background: white;
  border: 1px solid #ddd;
  border-radius: 4px;
  cursor: pointer;
  color: #666;
}

.btn-remove:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 주문 요약 */
.order-summary {
  background: white;
  border-radius: 8px;
  padding: 1.5rem;
  position: sticky;
  top: 2rem;
}

.order-summary h2 {
  font-size: 1.25rem;
  margin-bottom: 1.5rem;
  color: #333;
}

.summary-row {
  display: flex;
  justify-content: space-between;
  margin-bottom: 1rem;
  font-size: 1rem;
}

.summary-row.total {
  font-size: 1.25rem;
  font-weight: bold;
  color: #2d5016;
}

.shipping-notice {
  background: #f0f7eb;
  padding: 0.75rem;
  border-radius: 4px;
  margin-bottom: 1rem;
}

.shipping-notice p {
  font-size: 0.875rem;
  color: #2d5016;
  text-align: center;
  margin: 0;
}

.summary-divider {
  height: 1px;
  background: #eee;
  margin: 1.5rem 0;
}

.total-price {
  font-size: 1.5rem;
  color: #2d5016;
}

.btn-checkout {
  width: 100%;
  padding: 1rem;
  background: #2d5016;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-weight: bold;
  font-size: 1rem;
  margin-bottom: 0.5rem;
}

.btn-checkout:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.btn-continue-shopping {
  width: 100%;
  padding: 1rem;
  background: white;
  color: #2d5016;
  border: 1px solid #2d5016;
  border-radius: 4px;
  cursor: pointer;
  font-weight: bold;
  font-size: 1rem;
}

/* 반응형 */
@media (max-width: 1024px) {
  .cart-content {
    grid-template-columns: 1fr;
  }

  .order-summary {
    position: static;
  }
}

@media (max-width: 768px) {
  .cart-item {
    grid-template-columns: auto 80px 1fr;
    gap: 1rem;
  }

  .item-quantity,
  .item-subtotal,
  .item-actions {
    grid-column: 2 / 4;
  }

  .item-quantity {
    justify-content: flex-start;
  }

  .item-subtotal {
    text-align: left;
  }
}
</style>
