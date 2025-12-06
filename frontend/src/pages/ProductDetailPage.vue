<template>
  <div class="product-detail-page">
    <!-- 로딩 상태 (기존 유지) -->
    <div v-if="loading" class="loading">로딩중...</div>

    <!-- 에러 상태 (기존 유지) -->
    <div v-else-if="error" class="error">
      <p>{{ error }}</p>
      <button @click="$router.back()">뒤로가기</button>
    </div>

    <!-- 본문: 마트쇼핑몰형 2컬럼 레이아웃 -->
    <div v-else-if="product">
      

      <div class="detail-grid">
      <!-- 좌측: 이미지 갤러리 -->
      <div class="gallery-wrap">
        <ProductGallery :product="product" />
      </div>

      <!-- 우측: 정보/CTA -->
      <div class="info-wrap sticky-buy-panel">
        <p class="brand" v-if="product.seller?.brand_name">{{ product.seller.brand_name }}</p>
        <h1 class="title">{{ product.name }}</h1>

        <div class="price-box">
          <div class="price-main">
            <span v-if="product.original_price && discountRate > 0" class="original">
              {{ formatPrice(product.original_price) }}
            </span>
            <div class="current">
              <span v-if="discountRate > 0" class="discount">{{ discountRate }}%</span>
              <span class="now">{{ formatPrice(product.price) }}</span>
            </div>
          </div>
        </div>

        <div class="meta-box">
          <div class="meta-row">
            <span class="label">배송비</span>
            <span class="value">
              {{ product.shipping_fee > 0 ? formatPrice(product.shipping_fee) : '무료배송' }}
            </span>
          </div>
          <div class="meta-row" v-if="product.free_shipping_threshold">
            <span class="label">무료배송</span>
            <span class="value">{{ formatPrice(product.free_shipping_threshold) }} 이상 구매 시</span>
          </div>
          <div class="meta-row" v-if="product.unit">
            <span class="label">판매단위</span>
            <span class="value">{{ product.unit }}</span>
          </div>
        </div>

        <div class="qty-like">
          <div class="qty-control">
            <button @click="quantity = Math.max(1, quantity - 1)">-</button>
            <input
              type="number"
              :value="quantity"
              min="1"
              @input="quantity = Math.max(1, Number(($event.target as HTMLInputElement).value) || 1)"
            />
            <button @click="quantity = quantity + 1">+</button>
          </div>
          <button class="wish" @click="toggleWishlist">
            {{ product.is_wishlist ? '♡ 취소' : '♡ 찜' }} ({{ wishlistCount }})
          </button>
        </div>

        <div class="cta-row">
          <button class="btn-buy" @click="buyNow">바로구매</button>
          <button class="btn-cart" @click="addToCart">장바구니 담기</button>
        </div>
      </div>
    </div>
    </div>

    <!-- 하단 섹션(탭/연관상품/스티키바) 유지 -->
    <div v-if="product" class="section" id="detail">
      <ProductInfoTabs
        :product="product"
        :short-description="shortDescription"
        :full-description="fullDescription"
      />
    </div>

    <div v-if="product" class="section" id="reviews">
      <ReviewsSection :reviews="reviews" :average="averageRating" :count="reviewCount" />
    </div>

    <section v-if="product" class="section" id="shipping">
      <h2>배송/교환/반품</h2>
      <p>배송·교환·반품 정보는 준비 중입니다.</p>
    </section>

    <section v-if="product?.related_products?.length" class="related section">
      <h2>연관 상품</h2>
      <div class="related-grid">
        <ProductCard v-for="item in product.related_products" :key="item.id" :product="item" />
      </div>
    </section>
    <StickyPurchaseBar
      v-if="product"
      :product="product"
      :discount-rate="discountRate"
      :quantity="quantity"
      @change-qty="quantity = $event"
      @toggle-wish="toggleWishlist"
      @add-cart="addToCart"
      @buy-now="buyNow"
    />
  </div>
</template>

<script setup lang="ts">

// 리뷰 타입 정의 (파일 상단 script setup 안)
type Review = {
  id: number
  rating: number
  content: string
  author: string
  date: string
  images?: string[]
}

import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { productsAPI } from '@/services/api'
import { useCartStore } from '@/stores/cart'
import { useWishlistStore } from '@/stores/wishlist'
import { useAuthStore } from '@/stores/auth'
import { calculateDiscountRate, formatPrice, type ProductDetail } from '@/types/product'
import ProductCard from '@/components/ui/ProductCard.vue'
import ProductGallery from '@/components/product/ProductGallery.vue'
import ProductInfoTabs from '@/components/product/ProductInfoTabs.vue'
import StickyPurchaseBar from '@/components/product/StickyPurchaseBar.vue'
import ReviewsSection from '@/components/product/ReviewsSection.vue'

const route = useRoute()
const router = useRouter()
const cartStore = useCartStore()
const wishlistStore = useWishlistStore()
const authStore = useAuthStore()

const product = ref<ProductDetail | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
const quantity = ref(1)


const discountRate = computed(() => {
  if (!product.value) return 0
  return calculateDiscountRate(product.value.original_price ?? 0, product.value.price)
})

