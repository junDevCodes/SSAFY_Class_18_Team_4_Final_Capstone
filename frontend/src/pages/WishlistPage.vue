<template>
  <div class="wishlist-page">
    <div class="container">
      <!-- Header -->
      <div class="page-header">
        <h1 class="page-title">찜 목록</h1>
        <p class="page-description">관심있는 상품을 모아보세요</p>
      </div>

      <!-- Loading State -->
      <div v-if="wishlistStore.loading && !wishlistStore.items.length" class="loading-state">
        <div class="spinner"></div>
        <p>찜 목록을 불러오는 중...</p>
      </div>

      <!-- Error State -->
      <div v-else-if="wishlistStore.error" class="error-state">
        <p class="error-message">{{ wishlistStore.error }}</p>
        <button @click="loadWishlist" class="btn-retry">다시 시도</button>
      </div>

      <!-- Empty State -->
      <div v-else-if="!wishlistStore.items.length" class="empty-state">
        <div class="empty-icon">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
          </svg>
        </div>
        <h2>찜한 상품이 없습니다</h2>
        <p>마음에 드는 상품을 찜해보세요</p>
        <router-link to="/" class="btn-primary">쇼핑 시작하기</router-link>
      </div>

      <!-- Wishlist Items -->
      <div v-else class="wishlist-content">
        <!-- Header Actions -->
        <div class="wishlist-header">
          <p class="item-count">총 {{ wishlistStore.count }}개 상품</p>
          <button
            @click="removeSelectedItems"
            class="btn-remove-selected"
            :disabled="selectedItems.size === 0 || removing"
          >
            선택 삭제
          </button>
        </div>

        <!-- Items Grid -->
        <div class="wishlist-grid">
          <div
            v-for="item in wishlistStore.items"
            :key="item.id"
            class="wishlist-item"
            :class="{ removing: removingItems.has(item.id), adding: addingToCart.has(item.id) }"
          >
            <!-- Checkbox -->
            <div class="item-checkbox">
              <input
                type="checkbox"
                :id="`item-${item.id}`"
                :checked="selectedItems.has(item.id)"
                @change="toggleSelection(item.id)"
                :disabled="removingItems.has(item.id)"
              />
              <label :for="`item-${item.id}`"></label>
            </div>

            <!-- Product Image -->
            <router-link
              :to="`/products/${item.product.slug}`"
              class="item-image"
            >
              <img
                :src="getProductImage(item.product)"
                :alt="item.product.name"
                @error="handleImageError"
              />
            </router-link>

            <!-- Product Info -->
            <div class="item-info">
              <router-link
                :to="`/products/${item.product.slug}`"
                class="item-name"
              >
                {{ item.product.name }}
              </router-link>

              <div class="item-meta">
                <span v-if="item.product.category_name" class="category">
                  {{ item.product.category_name }}
                </span>
                <span v-if="item.product.unit" class="unit">
                  {{ item.product.unit }}
                </span>
              </div>

              <div class="item-price">
                <div v-if="item.product.discount_rate > 0" class="price-discount">
                  <span class="discount-rate">{{ item.product.discount_rate }}%</span>
                  <span class="original-price">{{ formatPrice(item.product.original_price || 0) }}</span>
                </div>
                <span class="current-price">{{ formatPrice(item.product.price) }}</span>
              </div>

              <div class="item-stats">
                <span v-if="item.product.average_rating > 0" class="rating">
                  ⭐ {{ item.product.average_rating.toFixed(1) }}
                </span>
                <span v-if="item.product.review_count > 0" class="reviews">
                  리뷰 {{ item.product.review_count }}
                </span>
              </div>

              <p class="added-date">{{ formatDate(item.created_at) }}</p>
            </div>

            <!-- Actions -->
            <div class="item-actions">
              <button
                @click="addToCartFromWishlist(item)"
                class="btn-add-cart"
                :disabled="addingToCart.has(item.id)"
              >
                <span v-if="addingToCart.has(item.id)">담는 중...</span>
                <span v-else>장바구니 담기</span>
              </button>

              <button
                @click="removeItem(item.id)"
                class="btn-remove"
                :disabled="removingItems.has(item.id)"
              >
                <span v-if="removingItems.has(item.id)">삭제 중...</span>
                <span v-else>삭제</span>
              </button>
            </div>
          </div>
        </div>

        <!-- Bulk Actions Footer -->
        <div class="wishlist-footer">
          <div class="select-all">
            <input
              type="checkbox"
              id="select-all"
              :checked="isAllSelected"
              @change="toggleSelectAll"
              :disabled="removing"
            />
            <label for="select-all">전체 선택</label>
          </div>

          <button
            @click="addAllToCart"
            class="btn-add-all-cart"
            :disabled="selectedItems.size === 0 || removing"
          >
            선택 상품 장바구니 담기
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useWishlistStore } from '@/stores/wishlist'
import { useCartStore } from '@/stores/cart'
import type { WishlistItem } from '@/types/product'
import { getProductImage, formatPrice, DEFAULT_PRODUCT_IMAGE } from '@/types/product'

