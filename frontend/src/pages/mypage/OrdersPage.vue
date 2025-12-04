<template>
  <div class="orders-page">
    <div class="page-header">
      <h2 class="page-title">주문 내역</h2>
      <p class="page-description">지금까지 주문하신 내역을 확인할 수 있습니다.</p>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>주문 내역을 불러오는 중입니다...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="error-state">
      <p class="error-message">{{ error }}</p>
      <button @click="loadOrders" class="btn-retry">다시 시도</button>
    </div>

    <!-- Empty State -->
    <div v-else-if="orders.length === 0" class="empty-state">
      <div class="empty-icon">
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z" />
        </svg>
      </div>
      <h3>주문 내역이 없습니다</h3>
      <p>첫 주문을 지금 바로 시작해 보세요.</p>
      <router-link to="/" class="btn-primary">쇼핑 시작하기</router-link>
    </div>

    <!-- Orders List -->
    <div v-else class="orders-list">
      <div
        v-for="order in orders"
        :key="order.id"
        class="order-card"
      >
        <!-- Order Header -->
        <div class="order-header">
          <div class="order-info">
            <router-link
              :to="`/mypage/orders/${order.id}`"
              class="order-number"
            >
              주문번호: {{ order.order_no }}
            </router-link>
            <span class="order-date">{{ formatDate(order.created_at) }}</span>
          </div>
          <div class="order-status">
            <span class="status-badge" :class="`status-${order.status}`">
              {{ getOrderStatusText(order.status) }}
            </span>
          </div>
        </div>

        <!-- Order Items -->
        <div class="order-items">
          <div
            v-for="item in order.items.slice(0, 3)"
            :key="item.id"
            class="order-item"
          >
            <div class="item-image">
              <img
                :src="item.image_url || DEFAULT_PRODUCT_IMAGE"
                :alt="item.product_name"
                @error="handleImageError"
              />
            </div>
            <div class="item-info">
              <h4 class="item-name">{{ item.product_name }}</h4>
              <p class="item-quantity">
                {{ item.quantity }}개 × {{ formatPrice(item.unit_price || 0) }}
              </p>
            </div>
            <div class="item-total">
              {{ formatPrice(item.total_price) }}
            </div>
          </div>

          <!-- More Items Indicator -->
          <div v-if="order.items.length > 3" class="more-items">
            외 {{ order.items.length - 3 }}개 상품
          </div>
        </div>

        <!-- Order Footer -->
        <div class="order-footer">
          <div class="order-summary">
            <div class="summary-row">
              <span>상품 금액</span>
              <span>{{ formatPrice(order.subtotal) }}</span>
            </div>
            <div class="summary-row">
              <span>배송비</span>
              <span>{{ formatPrice(order.shipping_fee) }}</span>
            </div>
            <div v-if="order.discount_amount > 0" class="summary-row discount">
              <span>할인</span>
              <span>-{{ formatPrice(order.discount_amount) }}</span>
            </div>
            <div class="summary-row total">
              <span>결제 금액</span>
              <span class="total-amount">{{ formatPrice(order.total_amount) }}</span>
            </div>
          </div>

          <div class="order-actions">
            <router-link
              :to="`/mypage/orders/${order.id}`"
              class="btn-detail"
            >
              상세보기
            </router-link>

            <button
              v-if="canCancelOrder(order)"
              @click="handleCancelOrder(order.id)"
              class="btn-cancel"
              :disabled="cancelling === order.id"
            >
              <span v-if="cancelling === order.id">취소 처리 중...</span>
              <span v-else>주문 취소</span>
            </button>

            <button
              v-if="canConfirmDelivery(order)"
              @click="handleConfirmDelivery(order.id)"
              class="btn-confirm"
              :disabled="confirming === order.id"
            >
              <span v-if="confirming === order.id">확인 처리 중...</span>
              <span v-else>배송 완료 확인</span>
            </button>
          </div>
        </div>
      </div>

      <!-- Pagination -->
      <div v-if="totalPages > 1" class="pagination">
        <button
          @click="goToPage(currentPage - 1)"
          :disabled="currentPage === 1"
          class="btn-page"
        >
          이전
        </button>

        <div class="page-numbers">
          <button
            v-for="page in visiblePages"
            :key="page"
            @click="goToPage(page)"
            :class="{ active: page === currentPage }"
            class="btn-page-number"
          >
            {{ page }}
          </button>
        </div>

        <button
          @click="goToPage(currentPage + 1)"
          :disabled="currentPage === totalPages"
          class="btn-page"
        >
          다음
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useOrdersStore } from '@/stores/orders'
import { formatPrice, DEFAULT_PRODUCT_IMAGE } from '@/types/product'
import { getOrderStatusText } from '@/utils/status'

const ordersStore = useOrdersStore()

