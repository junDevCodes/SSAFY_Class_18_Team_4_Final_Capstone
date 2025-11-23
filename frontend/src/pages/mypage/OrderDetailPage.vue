<template>
  <div class="order-detail-page">
    <!-- Loading State -->
    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>주문 정보를 불러오는 중...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="error-state">
      <p class="error-message">{{ error }}</p>
      <router-link to="/mypage/orders" class="btn-back">주문 내역으로 돌아가기</router-link>
    </div>

    <!-- Order Detail Content -->
    <div v-else-if="order" class="order-detail-content">
      <!-- Page Header -->
      <div class="page-header">
        <div class="header-left">
          <router-link to="/mypage/orders" class="btn-back-link">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
            </svg>
            목록으로
          </router-link>
          <h2 class="page-title">주문 상세</h2>
        </div>
        <div class="header-right">
          <span class="status-badge" :class="`status-${order.order_status}`">
            {{ getOrderStatusText(order.order_status) }}
          </span>
        </div>
      </div>

      <!-- Order Info Card -->
      <div class="info-card">
        <div class="info-row">
          <span class="label">주문번호</span>
          <span class="value">{{ order.order_number }}</span>
        </div>
        <div class="info-row">
          <span class="label">주문일시</span>
          <span class="value">{{ formatDateTime(order.created_at) }}</span>
        </div>
        <div v-if="order.paid_at" class="info-row">
          <span class="label">결제일시</span>
          <span class="value">{{ formatDateTime(order.paid_at) }}</span>
        </div>
        <div class="info-row">
          <span class="label">결제상태</span>
          <span class="value">{{ getPaymentStatusText(order.payment_status) }}</span>
        </div>
      </div>

      <!-- Order Items Section -->
      <section class="section">
        <h3 class="section-title">주문 상품</h3>
        <div class="order-items">
          <div
            v-for="item in order.items"
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
              <p class="item-price">{{ formatPrice(item.price) }} × {{ item.quantity }}개</p>
            </div>
            <div class="item-total">
              {{ formatPrice(item.total_price) }}
            </div>
          </div>
        </div>
      </section>

      <!-- Shipping Info Section -->
      <section class="section">
        <h3 class="section-title">배송 정보</h3>
        <div class="shipping-info">
          <div class="info-row">
            <span class="label">받는 사람</span>
            <span class="value">{{ order.recipient_name }}</span>
          </div>
          <div class="info-row">
            <span class="label">연락처</span>
            <span class="value">{{ order.phone }}</span>
          </div>
          <div class="info-row">
            <span class="label">배송 주소</span>
            <span class="value">
              ({{ order.postal_code }}) {{ order.address }}<br>
              {{ order.address_detail }}
            </span>
          </div>
          <div v-if="order.delivery_request" class="info-row">
            <span class="label">배송 요청사항</span>
            <span class="value">{{ order.delivery_request }}</span>
          </div>
        </div>
      </section>

      <!-- Payment Summary Section -->
      <section class="section">
        <h3 class="section-title">결제 정보</h3>
        <div class="payment-summary">
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
          <div class="summary-divider"></div>
          <div class="summary-row total">
            <span>최종 결제 금액</span>
            <span class="total-amount">{{ formatPrice(order.total_amount) }}</span>
          </div>
          <div class="payment-method">
            <span class="label">결제 수단</span>
            <span class="value">즉시 결제 (MVP)</span>
          </div>
        </div>
      </section>

      <!-- Order Actions -->
      <div class="order-actions">
        <button
          v-if="canCancelOrder(order)"
          @click="handleCancelOrder"
          class="btn-cancel"
          :disabled="cancelling"
        >
          <span v-if="cancelling">취소 중...</span>
          <span v-else>주문 취소</span>
        </button>

        <button
          v-if="canConfirmDelivery(order)"
          @click="handleConfirmDelivery"
          class="btn-confirm"
          :disabled="confirming"
        >
          <span v-if="confirming">확인 중...</span>
          <span v-else>배송 확인</span>
        </button>
      </div>

      <!-- Order Timeline -->
      <section class="section">
        <h3 class="section-title">주문 진행 상황</h3>
        <div class="timeline">
          <div
            class="timeline-item"
            :class="{ active: isStatusActive('pending') }"
          >
            <div class="timeline-marker"></div>
            <div class="timeline-content">
              <h4>주문 접수</h4>
              <p v-if="order.created_at">{{ formatDateTime(order.created_at) }}</p>
            </div>
          </div>

          <div
            class="timeline-item"
            :class="{ active: isStatusActive('paid') }"
          >
            <div class="timeline-marker"></div>
            <div class="timeline-content">
              <h4>결제 완료</h4>
              <p v-if="order.paid_at">{{ formatDateTime(order.paid_at) }}</p>
            </div>
          </div>

          <div
            class="timeline-item"
            :class="{ active: isStatusActive('processing') }"
          >
            <div class="timeline-marker"></div>
            <div class="timeline-content">
              <h4>상품 준비중</h4>
              <p v-if="order.order_status === 'processing'">처리 중</p>
            </div>
          </div>

          <div
            class="timeline-item"
            :class="{ active: isStatusActive('shipped') }"
          >
            <div class="timeline-marker"></div>
            <div class="timeline-content">
              <h4>배송 시작</h4>
              <p v-if="order.order_status === 'shipped'">배송 중</p>
            </div>
          </div>

          <div
            class="timeline-item"
            :class="{ active: isStatusActive('delivered') }"
          >
            <div class="timeline-marker"></div>
            <div class="timeline-content">
              <h4>배송 완료</h4>
              <p v-if="order.order_status === 'delivered'">배송 완료</p>
            </div>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useOrdersStore } from '@/stores/orders'
