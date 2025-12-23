<template>
  <div class="seller-dashboard-page">
    <div class="container">
      <!-- Page Header -->
      <div class="page-header">
        <h1 class="page-title">판매자 대시보드</h1>
        <p class="page-description">판매 현황을 한눈에 확인하세요</p>
      </div>

      <!-- Loading State -->
      <div v-if="loading" class="loading-state">
        <div class="spinner"></div>
        <p>대시보드 정보를 불러오는 중...</p>
      </div>

      <!-- Error State -->
      <div v-else-if="error" class="error-state">
        <p class="error-message">{{ error }}</p>
        <button @click="loadDashboard" class="btn-retry">다시 시도</button>
      </div>

      <!-- Dashboard Content -->
      <div v-else class="dashboard-content">
        <!-- Stats Cards -->
        <div class="stats-grid">
          <div class="stat-card">
            <div class="stat-icon products">
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
              </svg>
            </div>
            <div class="stat-info">
              <h3 class="stat-label">전체 상품</h3>
              <p class="stat-value">{{ stats.total_products || 0 }}</p>
            </div>
          </div>

          <div class="stat-card">
            <div class="stat-icon orders">
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z" />
              </svg>
            </div>
            <div class="stat-info">
              <h3 class="stat-label">전체 주문</h3>
              <p class="stat-value">{{ stats.total_orders || 0 }}</p>
            </div>
          </div>

          <div class="stat-card">
            <div class="stat-icon revenue">
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div class="stat-info">
              <h3 class="stat-label">총 매출</h3>
              <p class="stat-value">{{ formatPrice(stats.total_revenue || 0) }}</p>
            </div>
          </div>

          <div class="stat-card">
            <div class="stat-icon rating">
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
              </svg>
            </div>
            <div class="stat-info">
              <h3 class="stat-label">평균 평점</h3>
              <p class="stat-value">{{ formatRating(stats.average_rating) }}</p>
            </div>
          </div>
        </div>

        <!-- Quick Actions -->
        <section class="section">
          <h2 class="section-title">빠른 작업</h2>
          <div class="actions-grid">
            <router-link to="/seller/products/create" class="action-card">
              <div class="action-icon">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
                </svg>
              </div>
              <h3>상품 등록</h3>
              <p>새로운 상품을 등록하세요</p>
            </router-link>

            <router-link to="/seller/products" class="action-card">
              <div class="action-icon">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 10h16M4 14h16M4 18h16" />
                </svg>
              </div>
              <h3>상품 관리</h3>
              <p>등록된 상품을 관리하세요</p>
            </router-link>

            <router-link to="/seller/analytics" class="action-card">
              <div class="action-icon">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 12h4l3-8 4 16 3-8h3" />
                </svg>
              </div>
              <h3>유입·전환 분석</h3>
              <p>채널/상품별 전환 추이를 바로 확인하세요</p>
            </router-link>

            <router-link to="/seller/orders" class="action-card">
              <div class="action-icon">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                </svg>
              </div>
              <h3>주문 관리</h3>
              <p>주문 내역을 확인하세요</p>
            </router-link>

            <router-link to="/seller/settings" class="action-card">
              <div class="action-icon">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
              </div>
              <h3>설정</h3>
              <p>판매자 정보를 수정하세요</p>
            </router-link>
          </div>
        </section>

        <!-- Recent Products -->
        <section v-if="recentProducts.length > 0" class="section">
          <div class="section-header">
            <h2 class="section-title">최근 등록 상품</h2>
            <router-link to="/seller/products" class="btn-view-all">
              전체보기
            </router-link>
          </div>
          <div class="products-grid">
            <div
              v-for="product in recentProducts"
              :key="product.id"
              class="product-card"
            >
              <div class="product-image">
                <img
                  :src="product.main_image_url || product.main_image || DEFAULT_PRODUCT_IMAGE"
                  :alt="product.name"
                  @error="handleImageError"
                />
              </div>
              <div class="product-info">
                <h3 class="product-name">{{ product.name }}</h3>
                <p class="product-price">{{ formatPrice(product.price) }}</p>
                <div class="product-meta">
                  <span class="status" :class="`status-${product.status}`">
                    {{ getStatusText(product.status) }}
                  </span>
                  <span class="views">조회 {{ product.view_count || 0 }}</span>
                </div>
              </div>
            </div>
          </div>
        </section>

        <!-- Welcome Message for New Sellers -->
        <section v-else class="section welcome-section">
          <div class="welcome-content">
            <div class="welcome-icon">
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
              </svg>
            </div>
            <h2>판매자 등록을 환영합니다!</h2>
            <p>첫 상품을 등록하고 판매를 시작해보세요</p>
            <router-link to="/seller/products/create" class="btn-start">
              상품 등록하기
            </router-link>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { sellersAPI, sellerProductsAPI } from '@/services/api'
