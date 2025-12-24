<template>
  <div class="seller-settings-page">
    <div class="container">
      <header class="page-header">
        <div>
          <p class="eyebrow">Seller Workspace</p>
          <h1 class="page-title">판매자 설정</h1>
          <p class="page-description">
            판매자 등록 시 입력했던 브랜드·사업자·정산 정보를 수정해 최신 상태로 유지하세요.
          </p>
        </div>
        <div class="header-actions">
          <div class="chips">
            <span class="chip" :class="hasChanges ? 'chip-warning' : 'chip-success'">
              {{ hasChanges ? '변경사항 있음' : '최신 상태' }}
            </span>
            <span class="chip chip-ghost">BRAND : {{ sellerSlug || '-' }}</span>
          </div>
          <button type="button" class="link-button" @click="router.push('/seller/dashboard')">
            대시보드로 이동
          </button>
        </div>
      </header>

      <div v-if="loading" class="state-card">
        <div class="spinner"></div>
        <p>판매자 정보를 불러오는 중입니다.</p>
      </div>

      <div v-else>
        <div v-if="error" class="state-card error">
          <p>{{ error }}</p>
          <div class="state-actions">
            <button class="btn ghost" type="button" @click="fetchProfile">다시 불러오기</button>
            <router-link to="/seller/dashboard" class="btn link">대시보드로 이동</router-link>
          </div>
        </div>

        <div v-if="successMessage" class="state-card success">
          {{ successMessage }}
        </div>

        <div class="settings-grid">
          <form class="settings-form" @submit.prevent="handleSubmit">
            <section class="form-section">
              <div class="section-header">
                <div>
                  <p class="section-eyebrow">BRAND 정보</p>
                  <h2 class="section-title">BRAND 프로필</h2>
                  <p class="section-description">
                    스토어 상단에 노출되는 핵심 정보예요. BRAND명과 소개는 필수로 입력해주세요.
                  </p>
                </div>
              </div>

              <div class="field-grid">
                <div class="form-group">
                  <label for="brand_name">BRAND명 *</label>
                  <input
                    id="brand_name"
                    v-model="formData.brand_name"
                    type="text"
                    placeholder="BRAND명을 입력하세요"
                    required
                  />
                </div>

                <div class="form-group">
                  <label for="brand_name_en">BRAND명(영문)</label>
                  <input
                    id="brand_name_en"
                    v-model="formData.brand_name_en"
                    type="text"
                    placeholder="Brand Name (EN)"
                  />
                </div>

                <div class="form-group full">
                  <label for="brand_description">BRAND 소개 *</label>
                  <textarea
                    id="brand_description"
                    v-model="formData.brand_description"
                    rows="4"
                    placeholder="BRAND 스토리와 강점을 소개해주세요"
                    required
                  ></textarea>
                </div>

                <div class="form-group">
                  <div class="label-row">
                    <label for="brand_logo_url">BRAND 로고</label>
                    <span class="pill-note">정사각형 권장 · 5MB 이하</span>
                  </div>
                  <div class="upload-box">
                    <input
                      class="file-input"
                      type="file"
                      accept="image/jpeg,image/png,image/gif,image/webp"
                      @change="(event) => handleImageChange(event, 'logo')"
                    />
                    <div class="upload-copy">
                      <strong>로고 이미지 첨부</strong>
                      <span>드래그 또는 클릭해 업로드</span>
                    </div>
                  </div>
                  <div v-if="logoPreview" class="single-preview">
                    <img :src="logoPreview" alt="브랜드 로고 미리보기" />
                    <div class="preview-meta">
                      <span class="filename">{{ logoFile?.file.name || '로고 이미지' }}</span>
                      <button type="button" class="btn-remove-image" @click="clearImage('logo')">삭제</button>
                    </div>
                  </div>
                </div>

                <div class="form-group">
                  <div class="label-row">
                    <label for="brand_banner_url">BRAND 배너</label>
                    <span class="pill-note">가로형 권장 · 5MB 이하</span>
                  </div>
                  <div class="upload-box">
                    <input
                      class="file-input"
                      type="file"
                      accept="image/jpeg,image/png,image/gif,image/webp"
                      @change="(event) => handleImageChange(event, 'banner')"
                    />
                    <div class="upload-copy">
                      <strong>배너 이미지 첨부</strong>
                      <span>드래그 또는 클릭해 업로드</span>
                    </div>
                  </div>
                  <div v-if="bannerPreview" class="single-preview">
                    <img :src="bannerPreview" alt="브랜드 배너 미리보기" />
                    <div class="preview-meta">
                      <span class="filename">{{ bannerFile?.file.name || '배너 이미지' }}</span>
                      <button type="button" class="btn-remove-image" @click="clearImage('banner')">삭제</button>
                    </div>
                  </div>
                </div>
              </div>
            </section>

            <section class="form-section">
              <div class="section-header">
                <div>
                  <p class="section-eyebrow">사업자 정보</p>
                  <h2 class="section-title">사업자·연락처</h2>
                  <p class="section-description">사업자 등록증과 고객센터 연락처 정보를 업데이트하세요.</p>
                </div>
              </div>

              <div class="field-grid">
                <div class="form-group">
                  <label for="business_registration_number">사업자등록번호</label>
                  <input
                    id="business_registration_number"
                    v-model="formData.business_registration_number"
                    type="text"
                    placeholder="000-00-00000"
                  />
                </div>

                <div class="form-group">
                  <label for="business_type">사업자 유형</label>
                  <select id="business_type" v-model="formData.business_type">
                    <option value="">선택해주세요</option>
                    <option value="individual">개인사업자</option>
                    <option value="corporation">법인사업자</option>
                    <option value="cooperative">협동조합</option>
                  </select>
                </div>

                <div class="form-group">
                  <label for="company_name">상호</label>
                  <input
                    id="company_name"
                    v-model="formData.company_name"
                    type="text"
                    placeholder="상호를 입력하세요"
                  />
                </div>

                <div class="form-group">
                  <label for="ceo_name">대표자명</label>
                  <input
                    id="ceo_name"
                    v-model="formData.ceo_name"
                    type="text"
                    placeholder="대표자명을 입력하세요"
                  />
                </div>

                <div class="form-group">
                  <label for="business_phone">대표 전화번호</label>
                  <input
                    id="business_phone"
                    v-model="formData.business_phone"
                    type="tel"
                    placeholder="02-0000-0000"
                  />
                </div>

                <div class="form-group">
                  <label for="business_email">대표 이메일</label>
                  <input
                    id="business_email"
                    v-model="formData.business_email"
                    type="email"
                    placeholder="business@example.com"
                  />
                </div>

                <div class="form-group">
                  <label for="customer_service_phone">고객센터 전화번호</label>
                  <input
                    id="customer_service_phone"
                    v-model="formData.customer_service_phone"
                    type="tel"
                    placeholder="1588-0000"
                  />
                </div>

                <div class="form-group full">
                  <label for="business_address">사업장 주소</label>
                  <input
                    id="business_address"
                    v-model="formData.business_address"
                    type="text"
                    placeholder="사업장 주소를 입력하세요"
                  />
                </div>

                <div class="form-group full">
                  <label for="warehouse_address">물류창고 주소</label>
                  <input
                    id="warehouse_address"
                    v-model="formData.warehouse_address"
                    type="text"
                    placeholder="물류창고 주소를 입력하세요"
                  />
                </div>
              </div>
            </section>

            <section class="form-section">
              <div class="section-header">
                <div>
                  <p class="section-eyebrow">정산 정보</p>
                  <h2 class="section-title">입금 계좌</h2>
                  <p class="section-description">정산 받을 계좌 정보를 확인하고 수정하세요.</p>
                </div>
              </div>

              <div class="field-grid">
                <div class="form-group">
                  <label for="bank_name">은행명</label>
                  <select id="bank_name" v-model="formData.bank_name">
                    <option value="">선택해주세요</option>
                    <option value="KB국민은행">KB국민은행</option>
                    <option value="신한은행">신한은행</option>
                    <option value="우리은행">우리은행</option>
                    <option value="하나은행">하나은행</option>
                    <option value="NH농협은행">NH농협은행</option>
                    <option value="IBK기업은행">IBK기업은행</option>
                    <option value="SC제일은행">SC제일은행</option>
                    <option value="카카오뱅크">카카오뱅크</option>
                    <option value="케이뱅크">케이뱅크</option>
                    <option value="토스뱅크">토스뱅크</option>
                  </select>
                </div>

                <div class="form-group">
                  <label for="bank_account_number">계좌번호</label>
                  <input
                    id="bank_account_number"
                    v-model="formData.bank_account_number"
                    type="text"
                    placeholder="계좌번호를 입력하세요"
                  />
                </div>

                <div class="form-group">
                  <label for="account_holder_name">예금주명</label>
                  <input
                    id="account_holder_name"
                    v-model="formData.account_holder_name"
                    type="text"
                    placeholder="예금주명을 입력하세요"
                  />
                </div>
              </div>
            </section>

            <section class="form-section">
              <div class="section-header">
                <div>
                  <p class="section-eyebrow">증빙 자료</p>
                  <h2 class="section-title">검수용 문서</h2>
                  <p class="section-description">
                    사업자등록증, 통신판매업 신고증 등 검수에 필요한 자료 URL을 첨부하세요.
                  </p>
                </div>
              </div>

              <div class="field-grid">
                <div class="form-group full">
                  <label for="verification_document_url">증빙 서류 URL</label>
                  <input
                    id="verification_document_url"
                    v-model="formData.verification_document_url"
                    type="url"
                    placeholder="https://example.com/document.pdf"
                  />
                  <p class="field-hint">필요 시 여러 자료를 하나의 문서로 업로드한 링크를 남겨주세요.</p>
                </div>
              </div>
            </section>

            <div class="form-actions">
              <div class="actions-meta">
                <p>필수 항목을 모두 입력했는지 확인해주세요.</p>
                <p class="sub">변경된 항목만 서버에 패치됩니다.</p>
              </div>
              <div class="actions-buttons">
                <router-link to="/seller/dashboard" class="btn ghost">취소</router-link>
                <button type="submit" class="btn primary" :disabled="saving">
                  <span v-if="saving">저장 중...</span>
                  <span v-else>정보 저장</span>
                </button>
              </div>
            </div>
          </form>

          <aside class="side-panel">
            <div class="panel-card">
              <h3>BRAND</h3>
              <p class="preview-title">{{ formData.brand_name || '브랜드명' }}</p>
              <p class="preview-sub">{{ formData.brand_description || '브랜드 소개가 여기에 표시됩니다.' }}</p>
              <dl class="preview-list">
                <div>
                  <dt>사업자 유형</dt>
                  <dd>{{ businessTypeText }}</dd>
                </div>
                <div>
                  <dt>대표 연락처</dt>
                  <dd>{{ formData.business_phone || '미입력' }}</dd>
                </div>
                <div>
                  <dt>고객센터</dt>
                  <dd>{{ formData.customer_service_phone || '미입력' }}</dd>
                </div>
                <div>
                  <dt>정산 계좌</dt>
                  <dd>
                    <span v-if="formData.bank_name || formData.bank_account_number">
                      {{ formData.bank_name || '은행' }} · {{ formData.bank_account_number || '계좌번호' }}
                    </span>
                    <span v-else>미입력</span>
                  </dd>
                </div>
              </dl>
            </div>

            <div class="panel-card checklist">
              <h3>검수 체크리스트</h3>
              <ul>
                <li>브랜드명/소개 필수 입력</li>
                <li>사업자등록번호와 대표자 정보 최신화</li>
                <li>고객센터 연락처 확인</li>
                <li>정산 계좌 예금주 일치 여부 확인</li>
                <li>증빙 자료 URL 업로드</li>
              </ul>
            </div>
          </aside>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { sellersAPI } from '@/services/api'
