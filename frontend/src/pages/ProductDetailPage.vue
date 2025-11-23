<template>
  <div class="product-detail-page">
    <div v-if="loading" class="loading">
      <p>로딩 중...</p>
    </div>

    <div v-else-if="error" class="error">
      <p>{{ error }}</p>
      <button @click="$router.back()">돌아가기</button>
    </div>

    <div v-else-if="product" class="product-detail">
      <!-- 상품 이미지 & 정보 -->
      <div class="product-main">
        <div class="product-images">
          <img
            :src="getProductImage(product)"
            :alt="product.name"
            @error="handleImageError"
          />
        </div>

        <div class="product-info">
          <h1 class="product-name">{{ product.name }}</h1>

          <div class="product-price">
            <span v-if="product.original_price && product.discount_rate > 0" class="original-price">
              {{ formatPrice(product.original_price) }}
            </span>
            <span class="current-price">{{ formatPrice(product.final_price || product.price) }}</span>
            <span v-if="product.discount_rate > 0" class="discount-rate">
              {{ product.discount_rate }}%
            </span>
          </div>

          <div v-if="product.short_description" class="product-description">
            {{ product.short_description }}
          </div>

          <div class="product-meta">
            <div class="meta-item">
              <span class="label">배송비:</span>
              <span class="value">
                {{ product.shipping_fee > 0 ? formatPrice(product.shipping_fee) : '무료배송' }}
              </span>
            </div>
            <div v-if="product.origin" class="meta-item">
              <span class="label">원산지:</span>
              <span class="value">{{ product.origin }}</span>
            </div>
            <div class="meta-item">
              <span class="label">판매단위:</span>
              <span class="value">{{ product.unit || '개' }}</span>
            </div>
          </div>

          <div class="product-actions">
            <div class="quantity-selector">
              <button @click="decreaseQuantity" :disabled="quantity <= 1">-</button>
              <input v-model.number="quantity" type="number" min="1" />
              <button @click="increaseQuantity">+</button>
            </div>

            <button
              class="btn-wishlist"
              @click="toggleWishlist"
              :class="{ active: product.is_wishlist }"
            >
              {{ product.is_wishlist ? '♥' : '♡' }} 찜
            </button>

            <button class="btn-cart" @click="addToCart">
              장바구니 담기
            </button>

            <button class="btn-buy" @click="buyNow">
              바로구매
            </button>
          </div>
        </div>
      </div>

      <!-- 상품 상세 정보 -->
      <div class="product-tabs">
        <div class="tabs">
          <button
            :class="{ active: activeTab === 'detail' }"
            @click="activeTab = 'detail'"
          >
            상세정보
          </button>
          <button
            :class="{ active: activeTab === 'info' }"
            @click="activeTab = 'info'"
          >
            상품정보
          </button>
        </div>

        <div class="tab-content">
          <div v-if="activeTab === 'detail'" class="detail-content">
            <div v-if="product.description" v-html="product.description"></div>
            <div v-else-if="product.detail_info" v-html="product.detail_info"></div>
            <p v-else>상세 정보가 없습니다.</p>
          </div>

          <div v-if="activeTab === 'info'" class="info-content">
            <table>
              <tr v-if="product.origin">
                <th>원산지</th>
                <td>{{ product.origin }}</td>
              </tr>
              <tr v-if="product.unit">
                <th>판매단위</th>
                <td>{{ product.unit }}</td>
              </tr>
              <tr v-if="product.storage_method">
                <th>보관방법</th>
                <td>{{ product.storage_method }}</td>
              </tr>
              <tr v-if="product.expiration_date">
                <th>유통기한</th>
                <td>{{ product.expiration_date }}</td>
              </tr>
            </table>
          </div>
        </div>
      </div>

      <!-- 관련 상품 -->
      <div v-if="product.related_products && product.related_products.length > 0" class="related-products">
        <h2>관련 상품</h2>
        <div class="products-grid">
          <ProductCard
            v-for="item in product.related_products"
            :key="item.id"
            :product="item"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { productsAPI } from '@/services/api'
import { useCartStore } from '@/stores/cart'
import { useWishlistStore } from '@/stores/wishlist'
import { useAuthStore } from '@/stores/auth'
import { getProductImage, formatPrice, type ProductDetail, DEFAULT_PRODUCT_IMAGE } from '@/types/product'
import ProductCard from '@/components/ui/ProductCard.vue'

const route = useRoute()
const router = useRouter()
const cartStore = useCartStore()
const wishlistStore = useWishlistStore()
const authStore = useAuthStore()

const product = ref<ProductDetail | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
const quantity = ref(1)
const activeTab = ref('detail')

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

function increaseQuantity() {
  quantity.value++
}

function decreaseQuantity() {
  if (quantity.value > 1) {
    quantity.value--
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
    const isWishlisted = await wishlistStore.toggleWishlist(product.value as any)
    product.value.is_wishlist = isWishlisted
  } catch (err) {
    alert('찜 처리에 실패했습니다.')
  }
}

function buyNow() {
  addToCart()
  router.push('/checkout')
}

function handleImageError(e: Event) {
  (e.target as HTMLImageElement).src = DEFAULT_PRODUCT_IMAGE
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

@media (max-width: 768px) {
  .product-main {
    grid-template-columns: 1fr;
  }

  .product-actions {
    grid-template-columns: 1fr;
  }
}
</style>