const router = useRouter()
const wishlistStore = useWishlistStore()
const cartStore = useCartStore()

// Selection state
const selectedItems = ref<Set<number>>(new Set())
const removingItems = ref<Set<number>>(new Set())
const addingToCart = ref<Set<number>>(new Set())
const removing = ref(false)

// Computed
const isAllSelected = computed(() => {
  return wishlistStore.items.length > 0 &&
         selectedItems.value.size === wishlistStore.items.length
})

// Load wishlist
const loadWishlist = async () => {
  await wishlistStore.loadWishlist()
}

// Toggle selection
const toggleSelection = (id: number) => {
  if (selectedItems.value.has(id)) {
    selectedItems.value.delete(id)
  } else {
    selectedItems.value.add(id)
  }
}

// Toggle select all
const toggleSelectAll = () => {
  if (isAllSelected.value) {
    selectedItems.value.clear()
  } else {
    wishlistStore.items.forEach(item => {
      selectedItems.value.add(item.id)
    })
  }
}

// Remove item
const removeItem = async (id: number) => {
  if (removingItems.value.has(id)) return

  const confirmed = confirm('찜 목록에서 삭제하시겠습니까?')
  if (!confirmed) return

  removingItems.value.add(id)

  try {
    await wishlistStore.removeFromWishlist(id)
    selectedItems.value.delete(id)
  } catch (err) {
    console.error('삭제 실패:', err)
    alert('삭제에 실패했습니다. 다시 시도해주세요.')
  } finally {
    removingItems.value.delete(id)
  }
}

// Remove selected items
const removeSelectedItems = async () => {
  if (selectedItems.value.size === 0) return

  const confirmed = confirm(`선택한 ${selectedItems.value.size}개 상품을 삭제하시겠습니까?`)
  if (!confirmed) return

  removing.value = true
  const itemsToRemove = Array.from(selectedItems.value)

  try {
    // Remove items sequentially to avoid race conditions
    for (const id of itemsToRemove) {
      removingItems.value.add(id)
      try {
        await wishlistStore.removeFromWishlist(id)
        selectedItems.value.delete(id)
      } catch (err) {
        console.error(`Item ${id} 삭제 실패:`, err)
      } finally {
        removingItems.value.delete(id)
      }
    }
  } finally {
    removing.value = false
  }
}

// Add to cart from wishlist
const addToCartFromWishlist = async (item: WishlistItem) => {
  if (addingToCart.value.has(item.id)) return

  addingToCart.value.add(item.id)

  try {
    await cartStore.addToCart(item.product, 1)
    alert('장바구니에 담았습니다.')
  } catch (err) {
    console.error('장바구니 담기 실패:', err)
    alert('장바구니 담기에 실패했습니다. 다시 시도해주세요.')
  } finally {
    addingToCart.value.delete(item.id)
  }
}

// Add all selected to cart
const addAllToCart = async () => {
  if (selectedItems.value.size === 0) return

  removing.value = true
  const itemsToAdd = wishlistStore.items.filter(item => selectedItems.value.has(item.id))

  try {
    let successCount = 0

    for (const item of itemsToAdd) {
      addingToCart.value.add(item.id)
      try {
        await cartStore.addToCart(item.product, 1)
        successCount++
      } catch (err) {
        console.error(`Item ${item.id} 장바구니 담기 실패:`, err)
      } finally {
        addingToCart.value.delete(item.id)
      }
    }

    if (successCount > 0) {
      alert(`${successCount}개 상품을 장바구니에 담았습니다.`)
    }
  } finally {
    removing.value = false
  }
}

// Format date
const formatDate = (dateString: string): string => {
  const date = new Date(dateString)
  const now = new Date()
  const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24))

  if (diffDays === 0) return '오늘 추가'
  if (diffDays === 1) return '어제 추가'
  if (diffDays < 7) return `${diffDays}일 전 추가`
  if (diffDays < 30) return `${Math.floor(diffDays / 7)}주 전 추가`

  return date.toLocaleDateString('ko-KR', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  })
}

// Handle image error
const handleImageError = (event: Event) => {
  const target = event.target as HTMLImageElement
  target.src = DEFAULT_PRODUCT_IMAGE
}

// Initialize
onMounted(() => {
  loadWishlist()
})
</script>

<style scoped>
.wishlist-page {
  min-height: 100vh;
  background: #f8f9fa;
  padding: 2rem 0;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1rem;
}

