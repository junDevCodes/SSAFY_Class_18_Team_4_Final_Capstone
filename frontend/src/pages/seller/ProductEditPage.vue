<template>
  <div class="product-edit-page">
    <div class="container">
      <div class="page-header">
        <h1 class="page-title">상품 수정</h1>
        <p class="page-description">상품 정보를 수정하세요</p>
      </div>

      <div v-if="loading" class="loading-state">
        <div class="spinner"></div>
        <p>상품 정보를 불러오는 중...</p>
      </div>

      <div v-else-if="error && !product" class="error-state">
        <p class="error-message">{{ error }}</p>
        <router-link to="/seller/products" class="btn-back">목록으로</router-link>
      </div>

      <form v-else @submit.prevent="handleSubmit" class="product-form">
        <div class="form-group">
          <label for="name">상품명 *</label>
          <input
            id="name"
            v-model="formData.name"
            type="text"
            required
          />
        </div>

        <div class="form-row">
          <div class="form-group">
            <label for="price">가격 *</label>
            <input
              id="price"
              v-model.number="formData.price"
              type="number"
              min="0"
              required
            />
          </div>

          <div class="form-group">
            <label for="stock_quantity">재고 수량</label>
            <input
              id="stock_quantity"
              v-model.number="formData.stock_quantity"
              type="number"
              min="0"
            />
          </div>

          <div class="form-group">
            <label for="unit">단위</label>
            <input
              id="unit"
              v-model="formData.unit"
              type="text"
            />
          </div>
        </div>

        <div class="form-group">
          <label for="short_description">짧은 설명</label>
          <input
            id="short_description"
            v-model="formData.short_description"
            type="text"
          />
        </div>

        <div class="form-group">
          <label for="description">상품 설명</label>
          <textarea
            id="description"
            v-model="formData.description"
            rows="6"
          ></textarea>
        </div>

        <div class="form-group">
          <label for="main_image_url">메인 이미지 URL</label>
          <input
            id="main_image_url"
            v-model="formData.main_image_url"
            type="url"
            @input="handleImageUrlChange"
          />
          <p class="field-hint">MVP: 이미지 URL을 직접 입력해주세요</p>
          <div v-if="formData.main_image_url && imagePreview" class="image-preview">
            <img :src="formData.main_image_url" alt="이미지 미리보기" @error="handleImageError" />
            <button type="button" @click="clearImage" class="btn-remove-image">이미지 제거</button>
          </div>
          <div v-else-if="formData.main_image_url && !imagePreview" class="image-error">
            <p>이미지를 불러올 수 없습니다. URL을 확인해주세요.</p>
          </div>
        </div>

        <div v-if="error" class="error-message">{{ error }}</div>

        <div class="form-actions">
          <button type="submit" class="btn-submit" :disabled="submitting">
            <span v-if="submitting">저장 중...</span>
            <span v-else>변경사항 저장</span>
          </button>
          <router-link to="/seller/products" class="btn-cancel">취소</router-link>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { sellerProductsAPI } from '@/services/api'

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const submitting = ref(false)
const error = ref<string | null>(null)
const product = ref<any>(null)
const imagePreview = ref(false)

const formData = reactive({
  name: '',
  price: 0,
  stock_quantity: 0,
  unit: '',
  short_description: '',
  description: '',
  main_image_url: ''
})

// Handle image URL change
const handleImageUrlChange = () => {
  if (formData.main_image_url) {
    try {
      new URL(formData.main_image_url)
      const img = new Image()
      img.onload = () => {
        imagePreview.value = true
      }
      img.onerror = () => {
        imagePreview.value = false
      }
      img.src = formData.main_image_url
    } catch {
      imagePreview.value = false
    }
  } else {
    imagePreview.value = false
  }
}

// Handle image error
const handleImageError = () => {
  imagePreview.value = false
}

// Clear image
const clearImage = () => {
  formData.main_image_url = ''
  imagePreview.value = false
}

