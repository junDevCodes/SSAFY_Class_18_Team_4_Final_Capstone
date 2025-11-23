<template>
  <div class="profile-page">
    <div class="page-header">
      <h2 class="page-title">프로필 관리</h2>
      <p class="page-description">회원 정보를 관리할 수 있습니다</p>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>프로필 정보를 불러오는 중...</p>
    </div>

    <!-- Profile Content -->
    <div v-else class="profile-content">
      <!-- Profile Form -->
      <form @submit.prevent="handleSubmit" class="profile-form">
        <div class="form-section">
          <h3 class="section-title">기본 정보</h3>

          <div class="form-group">
            <label for="email">이메일</label>
            <input
              id="email"
              type="email"
              :value="authStore.user?.email"
              disabled
              class="input-disabled"
            />
            <p class="field-hint">이메일은 변경할 수 없습니다</p>
          </div>

          <div class="form-group">
            <label for="name">이름 *</label>
            <input
              id="name"
              v-model="formData.name"
              type="text"
              placeholder="이름을 입력하세요"
              required
            />
          </div>

          <div class="form-group">
            <label for="phone">연락처</label>
            <input
              id="phone"
              v-model="formData.phone"
              type="tel"
              placeholder="010-0000-0000"
            />
          </div>
        </div>

        <div class="form-section">
          <h3 class="section-title">배송지 정보</h3>

          <div class="form-group">
            <label for="postal_code">우편번호</label>
            <div class="postal-code-group">
              <input
                id="postal_code"
                v-model="formData.postal_code"
                type="text"
                placeholder="우편번호"
              />
              <button type="button" class="btn-search-address">주소 검색</button>
            </div>
          </div>

          <div class="form-group">
            <label for="address">주소</label>
            <input
              id="address"
              v-model="formData.address"
              type="text"
              placeholder="주소"
            />
          </div>

          <div class="form-group">
            <label for="address_detail">상세 주소</label>
            <input
              id="address_detail"
              v-model="formData.address_detail"
              type="text"
              placeholder="상세 주소를 입력하세요"
            />
          </div>
        </div>

        <div class="form-section">
          <h3 class="section-title">비밀번호 변경</h3>
          <p class="section-description">비밀번호를 변경하려면 아래 필드를 입력하세요</p>

          <div class="form-group">
            <label for="current_password">현재 비밀번호</label>
            <input
              id="current_password"
              v-model="passwordData.current_password"
              type="password"
              placeholder="현재 비밀번호"
              autocomplete="current-password"
            />
          </div>

          <div class="form-group">
            <label for="new_password">새 비밀번호</label>
            <input
              id="new_password"
              v-model="passwordData.new_password"
              type="password"
              placeholder="새 비밀번호 (8자 이상)"
              autocomplete="new-password"
            />
          </div>

          <div class="form-group">
            <label for="new_password_confirm">새 비밀번호 확인</label>
            <input
              id="new_password_confirm"
              v-model="passwordData.new_password_confirm"
              type="password"
              placeholder="새 비밀번호 확인"
              autocomplete="new-password"
            />
          </div>
        </div>

        <!-- Error Message -->
        <div v-if="error" class="error-message">
          {{ error }}
        </div>

        <!-- Success Message -->
        <div v-if="successMessage" class="success-message">
          {{ successMessage }}
        </div>

        <!-- Form Actions -->
        <div class="form-actions">
          <button
            type="submit"
            class="btn-save"
            :disabled="saving"
          >
            <span v-if="saving">저장 중...</span>
            <span v-else>변경사항 저장</span>
          </button>

          <button
            type="button"
            @click="resetForm"
            class="btn-cancel"
            :disabled="saving"
          >
            취소
          </button>
        </div>
      </form>

      <!-- Account Info -->
      <aside class="account-info">
        <div class="info-card">
          <h3 class="card-title">계정 정보</h3>
          <div class="info-list">
            <div class="info-item">
              <span class="label">회원 유형</span>
              <span class="value">
                <span v-if="authStore.isSeller" class="badge badge-seller">판매자</span>
                <span v-else class="badge badge-buyer">구매자</span>
              </span>
            </div>
            <div class="info-item">
              <span class="label">가입일</span>
              <span class="value">{{ formatDate(authStore.user?.created_at) }}</span>
            </div>
            <div class="info-item">
              <span class="label">마지막 로그인</span>
              <span class="value">{{ formatDate(authStore.user?.last_login) }}</span>
            </div>
          </div>
        </div>

        <div v-if="!authStore.isSeller" class="info-card seller-promotion">
          <h3 class="card-title">판매자로 전환하기</h3>
          <p class="card-description">
            판매자로 등록하고 농산물을 판매해보세요
          </p>
          <router-link to="/seller/register" class="btn-seller-register">
            판매자 등록하기
          </router-link>
        </div>

        <div class="info-card danger-zone">
          <h3 class="card-title">위험 구역</h3>
          <p class="card-description">
            계정을 삭제하면 모든 데이터가 영구적으로 삭제됩니다
          </p>
          <button @click="handleDeleteAccount" class="btn-delete">
            계정 삭제
          </button>
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { authAPI } from '@/services/api'

