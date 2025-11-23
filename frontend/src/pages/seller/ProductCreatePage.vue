<template>
  <div class="product-create-page">
    <div class="container">
      <div class="page-header">
        <h1 class="page-title">상품 등록</h1>
        <p class="page-description">새로운 상품을 등록하세요</p>
      </div>

      <form @submit.prevent="handleSubmit" class="product-form">
        <div class="form-group">
          <label for="name">상품명 *</label>
          <input
            id="name"
            v-model="formData.name"
            type="text"
            placeholder="상품명을 입력하세요"
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
              placeholder="0"
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
              placeholder="0"
            />
          </div>

          <div class="form-group">
            <label for="unit">단위</label>
            <input
              id="unit"
              v-model="formData.unit"
              type="text"
              placeholder="예: 1kg, 500g"
            />
          </div>
        </div>

        <div class="form-group">
          <label for="short_description">짧은 설명</label>
          <input
            id="short_description"
            v-model="formData.short_description"
            type="text"
            placeholder="한 줄 설명"
          />
        </div>

        <div class="form-group">
          <label for="description">상품 설명</label>
          <textarea
            id="description"
            v-model="formData.description"
            rows="6"
            placeholder="상품에 대한 자세한 설명을 입력하세요"
          ></textarea>
        </div>

        <div class="form-group">
          <label for="main_image_url">메인 이미지 URL</label>
          <input
            id="main_image_url"
            v-model="formData.main_image_url"
            type="url"
            placeholder="https://example.com/image.jpg"
          />
          <p class="field-hint">MVP: 이미지 URL을 직접 입력해주세요</p>
        </div>

        <div v-if="error" class="error-message">{{ error }}</div>

        <div class="form-actions">
          <button type="submit" class="btn-submit" :disabled="submitting">
            <span v-if="submitting">등록 중...</span>
            <span v-else">상품 등록</span>
          </button>
          <router-link to="/seller/products" class="btn-cancel">취소</router-link>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { sellerProductsAPI } from '@/services/api'

const router = useRouter()
const submitting = ref(false)
const error = ref<string | null>(null)

const formData = reactive({
  name: '',
  price: 0,
  stock_quantity: 0,
  unit: '',
  short_description: '',
  description: '',
  main_image_url: ''
})

const handleSubmit = async () => {
  error.value = null
  submitting.value = true

  try {
    const data: any = {
      name: formData.name,
      price: formData.price
    }

    if (formData.stock_quantity) data.stock_quantity = formData.stock_quantity
    if (formData.unit) data.unit = formData.unit
    if (formData.short_description) data.short_description = formData.short_description
    if (formData.description) data.description = formData.description
    if (formData.main_image_url) data.main_image_url = formData.main_image_url

    await sellerProductsAPI.createProduct(data)
    alert('상품이 등록되었습니다.')
    router.push('/seller/products')
  } catch (err: any) {
    error.value = err.response?.data?.message || '상품 등록에 실패했습니다.'
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.product-create-page {
  min-height: 100vh;
  background: #f8f9fa;
  padding: 2rem 0;
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

.error-message {
  padding: 1rem;
  background: #fee;
  color: #dc3545;
  border-radius: 6px;
  margin-bottom: 1.5rem;
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
