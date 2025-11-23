<template>
  <div class="brand-mall-page">
    <div class="container">
      <div class="page-header">
        <h1 class="page-title">브랜드몰</h1>
        <p class="page-description">신뢰할 수 있는 농산물 브랜드를 만나보세요</p>
      </div>

      <div v-if="loading" class="loading-state">
        <div class="spinner"></div>
        <p>브랜드 목록을 불러오는 중...</p>
      </div>

      <div v-else-if="error" class="error-state">
        <p class="error-message">{{ error }}</p>
        <button @click="loadBrands" class="btn-retry">다시 시도</button>
      </div>

      <div v-else-if="brands.length === 0" class="empty-state">
        <h2>등록된 브랜드가 없습니다</h2>
        <router-link to="/" class="btn-primary">홈으로</router-link>
      </div>

      <div v-else class="brands-grid">
        <router-link
          v-for="brand in brands"
          :key="brand.id"
          :to="`/brands/${brand.brand_slug}`"
          class="brand-card"
        >
          <div class="brand-logo">
            <img
              :src="brand.brand_logo_url || DEFAULT_LOGO"
              :alt="brand.brand_name"
              @error="handleImageError"
            />
          </div>
          <div class="brand-info">
            <h3 class="brand-name">{{ brand.brand_name }}</h3>
            <p v-if="brand.brand_description" class="brand-description">
              {{ brand.brand_description }}
            </p>
            <div class="brand-stats">
              <span class="stat">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
                </svg>
                상품 {{ brand.total_products || 0 }}
              </span>
              <span v-if="brand.average_rating > 0" class="stat">
                <svg xmlns="http://www.w3.org/2000/svg" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
                </svg>
                {{ brand.average_rating.toFixed(1) }}
              </span>
            </div>
          </div>
        </router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { sellersAPI } from '@/services/api'

const DEFAULT_LOGO = '/images/default-brand.svg'

const loading = ref(true)
const error = ref<string | null>(null)
const brands = ref<any[]>([])

const loadBrands = async () => {
  loading.value = true
  error.value = null

  try {
    const response = await sellersAPI.getSellers()
    brands.value = response.data.results || response.data || []
  } catch (err: any) {
    error.value = '브랜드 목록을 불러오는데 실패했습니다.'
  } finally {
    loading.value = false
  }
}

const handleImageError = (event: Event) => {
  const target = event.target as HTMLImageElement
  target.src = DEFAULT_LOGO
}

onMounted(() => {
  loadBrands()
})
</script>

<style scoped>
.brand-mall-page {
  min-height: 100vh;
  background: #f8f9fa;
  padding: 2rem 0;
}

.container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 1rem;
}

.page-header {
  text-align: center;
  margin-bottom: 3rem;
}

.page-title {
  font-size: 2.5rem;
  font-weight: 700;
  color: #1a1a1a;
  margin-bottom: 0.75rem;
}

.page-description {
  font-size: 1.125rem;
  color: #666;
}

.loading-state,
.error-state,
.empty-state {
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

.btn-retry,
.btn-primary {
  padding: 0.875rem 2rem;
  background: #00a86b;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  text-decoration: none;
  display: inline-block;
}

.btn-retry:hover,
.btn-primary:hover {
  background: #008c5a;
}

.brands-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 2rem;
}

.brand-card {
  background: white;
  border-radius: 12px;
  padding: 2rem;
  text-decoration: none;
  transition: all 0.3s;
  border: 2px solid transparent;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.brand-card:hover {
  transform: translateY(-8px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
  border-color: #00a86b;
}

.brand-logo {
  width: 120px;
  height: 120px;
  border-radius: 50%;
  overflow: hidden;
  margin-bottom: 1.5rem;
  background: #f8f9fa;
  border: 3px solid #e9ecef;
}

.brand-logo img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.brand-info {
  width: 100%;
}

.brand-name {
  font-size: 1.5rem;
  font-weight: 700;
  color: #1a1a1a;
  margin-bottom: 0.75rem;
}

.brand-description {
  font-size: 0.9375rem;
  color: #666;
  line-height: 1.6;
  margin-bottom: 1.25rem;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.brand-stats {
  display: flex;
  justify-content: center;
  gap: 1.5rem;
  padding-top: 1rem;
  border-top: 1px solid #e9ecef;
}

.stat {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  color: #666;
  font-weight: 600;
}

.stat svg {
  width: 18px;
  height: 18px;
  color: #00a86b;
}

@media (max-width: 768px) {
  .brands-grid {
    grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
    gap: 1.5rem;
  }

  .brand-card {
    padding: 1.5rem;
  }

  .brand-logo {
    width: 100px;
    height: 100px;
  }
}
</style>