import { formatPrice, DEFAULT_PRODUCT_IMAGE } from '@/types/product'

const loading = ref(true)
const error = ref<string | null>(null)
const dashboard = ref<any>({})
const recentProducts = ref<any[]>([])
const stats = computed(() => dashboard.value?.statistics || {})

const formatRating = (value?: number | string | null) => {
  return Number(value ?? 0).toFixed(1)
}

// Load dashboard data
const loadDashboard = async () => {
  loading.value = true
  error.value = null

  try {
    // Ensure user is loaded first
    const { useAuthStore } = await import('@/stores/auth')
    const authStore = useAuthStore()
    
    // Reload user to ensure token is valid
    await authStore.loadUser()
    
    if (!authStore.isAuthenticated) {
      error.value = '로그인이 필요합니다.'
      loading.value = false
      return
    }

    // Load dashboard stats
    const dashboardResponse = await sellersAPI.getDashboard()
    const dashboardData = dashboardResponse.data || {}
    dashboard.value = {
      ...dashboardData,
      statistics: dashboardData.statistics || {}
    }

    // Load recent products
    const productsResponse = await sellerProductsAPI.getMyProducts({
      page: 1,
      page_size: 6
    })
    recentProducts.value = productsResponse.data.results || []
  } catch (err: any) {
    console.error('대시보드 로드 실패:', err)
    if (err.response?.status === 401) {
      error.value = '로그인이 만료되었습니다. 다시 로그인해주세요.'
    } else {
      error.value = err.response?.data?.detail || '대시보드 정보를 불러오는데 실패했습니다.'
    }
  } finally {
    loading.value = false
  }
}

// Get status text
const getStatusText = (status: string): string => {
  const statusMap: Record<string, string> = {
    active: '판매중',
    inactive: '판매중지',
    draft: '초안',
    out_of_stock: '품절'
  }
  return statusMap[status] || status
}

// Handle image error
const handleImageError = (event: Event) => {
  const target = event.target as HTMLImageElement
  target.src = DEFAULT_PRODUCT_IMAGE
}

// Initialize
onMounted(() => {
  loadDashboard()
})
</script>

<style scoped>
.seller-dashboard-page {
  min-height: calc(100vh - 4rem);
  background: linear-gradient(to bottom, #fafafa 0%, #ffffff 100%);
  padding-top: 5rem; /* 헤더 높이(64px) + 여백 */
  padding-bottom: 4rem;
}

.container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 1rem;
}

/* Page Header */
.page-header {
  margin-bottom: 2rem;
}

.page-title {
  font-size: 2rem;
  font-weight: 700;
  color: #1a1a1a;
  margin-bottom: 0.5rem;
}

.page-description {
  color: #666;
  font-size: 1rem;
}

/* Loading & Error States */
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

.btn-retry {
  padding: 0.75rem 1.5rem;
  background: #00a86b;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 1rem;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-retry:hover {
  background: #008c5a;
}

/* Dashboard Content */
.dashboard-content {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

/* Stats Grid */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.5rem;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 1.5rem;
  padding: 1.75rem;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  transition: transform 0.2s, box-shadow 0.2s;
}

.stat-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
}

