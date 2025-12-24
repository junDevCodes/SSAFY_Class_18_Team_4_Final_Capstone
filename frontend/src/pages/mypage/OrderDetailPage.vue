<template>
  <div class="order-detail-page">
    <!-- Loading State -->
    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>주문 정보를 불러오는 중입니다...</p>
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
          <span class="status-badge" :class="`status-${order.status}`">
            {{ getOrderStatusText(order.status) }}
          </span>
        </div>
      </div>

      <!-- Order Info Card -->
      <div class="info-card">
        <div class="info-row">
          <span class="label">주문번호</span>
          <span class="value">{{ order.order_no }}</span>
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
            <div class="item-info clickable" @click="goProductDetail(item)">
              <h4 class="item-name link">{{ item.product_name }}</h4>
              <p class="item-price link-sub">
                {{ formatPrice(item.unit_price) }} × {{ item.quantity }}개
              </p>
            </div>
            <div class="item-total">
              {{ formatPrice(item.total_price) }}
            </div>
            <div v-if="reviewMap[item.id]" class="item-actions">
              <button class="btn-review" @click="goEditReview(item, reviewMap[item.id])">
                리뷰 수정
              </button>
              <button
                class="btn-review danger"
                :disabled="deletingReviewId === reviewMap[item.id].id"
                @click="handleDeleteReview(reviewMap[item.id])"
              >
                {{ deletingReviewId === reviewMap[item.id].id ? '삭제 중...' : '리뷰 삭제' }}
              </button>
            </div>
            <div v-else-if="isReviewedToday(item)" class="item-actions">
              <button class="btn-review" disabled>
                이미 작성했어요!
              </button>
            </div>
            <div v-else-if="isReviewWriteAvailable(item)" class="item-actions">
              <button class="btn-review" @click="openWriteReview(item)">
                리뷰 작성
              </button>
            </div>
          </div>
        </div>
      </section>

      <!-- Shipping Info Section -->
      <section class="section">
        <h3 class="section-title">배송 정보</h3>
        <div class="shipping-info" v-if="order.shipment">
          <div class="info-row">
            <span class="label">받는 사람</span>
            <span class="value">{{ order.shipment.recipient_name }}</span>
          </div>
          <div class="info-row">
            <span class="label">연락처</span>
            <span class="value">{{ order.shipment.recipient_phone }}</span>
          </div>
          <div class="info-row">
            <span class="label">배송 주소</span>
            <span class="value">
              {{ order.shipment.address_full }}
            </span>
          </div>
          <div v-if="order.shipment.shipping_memo" class="info-row">
            <span class="label">배송 요청사항</span>
            <span class="value">{{ order.shipment.shipping_memo }}</span>
          </div>
        </div>
        <p v-else class="no-shipping">배송 정보가 없습니다.</p>
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
            <span class="value">
              <template v-if="order.payment">
                {{ order.payment.method_type }} ({{ getPaymentStatusText(order.payment_status) }})
              </template>
              <template v-else>
                정보 없음
              </template>
            </span>
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
          <span v-if="cancelling">취소 처리 중...</span>
          <span v-else>주문 취소</span>
        </button>

        <button
          v-if="canConfirmDelivery(order)"
          @click="handleConfirmDelivery"
          class="btn-confirm"
          :disabled="confirming"
        >
          <span v-if="confirming">확인 처리 중...</span>
          <span v-else>배송 완료 확인</span>
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
              <p v-if="order.status === 'processing'">처리 중</p>
            </div>
          </div>

          <div
            class="timeline-item"
            :class="{ active: isStatusActive('shipped') }"
          >
            <div class="timeline-marker"></div>
            <div class="timeline-content">
              <h4>배송 시작</h4>
              <p v-if="order.status === 'shipped'">배송 중</p>
            </div>
          </div>

          <div
            class="timeline-item"
            :class="{ active: isStatusActive('delivered') }"
          >
            <div class="timeline-marker"></div>
            <div class="timeline-content">
              <h4>배송 완료</h4>
              <p v-if="order.status === 'delivered'">배송 완료</p>
            </div>
          </div>
        </div>
      </section>
    </div>

    <ReviewWriteModal
      :open="writeModalOpen"
      :product-id="writeModalProductId"
      :order-item-id="writeModalOrderItemId"
      :product-name="writeModalProductName"
      @close="writeModalOpen = false"
      @submitted="handleReviewSubmitted"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useOrdersStore, type Order, type OrderItem } from '@/stores/orders'
