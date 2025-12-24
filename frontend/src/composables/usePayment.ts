/**
 * 결제 관리 컴포저블 (토스페이먼츠 결제위젯 v2 연동)
 *
 * 토스페이먼츠 결제위젯 SDK v2를 사용하여 결제 UI를 렌더링하고 결제를 처리합니다.
 * - 데모 모드: 토스페이먼츠 테스트 키 사용 (실제 결제 없음)
 * - 프로덕션 모드: 실제 라이브 키 사용
 *
 * 공식 문서: https://docs.tosspayments.com/guides/v2/payment-widget/integration
 */
import { ref, computed, type Ref } from 'vue'
import { paymentsAPI } from '@/services/api'
import type {
  PaymentPrepareRequest,
  PaymentPrepareResponse,
  PaymentConfirmRequest,
  PaymentConfirmResponse,
  TossPaymentWidgets,
} from '@/types/payment'

/**
 * 랜덤 문자열 생성 (고객 키용)
 */
function generateRandomString(): string {
  return Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15)
}

/**
 * 결제 관리 컴포저블
 */
export function usePayment() {
  // ========== 상태 ==========
  const loading = ref(false)
  const error = ref<string | null>(null)
  const paymentData = ref<PaymentPrepareResponse | null>(null)
  const confirmResult = ref<PaymentConfirmResponse | null>(null)

  // 결제 위젯 인스턴스 (v2)
  const widgets: Ref<TossPaymentWidgets | null> = ref(null)

  // ========== 계산된 속성 ==========

  /** 데모 모드 여부 */
  const isDemo = computed(() => paymentData.value?.is_demo ?? true)

  /** 결제 금액 */
  const amount = computed(() => paymentData.value?.amount ?? 0)

  /** 주문명 */
  const orderName = computed(() => paymentData.value?.order_name ?? '')

  /** 토스 주문 ID */
  const tossOrderId = computed(() => paymentData.value?.toss_order_id ?? '')

  /** 위젯이 렌더링되었는지 여부 */
  const isWidgetReady = computed(() => widgets.value !== null)

  // ========== 메서드 ==========

  /**
   * 결제 준비 (주문 생성 + PG 초기화)
   * 장바구니 기반으로 주문을 생성하고 토스 SDK 초기화 데이터를 받습니다.
   *
   * @param orderData 주문 정보 (배송지, 수령인 등)
   * @returns 결제 준비 응답 또는 null (실패 시)
   */
  const preparePayment = async (
    orderData: PaymentPrepareRequest
  ): Promise<PaymentPrepareResponse | null> => {
    loading.value = true
    error.value = null

    try {
      const response = await paymentsAPI.prepare(orderData)
      paymentData.value = response.data
      return response.data
    } catch (err: any) {
      const message =
        err.response?.data?.error ||
        err.response?.data?.message ||
        err.message ||
        '결제 준비 중 오류가 발생했습니다.'
      error.value = message
      console.error('[usePayment] 결제 준비 실패:', err)
      return null
    } finally {
      loading.value = false
    }
  }

  /**
   * 결제 위젯 초기화 및 렌더링 (v2 SDK)
   * 결제 수단 선택 UI와 약관 동의 UI를 렌더링합니다.
   *
   * @param paymentMethodSelector 결제 수단 UI를 렌더링할 CSS 선택자
   * @param agreementSelector 약관 동의 UI를 렌더링할 CSS 선택자
   */
  const renderPaymentWidget = async (
    paymentMethodSelector: string = '#payment-method',
    agreementSelector: string = '#agreement'
  ): Promise<boolean> => {
    if (!paymentData.value) {
      error.value = '결제 정보가 없습니다. 먼저 preparePayment를 호출해주세요.'
      return false
    }

    // TossPayments SDK 로드 확인
    if (typeof window.TossPayments === 'undefined') {
      error.value = '토스페이먼츠 SDK가 로드되지 않았습니다.'
      console.error('[usePayment] TossPayments SDK not found')
      return false
    }

    loading.value = true
    error.value = null

    try {
      // 1. 토스페이먼츠 SDK 초기화 (동기 호출 - 공식 예제 방식)
      const tossPayments = window.TossPayments(paymentData.value.client_key)

      // 2. 고객 키 결정 (회원이면 고유 ID, 비회원이면 ANONYMOUS)
      const customerKey = paymentData.value.customer_email
        ? `user_${generateRandomString()}`
        : window.TossPayments.ANONYMOUS

      // 3. 결제위젯 인스턴스 생성
      widgets.value = tossPayments.widgets({ customerKey })

      // 4. 결제 금액 설정
      await widgets.value.setAmount({
        currency: 'KRW',
        value: paymentData.value.amount,
      })

      // 5. 결제 수단 UI + 약관 동의 UI 병렬 렌더링 (공식 예제 방식)
      await Promise.all([
        widgets.value.renderPaymentMethods({
          selector: paymentMethodSelector,
          variantKey: 'DEFAULT',
        }),
        widgets.value.renderAgreement({
          selector: agreementSelector,
          variantKey: 'AGREEMENT',
        }),
      ])

      return true
    } catch (err: any) {
      error.value = err.message || '결제 위젯 렌더링 중 오류가 발생했습니다.'
      console.error('[usePayment] 결제 위젯 렌더링 실패:', err)
      return false
    } finally {
      loading.value = false
    }
  }

  /**
   * 결제 요청
   * 렌더링된 결제 위젯으로 결제를 요청합니다.
   * 성공/실패 시 지정된 URL로 리다이렉트됩니다.
   */
  const requestPayment = async (): Promise<void> => {
    if (!widgets.value || !paymentData.value) {
      error.value = '결제 위젯이 초기화되지 않았습니다.'
      return
    }

    loading.value = true
    error.value = null

    try {
      const successUrl = paymentData.value.success_url || `${window.location.origin}/checkout/success`
      const failUrl = paymentData.value.fail_url || `${window.location.origin}/checkout/fail`

      await widgets.value.requestPayment({
        orderId: paymentData.value.toss_order_id,
        orderName: paymentData.value.order_name,
        successUrl,
        failUrl,
        customerEmail: paymentData.value.customer_email,
        customerName: paymentData.value.customer_name,
      })
    } catch (err: any) {
      // 사용자 취소 시
      if (err.code === 'USER_CANCEL' || err.message?.includes('취소')) {
        error.value = '결제가 취소되었습니다.'
      } else {
        error.value = err.message || '결제 진행 중 오류가 발생했습니다.'
      }
      console.error('[usePayment] 결제 요청 실패:', err)
    } finally {
      loading.value = false
    }
  }

  /**
   * 결제 승인
   * 토스 SDK 리다이렉트 후 호출합니다.
   *
   * @param data 결제 승인 요청 데이터 (paymentKey, orderId, amount)
   * @returns 결제 승인 응답 또는 null (실패 시)
   */
  const confirmPayment = async (
    data: PaymentConfirmRequest
  ): Promise<PaymentConfirmResponse | null> => {
    loading.value = true
    error.value = null

    try {
      const response = await paymentsAPI.confirm(data)
      confirmResult.value = response.data

      if (!response.data.success) {
        error.value = response.data.error_message || '결제 승인에 실패했습니다.'
        return null
      }

      return response.data
    } catch (err: any) {
      const message =
        err.response?.data?.error ||
        err.response?.data?.error_message ||
        err.message ||
        '결제 승인 중 오류가 발생했습니다.'
      error.value = message
      console.error('[usePayment] 결제 승인 실패:', err)
      return null
    } finally {
      loading.value = false
    }
  }

  /**
   * 결제 취소
   *
   * @param paymentId 결제 ID
   * @param cancelReason 취소 사유
   * @returns 성공 여부
   */
  const cancelPayment = async (
    paymentId: number,
    cancelReason: string
  ): Promise<boolean> => {
    loading.value = true
    error.value = null

    try {
      const response = await paymentsAPI.cancel(paymentId, cancelReason)
      return response.data.success
    } catch (err: any) {
      const message =
        err.response?.data?.error ||
        err.response?.data?.error_message ||
        err.message ||
        '결제 취소 중 오류가 발생했습니다.'
      error.value = message
      console.error('[usePayment] 결제 취소 실패:', err)
      return false
    } finally {
      loading.value = false
    }
  }

  /**
   * 상태 초기화
   */
  const reset = () => {
    loading.value = false
    error.value = null
    paymentData.value = null
    confirmResult.value = null
    widgets.value = null
  }

  return {
    // 상태
    loading,
    error,
    paymentData,
    confirmResult,

    // 계산된 속성
    isDemo,
    amount,
    orderName,
    tossOrderId,
    isWidgetReady,

    // 메서드
    preparePayment,
    renderPaymentWidget,
    requestPayment,
    confirmPayment,
    cancelPayment,
    reset,
  }
}
