import apiClient from './client'
import type { CartItem } from '@/types/product'

// 장바구니 API 서비스
export const cartApi = {
  // 장바구니 조회
  getCart: async (): Promise<CartItem[]> => {
    const response = await apiClient.get<CartItem[]>('/cart')
    return response.data
  },

  // 장바구니에 상품 추가
  addToCart: async (productId: number, quantity: number = 1): Promise<CartItem> => {
    const response = await apiClient.post<CartItem>('/cart', { productId, quantity })
    return response.data
  },

  // 장바구니 수량 변경
  updateCartItem: async (itemId: number, quantity: number): Promise<CartItem> => {
    const response = await apiClient.put<CartItem>(`/cart/${itemId}`, { quantity })
    return response.data
  },

  // 장바구니에서 상품 제거
  removeFromCart: async (itemId: number): Promise<void> => {
    await apiClient.delete(`/cart/${itemId}`)
  },
}

