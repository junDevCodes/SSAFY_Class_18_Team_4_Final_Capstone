/**
 * Orders Store
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { ordersAPI } from '@/services/api'

// ----- 타입 정의 (ERD V2.1 DTO 기준) -----

export interface OrderItem {
  id: number
  product: any
  product_name: string
  image_url: string | null
  quantity: number
  unit_price: number
  discount_amount: number
  total_price: number
  status: string
  created_at: string
}

export interface Shipment {
  id: number
  recipient_name: string
  recipient_phone: string
  address_full: string
  shipping_memo: string | null
  courier: string | null
  tracking_no: string | null
  shipping_fee: number
  shipped_at: string | null
  delivered_at: string | null
  created_at: string
  updated_at: string
}

export interface Payment {
  id: number
  method_type: string
  amount: number
  status: string
  is_simulation: boolean
  simulation_note: string | null
  pg_provider: string | null
  pg_tid: string | null
  created_at: string
  processed_at: string | null
  failure_reason: string | null
}

export interface Order {
  id: number
  order_no: string
  user: number
  status: string
  status_display: string
  subtotal: number
  shipping_fee: number
  discount_amount: number
  total_amount: number
  cancelled_at: string | null
  cancel_reason: string | null
  refunded_at: string | null
  created_at: string
  updated_at: string
  items: OrderItem[]
  shipment: Shipment | null
  payment: Payment | null
  payment_status: string | null
  payment_status_display: string | null
  paid_at: string | null
}

export const useOrdersStore = defineStore('orders', () => {
  const orders = ref<Order[]>([])
  const currentOrder = ref<Order | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const total = ref(0)

  // Computed
  const count = computed(() => orders.value.length)

  // 주문 목록 로드
  const loadOrders = async (params?: { page?: number; page_size?: number }) => {
    loading.value = true
    error.value = null

    try {
      const response = await ordersAPI.getOrders(params)
      // DRF 페이지네이션 또는 비페이지네이션 모두 대응
      const data = response.data
      orders.value = (data.results as Order[]) || (data as Order[])
      total.value = (data.count as number) || orders.value.length
    } catch (err: any) {
      error.value = err.response?.data?.message || '주문 목록을 불러오는데 실패했습니다.'
      console.error('주문 목록 로드 실패:', err)
    } finally {
      loading.value = false
    }
  }

  // 주문 상세 로드
  const loadOrder = async (id: number) => {
    loading.value = true
    error.value = null

    try {
      const response = await ordersAPI.getOrder(id)
      currentOrder.value = response.data as Order
      return response.data as Order
    } catch (err: any) {
      error.value = err.response?.data?.message || '주문 정보를 불러오는데 실패했습니다.'
      console.error('주문 상세 로드 실패:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  // 주문 생성
  const createOrder = async (data: {
    cart_item_ids?: number[]
    recipient_name: string
    recipient_phone: string
    shipping_address: string
    shipping_memo?: string
    payment_method_type?: string
  }) => {
    loading.value = true
    error.value = null

    try {
      const response = await ordersAPI.createOrder(data)
      const newOrder = response.data.order as Order

      // 주문 목록에 추가
      orders.value.unshift(newOrder)
      currentOrder.value = newOrder

      return newOrder
    } catch (err: any) {
      error.value = err.response?.data?.message || '주문 생성에 실패했습니다.'
      console.error('주문 생성 실패:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  // 주문 취소
  const cancelOrder = async (id: number, cancel_reason: string) => {
    loading.value = true
    error.value = null

    try {
      const response = await ordersAPI.cancelOrder(id, cancel_reason)
      const updatedOrder = response.data.order as Order

      // 주문 목록 업데이트
      const index = orders.value.findIndex(o => o.id === id)
      if (index !== -1) {
        orders.value[index] = updatedOrder
      }

      // 현재 주문 업데이트
      if (currentOrder.value?.id === id) {
        currentOrder.value = updatedOrder
      }

      return updatedOrder
    } catch (err: any) {
      error.value = err.response?.data?.error || '주문 취소에 실패했습니다.'
      console.error('주문 취소 실패:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  // 배송 완료 확인
  const confirmDelivery = async (id: number) => {
    loading.value = true
    error.value = null

    try {
      const response = await ordersAPI.confirmDelivery(id)
      const updatedOrder = response.data.order as Order

      // 주문 목록 업데이트
      const index = orders.value.findIndex(o => o.id === id)
      if (index !== -1) {
        orders.value[index] = updatedOrder
      }

      // 현재 주문 업데이트
      if (currentOrder.value?.id === id) {
        currentOrder.value = updatedOrder
      }

      return updatedOrder
    } catch (err: any) {
      error.value = err.response?.data?.error || '배송 완료 확인에 실패했습니다.'
      console.error('배송 완료 확인 실패:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  // 초기화
  const reset = () => {
    orders.value = []
    currentOrder.value = null
    loading.value = false
    error.value = null
  }

  return {
    orders,
    currentOrder,
    loading,
    error,
    count,
    total,
    loadOrders,
    loadOrder,
    createOrder,
    cancelOrder,
    confirmDelivery,
    reset,
  }
})
