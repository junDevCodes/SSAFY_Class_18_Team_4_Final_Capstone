<template>
  <div class="product-edit-page">
    <div class="container">
      <div class="page-header">
        <h1 class="page-title">상품 수정</h1>
        <p class="page-description">등록한 상품 정보를 그대로 수정하고 바로 반영하세요.</p>
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
            placeholder="상품명을 입력하세요"
            required
          />
        </div>

        <div class="form-row">
          <div class="form-group">
            <label for="original_price">가격 (정가)</label>
            <input
              id="original_price"
              v-model.number="formData.original_price"
              type="number"
              min="0"
              placeholder="0"
            />
          </div>
          <div class="form-group">
            <label for="price">할인가격 (판매가) *</label>
            <input
              id="price"
              v-model.number="formData.price"
              type="number"
              min="0"
              placeholder="0"
              required
            />
            <p v-if="discountRate !== null" class="field-hint">
              예상 할인율: {{ discountRate }}%
            </p>
          </div>
          <div class="form-group">
            <label for="stock_quantity">재고 *</label>
            <input
              id="stock_quantity"
              v-model.number="formData.stock_quantity"
              type="number"
              min="0"
              placeholder="0"
              required
            />
          </div>
        </div>

        <div class="form-group">
          <label for="category">카테고리 *</label>
          <select
            id="category"
            v-model.number="formData.category_id"
            required
          >
            <option value="" disabled>카테고리를 선택하세요</option>
            <option
              v-for="category in categories"
              :key="category.id"
              :value="category.id"
            >
              {{ category.name }}
            </option>
          </select>
        </div>

        <div class="form-row single">
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
          <label>메인 상품 이미지 업로드 *</label>
          <div class="upload-box">
            <input
              ref="mainFileInput"
              class="file-input"
              type="file"
              accept="image/jpeg,image/png,image/gif,image/webp"
              multiple
              @change="handleMainImages"
            />
            <div class="upload-copy">
              <strong>파일을 선택하거나 클릭해 업로드</strong>
              <span>최대 10개, JPEG/PNG/GIF/WebP, 5MB 이하</span>
            </div>
          </div>
          <div v-if="existingMainImages.length" class="preview-grid">
            <div v-for="(item, index) in existingMainImages" :key="item.id || item.url" class="preview-card">
              <img :src="item.url" :alt="item.filename" />
              <div class="preview-meta">
                <span class="filename" :title="item.filename">{{ item.filename }}</span>
                <button type="button" class="btn-remove-image" @click="removeExistingMainImage(index, item)">삭제</button>
              </div>
            </div>
          </div>
          <div v-if="mainImages.length" class="preview-grid">
            <div v-for="(item, index) in mainImages" :key="item.preview" class="preview-card">
              <img :src="item.preview" :alt="item.file.name" />
              <div class="preview-meta">
                <span class="filename" :title="item.file.name">{{ item.file.name }}</span>
                <button type="button" class="btn-remove-image" @click="removeMainImage(index)">삭제</button>
              </div>
            </div>
          </div>
        </div>

        <div class="form-group">
          <label for="short_description">간단한 설명</label>
          <input
            id="short_description"
            v-model="formData.short_description"
            type="text"
            maxlength="120"
            placeholder="한 줄 설명 (예: 달콤한 제철 과일)"
          />
          <p class="field-hint">리스트 노출용, 120자 이내 추천</p>
        </div>

        <div class="form-group">
          <label>상품 상세 설명 이미지 업로드</label>
          <div class="upload-box">
            <input
              ref="detailFileInput"
              class="file-input"
              type="file"
              accept="image/jpeg,image/png,image/gif,image/webp"
              multiple
              @change="handleDetailImages"
            />
            <div class="upload-copy">
              <strong>파일을 선택하거나 클릭해 업로드</strong>
              <span>최대 20개, JPEG/PNG/GIF/WebP, 10MB 이하</span>
            </div>
          </div>
          <div v-if="existingDetailImages.length" class="preview-grid">
            <div v-for="(url, index) in existingDetailImages" :key="url + index" class="preview-card">
              <img :src="url" :alt="`상세 이미지 ${index + 1}`" />
              <div class="preview-meta">
                <span class="filename" :title="getFilenameFromUrl(url)">{{ getFilenameFromUrl(url) }}</span>
              </div>
            </div>
          </div>
          <div v-if="detailImages.length" class="preview-grid">
            <div v-for="(item, index) in detailImages" :key="item.preview" class="preview-card">
              <img :src="item.preview" :alt="item.file.name" />
              <div class="preview-meta">
                <span class="filename" :title="item.file.name">{{ item.file.name }}</span>
                <button type="button" class="btn-remove-image" @click="removeDetailImage(index)">삭제</button>
              </div>
            </div>
          </div>
        </div>

        <div class="form-group">
          <label for="full_description">상품 설명 (선택)</label>
          <textarea
            id="full_description"
            v-model="formData.full_description"
            rows="6"
            placeholder="상품에 대한 상세 설명을 입력하세요."
          ></textarea>
        </div>

        <div v-if="error" class="error-message">{{ error }}</div>

        <div class="form-actions">
          <button type="submit" class="btn-submit" :disabled="submitting">
            <span v-if="submitting">수정 중...</span>
            <span v-else>변경사항 저장</span>
          </button>
          <router-link to="/seller/products" class="btn-cancel">취소</router-link>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { productsAPI, sellerProductsAPI } from '@/services/api'
