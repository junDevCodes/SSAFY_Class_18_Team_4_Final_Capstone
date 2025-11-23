// 상품 타입 정의
export interface Category {
  id: number
  name: string
  slug: string
  created_at: string
  updated_at: string
}

export interface Product {
  id: number
  category: Category | null
  site_name: string | null
  name: string
  price: number
  unit: string | null
  description: string | null
  product_url: string | null
  image_url: string
  detail_info: string | null
  crawled_at: string | null
  original_price: number | null
  discount: number
  is_best: boolean
  created_at: string
  updated_at: string
}

export interface CartItem extends Product {
  qty: number
}

export interface ProductListResponse {
  count: number
  next: string | null
  previous: string | null
  results: Product[]
}

export interface CategoryListResponse {
  count: number
  next: string | null
  previous: string | null
  results: Category[]
}