const authStore = useAuthStore()

const loading = ref(true)
const saving = ref(false)
const error = ref<string | null>(null)
const successMessage = ref<string | null>(null)

// Form data
const formData = reactive({
  name: '',
  phone: '',
  postal_code: '',
  address: '',
  address_detail: ''
})

// Password change data
const passwordData = reactive({
  current_password: '',
  new_password: '',
  new_password_confirm: ''
})

// Load user data
const loadUserData = async () => {
  loading.value = true
  error.value = null

  try {
    const response = await authAPI.getProfile()
    const userData = response.data

    // Fill form with user data
    formData.name = userData.name || ''
    formData.phone = userData.phone || ''
    formData.postal_code = userData.postal_code || ''
    formData.address = userData.address || ''
    formData.address_detail = userData.address_detail || ''
  } catch (err: any) {
    console.error('프로필 로드 실패:', err)
    error.value = '프로필 정보를 불러오는데 실패했습니다.'
  } finally {
    loading.value = false
  }
}

// Handle form submit
const handleSubmit = async () => {
  error.value = null
  successMessage.value = null

  // Validate password change if provided
  if (passwordData.current_password || passwordData.new_password || passwordData.new_password_confirm) {
    if (!passwordData.current_password) {
      error.value = '현재 비밀번호를 입력해주세요.'
      return
    }

    if (!passwordData.new_password) {
      error.value = '새 비밀번호를 입력해주세요.'
      return
    }

    if (passwordData.new_password.length < 8) {
      error.value = '새 비밀번호는 8자 이상이어야 합니다.'
      return
    }

    if (passwordData.new_password !== passwordData.new_password_confirm) {
      error.value = '새 비밀번호가 일치하지 않습니다.'
      return
    }
  }

  saving.value = true

  try {
    // Update profile
    await authAPI.updateProfile({
      name: formData.name,
      phone: formData.phone,
      postal_code: formData.postal_code,
      address: formData.address,
      address_detail: formData.address_detail
    })

    // Update password if provided
    if (passwordData.current_password && passwordData.new_password) {
      try {
        await authAPI.changePassword({
          old_password: passwordData.current_password,
          new_password: passwordData.new_password
        })
      } catch (err: any) {
        throw new Error(err.response?.data?.message || '비밀번호 변경에 실패했습니다.')
      }
    }

    // Reload auth store
    await authStore.loadUser()

    // Clear password fields
    passwordData.current_password = ''
    passwordData.new_password = ''
    passwordData.new_password_confirm = ''

    successMessage.value = '프로필이 성공적으로 업데이트되었습니다.'

    // Clear success message after 3 seconds
    setTimeout(() => {
      successMessage.value = null
    }, 3000)
  } catch (err: any) {
    console.error('프로필 업데이트 실패:', err)
    error.value = err.message || '프로필 업데이트에 실패했습니다.'
  } finally {
    saving.value = false
  }
}

// Reset form
const resetForm = () => {
  loadUserData()
  passwordData.current_password = ''
  passwordData.new_password = ''
  passwordData.new_password_confirm = ''
  error.value = null
  successMessage.value = null
}

// Delete account
const handleDeleteAccount = async () => {
  const confirmed = confirm(
    '정말로 계정을 삭제하시겠습니까? 이 작업은 되돌릴 수 없으며, 모든 데이터가 영구적으로 삭제됩니다.'
  )

  if (!confirmed) return

  const doubleConfirmed = confirm(
    '마지막 확인입니다. 계정을 삭제하면 주문 내역, 찜 목록, 장바구니 등 모든 정보가 삭제됩니다. 계속하시겠습니까?'
  )

  if (!doubleConfirmed) return

  try {
    // MVP: Account deletion not implemented in backend yet
    alert('계정 삭제 기능은 현재 개발 중입니다.')
  } catch (err: any) {
    console.error('계정 삭제 실패:', err)
    alert('계정 삭제에 실패했습니다.')
  }
}

// Format date
const formatDate = (dateString?: string): string => {
  if (!dateString) return '-'

  const date = new Date(dateString)
  return date.toLocaleDateString('ko-KR', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  })
}

// Initialize
onMounted(() => {
  loadUserData()
})
</script>

<style scoped>
.profile-page {
  max-width: 100%;
}

.page-header {
  margin-bottom: 2.5rem;
  padding-bottom: 1.5rem;
  border-bottom: 1px solid rgba(95, 0, 128, 0.1);
}

.page-title {
  font-size: 1.875rem;
  font-weight: 700;
  color: #1a1a1a;
  margin-bottom: 0.5rem;
  letter-spacing: -0.02em;
}