const loadProduct = async () => {
  loading.value = true
  error.value = null

  try {
    const productId = Number(route.params.id)
    const response = await sellerProductsAPI.getMyProduct(productId)
    product.value = response.data

    formData.name = product.value.name || ''
    formData.price = product.value.price || 0
    formData.stock_quantity = product.value.stock_quantity || 0
    formData.unit = product.value.unit || ''
    formData.short_description = product.value.short_description || ''
    formData.description = product.value.description || ''
    formData.main_image_url = product.value.main_image_url || ''
    
    // Check if image URL is valid
    if (formData.main_image_url) {
      handleImageUrlChange()
    }
  } catch (err: any) {
    error.value = '상품 정보를 불러오는데 실패했습니다.'
  } finally {
    loading.value = false
  }
}

const handleSubmit = async () => {
  error.value = null
  submitting.value = true

  try {
    const productId = Number(route.params.id)
    const data: any = {
      name: formData.name,
      price: formData.price,
      stock_quantity: formData.stock_quantity
    }

    if (formData.unit) data.unit = formData.unit
    if (formData.short_description) data.short_description = formData.short_description
    if (formData.description) data.description = formData.description
    if (formData.main_image_url) data.main_image_url = formData.main_image_url

    await sellerProductsAPI.updateProduct(productId, data)
    alert('상품이 수정되었습니다.')
    router.push('/seller/products')
  } catch (err: any) {
    error.value = err.response?.data?.message || '상품 수정에 실패했습니다.'
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  loadProduct()
})
</script>

<style scoped>
.product-edit-page {
  min-height: calc(100vh - 4rem);
  background: linear-gradient(to bottom, #fafafa 0%, #ffffff 100%);
  padding-top: 5rem; /* 헤더 높이(64px) + 여백 */
  padding-bottom: 4rem;
}

.container {
  max-width: 900px;
  margin: 0 auto;
  padding: 0 1rem;
}

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
}

.loading-state,
.error-state {
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
  padding: 1rem;
  background: #fee;
  color: #dc3545;
  border-radius: 6px;
  margin-bottom: 1.5rem;
}

.btn-back {
  display: inline-block;
  padding: 0.75rem 1.5rem;
  background: #00a86b;
  color: white;
  text-decoration: none;
  border-radius: 6px;
}

.product-form {
  background: white;
  border-radius: 12px;
  padding: 2.5rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-row {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.form-group label {
  display: block;
  font-size: 0.9375rem;
  font-weight: 600;
  color: #333;
  margin-bottom: 0.5rem;
}

.form-group input,
.form-group textarea {
  width: 100%;
  padding: 0.875rem;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 1rem;
}

.form-group input:focus,
.form-group textarea:focus {
  outline: none;
  border-color: #00a86b;
}

.field-hint {
  font-size: 0.8125rem;
  color: #999;
  margin-top: 0.375rem;
}

.image-preview {
  margin-top: 1rem;
  padding: 1rem;
  background: #f8f9fa;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
}

.image-preview img {
  width: 100%;
  max-width: 400px;
  height: auto;
  border-radius: 6px;
  margin-bottom: 0.75rem;
  display: block;
}

.btn-remove-image {
  padding: 0.5rem 1rem;
  background: #dc2626;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-remove-image:hover {
  background: #b91c1c;
}

.image-error {
  margin-top: 0.75rem;
  padding: 0.75rem;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 6px;
  color: #dc2626;
  font-size: 0.875rem;
}

.form-actions {
  display: flex;
  gap: 1rem;
  padding-top: 1rem;
}

.btn-submit,
.btn-cancel {
  padding: 1rem 2rem;
  border: none;
  border-radius: 8px;
  font-size: 1.125rem;
  font-weight: 700;
  cursor: pointer;
  text-decoration: none;
  display: inline-block;
  text-align: center;
}

.btn-submit {
  flex: 1;
  background: #00a86b;
  color: white;
}

.btn-submit:hover:not(:disabled) {
  background: #008c5a;
}

.btn-submit:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-cancel {
  background: #e9ecef;
  color: #333;
}

.btn-cancel:hover {
  background: #dee2e6;
}

@media (max-width: 768px) {
  .form-row {
    grid-template-columns: 1fr;
  }

  .form-actions {
    flex-direction: column;
  }
}
</style>
