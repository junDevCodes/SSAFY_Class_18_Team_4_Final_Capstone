import apiClient from './client'
import type {
  Product,
  ProductDetail,
  ProductListResponse,
  ProductFilterParams,
  Category,
  CategoryListResponse,
} from '@/types/product'

/**
 * 상품 API 서비스 v2.1
 *
 * v2.1: ProductDetail, ProductInventory, ProductStats, ProductPriceHistory 지원
 */
export const productApi = {
  // ========================= 상품 목록 =========================

  /**
   * 상품 목록 조회 (페이지네이션 지원)
   */
  getProducts: async (params?: ProductFilterParams): Promise<ProductListResponse> => {
    const response = await apiClient.get<ProductListResponse>('/products/', { params })
    return response.data
  },

  /**
   * 상품 목록 조회 (배열 반환 - 레거시 호환)
   */
  getProductsLegacy: async (): Promise<Product[]> => {
    const response = await apiClient.get<ProductListResponse>('/products/')
    return response.data.results || []
  },

  /**
   * 추천 상품 목록 조회
   */
  getFeaturedProducts: async (limit: number = 8): Promise<Product[]> => {
    const response = await apiClient.get<ProductListResponse>('/products/', {
      params: { is_featured: true, page_size: limit },
    })
    return response.data.results || []
  },

  /**
   * 베스트 상품 목록 조회
   */
  getBestProducts: async (limit: number = 8): Promise<Product[]> => {
    const response = await apiClient.get<ProductListResponse>('/products/', {
      params: { is_best: true, page_size: limit },
    })
    return response.data.results || []
  },

  /**
   * 신상품 목록 조회
   */
  getNewProducts: async (limit: number = 8): Promise<Product[]> => {
    const response = await apiClient.get<ProductListResponse>('/products/', {
      params: { is_new: true, page_size: limit, ordering: '-created_at' },
    })
    return response.data.results || []
  },

  /**
   * 할인 상품 목록 조회
   */
  getSaleProducts: async (limit: number = 8): Promise<Product[]> => {
    const response = await apiClient.get<ProductListResponse>('/products/', {
      params: { is_on_sale: true, page_size: limit },
    })
    return response.data.results || []
  },

  // ========================= 상품 상세 =========================

  /**
   * 상품 상세 조회 (v2.1 - 분리 테이블 포함)
   */
  getProduct: async (idOrSlug: number | string): Promise<ProductDetail> => {
    const response = await apiClient.get<ProductDetail>(`/products/${idOrSlug}/`)
    return response.data
  },

  /**
   * 상품 상세 조회 (슬러그 기반)
   */
  getProductBySlug: async (slug: string): Promise<ProductDetail> => {
    const response = await apiClient.get<ProductDetail>(`/products/${slug}/`)
    return response.data
  },

  // ========================= 카테고리 =========================

  /**
   * 카테고리 목록 조회
   */
  getCategories: async (): Promise<Category[]> => {
    const response = await apiClient.get<CategoryListResponse>('/categories/')
    return response.data.results || []
  },

  /**
   * 카테고리별 상품 조회
   */
  getProductsByCategory: async (
    categoryId: number,
    params?: Omit<ProductFilterParams, 'category'>
  ): Promise<ProductListResponse> => {
    const response = await apiClient.get<ProductListResponse>('/products/', {
      params: { category: categoryId, ...params },
    })
    return response.data
  },

  // ========================= 검색 =========================

  /**
   * 상품 검색
   */
  searchProducts: async (
    query: string,
    params?: Omit<ProductFilterParams, 'search'>
  ): Promise<ProductListResponse> => {
    const response = await apiClient.get<ProductListResponse>('/products/', {
      params: { search: query, ...params },
    })
    return response.data
  },

  // ========================= 조회수 =========================

  /**
   * 상품 조회수 증가
   */
  incrementViewCount: async (productId: number): Promise<void> => {
    await apiClient.post(`/products/${productId}/view/`)
  },
}

