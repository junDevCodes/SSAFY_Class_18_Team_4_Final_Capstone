/**
 * Product 타입 정의 - 백엔드 API 응답과 일치
 */

// 카테고리
export interface Category {
  id: number
  name: string
  slug: string
  created_at: string
  updated_at: string
}

// 판매자 간단 정보
export interface SellerBrief {
  brand_name: string
  brand_slug: string
  average_rating: number
  total_products: number
}

// 상품 이미지
export interface ProductImage {
  id: number
  image_url: string
  alt_text: string | null
  display_order: number
  width: number | null
  height: number | null
  format: string | null
}

// 상품 목록용 (간소화)
export interface Product {
  id: number
  slug: string
  name: string
  price: number
  original_price: number | null
  discount_rate: number
  unit: string | null
  main_image: string | null
  category_name: string | null
  is_featured: boolean
  is_best: boolean
  is_new: boolean
  is_on_sale: boolean
  quality_score: number
  view_count: number
  average_rating: number
  review_count: number

  // 레거시 필드 (호환성)
  image_url?: string
  category?: Category | null
  site_name?: string | null
  description?: string | null
  product_url?: string | null
  detail_info?: string | null
  crawled_at?: string | null
  discount?: number
  created_at?: string
  updated_at?: string
}

// 상품 상세
export interface ProductDetail {
  // 기본 정보
  id: number
  slug: string
  name: string
  short_description: string | null
  description: string | null

  // 카테고리
  category: Category | null
  category_name: string | null

  // 판매자
  seller: SellerBrief | null
  product_type: 'main' | 'seller'

  // 가격
  price: number
  original_price: number | null
  discount_rate: number
  final_price: number
  unit: string | null

  // 이미지
  main_image_url: string | null
  image_url: string | null
  images: ProductImage[]

  // 재고 및 상태
  stock_quantity: number
  min_order_quantity: number
  max_order_quantity: number
  status: 'active' | 'inactive' | 'draft' | 'out_of_stock'

  // 특성
  is_featured: boolean
  is_best: boolean
  is_new: boolean
  is_on_sale: boolean
  is_organic: boolean

  // 품질 정보
  quality_score: number
  origin: string | null
  certification: string | null

  // 배송 정보
  shipping_fee: number
  free_shipping_threshold: number | null
  expected_delivery_days: number

  // 통계
  view_count: number
  click_count: number
  purchase_count: number
  average_rating: number
  review_count: number

  // 추가 정보
  is_wishlist: boolean
  related_products: Product[]

  // 상세 정보
  detail_info: string | null
  ingredients: string | null
  nutrition_info: string | null
  storage_method: string | null
  expiration_date: string | null

  // 메타데이터
  product_url: string | null
  site_name: string | null
  crawled_at: string | null
  published_at: string | null
  created_at: string
  updated_at: string
}

// 장바구니 아이템 (백엔드 응답)
export interface CartItem {
  id: number
  product: Product
  quantity: number
  subtotal: number
  created_at: string
  updated_at: string
}

// 찜 아이템
export interface WishlistItem {
  id: number
  product: Product
  created_at: string
}

// 상품 목록 응답
export interface ProductListResponse {
  count: number
  next: string | null
  previous: string | null
  results: Product[]
}

// 카테고리 목록 응답
export interface CategoryListResponse {
  count: number
  next: string | null
  previous: string | null
  results: Category[]
}

// 상품 필터 파라미터
export interface ProductFilterParams {
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
}

// 상품 정렬 옵션
export type ProductOrderingOption =
  | 'price'           // 가격 낮은순
  | '-price'          // 가격 높은순
  | 'created_at'      // 등록일순
  | '-created_at'     // 최신순
  | 'quality_score'   // 품질점수 낮은순
  | '-quality_score'  // 품질점수 높은순
  | 'view_count'      // 조회수 낮은순
  | '-view_count'     // 조회수 높은순
  | 'average_rating'  // 평점 낮은순
  | '-average_rating' // 평점 높은순

// 유틸리티 함수용 타입 가드
export function isProductDetail(product: Product | ProductDetail): product is ProductDetail {
  return 'final_price' in product && 'images' in product
}

// 기본 이미지 URL
export const DEFAULT_PRODUCT_IMAGE = '/images/default-product.svg'

// 이미지 URL 헬퍼
export function getProductImage(product: Product | ProductDetail): string {
  if ('main_image' in product && product.main_image) {
    return product.main_image
  }
  if ('main_image_url' in product && product.main_image_url) {
    return product.main_image_url
  }
  if (product.image_url) {
    return product.image_url
  }
  return DEFAULT_PRODUCT_IMAGE
}

// 가격 포맷 헬퍼
export function formatPrice(price: number): string {
  return new Intl.NumberFormat('ko-KR').format(price) + '원'
}

// 할인율 계산
export function calculateDiscountRate(original: number, current: number): number {
  if (!original || original === current) return 0
  return Math.round(((original - current) / original) * 100)
}