import { useAuthStore } from '@/stores/auth'

type FormKey =
  | 'brand_name'
  | 'brand_name_en'
  | 'brand_description'
  | 'brand_logo_url'
  | 'brand_banner_url'
  | 'business_registration_number'
  | 'business_type'
  | 'company_name'
  | 'ceo_name'
  | 'business_phone'
  | 'business_email'
  | 'customer_service_phone'
  | 'business_address'
  | 'warehouse_address'
  | 'bank_name'
  | 'bank_account_number'
  | 'account_holder_name'
  | 'verification_document_url'

type UploadItem = { file: File; preview: string }

const FIELD_KEYS: FormKey[] = [
  'brand_name',
  'brand_name_en',
  'brand_description',
  'brand_logo_url',
  'brand_banner_url',
  'business_registration_number',
  'business_type',
  'company_name',
  'ceo_name',
  'business_phone',
  'business_email',
  'customer_service_phone',
  'business_address',
  'warehouse_address',
  'bank_name',
  'bank_account_number',
  'account_holder_name',
  'verification_document_url'
]

const router = useRouter()
const authStore = useAuthStore()

const loading = ref(true)
const saving = ref(false)
const error = ref<string | null>(null)
const successMessage = ref<string | null>(null)
const sellerSlug = ref<string>('')