import { formatPrice, DEFAULT_PRODUCT_IMAGE } from '@/types/product'

const route = useRoute()
const ordersStore = useOrdersStore()

const loading = ref(true)
const error = ref<string | null>(null)
const cancelling = ref(false)
const confirming = ref(false)
const order = ref<any>(null)

// Load order detail
const loadOrderDetail = async () => {
  loading.value = true
  error.value = null

  try {
    const orderId = Number(route.params.id)
    if (isNaN(orderId)) {
      error.value = '잘못된 주문 번호입니다.'
      return
    }

    const response = await ordersStore.loadOrder(orderId)
    order.value = response
  } catch (err: any) {
    console.error('주문 상세 로드 실패:', err)
    error.value = '주문 정보를 불러오는데 실패했습니다.'
  } finally {
    loading.value = false
  }
}

// Cancel order
const handleCancelOrder = async () => {
  if (!order.value) return

  const confirmed = confirm('주문을 취소하시겠습니까?')
  if (!confirmed) return

  cancelling.value = true

  try {
    await ordersStore.cancelOrder(order.value.id, '고객 요청')
    alert('주문이 취소되었습니다.')
    await loadOrderDetail()
  } catch (err: any) {
    console.error('주문 취소 실패:', err)
    alert(err.response?.data?.message || '주문 취소에 실패했습니다.')
  } finally {
    cancelling.value = false
  }
}

