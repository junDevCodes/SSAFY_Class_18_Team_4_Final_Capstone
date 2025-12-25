/**
 * 통합 API 서비스
 * 모든 백엔드 API 엔드포인트를 중앙에서 관리
 *
 * v2.1: ProductDetail, ProductInventory, ProductStats, ProductPriceHistory 지원
 */
import apiClient from './client'
import type {
  LoginRequest,
  RegisterRequest,
  LoginResponse,
  User,
  RegisterResponse,
  UserAddress,
  UserAddressRequest,
  AddressListResponse
} from '@/types/auth'
import type {
  ProductDetail,
  ProductListResponse,
  ProductFilterParams,
  CategoryListResponse,
  NewProductListResponse,
} from '@/types/product'
import type {
  PaymentPrepareRequest,
  PaymentPrepareResponse,
  PaymentConfirmRequest,
  PaymentConfirmResponse,
  PaymentCancelResponse,
  Payment,
} from '@/types/payment'
import { analyticsAPI, adminAnalyticsAPI } from './analytics'

// ==================== Auth API ====================
export const authAPI = {
  // 회원가입
  register: (data: RegisterRequest) =>
    apiClient.post<RegisterResponse>('/auth/register/', data),

  // 이메일 인증
  verifyEmail: (payload: { email: string; code: string }) =>
    apiClient.post('/auth/register/verify/', payload),

  // 로그인
  login: (data: LoginRequest) =>
    apiClient.post<LoginResponse>('/auth/login/', data),

  // 로그아웃
  logout: () =>
    apiClient.post('/auth/logout/'),

  // 현재 사용자 정보
  getCurrentUser: () =>
    apiClient.get<User>('/auth/user/'),

  // 사용자 정보 수정
  updateUser: (data: Partial<User>) =>
    apiClient.patch<User>('/auth/user/', data),

  // 비밀번호 변경
  changePassword: (data: { old_password: string; new_password: string }) =>
    apiClient.post('/auth/password/change/', data),

  // 계정 삭제 가능 여부 조회
  checkAccountDeletion: () =>
    apiClient.get<{
      can_delete: boolean
      blockers: Array<{
        type: string
        count: number
        message: string
      }>
      auth_method: 'email' | 'google' | 'kakao' | 'unknown'
      is_seller: boolean
    }>('/auth/account/'),

  // 계정 삭제
  deleteAccount: (data: {
    password?: string
    confirm_text?: string
    reason?: string
  }) => apiClient.delete('/auth/account/', { data }),

  // 토큰 갱신
  refreshToken: (refresh: string) =>
    apiClient.post<{ access: string }>('/auth/token/refresh/', { refresh }),

  // 프로필 조회 (별칭)
  getProfile: () =>
    apiClient.get<User>('/auth/user/'),

  // 프로필 수정 (별칭)
  updateProfile: (data: Partial<User>) =>
    apiClient.patch<User>('/auth/user/', data),
}

// ==================== Addresses API (배송지 관리) ====================
export const addressesAPI = {
  // 배송지 목록 조회
  getAddresses: (params?: { page?: number; page_size?: number }) =>
    apiClient.get<AddressListResponse>('/api/users/me/addresses/', { params }),

  // 배송지 상세 조회
  getAddress: (id: number) =>
    apiClient.get<UserAddress>(`/api/users/me/addresses/${id}/`),

  // 배송지 추가
  createAddress: (data: UserAddressRequest) =>
    apiClient.post<UserAddress>('/api/users/me/addresses/', data),

  // 배송지 수정
  updateAddress: (id: number, data: Partial<UserAddressRequest>) =>
    apiClient.patch<UserAddress>(`/api/users/me/addresses/${id}/`, data),

  // 배송지 삭제
  deleteAddress: (id: number) =>
    apiClient.delete(`/api/users/me/addresses/${id}/`),

  // 기본 배송지 설정
  setDefaultAddress: (id: number) =>
    apiClient.post<UserAddress>(`/api/users/me/addresses/${id}/set-default/`),
}