const shortDescription = computed(() => product.value?.detail?.short_description ?? null)
const fullDescription = computed(() => product.value?.detail?.full_description ?? null)
const wishlistCount = computed(() => product.value?.stats?.wishlist_count ?? 0)





// 리뷰 상태 (기존 reviews 선언 위치 교체)
const reviews = ref<Review[]>([
  {
    id: 1,
    rating: 5,
    content: '맛있고 배송이 빨라요',
    author: 'user1',
    date: '2025.01.01',
    images: []
  },
  {
    id: 2,
    rating: 4,
    content: '구성이 좋아요',
    author: 'user2',
    date: '2025.01.02',
    images: []
  }
])

// 평균 계산 (acc, r 타입 명시)
const averageRating = computed(() => {
  if (!reviews.value.length) return 0
  const sum = reviews.value.reduce((acc: number, r: Review) => acc + (r.rating ?? 0), 0)
  return sum / reviews.value.length
})
const reviewCount = computed(() => reviews.value.length)

// slug 변경 시마다 재로딩 + 초기화 + 스크롤
watch(
  () => route.params.slug,
  async () => {
    quantity.value = 1
    await loadProduct()
    window.scrollTo({ top: 0, behavior: 'auto' })
  },
  { immediate: true }
)

async function loadProduct() {
  loading.value = true
  error.value = null
  try {
    const slug = route.params.slug as string
    const response = await productsAPI.getProduct(slug)
    product.value = response.data
  } catch (err: any) {
    error.value = err.response?.data?.detail || '상품을 불러오는데 실패했습니다.'
  } finally {
    loading.value = false
  }
}

async function addToCart() {
  if (!authStore.isAuthenticated) {
    window.dispatchEvent(new CustomEvent('auth:required'))
    return
  }
  if (!product.value) return
  try {
    await cartStore.addToCart(product.value as any, quantity.value)
    alert('장바구니에 담았습니다.')
  } catch (err) {
    alert('장바구니 담기에 실패했습니다.')
  }
}

async function toggleWishlist() {
  if (!authStore.isAuthenticated) {
    window.dispatchEvent(new CustomEvent('auth:required'))
    return
  }
  if (!product.value) return
  try {
    const result = await wishlistStore.toggleWishlist(product.value as any)
    product.value.is_wishlist = result.isWishlisted
    if (product.value.stats) {
      product.value.stats.wishlist_count = result.wishlistCount
    }
  } catch (err) {
    alert('찜 처리에 실패했습니다.')
  }
}

function buyNow() {
  addToCart()
  router.push('/checkout')
}


</script>

<style scoped>

.sticky-buy-panel {
  position: sticky;
  top: calc(var(--app-content-top, 0px) + 16px);
}
.section {
  margin-top: 48px;
}
.product-detail-page { max-width: 1200px; margin: 0 auto; padding: 2rem 1.5rem; }
.detail-grid { display: grid; grid-template-columns: 1.1fr 0.9fr; gap: 32px; align-items: start; margin-bottom: 32px; }
.gallery-wrap { background: white; border-radius: 12px; padding: 12px; }
.info-wrap { background: white; border-radius: 12px; padding: 20px; box-shadow: 0 6px 20px rgba(0,0,0,0.04); display: flex; flex-direction: column; gap: 16px; }
.brand { color: #0f3a2a; font-weight: 700; }
.title { font-size: 26px; font-weight: 800; color: #1a1a1a; line-height: 1.3; }
.price-box { border-bottom: 1px solid #e5e7eb; padding-bottom: 12px; }
.price-main { display: flex; flex-direction: column; gap: 6px; }
.original { text-decoration: line-through; color: #9ca3af; font-size: 14px; }
.current { display: flex; align-items: center; gap: 8px; }
.discount { color: #d32f2f; font-weight: 800; font-size: 18px; }
.now { font-size: 28px; font-weight: 800; color: #0f3a2a; }
.meta-box { display: flex; flex-direction: column; gap: 8px; }
.meta-row { display: flex; justify-content: space-between; font-size: 14px; color: #111827; }
.label { color: #6b7280; }
.qty-like { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
.qty-control { display: inline-flex; border: 1px solid #d1d5db; border-radius: 8px; overflow: hidden; }
.qty-control button { width: 38px; height: 38px; border: none; background: white; cursor: pointer; }
.qty-control input { width: 60px; text-align: center; border: none; outline: none; }
.wish { padding: 10px 14px; border: 1px solid #d1d5db; border-radius: 8px; background: white; cursor: pointer; }
.cta-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.btn-buy { padding: 14px; border: none; border-radius: 10px; background: #2d5016; color: white; font-weight: 700; cursor: pointer; }
.btn-cart { padding: 14px; border: 1px solid #2d5016; border-radius: 10px; background: white; color: #2d5016; font-weight: 700; cursor: pointer; }
.related { margin-top: 40px; }
.related h2 { font-weight: 800; margin-bottom: 16px; }
.related-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 16px; }
.loading, .error { text-align: center; padding: 3rem; }
@media (max-width: 1024px) { .detail-grid { grid-template-columns: 1fr; } .cta-row { grid-template-columns: 1fr; } .sticky-tabs { top: 0; } .sticky-buy-panel { position: static; } }
</style>
