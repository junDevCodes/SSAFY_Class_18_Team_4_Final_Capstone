<template>
  <div class="product-detail-page">
    <div v-if="loading" class="loading">로딩중...</div>
    <div v-else-if="error" class="error">
      <p>{{ error }}</p>
      <button @click="$router.back()">뒤로가기</button>
    </div>

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
            <div v-if="stockLeftLabel" class="stock-row">
              <span
                :class="[
                  'stock-pill',
                  { low: !isSoldOut && stockQuantity !== null && stockQuantity <= 5, soldout: isSoldOut }
                ]"
              >
                {{ stockLeftLabel }}
              </span>
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
            <div class="qty-control" :class="{ disabled: isSoldOut }">
              <button @click="quantity = Math.max(1, quantity - 1)" :disabled="quantity <= 1 || isSoldOut">-</button>
              <input
                type="number"
                :value="quantity"
                min="1"
                :disabled="isSoldOut"
                @input="quantity = Math.max(1, Number(($event.target as HTMLInputElement).value) || 1)"
              />
              <button @click="quantity = quantity + 1" :disabled="isSoldOut">+</button>
            </div>
            <button
              class="wish"
              type="button"
              @click="toggleWishlist"
              :aria-pressed="product.is_wishlist"
              :disabled="isTogglingWish"
            >
              <span class="heart" :class="{ filled: product.is_wishlist }">
                {{ product.is_wishlist ? '♥' : '♡' }}
              </span>
              <span v-if="showWishCount" class="wish-count">{{ wishlistCount }}</span>
            </button>
          </div>

          <div class="cta-row">
            <button class="btn-buy" @click="buyNow" :disabled="isSoldOut">
              {{ isSoldOut ? '품절' : '바로구매' }}
            </button>
            <button class="btn-cart" @click="addToCart" :disabled="isSoldOut">
              {{ isSoldOut ? '품절' : '장바구니 담기' }}
            </button>
          </div>
        </div>
      </div>

      <!-- 하단 섹션(탭/연관상품/스티키바) -->
      <div class="section" id="detail">
        <ProductInfoTabs
          :product="product"
          :short-description="shortDescription"
          :full-description="fullDescription"
          :detail-images="detailImages"
          :initial-tab="initialTab"
        >
          <template #review>
            <div class="section" id="reviews">
              <ReviewsSection
                :product-id="product.id"
                :initial-average="product.stats?.average_rating ?? 0"
                :initial-count="product.stats?.review_count ?? 0"
                :initial-edit-review-id="initialEditReviewId"
              />
            </div>
          </template>
        </ProductInfoTabs>
      </div>

      <section class="section" id="shipping">
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
        :product="product"
        :discount-rate="discountRate"
        :quantity="quantity"
        :sold-out="isSoldOut"
        :stock-label="stockLeftLabel"
        @change-qty="quantity = $event"
        @toggle-wish="toggleWishlist"
        @add-cart="addToCart"
        @buy-now="buyNow"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { productsAPI } from '@/services/api'
import { useCartStore } from '@/stores/cart'
import { useWishlistStore } from '@/stores/wishlist'
import { useAuthStore } from '@/stores/auth'
import {
  calculateDiscountRate,
  formatPrice,
  getFullImageDescription,
  getFullTextDescription,
  type ProductDetail
} from '@/types/product'
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
const showWishCount = ref(false)
const isTogglingWish = ref(false)

const initialTab = computed(() => {
  const tabParam = route.query.tab
  if (tabParam === 'review') return 'review'
  if (route.query.editReviewId) return 'review'
  return 'detail'
})

const initialEditReviewId = computed(() => {
  const raw = route.query.editReviewId
  const num = Number(raw)
  return Number.isFinite(num) ? num : null
})

const discountRate = computed(() => {
  if (!product.value) return 0
  return calculateDiscountRate(product.value.original_price ?? 0, product.value.price)
})

