import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Product, Category, ProductFilterParams } from '@/types/product'
import { productsAPI } from '@/services/api'

// 상품 스토어
export const useProductStore = defineStore('products', () => {
  const products = ref<Product[]>([])
  const categories = ref<Category[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  /**
   * 제품 목록 조회
   * @param params - 쿼리 파라미터 (page, page_size, search, category, is_best, is_featured, is_new, is_on_sale, ordering)
   */
  const fetchProducts = async (params?: ProductFilterParams) => {
    loading.value = true
    error.value = null
    try {
      const { data } = await productsAPI.getProducts(params)
      products.value = data.results
      return data
    } catch (err) {
      error.value = '상품 목록을 불러오는 데 실패했습니다.'
      console.error('Failed to fetch products:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * 카테고리 목록 조회
   */
  

  const fetchCategories = async () => {
    loading.value = true
    error.value = null
    try {
      const { data } = await productsAPI.getCategories()
      categories.value = data.results
      return data
    } catch (err) {
      error.value = '카테고리 목록을 불러오는 데 실패했습니다.'
      console.error('Failed to fetch categories:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * 베스트 제품 조회 (조회수/주문수 기준)
   */
  const fetchBestProducts = async (limit: number = 20) => {
    return fetchProducts({ is_best: true, page_size: limit })
  }

  /**
   * 추천 제품 조회 (quality_score 기준)
   */
  const fetchFeaturedProducts = async (limit: number = 8) => {
    return fetchProducts({ is_featured: true, page_size: limit })
  }

  /**
   * 신상품 조회 (최근 7일 내 등록)
   */
  const fetchNewProducts = async (limit: number = 8) => {
    return fetchProducts({ is_new: true, page_size: limit })
  }

  /**
   * 할인 상품 조회 (original_price > price)
   */
  const fetchSaleProducts = async (limit: number = 8) => {
    return fetchProducts({ is_on_sale: true, page_size: limit })
  }

  return {
    products,
    categories,
    loading,
    error,
    fetchProducts,
    fetchCategories,
    fetchBestProducts,
    fetchFeaturedProducts,
    fetchNewProducts,
    fetchSaleProducts
  }
})