const loading = ref(true)
const error = ref<string | null>(null)
const cancelling = ref<number | null>(null)
const confirming = ref<number | null>(null)
const currentPage = ref(1)
const pageSize = 10

// Computed
const orders = computed(() => ordersStore.orders)

const totalPages = computed(() => {
  const total = ordersStore.total || orders.value.length
  return Math.ceil(total / pageSize)
})

const visiblePages = computed(() => {
  const pages: number[] = []
  const maxVisible = 5
  let start = Math.max(1, currentPage.value - Math.floor(maxVisible / 2))
  let end = Math.min(totalPages.value, start + maxVisible - 1)

  if (end - start < maxVisible - 1) {
    start = Math.max(1, end - maxVisible + 1)
  }

  for (let i = start; i <= end; i++) {
    pages.push(i)
  }

  return pages
})

// Load orders
const loadOrders = async () => {
  loading.value = true
  error.value = null

  try {
    await ordersStore.loadOrders({
      page: currentPage.value,
      page_size: pageSize,
    })
  } catch (err: any) {
    console.error('주문 목록 로드 실패:', err)
    error.value = '주문 내역을 불러오는 데 실패했습니다.'
  } finally {
    loading.value = false
  }
}

// Pagination
const goToPage = (page: number) => {
  if (page < 1 || page > totalPages.value) return
  currentPage.value = page
  loadOrders()
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

// Cancel order
const handleCancelOrder = async (orderId: number) => {
  const confirmed = confirm('주문을 취소하시겠습니까?')
  if (!confirmed) return

  cancelling.value = orderId

  try {
    await ordersStore.cancelOrder(orderId, '고객 요청')
    alert('주문이 취소되었습니다.')
    await loadOrders()
  } catch (err: any) {
    console.error('주문 취소 실패:', err)
    alert(err.response?.data?.message || '주문 취소에 실패했습니다.')
  } finally {
    cancelling.value = null
  }
}

// Confirm delivery
const handleConfirmDelivery = async (orderId: number) => {
  const confirmed = confirm('배송 완료를 확인하시겠습니까?')
  if (!confirmed) return

  confirming.value = orderId

  try {
    await ordersStore.confirmDelivery(orderId)
    alert('배송 완료가 확인되었습니다.')
    await loadOrders()
  } catch (err: any) {
    console.error('배송 확인 실패:', err)
    alert(err.response?.data?.message || '배송 확인에 실패했습니다.')
  } finally {
    confirming.value = null
  }
}

// Check if order can be cancelled
const canCancelOrder = (order: any): boolean => {
  return ['pending', 'paid', 'processing'].includes(order.status)
}

// Check if delivery can be confirmed
const canConfirmDelivery = (order: any): boolean => {
  return ['paid', 'shipped'].includes(order.status)
}

// Format date
const formatDate = (dateString: string): string => {
  const date = new Date(dateString)
  return date.toLocaleDateString('ko-KR', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })
}

// Handle image error
const handleImageError = (event: Event) => {
  const target = event.target as HTMLImageElement
  target.src = DEFAULT_PRODUCT_IMAGE
}

// Initialize
onMounted(() => {
  loadOrders()
})
</script>

<style scoped>
.orders-page {
  max-width: 100%;
}

.page-header {
  margin-bottom: 2.5rem;
  padding-bottom: 1.5rem;
  border-bottom: 1px solid rgba(95, 0, 128, 0.1);
}

.page-title {
  font-size: 1.875rem;
  font-weight: 700;
  color: #1a1a1a;
  margin-bottom: 0.5rem;
  letter-spacing: -0.02em;
}

.page-description {
  color: #666;
  font-size: 0.9375rem;
  line-height: 1.6;
}

/* Loading & Error States */
.loading-state,
.error-state,
.empty-state {
  text-align: center;
  padding: 4rem 1rem;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #5f0080;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 1rem;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.error-message {
  color: #dc3545;
  font-size: 1.1rem;
  margin-bottom: 1rem;
}

