<template>
  <div class="checkout-page">
    <div class="container">
      <!-- Header -->
      <div class="page-header">
        <h1 class="page-title">주문/결제</h1>
        <p class="page-description">상품을 확인하고 주문을 완료하세요</p>
      </div>

      <!-- Loading State -->
      <div v-if="loading" class="loading-state">
        <div class="spinner"></div>
        <p>주문 정보를 불러오는 중...</p>
      </div>

      <!-- Error State -->
      <div v-else-if="error" class="error-state">
        <p class="error-message">{{ error }}</p>
        <router-link to="/cart" class="btn-retry">장바구니로 돌아가기</router-link>
      </div>

      <!-- Checkout Content -->
      <div v-else class="checkout-content">
        <div class="checkout-main">
          <!-- Order Items Section -->
          <section class="section order-items-section">
            <h2 class="section-title">주문 상품</h2>
            <div class="order-items">
              <div
                v-for="item in orderItems"
                :key="item.id"
                class="order-item"
              >
                <div class="item-image">
                  <img
                    :src="getProductImage(item.product)"
                    :alt="item.product.name"
                    @error="handleImageError"
                  />
                </div>
                <div class="item-info">
                  <h3 class="item-name">{{ item.product.name }}</h3>
                  <p class="item-meta">
                    <span v-if="item.product.category_name">{{ item.product.category_name }}</span>
                    <span v-if="item.product.unit"> · {{ item.product.unit }}</span>
                  </p>
                  <p class="item-quantity">수량: {{ item.quantity }}개</p>
                </div>
                <div class="item-price">
                  <p class="price">{{ formatPrice(item.product.price) }}</p>
                  <p class="subtotal">{{ formatPrice(item.subtotal || item.product.price * item.quantity) }}</p>
                </div>
              </div>
            </div>
          </section>

          <!-- Guest Info Section (비회원일 때만 표시) -->
          <section v-if="!authStore.isAuthenticated" class="section guest-section">
            <h2 class="section-title">주문자 정보</h2>
            <div class="guest-notice">
              <p>비회원 주문입니다. 주문 확인을 위해 정보를 입력해주세요.</p>
            </div>
            <form class="shipping-form">
              <div class="form-group">
                <label for="guest_name">주문자 이름 *</label>
                <input
                  id="guest_name"
                  v-model="guestInfo.name"
                  type="text"
                  placeholder="주문자 이름을 입력하세요"
                  required
                />
              </div>

              <div class="form-group">
                <label for="guest_email">이메일 *</label>
                <input
                  id="guest_email"
                  v-model="guestInfo.email"
                  type="email"
                  placeholder="주문 확인용 이메일을 입력하세요"
                  required
                />
                <small class="form-hint">주문번호와 함께 주문 조회에 사용됩니다</small>
              </div>

              <div class="form-group">
                <label for="guest_phone">연락처 *</label>
                <input
                  id="guest_phone"
                  v-model="guestInfo.phone"
                  type="tel"
                  placeholder="010-0000-0000"
                  required
                />
              </div>
            </form>
          </section>

          <!-- Shipping Info Section -->
          <section class="section shipping-section">
            <div class="section-header">
              <h2 class="section-title">배송 정보</h2>
              <!-- 회원이고 저장된 배송지가 있을 때 선택 옵션 표시 -->
              <div v-if="authStore.isAuthenticated && addressesStore.addresses.length > 0" class="address-select-wrapper">
                <select v-model="selectedAddressId" @change="onAddressSelect" class="address-select">
                  <option :value="null">새 배송지 입력</option>
                  <option
                    v-for="addr in addressesStore.addresses"
                    :key="addr.id"
                    :value="addr.id"
                  >
                    {{ addr.address_name }}{{ addr.is_default ? ' (기본)' : '' }} - {{ addr.recipient_name }}
                  </option>
                </select>
              </div>
            </div>

            <!-- 저장된 배송지 선택 시 표시 -->
            <div v-if="selectedAddress" class="selected-address-card">
              <div class="address-info">
                <div class="address-badge">
                  <span v-if="selectedAddress.is_default" class="badge-default">기본</span>
                  <span class="address-name">{{ selectedAddress.address_name }}</span>
                </div>
                <p class="recipient">{{ selectedAddress.recipient_name }} · {{ selectedAddress.recipient_phone }}</p>
                <p class="address-text">
                  [{{ selectedAddress.postal_code }}] {{ selectedAddress.address_line1 }}
                  <span v-if="selectedAddress.address_line2">, {{ selectedAddress.address_line2 }}</span>
                </p>
                <p v-if="selectedAddress.delivery_memo" class="delivery-memo">
                  배송 요청: {{ selectedAddress.delivery_memo }}
                </p>
              </div>
              <!-- 배송 요청사항 변경 가능 -->
              <div class="form-group memo-override">
                <label for="delivery_request_override">배송 요청사항 (변경 가능)</label>
                <select id="delivery_request_override" v-model="shippingInfo.delivery_request">
                  <option value="">저장된 요청사항 사용</option>
                  <option value="문 앞에 놓아주세요">문 앞에 놓아주세요</option>
                  <option value="경비실에 맡겨주세요">경비실에 맡겨주세요</option>
                  <option value="택배함에 넣어주세요">택배함에 넣어주세요</option>
                  <option value="배송 전 연락주세요">배송 전 연락주세요</option>
                  <option value="직접 입력">직접 입력</option>
                </select>
                <input
                  v-if="shippingInfo.delivery_request === '직접 입력'"
                  v-model="customRequest"
                  type="text"
                  placeholder="요청사항을 입력하세요"
                  class="custom-memo-input"
                />
              </div>
            </div>

            <!-- 새 배송지 입력 폼 -->
            <form v-else class="shipping-form">
              <div class="form-group">
                <label for="recipient_name">받는 사람 *</label>
                <input
                  id="recipient_name"
                  v-model="shippingInfo.recipient_name"
                  type="text"
                  placeholder="받는 사람 이름을 입력하세요"
                  required
                />
              </div>

              <div class="form-group">
                <label for="phone">연락처 *</label>
                <input
                  id="phone"
                  v-model="shippingInfo.phone"
                  type="tel"
                  placeholder="010-0000-0000"
                  required
                />
              </div>

              <div class="form-group">
                <label for="postal_code">우편번호 *</label>
                <div class="postal-code-group">
                  <input
                    id="postal_code"
                    v-model="shippingInfo.postal_code"
                    type="text"
                    placeholder="우편번호"
                    required
                    readonly
                  />
                  <button type="button" class="btn-search-address" @click="searchAddress">주소 검색</button>
                </div>
              </div>

              <div class="form-group">
                <label for="address">주소 *</label>
                <input
                  id="address"
                  v-model="shippingInfo.address"
                  type="text"
                  placeholder="주소"
                  required
                  readonly
                />
              </div>

              <div class="form-group">
                <label for="address_detail">상세 주소</label>
                <input
                  id="address_detail"
                  v-model="shippingInfo.address_detail"
                  type="text"
                  placeholder="상세 주소를 입력하세요"
                />
              </div>

              <div class="form-group">
                <label for="delivery_request">배송 요청사항</label>
                <select id="delivery_request" v-model="shippingInfo.delivery_request">
                  <option value="">배송 시 요청사항을 선택하세요</option>
                  <option value="문 앞에 놓아주세요">문 앞에 놓아주세요</option>
                  <option value="경비실에 맡겨주세요">경비실에 맡겨주세요</option>
                  <option value="택배함에 넣어주세요">택배함에 넣어주세요</option>
                  <option value="배송 전 연락주세요">배송 전 연락주세요</option>
                  <option value="직접 입력">직접 입력</option>
                </select>
              </div>

              <div v-if="shippingInfo.delivery_request === '직접 입력'" class="form-group">
                <label for="custom_request">직접 입력</label>
                <input
                  id="custom_request"
                  v-model="customRequest"
                  type="text"
                  placeholder="요청사항을 입력하세요"
                />
              </div>

              <!-- 회원이고 새 배송지 입력 시 저장 옵션 -->
              <div v-if="authStore.isAuthenticated && !selectedAddressId" class="save-address-option">
                <label class="checkbox-label">
                  <input type="checkbox" v-model="saveAsNewAddress" />
                  <span>이 배송지를 저장합니다</span>
                </label>
                <div v-if="saveAsNewAddress" class="save-address-fields">
                  <input
                    v-model="newAddressName"
                    type="text"
                    placeholder="배송지 이름 (예: 집, 회사)"
                    class="address-name-input"
                  />
                  <label class="checkbox-label">
                    <input type="checkbox" v-model="setAsDefault" />
                    <span>기본 배송지로 설정</span>
                  </label>
                </div>
              </div>
            </form>
          </section>

          <!-- 결제 수단 섹션 (회원 전용 - 토스 결제 위젯) -->
          <section v-if="authStore.isAuthenticated" class="section payment-section">
            <h2 class="section-title">결제 수단</h2>

            <!-- 결제 위젯이 렌더링될 영역 -->
            <div v-if="paymentReady" class="payment-widget-area">
              <!-- 토스 결제 수단 위젯 -->
              <div id="payment-method" class="payment-method-widget"></div>
              <!-- 토스 약관 동의 위젯 -->
              <div id="agreement" class="agreement-widget"></div>
            </div>

            <!-- 결제 위젯 로딩/준비 상태 -->
            <div v-else class="payment-widget-placeholder">
              <div v-if="paymentLoading" class="widget-loading">
                <div class="spinner-small"></div>
                <span>결제 위젯을 불러오는 중...</span>
              </div>
              <div v-else class="widget-notice">
                <p>배송 정보 입력 후 결제하기 버튼을 누르면 결제 수단을 선택할 수 있습니다.</p>
              </div>
            </div>

          </section>

          <!-- 결제 수단 섹션 (비회원 - 기존 모의 결제) -->
          <section v-else class="section payment-section">
            <h2 class="section-title">결제 수단</h2>
            <div class="payment-methods">
              <div class="payment-method selected">
                <input
                  id="instant"
                  type="radio"
                  value="instant"
                  v-model="guestPaymentMethod"
                  checked
                />
                <label for="instant">
                  <span class="method-name">즉시 결제</span>
                  <span class="method-desc">주문과 동시에 결제가 완료됩니다</span>
                </label>
              </div>
            </div>
            <p class="mvp-notice">
              * 비회원 주문은 모의 결제로 진행됩니다 (실제 결제 없음)
            </p>
          </section>
        </div>

        <!-- Order Summary Sidebar -->
        <aside class="checkout-sidebar">
          <div class="summary-sticky">
            <h2 class="summary-title">결제 금액</h2>

            <div class="summary-details">
              <div class="summary-row">
                <span>상품 금액</span>
                <span>{{ formatPrice(orderSummary.subtotal) }}</span>
              </div>

              <div class="summary-row">
                <span>배송비</span>
                <span>{{ formatPrice(orderSummary.shipping_fee) }}</span>
              </div>

              <div v-if="orderSummary.discount > 0" class="summary-row discount">
                <span>할인</span>
                <span>-{{ formatPrice(orderSummary.discount) }}</span>
              </div>

              <div class="summary-divider"></div>

              <div class="summary-row total">
                <span>최종 결제 금액</span>
                <span class="total-amount">{{ formatPrice(orderSummary.total) }}</span>
              </div>
            </div>

            <div v-if="orderSummary.shipping_fee === 0 && orderSummary.subtotal > 0" class="free-shipping-badge">
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
              </svg>
              무료 배송
            </div>

            <!-- 결제 버튼 -->
            <button
              v-if="!paymentReady"
              @click="handlePreparePayment"
              class="btn-place-order"
              :disabled="placing || !isFormValid"
            >
              <span v-if="placing">주문 처리 중...</span>
              <span v-else>{{ formatPrice(orderSummary.total) }} 결제하기</span>
            </button>

            <!-- 결제 위젯 렌더링 후에는 결제 요청 버튼 -->
            <button
              v-else
              @click="handleRequestPayment"
              class="btn-place-order btn-payment"
              :disabled="paymentLoading"
            >
              <span v-if="paymentLoading">결제 진행 중...</span>
              <span v-else>{{ formatPrice(orderSummary.total) }} 결제하기</span>
            </button>

            <div v-if="paymentError" class="payment-error">
              {{ paymentError }}
            </div>

            <div class="recommendation-card">
              <CartRecommendations :limit="6" />
            </div>
          </div>
        </aside>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useCartStore } from '@/stores/cart'
