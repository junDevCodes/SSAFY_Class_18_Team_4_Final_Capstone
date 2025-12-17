import apiClient from './client'
import type {
  Product,
  CartRecipeResponse,
  RecipeDetail,
  RecipeSearchResponse,
} from '@/types/product'

/**
 * 추천 API 응답 타입
 */
export interface RecentViewedResponse {
  products: Product[]
}

/**
 * 홈 추천 API 응답 타입
 */
export interface HomeRecommendationsResponse {
  products: Product[]
  user_type: 'cold' | 'warm' | 'hot'
  model_name: string
}

/**
 * 상품 상세 추천 API 응답 타입
 */
export interface ProductRecommendationsResponse {
  products: Product[]
}

/**
 * 딜 추천 API 응답 타입
 */
export interface DealRecommendationsResponse {
  products: Product[]
}

/**
 * 장바구니 통합 추천 상품 타입
 */
export interface CartRecommendationProduct {
  product_id: number
  name: string
  price: number
  original_price?: number
  discount_rate?: number
  image_url?: string
  category_id?: number
  source: 'recipe' | 'personalized' | 'instacart'
  recommendation_score?: number
  recipe_name?: string  // 레시피 기반 추천 시 요리명
  ingredient_name?: string  // 레시피 기반 추천 시 부족 재료명
}

/**
 * 장바구니 통합 추천 API 응답 타입
 */
export interface CartUnifiedRecommendationResponse {
  success: boolean
  recommendations: CartRecommendationProduct[]
  total_count: number
  recipe_count: number
  personalized_count: number
  instacart_count: number
  user_type: 'cold' | 'lukewarm' | 'warm'
  processing_time_ms: number
  message?: string
}

/**
 * 레시피 상세 API 응답 타입
 */
export interface RecipeDetailResponse {
  success: boolean
  recipe: RecipeDetail | null
  ingredients: Array<{
    ingredient_id: number
    name: string
    amount: string | null
    is_main: boolean
  }>
  message?: string
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

  /**
   * 홈 페이지 추천 상품 조회
   *
   * ML 추천 서비스(pred)를 통한 개인화/비개인화 추천 상품을 반환합니다.
   * 로그인한 사용자는 개인화 추천, 비로그인 사용자는 인기 상품을 받습니다.
   *
   * @param limit 조회 개수 (기본: 10, 최대: 50)
   * @returns 추천 상품 목록 및 추천 정보
   *
   * @example
   * const { products, user_type, model_name } = await recommendationApi.getHomeRecommendations(8)
   */
  getHomeRecommendations: async (limit: number = 10): Promise<HomeRecommendationsResponse> => {
    const response = await apiClient.get<HomeRecommendationsResponse>(
      '/api/recommendations/home/',
      { params: { limit } }
    )
    return response.data
  },

  /**
   * 상품 상세 페이지 연관 상품 추천
   *
   * 특정 상품과 관련된 추천 상품 목록을 반환합니다.
   *
   * @param productId 기준 상품 ID
   * @param limit 조회 개수 (기본: 10, 최대: 50)
   * @returns 연관 상품 목록
   *
   * @example
   * const { products } = await recommendationApi.getProductRecommendations(123, 5)
   */
  getProductRecommendations: async (productId: number, limit: number = 10): Promise<ProductRecommendationsResponse> => {
    const response = await apiClient.get<ProductRecommendationsResponse>(
      `/api/recommendations/product/${productId}/`,
      { params: { limit } }
    )
    return response.data
  },

  /**
   * 딜/할인 상품 추천
   *
   * TimeDeal 등에서 사용할 할인 상품 추천 목록을 반환합니다.
   *
   * @param limit 조회 개수 (기본: 10, 최대: 50)
   * @param categoryId 카테고리 필터 (선택)
   * @returns 딜 상품 목록
   *
   * @example
   * const { products } = await recommendationApi.getDealRecommendations(10, 5)
   */
  getDealRecommendations: async (limit: number = 10, categoryId?: number): Promise<DealRecommendationsResponse> => {
    const params: Record<string, number> = { limit }
    if (categoryId) {
      params.category_id = categoryId
    }
    const response = await apiClient.get<DealRecommendationsResponse>(
      '/api/recommendations/deals/',
      { params }
    )
    return response.data
  },

