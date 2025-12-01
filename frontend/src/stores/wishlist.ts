/**
 * Wishlist Store
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { wishlistAPI } from '@/services/api'
import type { Product } from '@/types/product'

export interface WishlistItem {
  id: number
  product: Product
  created_at: string
}

export const useWishlistStore = defineStore('wishlist', () => {
  const items = ref<WishlistItem[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Computed
  const count = computed(() => items.value.length)
  const productIds = computed(() => items.value.map(item => item.product.id))

  // 찜 여부 확인
  const isWishlisted = (productId: number) => {
    return productIds.value.includes(productId)
  }

  // 찜 목록 로드
  const loadWishlist = async () => {
    loading.value = true
    error.value = null

    try {
      const response = await wishlistAPI.getWishlist({ page_size: 100 })
      items.value = response.data.results || response.data
    } catch (err: any) {
      error.value = err.response?.data?.message || '찜 목록을 불러오는데 실패했습니다.'
      console.error('찜 목록 로드 실패:', err)
    } finally {
      loading.value = false
    }
  }

  // 찜 토글
  const toggleWishlist = async (product: Product) => {
    try {
      const response = await wishlistAPI.toggleWishlist(product.id)
      const isWishlisted = response.data.is_wishlist

      if (isWishlisted) {
        // 추가됨
        items.value.push(response.data.wishlist)
      } else {
        // 제거됨
        items.value = items.value.filter(item => item.product.id !== product.id)
      }

      return isWishlisted
    } catch (err: any) {
      error.value = err.response?.data?.message || '찜 처리에 실패했습니다.'
      console.error('찜 토글 실패:', err)
      throw err
    }
  }

  // 찜 삭제
  const removeFromWishlist = async (id: number) => {
    try {
      await wishlistAPI.removeFromWishlist(id)
      items.value = items.value.filter(item => item.id !== id)
    } catch (err: any) {
      error.value = err.response?.data?.message || '찜 삭제에 실패했습니다.'
      console.error('찜 삭제 실패:', err)
      throw err
    }
  }

  // 초기화
  const reset = () => {
    items.value = []
    loading.value = false
    error.value = null
  }

  return {
    items,
    loading,
    error,
    count,
    productIds,
    isWishlisted,
    loadWishlist,
    toggleWishlist,
    removeFromWishlist,
    reset,
  }
})