import { useAuthStore } from '@/stores/auth'
import { useAddressesStore } from '@/stores/addresses'
import { usePayment } from '@/composables/usePayment'
import { guestOrdersAPI } from '@/services/api'
import { getProductImage, formatPrice, DEFAULT_PRODUCT_IMAGE } from '@/types/product'
import type { UserAddress } from '@/types/auth'
import CartRecommendations from '@/components/ui/CartRecommendations.vue'

const router = useRouter()
const cartStore = useCartStore()
const authStore = useAuthStore()
const addressesStore = useAddressesStore()

// 결제 composable
const {
  loading: paymentLoading,
  error: paymentError,
  preparePayment,
  renderPaymentWidget,
  requestPayment,
} = usePayment()

const FREE_SHIPPING_THRESHOLD = 30000

// State
const loading = ref(true)
const error = ref<string | null>(null)
const placing = ref(false)
const customRequest = ref('')
const paymentReady = ref(false) // 결제 위젯이 렌더링되었는지

// 결제 수단 (비회원용)
const guestPaymentMethod = ref('instant')

// 배송지 선택 관련
const selectedAddressId = ref<number | null>(null)
const saveAsNewAddress = ref(false)
const newAddressName = ref('')
const setAsDefault = ref(false)

// 선택된 배송지 computed
const selectedAddress = computed<UserAddress | null>(() => {
  if (!selectedAddressId.value) return null
  return addressesStore.getAddressById(selectedAddressId.value) || null
})