  // ============================================================
  // 장바구니 통합 추천 API (레시피 > 개인화 > Instacart)
  // ============================================================

  /**
   * 장바구니 통합 추천
   *
   * 장바구니 상품 기반 통합 추천 API.
   * 추천 우선순위: 레시피 기반 > 개인화 > Instacart Cold Start
   *
   * 레시피 기반 추천 상품에는 recipe_name(요리명)과 ingredient_name(부족 재료명)이 포함됩니다.
   *
   * @param cartProductIds 장바구니 상품 ID 목록
   * @param userId 사용자 ID (로그인 시)
   * @param limit 추천 개수 (기본 9개)
   * @returns 통합 추천 상품 목록
   *
   * @example
   * const result = await recommendationApi.getCartUnifiedRecommendations([1, 2, 3], 123, 9)
   * result.recommendations.forEach(rec => {
   *   if (rec.source === 'recipe') {
   *     console.log(`${rec.recipe_name} 재료: ${rec.ingredient_name}`)
   *   }
   * })
   */
  getCartUnifiedRecommendations: async (
    cartProductIds: number[],
    userId?: number,
    limit: number = 9,
  ): Promise<CartUnifiedRecommendationResponse> => {
    const response = await apiClient.post<CartUnifiedRecommendationResponse>(
      '/api/recommendations/cart/unified/',
      {
        user_id: userId,
        cart_product_ids: cartProductIds,
        limit,
      }
    )
    return response.data
  },

  // ============================================================
  // 레시피 GapFilling 추천 API
  // ============================================================

  /**
   * 장바구니 기반 레시피 추천
   *
   * 장바구니에 담긴 상품을 분석하여 만들 수 있는 레시피를 추천하고,
   * 부족한 재료(Gap)에 해당하는 상품을 추천합니다.
   *
   * @param cartProductIds 장바구니 상품 ID 목록
   * @param limit 추천 레시피 개수 (기본 3개)
   * @returns 추천 레시피 및 부족 재료 상품
   *
   * @example
   * const result = await recommendationApi.getCartRecipeRecommendations([1, 2, 3], 3)
   * result.recipes.forEach(recipe => {
   *   console.log(recipe.name, recipe.match_ratio)
   *   recipe.recommended_products.forEach(p => console.log(p.name, p.ingredient))
   * })
   */
  getCartRecipeRecommendations: async (
    cartProductIds: number[],
    limit: number = 3,
  ): Promise<CartRecipeResponse> => {
    const response = await apiClient.post<CartRecipeResponse>(
      '/api/recommendations/cart-recipes/',
      { cart_product_ids: cartProductIds, limit }
    )
    return response.data
  },

  /**
   * 레시피 상세 정보 조회
   *
   * @param recipeId 레시피 ID
   * @returns 레시피 상세 정보 및 재료 목록
   *
   * @example
   * const { recipe, ingredients } = await recommendationApi.getRecipeDetail(123)
   */
  getRecipeDetail: async (recipeId: number): Promise<RecipeDetailResponse> => {
    const response = await apiClient.get<RecipeDetailResponse>(
      `/api/recommendations/recipe/${recipeId}/`
    )
    return response.data
  },

  /**
   * 레시피 검색
   *
   * @param query 검색어 (레시피명 또는 재료)
   * @param category 카테고리 필터
   * @param limit 결과 개수
   * @returns 검색 결과
   *
   * @example
   * const { recipes, total_count } = await recommendationApi.searchRecipes('김치찌개', null, 10)
   */
  searchRecipes: async (
    query: string,
    category: string | null = null,
    limit: number = 20,
  ): Promise<RecipeSearchResponse> => {
    const params: Record<string, string | number> = { query, limit }
    if (category) {
      params.category = category
    }
    const response = await apiClient.get<RecipeSearchResponse>(
      '/api/recommendations/recipe/search/',
      { params }
    )
    return response.data
  },
}
