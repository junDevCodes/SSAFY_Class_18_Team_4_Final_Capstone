<template>
  <div class="brand-detail-page">
    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>브랜드 정보를 불러오는 중...</p>
    </div>

    <div v-else-if="error" class="error-state">
      <p class="error-message">{{ error }}</p>
      <router-link to="/brands" class="btn-back">브랜드몰로 돌아가기</router-link>
    </div>

    <div v-else-if="brand" class="brand-detail-content">
      <!-- Brand Header -->
      <div class="brand-header" :style="bannerStyle">
        <div class="brand-header-overlay">
          <div class="container">
            <div class="brand-profile">
              <div class="brand-logo">
                <img
                  :src="brand.brand_logo_url || DEFAULT_LOGO"
                  :alt="brand.brand_name"
                  @error="handleImageError"
                />
              </div>
              <div class="brand-info">
                <h1 class="brand-name">{{ brand.brand_name }}</h1>
                <p v-if="brand.brand_description" class="brand-description">
                  {{ brand.brand_description }}
                </p>
                <div class="brand-stats">
                  <div class="stat">
                    <span class="label">상품</span>
                    <span class="value">{{ brand.total_products || 0 }}</span>
                  </div>
                  <div v-if="brand.average_rating > 0" class="stat">
                    <span class="label">평점</span>
                    <span class="value">⭐ {{ brand.average_rating.toFixed(1) }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Brand Products -->
      <div class="container">
        <div class="products-section">
          <h2 class="section-title">브랜드 상품</h2>

          <div v-if="productsLoading" class="loading-state">
            <div class="spinner"></div>
          </div>

          <div v-else-if="products.length === 0" class="empty-products">
            <p>등록된 상품이 없습니다</p>
          </div>

          <div v-else class="products-grid">
            <router-link
              v-for="product in products"
              :key="product.id"
              :to="`/products/${product.slug}`"
              class="product-card"
            >
              <div class="product-image">
                <img
                  :src="getProductImage(product)"
                  :alt="product.name"
                  @error="handleProductImageError"
                />
              </div>
              <div class="product-info">
                <h3 class="product-name">{{ product.name }}</h3>
                <div class="product-price">
                  <span v-if="product.discount_rate > 0" class="discount-rate">
                    {{ product.discount_rate }}%
                  </span>
                  <span class="price">{{ formatPrice(product.price) }}</span>
                </div>
                <div v-if="product.average_rating > 0" class="product-rating">
                  ⭐ {{ product.average_rating.toFixed(1) }}
                  <span class="review-count">({{ product.review_count }})</span>
                </div>
              </div>
            </router-link>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { sellersAPI, productsAPI } from '@/services/api'
import { formatPrice, getProductImage, DEFAULT_PRODUCT_IMAGE } from '@/types/product'

const DEFAULT_LOGO = '/images/default-brand.svg'
const DEFAULT_BANNER = 'linear-gradient(135deg, #00a86b 0%, #008c5a 100%)'

const route = useRoute()

const loading = ref(true)
const productsLoading = ref(true)
const error = ref<string | null>(null)
const brand = ref<any>(null)
const products = ref<any[]>([])

const bannerStyle = computed(() => {
  if (brand.value?.brand_banner_url) {
    return {
      backgroundImage: `url(${brand.value.brand_banner_url})`
    }
  }
  return {
    background: DEFAULT_BANNER
  }
})

const loadBrand = async () => {
  loading.value = true
  error.value = null

  try {
    const brandSlug = route.params.slug as string
    const response = await sellersAPI.getSeller(brandSlug)
    brand.value = response.data

    // Load brand products
    await loadProducts()
  } catch (err: any) {
    error.value = '브랜드 정보를 불러오는데 실패했습니다.'
  } finally {
    loading.value = false
  }
}

const loadProducts = async () => {
  if (!brand.value) return

  productsLoading.value = true

  try {
    // MVP: Load all products and filter by seller (or use backend filter if available)
    const response = await productsAPI.getProducts({
      page_size: 100
    })

    // Filter products by this seller if needed
    // For now, show all products (backend should implement seller filter)
    products.value = response.data.results || []
  } catch (err: any) {
    console.error('상품 로드 실패:', err)
  } finally {
    productsLoading.value = false
  }
}

const handleImageError = (event: Event) => {
  const target = event.target as HTMLImageElement
  target.src = DEFAULT_LOGO
}

const handleProductImageError = (event: Event) => {
  const target = event.target as HTMLImageElement
  target.src = DEFAULT_PRODUCT_IMAGE
}

onMounted(() => {
  loadBrand()
})
</script>

<style scoped>
.brand-detail-page {
  min-height: 100vh;
  background: #f8f9fa;
}

.loading-state,
.error-state {
  text-align: center;
  padding: 4rem 1rem;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #00a86b;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 1rem;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.error-message {
  color: #dc3545;
  font-size: 1.1rem;
  margin-bottom: 1rem;
}

.btn-back {
  display: inline-block;
  padding: 0.875rem 2rem;
  background: #00a86b;
  color: white;
  text-decoration: none;
  border-radius: 8px;
}

/* Brand Header */
.brand-header {
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
  position: relative;
}

.brand-header-overlay {
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(4px);
  padding: 4rem 0;
}

.container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 1rem;
}

