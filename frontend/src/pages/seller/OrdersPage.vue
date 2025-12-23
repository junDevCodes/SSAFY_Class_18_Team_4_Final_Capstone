<template>
  <div class="seller-orders-page">
    <div class="container">
      <div class="page-header">
        <div>
          <h1 class="page-title">주문 관리</h1>
          <p class="page-description">
            주문 상태를 확인하고 배송 단계를 한눈에 관리하세요. 배송완료는 구매자 확인 시 자동 반영됩니다.
          </p>
        </div>
        <div class="summary-cards">
          <div class="summary-card">
            <p class="label">주문확인중</p>
            <p class="value">{{ summaryCount('pending') }}</p>
          </div>
          <div class="summary-card">
            <p class="label">배송출고</p>
            <p class="value">{{ summaryCount('paid') }}</p>
          </div>
          <div class="summary-card">
            <p class="label">배송중</p>
            <p class="value">{{ summaryCount('shipping') }}</p>
          </div>
          <div class="summary-card accent">
            <p class="label">배송완료</p>
            <p class="value">{{ summaryCount('delivered') }}</p>
          </div>
        </div>
      </div>

      <div class="tabs">
        <div class="tab-buttons">
          <button
            v-for="tab in tabs"
            :key="tab.key"
            :class="['tab-btn', { active: statusFilter === tab.key }]"
            @click="switchTab(tab.key)"
          >
            {{ tab.label }}
            <span class="tab-badge">{{ summaryCount(tab.key) }}</span>
          </button>
        </div>
        <div class="tab-hint">
          배송완료는 구매자가 확인 버튼을 누르면 자동 표시됩니다.
        </div>
      </div>

      <div v-if="loading" class="state-card">
        <div class="spinner"></div>
        <p>주문을 불러오는 중입니다...</p>
      </div>

      <div v-else-if="error" class="state-card error">
        <p class="error-message">{{ error }}</p>
        <button class="btn" @click="loadOrders">다시 시도</button>
      </div>

      <div v-else-if="orders.length === 0" class="state-card empty">
        <div class="empty-icon">📦</div>
        <h3>해당 상태의 주문이 없습니다.</h3>
        <p>다른 탭을 확인하거나 새 주문이 들어오면 여기서 관리할 수 있어요.</p>
      </div>

      <div v-else class="orders-grid">
        <div
          v-for="item in orders"
          :key="item.id"
          class="order-card"
        >
          <div class="order-card__header">
            <div class="order-meta">
              <p class="order-number">주문번호 {{ item.order_no }}</p>
              <p class="order-date">{{ formatDate(item.order_created_at) }}</p>
            </div>
            <div class="status-group">
              <span class="status-chip" :class="`status-${item.status}`">
                {{ statusLabel(item.status) }}
              </span>
              <span v-if="item.order_status_display" class="sub-chip">
                주문 {{ item.order_status_display }}
              </span>
            </div>
          </div>

          <div class="order-card__body">
            <div class="product">
              <div class="thumb">
                <img
                  :src="item.product_image || DEFAULT_PRODUCT_IMAGE"
                  :alt="item.product_name"
                  @error="handleImageError"
                />
              </div>
              <div class="product-info">
                <h3 class="product-name">{{ item.product_name }}</h3>
                <p class="product-sub">
                  {{ item.quantity }}개 · {{ formatPrice(item.unit_price || 0) }}
                </p>
              </div>
            </div>

            <div class="info-grid">
              <div class="info-block">
                <p class="label">수취인</p>
                <p class="value">{{ item.buyer_name || '정보 없음' }}</p>
                <p class="sub">{{ item.buyer_phone || '' }}</p>
              </div>
              <div class="info-block">
                <p class="label">배송지</p>
                <p class="value">{{ item.shipping_address || '주소 없음' }}</p>
                <p v-if="item.shipping_memo" class="sub">{{ item.shipping_memo }}</p>
              </div>
              <div class="info-block">
                <p class="label">배송 정보</p>
                <p class="value">{{ item.courier || '택배사 미입력' }}</p>
                <p class="sub">
                  {{ item.tracking_no ? `송장번호 ${item.tracking_no}` : '송장번호 없음' }}
                </p>
              </div>
              <div class="info-block total">
                <p class="label">총 금액</p>
                <p class="total-price">{{ formatPrice(item.total_price || 0) }}</p>
              </div>
            </div>
          </div>

          <div class="order-card__footer">
            <div v-if="item.status === 'delivered'" class="status-complete">
              배송완료 처리된 주문입니다.
            </div>
            <div v-else class="status-control">
              <p class="label">상태 변경</p>
              <div class="control-row">
                <select v-model="statusDraft[item.id]" class="select">
                  <option
                    v-for="opt in statusOptions"
                    :key="opt.value"
                    :value="opt.value"
                  >
                    {{ opt.label }}
                  </option>
                </select>
                <button
                  class="btn primary"
                  :disabled="updatingId === item.id || statusDraft[item.id] === item.status"
                  @click="handleStatusUpdate(item)"
                >
                  <span v-if="updatingId === item.id">변경 중...</span>
                  <span v-else>변경하기</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { sellerOrdersAPI } from '@/services/api'