import type { Category } from '@/types/product'

type UploadItem = { file: File; preview: string }
type ExistingImage = { id?: number; url: string; filename: string }

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const submitting = ref(false)
const error = ref<string | null>(null)
const product = ref<any>(null)
const categories = ref<Category[]>([])

const formData = reactive({
  name: '',
  price: 0,
  original_price: 0,
  stock_quantity: 0,
  category_id: null as number | null,
  unit: '',
  short_description: '',
  full_description: ''
})

const mainImages = ref<UploadItem[]>([])
const detailImages = ref<UploadItem[]>([])
const existingMainImages = ref<ExistingImage[]>([])
const existingDetailImages = ref<string[]>([])

const getFilenameFromUrl = (url: string) => {
  if (!url) return 'image'
  const parts = url.split('/')
  return parts[parts.length - 1] || 'image'
}

const discountRate = computed(() => {
  if (!formData.original_price || !formData.price) return null
  if (formData.original_price <= formData.price) return null
  const rate = Math.round(((formData.original_price - formData.price) / formData.original_price) * 100)
  return Number.isFinite(rate) ? rate : null
})

const allowedImageTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']

const revokePreviews = (items: UploadItem[]) => {
  items.forEach((item) => URL.revokeObjectURL(item.preview))
}

const validateAndAddFiles = (files: File[], target: 'main' | 'detail') => {
  error.value = null
  const limit = target === 'main' ? 10 : 20
  const maxSize = target === 'main' ? 5 * 1024 * 1024 : 10 * 1024 * 1024
  const current = target === 'main' ? mainImages : detailImages

  const next: UploadItem[] = [...current.value]
  for (const file of files) {
    if (!allowedImageTypes.includes(file.type)) {
      error.value = 'JPEG, PNG, GIF, WebP 형식만 업로드할 수 있습니다.'
      continue
    }
    if (file.size > maxSize) {
      error.value = target === 'main' ? '메인 이미지는 5MB 이하만 업로드하세요.' : '상세 이미지는 10MB 이하만 업로드하세요.'
      continue
    }
    if (next.length >= limit) {
      error.value = target === 'main' ? '메인 이미지는 최대 10개까지 업로드할 수 있습니다.' : '상세 이미지는 최대 20개까지 업로드할 수 있습니다.'
      break
    }
    next.push({ file, preview: URL.createObjectURL(file) })
  }
  current.value = next
}

const handleMainImages = (event: Event) => {
  const files = (event.target as HTMLInputElement)?.files
  if (files) {
    validateAndAddFiles(Array.from(files), 'main')
    ;(event.target as HTMLInputElement).value = ''
  }
}

const handleDetailImages = (event: Event) => {
  const files = (event.target as HTMLInputElement)?.files
  if (files) {
    validateAndAddFiles(Array.from(files), 'detail')
    ;(event.target as HTMLInputElement).value = ''
  }
}

const removeMainImage = (index: number) => {
  const removed = mainImages.value.splice(index, 1)
  revokePreviews(removed)
}

const removeDetailImage = (index: number) => {
  const removed = detailImages.value.splice(index, 1)
  revokePreviews(removed)
}

onBeforeUnmount(() => {
  revokePreviews(mainImages.value)
  revokePreviews(detailImages.value)
})

const loadCategories = async () => {
  try {
    const res = await productsAPI.getCategories()
    const results = res.data?.results ?? res.data ?? []
    categories.value = Array.isArray(results) ? results : []
  } catch (err) {
    console.error('???? ???? ??:', err)
  }
}

const loadProduct = async () => {
  loading.value = true
  error.value = null

  try {
    const productId = Number(route.params.id)
    const response = await sellerProductsAPI.getMyProduct(productId)
    const data = response.data
    product.value = data

    formData.name = data.name || ''
    formData.price = Number(data.price) || 0
    formData.original_price = Number(data.original_price) || 0
    formData.stock_quantity = Number(data.stock_quantity ?? data.inventory?.stock_quantity ?? 0) || 0
    formData.category_id = data.category_id || data.category?.id || null
    formData.unit = data.unit || ''
    formData.short_description = data.short_description || data.detail?.short_description || ''
    formData.full_description =
      data.full_description ||
      data.description ||
      data.detail?.full_text_description ||
      ''

    if (Array.isArray(data.images) && data.images.length) {
      existingMainImages.value = data.images
        .filter((img: any) => img?.image_url)
        .map((img: any) => ({
          id: img.id,
          url: img.image_url,
          filename: getFilenameFromUrl(img.image_url)
        }))
    } else if (data.main_image || data.main_image_url) {
      const url = data.main_image || data.main_image_url
      existingMainImages.value = url ? [{ url, filename: getFilenameFromUrl(url) }] : []
    } else {
      existingMainImages.value = []
    }

    const detailImgs = data.detail?.full_image_description || data.full_image_description || []
    existingDetailImages.value = Array.isArray(detailImgs) ? detailImgs.filter(Boolean) : []
  } catch (err: any) {
    error.value = '상품 정보를 불러오는데 실패했습니다.'
  } finally {
    loading.value = false
  }
}

