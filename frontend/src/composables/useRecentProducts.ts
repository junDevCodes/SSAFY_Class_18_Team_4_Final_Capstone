import { ref, onMounted } from 'vue'
import { AxiosError } from 'axios'
import { recommendationApi } from '@/services/api/recommendations'
import type { Product } from '@/types/product'

/**
 * 최근 본 상품 관리 Composable (REC-005)
 *
 * 로그인한 사용자의 최근 본 상품 목록을 관리합니다.
 *
 * @param limit 조회 개수 (기본: 10)
 * @returns 최근 본 상품 상태 및 관리 함수
 *
 * @example
 * ```vue
 * <script setup>
 * import { useRecentProducts } from '@/composables/useRecentProducts'
 *
 * const { recentProducts, isLoading, error, refresh } = useRecentProducts(5)
 * </script>
 *
 * <template>
 *   <div v-if="isLoading">로딩 중...</div>
 *   <div v-else-if="error">{{ error.message }}</div>
 *   <ProductCard v-for="product in recentProducts" :key="product.id" :product="product" />
 * </template>
 * ```
 */
export function useRecentProducts(limit: number = 10) {
  const recentProducts = ref<Product[]>([])
  const isLoading = ref(false)
  const error = ref<Error | null>(null)

  /**
   * 최근 본 상품 목록 조회
   */
  const fetchRecentProducts = async () => {
    isLoading.value = true
    error.value = null

    try {
      recentProducts.value = await recommendationApi.getRecentViewedProducts(limit)
    } catch (e) {
      error.value = e as Error
      // 401 에러는 로그인 필요 상태이므로 별도 처리
      const axiosError = e as AxiosError
      if (axiosError?.response?.status !== 401) {
        console.error('최근 본 상품 조회 실패:', e)
      }
    } finally {
      isLoading.value = false
    }
  }

  // 컴포넌트 마운트 시 자동 조회
  onMounted(fetchRecentProducts)

  return {
    /** 최근 본 상품 목록 */
    recentProducts,
    /** 로딩 상태 */
    isLoading,
    /** 에러 정보 */
    error,
    /** 목록 새로고침 */
    refresh: fetchRecentProducts,
  }
}