import { formatPrice, DEFAULT_PRODUCT_IMAGE } from '@/types/product'
import { getOrderStatusText, getPaymentStatusText } from '@/utils/status'
import { reviewApi, type Review } from '@/services/api/reviews'
import ReviewWriteModal from '@/components/order/ReviewWriteModal.vue'

const route = useRoute()
const router = useRouter()
const ordersStore = useOrdersStore()

const loading = ref(true)
const error = ref<string | null>(null)
const cancelling = ref(false)
const confirming = ref(false)
const order = ref<Order | null>(null)
const myReviews = ref<Review[]>([])
const deletingReviewId = ref<number | null>(null)
const writeModalOpen = ref(false)
const writeModalProductId = ref<number | null>(null)
const writeModalOrderItemId = ref<number | null>(null)
const writeModalProductName = ref<string>('')
const reviewMap = computed<Record<number, Review>>(() => {
  const map: Record<number, Review> = {}
  myReviews.value.forEach((r) => {
    if (r.order_item) {
      map[r.order_item] = r
    }
  })
  return map
})
const isDelivered = computed(() => order.value?.status === 'delivered')

// 주문 상세 로드
const loadOrderDetail = async () => {
  loading.value = true
  error.value = null

  try {
    const orderId = Number(route.params.id)
    if (isNaN(orderId)) {
      error.value = '유효하지 않은 주문 번호입니다.'
      return
    }

    const response = await ordersStore.loadOrder(orderId)
    order.value = response
  } catch (err: any) {
    console.error('주문 상세 로드 실패:', err)
    error.value = '주문 정보를 불러오는 데 실패했습니다.'
  } finally {
    loading.value = false
  }
}

const loadMyReviews = async () => {
  try {
    const results: Review[] = []
    let page = 1
    let hasNext = true
    while (hasNext) {
      const data = await reviewApi.getMyReviews({ page, page_size: 100 })
      results.push(...data.results)
      hasNext = Boolean(data.next)
      page += 1
    }
    myReviews.value = results
  } catch (err: any) {
    console.error('리뷰 목록 로드 실패:', err)
  }
}

const getProductSlug = (item: OrderItem): string | number | null => {
  const productAny = (item as any).product
  if (productAny && typeof productAny === 'object') {
    return productAny.slug ?? productAny.id ?? null
  }
  if (typeof productAny === 'string' || typeof productAny === 'number') {
    return productAny
  }
  return null
}

const normalizeId = (value: unknown): number | null => {
  if (typeof value === 'number' && Number.isFinite(value)) return value
  if (typeof value === 'string') {
    const num = Number(value)
    if (Number.isFinite(num)) return num
  }
  return null
}

const getProductId = (item: OrderItem): number | null => {
  const anyItem = item as any
  // 직접 필드 우선
  const direct = normalizeId(anyItem.product_id)
  if (direct !== null) return direct

  const productAny = anyItem.product
  if (productAny && typeof productAny === 'object') {
    const fromObj = normalizeId((productAny as any).id) ?? normalizeId((productAny as any).product_id)
    if (fromObj !== null) return fromObj
  }

  return normalizeId(productAny)
}

const hasAnyReview = (productId: number) =>
  myReviews.value.some((r) => r.product === productId)

const isReviewedToday = (item: OrderItem) => {
  const productId = getProductId(item)
  if (!productId) return false
  return hasAnyReview(productId)
}

const goEditReview = (item: OrderItem, review: Review) => {
  const slug = getProductSlug(item)
  if (!slug) {
    alert('상품 정보를 찾을 수 없습니다.')
    return
  }
  router.push({
    name: 'product-detail',
    params: { slug },
    query: { tab: 'review', editReviewId: review.id },
  })
}

const goProductDetail = (item: OrderItem) => {
  const slug = getProductSlug(item)
  if (!slug) {
    alert('상품 정보를 찾을 수 없습니다.')
    return
  }
  router.push({ name: 'product-detail', params: { slug } })
}

const handleDeleteReview = async (review: Review) => {
  const confirmed = confirm('리뷰를 삭제하시겠습니까?')
  if (!confirmed) return
  deletingReviewId.value = review.id
  try {
    await reviewApi.deleteReview(review.id)
    myReviews.value = myReviews.value.filter((r) => r.id !== review.id)
    alert('리뷰가 삭제되었습니다.')
  } catch (err: any) {
    console.error('리뷰 삭제 실패:', err)
    alert(err?.response?.data?.detail || '리뷰 삭제에 실패했습니다.')
  } finally {
    deletingReviewId.value = null
  }
}