const removeExistingMainImage = async (index: number, image: ExistingImage) => {
  const confirmed = confirm('이 이미지를 삭제하시겠습니까?')
  if (!confirmed) return

  try {
    const productId = Number(route.params.id)
    if (image.id) {
      await sellerProductsAPI.deleteProductImage(productId, image.id)
    }
    existingMainImages.value.splice(index, 1)
  } catch (err: any) {
    error.value = err.response?.data?.message || '이미지 삭제에 실패했습니다.'
  }
}

const validateForm = () => {
  if (!formData.name.trim()) {
    error.value = '상품명을 입력해주세요.'
    return false
  }
  if (!formData.price || formData.price <= 0) {
    error.value = '판매가를 0보다 크게 입력해주세요.'
    return false
  }
  if (formData.original_price && formData.original_price < formData.price) {
    error.value = '할인가격은 정가보다 클 수 없습니다.'
    return false
  }
  if (formData.stock_quantity < 0) {
    error.value = '재고는 0 이상이어야 합니다.'
    return false
  }
  if (!formData.category_id) {
    error.value = '????? ??????.'
    return false
  }
  if (!existingMainImages.value.length && !mainImages.value.length) {
    error.value = '메인 상품 이미지를 최소 1개 이상 유지해주세요.'
    return false
  }
  return true
}

const handleSubmit = async () => {
  error.value = null
  if (!validateForm()) return

  submitting.value = true

  try {
    const productId = Number(route.params.id)
    const payload = {
      name: formData.name.trim(),
      price: formData.price,
      original_price: formData.original_price || undefined,
      stock_quantity: formData.stock_quantity || 0,
      category_id: formData.category_id || undefined,
      unit: formData.unit || undefined,
      short_description: formData.short_description || '',
      full_description: formData.full_description || '',
      description: formData.full_description || ''
    }

    await sellerProductsAPI.updateProduct(productId, payload)

    if (mainImages.value.length) {
      await sellerProductsAPI.uploadProductImages(
        productId,
        mainImages.value.map((item) => item.file)
      )
    }

    if (detailImages.value.length) {
      await sellerProductsAPI.uploadProductDetailImages(
        productId,
        detailImages.value.map((item) => item.file)
      )
    }

    alert('상품이 수정되었습니다.')
    router.push('/seller/products')
  } catch (err: any) {
    error.value =
      err.response?.data?.message ||
      err.response?.data?.error ||
      err.message ||
      '상품 수정에 실패했습니다.'
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  loadCategories()
  loadProduct()
})
</script>

<style scoped>
.product-edit-page {
  min-height: calc(100vh - 4rem);
  background: linear-gradient(to bottom, #fafafa 0%, #ffffff 100%);
  padding-top: 5rem;
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
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.form-row.single {
  grid-template-columns: 1fr;
}

.form-group label {
  display: block;
  font-size: 0.9375rem;
  font-weight: 600;
  color: #333;
  margin-bottom: 0.5rem;
}

.form-group input,
.form-group select,
.form-group textarea {
  width: 100%;
  padding: 0.875rem;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 1rem;
  resize: vertical;
}

.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus {
  outline: none;
  border-color: #00a86b;
}

.field-hint {
  font-size: 0.8125rem;
  color: #999;
  margin-top: 0.375rem;
}

.upload-box {
  position: relative;
  padding: 1.25rem;
  border: 1px dashed #d1d5db;
  border-radius: 10px;
  background: #f9fafb;
  cursor: pointer;
  transition: border-color 0.2s, background 0.2s;
}

.upload-box:hover {
  border-color: #00a86b;
  background: #f4faf6;
}

.file-input {
  position: absolute;
  inset: 0;
  opacity: 0;
  cursor: pointer;
}

.upload-copy {
  pointer-events: none;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  color: #4b5563;
}

.upload-copy strong {
  color: #1f2937;
}

.preview-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 0.75rem;
  margin-top: 1rem;
}

.preview-card {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.preview-card img {
  width: 100%;
  height: 120px;
  object-fit: cover;
}

.preview-meta {
  padding: 0.65rem 0.75rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.filename {
  font-size: 0.85rem;
  color: #374151;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.btn-remove-image {
  padding: 0.35rem 0.65rem;
  background: #dc2626;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 0.8125rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-remove-image:hover {
  background: #b91c1c;
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

  .preview-grid {
    grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  }
}
</style>