// ==================== Products API ====================
export const productsAPI = {
  /**
   * 상품 목록 조회 (필터링, 검색, 정렬, 페이지네이션)
   */
  getProducts: (params?: ProductFilterParams) =>
    apiClient.get<ProductListResponse>('/api/products/', { params }),

  /**
   * 상품 상세 조회 (v2.1 - detail, inventory, stats, price_histories 포함)
   */
  getProduct: (idOrSlug: number | string) =>
    apiClient.get<ProductDetail>(`/api/products/${idOrSlug}/`),

  /**
   * 카테고리 목록 조회
   */
  getCategories: () =>
    apiClient.get<CategoryListResponse>('/api/categories/'),

  /**
   * 추천 상품 목록 조회
   */
  getFeaturedProducts: (limit: number = 8) =>
    apiClient.get<ProductListResponse>('/api/products/', {
      params: { is_featured: true, page_size: limit },
    }),

  /**
   * 베스트 상품 목록 조회
   */
  getBestProducts: (limit: number = 8) =>
    apiClient.get<ProductListResponse>('/api/products/', {
      params: { is_best: true, page_size: limit },
    }),

  /**
   * 신상품 목록 조회 (최근 7일 내 등록)
   */
  getNewProducts: (limit: number = 8) =>
    apiClient.get<ProductListResponse>('/api/products/', {
      params: { is_new: true, page_size: limit },
    }),

  /**
   * ??? ?? ?? (40? ?? - /api/products/new/)
   */
  getNewProductList: () =>
    apiClient.get<NewProductListResponse>('/api/products/new/'),

  /**
   * 할인 상품 목록 조회
   */
  getSaleProducts: (limit: number = 8) =>
    apiClient.get<ProductListResponse>('/api/products/', {
      params: { is_on_sale: true, page_size: limit },
    }),

  /**
   * 상품 검색
   */
  searchProducts: (query: string, params?: Omit<ProductFilterParams, 'search'>) =>
    apiClient.get<ProductListResponse>('/api/products/', {
      params: { search: query, ...params },
    }),

  /**
   * 카테고리별 상품 조회
   */
  getProductsByCategory: (categoryId: number, params?: Omit<ProductFilterParams, 'category'>) =>
    apiClient.get<ProductListResponse>('/api/products/', {
      params: { category: categoryId, ...params },
    }),

  /**
   * 상품 조회수 증가
   */
  incrementViewCount: (productId: number) =>
    apiClient.post(`/api/products/${productId}/view/`),
}

// ==================== Wishlist API ====================
export const wishlistAPI = {
  // 찜 목록 조회
  getWishlist: (params?: { page?: number; page_size?: number }) =>
    apiClient.get('/api/wishlist/', { params }),

  // 찜 추가
  addToWishlist: (product_id: number) =>
    apiClient.post('/api/wishlist/', { product_id }),

  // 찜 삭제
  removeFromWishlist: (id: number) =>
    apiClient.delete(`/api/wishlist/${id}/`),

  // 찜 토글 (있으면 삭제, 없으면 추가)
  toggleWishlist: (product_id: number) =>
    apiClient.post('/api/wishlist/toggle/', { product_id }),
}

// ==================== Cart API ====================
export const cartAPI = {
  // 장바구니 조회
  getCart: (params?: { page?: number; page_size?: number }) =>
    apiClient.get('/api/cart/', { params }),

  // 장바구니 요약
  getCartSummary: () =>
    apiClient.get('/api/cart/summary/'),

  // 장바구니 추가 (이미 있으면 수량 증가)
  addToCart: (data: { product_id: number; quantity?: number }) =>
    apiClient.post('/api/cart/', data),

  // 장바구니 수량 변경
  updateCartItem: (id: number, quantity: number) =>
    apiClient.patch(`/api/cart/${id}/`, { quantity }),

  // 장바구니 항목 삭제
  removeFromCart: (id: number) =>
    apiClient.delete(`/api/cart/${id}/`),

  // 장바구니 비우기
  clearCart: () =>
    apiClient.post('/api/cart/clear/'),
}

// ==================== Orders API ====================
export const ordersAPI = {
  // 주문 목록
  getOrders: (params?: { page?: number; page_size?: number }) =>
    apiClient.get('/api/orders/', { params }),

  // 주문 상세
  getOrder: (id: number) =>
    apiClient.get(`/api/orders/${id}/`),

  // 주문 생성 (장바구니에서)
  createOrder: (data: {
    cart_item_ids?: number[]
    recipient_name: string
    recipient_phone: string
    shipping_address: string
    shipping_memo?: string
    payment_method_type?: string
  }) => apiClient.post('/api/orders/create_order/', data),

  // 주문 취소
  cancelOrder: (id: number, cancel_reason: string) =>
    apiClient.post(`/api/orders/${id}/cancel/`, { cancel_reason }),

  // 배송 완료 확인
  confirmDelivery: (id: number) =>
    apiClient.post(`/api/orders/${id}/confirm_delivery/`),
}