const formData = reactive<Record<FormKey, string>>({
  brand_name: '',
  brand_name_en: '',
  brand_description: '',
  brand_logo_url: '',
  brand_banner_url: '',
  business_registration_number: '',
  business_type: '',
  company_name: '',
  ceo_name: '',
  business_phone: '',
  business_email: '',
  customer_service_phone: '',
  business_address: '',
  warehouse_address: '',
  bank_name: '',
  bank_account_number: '',
  account_holder_name: '',
  verification_document_url: ''
})

const allowedImageTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
const maxImageSize = 5 * 1024 * 1024
const logoFile = ref<UploadItem | null>(null)
const bannerFile = ref<UploadItem | null>(null)

const initialData = ref<Record<FormKey, string>>({ ...formData })

const normalizeValue = (value: unknown) => {
  if (value === null || value === undefined) return ''
  if (typeof value === 'string') return value.trim()
  return String(value)
}

const applyProfileToForm = (data: any) => {
  FIELD_KEYS.forEach((key) => {
    const value = normalizeValue(data?.[key])
    formData[key] = value
  })
  initialData.value = FIELD_KEYS.reduce((acc, key) => {
    acc[key] = normalizeValue(formData[key])
    return acc
  }, {} as Record<FormKey, string>)
}

const buildPayload = () => {
  const payload: Record<string, string> = {}
  FIELD_KEYS.forEach((key) => {
    const current = normalizeValue(formData[key])
    const initial = initialData.value[key] ?? ''
    if (current !== initial) {
      payload[key] = current
    }
  })
  return payload
}

