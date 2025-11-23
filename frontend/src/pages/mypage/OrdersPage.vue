<template>
  <div class="orders-page">
    <div class="page-header">
      <h2 class="page-title">주문 내역</h2>
      <p class="page-description">지금까지 주문한 내역을 확인할 수 있습니다</p>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>주문 내역을 불러오는 중...</p>
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
      <p>첫 주문을 시작해보세요</p>
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
              주문번호: {{ order.order_number }}
            </router-link>
            <span class="order-date">{{ formatDate(order.created_at) }}</span>
          </div>
          <div class="order-status">
            <span class="status-badge" :class="`status-${order.order_status}`">
              {{ getOrderStatusText(order.order_status) }}
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
              <p class="item-quantity">{{ item.quantity }}개 × {{ formatPrice(item.price) }}</p>
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
              <span v-if="cancelling === order.id">취소 중...</span>
              <span v-else>주문 취소</span>
            </button>

            <button
              v-if="canConfirmDelivery(order)"
              @click="handleConfirmDelivery(order.id)"
              class="btn-confirm"
              :disabled="confirming === order.id"
            >
              <span v-if="confirming === order.id">확인 중...</span>
              <span v-else>배송 확인</span>
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
      page_size: pageSize
    })
  } catch (err: any) {
    console.error('주문 내역 로드 실패:', err)
    error.value = '주문 내역을 불러오는데 실패했습니다.'
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
  const confirmed = confirm('배송을 확인하시겠습니까?')
  if (!confirmed) return

  confirming.value = orderId

  try {
    await ordersStore.confirmDelivery(orderId)
    alert('배송이 확인되었습니다.')
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
  return ['pending', 'paid', 'processing'].includes(order.order_status)
}

// Check if delivery can be confirmed
const canConfirmDelivery = (order: any): boolean => {
  return order.order_status === 'shipped'
}

// Get order status text
const getOrderStatusText = (status: string): string => {
  const statusMap: Record<string, string> = {
    pending: '주문대기',
    paid: '결제완료',
    processing: '처리중',
    shipped: '배송중',
    delivered: '배송완료',
    cancelled: '취소',
    refunded: '환불'
  }
  return statusMap[status] || status
}

// Format date
const formatDate = (dateString: string): string => {
  const date = new Date(dateString)
  return date.toLocaleDateString('ko-KR', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
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
  margin-bottom: 2rem;
  padding-bottom: 1rem;
  border-bottom: 2px solid #f0f0f0;
}

.page-title {
  font-size: 1.75rem;
  font-weight: 700;
  color: #1a1a1a;
  margin-bottom: 0.5rem;
}

.page-description {
  color: #666;
  font-size: 0.9375rem;
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
  border-top: 4px solid #00a86b;
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
  padding: 0.75rem 1.5rem;
  background: #00a86b;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 1rem;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-retry:hover {
  background: #008c5a;
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
  background: #00a86b;
  color: white;
  text-decoration: none;
  border-radius: 6px;
  font-weight: 600;
  transition: background 0.2s;
}

.btn-primary:hover {
  background: #008c5a;
}

/* Orders List */
.orders-list {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.order-card {
  background: white;
  border: 1px solid #e9ecef;
  border-radius: 8px;
  overflow: hidden;
}

/* Order Header */
.order-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.25rem 1.5rem;
  background: #f8f9fa;
  border-bottom: 1px solid #e9ecef;
}

.order-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.order-number {
  font-size: 1rem;
  font-weight: 700;
  color: #1a1a1a;
  text-decoration: none;
}

.order-number:hover {
  color: #00a86b;
}

.order-date {
  font-size: 0.875rem;
  color: #666;
}

.order-status {
  display: flex;
  align-items: center;
}

.status-badge {
  padding: 0.375rem 0.875rem;
  border-radius: 12px;
  font-size: 0.8125rem;
  font-weight: 700;
}

.status-pending { background: #ffc107; color: #000; }
.status-paid { background: #28a745; color: white; }
.status-processing { background: #007bff; color: white; }
.status-shipped { background: #17a2b8; color: white; }
.status-delivered { background: #6c757d; color: white; }
.status-cancelled { background: #dc3545; color: white; }
.status-refunded { background: #e83e8c; color: white; }

/* Order Items */
.order-items {
  padding: 1.5rem;
  border-bottom: 1px solid #e9ecef;
}

.order-item {
  display: grid;
  grid-template-columns: 60px 1fr auto;
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
  text-align: right;
  font-size: 1rem;
  font-weight: 700;
  color: #1a1a1a;
}

.more-items {
  text-align: center;
  padding: 0.75rem;
  background: #f8f9fa;
  border-radius: 6px;
  font-size: 0.875rem;
  color: #666;
  margin-top: 0.75rem;
}

/* Order Footer */
.order-footer {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  padding: 1.5rem;
}

.order-summary {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.summary-row {
  display: flex;
  justify-content: space-between;
  gap: 2rem;
  font-size: 0.875rem;
  color: #666;
}

.summary-row.discount {
  color: #dc3545;
}

.summary-row.total {
  font-size: 1rem;
  font-weight: 700;
  color: #1a1a1a;
  padding-top: 0.5rem;
  border-top: 1px solid #e9ecef;
  margin-top: 0.5rem;
}

.total-amount {
  font-size: 1.25rem;
  color: #00a86b;
}

.order-actions {
  display: flex;
  gap: 0.5rem;
}

.btn-detail,
.btn-cancel,
.btn-confirm {
  padding: 0.625rem 1.25rem;
  border: none;
  border-radius: 6px;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  text-decoration: none;
  display: inline-block;
}

.btn-detail {
  background: #00a86b;
  color: white;
}

.btn-detail:hover {
  background: #008c5a;
}

.btn-cancel {
  background: white;
  color: #dc3545;
  border: 1px solid #dc3545;
}

.btn-cancel:hover:not(:disabled) {
  background: #dc3545;
  color: white;
}

.btn-confirm {
  background: #007bff;
  color: white;
}

.btn-confirm:hover:not(:disabled) {
  background: #0056b3;
}

.btn-cancel:disabled,
.btn-confirm:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Pagination */
.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 0.5rem;
  margin-top: 2rem;
  padding-top: 2rem;
  border-top: 1px solid #e9ecef;
}

.btn-page,
.btn-page-number {
  padding: 0.5rem 0.875rem;
  background: white;
  color: #333;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-page:hover:not(:disabled),
.btn-page-number:hover:not(:disabled) {
  background: #f8f9fa;
  border-color: #00a86b;
  color: #00a86b;
}

.btn-page:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-page-number.active {
  background: #00a86b;
  color: white;
  border-color: #00a86b;
}

.page-numbers {
  display: flex;
  gap: 0.25rem;
}

/* Responsive */
@media (max-width: 768px) {
  .page-title {
    font-size: 1.5rem;
  }

  .order-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.75rem;
  }

  .order-footer {
    flex-direction: column;
    align-items: stretch;
    gap: 1.5rem;
  }

  .order-actions {
    flex-direction: column;
  }

  .btn-detail,
  .btn-cancel,
  .btn-confirm {
    width: 100%;
    text-align: center;
  }
}

@media (max-width: 480px) {
  .order-items,
  .order-footer {
    padding: 1rem;
  }

  .order-item {
    grid-template-columns: 50px 1fr;
    grid-template-areas:
      "image info"
      "total total";
  }

  .item-image {
    grid-area: image;
    width: 50px;
    height: 50px;
  }

  .item-info {
    grid-area: info;
  }

  .item-total {
    grid-area: total;
    text-align: left;
    padding-top: 0.5rem;
    border-top: 1px solid #f0f0f0;
  }
}
</style>
