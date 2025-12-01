import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Product, Category } from '@/types/product'
import { productsAPI, categoriesAPI } from '@/api/products'

// 상품 스토어
export const useProductStore = defineStore('products', () => {
  const products = ref<Product[]>([])
  const categories = ref<Category[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  /**
   * 제품 목록 조회
   * @param params - 쿼리 파라미터 (page, page_size, search, category, is_best)
   */
  const fetchProducts = async (params?: {
    page?: number
    page_size?: number
    search?: string
    category?: number
    is_best?: boolean
  }) => {
    loading.value = true
    error.value = null
    try {
      const response = await productsAPI.getProducts(params)
      products.value = response.results
      return response
    } catch (err) {
      error.value = '제품 목록을 불러오는데 실패했습니다.'
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
      const response = await categoriesAPI.getCategories()
      categories.value = response.results
      return response
    } catch (err) {
      error.value = '카테고리 목록을 불러오는데 실패했습니다.'
      console.error('Failed to fetch categories:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * 베스트 제품만 조회
   */
  const fetchBestProducts = async () => {
    return fetchProducts({ is_best: true, page_size: 20 })
  }

  return {
    products,
    categories,
    loading,
    error,
    fetchProducts,
    fetchCategories,
    fetchBestProducts
  }
})

