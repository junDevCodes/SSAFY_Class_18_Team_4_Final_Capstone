/**
 * 제품 API 클라이언트
 *
 * 커스텀 필터 (백엔드 v2.1 지원):
 * - is_featured: 추천 상품 (quality_score 기준 정렬)
 * - is_best: 베스트 상품 (조회수/주문수 기준 정렬)
 * - is_new: 신상품 (최근 7일 내 등록)
 * - is_on_sale: 할인 상품 (original_price > price)
 */
import axios from 'axios'
import type { ProductListResponse, CategoryListResponse, Product, Category, ProductFilterParams } from '@/types/product'
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
   * @param params - 쿼리 파라미터 (page, page_size, search, category, is_best, is_featured, is_new, is_on_sale)
   */
  async getProducts(params?: ProductFilterParams): Promise<ProductListResponse> {
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

  /**
   * 추천 상품 목록 조회 (quality_score 기준)
   */
  async getFeaturedProducts(limit: number = 8): Promise<Product[]> {
    const response = await api.get<ProductListResponse>('/api/products/', {
      params: { is_featured: true, page_size: limit },
    })
    return response.data.results || []
  },

  /**
   * 베스트 상품 목록 조회 (조회수/주문수 기준)
   */
  async getBestProducts(limit: number = 8): Promise<Product[]> {
    const response = await api.get<ProductListResponse>('/api/products/', {
      params: { is_best: true, page_size: limit },
    })
    return response.data.results || []
  },

  /**
   * 신상품 목록 조회 (최근 7일 내 등록)
   */
  async getNewProducts(limit: number = 8): Promise<Product[]> {
    const response = await api.get<ProductListResponse>('/api/products/', {
      params: { is_new: true, page_size: limit },
    })
    return response.data.results || []
  },

  /**
   * 할인 상품 목록 조회 (original_price > price)
   */
  async getSaleProducts(limit: number = 8): Promise<Product[]> {
    const response = await api.get<ProductListResponse>('/api/products/', {
      params: { is_on_sale: true, page_size: limit },
    })
    return response.data.results || []
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