// ==================== Guest Orders API (비회원 주문) ====================
export const guestOrdersAPI = {
  // 비회원 주문 생성
  createOrder: (data: {
    items: Array<{ product_id: number; quantity: number }>
    guest_email: string
    guest_name: string
    guest_phone: string
    recipient_name: string
    recipient_phone: string
    shipping_address: string
    shipping_memo?: string
    payment_method_type?: string
  }) => apiClient.post('/api/orders/guest/create_order/', data),

  // 비회원 주문 조회
  lookupOrder: (data: { order_no: string; guest_email: string }) =>
    apiClient.post('/api/orders/guest/lookup/', data),
}

// ==================== Recommendations API ====================
export interface CartRecommendedProduct {
  product_id: number
  name: string
  slug: string
  price: number
  original_price: number | null
  main_image: string | null
  order_count: number
  ingredient: string  // 이 상품이 커버하는 재료
}

export interface CartRecommendationsResponse {
  products: CartRecommendedProduct[]
  cart_ingredients: string[]
  model_version: string
  total_count: number
}

/**
 * 개인화 추천 상품 정보
 * ALS 32차원 모델 기반 추천 상품
 */
export interface PersonalizedProduct {
  product_id: number
  name: string
  slug: string
  price: number
  original_price: number | null
  main_image: string | null
  category_id: number | null
  category_name: string | null
  order_count: number
  view_count: number
  average_rating: number
  wishlist_count: number
  recommendation_score: number
  recommendation_source: string
}

/**
 * 개인화 추천 응답
 * ALS 32차원 + 하이브리드 추천 결과
 */
export interface PersonalizedRecommendationsResponse {
  products: PersonalizedProduct[]
  user_type: 'cold' | 'lukewarm' | 'warm'
  model_version: string
  total_count: number
  metadata: Record<string, unknown>
}

/**
 * 타임세일 가성비 상품 정보
 * self_price_analyzer_v1.pkl 모델 기반 가성비 상품
 */
export interface TimeDealProduct {
  product_id: number
  name: string
  slug: string
  price: number
  original_price: number | null
  previous_price: number | null
  main_image: string | null
  category_id: number | null
  category_name: string | null
  order_count: number
  view_count: number
  average_rating: number
  // 모델 추천 관련 필드
  price_change_rate: number      // 가격 변동률 (%)
  price_status: string           // SUPER_SALE, DISCOUNT, STABLE, INCREASE
  score_boost: number            // 상태별 점수 가중치
  final_score: number            // 최종 가성비 점수 (모델 추천순)
  savings: number                // 절감액 (원)
  is_lowest_ever: boolean        // 역대 최저가 여부
}

/**
 * 타임세일 응답
 * PriceScout 점수 기반 가성비 상품 목록
 */
export interface TimeDealResponse {
  products: TimeDealProduct[]
  model_version: string
  total_count: number
}

/**
 * 가격 히스토리 데이터 포인트
 */
export interface PriceHistoryPoint {
  recorded_at: string         // ISO 8601 형식
  price: number               // 가격
  previous_price: number | null
  price_change: number | null
  price_change_rate: number | null  // %
}

/**
 * 가격 통계
 */
export interface PriceStatistics {
  current_price: number       // 현재 가격
  min_price: number           // 최저가
  max_price: number           // 최고가
  avg_price: number           // 평균가
  price_change_from_avg: number  // 평균가 대비 변동률 (%)
  is_lowest_ever: boolean     // 역대 최저가 여부
  total_records: number       // 기록 수
}

/**
 * 가격 히스토리 응답
 */
export interface PriceHistoryResponse {
  product_id: number
  product_name: string
  history: PriceHistoryPoint[]
  statistics: PriceStatistics | null
}

