<template>
  <div class="seller-register-page">
    <div class="container">
      <!-- Page Header -->
      <div class="page-header">
        <h1 class="page-title">판매자 등록</h1>
        <p class="page-description">
          판매자로 등록하여 농산물을 판매하세요
        </p>
      </div>

      <!-- Registration Form -->
      <div class="register-content">
        <form @submit.prevent="handleSubmit" class="register-form">
          <!-- Brand Information Section -->
          <section class="form-section">
            <h2 class="section-title">브랜드 정보</h2>
            <p class="section-description">고객에게 보여질 브랜드 정보를 입력해주세요</p>

            <div class="form-group">
              <label for="brand_name">브랜드명 *</label>
              <input
                id="brand_name"
                v-model="formData.brand_name"
                type="text"
                placeholder="브랜드명을 입력하세요"
                required
              />
            </div>

            <div class="form-group">
              <label for="brand_name_en">브랜드 영문명</label>
              <input
                id="brand_name_en"
                v-model="formData.brand_name_en"
                type="text"
                placeholder="Brand Name (영문)"
              />
            </div>

            <div class="form-group">
              <label for="brand_description">브랜드 소개 *</label>
              <textarea
                id="brand_description"
                v-model="formData.brand_description"
                rows="4"
                placeholder="브랜드를 소개해주세요"
                required
              ></textarea>
            </div>

            <div class="form-group">
              <label for="brand_logo_url">브랜드 로고 URL</label>
              <input
                id="brand_logo_url"
                v-model="formData.brand_logo_url"
                type="url"
                placeholder="https://example.com/logo.png"
              />
              <p class="field-hint">MVP: 이미지 URL을 직접 입력해주세요</p>
            </div>

            <div class="form-group">
              <label for="brand_banner_url">브랜드 배너 URL</label>
              <input
                id="brand_banner_url"
                v-model="formData.brand_banner_url"
                type="url"
                placeholder="https://example.com/banner.png"
              />
              <p class="field-hint">브랜드 페이지 상단에 표시될 배너 이미지</p>
            </div>
          </section>

          <!-- Business Information Section -->
          <section class="form-section">
            <h2 class="section-title">사업자 정보</h2>
            <p class="section-description">사업자 등록 정보를 입력해주세요</p>

            <div class="form-group">
              <label for="business_registration_number">사업자 등록번호</label>
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
                <option value="">선택하세요</option>
                <option value="individual">개인사업자</option>
                <option value="corporation">법인사업자</option>
                <option value="cooperative">농업협동조합</option>
              </select>
            </div>

            <div class="form-group">
              <label for="company_name">상호명</label>
              <input
                id="company_name"
                v-model="formData.company_name"
                type="text"
                placeholder="상호명"
              />
            </div>

            <div class="form-group">
              <label for="ceo_name">대표자명</label>
              <input
                id="ceo_name"
                v-model="formData.ceo_name"
                type="text"
                placeholder="대표자명"
              />
            </div>

            <div class="form-group">
              <label for="business_phone">사업장 전화번호</label>
              <input
                id="business_phone"
                v-model="formData.business_phone"
                type="tel"
                placeholder="02-0000-0000"
              />
            </div>

            <div class="form-group">
              <label for="business_email">사업장 이메일</label>
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

            <div class="form-group">
              <label for="business_address">사업장 주소</label>
              <input
                id="business_address"
                v-model="formData.business_address"
                type="text"
                placeholder="사업장 주소를 입력하세요"
              />
            </div>

            <div class="form-group">
              <label for="warehouse_address">물류창고 주소</label>
              <input
                id="warehouse_address"
                v-model="formData.warehouse_address"
                type="text"
                placeholder="물류창고 주소를 입력하세요"
              />
            </div>
          </section>

          <!-- Settlement Information Section -->
          <section class="form-section">
            <h2 class="section-title">정산 정보</h2>
            <p class="section-description">판매 대금을 받을 계좌 정보를 입력해주세요</p>

            <div class="form-group">
              <label for="bank_name">은행명</label>
              <select id="bank_name" v-model="formData.bank_name">
                <option value="">선택하세요</option>
                <option value="KB국민은행">KB국민은행</option>
                <option value="신한은행">신한은행</option>
                <option value="우리은행">우리은행</option>
                <option value="하나은행">하나은행</option>
                <option value="NH농협은행">NH농협은행</option>
                <option value="IBK기업은행">IBK기업은행</option>
                <option value="SC제일은행">SC제일은행</option>
                <option value="한국씨티은행">한국씨티은행</option>
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
                placeholder="계좌번호 (숫자만 입력)"
              />
            </div>

            <div class="form-group">
              <label for="account_holder_name">예금주명</label>
              <input
                id="account_holder_name"
                v-model="formData.account_holder_name"
                type="text"
                placeholder="예금주명"
              />
            </div>
          </section>

          <!-- Verification Documents Section -->
          <section class="form-section">
            <h2 class="section-title">인증 서류</h2>
            <p class="section-description">판매자 심사를 위한 서류를 제출해주세요</p>

            <div class="form-group">
              <label for="verification_document_url">인증 서류 URL</label>
              <input
                id="verification_document_url"
                v-model="formData.verification_document_url"
                type="url"
                placeholder="https://example.com/document.pdf"
              />
              <p class="field-hint">
                MVP: 사업자등록증, 통장사본 등의 문서 URL을 입력해주세요
              </p>
            </div>
          </section>

          <!-- Error Message -->
          <div v-if="error" class="error-message">
            {{ error }}
          </div>

          <!-- Success Message -->
          <div v-if="successMessage" class="success-message">
            {{ successMessage }}
          </div>

          <!-- Terms Agreement -->
          <div class="terms-section">
            <label class="checkbox-label">
              <input type="checkbox" v-model="agreedToTerms" required />
              <span>판매자 약관 및 운영 정책에 동의합니다 *</span>
            </label>
          </div>

          <!-- Form Actions -->
          <div class="form-actions">
            <button
              type="submit"
              class="btn-submit"
              :disabled="submitting || !agreedToTerms"
            >
              <span v-if="submitting">등록 중...</span>
              <span v-else>판매자 등록</span>
            </button>

            <router-link to="/mypage" class="btn-cancel">
              취소
            </router-link>
          </div>
        </form>

        <!-- Info Sidebar -->
        <aside class="info-sidebar">
          <div class="info-card">
            <h3 class="card-title">판매자 등록 안내</h3>
            <ul class="info-list">
              <li>판매자 등록 심사는 자동으로 승인됩니다 (MVP)</li>
              <li>승인 후 즉시 상품 등록이 가능합니다</li>
              <li>정확한 정보 입력이 필요합니다</li>
              <li>필수 항목은 * 표시되어 있습니다</li>
            </ul>
          </div>

          <div class="info-card">
            <h3 class="card-title">판매자 혜택</h3>
            <ul class="benefit-list">
              <li>
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                </svg>
                <span>무료 상품 등록</span>
              </li>
              <li>
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                </svg>
                <span>브랜드 페이지 제공</span>
              </li>
              <li>
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                </svg>
                <span>판매 통계 제공</span>
              </li>
              <li>
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                </svg>
                <span>고객 관리 도구</span>
              </li>
            </ul>
          </div>

          <div class="help-card">
            <h3 class="card-title">도움이 필요하신가요?</h3>
            <p>판매자 등록과 관련하여 궁금한 사항이 있으시면 고객센터로 문의해주세요</p>
            <a href="mailto:seller@example.com" class="btn-contact">
              문의하기
            </a>
          </div>
        </aside>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { sellersAPI } from '@/services/api'

