import apiClient from './client'

export interface ReviewImage {
  id: number
  image_url: string
  display_order: number
}

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

export interface ReviewListResponse {
  count: number
  next: string | null
  previous: string | null
  results: Review[]
}

export interface ReviewCreateRequest {
  product: number
  order_item?: number | null
  rating: number
  content: string
  image_urls?: string[]
}

export const reviewApi = {
  getProductReviews: async (
    productId: number,
    params?: { page?: number; page_size?: number; ordering?: string }
  ): Promise<ReviewListResponse> => {
    const response = await apiClient.get<ReviewListResponse>('/api/reviews/', {
      params: { product: productId, ...params },
    })
    return response.data
  },

  createReview: async (data: ReviewCreateRequest): Promise<Review> => {
    const response = await apiClient.post<Review>('/api/reviews/', data)
    return response.data
  },

  updateReview: async (
    reviewId: number,
    data: Partial<ReviewCreateRequest>
  ): Promise<Review> => {
    const response = await apiClient.patch<Review>(`/api/reviews/${reviewId}/`, data)
    return response.data
  },

  deleteReview: async (reviewId: number): Promise<void> => {
    await apiClient.delete(`/api/reviews/${reviewId}/`)
  },

  getMyReviews: async (params?: { page?: number; page_size?: number }): Promise<ReviewListResponse> => {
    const response = await apiClient.get<ReviewListResponse>('/api/reviews/my/', { params })
    return response.data
  },
}