.page-description {
  color: #666;
  font-size: 0.9375rem;
  line-height: 1.6;
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

/* Profile Content */
.profile-content {
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: 2.5rem;
}

/* Profile Form */
.profile-form {
  display: flex;
  flex-direction: column;
  gap: 2.5rem;
}

.form-section {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  padding-bottom: 2rem;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
}

.form-section:last-of-type {
  border-bottom: none;
  padding-bottom: 0;
}

.section-title {
  font-size: 1.25rem;
  font-weight: 700;
  color: #1a1a1a;
  letter-spacing: -0.01em;
}

.section-description {
  font-size: 0.875rem;
  color: #666;
  margin-top: -0.5rem;
  line-height: 1.6;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.625rem;
}

.form-group label {
  font-size: 0.875rem;
  font-weight: 600;
  color: #333;
  letter-spacing: -0.01em;
}

.form-group input {
  padding: 0.875rem 1rem;
  border: 1.5px solid #e5e7eb;
  border-radius: 8px;
  font-size: 0.9375rem;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  background: white;
}

.form-group input:hover {
  border-color: #d1d5db;
}

.form-group input:focus {
  outline: none;
  border-color: #5f0080;
  box-shadow: 0 0 0 3px rgba(95, 0, 128, 0.1);
}

.form-group input:disabled,
.input-disabled {
  background: #f9fafb;
  color: #9ca3af;
  cursor: not-allowed;
  border-color: #e5e7eb;
}

.field-hint {
  font-size: 0.8125rem;
  color: #9ca3af;
  margin-top: -0.25rem;
}

.postal-code-group {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 0.75rem;
}

.btn-search-address {
  padding: 0.875rem 1.5rem;
  background: #5f0080;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  white-space: nowrap;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.btn-search-address:hover {
  background: #4c0066;
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

/* Messages */
.error-message,
.success-message {
  padding: 1rem 1.25rem;
  border-radius: 8px;
  font-size: 0.9375rem;
  font-weight: 500;
  line-height: 1.5;
}

.error-message {
  background: #fef2f2;
  color: #dc2626;
  border: 1px solid #fecaca;
}

.success-message {
  background: #f0fdf4;
  color: #16a34a;
  border: 1px solid #bbf7d0;
}

/* Form Actions */
.form-actions {
  display: flex;
  gap: 0.75rem;
  padding-top: 1rem;
}

.btn-save,
.btn-cancel {
  padding: 0.875rem 2rem;
  border: none;
  border-radius: 8px;
  font-size: 0.9375rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.btn-save {
  background: #5f0080;
  color: white;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.btn-save:hover:not(:disabled) {
  background: #4c0066;
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.btn-cancel {
  background: #f3f4f6;
  color: #374151;
  border: 1px solid #e5e7eb;
}

.btn-cancel:hover:not(:disabled) {
  background: #e5e7eb;
  border-color: #d1d5db;
}

.btn-save:disabled,
.btn-cancel:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

/* Account Info */
.account-info {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.info-card {
  padding: 1.75rem;
  background: #fafafa;
  border-radius: 12px;
  border: 1px solid rgba(0, 0, 0, 0.04);
}

.card-title {
  font-size: 1rem;
  font-weight: 700;
  color: #1a1a1a;
  margin-bottom: 1.25rem;
  letter-spacing: -0.01em;
}

.card-description {
  font-size: 0.875rem;
  color: #666;
  line-height: 1.6;
  margin-bottom: 1rem;
}

.info-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.875rem;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}

.info-item:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.info-item .label {
  color: #6b7280;
}

.info-item .value {
  font-weight: 600;
  color: #1a1a1a;
}

.badge {
  padding: 0.375rem 0.875rem;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.01em;
}

.badge-seller {
  background: linear-gradient(135deg, #5f0080 0%, #4c0066 100%);
  color: white;
}

.badge-buyer {
  background: #6b7280;
  color: white;
}

/* Seller Promotion */
.seller-promotion {
  background: linear-gradient(135deg, #5f0080 0%, #4c0066 100%);
  color: white;
  border: none;
}

.seller-promotion .card-title,
.seller-promotion .card-description {
  color: white;
}

.btn-seller-register {
  display: block;
  width: 100%;
  padding: 0.875rem;
  background: white;
  color: #5f0080;
  text-align: center;
  text-decoration: none;
  border-radius: 8px;
  font-size: 0.9375rem;
  font-weight: 700;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.btn-seller-register:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
}

/* Danger Zone */
.danger-zone {
  background: #fef2f2;
  border: 1px solid #fecaca;
}

.danger-zone .card-title {
  color: #dc2626;
}

.btn-delete {
  width: 100%;
  padding: 0.875rem;
  background: #dc2626;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 0.9375rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.btn-delete:hover {
  background: #b91c1c;
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

/* Responsive */
@media (max-width: 968px) {
  .profile-content {
    grid-template-columns: 1fr;
    gap: 2rem;
  }

  .account-info {
    order: -1;
  }
}

@media (max-width: 480px) {
  .page-title {
    font-size: 1.5rem;
  }

  .form-actions {
    flex-direction: column;
  }

  .btn-save,
  .btn-cancel {
    width: 100%;
  }

  .postal-code-group {
    grid-template-columns: 1fr;
  }

  .info-card {
    padding: 1.25rem;
  }
}
</style>
