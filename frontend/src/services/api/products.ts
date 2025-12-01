import apiClient from './client'
import type { Product } from '@/types/product'

// 상품 API 서비스
export const productApi = {
  // 상품 목록 조회
  getProducts: async (): Promise<Product[]> => {
    const response = await apiClient.get<Product[]>('/products')
    return response.data
  },

  // 상품 상세 조회
  getProduct: async (id: number): Promise<Product> => {
    const response = await apiClient.get<Product>(`/products/${id}`)
    return response.data
  },
}