import { formatPrice, DEFAULT_PRODUCT_IMAGE } from '@/types/product'

interface SellerOrderItem {
  id: number
  order_id: number
  order_no: string
  order_status: string
  order_status_display?: string
  order_created_at?: string
  product_name: string
  product_image?: string | null
  quantity: number
  unit_price: number
  discount_amount: number
  total_price: number
  status: string
  status_display: string
  buyer_name?: string | null
  buyer_phone?: string | null
  shipping_address?: string | null
  shipping_memo?: string | null
  courier?: string | null
  tracking_no?: string | null
}

const tabs = [
  { key: 'pending', label: '주문확인중' },
  { key: 'paid', label: '배송출고' },
  { key: 'shipping', label: '배송중' },
  { key: 'delivered', label: '배송완료' },
]

const statusOptions = [
  { value: 'pending', label: '주문확인중' },
  { value: 'paid', label: '배송출고' },
  { value: 'shipping', label: '배송중' },
]

const statusDraft = ref<Record<number, string>>({})
const orders = ref<SellerOrderItem[]>([])
const summary = ref<Record<string, number>>({})
const statusFilter = ref<string>('pending')
const loading = ref(true)
const error = ref<string | null>(null)
const updatingId = ref<number | null>(null)

const statusLabel = (status: string) => {
  const map: Record<string, string> = {
    pending: '주문확인중',
    paid: '배송출고',
    shipping: '배송중',
    delivered: '배송완료',
    cancelled: '취소됨',
    refunded: '환불됨',
  }
  return map[status] || status
}

const summaryCount = (status: string) => summary.value[status] ?? 0

const switchTab = (status: string) => {
  if (statusFilter.value === status) return
  statusFilter.value = status
  loadOrders()
}