const isReviewWriteAvailable = (item: OrderItem) => {
  if (!isDelivered.value || !order.value) return false
  const productId = getProductId(item)
  if (!productId) return false
  if (hasAnyReview(productId)) return false
  return true
}

const openWriteReview = (item: OrderItem) => {
  if (!isReviewWriteAvailable(item)) return
  const productId = getProductId(item)
  if (!productId) {
    alert('상품 정보를 찾을 수 없습니다.')
    return
  }
  writeModalProductId.value = productId
  writeModalOrderItemId.value = item.id
  writeModalProductName.value = item.product_name
  writeModalOpen.value = true
}

const handleReviewSubmitted = (payload?: { message?: string; alreadyReviewed?: boolean }) => {
  if (payload?.message) alert(payload.message)
  writeModalOpen.value = false
  loadMyReviews()
}

// 주문 취소
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

// 배송 완료 확인
const handleConfirmDelivery = async () => {
  if (!order.value) return

  const confirmed = confirm('배송 완료를 확인하시겠습니까?')
  if (!confirmed) return

  confirming.value = true

  try {
    await ordersStore.confirmDelivery(order.value.id)
    alert('배송 완료가 확인되었습니다.')
    await loadOrderDetail()
  } catch (err: any) {
    console.error('배송 확인 실패:', err)
    alert(err.response?.data?.message || '배송 확인에 실패했습니다.')
  } finally {
    confirming.value = false
  }
}

// 주문 취소 가능 여부
const canCancelOrder = (order: Order): boolean => {
  return ['pending', 'paid', 'processing'].includes(order.status)
}

// 배송 완료 확인 가능 여부
const canConfirmDelivery = (order: Order): boolean => {
  return ['paid', 'shipped'].includes(order.status)
}

// 타임라인 상태 활성 여부
const isStatusActive = (status: string): boolean => {
  if (!order.value) return false

  const statusOrder = ['pending', 'paid', 'processing', 'shipped', 'delivered']
  const currentIndex = statusOrder.indexOf(order.value.status)
  const checkIndex = statusOrder.indexOf(status)

  return checkIndex <= currentIndex
}

// 날짜/시간 포맷
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

// 이미지 로딩 실패 처리
const handleImageError = (event: Event) => {
  const target = event.target as HTMLImageElement
  target.src = DEFAULT_PRODUCT_IMAGE
}

// 초기 로드
onMounted(() => {
  loadOrderDetail()
  loadMyReviews()
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
}

.btn-back-link svg {
  width: 20px;
  height: 20px;
}

.page-title {
  font-size: 1.75rem;
  font-weight: 700;
  color: #1a1a1a;
}

.header-right {
  display: flex;
  align-items: center;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.375rem 0.875rem;
  border-radius: 999px;
  font-size: 0.875rem;
  font-weight: 600;
  border: 1px solid transparent;
}

.status-pending {
  background: #fff3cd;
  color: #856404;
  border-color: #ffeeba;
}

.status-paid {
  background: #e6f4ff;
  color: #0b5ed7;
  border-color: #b6e0ff;
}

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

.item-name.link { color: #1a1a1a; }
.item-name.link:hover { color: #00a86b; text-decoration: underline; }
.item-price.link-sub { color: #666; }
.clickable { cursor: pointer; }

.item-total {
  text-align: right;
  font-size: 1.125rem;
  font-weight: 700;
  color: #1a1a1a;
}

.item-actions {
  display: flex;
  gap: 0.5rem;
  margin-left: 1rem;
}

.btn-review {
  padding: 0.35rem 0.75rem;
  border-radius: 8px;
  border: 1px solid #d1d5db;
  background: #fff;
  font-size: 0.8125rem;
  font-weight: 600;
  cursor: pointer;
}

.btn-review:hover:not(:disabled) {
  border-color: #00a86b;
  color: #00a86b;
}

.btn-review.danger {
  border-color: #f5c2c7;
  color: #dc3545;
}

.btn-review.danger:hover:not(:disabled) {
  background: #dc3545;
  color: #fff;
}

.btn-review:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Shipping Info */
.shipping-info {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.no-shipping {
  font-size: 0.9375rem;
  color: #666;
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
