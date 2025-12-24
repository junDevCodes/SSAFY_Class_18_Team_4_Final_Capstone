/**
 * 결제 관련 타입 정의 (토스페이먼츠 PG 연동)
 */

// ========== 결제 수단 타입 ==========

/**
 * 결제 수단 유형
 */
export type PaymentMethodType = 'CARD' | 'VIRTUAL_ACCOUNT' | 'TRANSFER' | 'MOBILE'

/**
 * 결제 수단 정보
 */
export interface PaymentMethod {
  type: PaymentMethodType
  label: string
  description: string
  icon: string
}

/**
 * 사용 가능한 결제 수단 목록
 */
export const PAYMENT_METHODS: PaymentMethod[] = [
  {
    type: 'CARD',
    label: '신용/체크카드',
    description: '국내 모든 카드 결제 가능',
    icon: 'credit-card',
  },
  {
    type: 'VIRTUAL_ACCOUNT',
    label: '가상계좌',
    description: '무통장입금 (24시간 내 입금)',
    icon: 'building',
  },
  {
    type: 'TRANSFER',
    label: '계좌이체',
    description: '실시간 계좌이체',
    icon: 'wallet',
  },
  {
    type: 'MOBILE',
    label: '휴대폰 결제',
    description: '휴대폰 소액결제',
    icon: 'smartphone',
  },
]

// ========== 결제 준비 요청/응답 ==========

/**
 * 결제 준비 요청 데이터
 */
export interface PaymentPrepareRequest {
  /** 장바구니 ID 목록 (비어 있으면 전체 장바구니) */
  cart_item_ids?: number[]
  /** 수령인 이름 */
  recipient_name: string
  /** 수령인 전화번호 */
  recipient_phone: string
  /** 배송 주소 */
  shipping_address: string
  /** 배송 메모 */
  shipping_memo?: string
  /** 새 배송지 저장 여부 */
  save_address?: boolean
  /** 배송지 이름 */
  address_name?: string
}

/**
 * 결제 준비 응답 데이터
 */
export interface PaymentPrepareResponse {
  /** 내부 주문 ID */
  order_id: number
  /** 주문번호 */
  order_no: string
  /** 결제 ID */
  payment_id: number
  /** 토스 주문 ID (orderId) */
  toss_order_id: string
  /** 결제 금액 */
  amount: number
  /** 토스 클라이언트 키 */
  client_key: string
  /** 주문명 */
  order_name: string
  /** 데모 모드 여부 */
  is_demo: boolean
  /** 고객 이메일 */
  customer_email?: string
  /** 고객 이름 */
  customer_name?: string
  /** 결제 성공 시 리다이렉트 URL */
  success_url?: string
  /** 결제 실패 시 리다이렉트 URL */
  fail_url?: string
}

// ========== 결제 승인 요청/응답 ==========

/**
 * 결제 승인 요청 데이터
 * 토스 SDK 리다이렉트 후 URL 파라미터
 */
export interface PaymentConfirmRequest {
  /** 토스 결제 키 */
  paymentKey: string
  /** 토스 주문 ID */
  orderId: string
  /** 결제 금액 */
  amount: number
}

/**
 * 결제 승인 응답 데이터
 */
export interface PaymentConfirmResponse {
  /** 성공 여부 */
  success: boolean
  /** 내부 주문 ID */
  order_id?: number
  /** 주문번호 */
  order_no?: string
  /** 결제 금액 */
  amount?: number
  /** 결제 수단 */
  method?: string
  /** 에러 코드 */
  error_code?: string
  /** 에러 메시지 */
  error_message?: string
}

// ========== 결제 취소 ==========

/**
 * 결제 취소 요청 데이터
 */
export interface PaymentCancelRequest {
  /** 취소 사유 */
  cancel_reason: string
}

/**
 * 결제 취소 응답 데이터
 */
