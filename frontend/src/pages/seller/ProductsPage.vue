<template>
  <div class="seller-products-page">
    <div class="container">
      <!-- Page Header -->
      <div class="page-header">
        <div class="header-left">
          <h1 class="page-title">상품 관리</h1>
          <p class="page-description">등록한 상품을 관리하세요</p>
        </div>
        <router-link to="/seller/products/create" class="btn-create">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
          </svg>
          상품 등록
        </router-link>
      </div>

      <!-- Loading State -->
      <div v-if="loading" class="loading-state">
        <div class="spinner"></div>
        <p>상품 목록을 불러오는 중...</p>
      </div>

      <!-- Error State -->
      <div v-else-if="error" class="error-state">
        <p class="error-message">{{ error }}</p>
        <button @click="loadProducts" class="btn-retry">다시 시도</button>
      </div>

      <!-- Empty State -->
      <div v-else-if="products.length === 0" class="empty-state">
        <div class="empty-icon">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
          </svg>
        </div>
        <h2>등록된 상품이 없습니다</h2>
        <p>첫 상품을 등록해보세요</p>
        <router-link to="/seller/products/create" class="btn-primary">
          상품 등록하기
        </router-link>
      </div>

      <!-- Products List -->
      <div v-else class="products-content">
        <!-- Products Table -->
        <div class="products-table">
          <table>
            <thead>
              <tr>
                <th>상품</th>
                <th>가격</th>
                <th>재고</th>
                <th>상태</th>
                <th>조회수</th>
                <th>등록일</th>
                <th>관리</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="product in products" :key="product.id">
                <td class="product-cell">
                  <div class="product-info">
                    <div class="product-image">
                      <img
                        :src="product.main_image || DEFAULT_PRODUCT_IMAGE"
                        :alt="product.name"
                        @error="handleImageError"
                      />
                    </div>
                    <div class="product-details">
                      <h3 class="product-name">{{ product.name }}</h3>
                      <p v-if="product.category_name" class="product-category">
                        {{ product.category_name }}
                      </p>
                    </div>
                  </div>
                </td>
                <td class="price-cell">
                  <span class="price">{{ formatPrice(product.price) }}</span>
                  <span v-if="product.discount_rate > 0" class="discount">
                    {{ product.discount_rate }}% 할인
                  </span>
                </td>
                <td class="stock-cell">
                  <span :class="{ 'low-stock': product.stock_quantity < 10 }">
                    {{ product.stock_quantity || 0 }}
                  </span>
                </td>
                <td class="status-cell">
                  <span class="status-badge" :class="`status-${product.status}`">
                    {{ getStatusText(product.status) }}
                  </span>
                </td>
                <td class="views-cell">
                  {{ product.view_count || 0 }}
                </td>
                <td class="date-cell">
                  {{ formatDate(product.created_at) }}
                </td>
                <td class="actions-cell">
                  <div class="action-buttons">
                    <router-link
                      :to="`/seller/products/${product.id}/edit`"
                      class="btn-edit"
                      title="수정"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                      </svg>
                    </router-link>
                    <button
                      v-if="product.status === 'active'"
                      @click="handleUnpublish(product.id)"
                      class="btn-unpublish"
                      title="판매중지"
                      :disabled="updating === product.id"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 9v6m4-6v6m7-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    </button>
                    <button
                      v-else
                      @click="handlePublish(product.id)"
                      class="btn-publish"
                      title="판매시작"
                      :disabled="updating === product.id"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    </button>
                    <button
                      @click="handleDelete(product.id)"
                      class="btn-delete"
                      title="삭제"
                      :disabled="deleting === product.id"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Pagination -->
        <div v-if="totalPages > 1" class="pagination">
          <button
            @click="goToPage(currentPage - 1)"
            :disabled="currentPage === 1"
            class="btn-page"
          >
            이전
          </button>

          <div class="page-numbers">
            <button
              v-for="page in visiblePages"
              :key="page"
              @click="goToPage(page)"
              :class="{ active: page === currentPage }"
              class="btn-page-number"
            >
              {{ page }}
            </button>
          </div>

          <button
            @click="goToPage(currentPage + 1)"
            :disabled="currentPage === totalPages"
            class="btn-page"
          >
            다음
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { sellerProductsAPI } from '@/services/api'
import { formatPrice, DEFAULT_PRODUCT_IMAGE } from '@/types/product'