const router = useRouter()
const authStore = useAuthStore()

const submitting = ref(false)
const error = ref<string | null>(null)
const successMessage = ref<string | null>(null)
const agreedToTerms = ref(false)

// Form data
const formData = reactive({
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

// Handle form submit
const handleSubmit = async () => {
  error.value = null
  successMessage.value = null

  // Validate required fields
  if (!formData.brand_name.trim()) {
    error.value = '브랜드명을 입력해주세요.'
    return
  }

  if (!formData.brand_description.trim()) {
    error.value = '브랜드 소개를 입력해주세요.'
    return
  }

  if (!agreedToTerms.value) {
    error.value = '판매자 약관에 동의해주세요.'
    return
  }

  submitting.value = true

  try {
    // Prepare data - only send non-empty fields
    const data: any = {
      brand_name: formData.brand_name.trim(),
      brand_description: formData.brand_description.trim()
    }

    // Add optional fields if provided
    if (formData.brand_name_en.trim()) data.brand_name_en = formData.brand_name_en.trim()
    if (formData.brand_logo_url.trim()) data.brand_logo_url = formData.brand_logo_url.trim()
    if (formData.brand_banner_url.trim()) data.brand_banner_url = formData.brand_banner_url.trim()
    if (formData.business_registration_number.trim()) data.business_registration_number = formData.business_registration_number.trim()
    if (formData.business_type) data.business_type = formData.business_type
    if (formData.company_name.trim()) data.company_name = formData.company_name.trim()
    if (formData.ceo_name.trim()) data.ceo_name = formData.ceo_name.trim()
    if (formData.business_phone.trim()) data.business_phone = formData.business_phone.trim()
    if (formData.business_email.trim()) data.business_email = formData.business_email.trim()
    if (formData.customer_service_phone.trim()) data.customer_service_phone = formData.customer_service_phone.trim()
    if (formData.business_address.trim()) data.business_address = formData.business_address.trim()
    if (formData.warehouse_address.trim()) data.warehouse_address = formData.warehouse_address.trim()
    if (formData.bank_name) data.bank_name = formData.bank_name
    if (formData.bank_account_number.trim()) data.bank_account_number = formData.bank_account_number.trim()
    if (formData.account_holder_name.trim()) data.account_holder_name = formData.account_holder_name.trim()
    if (formData.verification_document_url.trim()) data.verification_document_url = formData.verification_document_url.trim()

    // Register as seller
    await sellersAPI.registerAsSeller(data)

    // Reload user to update isSeller status
    await authStore.loadUser()

    // Show success message
    successMessage.value = '판매자 등록이 완료되었습니다! 판매자 대시보드로 이동합니다...'

    // Redirect to seller dashboard after 2 seconds
    setTimeout(() => {
      router.push('/seller/dashboard')
    }, 2000)
  } catch (err: any) {
    console.error('판매자 등록 실패:', err)
    error.value = err.response?.data?.message || '판매자 등록에 실패했습니다. 다시 시도해주세요.'
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.seller-register-page {
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

/* Register Content */
.register-content {
  display: grid;
  grid-template-columns: 1fr 380px;
  gap: 2rem;
  align-items: start;
}

/* Register Form */
.register-form {
  background: white;
  border-radius: 8px;
  padding: 2.5rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.form-section {
  padding-bottom: 2rem;
  margin-bottom: 2rem;
  border-bottom: 2px solid #f0f0f0;
}

.form-section:last-of-type {
  border-bottom: none;
}

.section-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: #1a1a1a;
  margin-bottom: 0.5rem;
}

.section-description {
  font-size: 0.9375rem;
  color: #666;
  margin-bottom: 1.5rem;
}

.form-group {
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
.form-group select,
.form-group textarea {
  width: 100%;
  padding: 0.875rem;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 1rem;
  transition: border-color 0.2s;
}

.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus {
  outline: none;
  border-color: #00a86b;
}

.form-group textarea {
  resize: vertical;
  min-height: 100px;
}

.field-hint {
  font-size: 0.8125rem;
  color: #999;
  margin-top: 0.375rem;
}

/* Messages */
.error-message,
.success-message {
  padding: 1rem 1.25rem;
  border-radius: 6px;
  font-size: 0.9375rem;
  font-weight: 500;
  margin-bottom: 1.5rem;
}

.error-message {
  background: #fee;
  color: #dc3545;
  border: 1px solid #fcc;
}

.success-message {
  background: #d4edda;
  color: #155724;
  border: 1px solid #c3e6cb;
}

/* Terms Section */
.terms-section {
  padding: 1.5rem;
  background: #f8f9fa;
  border-radius: 8px;
  margin-bottom: 2rem;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-size: 1rem;
  color: #333;
  cursor: pointer;
}

.checkbox-label input[type="checkbox"] {
  width: 20px;
  height: 20px;
  cursor: pointer;
}

/* Form Actions */
.form-actions {
  display: flex;
  gap: 1rem;
}

.btn-submit,
.btn-cancel {
  padding: 1rem 2.5rem;
  border: none;
  border-radius: 8px;
  font-size: 1.125rem;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s;
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
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 168, 107, 0.3);
}

.btn-submit:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

.btn-cancel {
  background: #e9ecef;
  color: #333;
}

.btn-cancel:hover {
  background: #dee2e6;
}

/* Info Sidebar */
.info-sidebar {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  position: sticky;
  top: 2rem;
}

.info-card,
.help-card {
  padding: 1.5rem;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.card-title {
  font-size: 1.125rem;
  font-weight: 700;
  color: #1a1a1a;
  margin-bottom: 1rem;
}

.info-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.info-list li {
  padding-left: 1.25rem;
  position: relative;
  font-size: 0.9375rem;
  color: #666;
  line-height: 1.5;
}

.info-list li::before {
  content: '•';
  position: absolute;
  left: 0;
  color: #00a86b;
  font-weight: 700;
}

.benefit-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.benefit-list li {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-size: 0.9375rem;
  color: #333;
}

.benefit-list li svg {
  width: 20px;
  height: 20px;
  color: #00a86b;
  flex-shrink: 0;
}

.help-card {
  background: linear-gradient(135deg, #00a86b 0%, #008c5a 100%);
  color: white;
}

.help-card .card-title {
  color: white;
}

.help-card p {
  font-size: 0.9375rem;
  line-height: 1.6;
  margin-bottom: 1.25rem;
}

.btn-contact {
  display: block;
  width: 100%;
  padding: 0.875rem;
  background: white;
  color: #00a86b;
  text-align: center;
  text-decoration: none;
  border-radius: 6px;
  font-size: 1rem;
  font-weight: 700;
  transition: all 0.2s;
}

.btn-contact:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

/* Responsive */
@media (max-width: 1100px) {
  .register-content {
    grid-template-columns: 1fr;
  }

  .info-sidebar {
    position: static;
    order: -1;
  }
}

@media (max-width: 768px) {
  .seller-register-page {
    padding: 1rem 0;
  }

  .page-title {
    font-size: 2rem;
  }

  .register-form {
    padding: 2rem 1.5rem;
  }

  .form-actions {
    flex-direction: column;
  }

  .btn-submit,
  .btn-cancel {
    width: 100%;
  }
}

@media (max-width: 480px) {
  .page-title {
    font-size: 1.75rem;
  }

  .register-form {
    padding: 1.5rem 1rem;
  }

  .section-title {
    font-size: 1.25rem;
  }
}
</style>