// 비회원 정보
const guestInfo = ref({
  name: '',
  email: '',
  phone: ''
})

// Shipping info
const shippingInfo = ref({
  recipient_name: '',
  phone: '',
  postal_code: '',
  address: '',
  address_detail: '',
  delivery_request: ''
})

// Order items from cart
const orderItems = computed(() => cartStore.items)

// Order summary
const orderSummary = computed(() => {
  const subtotal = cartStore.total
  const shipping_fee = subtotal >= FREE_SHIPPING_THRESHOLD ? 0 : (subtotal > 0 ? 3000 : 0)
  const discount = 0 // MVP: 할인 기능 없음
  const total = subtotal + shipping_fee - discount

  return {
    subtotal,
    shipping_fee,
    discount,
    total
  }
})

// Form validation
const isFormValid = computed(() => {
  // 기본 조건: 주문 상품 있음
  if (orderItems.value.length === 0) {
    return false
  }

  // 비회원인 경우 추가 검증
  if (!authStore.isAuthenticated) {
    if (!guestInfo.value.name.trim() || !guestInfo.value.email.trim() || !guestInfo.value.phone.trim()) {
      return false
    }
  }

  // 저장된 배송지 선택 시: 배송지가 선택되었으면 유효
  if (selectedAddressId.value && selectedAddress.value) {
    return true
  }

  // 새 배송지 입력 시: 필수 필드 검증
  const newAddressValid = (
    shippingInfo.value.recipient_name.trim() !== '' &&
    shippingInfo.value.phone.trim() !== '' &&
    shippingInfo.value.postal_code.trim() !== '' &&
    shippingInfo.value.address.trim() !== ''
  )

  return newAddressValid
})