const isSellerOutOfStock = (p: ProductDetail | null) => {
  if (!p || p.product_type !== 'seller') return false
  const stock = p.inventory?.stock_quantity
  if (stock === null) return true
  if (typeof stock === 'number') return stock <= 0
  return false
}

const stockQuantity = computed(() => {
  if (!product.value || product.value.product_type !== 'seller') return null
  const stock = product.value.inventory?.stock_quantity
  return typeof stock === 'number' ? stock : null
})

const isSoldOut = computed(() => isSellerOutOfStock(product.value))
const stockLeftLabel = computed(() => {
  if (!product.value || product.value.product_type !== 'seller') return null
  const stock = product.value.inventory?.stock_quantity
  if (stock === null || stock === 0) return '품절'
  if (typeof stock === 'number' && stock <= 20) return `${stock}개 남음`
  return null
})



const shortDescription = computed(() => product.value?.detail?.short_description ?? null)
const fullDescription = computed(() => {
  if (!product.value) return null
  return (
    getFullTextDescription(product.value) ??
    product.value.detail?.full_description ??
    product.value.detail?.short_description ??
    null
  )
})
const detailImages = computed(() => (product.value ? getFullImageDescription(product.value) : []))
const wishlistCount = computed(() => product.value?.stats?.wishlist_count ?? 0)

watch(
  () => route.params.slug,
  async () => {
    quantity.value = 1
    showWishCount.value = false
    isTogglingWish.value = false
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
  if (isSoldOut.value) {
    alert('품절된 상품은 장바구니에 담을 수 없습니다.')
    return
  }
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
  if (isTogglingWish.value) return
  if (!product.value) return
  try {
    isTogglingWish.value = true
    const result = await wishlistStore.toggleWishlist(product.value as any)
    product.value.is_wishlist = result.isWishlisted
    if (product.value.stats) {
      product.value.stats.wishlist_count = result.wishlistCount
    }
    showWishCount.value = true
  } catch (err) {
    alert('찜 처리에 실패했습니다.')
  } finally {
    isTogglingWish.value = false
  }
}

function buyNow() {
  if (isSoldOut.value) {
    alert('품절된 상품은 구매할 수 없습니다.')
    return
  }
  addToCart()
  router.push('/checkout')
}
</script>

<style scoped>
.sticky-buy-panel { position: sticky; top: calc(var(--app-content-top, 0px) + 16px); }
.section { margin-top: 48px; }
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
.qty-control.disabled { opacity: 0.6; }
.wish { padding: 10px 14px; border: 1px solid #d1d5db; border-radius: 8px; background: white; cursor: pointer; display: inline-flex; align-items: center; justify-content: center; gap: 6px; }
.wish:disabled { cursor: not-allowed; opacity: 0.7; }
.wish .heart { color: #d1d5db; font-size: 18px; line-height: 1; }
.wish .heart.filled { color: #d14343; }
.wish-count { font-size: 12px; color: #374151; }
.cta-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.btn-buy { padding: 14px; border: none; border-radius: 10px; background: #2d5016; color: white; font-weight: 700; cursor: pointer; }
.btn-cart { padding: 14px; border: 1px solid #2d5016; border-radius: 10px; background: white; color: #2d5016; font-weight: 700; cursor: pointer; }
.related { margin-top: 40px; }
.related h2 { font-weight: 800; margin-bottom: 16px; }
.related-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 16px; }
.loading, .error { text-align: center; padding: 3rem; }
.stock-row { margin-top: 10px; }
.stock-pill { display: inline-flex; align-items: center; gap: 6px; padding: 6px 10px; border-radius: 999px; font-weight: 700; font-size: 13px; background: #e8f8ef; color: #0f3a2a; }
.stock-pill.low { background: #fff5e6; color: #b45309; }
.stock-pill.soldout { background: #f3f4f6; color: #6b7280; text-decoration: line-through; }
@media (max-width: 1024px) { .detail-grid { grid-template-columns: 1fr; } .cta-row { grid-template-columns: 1fr; } .sticky-tabs { top: 0; } .sticky-buy-panel { position: static; } }
</style>