.stat-icon {
  width: 60px;
  height: 60px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.stat-icon svg {
  width: 32px;
  height: 32px;
  color: white;
}

.stat-icon.products {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.stat-icon.orders {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
}

.stat-icon.revenue {
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
}

.stat-icon.rating {
  background: linear-gradient(135deg, #ffd89b 0%, #19547b 100%);
}

.stat-info {
  flex: 1;
}

.stat-label {
  font-size: 0.875rem;
  color: #666;
  margin-bottom: 0.5rem;
}

.stat-value {
  font-size: 1.75rem;
  font-weight: 700;
  color: #1a1a1a;
}

/* Section */
.section {
  background: white;
  border-radius: 12px;
  padding: 2rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.section-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: #1a1a1a;
}

.btn-view-all {
  color: #00a86b;
  text-decoration: none;
  font-size: 0.9375rem;
  font-weight: 600;
  transition: color 0.2s;
}

.btn-view-all:hover {
  color: #008c5a;
}

/* Actions Grid */
.actions-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1.5rem;
}

.action-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 2rem 1.5rem;
  border: 2px solid #e9ecef;
  border-radius: 12px;
  text-decoration: none;
  transition: all 0.2s;
}

.action-card:hover {
  border-color: #00a86b;
  transform: translateY(-4px);
  box-shadow: 0 4px 12px rgba(0, 168, 107, 0.15);
}

.action-icon {
  width: 60px;
  height: 60px;
  background: linear-gradient(135deg, #00a86b 0%, #008c5a 100%);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 1rem;
}

.action-icon svg {
  width: 30px;
  height: 30px;
  color: white;
}

.action-card h3 {
  font-size: 1.125rem;
  font-weight: 700;
  color: #1a1a1a;
  margin-bottom: 0.5rem;
}

.action-card p {
  font-size: 0.875rem;
  color: #666;
}

/* Products Grid */
.products-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 1.5rem;
}

.product-card {
  border: 1px solid #e9ecef;
  border-radius: 8px;
  overflow: hidden;
  transition: all 0.2s;
}

.product-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  transform: translateY(-4px);
}

.product-image {
  width: 100%;
  height: 200px;
  background: #f8f9fa;
}

.product-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.product-info {
  padding: 1rem;
}

.product-name {
  font-size: 1rem;
  font-weight: 600;
  color: #1a1a1a;
  margin-bottom: 0.5rem;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.product-price {
  font-size: 1.125rem;
  font-weight: 700;
  color: #00a86b;
  margin-bottom: 0.75rem;
}

.product-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.875rem;
}

.status {
  padding: 0.25rem 0.625rem;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 700;
}

.status-active {
  background: #d4edda;
  color: #155724;
}

.status-inactive {
  background: #f8d7da;
  color: #721c24;
}

.status-draft {
  background: #fff3cd;
  color: #856404;
}

.status-out_of_stock {
  background: #e2e3e5;
  color: #383d41;
}

.views {
  color: #666;
}

/* Welcome Section */
.welcome-section {
  text-align: center;
  padding: 4rem 2rem;
}

.welcome-content {
  max-width: 600px;
  margin: 0 auto;
}

.welcome-icon {
  width: 100px;
  height: 100px;
  background: linear-gradient(135deg, #00a86b 0%, #008c5a 100%);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 2rem;
}

.welcome-icon svg {
  width: 50px;
  height: 50px;
  color: white;
}

.welcome-content h2 {
  font-size: 2rem;
  font-weight: 700;
  color: #1a1a1a;
  margin-bottom: 1rem;
}

.welcome-content p {
  font-size: 1.125rem;
  color: #666;
  margin-bottom: 2rem;
}

.btn-start {
  display: inline-block;
  padding: 1rem 2.5rem;
  background: #00a86b;
  color: white;
  text-decoration: none;
  border-radius: 8px;
  font-size: 1.125rem;
  font-weight: 700;
  transition: all 0.2s;
}

.btn-start:hover {
  background: #008c5a;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 168, 107, 0.3);
}

/* Responsive */
@media (max-width: 768px) {
  .seller-dashboard-page {
    padding: 1rem 0;
  }

  .page-title {
    font-size: 1.5rem;
  }

  .stats-grid {
    grid-template-columns: 1fr;
  }

  .actions-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .products-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 480px) {
  .actions-grid,
  .products-grid {
    grid-template-columns: 1fr;
  }

  .section {
    padding: 1.5rem;
  }

  .welcome-content h2 {
    font-size: 1.5rem;
  }
}
</style>