// Load initial data
const loadCheckoutData = async () => {
  loading.value = true
  error.value = null

  try {
    // Load cart if not already loaded
    if (cartStore.items.length === 0) {
      await cartStore.loadCart()
    }

    // Check if cart is empty
    if (cartStore.items.length === 0) {
      error.value = '장바구니가 비어있습니다.'
      return
    }

    // 회원인 경우 저장된 배송지 로드
    if (authStore.isAuthenticated) {
      await addressesStore.loadAddresses()

      // 기본 배송지가 있으면 자동 선택
      if (addressesStore.defaultAddress) {
        selectedAddressId.value = addressesStore.defaultAddress.id
      } else if (addressesStore.addresses.length > 0) {
        // 기본 배송지가 없으면 첫 번째 배송지 선택
        selectedAddressId.value = addressesStore.addresses[0].id
      }
    }

    // Pre-fill user info if available (새 배송지 입력 시 기본값)
    if (authStore.user) {
      shippingInfo.value.recipient_name = authStore.displayName || ''
      shippingInfo.value.phone = authStore.phoneNumber || ''
    }
  } catch (err: any) {
    console.error('결제 페이지 로드 실패:', err)
    error.value = '결제 정보를 불러오는데 실패했습니다.'
  } finally {
    loading.value = false
  }
}

