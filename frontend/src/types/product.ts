/**
 * Product 타입 정의 - 백엔드 API 응답과 일치
 *
 * v2.1: ProductDetailInfo, ProductInventory, ProductStats, ProductPriceHistory 지원
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

// 상품 이미지 - 백엔드 ProductImage 모델과 일치 (ERD V2.1)
export interface ProductImage {
  id: number
  image_url: string
  display_order: number
  created_at: string
}

// ========================= v2.1 신규 타입 =========================

// 상품 상세 정보 (v2.1 분리 테이블)
export interface ProductDetailInfo {
  short_description: string | null
  full_description: string | null
  meta_title: string | null
  meta_keywords: string | null
}

// 상품 재고 정보 (v2.1 분리 테이블)
export interface ProductInventory {
  stock_quantity: number
  safe_stock_level: number
  is_low_stock: boolean
  updated_at: string
}

// 상품 통계 정보 (v2.1 분리 테이블)
export interface ProductStats {
  view_count: number
  recommend_clicked_count: number
  cart_event_count: number
  order_event_count: number
  wishlist_count: number
  review_count: number
  average_rating: number
  photo_review_count: number
  quality_score: number
  last_updated: string
}

// 가격 변동 이력 (v2.1 신규) - 백엔드 ProductPriceHistory 모델과 일치
export interface ProductPriceHistory {
  price: number               // 해당 시점의 가격
  original_price: number | null  // 해당 시점의 원가 (할인 전 가격)
  recorded_at: string         // 기록 시각
  source?: string | null      // 변경 출처 (import, manual, crawl 등)
}

// 상품 목록용 (간소화) - 백엔드 ProductListSerializerV2와 일치
export interface Product {
  id: number
  slug: string
  name: string
  price: number
  original_price: number | null
  unit: string | null
  main_image: string | null          // ProductImage에서 display_order가 가장 낮은 이미지
  category?: Category | null
  category_name: string | null
  status: 'active' | 'inactive' | 'draft' | 'out_of_stock' | 'discontinued'
  product_type: 'main' | 'seller'
  created_at: string

  // v2.1 ProductStats에서 가져오는 통계 정보
  view_count: number
  average_rating: number
  review_count: number
  wishlist_count: number
  quality_score: number

  // 계산된 할인율 (프론트엔드에서 계산)
  discount_rate?: number
}

// 상품 상세 (v2.1 - 분리 테이블 포함) - 백엔드 ProductDetailSerializerV2와 일치
export interface ProductDetail {
  // 기본 정보
  id: number
  slug: string
  name: string
  price: number
  original_price: number | null
  unit: string | null

  // 카테고리
  category: Category | null

  // 판매자
  seller: SellerBrief | null
  product_type: 'main' | 'seller'
  status: 'active' | 'inactive' | 'draft' | 'out_of_stock' | 'discontinued'

  // 이미지
  main_image: string | null   // Serializer에서 계산된 메인 이미지
  images: ProductImage[]

  // v2.1 분리 테이블
  detail: ProductDetailInfo | null
  inventory: ProductInventory | null
  stats: ProductStats | null

  // 배송 정보
  shipping_required: boolean
  shipping_fee: number
  free_shipping_threshold: number | null
  estimated_delivery_days: number | null

  // 추가 정보 (Serializer에서 계산)
  is_wishlist: boolean
  related_products: Product[]

  // 크롤링 메타데이터
  source_site?: string | null
  source_url?: string | null
  crawled_at?: string | null

  // 타임스탬프
  created_at: string
  updated_at: string
}

// 레거시 상품 상세 (하위 호환성)
export interface ProductDetailLegacy {
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
  wishlist_count: number
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

// 상품 필터 파라미터 (v2.1 백엔드 호환)
export interface ProductFilterParams {
  // 기본 필터
  category?: number
  price__gte?: number
  price__lte?: number
  status?: 'active' | 'inactive' | 'draft' | 'out_of_stock' | 'discontinued'
  product_type?: 'main' | 'seller'

  // 커스텀 필터 (백엔드 v2.1 지원)
  is_featured?: boolean  // 추천 상품 (quality_score >= 70)
  is_best?: boolean      // 베스트 상품 (조회수/주문수 기준)
  is_new?: boolean       // 신상품 (최근 7일 내 등록)
  is_on_sale?: boolean   // 할인 상품 (original_price > price)

  // 검색 및 정렬
  search?: string
  ordering?: string

  // 페이지네이션
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

// v2.1 타입 가드: 분리 테이블 포함 여부 확인
export function hasV21Tables(product: ProductDetail): boolean {
  return 'detail' in product && 'inventory' in product && 'stats' in product
}

// 기본 이미지 URL
export const DEFAULT_PRODUCT_IMAGE = '/images/default-product.svg'

// 이미지 URL 헬퍼
export function getProductImage(product: Product | ProductDetail): string {
  if ('main_image' in product && product.main_image) {
    return product.main_image
  }
  // 레거시 필드 지원 (eslint-disable로 any 캐스팅 허용)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const productAny = product as any
  if (productAny.main_image_url) {
    return productAny.main_image_url
  }
  if (productAny.image_url) {
    return productAny.image_url
  }
  return DEFAULT_PRODUCT_IMAGE
}

// 가격 포맷 헬퍼
export function formatPrice(price: number | null | undefined): string {
  // null, undefined, NaN 방어
  if (price === null || price === undefined || isNaN(price)) {
    return '0원'
  }
  return new Intl.NumberFormat('ko-KR').format(price) + '원'
}

// 할인율 계산
export function calculateDiscountRate(original: number, current: number): number {
  if (!original || original === current) return 0
  return Math.round(((original - current) / original) * 100)
}

// ========================= v2.1 헬퍼 함수 =========================

// 상품 상세 정보 가져오기 (v2.1 분리 테이블에서)
export function getProductDescription(product: ProductDetail): string | null {
  if (product.detail?.short_description) {
    return product.detail.short_description
  }
  return null
}

// 상품 재고 수량 가져오기 (v2.1)
export function getStockQuantity(product: ProductDetail): number {
  return product.inventory?.stock_quantity ?? 0
}

// 상품 재고 부족 여부 (v2.1)
export function isLowStock(product: ProductDetail): boolean {
  return product.inventory?.is_low_stock ?? false
}

// 상품 통계 가져오기 (v2.1)
export function getProductStats(product: ProductDetail): ProductStats | null {
  return product.stats ?? null
}

// 상품 조회수 가져오기 (v2.1)
export function getViewCount(product: ProductDetail): number {
  return product.stats?.view_count ?? 0
}

// 상품 평균 평점 가져오기 (v2.1)
export function getAverageRating(product: ProductDetail): number {
  return product.stats?.average_rating ?? 0
}

// 상품 리뷰 수 가져오기 (v2.1)
export function getReviewCount(product: ProductDetail): number {
  return product.stats?.review_count ?? 0
}

// 가격 변동 이력 가져오기 (v2.1)
// NOTE: 현재 백엔드 Serializer에서 price_histories를 반환하지 않으므로 빈 배열 반환
// 향후 API 확장 시 별도 엔드포인트로 조회 필요
export function getPriceHistories(_product: ProductDetail): ProductPriceHistory[] {
  // 현재는 ProductDetailSerializerV2에서 price_histories를 포함하지 않음
  // 별도 API 호출 필요: GET /api/products/{id}/price-history/
  return []
}

// 최근 가격 변동률 가져오기 (v2.1)
// 이전 가격과 현재 가격의 차이를 계산하여 변동률 반환
export function getLatestPriceChangeRate(product: ProductDetail): number | null {
  if (!product.stats) return null
  // stats에서 가격 변동 정보가 없으므로 현재 가격과 원가 비교로 계산
  if (product.original_price && product.price !== product.original_price) {
    return Math.round(((product.original_price - product.price) / product.original_price) * 100)
  }
  return null
}

// ========================= 레시피 GapFilling 타입 =========================

// Gap 재료 상품 (부족한 재료에 대응하는 상품)
export interface GapProduct {
  product_id: number
  name: string
  price: number
  original_price: number | null
  main_image: string | null
  ingredient: string  // 해당 재료명
}

// 추천 레시피
export interface RecipeRecommendation {
  recipe_id: number
  name: string           // 요리명 (CKG_NM)
  title: string | null   // 레시피 제목
  match_ratio: number    // 재료 매칭률 (0-1)
  gap_count: number      // 부족한 재료 수
  gap_ingredients: string[]      // 부족한 재료 목록
  matched_ingredients: string[]  // 매칭된 재료 목록
  recommended_products: GapProduct[]  // 추천 상품 목록
  view_count: number     // 레시피 조회수
  matched_dish: string | null    // 상품명에서 검출된 요리명 (예: 삼계탕)
  is_dish_matched: boolean       // 요리명 기반 매칭 여부
}

// 장바구니 레시피 추천 응답
export interface CartRecipeResponse {
  success: boolean
  recipes: RecipeRecommendation[]
  cart_ingredients: string[]     // 인식된 재료 목록
  detected_dishes: string[]      // 상품명에서 검출된 요리명 목록
  total_gap_count: number        // 전체 부족 재료 수
  processing_time_ms: number     // 처리 시간 (ms)
  message: string | null
}

// 레시피 상세 정보
export interface RecipeDetail {
  recipe_id: number
  name: string
  title: string | null
  category: string | null
  cooking_time: number | null
  servings: number | null
  difficulty: string | null
  description: string | null
  view_count: number
  rating: number | null
  ingredients: RecipeIngredient[]
}

// 레시피 재료
export interface RecipeIngredient {
  ingredient_id: number
  name: string
  amount: string | null
  is_main: boolean
}

// 레시피 검색 응답
export interface RecipeSearchResponse {
  recipes: RecipeDetail[]
  total_count: number
  query: string
  category: string | null
}