const loading = ref(true)
const error = ref<string | null>(null)
const products = ref<any[]>([])
const updating = ref<number | null>(null)
const deleting = ref<number | null>(null)
const currentPage = ref(1)
const totalPages = ref(1)
const pageSize = 20

// Computed
const visiblePages = computed(() => {
  const pages: number[] = []
  const maxVisible = 5
  let start = Math.max(1, currentPage.value - Math.floor(maxVisible / 2))
  let end = Math.min(totalPages.value, start + maxVisible - 1)

  if (end - start < maxVisible - 1) {
    start = Math.max(1, end - maxVisible + 1)
  }

  for (let i = start; i <= end; i++) {
    pages.push(i)
  }

  return pages
})

// Load products
const loadProducts = async () => {
  loading.value = true
  error.value = null

  try {
    const response = await sellerProductsAPI.getMyProducts({
      page: currentPage.value,
      page_size: pageSize
    })

    products.value = response.data.results || []
    const total = response.data.count || products.value.length
    totalPages.value = Math.ceil(total / pageSize)
  } catch (err: any) {
    console.error('상품 목록 로드 실패:', err)
    error.value = '상품 목록을 불러오는데 실패했습니다.'
  } finally {
    loading.value = false
  }
}

// Pagination
const goToPage = (page: number) => {
  if (page < 1 || page > totalPages.value) return
  currentPage.value = page
  loadProducts()
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

// Publish product
const handlePublish = async (productId: number) => {
  updating.value = productId

  try {
    await sellerProductsAPI.publishProduct(productId)
    await loadProducts()
  } catch (err: any) {
    console.error('상품 판매 시작 실패:', err)
    alert('상품 판매 시작에 실패했습니다.')
  } finally {
    updating.value = null
  }
}

// Unpublish product
const handleUnpublish = async (productId: number) => {
  updating.value = productId

  try {
    await sellerProductsAPI.unpublishProduct(productId)
    await loadProducts()
  } catch (err: any) {
    console.error('상품 판매 중지 실패:', err)
    alert('상품 판매 중지에 실패했습니다.')
  } finally {
    updating.value = null
  }
}

// Delete product
const handleDelete = async (productId: number) => {
  const confirmed = confirm('정말로 이 상품을 삭제하시겠습니까?')
  if (!confirmed) return

  deleting.value = productId

  try {
    await sellerProductsAPI.deleteProduct(productId)
    await loadProducts()
  } catch (err: any) {
    console.error('상품 삭제 실패:', err)
    alert('상품 삭제에 실패했습니다.')
  } finally {
    deleting.value = null
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

// Format date
const formatDate = (dateString: string): string => {
  const date = new Date(dateString)
  return date.toLocaleDateString('ko-KR', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  })
}

// Handle image error
const handleImageError = (event: Event) => {
  const target = event.target as HTMLImageElement
  target.src = DEFAULT_PRODUCT_IMAGE
}

// Initialize
onMounted(() => {
  loadProducts()
})
</script>

<style scoped>
.seller-products-page {
  min-height: 100vh;
  background: #f8f9fa;
  padding: 2rem 0;
}

.container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 1rem;
}

/* Page Header */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
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

.btn-create {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.875rem 1.75rem;
  background: #00a86b;
  color: white;
  text-decoration: none;
  border-radius: 8px;
  font-weight: 600;
  transition: all 0.2s;
}

.btn-create svg {
  width: 20px;
  height: 20px;
}

.btn-create:hover {
  background: #008c5a;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 168, 107, 0.3);
}

/* Loading, Error, Empty States */
.loading-state,
.error-state,
.empty-state {
  text-align: center;
  padding: 4rem 1rem;
  background: white;
  border-radius: 12px;
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

.empty-icon {
  width: 80px;
  height: 80px;
  margin: 0 auto 1.5rem;
  color: #ddd;
}

.empty-icon svg {
  width: 100%;
  height: 100%;
}

.empty-state h2 {
  font-size: 1.5rem;
  color: #333;
  margin-bottom: 0.5rem;
}

.empty-state p {
  color: #666;
  margin-bottom: 2rem;
}

.btn-primary {
  display: inline-block;
  padding: 0.875rem 2rem;
  background: #00a86b;
  color: white;
  text-decoration: none;
  border-radius: 6px;
  font-weight: 600;
  transition: background 0.2s;
}

.btn-primary:hover {
  background: #008c5a;
}

/* Products Table */
.products-content {
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.products-table {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
}

thead {
  background: #f8f9fa;
  border-bottom: 2px solid #e9ecef;
}

th {
  padding: 1rem;
  text-align: left;
  font-size: 0.875rem;
  font-weight: 700;
  color: #333;
  white-space: nowrap;
}

tbody tr {
  border-bottom: 1px solid #e9ecef;
  transition: background 0.2s;
}

tbody tr:hover {
  background: #f8f9fa;
}

td {
  padding: 1rem;
  font-size: 0.9375rem;
  color: #333;
}

.product-cell {
  min-width: 300px;
}

.product-info {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.product-image {
  width: 60px;
  height: 60px;
  border-radius: 6px;
  overflow: hidden;
  flex-shrink: 0;
}

.product-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.product-name {
  font-size: 0.9375rem;
  font-weight: 600;
  color: #1a1a1a;
  margin-bottom: 0.25rem;
  line-height: 1.4;
}

.product-category {
  font-size: 0.8125rem;
  color: #666;
}

.price-cell {
  min-width: 120px;
}

.price {
  display: block;
  font-weight: 700;
  color: #1a1a1a;
}

.discount {
  display: block;
  font-size: 0.8125rem;
  color: #dc3545;
  margin-top: 0.25rem;
}

.stock-cell {
  text-align: center;
}

.low-stock {
  color: #dc3545;
  font-weight: 700;
}

.status-cell {
  min-width: 100px;
}

.status-badge {
  display: inline-block;
  padding: 0.375rem 0.75rem;
  border-radius: 12px;
  font-size: 0.8125rem;
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

.views-cell,
.date-cell {
  text-align: center;
  color: #666;
}

.actions-cell {
  min-width: 150px;
}

.action-buttons {
  display: flex;
  gap: 0.5rem;
  justify-content: center;
}

.btn-edit,
.btn-publish,
.btn-unpublish,
.btn-delete {
  width: 36px;
  height: 36px;
  padding: 0;
  border: none;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-edit svg,
.btn-publish svg,
.btn-unpublish svg,
.btn-delete svg {
  width: 18px;
  height: 18px;
}

.btn-edit {
  background: #007bff;
  color: white;
}

.btn-edit:hover {
  background: #0056b3;
}

.btn-publish {
  background: #28a745;
  color: white;
}

.btn-publish:hover {
  background: #1e7e34;
}

.btn-unpublish {
  background: #ffc107;
  color: #000;
}

.btn-unpublish:hover {
  background: #e0a800;
}

.btn-delete {
  background: #dc3545;
  color: white;
}

.btn-delete:hover {
  background: #c82333;
}

.btn-edit:disabled,
.btn-publish:disabled,
.btn-unpublish:disabled,
.btn-delete:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Pagination */
.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 0.5rem;
  margin-top: 2rem;
  padding-top: 2rem;
  border-top: 1px solid #e9ecef;
}

.btn-page,
.btn-page-number {
  padding: 0.5rem 0.875rem;
  background: white;
  color: #333;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-page:hover:not(:disabled),
.btn-page-number:hover {
  background: #f8f9fa;
  border-color: #00a86b;
  color: #00a86b;
}

.btn-page:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-page-number.active {
  background: #00a86b;
  color: white;
  border-color: #00a86b;
}

.page-numbers {
  display: flex;
  gap: 0.25rem;
}

/* Responsive */
@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 1rem;
  }

  .btn-create {
    width: 100%;
    justify-content: center;
  }

  .products-table {
    overflow-x: scroll;
  }
}
</style>