// 배송지 선택 변경 핸들러
const onAddressSelect = () => {
  // 새 배송지 입력으로 전환 시 사용자 정보 기본값 설정
  if (!selectedAddressId.value && authStore.user) {
    shippingInfo.value.recipient_name = authStore.displayName || ''
    shippingInfo.value.phone = authStore.phoneNumber || ''
  }
  // 배송 요청사항 초기화
  shippingInfo.value.delivery_request = ''
  customRequest.value = ''
}

// 다음 주소 검색 API
const searchAddress = () => {
  // @ts-ignore - Daum Postcode API
  if (typeof daum === 'undefined') {
    // 다음 주소 검색 스크립트가 로드되지 않은 경우 동적 로드
    const script = document.createElement('script')
    script.src = '//t1.daumcdn.net/mapjsapi/bundle/postcode/prod/postcode.v2.js'
    script.onload = () => openPostcode()
    document.head.appendChild(script)
  } else {
    openPostcode()
  }
}

const openPostcode = () => {
  // @ts-ignore - Daum Postcode API
  new daum.Postcode({
    oncomplete: (data: any) => {
      // 도로명 주소 우선 사용
      shippingInfo.value.postal_code = data.zonecode
      shippingInfo.value.address = data.roadAddress || data.jibunAddress
    }
  }).open()
}

// 배송 정보 추출 헬퍼
const getShippingDetails = () => {
  let recipientName = ''
  let recipientPhone = ''
  let postalCode = ''
  let address = ''
  let addressDetail = ''
  let deliveryRequest = ''

  if (selectedAddressId.value && selectedAddress.value) {
    // 저장된 배송지 사용
    recipientName = selectedAddress.value.recipient_name
    recipientPhone = selectedAddress.value.recipient_phone
    postalCode = selectedAddress.value.postal_code
    address = selectedAddress.value.address_line1
    addressDetail = selectedAddress.value.address_line2 || ''

    // 배송 요청사항
    if (shippingInfo.value.delivery_request === '직접 입력' && customRequest.value.trim()) {
      deliveryRequest = customRequest.value.trim()
    } else if (shippingInfo.value.delivery_request && shippingInfo.value.delivery_request !== '') {
      deliveryRequest = shippingInfo.value.delivery_request
    } else {
      deliveryRequest = selectedAddress.value.delivery_memo || ''
    }
  } else {
    // 새 배송지 입력
    recipientName = shippingInfo.value.recipient_name
    recipientPhone = shippingInfo.value.phone
    postalCode = shippingInfo.value.postal_code
    address = shippingInfo.value.address
    addressDetail = shippingInfo.value.address_detail

    if (shippingInfo.value.delivery_request === '직접 입력' && customRequest.value.trim()) {
      deliveryRequest = customRequest.value.trim()
    } else {
      deliveryRequest = shippingInfo.value.delivery_request || ''
    }
  }

  const shippingAddress = `(${postalCode}) ${address} ${addressDetail}`.trim()

  return {
    recipientName,
    recipientPhone,
    postalCode,
    address,
    addressDetail,
    shippingAddress,
    deliveryRequest
  }
}