export interface PaymentCancelResponse {
  /** 성공 여부 */
  success: boolean
  /** 환불 금액 */
  refund_amount?: number
  /** 에러 코드 */
  error_code?: string
  /** 에러 메시지 */
  error_message?: string
}

// ========== 결제 정보 ==========

/**
 * 결제 상태
 */
export type PaymentStatus = 'pending' | 'success' | 'failed' | 'cancelled'

/**
 * 결제 정보 (상세)
 */
export interface Payment {
  id: number
  method_type: string
  method_type_display: string
  amount: number
  status: PaymentStatus
  status_display: string
  is_simulation: boolean
  simulation_note?: string
  pg_provider?: string
  pg_tid?: string
  pg_order_id?: string
  expected_amount?: number
  // 카드 정보
  card_company?: string
  card_number_masked?: string
  card_installment_months?: number
  // 가상계좌 정보
  virtual_account_number?: string
  virtual_account_bank?: string
  virtual_account_due_date?: string
  virtual_account_holder?: string
  // 환불 정보
  refund_amount?: number
  refunded_at?: string
  // 타임스탬프
  created_at: string
  processed_at?: string
  failure_reason?: string
}

// ========== 토스페이먼츠 결제위젯 SDK v2 타입 ==========

/**
 * 결제 금액 설정 옵션
 */
export interface PaymentAmountOptions {
  /** 통화 (KRW) */
  currency: string
  /** 결제 금액 */
  value: number
}

/**
 * 결제 요청 옵션 (v2)
 */
export interface PaymentWidgetRequestOptions {
  /** 주문 ID */
  orderId: string
  /** 주문명 */
  orderName: string
  /** 성공 시 리다이렉트 URL */
  successUrl: string
  /** 실패 시 리다이렉트 URL */
  failUrl: string
  /** 고객 이메일 (선택) */
  customerEmail?: string
  /** 고객 이름 (선택) */
  customerName?: string
  /** 고객 휴대폰 번호 (선택) */
  customerMobilePhone?: string
}

/**
 * 결제 수단 위젯 렌더 옵션
 */
export interface RenderPaymentMethodsOptions {
  /** CSS 선택자 */
  selector: string
  /** variantKey (optional) */
  variantKey?: string
}

/**
 * 이용약관 위젯 렌더 옵션
 */
export interface RenderAgreementOptions {
  /** CSS 선택자 */
  selector: string
  /** variantKey (optional) */
  variantKey?: string
}

/**
 * 토스페이먼츠 결제위젯 인스턴스 (v2)
 */
export interface TossPaymentWidgets {
  /** 결제 금액 설정 */
  setAmount: (options: PaymentAmountOptions) => Promise<void>
  /** 결제 수단 UI 렌더링 */
  renderPaymentMethods: (options: RenderPaymentMethodsOptions) => Promise<void>
  /** 약관 동의 UI 렌더링 */
  renderAgreement: (options: RenderAgreementOptions) => Promise<void>
  /** 결제 요청 */
  requestPayment: (options: PaymentWidgetRequestOptions) => Promise<void>
}

/**
 * 토스페이먼츠 SDK 인스턴스 (v2)
 */
export interface TossPaymentsInstance {
  /** 결제위젯 인스턴스 생성 */
  widgets: (options: { customerKey: string }) => TossPaymentWidgets
  /** 익명 고객 키 상수 */
  ANONYMOUS: string
}

/**
 * TossPayments 생성자 함수 타입
 */
export interface TossPaymentsConstructor {
  (clientKey: string): TossPaymentsInstance
  /** 익명 고객 키 상수 */
  ANONYMOUS: string
}

// Window 인터페이스 확장 - 결제위젯 SDK v2
declare global {
  interface Window {
    /** 토스페이먼츠 SDK (v2) - 동기 호출 */
    TossPayments: TossPaymentsConstructor
  }
}

/** 익명 고객 키 (비회원 또는 고객 식별 불필요 시) - TossPayments.ANONYMOUS 사용 권장 */
export const ANONYMOUS_CUSTOMER_KEY = 'ANONYMOUS'
