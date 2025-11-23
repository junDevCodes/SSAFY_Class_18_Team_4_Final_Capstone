/**
 * 통합 API 서비스
 * 모든 백엔드 API 엔드포인트를 중앙에서 관리
 */
import apiClient from './client'
import type {
  LoginRequest,
  RegisterRequest,
  LoginResponse,
  User,
  RegisterResponse
} from '@/types/auth'
import type { Product, ProductDetail } from '@/types/product'

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

// ==================== Products API ====================
export const productsAPI = {
  // 상품 목록 (필터링, 검색, 정렬)
  getProducts: (params?: {
    category?: number
    price__gte?: number
    price__lte?: number
    is_featured?: boolean
    is_best?: boolean
    is_new?: boolean
    is_on_sale?: boolean
    search?: string
    ordering?: string
    page?: number
    page_size?: number
  }) => apiClient.get<{
    count: number
    next: string | null
    previous: string | null
    results: Product[]
  }>('/api/products/', { params }),

  // 상품 상세
  getProduct: (slug: string) =>
    apiClient.get<ProductDetail>(`/api/products/${slug}/`),

  // 카테고리 목록
  getCategories: () =>
    apiClient.get('/api/categories/'),
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
    category_id?: number
    description?: string
    short_description?: string
    main_image_url?: string
    stock_quantity?: number
    unit?: string
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

  // 상품 이미지 삭제
  deleteProductImage: (product_id: number, image_id: number) =>
    apiClient.delete(`/api/seller-products/${product_id}/images/${image_id}/`),
}

// 전체 API를 하나의 객체로 export
export const api = {
  auth: authAPI,
  products: productsAPI,
  wishlist: wishlistAPI,
  cart: cartAPI,
  orders: ordersAPI,
  sellers: sellersAPI,
  sellerProducts: sellerProductsAPI,
}

export default api