.btn-retry {
  padding: 0.875rem 1.75rem;
  background: #5f0080;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 0.9375rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.btn-retry:hover {
  background: #4c0066;
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

/* Empty State */
.empty-icon {
  width: 80px;
  height: 80px;
  margin: 0 auto 1.5rem;
  color: #ddd;
}

.empty-icon svg {
  width: 100%;
  height: 100%;
}

.empty-state h3 {
  font-size: 1.5rem;
  color: #333;
  margin-bottom: 0.5rem;
}

.empty-state p {
  color: #666;
  margin-bottom: 2rem;
}

.btn-primary {
  display: inline-block;
  padding: 0.875rem 2rem;
  background: #5f0080;
  color: white;
  text-decoration: none;
  border-radius: 8px;
  font-weight: 600;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.btn-primary:hover {
  background: #4c0066;
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

/* Orders List */
.orders-list {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.order-card {
  background: white;
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 12px;
  overflow: hidden;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
}

.order-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  border-color: rgba(95, 0, 128, 0.2);
}

/* Order Header */
.order-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.25rem 1.5rem 1rem;
  border-bottom: 1px solid rgba(0, 0, 0, 0.04);
}

.order-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.order-number {
  font-weight: 600;
  color: #1a1a1a;
  text-decoration: none;
}

.order-number:hover {
  color: #5f0080;
}

.order-date {
  font-size: 0.875rem;
  color: #888;
}

.order-status {
  display: flex;
  align-items: center;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.375rem 0.875rem;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 600;
  border: 1px solid transparent;
}

.status-pending {
  background: #fff3cd;
  color: #856404;
  border-color: #ffeeba;
}

.status-paid,
.status-processing {
  background: #e6f4ff;
  color: #0b5ed7;
  border-color: #b6e0ff;
}

.status-shipped {
  background: #e0f3ff;
  color: #055160;
  border-color: #9eeaf9;
}

.status-delivered {
  background: #d1e7dd;
  color: #0f5132;
  border-color: #badbcc;
}

.status-cancelled,
.status-refunded {
  background: #f8d7da;
  color: #842029;
  border-color: #f5c2c7;
}

/* Order Items */
.order-items {
  padding: 1rem 1.5rem;
  border-bottom: 1px solid rgba(0, 0, 0, 0.04);
}

.order-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.75rem 0;
}

.order-item:not(:last-child) {
  border-bottom: 1px solid #f0f0f0;
  margin-bottom: 0.75rem;
}

.item-image {
  width: 60px;
  height: 60px;
  border-radius: 6px;
  overflow: hidden;
}

.item-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.item-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.item-name {
  font-size: 0.9375rem;
  font-weight: 600;
  color: #1a1a1a;
  line-height: 1.4;
}

.item-quantity {
  font-size: 0.875rem;
  color: #666;
}

.item-total {
  margin-left: auto;
  font-size: 1rem;
  font-weight: 600;
  color: #1a1a1a;
}

.more-items {
  margin-top: 0.5rem;
  padding-top: 0.5rem;
  border-top: 1px dashed #e0e0e0;
  font-size: 0.875rem;
  color: #666;
}

/* Order Footer */
.order-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.5rem 1.25rem;
  gap: 1.5rem;
}

.order-summary {
  flex: 1;
}

.summary-row {
  display: flex;
  justify-content: space-between;
  font-size: 0.9375rem;
  color: #444;
}

.summary-row + .summary-row {
  margin-top: 0.25rem;
}

.summary-row.discount {
  color: #dc3545;
}

.summary-row.total {
  margin-top: 0.5rem;
  font-size: 1.0625rem;
  font-weight: 700;
  color: #1a1a1a;
}

.total-amount {
  font-size: 1.25rem;
  color: #5f0080;
}

.order-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.btn-detail,
.btn-cancel,
.btn-confirm {
  padding: 0.5rem 1rem;
  border-radius: 999px;
  font-size: 0.875rem;
  font-weight: 600;
  border: 1px solid transparent;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-detail {
  background: white;
  color: #5f0080;
  border-color: #e5d4f4;
}

.btn-detail:hover {
  border-color: #5f0080;
}

.btn-cancel {
  background: white;
  color: #dc3545;
  border-color: #f5c2c7;
}

.btn-cancel:hover:not(:disabled) {
  background: #dc3545;
  color: white;
}

.btn-confirm {
  background: #5f0080;
  color: white;
}

.btn-confirm:hover:not(:disabled) {
  background: #4c0066;
}

.btn-cancel:disabled,
.btn-confirm:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Pagination */
.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 0.75rem;
  margin-top: 2rem;
}

.btn-page {
  padding: 0.5rem 1rem;
  border-radius: 999px;
  border: 1px solid #ddd;
  background: white;
  font-size: 0.875rem;
  cursor: pointer;
}

.btn-page:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.page-numbers {
  display: flex;
  gap: 0.25rem;
}

.btn-page-number {
  width: 32px;
  height: 32px;
  border-radius: 999px;
  border: 1px solid #ddd;
  background: white;
  font-size: 0.875rem;
  cursor: pointer;
}

.btn-page-number.active {
  background: #5f0080;
  color: white;
  border-color: #5f0080;
}

/* Responsive */
@media (max-width: 768px) {
  .order-footer {
    flex-direction: column;
    align-items: flex-start;
  }

  .order-actions {
    width: 100%;
    justify-content: flex-end;
  }

  .orders-list {
    gap: 1rem;
  }
}

@media (max-width: 480px) {
  .order-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
  }

  .order-footer {
    padding: 0.75rem 1rem 1rem;
  }

  .order-items {
    padding: 0.75rem 1rem;
  }
}
</style>