export const recommendationsAPI = {
  // 장바구니 기반 ML 추천 (비회원 허용)
  getCartRecommendations: (productIds: number[], limit: number = 20) =>
    apiClient.post<CartRecommendationsResponse>('/api/recommendations/cart/', {
      product_ids: productIds,
      limit,
    }),

  /**
   * 개인화 추천 (로그인 필수)
   * 메인 페이지 MD's Pick 섹션에서 사용
   *
   * - ALS 32차원: Kaggle 최상위 수준 알고리즘
   * - 하이브리드: CBF 0.7 + CF 0.3 동적 가중치
   * - Cold user: 인기 상품으로 폴백
   */
  getPersonalizedRecommendations: (params?: {
    limit?: number
    page_type?: 'home' | 'category' | 'product_detail'
    category_id?: number
  }) => {
    const queryParams: Record<string, any> = {
      limit: params?.limit ?? 8,
      page_type: params?.page_type ?? 'home',
    }
    
    // category_id가 명시적으로 전달된 경우에만 추가 (undefined가 아닐 때)
    if (params?.category_id !== undefined && params.category_id !== null) {
      queryParams.category_id = params.category_id
    }
    
    return apiClient.get<PersonalizedRecommendationsResponse>('/api/recommendations/personalized/', {
      params: queryParams,
    })
  },

  /**
   * 타임세일 가성비 상품 (비회원 허용)
   * 메인 페이지 타임세일 섹션에서 사용
   *
   * - self_price_analyzer_v1.pkl 모델 기반
   * - PriceScout 점수 기준 정렬
   * - 가격 하락 상품 우선 노출
   * - ABNORMAL 상품 제외
   *
   * @param limit 조회할 상품 수 (기본 10, 최대 50)
   * @param categoryId 카테고리 ID (선택적 필터)
   */
  getTimeDealProducts: (params?: {
    limit?: number
    category_id?: number
  }) =>
    apiClient.get<TimeDealResponse>('/api/recommendations/time-deal/', {
      params: {
        limit: params?.limit ?? 10,
        ...(params?.category_id ? { category_id: params.category_id } : {}),
      },
    }),

  /**
   * 가격 히스토리 조회 (비회원 허용)
   * 폴센트 스타일 가격 추적 그래프용 데이터
   *
   * @param productId 상품 ID
   * @param days 조회 기간 (기본 30일, 7~365일)
   */
  getPriceHistory: (productId: number, days: number = 30) =>
    apiClient.get<PriceHistoryResponse>(`/api/recommendations/price-history/${productId}/`, {
      params: { days },
    }),
}

// ==================== Sellers API ====================
export const sellersAPI = {
  // 판매자 목록
  getSellers: (params?: { search?: string; page?: number }) =>
    apiClient.get('/api/sellers/', { params }),

  // 판매자 상세
  getSeller: (brand_slug: string) =>
    apiClient.get(`/api/sellers/${brand_slug}/`),

  // 자신의 판매자 정보
  getMySellerProfile: () =>
    apiClient.get('/api/sellers/me/'),

  // 판매자 등록
  registerAsSeller: (data: {
    brand_name: string
    brand_name_en?: string
    brand_description?: string
    brand_logo_url?: string
    brand_banner_url?: string
    business_registration_number?: string
    business_type?: string
    company_name?: string
    ceo_name?: string
    business_phone?: string
    business_email?: string
    customer_service_phone?: string
    business_address?: string
    warehouse_address?: string
    bank_name?: string
    bank_account_number?: string
    account_holder_name?: string
    verification_document_url?: string
  }) => apiClient.post('/api/sellers/register/', data),

  // 판매자 정보 수정
  updateSeller: (brand_slug: string, data: any) =>
    apiClient.patch(`/api/sellers/${brand_slug}/`, data),

  // 판매자 대시보드
  getDashboard: () =>
    apiClient.get('/api/sellers/dashboard/'),

  // ?ë§¤???´ë?ì§€ ?…ë¡œ??
  uploadSellerImage: (image: File, imageType: 'profile' | 'logo' | 'banner') => {
    const formData = new FormData()
    formData.append('image', image)
    formData.append('image_type', imageType)

    return apiClient.post(
      '/api/sellers/me/images/upload/',
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    )
  },
}