.brand-profile {
  display: flex;
  align-items: center;
  gap: 2rem;
}

.brand-logo {
  width: 150px;
  height: 150px;
  border-radius: 50%;
  overflow: hidden;
  background: white;
  border: 4px solid white;
  flex-shrink: 0;
}

.brand-logo img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.brand-info {
  flex: 1;
  color: white;
}

.brand-name {
  font-size: 2.5rem;
  font-weight: 700;
  margin-bottom: 1rem;
}

.brand-description {
  font-size: 1.125rem;
  line-height: 1.6;
  margin-bottom: 1.5rem;
  max-width: 600px;
}

.brand-stats {
  display: flex;
  gap: 2rem;
}

.stat {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.stat .label {
  font-size: 0.875rem;
  opacity: 0.9;
}

.stat .value {
  font-size: 1.5rem;
  font-weight: 700;
}

/* Products Section */
.products-section {
  padding: 3rem 0;
}

.section-title {
  font-size: 2rem;
  font-weight: 700;
  color: #1a1a1a;
  margin-bottom: 2rem;
}

.empty-products {
  text-align: center;
  padding: 4rem 1rem;
  color: #666;
}

.products-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 2rem;
}

.product-card {
  background: white;
  border-radius: 12px;
  overflow: hidden;
  text-decoration: none;
  transition: all 0.3s;
}

.product-card:hover {
  transform: translateY(-8px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
}

.product-image {
  width: 100%;
  height: 250px;
  background: #f8f9fa;
}

.product-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.product-info {
  padding: 1.25rem;
}

.product-name {
  font-size: 1.125rem;
  font-weight: 600;
  color: #1a1a1a;
  margin-bottom: 0.75rem;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.product-price {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.discount-rate {
  font-size: 1rem;
  font-weight: 700;
  color: #dc3545;
}

.price {
  font-size: 1.25rem;
  font-weight: 700;
  color: #00a86b;
}

.product-rating {
  font-size: 0.875rem;
  color: #666;
}

.review-count {
  color: #999;
}

/* Responsive */
@media (max-width: 768px) {
  .brand-header-overlay {
    padding: 2rem 0;
  }

  .brand-profile {
    flex-direction: column;
    text-align: center;
  }

  .brand-logo {
    width: 120px;
    height: 120px;
  }

  .brand-name {
    font-size: 2rem;
  }

  .brand-stats {
    justify-content: center;
  }

  .products-grid {
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 1.5rem;
  }
}
</style>