// 결제 준비 (회원: PG, 비회원: 모의 결제)
const handlePreparePayment = async () => {
  if (!isFormValid.value || placing.value) return

  // 비회원 검증
  if (!authStore.isAuthenticated) {
    if (!guestInfo.value.name.trim()) {
      alert('주문자 이름을 입력해주세요.')
      return
    }
    if (!guestInfo.value.email.trim()) {
      alert('이메일을 입력해주세요.')
      return
    }
    if (!guestInfo.value.phone.trim()) {
      alert('주문자 연락처를 입력해주세요.')
      return
    }
  }

  // 새 배송지 입력 시 검증
  if (!selectedAddressId.value && !selectedAddress.value) {
    if (!shippingInfo.value.recipient_name.trim()) {
      alert('받는 사람 이름을 입력해주세요.')
      return
    }
    if (!shippingInfo.value.phone.trim()) {
      alert('연락처를 입력해주세요.')
      return
    }
    if (!shippingInfo.value.postal_code.trim() || !shippingInfo.value.address.trim()) {
      alert('배송 주소를 입력해주세요.')
      return
    }
  }

  placing.value = true

  try {
    const shipping = getShippingDetails()

    if (!authStore.isAuthenticated) {
      // ========== 비회원 주문 (기존 모의 결제) ==========
      const guestOrderData = {
        items: cartStore.items.map(item => ({
          product_id: item.product.id,
          quantity: item.quantity
        })),
        guest_email: guestInfo.value.email,
        guest_name: guestInfo.value.name,
        guest_phone: guestInfo.value.phone,
        recipient_name: shipping.recipientName,
        recipient_phone: shipping.recipientPhone,
        shipping_address: shipping.shippingAddress,
        shipping_memo: shipping.deliveryRequest
      }

      const response = await guestOrdersAPI.createOrder(guestOrderData)

      // 로컬 장바구니 비우기
      await cartStore.clearCart()

      // 주문번호 표시
      const orderNo = response.data.order?.order_no || '주문번호'
      alert(`비회원 주문이 완료되었습니다!\n\n주문번호: ${orderNo}\n이메일: ${guestInfo.value.email}\n\n주문 조회 시 주문번호와 이메일이 필요합니다.`)

      // 홈으로 이동
      router.push('/')
    } else {
      // ========== 회원 주문 - PG 결제 흐름 ==========

      // 새 배송지 저장 옵션이 선택된 경우 배송지 먼저 저장
      if (!selectedAddressId.value && saveAsNewAddress.value) {
        try {
          await addressesStore.addAddress({
            address_name: newAddressName.value.trim() || '새 배송지',
            recipient_name: shipping.recipientName,
            recipient_phone: shipping.recipientPhone,
            postal_code: shipping.postalCode,
            address_line1: shipping.address,
            address_line2: shipping.addressDetail || null,
            delivery_memo: shipping.deliveryRequest || null,
            is_default: setAsDefault.value
          })
        } catch (saveErr) {
          console.error('배송지 저장 실패 (주문은 계속 진행):', saveErr)
        }
      }

      // 1. 결제 준비 API 호출 (주문 생성 + PG 초기화)
      const prepareResult = await preparePayment({
        cart_item_ids: cartStore.items.map(item => item.id as number),
        recipient_name: shipping.recipientName,
        recipient_phone: shipping.recipientPhone,
        shipping_address: shipping.shippingAddress,
        shipping_memo: shipping.deliveryRequest,
        save_address: saveAsNewAddress.value && !selectedAddressId.value,
        address_name: newAddressName.value.trim() || undefined,
      })

      if (!prepareResult) {
        alert(paymentError.value || '결제 준비 중 오류가 발생했습니다.')
        return
      }

      // 2. 결제 위젯 렌더링
      paymentReady.value = true

      // DOM 업데이트 후 위젯 렌더링
      await nextTick()

      const widgetRendered = await renderPaymentWidget('#payment-method', '#agreement')
      if (!widgetRendered) {
        paymentReady.value = false
        alert(paymentError.value || '결제 위젯 로드에 실패했습니다.')
      }
    }
  } catch (err: any) {
    console.error('주문 실패:', err)
    alert(err.response?.data?.message || err.response?.data?.error || '주문에 실패했습니다. 다시 시도해주세요.')
  } finally {
    placing.value = false
  }
}

// 결제 요청 (위젯 렌더링 후)
const handleRequestPayment = async () => {
  await requestPayment()
  // requestPayment 실행 후 성공 시 토스가 자동으로 successUrl로 리다이렉트
  // 실패 시 failUrl로 리다이렉트
}

// Handle image error
const handleImageError = (event: Event) => {
  const target = event.target as HTMLImageElement
  target.src = DEFAULT_PRODUCT_IMAGE
}

// Initialize
onMounted(() => {
  loadCheckoutData()
})
</script>

<style scoped>
.checkout-page {
  min-height: 100vh;
  background: #f8f9fa;
  padding: 2rem 0;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1rem;
}

/* Header */
.page-header {
  margin-bottom: 2rem;
  text-align: center;
}

.page-title {
  font-size: 2rem;
  font-weight: 700;
  color: #1a1a1a;
  margin-bottom: 0.5rem;
}