/* Header */
.page-header {
  margin-bottom: 2rem;
  text-align: center;
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

/* Loading State */
.loading-state {
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

/* Error State */
.error-state {
  text-align: center;
  padding: 4rem 1rem;
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

/* Empty State */
.empty-state {
  text-align: center;
  padding: 4rem 1rem;
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

/* Wishlist Content */
.wishlist-content {
  background: white;
  border-radius: 8px;
  padding: 1.5rem;
}

.wishlist-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  padding-bottom: 1rem;
  border-bottom: 2px solid #f0f0f0;
}

.item-count {
  font-size: 1.1rem;
  font-weight: 600;
  color: #333;
}

.btn-remove-selected {
  padding: 0.5rem 1rem;
  background: white;
  color: #dc3545;
  border: 1px solid #dc3545;
  border-radius: 4px;
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-remove-selected:hover:not(:disabled) {
  background: #dc3545;
  color: white;
}

.btn-remove-selected:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Wishlist Grid */
.wishlist-grid {
  display: grid;
  gap: 1rem;
}

.wishlist-item {
  display: grid;
  grid-template-columns: auto 120px 1fr auto;
  gap: 1rem;
  padding: 1rem;
  border: 1px solid #e9ecef;
  border-radius: 8px;
  transition: all 0.2s;
  position: relative;
}

.wishlist-item:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.wishlist-item.removing {
  opacity: 0.5;
  pointer-events: none;
}

.wishlist-item.adding {
  opacity: 0.7;
}

/* Checkbox */
.item-checkbox {
  display: flex;
  align-items: center;
}

.item-checkbox input[type="checkbox"] {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

/* Product Image */
.item-image {
  display: block;
  width: 120px;
  height: 120px;
  border-radius: 8px;
  overflow: hidden;
  flex-shrink: 0;
}

.item-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.2s;
}

.item-image:hover img {
  transform: scale(1.05);
}

/* Product Info */
.item-info {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.item-name {
  font-size: 1.1rem;
  font-weight: 600;
  color: #1a1a1a;
  text-decoration: none;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.item-name:hover {
  color: #00a86b;
}

.item-meta {
  display: flex;
  gap: 0.75rem;
  font-size: 0.875rem;
  color: #666;
}

.item-price {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.price-discount {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.discount-rate {
  font-size: 1rem;
  font-weight: 700;
  color: #dc3545;
}

.original-price {
  font-size: 0.875rem;
  color: #999;
  text-decoration: line-through;
}

.current-price {
  font-size: 1.25rem;
  font-weight: 700;
  color: #1a1a1a;
}

.item-stats {
  display: flex;
  gap: 1rem;
  font-size: 0.875rem;
  color: #666;
}

.added-date {
  font-size: 0.875rem;
  color: #999;
  margin-top: auto;
}

/* Actions */
.item-actions {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  align-items: flex-end;
}

.btn-add-cart,
.btn-remove {
  padding: 0.625rem 1.25rem;
  border: none;
  border-radius: 4px;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
  min-width: 120px;
}

.btn-add-cart {
  background: #00a86b;
  color: white;
}

.btn-add-cart:hover:not(:disabled) {
  background: #008c5a;
}

.btn-remove {
  background: white;
  color: #dc3545;
  border: 1px solid #dc3545;
}

.btn-remove:hover:not(:disabled) {
  background: #dc3545;
  color: white;
}

.btn-add-cart:disabled,
.btn-remove:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Footer */
.wishlist-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 2rem;
  padding-top: 1.5rem;
  border-top: 2px solid #f0f0f0;
}

.select-all {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.select-all input[type="checkbox"] {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.select-all label {
  font-size: 1rem;
  font-weight: 600;
  color: #333;
  cursor: pointer;
}

.btn-add-all-cart {
  padding: 0.875rem 2rem;
  background: #00a86b;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-add-all-cart:hover:not(:disabled) {
  background: #008c5a;
}

.btn-add-all-cart:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Responsive */
@media (max-width: 768px) {
  .wishlist-page {
    padding: 1rem 0;
  }

  .page-title {
    font-size: 1.5rem;
  }

  .wishlist-item {
    grid-template-columns: auto 1fr;
    grid-template-areas:
      "checkbox image"
      "info info"
      "actions actions";
  }

  .item-checkbox {
    grid-area: checkbox;
  }

  .item-image {
    grid-area: image;
    width: 100px;
    height: 100px;
  }

  .item-info {
    grid-area: info;
  }

  .item-actions {
    grid-area: actions;
    flex-direction: row;
    justify-content: flex-end;
    gap: 0.5rem;
  }

  .btn-add-cart,
  .btn-remove {
    flex: 1;
    min-width: auto;
  }

  .wishlist-footer {
    flex-direction: column;
    gap: 1rem;
  }

  .btn-add-all-cart {
    width: 100%;
  }
}

@media (max-width: 480px) {
  .page-header {
    margin-bottom: 1.5rem;
  }

  .wishlist-header {
    flex-direction: column;
    gap: 1rem;
    align-items: flex-start;
  }

  .btn-remove-selected {
    width: 100%;
  }
}
</style>