// Confirm delivery
const handleConfirmDelivery = async () => {
  if (!order.value) return

  const confirmed = confirm('배송을 확인하시겠습니까?')
  if (!confirmed) return

  confirming.value = true

  try {
    await ordersStore.confirmDelivery(order.value.id)
    alert('배송이 확인되었습니다.')
    await loadOrderDetail()
  } catch (err: any) {
    console.error('배송 확인 실패:', err)
    alert(err.response?.data?.message || '배송 확인에 실패했습니다.')
  } finally {
    confirming.value = false
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

// Check if status is active in timeline
const isStatusActive = (status: string): boolean => {
  if (!order.value) return false

  const statusOrder = ['pending', 'paid', 'processing', 'shipped', 'delivered']
  const currentIndex = statusOrder.indexOf(order.value.order_status)
  const checkIndex = statusOrder.indexOf(status)

  return checkIndex <= currentIndex
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

// Get payment status text
const getPaymentStatusText = (status: string): string => {
  const statusMap: Record<string, string> = {
    pending: '대기중',
    paid: '결제완료',
    failed: '실패',
    cancelled: '취소',
    refunded: '환불'
  }
  return statusMap[status] || status
}

// Format date time
const formatDateTime = (dateString: string): string => {
  const date = new Date(dateString)
  return date.toLocaleString('ko-KR', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// Handle image error
const handleImageError = (event: Event) => {
  const target = event.target as HTMLImageElement
  target.src = DEFAULT_PRODUCT_IMAGE
}

// Initialize
onMounted(() => {
  loadOrderDetail()
})
</script>

<style scoped>
.order-detail-page {
  max-width: 100%;
}

/* Loading & Error States */
.loading-state,
.error-state {
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

.btn-back {
  display: inline-block;
  padding: 0.75rem 1.5rem;
  background: #00a86b;
  color: white;
  text-decoration: none;
  border-radius: 6px;
  transition: background 0.2s;
}

.btn-back:hover {
  background: #008c5a;
}

/* Page Header */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
  padding-bottom: 1rem;
  border-bottom: 2px solid #f0f0f0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.btn-back-link {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  color: #666;
  text-decoration: none;
  font-size: 0.9375rem;
  font-weight: 600;
  transition: color 0.2s;
}

.btn-back-link svg {
  width: 20px;
  height: 20px;
}

.btn-back-link:hover {
  color: #00a86b;
}

.page-title {
  font-size: 1.75rem;
  font-weight: 700;
  color: #1a1a1a;
}

.status-badge {
  padding: 0.5rem 1rem;
  border-radius: 12px;
  font-size: 0.875rem;
  font-weight: 700;
}

.status-pending { background: #ffc107; color: #000; }
.status-paid { background: #28a745; color: white; }
.status-processing { background: #007bff; color: white; }
.status-shipped { background: #17a2b8; color: white; }
.status-delivered { background: #6c757d; color: white; }
.status-cancelled { background: #dc3545; color: white; }
.status-refunded { background: #e83e8c; color: white; }

/* Info Card */
.info-card {
  padding: 1.5rem;
  background: #f8f9fa;
  border-radius: 8px;
  margin-bottom: 2rem;
}

.info-row {
  display: flex;
  justify-content: space-between;
  padding: 0.75rem 0;
  border-bottom: 1px solid #e9ecef;
}

.info-row:last-child {
  border-bottom: none;
}

.info-row .label {
  font-size: 0.9375rem;
  color: #666;
  font-weight: 600;
}

.info-row .value {
  font-size: 0.9375rem;
  color: #1a1a1a;
  text-align: right;
}

/* Section */
.section {
  margin-bottom: 2rem;
  padding: 1.5rem;
  border: 1px solid #e9ecef;
  border-radius: 8px;
}

.section-title {
  font-size: 1.25rem;
  font-weight: 700;
  color: #1a1a1a;
  margin-bottom: 1.5rem;
  padding-bottom: 0.75rem;
  border-bottom: 2px solid #f0f0f0;
}

/* Order Items */
.order-items {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.order-item {
  display: grid;
  grid-template-columns: 80px 1fr auto;
  gap: 1rem;
  padding: 1rem;
  background: #f8f9fa;
  border-radius: 6px;
}

.item-image {
  width: 80px;
  height: 80px;
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
  font-size: 1rem;
  font-weight: 600;
  color: #1a1a1a;
  line-height: 1.4;
}

.item-price {
  font-size: 0.875rem;
  color: #666;
}

.item-total {
  text-align: right;
  font-size: 1.125rem;
  font-weight: 700;
  color: #1a1a1a;
}

/* Shipping Info */
.shipping-info {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

/* Payment Summary */
.payment-summary {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.summary-row {
  display: flex;
  justify-content: space-between;
  font-size: 1rem;
  color: #333;
}

.summary-row.discount {
  color: #dc3545;
}

.summary-divider {
  height: 1px;
  background: #e9ecef;
  margin: 0.5rem 0;
}

.summary-row.total {
  font-size: 1.125rem;
  font-weight: 700;
  color: #1a1a1a;
  padding-top: 0.75rem;
}

.total-amount {
  font-size: 1.5rem;
  color: #00a86b;
}

.payment-method {
  display: flex;
  justify-content: space-between;
  padding-top: 1rem;
  margin-top: 1rem;
  border-top: 1px solid #e9ecef;
  font-size: 0.9375rem;
}

.payment-method .label {
  color: #666;
  font-weight: 600;
}

/* Order Actions */
.order-actions {
  display: flex;
  gap: 1rem;
  margin-bottom: 2rem;
}

.btn-cancel,
.btn-confirm {
  padding: 0.875rem 2rem;
  border: none;
  border-radius: 6px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-cancel {
  background: white;
  color: #dc3545;
  border: 2px solid #dc3545;
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

/* Timeline */
.timeline {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  padding-left: 2rem;
  position: relative;
}

.timeline::before {
  content: '';
  position: absolute;
  left: 0.75rem;
  top: 0.75rem;
  bottom: 0.75rem;
  width: 2px;
  background: #e9ecef;
}

.timeline-item {
  position: relative;
  padding-left: 2rem;
  opacity: 0.5;
}

.timeline-item.active {
  opacity: 1;
}

.timeline-marker {
  position: absolute;
  left: 0;
  top: 0.375rem;
  width: 1.5rem;
  height: 1.5rem;
  border-radius: 50%;
  background: #e9ecef;
  border: 3px solid white;
  box-shadow: 0 0 0 2px #e9ecef;
}

.timeline-item.active .timeline-marker {
  background: #00a86b;
  box-shadow: 0 0 0 2px #00a86b;
}

.timeline-content h4 {
  font-size: 1rem;
  font-weight: 700;
  color: #1a1a1a;
  margin-bottom: 0.25rem;
}

.timeline-content p {
  font-size: 0.875rem;
  color: #666;
}

/* Responsive */
@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 1rem;
  }

  .page-title {
    font-size: 1.5rem;
  }

  .order-actions {
    flex-direction: column;
    width: 100%;
  }

  .btn-cancel,
  .btn-confirm {
    width: 100%;
  }
}

@media (max-width: 480px) {
  .section {
    padding: 1rem;
  }

  .order-item {
    grid-template-columns: 60px 1fr;
    grid-template-areas:
      "image info"
      "total total";
  }

  .item-image {
    grid-area: image;
    width: 60px;
    height: 60px;
  }

  .item-info {
    grid-area: info;
  }

  .item-total {
    grid-area: total;
    text-align: left;
    padding-top: 0.75rem;
    margin-top: 0.75rem;
    border-top: 1px solid #e9ecef;
  }

  .timeline {
    padding-left: 1.5rem;
  }

  .timeline-item {
    padding-left: 1.5rem;
  }
}
</style>