.page-description {
  color: #666;
  font-size: 1rem;
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

.spinner-small {
  width: 24px;
  height: 24px;
  border: 3px solid #f3f3f3;
  border-top: 3px solid #00a86b;
  border-radius: 50%;
  animation: spin 1s linear infinite;
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
  display: inline-block;
  padding: 0.75rem 1.5rem;
  background: #00a86b;
  color: white;
  text-decoration: none;
  border-radius: 6px;
  transition: background 0.2s;
}

.btn-retry:hover {
  background: #008c5a;
}

/* Checkout Content */
.checkout-content {
  display: grid;
  grid-template-columns: 1fr 380px;
  gap: 2rem;
  align-items: start;
}

.checkout-main {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

/* Section */
.section {
  background: white;
  border-radius: 8px;
  padding: 2rem;
}

.section-title {
  font-size: 1.5rem;
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
  border: 1px solid #e9ecef;
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

.item-meta {
  font-size: 0.875rem;
  color: #666;
}

.item-quantity {
  font-size: 0.875rem;
  color: #999;
  margin-top: 0.25rem;
}

.item-price {
  text-align: right;
}

.item-price .price {
  font-size: 0.875rem;
  color: #666;
  margin-bottom: 0.25rem;
}

.item-price .subtotal {
  font-size: 1.125rem;
  font-weight: 700;
  color: #1a1a1a;
}

/* Shipping Form */
.shipping-form {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-group label {
  font-size: 0.875rem;
  font-weight: 600;
  color: #333;
}

.form-group input,
.form-group select {
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
  transition: border-color 0.2s;
}

.form-group input:focus,
.form-group select:focus {
  outline: none;
  border-color: #00a86b;
}

.postal-code-group {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 0.5rem;
}

.btn-search-address {
  padding: 0.75rem 1.5rem;
  background: #6c757d;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
  white-space: nowrap;
}

.btn-search-address:hover {
  background: #5a6268;
}

/* Section Header with Address Select */
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  padding-bottom: 0.75rem;
  border-bottom: 2px solid #f0f0f0;
  flex-wrap: wrap;
  gap: 1rem;
}

.section-header .section-title {
  margin-bottom: 0;
  padding-bottom: 0;
  border-bottom: none;
}

.address-select-wrapper {
  flex-shrink: 0;
}

.address-select {
  padding: 0.5rem 1rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 0.875rem;
  min-width: 200px;
  background: white;
  cursor: pointer;
}

.address-select:focus {
  outline: none;
  border-color: #00a86b;
}

/* Selected Address Card */
.selected-address-card {
  border: 2px solid #00a86b;
  border-radius: 8px;
  padding: 1.5rem;
  background: #f0fdf7;
}

.address-info {
  margin-bottom: 1rem;
}

.address-badge {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.badge-default {
  display: inline-block;
  padding: 0.125rem 0.5rem;
  background: #00a86b;
  color: white;
  font-size: 0.75rem;
  font-weight: 600;
  border-radius: 4px;
}

.address-name {
  font-size: 1rem;
  font-weight: 700;
  color: #1a1a1a;
}

.recipient {
  font-size: 0.9375rem;
  color: #333;
  margin-bottom: 0.25rem;
}

.address-text {
  font-size: 0.9375rem;
  color: #555;
  line-height: 1.5;
}

.delivery-memo {
  margin-top: 0.5rem;
  padding-top: 0.5rem;
  border-top: 1px dashed #c3e6cb;
  font-size: 0.875rem;
  color: #666;
}

.memo-override {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #e9ecef;
}

.custom-memo-input {
  margin-top: 0.5rem;
}

/* Save Address Option */
.save-address-option {
  margin-top: 1.5rem;
  padding: 1rem;
  background: #f8f9fa;
  border: 1px solid #e9ecef;
  border-radius: 6px;
}

.save-address-fields {
  margin-top: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.address-name-input {
  padding: 0.625rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 0.9375rem;
}

.address-name-input:focus {
  outline: none;
  border-color: #00a86b;
}

/* Payment Widget Area */
.payment-widget-area {
  min-height: 300px;
}

.payment-method-widget {
  margin-bottom: 1rem;
}

.agreement-widget {
  margin-top: 1rem;
}

.payment-widget-placeholder {
  min-height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f8f9fa;
  border-radius: 8px;
  padding: 2rem;
}

.widget-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  color: #666;
}

.widget-notice {
  text-align: center;
  color: #666;
}

/* Payment Methods (비회원용) */
.payment-methods {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.payment-method {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 1rem;
  border: 2px solid #e9ecef;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.payment-method.selected {
  border-color: #00a86b;
  background: #f0fdf7;
}

.payment-method input[type="radio"] {
  margin-top: 0.25rem;
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.payment-method label {
  flex: 1;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.method-name {
  font-size: 1rem;
  font-weight: 600;
  color: #1a1a1a;
}

.method-desc {
  font-size: 0.875rem;
  color: #666;
}

.mvp-notice {
  margin-top: 1rem;
  padding: 0.75rem;
  background: #fff3cd;
  border: 1px solid #ffeaa7;
  border-radius: 4px;
  font-size: 0.875rem;
  color: #856404;
}

/* Sidebar */
.checkout-sidebar {
  position: relative;
}

.summary-sticky {
  position: sticky;
  top: 2rem;
  background: white;
  border-radius: 8px;
  padding: 2rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.summary-title {
  font-size: 1.25rem;
  font-weight: 700;
  color: #1a1a1a;
  margin-bottom: 1.5rem;
}

.summary-details {
  display: flex;
  flex-direction: column;
  gap: 1rem;
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
  padding-top: 0.5rem;
}

.total-amount {
  font-size: 1.5rem;
  color: #00a86b;
}

.free-shipping-badge {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  margin-top: 1rem;
  padding: 0.75rem;
  background: #d4edda;
  border: 1px solid #c3e6cb;
  border-radius: 6px;
  color: #155724;
  font-weight: 600;
  font-size: 0.875rem;
}

.free-shipping-badge svg {
  width: 20px;
  height: 20px;
}

.recommendation-card {
  margin-top: 0.25rem;
}

.btn-place-order {
  width: 100%;
  padding: 1rem;
  margin-top: 1.5rem;
  background: #00a86b;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 1.125rem;
  font-weight: 700;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-place-order:hover:not(:disabled) {
  background: #008c5a;
}

.btn-place-order:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-payment {
  background: #0050ff;
}

.btn-payment:hover:not(:disabled) {
  background: #0040cc;
}

.payment-error {
  margin-top: 0.75rem;
  padding: 0.75rem;
  background: #f8d7da;
  border: 1px solid #f5c6cb;
  border-radius: 4px;
  color: #721c24;
  font-size: 0.875rem;
}

/* Guest Section */
.guest-section {
  border: 2px solid #ffc107;
}

.guest-notice {
  margin-bottom: 1.5rem;
  padding: 1rem;
  background: #fff3cd;
  border: 1px solid #ffeaa7;
  border-radius: 6px;
}

.guest-notice p {
  margin: 0;
  color: #856404;
  font-size: 0.9rem;
}

.form-hint {
  color: #6c757d;
  font-size: 0.75rem;
  margin-top: 0.25rem;
}

.checkbox-label {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  font-size: 0.875rem;
  color: #666;
  cursor: pointer;
}

.checkbox-label input[type="checkbox"] {
  margin-top: 0.125rem;
  width: 16px;
  height: 16px;
  cursor: pointer;
}

/* Responsive */
@media (max-width: 968px) {
  .checkout-content {
    grid-template-columns: 1fr;
  }

  .summary-sticky {
    position: static;
  }
}

@media (max-width: 768px) {
  .checkout-page {
    padding: 1rem 0;
  }

  .page-title {
    font-size: 1.5rem;
  }

  .section {
    padding: 1.5rem;
  }

  .section-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .address-select {
    width: 100%;
    min-width: unset;
  }

  .order-item {
    grid-template-columns: 60px 1fr;
    grid-template-areas:
      "image info"
      "price price";
  }

  .item-image {
    grid-area: image;
    width: 60px;
    height: 60px;
  }

  .item-info {
    grid-area: info;
  }

  .item-price {
    grid-area: price;
    text-align: left;
    margin-top: 0.5rem;
    padding-top: 0.5rem;
    border-top: 1px solid #e9ecef;
  }

  .selected-address-card {
    padding: 1rem;
  }
}

@media (max-width: 480px) {
  .summary-sticky {
    padding: 1.5rem;
  }

  .postal-code-group {
    grid-template-columns: 1fr;
  }

  .btn-search-address {
    width: 100%;
  }
}
</style>
