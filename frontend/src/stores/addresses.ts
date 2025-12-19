/**
 * Addresses Store (배송지 관리)
 * ERD V2.1 기준
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { addressesAPI } from '@/services/api'
import type { UserAddress, UserAddressRequest } from '@/types/auth'

export const useAddressesStore = defineStore('addresses', () => {
  // 상태
  const addresses = ref<UserAddress[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Computed
  const count = computed(() => addresses.value.length)
  const defaultAddress = computed(() => addresses.value.find(addr => addr.is_default) || null)
  const hasAddresses = computed(() => addresses.value.length > 0)

  // 배송지 목록 로드
  const loadAddresses = async () => {
    loading.value = true
    error.value = null

    try {
      const response = await addressesAPI.getAddresses({ page_size: 100 })
      // DRF 페이지네이션이 없으면 배열 직접 반환, 있으면 results 사용
      const data = response.data
      addresses.value = Array.isArray(data) ? data : (data.results || [])
    } catch (err: any) {
      error.value = err.response?.data?.detail || '배송지 목록을 불러오는데 실패했습니다.'
      console.error('배송지 목록 로드 실패:', err)
    } finally {
      loading.value = false
    }
  }

  // 배송지 추가
  const addAddress = async (data: UserAddressRequest): Promise<UserAddress> => {
    loading.value = true
    error.value = null

    try {
      const response = await addressesAPI.createAddress(data)
      const newAddress = response.data

      // 새 배송지가 기본 배송지인 경우 기존 기본 배송지 해제
      if (newAddress.is_default) {
        addresses.value = addresses.value.map(addr => ({
          ...addr,
          is_default: false
        }))
      }

      addresses.value.unshift(newAddress)
      return newAddress
    } catch (err: any) {
      error.value = err.response?.data?.detail || '배송지 추가에 실패했습니다.'
      console.error('배송지 추가 실패:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  // 배송지 수정
  const updateAddress = async (id: number, data: Partial<UserAddressRequest>): Promise<UserAddress> => {
    loading.value = true
    error.value = null

    try {
      const response = await addressesAPI.updateAddress(id, data)
      const updatedAddress = response.data

      // 수정된 배송지가 기본 배송지가 된 경우 기존 기본 배송지 해제
      if (updatedAddress.is_default) {
        addresses.value = addresses.value.map(addr => ({
          ...addr,
          is_default: addr.id === id
        }))
      }

      // 목록에서 해당 배송지 업데이트
      const index = addresses.value.findIndex(addr => addr.id === id)
      if (index !== -1) {
        addresses.value[index] = updatedAddress
      }

      return updatedAddress
    } catch (err: any) {
      error.value = err.response?.data?.detail || '배송지 수정에 실패했습니다.'
      console.error('배송지 수정 실패:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  // 배송지 삭제
  const deleteAddress = async (id: number): Promise<void> => {
    loading.value = true
    error.value = null

    try {
      await addressesAPI.deleteAddress(id)
      addresses.value = addresses.value.filter(addr => addr.id !== id)
    } catch (err: any) {
      error.value = err.response?.data?.detail || '배송지 삭제에 실패했습니다.'
      console.error('배송지 삭제 실패:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  // 기본 배송지 설정
  const setDefaultAddress = async (id: number): Promise<UserAddress> => {
    loading.value = true
    error.value = null

    try {
      const response = await addressesAPI.setDefaultAddress(id)
      const updatedAddress = response.data

      // 모든 배송지의 is_default 업데이트
      addresses.value = addresses.value.map(addr => ({
        ...addr,
        is_default: addr.id === id
      }))

      return updatedAddress
    } catch (err: any) {
      error.value = err.response?.data?.detail || '기본 배송지 설정에 실패했습니다.'
      console.error('기본 배송지 설정 실패:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  // ID로 배송지 조회
  const getAddressById = (id: number): UserAddress | undefined => {
    return addresses.value.find(addr => addr.id === id)
  }

  // 초기화
  const reset = () => {
    addresses.value = []
    loading.value = false
    error.value = null
  }

  return {
    // 상태
    addresses,
    loading,
    error,

    // Computed
    count,
    defaultAddress,
    hasAddresses,

    // 액션
    loadAddresses,
    addAddress,
    updateAddress,
    deleteAddress,
    setDefaultAddress,
    getAddressById,
    reset,
  }
})
