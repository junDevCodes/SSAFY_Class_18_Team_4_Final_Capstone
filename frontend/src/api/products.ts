// 제품 API 클라이언트
import axios from 'axios'
import type { ProductListResponse, CategoryListResponse, Product, Category } from '@/types/product'
import { API_BASE_URL } from '@/utils/constants'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 제품 API
export const productsAPI = {
  /**
   * 제품 목록 조회
   * @param params - 쿼리 파라미터 (page, page_size, search, category, is_best)
   */
  async getProducts(params?: {
    page?: number
    page_size?: number
    search?: string
    category?: number
    is_best?: boolean
  }): Promise<ProductListResponse> {
    const response = await api.get<ProductListResponse>('/api/products/', { params })
    return response.data
  },

  /**
   * 제품 상세 조회
   * @param id - 제품 ID
   */
  async getProduct(id: number): Promise<Product> {
    const response = await api.get<Product>(`/api/products/${id}/`)
    return response.data
  },
}

// 카테고리 API
export const categoriesAPI = {
  /**
   * 카테고리 목록 조회
   */
  async getCategories(): Promise<CategoryListResponse> {
    const response = await api.get<CategoryListResponse>('/api/categories/')
    return response.data
  },

  /**
   * 카테고리 상세 조회
   * @param id - 카테고리 ID
   */
  async getCategory(id: number): Promise<Category> {
    const response = await api.get<Category>(`/api/categories/${id}/`)
    return response.data
  },
}
