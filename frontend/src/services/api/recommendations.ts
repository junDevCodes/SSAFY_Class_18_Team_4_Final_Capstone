import apiClient from './client'
import type { Product } from '@/types/product'

/**
 * 추천 API 응답 타입
 */
export interface RecentViewedResponse {
  products: Product[]
}

/**
 * 추천 API 서비스 (REC-005)
 *
 * 최근 본 상품, 개인화 추천 등 추천 관련 API를 제공합니다.
 */
export const recommendationApi = {
  /**
   * 최근 본 상품 목록 조회 (REC-005)
   *
   * 사용자가 최근에 조회한 상품 목록을 마지막 조회 시간 기준 내림차순으로 반환합니다.
   * 로그인 필수 API입니다.
   *
   * @param limit 조회 개수 (기본: 10, 최대: 100)
   * @returns 최근 본 상품 목록 (최신순)
   * @throws 401 인증 필요
   *
   * @example
   * // 기본 사용 (10개)
   * const products = await recommendationApi.getRecentViewedProducts()
   *
   * // 개수 지정
   * const products = await recommendationApi.getRecentViewedProducts(5)
   */
  getRecentViewedProducts: async (limit: number = 10): Promise<Product[]> => {
    const response = await apiClient.get<RecentViewedResponse>(
      '/api/recommendations/recent/',
      { params: { limit } }
    )
    return response.data.products
  },
}
