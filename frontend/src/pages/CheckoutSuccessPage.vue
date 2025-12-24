<template>
  <div class="checkout-success-page">
    <div class="container">
      <!-- 로딩 상태 (결제 승인 처리 중) -->
      <div v-if="loading" class="loading-state">
        <div class="spinner"></div>
        <h2>결제를 확인하고 있습니다...</h2>
        <p>잠시만 기다려주세요.</p>
      </div>

      <!-- 에러 상태 -->
      <div v-else-if="error" class="error-state">
        <div class="error-icon">❌</div>
        <h2>결제 확인 중 오류가 발생했습니다</h2>
        <p class="error-message">{{ error }}</p>
        <div class="actions">
          <router-link to="/mypage/orders" class="btn-secondary">주문 내역 확인</router-link>
          <router-link to="/" class="btn-primary">홈으로 이동</router-link>
        </div>
      </div>

      <!-- 성공 상태 -->
      <div v-else class="success-state">
        <div class="success-icon">✅</div>
        <h1>결제가 완료되었습니다!</h1>
        <p class="success-message">주문이 성공적으로 접수되었습니다.</p>

        <div class="order-info">
          <div class="info-row">
            <span class="label">주문번호</span>
            <span class="value">{{ orderNo }}</span>
          </div>
          <div class="info-row">
            <span class="label">결제금액</span>
            <span class="value amount">{{ formatPrice(amount) }}</span>
          </div>
          <div v-if="method" class="info-row">
            <span class="label">결제수단</span>
            <span class="value">{{ method }}</span>
          </div>
        </div>

        <div class="actions">
          <router-link
            v-if="orderId"
            :to="`/mypage/orders/${orderId}`"
            class="btn-primary"
          >
            주문 상세 보기
          </router-link>
          <router-link to="/mypage/orders" class="btn-secondary">주문 내역</router-link>
          <router-link to="/" class="btn-outline">쇼핑 계속하기</router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { usePayment } from '@/composables/usePayment'
import { useCartStore } from '@/stores/cart'
import { formatPrice } from '@/types/product'

const route = useRoute()
const cartStore = useCartStore()
const { confirmPayment } = usePayment()

// 상태
const loading = ref(true)
const error = ref<string | null>(null)

// 결제 정보
const orderId = ref<number | null>(null)
const orderNo = ref('')
const amount = ref(0)
const method = ref('')

onMounted(async () => {
  // URL 쿼리 파라미터에서 결제 정보 추출
  const paymentKey = route.query.paymentKey as string
  const tossOrderId = route.query.orderId as string
  const paymentAmount = Number(route.query.amount)

  // 이미 처리된 성공 결과 (데모 모드에서 직접 전달된 경우)
  if (route.query.orderNo) {
    orderNo.value = route.query.orderNo as string
    amount.value = paymentAmount || 0
    method.value = (route.query.method as string) || ''
    loading.value = false

    // 장바구니 비우기
    await cartStore.clearCart()
    return
  }

  // 토스 SDK 리다이렉트로 온 경우 - 결제 승인 필요
  if (paymentKey && tossOrderId && paymentAmount) {
    try {
      const result = await confirmPayment({
        paymentKey,
        orderId: tossOrderId,
        amount: paymentAmount,
      })

      if (result?.success) {
        orderId.value = result.order_id || null
        orderNo.value = result.order_no || ''
        amount.value = result.amount || paymentAmount
        method.value = result.method || ''

        // 장바구니 비우기
        await cartStore.clearCart()
      } else {
        error.value = result?.error_message || '결제 승인에 실패했습니다.'
      }
    } catch (err: any) {
      error.value = err.message || '결제 처리 중 오류가 발생했습니다.'
    }
  } else {
    // 필수 파라미터 누락
    error.value = '결제 정보가 올바르지 않습니다.'
  }

  loading.value = false
})
</script>

<style scoped>
.checkout-success-page {
  min-height: calc(100vh - 160px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  background: #f8f9fa;
}

.container {
  max-width: 600px;
  width: 100%;
}

/* 로딩 상태 */
.loading-state {
  text-align: center;
  padding: 3rem 2rem;
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.loading-state h2 {
  margin-top: 1.5rem;
  font-size: 1.5rem;
  color: #333;
}

.loading-state p {
  margin-top: 0.5rem;
  color: #666;
}

.spinner {
  width: 48px;
  height: 48px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #00a86b;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* 에러 상태 */
.error-state {
  text-align: center;
  padding: 3rem 2rem;
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.error-icon {
  font-size: 4rem;
  margin-bottom: 1rem;
}

.error-state h2 {
  font-size: 1.5rem;
  color: #dc3545;
  margin-bottom: 1rem;
}

.error-message {
  color: #666;
  margin-bottom: 2rem;
}

/* 성공 상태 */
.success-state {
  text-align: center;
  padding: 3rem 2rem;
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.success-icon {
  font-size: 5rem;
  margin-bottom: 1rem;
}

.success-state h1 {
  font-size: 2rem;
  color: #00a86b;
  margin-bottom: 0.5rem;
}

.success-message {
  color: #666;
  font-size: 1.125rem;
  margin-bottom: 2rem;
}

/* 주문 정보 */
.order-info {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 1.5rem;
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
  color: #666;
  font-weight: 500;
}

.info-row .value {
  color: #333;
  font-weight: 600;
}

.info-row .value.amount {
  color: #00a86b;
  font-size: 1.25rem;
}

/* 액션 버튼 */
.actions {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.btn-primary,
.btn-secondary,
.btn-outline {
  display: block;
  padding: 1rem;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: 600;
  text-decoration: none;
  text-align: center;
  transition: all 0.2s;
}

.btn-primary {
  background: #00a86b;
  color: white;
}

.btn-primary:hover {
  background: #008c5a;
}

.btn-secondary {
  background: #6c757d;
  color: white;
}

.btn-secondary:hover {
  background: #5a6268;
}

.btn-outline {
  background: white;
  color: #333;
  border: 2px solid #ddd;
}

.btn-outline:hover {
  border-color: #00a86b;
  color: #00a86b;
}

/* 반응형 */
@media (max-width: 480px) {
  .checkout-success-page {
    padding: 1rem;
  }

  .success-state,
  .loading-state,
  .error-state {
    padding: 2rem 1.5rem;
  }

  .success-state h1 {
    font-size: 1.5rem;
  }

  .success-icon {
    font-size: 4rem;
  }
}
</style>
