import type { Product } from '@/types/product'

export type SellerBadge = {
  name: string
  avatar?: string
  rating?: number | null
  type?: string
}

export function createMockProduct(input: {
  id: number
  slug: string
  name: string
  price: number
  category_name?: string | null
  main_image?: string | null
  original_price?: number | null
  view_count?: number
  product_type?: 'main' | 'seller'
  status?: 'active' | 'inactive' | 'draft' | 'out_of_stock' | 'discontinued'
  average_rating?: number
  review_count?: number
  wishlist_count?: number
  quality_score?: number
  created_at?: string
}): Product {
  return {
    id: input.id,
    slug: input.slug,
    name: input.name,
    price: input.price,
    original_price: input.original_price ?? null,
    unit: null,
    main_image: input.main_image ?? null,
    category: null,
    category_name: input.category_name ?? null,
    status: input.status ?? 'active',
    product_type: input.product_type ?? 'main',
    created_at: input.created_at ?? '2023-01-01T00:00:00Z',
    view_count: input.view_count ?? 0,
    average_rating: input.average_rating ?? 0,
    review_count: input.review_count ?? 0,
    wishlist_count: input.wishlist_count ?? 0,
    quality_score: input.quality_score ?? 80
  }
}