const hasChanges = computed(() => {
  const baseChanged = FIELD_KEYS.some(
    (key) => normalizeValue(formData[key]) !== (initialData.value[key] ?? '')
  )
  return baseChanged || !!logoFile.value || !!bannerFile.value
})

const logoPreview = computed(() => logoFile.value?.preview || formData.brand_logo_url || '')
const bannerPreview = computed(() => bannerFile.value?.preview || formData.brand_banner_url || '')

const revokePreview = (item: UploadItem | null) => {
  if (item?.preview) {
    URL.revokeObjectURL(item.preview)
  }
}

const setImageFile = (files: FileList | null, target: 'logo' | 'banner') => {
  if (!files?.length) return
  error.value = null

  const file = files[0]
  if (!allowedImageTypes.includes(file.type)) {
    error.value = '이미지 파일만 업로드할 수 있습니다. (JPEG/PNG/GIF/WebP)'
    return
  }

  if (file.size > maxImageSize) {
    error.value = '이미지는 5MB 이하만 업로드할 수 있습니다.'
    return
  }

  const next: UploadItem = { file, preview: URL.createObjectURL(file) }
  if (target === 'logo') {
    revokePreview(logoFile.value)
    logoFile.value = next
  } else {
    revokePreview(bannerFile.value)
    bannerFile.value = next
  }
}

