<template>
  <div class="product-detail-page">
    <!-- 로딩 상태 -->
    <div v-if="loading" class="loading">로딩중...</div>

    <!-- 에러 상태 -->
    <div v-else-if="error" class="error">
      <p>{{ error }}</p>
      <button @click="$router.back()">뒤로가기</button>
    </div>

    <!-- 본문 -->
    <div v-else-if="product">
      <!-- 네비게이션/카테고리 경로 -->
      <div class="breadcrumb">
        홈 > {{ product.category?.name || '카테고리' }} > {{ product.name }}
      </div>

      <!-- 상단 요약: 이미지 갤러리 + 가격/혜택/CTA -->
      <section class="summary-grid">
        <ProductGallery :product="product" />
        <ProductSummary
          :product="product"
          :discount-rate="discountRate"
          :wishlist-count="wishlistCount"
          :quantity="quantity"
          @change-qty="quantity = $event"
          @toggle-wish="toggleWishlist"
          @add-cart="addToCart"
          @buy-now="buyNow"
        />
      </section>

      <!-- 상세/상품정보 탭 -->
      <ProductInfoTabs
        :product="product"
        :short-description="shortDescription"
        :full-description="fullDescription"
      />

      <!-- 연관 상품 영역 -->
      <section v-if="product.related_products?.length" class="related">
        <h2>연관 상품</h2>
        <div class="related-grid">
          <ProductCard
            v-for="item in product.related_products"
            :key="item.id"
            :product="item"
          />
        </div>
      </section>

      <!-- 하단 스티키 구매 바 (모바일/스크롤 시 CTA) -->
      <StickyPurchaseBar
        :product="product"
        :discount-rate="discountRate"
        :quantity="quantity"
        @change-qty="quantity = $event"
        @toggle-wish="toggleWishlist"
        @add-cart="addToCart"
        @buy-now="buyNow"
      />
    </div>
  </div>
</template>


<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { productsAPI } from '@/services/api'
import { useCartStore } from '@/stores/cart'
import { useWishlistStore } from '@/stores/wishlist'
import { useAuthStore } from '@/stores/auth'
import { calculateDiscountRate, type ProductDetail } from '@/types/product'
import ProductCard from '@/components/ui/ProductCard.vue'

/* Product 상세페이지를 구현하기 위한 import */
import ProductGallery from '@/components/product/ProductGallery.vue'
import ProductSummary from '@/components/product/ProductSummary.vue'
import ProductInfoTabs from '@/components/product/ProductInfoTabs.vue'
import StickyPurchaseBar from '@/components/product/StickyPurchaseBar.vue'

const route = useRoute()
const router = useRouter()
const cartStore = useCartStore()
const wishlistStore = useWishlistStore()
const authStore = useAuthStore()

const product = ref<ProductDetail | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
const quantity = ref(1)

// v2.1: 계산된 할인율 (원가 대비 현재 가격)
const discountRate = computed(() => {
  if (!product.value) return 0
  return calculateDiscountRate(product.value.original_price ?? 0, product.value.price)
})

// v2.1: 상품 설명 (detail 테이블에서 가져오기)
const shortDescription = computed(() => {
  return product.value?.detail?.short_description ?? null
})

// v2.1: 상세 설명 (detail 테이블에서 가져오기)
const fullDescription = computed(() => {
  return product.value?.detail?.full_description ?? null
})

// v2.1: 찜 수 (stats 테이블에서 가져오기)
const wishlistCount = computed(() => {
  return product.value?.stats?.wishlist_count ?? 0
})

onMounted(async () => {
  await loadProduct()
})

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
    // v2.1: 서버에서 반환된 정확한 wishlist_count를 stats에 반영
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
.product-detail-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem 1rem;
}

.loading, .error {
  text-align: center;
  padding: 3rem;
}

.breadcrumb { 
  font-size: 14px; 
  color: #6b7280; 
  margin-bottom: 16px; 
}

.summary-grid { 
  display: grid; 
  grid-template-columns: 1.1fr 0.9fr; 
  gap: 24px; align-items: start; 
  margin-bottom: 32px; 
}

.related { 
  margin-top: 40px; 
}

.related h2 { 
  font-weight: 800; 
  margin-bottom: 16px; 
}

.related-grid { 
  display: grid; 
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); 
  gap: 16px; 
}

.product-main {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 3rem;
  margin-bottom: 3rem;
}

.product-images img {
  width: 100%;
  border-radius: 8px;
}

.product-name {
  font-size: 1.8rem;
  margin-bottom: 1rem;
}

.product-price {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1rem;
}

.original-price {
  text-decoration: line-through;
  color: #999;
}

.current-price {
  font-size: 2rem;
  font-weight: bold;
  color: #2d5016;
}

.discount-rate {
  color: #e63946;
  font-weight: bold;
}

.product-description {
  color: #666;
  margin-bottom: 1.5rem;
}

.product-meta {
  border-top: 1px solid #eee;
  border-bottom: 1px solid #eee;
  padding: 1.5rem 0;
  margin-bottom: 1.5rem;
}

.meta-item {
  display: flex;
  padding: 0.5rem 0;
}

.meta-item .label {
  width: 100px;
  color: #666;
}

.quantity-selector {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.quantity-selector button {
  padding: 0.5rem 1rem;
  border: 1px solid #ddd;
  background: white;
  cursor: pointer;
}

.quantity-selector input {
  width: 60px;
  text-align: center;
  border: 1px solid #ddd;
  padding: 0.5rem;
}

.product-actions {
  display: grid;
  grid-template-columns: auto 1fr 2fr;
  gap: 0.5rem;
}

.btn-wishlist, .btn-cart, .btn-buy {
  padding: 1rem;
  border: 1px solid #ddd;
  background: white;
  cursor: pointer;
  font-weight: bold;
}

.btn-wishlist.active {
  color: #e63946;
}

.btn-cart {
  background: #2d5016;
  color: white;
  border: none;
}

.btn-buy {
  background: #a8d08d;
  border: none;
}

.product-tabs {
  margin-top: 3rem;
}

.tabs {
  display: flex;
  border-bottom: 2px solid #eee;
}

.tabs button {
  padding: 1rem 2rem;
  border: none;
  background: none;
  cursor: pointer;
  font-weight: bold;
}

.tabs button.active {
  border-bottom: 2px solid #2d5016;
  color: #2d5016;
}

.tab-content {
  padding: 2rem 0;
}

.info-content table {
  width: 100%;
  border-collapse: collapse;
}

.info-content th,
.info-content td {
  padding: 1rem;
  border-bottom: 1px solid #eee;
  text-align: left;
}

.info-content th {
  width: 150px;
  background: #f9f9f9;
  font-weight: bold;
}

.related-products {
  margin-top: 3rem;
}

.related-products h2 {
  margin-bottom: 1.5rem;
}

.products-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 1.5rem;
}

@media (max-width: 1024px) { 
  .summary-grid { 
    grid-template-columns: 1fr; 
  } 
}

@media (max-width: 768px) {
  .product-main {
    grid-template-columns: 1fr;
  }

  .product-actions {
    grid-template-columns: 1fr;
  }
}
</style>