const formatDate = (value?: string) => {
  if (!value) return ''
  return new Date(value).toLocaleString('ko-KR', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const normalizeResults = (data: any): SellerOrderItem[] => {
  if (!data) return []
  if (Array.isArray(data)) return data as SellerOrderItem[]
  if (Array.isArray(data.results)) return data.results as SellerOrderItem[]
  return []
}

const loadSummary = async () => {
  try {
    const { data } = await sellerOrdersAPI.getSummary()
    summary.value = data || {}
  } catch (err) {
    console.error('요약 불러오기 실패', err)
  }
}

const loadOrders = async () => {
  loading.value = true
  error.value = null

  try {
    const response = await sellerOrdersAPI.getOrderItems({
      status: statusFilter.value === 'delivered' ? 'delivered' : statusFilter.value,
      page_size: 30,
    })
    const list = normalizeResults(response.data)
    orders.value = list
    statusDraft.value = list.reduce<Record<number, string>>((acc, item) => {
      acc[item.id] = item.status
      return acc
    }, {})
  } catch (err: any) {
    console.error('주문 목록 로드 실패', err)
    error.value = err?.response?.data?.detail || '주문을 불러오지 못했습니다.'
  } finally {
    loading.value = false
  }
}

const handleStatusUpdate = async (item: SellerOrderItem) => {
  const nextStatus = statusDraft.value[item.id] || item.status
  if (nextStatus === item.status) return

  updatingId.value = item.id
  try {
    await sellerOrdersAPI.updateStatus(item.id, nextStatus)
    await Promise.all([loadOrders(), loadSummary()])
  } catch (err: any) {
    console.error('상태 변경 실패', err)
    alert(err?.response?.data?.message || '상태 변경에 실패했습니다.')
  } finally {
    updatingId.value = null
  }
}

const handleImageError = (event: Event) => {
  const target = event.target as HTMLImageElement
  target.src = DEFAULT_PRODUCT_IMAGE
}

onMounted(() => {
  loadSummary()
  loadOrders()
})
</script>

<style scoped>
.seller-orders-page {
  min-height: calc(100vh - 4rem);
  background: linear-gradient(180deg, #f7fbf8 0%, #ffffff 60%);
  padding: 3rem 0;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1rem;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1.5rem;
  margin-bottom: 1.5rem;
}

.page-title {
  font-size: 2rem;
  font-weight: 700;
  color: #0f172a;
  margin-bottom: 0.35rem;
}

.page-description {
  color: #4b5563;
  font-size: 0.95rem;
}

.summary-cards {
  display: grid;
  grid-template-columns: repeat(4, minmax(120px, 1fr));
  gap: 0.75rem;
}

.summary-card {
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 0.85rem 1rem;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
}

.summary-card.accent {
  border-color: #00a86b;
  box-shadow: 0 6px 18px rgba(0, 168, 107, 0.15);
}

.summary-card .label {
  color: #6b7280;
  font-size: 0.85rem;
}

.summary-card .value {
  font-size: 1.5rem;
  font-weight: 700;
  color: #0f172a;
}

.tabs {
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 0.85rem 1rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.tab-buttons {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.tab-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.6rem 0.9rem;
  border-radius: 10px;
  border: 1px solid #d1d5db;
  background: #f9fafb;
  color: #111827;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.tab-btn.active {
  border-color: #00a86b;
  background: #e8f6ef;
  color: #0f172a;
}

.tab-btn:hover {
  border-color: #00a86b;
}

.tab-badge {
  min-width: 28px;
  padding: 0.1rem 0.5rem;
  border-radius: 999px;
  background: #0ea5e9;
  color: #fff;
  font-size: 0.8rem;
  text-align: center;
}

.tab-hint {
  color: #6b7280;
  font-size: 0.9rem;
}

.state-card {
  background: #ffffff;
  border: 1px dashed #d1d5db;
  border-radius: 12px;
  padding: 2rem;
  text-align: center;
  color: #374151;
}

.state-card.error {
  border-color: #f87171;
  color: #b91c1c;
}

.state-card.empty .empty-icon {
  font-size: 2rem;
  margin-bottom: 0.75rem;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #e5e7eb;
  border-top-color: #00a86b;
  border-radius: 999px;
  margin: 0 auto 0.75rem;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.65rem 1.1rem;
  border-radius: 10px;
  border: 1px solid #d1d5db;
  background: #fff;
  cursor: pointer;
  font-weight: 600;
}

.btn.primary {
  background: #00a86b;
  color: #fff;
  border-color: #00a86b;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.orders-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 1rem;
}

.order-card {
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.04);
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding: 1rem;
}

.order-card__header {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: center;
  border-bottom: 1px solid #f3f4f6;
  padding-bottom: 0.75rem;
}

.order-number {
  font-weight: 700;
  color: #0f172a;
}

.order-date {
  color: #6b7280;
  font-size: 0.9rem;
}

.status-group {
  display: flex;
  gap: 0.4rem;
  align-items: center;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.status-chip {
  padding: 0.3rem 0.75rem;
  border-radius: 999px;
  font-size: 0.85rem;
  font-weight: 700;
  color: #0f172a;
  background: #e5f5ed;
  border: 1px solid #bbf7d0;
}

.status-pending { background: #fff7ed; border-color: #fed7aa; color: #9a3412; }
.status-paid { background: #e0f2fe; border-color: #bae6fd; color: #0b4f6c; }
.status-shipping { background: #e0f7fa; border-color: #b2ebf2; color: #055160; }
.status-delivered { background: #dcfce7; border-color: #bbf7d0; color: #166534; }
.status-cancelled,
.status-refunded { background: #fee2e2; border-color: #fecdd3; color: #b91c1c; }

.sub-chip {
  padding: 0.25rem 0.6rem;
  border-radius: 999px;
  background: #f3f4f6;
  color: #4b5563;
  font-size: 0.8rem;
}

.order-card__body {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.product {
  display: flex;
  gap: 0.75rem;
  align-items: center;
}

.thumb {
  width: 72px;
  height: 72px;
  border-radius: 12px;
  overflow: hidden;
  background: #f3f4f6;
  border: 1px solid #e5e7eb;
  flex-shrink: 0;
}

.thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.product-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.product-name {
  font-size: 1rem;
  font-weight: 700;
  color: #0f172a;
}

.product-sub {
  color: #6b7280;
  font-size: 0.9rem;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 0.75rem;
}

.info-block {
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 0.75rem;
}

.info-block .label {
  color: #6b7280;
  font-size: 0.85rem;
  margin-bottom: 0.2rem;
}

.info-block .value {
  color: #0f172a;
  font-weight: 700;
}

.info-block .sub {
  color: #6b7280;
  font-size: 0.9rem;
}

.info-block.total {
  background: linear-gradient(135deg, #f0fdf4 0%, #e0fbe2 100%);
  border-color: #bbf7d0;
}

.total-price {
  font-size: 1.25rem;
  color: #00a86b;
  font-weight: 800;
}

.order-card__footer {
  border-top: 1px solid #f3f4f6;
  padding-top: 0.75rem;
}

.status-control .label {
  color: #4b5563;
  margin-bottom: 0.35rem;
}

.control-row {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  flex-wrap: wrap;
}

.select {
  padding: 0.6rem 0.75rem;
  border-radius: 10px;
  border: 1px solid #d1d5db;
  min-width: 160px;
  background: #fff;
  font-weight: 600;
}

.status-complete {
  color: #166534;
  background: #ecfdf3;
  border: 1px solid #bbf7d0;
  border-radius: 10px;
  padding: 0.75rem;
  font-weight: 600;
}

.error-message {
  font-weight: 700;
}

@media (max-width: 960px) {
  .page-header {
    flex-direction: column;
  }

  .summary-cards {
    grid-template-columns: repeat(2, minmax(140px, 1fr));
  }
}

@media (max-width: 640px) {
  .tabs {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.75rem;
  }

  .orders-grid {
    grid-template-columns: 1fr;
  }

  .page-title {
    font-size: 1.5rem;
  }
}
</style>