const handleImageChange = (event: Event, target: 'logo' | 'banner') => {
  const files = (event.target as HTMLInputElement)?.files
  setImageFile(files, target)
  if (event.target) {
    ;(event.target as HTMLInputElement).value = ''
  }
}

const clearImage = (target: 'logo' | 'banner') => {
  if (target === 'logo') {
    revokePreview(logoFile.value)
    logoFile.value = null
  } else {
    revokePreview(bannerFile.value)
    bannerFile.value = null
  }
}

const uploadBrandImagesIfNeeded = async () => {
  if (!logoFile.value && !bannerFile.value) return

  const uploadSingle = async (item: UploadItem, type: 'logo' | 'banner') => {
    const res = await sellersAPI.uploadSellerImage(item.file, type)
    const url =
      res.data?.image_url ||
      (type === 'logo' ? res.data?.brand_logo_url : res.data?.brand_banner_url) ||
      ''

    if (type === 'logo') {
      formData.brand_logo_url = url
      clearImage('logo')
    } else {
      formData.brand_banner_url = url
      clearImage('banner')
    }
  }

  try {
    if (logoFile.value) {
      await uploadSingle(logoFile.value, 'logo')
    }
    if (bannerFile.value) {
      await uploadSingle(bannerFile.value, 'banner')
    }
  } catch (err: any) {
    const msg =
      err.response?.data?.error ||
      err.response?.data?.detail ||
      err.message ||
      '이미지 업로드에 실패했습니다.'
    throw new Error(msg)
  }
}

const businessTypeText = computed(() => {
  if (formData.business_type === 'individual') return '개인사업자'
  if (formData.business_type === 'corporation') return '법인사업자'
  if (formData.business_type === 'cooperative') return '협동조합'
  return '미입력'
})

const fetchProfile = async () => {
  loading.value = true
  error.value = null
  try {
    await authStore.loadUser()
    const response = await sellersAPI.getMySellerProfile()
    const profile = response.data || {}
    sellerSlug.value = profile.brand_slug || profile.slug || ''
    applyProfileToForm(profile)
  } catch (err: any) {
    console.error('판매자 프로필 불러오기 실패:', err)
    error.value = err.response?.data?.detail || '판매자 정보를 불러오지 못했습니다. 다시 시도해주세요.'
  } finally {
    loading.value = false
  }
}

const handleSubmit = async () => {
  error.value = null
  successMessage.value = null

  if (!formData.brand_name.trim()) {
    error.value = '브랜드명을 입력해주세요.'
    return
  }

  if (!formData.brand_description.trim()) {
    error.value = '브랜드 소개를 입력해주세요.'
    return
  }

  if (!sellerSlug.value) {
    error.value = '판매자 식별 정보를 불러오지 못했습니다. 새로고침 후 다시 시도해주세요.'
    return
  }

  const payload = buildPayload()
  const hasImageUploads = !!logoFile.value || !!bannerFile.value
  if (!hasImageUploads && Object.keys(payload).length === 0) {
    successMessage.value = '변경된 내용이 없습니다.'
    return
  }

  saving.value = true
  try {
    if (Object.keys(payload).length) {
      await sellersAPI.updateSeller(sellerSlug.value, payload)
    }
    await uploadBrandImagesIfNeeded()
    successMessage.value = '판매자 정보가 저장되었습니다.'
    initialData.value = FIELD_KEYS.reduce((acc, key) => {
      acc[key] = normalizeValue(formData[key])
      return acc
    }, {} as Record<FormKey, string>)
  } catch (err: any) {
    console.error('판매자 정보 업데이트 실패:', err)
    error.value =
      err.response?.data?.detail ||
      err.response?.data?.error ||
      err.message ||
      '정보 저장에 실패했습니다. 입력값을 확인해주세요.'
  } finally {
    saving.value = false
  }
}

