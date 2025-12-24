import apiClient from './client'

/**
 * 리뷰 이미지 타입
 */
export interface ReviewImage {
  id: number
  image_url: string
  display_order: number
}

/**
 * 리뷰 타입
 */
export interface Review {
  id: number
  product: number
  user: number
  user_name: string
  order_item: number | null
  rating: number
  content: string
  has_photos: boolean
  status: 'visible' | 'hidden' | 'reported' | 'deleted'
  images: ReviewImage[]
  created_at: string
  updated_at: string
}

/**
 * 리뷰 목록 응답 타입
 */
export interface ReviewListResponse {
  count: number
  next: string | null
  previous: string | null
  results: Review[]
}

export interface ReviewImageUploadResponse {
  image_urls: string[]
  message?: string
}

/**
 * 리뷰 생성 요청 타입
 */
export interface ReviewCreateRequest {
  product: number
  order_item?: number
  rating: number
  content: string
  image_urls?: string[]
}

/**
 * 리뷰 API 서비스
 *
 * 상품 리뷰 CRUD 및 통계 관련 API를 제공합니다.
 */
export const reviewApi = {
  /**
   * 상품별 리뷰 목록 조회
   *
   * @param productId 상품 ID
   * @param params 페이지네이션/정렬 파라미터
   */
  getProductReviews: async (
    productId: number,
    params?: { page?: number; page_size?: number; ordering?: string }
  ): Promise<ReviewListResponse> => {
    const response = await apiClient.get<ReviewListResponse>('/api/reviews/', {
      params: { product: productId, ...params },
    })
    return response.data
  },

  /**
   * 리뷰 상세 조회
   */
  getReview: async (reviewId: number): Promise<Review> => {
    const response = await apiClient.get<Review>(`/api/reviews/${reviewId}/`)
    return response.data
  },

  /**
   * 리뷰 작성 (로그인 필수)
   */
  createReview: async (data: ReviewCreateRequest): Promise<Review> => {
    const response = await apiClient.post<Review>('/api/reviews/', data)
    return response.data
  },

  /**
   * 리뷰 수정 (본인만)
   */
  updateReview: async (
    reviewId: number,
    data: Partial<ReviewCreateRequest>
  ): Promise<Review> => {
    const response = await apiClient.patch<Review>(`/api/reviews/${reviewId}/`, data)
    return response.data
  },

  /**
   * 리뷰 이미지 업로드 (파일 → S3 → URL 반환)
   */
  uploadReviewImages: async (files: File[]): Promise<ReviewImageUploadResponse> => {
    const formData = new FormData()
    files.forEach((file) => formData.append('images', file))

    const response = await apiClient.post<ReviewImageUploadResponse>(
      '/api/reviews/images/upload/',
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    )
    return response.data
  },

  /**
   * 리뷰 삭제 (본인만)
   */
  deleteReview: async (reviewId: number): Promise<void> => {
    await apiClient.delete(`/api/reviews/${reviewId}/`)
  },

  /**
   * 내 리뷰 목록 조회 (로그인 필수)
   */
  getMyReviews: async (params?: {
    page?: number
    page_size?: number
  }): Promise<ReviewListResponse> => {
    const response = await apiClient.get<ReviewListResponse>('/api/reviews/my/', {
      params,
    })
    return response.data
  },
}