// ==================== Seller Products API ====================
export const sellerProductsAPI = {
  // 자신의 상품 목록
  getMyProducts: (params?: { page?: number; page_size?: number }) =>
    apiClient.get('/api/seller-products/', { params }),

  // 자신의 상품 상세
  getMyProduct: (id: number) =>
    apiClient.get(`/api/seller-products/${id}/`),

  // 상품 등록 (draft)
  createProduct: (data: {
    name: string
    price: number
    slug?: string
    original_price?: number
    category_id?: number
    full_description?: string
    short_description?: string
    stock_quantity?: number
    unit?: string
    description?: string
  }) => apiClient.post('/api/seller-products/', data),

  // 상품 수정
  updateProduct: (id: number, data: any) =>
    apiClient.patch(`/api/seller-products/${id}/`, data),

  // 상품 삭제
  deleteProduct: (id: number) =>
    apiClient.delete(`/api/seller-products/${id}/`),

  // 상품 발행 (draft → active)
  publishProduct: (id: number) =>
    apiClient.post(`/api/seller-products/${id}/publish/`),

  // 상품 비공개 (active → inactive)
  unpublishProduct: (id: number) =>
    apiClient.post(`/api/seller-products/${id}/unpublish/`),

  // 상품 이미지 추가
  addProductImages: (product_id: number, images: Array<{
    image_url: string
    alt_text?: string
    display_order?: number
  }>) => apiClient.post(`/api/seller-products/${product_id}/images/`, { images }),

  // 상품 메인 이미지 업로드 (S3)
  uploadProductImages: (product_id: number, files: File[]) => {
    const formData = new FormData()
    files.forEach((file) => formData.append('images', file))

    return apiClient.post(
      `/api/seller-products/${product_id}/images/upload/`,
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    )
  },

  // 상품 상세 설명 이미지 업로드 (S3)
  uploadProductDetailImages: (product_id: number, files: File[]) => {
    const formData = new FormData()
    files.forEach((file) => formData.append('images', file))

    return apiClient.post(
      `/api/seller-products/${product_id}/detail-images/upload/`,
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    )
  },

  // 상품 이미지 삭제
  deleteProductImage: (product_id: number, image_id: number) =>
    apiClient.delete(`/api/seller-products/${product_id}/images/${image_id}/`),
}

// ==================== Seller Orders API ====================
export const sellerOrdersAPI = {
  // 판매자 상품 기준 주문 항목 목록
  getOrderItems: (params?: { status?: string; page?: number; page_size?: number }) =>
    apiClient.get('/api/sellers/orders/', { params }),

  // 상태별 개수 요약
  getSummary: () => apiClient.get('/api/sellers/orders/summary/'),

  // 주문 항목 상태 변경
  updateStatus: (id: number, status: string) =>
    apiClient.patch(`/api/sellers/orders/${id}/status/`, { status }),
}

// ==================== Payments API (토스페이먼츠 PG) ====================
export const paymentsAPI = {
  /**
   * 결제 준비 (주문 생성 + PG 초기화)
   * 장바구니 기반 주문을 생성하고 토스 SDK 초기화 데이터를 반환
   */
  prepare: (data: PaymentPrepareRequest) =>
    apiClient.post<PaymentPrepareResponse>('/api/orders/payments/prepare/', data),

  /**
   * 결제 승인
   * 토스 SDK 결제 완료 후 호출 (paymentKey, orderId, amount)
   */
  confirm: (data: PaymentConfirmRequest) =>
    apiClient.post<PaymentConfirmResponse>('/api/orders/payments/confirm/', data),

  /**
   * 결제 상태 조회
   */
  getStatus: (paymentId: number) =>
    apiClient.get<Payment>(`/api/orders/payments/${paymentId}/`),

  /**
   * 결제 취소
   */
  cancel: (paymentId: number, cancelReason: string) =>
    apiClient.post<PaymentCancelResponse>(`/api/orders/payments/${paymentId}/cancel/`, {
      cancel_reason: cancelReason,
    }),
}

// 전체 API를 하나의 객체로 export
export const api = {
  auth: authAPI,
  addresses: addressesAPI,
  products: productsAPI,
  wishlist: wishlistAPI,
  cart: cartAPI,
  orders: ordersAPI,
  guestOrders: guestOrdersAPI,
  payments: paymentsAPI,
  recommendations: recommendationsAPI,
  sellers: sellersAPI,
  sellerProducts: sellerProductsAPI,
  sellerOrders: sellerOrdersAPI,
  analytics: analyticsAPI,
  adminAnalytics: adminAnalyticsAPI,
}

export default api