onBeforeUnmount(() => {
  revokePreview(logoFile.value)
  revokePreview(bannerFile.value)
})

onMounted(() => {
  fetchProfile()
})
</script>

<style scoped>
.seller-settings-page {
  min-height: calc(100vh - 4rem);
  background: linear-gradient(180deg, #f9fafb 0%, #ffffff 100%);
  padding-top: 5rem;
  padding-bottom: 4rem;
}

.container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 1rem;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
  margin-bottom: 2rem;
}

.eyebrow {
  font-size: 0.875rem;
  font-weight: 700;
  color: #00a86b;
  margin-bottom: 0.25rem;
}

.page-title {
  font-size: 2.25rem;
  font-weight: 800;
  color: #1a1a1a;
  margin-bottom: 0.5rem;
}

.page-description {
  font-size: 1rem;
  color: #555;
  max-width: 760px;
  line-height: 1.6;
}

.header-actions {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.75rem;
}

.chips {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.chip {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  border-radius: 999px;
  font-size: 0.875rem;
  font-weight: 700;
}

.chip-success {
  background: #e6f4ec;
  color: #0f9d58;
}

.chip-warning {
  background: #fff4e5;
  color: #c87100;
}

.chip-ghost {
  background: #f2f4f7;
  color: #4b5563;
}

.link-button {
  background: transparent;
  border: none;
  color: #00a86b;
  font-weight: 700;
  cursor: pointer;
}

.state-card {
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  text-align: center;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  margin-bottom: 1.25rem;
}

.state-card.error {
  border: 1px solid #f8d7da;
  color: #a94442;
}

.state-card.success {
  border: 1px solid #c3e6cb;
  color: #155724;
}

.state-actions {
  display: flex;
  justify-content: center;
  gap: 0.75rem;
  margin-top: 1rem;
  flex-wrap: wrap;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #00a86b;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 0.75rem;
}

@keyframes spin {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}

.settings-grid {
  display: grid;
  grid-template-columns: 2fr 0.85fr;
  gap: 1.5rem;
  align-items: start;
}

.settings-form {
  background: white;
  border-radius: 12px;
  padding: 2rem;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.form-section {
  padding-bottom: 1.5rem;
  border-bottom: 1px solid #f0f0f0;
}

.form-section:last-of-type {
  border-bottom: none;
}

.section-header {
  margin-bottom: 1rem;
}

.section-eyebrow {
  font-size: 0.875rem;
  font-weight: 700;
  color: #00a86b;
  margin-bottom: 0.25rem;
}

.section-title {
  font-size: 1.5rem;
  font-weight: 800;
  color: #1f2937;
  margin-bottom: 0.25rem;
}

.section-description {
  font-size: 0.9375rem;
  color: #6b7280;
}

.field-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 1rem 1.25rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-group.full {
  grid-column: 1 / -1;
}

.form-group label {
  font-size: 0.9375rem;
  font-weight: 700;
  color: #111827;
}

.form-group input,
.form-group select,
.form-group textarea {
  width: 100%;
  padding: 0.85rem;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  font-size: 0.95rem;
  transition: border-color 0.2s, box-shadow 0.2s;
  background: #fafafa;
}

.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus {
  outline: none;
  border-color: #00a86b;
  box-shadow: 0 0 0 3px rgba(0, 168, 107, 0.15);
  background: white;
}

.form-group textarea {
  resize: vertical;
  min-height: 120px;
}

.field-hint {
  font-size: 0.85rem;
  color: #6b7280;
}

.label-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.pill-note {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.3rem 0.75rem;
  background: #f3f4f6;
  color: #4b5563;
  border-radius: 999px;
  font-size: 0.8125rem;
  font-weight: 700;
}

.upload-box {
  position: relative;
  padding: 1rem;
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

.single-preview {
  margin-top: 0.75rem;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  overflow: hidden;
  background: #fff;
}

.single-preview img {
  width: 100%;
  height: 180px;
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
  font-size: 0.9rem;
  color: #374151;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.btn-remove-image {
  padding: 0.35rem 0.75rem;
  background: #dc2626;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 0.85rem;
  font-weight: 800;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-remove-image:hover {
  background: #b91c1c;
}

.form-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #f0f0f0;
  flex-wrap: wrap;
}

.actions-meta {
  color: #4b5563;
  font-size: 0.9375rem;
}

.actions-meta .sub {
  font-size: 0.875rem;
  color: #6b7280;
}

.actions-buttons {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.btn {
  border: none;
  border-radius: 10px;
  padding: 0.85rem 1.5rem;
  font-size: 0.95rem;
  font-weight: 800;
  cursor: pointer;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  transition: transform 0.2s, box-shadow 0.2s, background 0.2s;
}

.btn.primary {
  background: linear-gradient(135deg, #00a86b 0%, #0e9760 100%);
  color: white;
}

.btn.primary:hover {
  box-shadow: 0 10px 20px rgba(0, 168, 107, 0.25);
  transform: translateY(-2px);
}

.btn.primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  box-shadow: none;
  transform: none;
}

.btn.ghost {
  background: #f4f6f8;
  color: #1f2937;
}

.btn.ghost:hover {
  background: #e5e7eb;
}

.btn.link {
  background: transparent;
  color: #00a86b;
  padding-left: 0;
  padding-right: 0;
}

.side-panel {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.panel-card {
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
}

.panel-card h3 {
  font-size: 1.125rem;
  font-weight: 800;
  color: #1f2937;
  margin-bottom: 0.75rem;
}

.preview-title {
  font-size: 1.25rem;
  font-weight: 800;
  color: #111827;
  margin-bottom: 0.35rem;
}

.preview-sub {
  font-size: 0.95rem;
  color: #4b5563;
  line-height: 1.5;
  margin-bottom: 1rem;
}

.preview-list {
  display: grid;
  gap: 0.75rem;
  margin: 0;
}

.preview-list dt {
  font-size: 0.875rem;
  color: #6b7280;
  margin-bottom: 0.15rem;
}

.preview-list dd {
  font-size: 0.975rem;
  font-weight: 700;
  color: #1f2937;
  margin: 0;
}

.checklist ul {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.checklist li {
  position: relative;
  padding-left: 1.25rem;
  font-size: 0.95rem;
  color: #374151;
}

.checklist li::before {
  content: '•';
  position: absolute;
  left: 0;
  color: #00a86b;
  font-size: 1.2rem;
  line-height: 1;
}

@media (max-width: 1100px) {
  .settings-grid {
    grid-template-columns: 1fr;
  }

  .side-panel {
    order: -1;
  }
}

@media (max-width: 768px) {
  .seller-settings-page {
    padding-top: 1.5rem;
  }

  .page-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .header-actions {
    align-items: flex-start;
    width: 100%;
  }

  .settings-form {
    padding: 1.5rem;
  }
}

@media (max-width: 480px) {
  .page-title {
    font-size: 1.85rem;
  }

  .form-actions {
    flex-direction: column;
    align-items: flex-start;
  }

  .actions-buttons {
    width: 100%;
  }

  .actions-buttons .btn {
    width: 100%;
    justify-content: center;
  }
}
</style>
