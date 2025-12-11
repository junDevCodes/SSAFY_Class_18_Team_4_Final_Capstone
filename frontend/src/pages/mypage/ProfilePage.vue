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
            <label for="username">닉네임 *</label>
            <input
              id="username"
              v-model="formData.username"
              type="text"
              placeholder="닉네임을 입력하세요"
              required
            />
          </div>
        </div>

        <div class="form-section">
          <div class="section-header">
            <h3 class="section-title">기본 배송지</h3>
            <router-link to="/mypage/addresses" class="link-manage">
              배송지 관리
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" width="16" height="16">
                <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
              </svg>
            </router-link>
          </div>

          <div v-if="defaultAddress" class="default-address-card">
            <div class="address-badge">
              <span class="badge-default">기본</span>
              <span class="address-name">{{ defaultAddress.address_name }}</span>
            </div>
            <div class="address-info">
              <p class="recipient">{{ defaultAddress.recipient_name }} · {{ defaultAddress.recipient_phone }}</p>
              <p class="address-text">
                [{{ defaultAddress.postal_code }}] {{ defaultAddress.address_line1 }}
                <span v-if="defaultAddress.address_line2">, {{ defaultAddress.address_line2 }}</span>
              </p>
            </div>
          </div>
          <div v-else class="no-address">
            <p>등록된 배송지가 없습니다</p>
            <router-link to="/mypage/addresses" class="btn-add-address">
              배송지 추가하기
            </router-link>
          </div>
        </div>

        <div v-if="isPasswordChangeAvailable" class="form-section">
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
        <div v-else class="form-section">
          <h3 class="section-title">비밀번호 변경</h3>
          <p class="section-description">Google/Kakao 소셜 로그인 계정은 비밀번호 변경이 필요 없습니다.</p>
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
                <span v-if="authStore.isAdmin" class="badge badge-admin">관리자</span>
                <span v-else-if="authStore.isSeller" class="badge badge-seller">판매자</span>
                <span v-else class="badge badge-buyer">구매자</span>
              </span>
            </div>
            <div class="info-item">
              <span class="label">이메일</span>
              <span class="value">{{ authStore.user?.email || '-' }}</span>
            </div>
            <div class="info-item">
              <span class="label">시간대</span>
              <span class="value">{{ authStore.user?.timezone || '-' }}</span>
            </div>
          </div>
        </div>

        <div v-if="!authStore.isSeller && !authStore.isAdmin" class="info-card seller-promotion">
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
          <button @click="openDeleteModal" class="btn-delete">
            계정 삭제
          </button>
        </div>
      </aside>
    </div>

    <!-- 계정 삭제 모달 -->
    <div v-if="showDeleteModal" class="modal-overlay" @click.self="closeDeleteModal">
      <div class="modal-content delete-modal">
        <h3 class="modal-title">계정 삭제</h3>

        <!-- 로딩 상태 -->
        <div v-if="deleteCheckLoading" class="modal-loading">
          <div class="spinner"></div>
          <p>계정 삭제 가능 여부를 확인하는 중...</p>
        </div>

        <!-- 삭제 불가 안내 -->
        <div v-else-if="!deleteCheckResult?.can_delete" class="delete-blockers">
          <p class="blocker-title">다음 조건을 해결한 후 계정을 삭제할 수 있습니다:</p>
          <ul class="blocker-list">
            <li v-for="blocker in deleteCheckResult?.blockers" :key="blocker.type">
              {{ blocker.message }}
            </li>
          </ul>
          <div class="modal-actions">
            <button @click="closeDeleteModal" class="btn-modal-cancel">
              확인
            </button>
          </div>
        </div>

        <!-- 삭제 가능 - 확인 폼 -->
        <div v-else class="delete-form">
          <div class="warning-box">
            <p><strong>⚠️ 주의:</strong> 계정 삭제 시 다음 데이터가 영구적으로 삭제됩니다:</p>
            <ul>
              <li>장바구니, 찜 목록</li>
              <li>배송지, 결제수단 정보</li>
              <li v-if="deleteCheckResult?.is_seller">판매자 정보 및 상품</li>
            </ul>
            <p class="preserve-note">주문 이력은 법적 의무에 따라 보존됩니다.</p>
          </div>

          <!-- 이메일 로그인 사용자: 비밀번호 확인 -->
          <div v-if="deleteCheckResult?.auth_method === 'email'" class="form-group">
            <label for="delete_password">비밀번호 확인</label>
            <input
              id="delete_password"
              v-model="deleteFormData.password"
              type="password"
              placeholder="현재 비밀번호를 입력하세요"
              autocomplete="current-password"
            />
          </div>

          <!-- OAuth 사용자: 확인 텍스트 -->
          <div v-else class="form-group">
            <label for="confirm_text">삭제 확인</label>
            <p class="field-hint">계정 삭제를 확인하려면 <strong>'계정삭제'</strong>를 입력하세요</p>
            <input
              id="confirm_text"
              v-model="deleteFormData.confirm_text"
              type="text"
              placeholder="계정삭제"
            />
          </div>

          <!-- 탈퇴 사유 (선택) -->
          <div class="form-group">
            <label for="delete_reason">탈퇴 사유 (선택)</label>
            <textarea
              id="delete_reason"
              v-model="deleteFormData.reason"
              placeholder="서비스 개선을 위해 탈퇴 사유를 알려주세요"
              rows="3"
            ></textarea>
          </div>

          <!-- 에러 메시지 -->
          <div v-if="deleteError" class="error-message">
            {{ deleteError }}
          </div>

          <div class="modal-actions">
            <button
              @click="executeDeleteAccount"
              class="btn-modal-delete"
              :disabled="deleteLoading || !isDeleteFormValid"
            >
              <span v-if="deleteLoading">삭제 중...</span>
              <span v-else>계정 영구 삭제</span>
            </button>
            <button @click="closeDeleteModal" class="btn-modal-cancel" :disabled="deleteLoading">
              취소
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useAddressesStore } from '@/stores/addresses'
import { authAPI } from '@/services/api'
import type { UserAddress } from '@/types/auth'

const router = useRouter()
const authStore = useAuthStore()
const addressesStore = useAddressesStore()

// 기본 배송지 computed
const defaultAddress = computed<UserAddress | null>(() => {
  return addressesStore.addresses.find(addr => addr.is_default) || addressesStore.addresses[0] || null
})

const loading = ref(true)
const saving = ref(false)
const error = ref<string | null>(null)
const successMessage = ref<string | null>(null)

// Form data (배송지 필드 제거 - 별도 배송지 관리 페이지 사용)
const formData = reactive({
  username: '',
})

// Password change data
const passwordData = reactive({
  current_password: '',
  new_password: '',
  new_password_confirm: ''
})

const isPasswordChangeAvailable = computed(() => {
  return !authStore.authProvider || authStore.authProvider === 'email'
})

// 계정 삭제 관련 상태
const showDeleteModal = ref(false)
const deleteCheckLoading = ref(false)
const deleteLoading = ref(false)
const deleteError = ref<string | null>(null)
const deleteCheckResult = ref<{
  can_delete: boolean
  blockers: Array<{ type: string; count: number; message: string }>
  auth_method: 'email' | 'google' | 'kakao' | 'unknown'
  is_seller: boolean
} | null>(null)

const deleteFormData = reactive({
  password: '',
  confirm_text: '',
  reason: ''
})

// 삭제 폼 유효성 검사
const isDeleteFormValid = computed(() => {
  if (!deleteCheckResult.value?.can_delete) return false

  if (deleteCheckResult.value.auth_method === 'email') {
    return deleteFormData.password.length > 0
  } else {
    return deleteFormData.confirm_text === '계정삭제'
  }
})

// Load user data
const loadUserData = async () => {
  loading.value = true
  error.value = null

  try {
    // 프로필 정보 로드
    const response = await authAPI.getProfile()
    const userData = response.data

    // Fill form with user data
    formData.username = userData.username || ''

    // 배송지 목록 로드
    await addressesStore.loadAddresses()
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

  const shouldChangePassword = isPasswordChangeAvailable.value && (
    passwordData.current_password ||
    passwordData.new_password ||
    passwordData.new_password_confirm
  )

  // Validate password change if provided
  if (shouldChangePassword) {
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
    // Update profile (배송지 필드 제거)
    await authAPI.updateProfile({
      username: formData.username,
    })

    // Update password if provided
    if (shouldChangePassword && passwordData.current_password && passwordData.new_password) {
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

// 계정 삭제 모달 열기
const openDeleteModal = async () => {
  showDeleteModal.value = true
  deleteCheckLoading.value = true
  deleteError.value = null
  deleteCheckResult.value = null

  // 폼 초기화
  deleteFormData.password = ''
  deleteFormData.confirm_text = ''
  deleteFormData.reason = ''

  try {
    const response = await authAPI.checkAccountDeletion()
    deleteCheckResult.value = response.data
  } catch (err: any) {
    console.error('계정 삭제 가능 여부 확인 실패:', err)
    deleteError.value = '계정 삭제 가능 여부를 확인하는데 실패했습니다.'
  } finally {
    deleteCheckLoading.value = false
  }
}

// 계정 삭제 모달 닫기
const closeDeleteModal = () => {
  if (deleteLoading.value) return // 삭제 중에는 닫기 불가
  showDeleteModal.value = false
  deleteCheckResult.value = null
  deleteError.value = null
}

// 계정 삭제 실행
const executeDeleteAccount = async () => {
  if (!isDeleteFormValid.value) return

  deleteLoading.value = true
  deleteError.value = null

  try {
    const requestData: { password?: string; confirm_text?: string; reason?: string } = {}

    if (deleteCheckResult.value?.auth_method === 'email') {
      requestData.password = deleteFormData.password
    } else {
      requestData.confirm_text = deleteFormData.confirm_text
    }

    if (deleteFormData.reason.trim()) {
      requestData.reason = deleteFormData.reason.trim()
    }

    await authAPI.deleteAccount(requestData)

    // 삭제 성공 - 로그아웃 처리 및 홈으로 이동
    closeDeleteModal()
    authStore.logout()
    router.push('/')

    // 성공 메시지 표시 (알림 등)
    alert('계정이 삭제되었습니다. 그동안 이용해 주셔서 감사합니다.')
  } catch (err: any) {
    console.error('계정 삭제 실패:', err)

    // 에러 메시지 추출
    const errorData = err.response?.data
    if (errorData?.detail) {
      deleteError.value = errorData.detail
    } else if (errorData?.password) {
      deleteError.value = Array.isArray(errorData.password)
        ? errorData.password[0]
        : errorData.password
    } else if (errorData?.confirm_text) {
      deleteError.value = Array.isArray(errorData.confirm_text)
        ? errorData.confirm_text[0]
        : errorData.confirm_text
    } else {
      deleteError.value = '계정 삭제에 실패했습니다. 다시 시도해주세요.'
    }
  } finally {
    deleteLoading.value = false
  }
}

// Format date
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

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.section-title {
  font-size: 1.25rem;
  font-weight: 700;
  color: #1a1a1a;
  letter-spacing: -0.01em;
  margin-bottom: 0;
}

.link-manage {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  color: #5f0080;
  font-size: 0.875rem;
  font-weight: 600;
  text-decoration: none;
  transition: color 0.2s;
}

.link-manage:hover {
  color: #4c0066;
}

.link-manage svg {
  transition: transform 0.2s;
}

.link-manage:hover svg {
  transform: translateX(2px);
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

/* 기본 배송지 카드 */
.default-address-card {
  padding: 1.25rem;
  background: #fafafa;
  border-radius: 10px;
  border: 1px solid #e5e7eb;
}

.address-badge {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}

.badge-default {
  padding: 0.25rem 0.625rem;
  background: #5f0080;
  color: white;
  font-size: 0.75rem;
  font-weight: 600;
  border-radius: 4px;
}

.address-name {
  font-size: 0.9375rem;
  font-weight: 600;
  color: #1a1a1a;
}

.address-info {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.recipient {
  font-size: 0.875rem;
  color: #374151;
  font-weight: 500;
  margin: 0;
}

.address-text {
  font-size: 0.875rem;
  color: #6b7280;
  line-height: 1.5;
  margin: 0;
}

.no-address {
  padding: 2rem;
  text-align: center;
  background: #fafafa;
  border-radius: 10px;
  border: 1px dashed #d1d5db;
}

.no-address p {
  color: #6b7280;
  font-size: 0.9375rem;
  margin: 0 0 1rem 0;
}

.btn-add-address {
  display: inline-block;
  padding: 0.625rem 1.25rem;
  background: #5f0080;
  color: white;
  font-size: 0.875rem;
  font-weight: 600;
  text-decoration: none;
  border-radius: 6px;
  transition: all 0.2s;
}

.btn-add-address:hover {
  background: #4c0066;
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

.badge-admin {
  background: linear-gradient(135deg, #0ea5e9 0%, #2563eb 100%);
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

  .section-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
  }

  .info-card {
    padding: 1.25rem;
  }
}

/* 계정 삭제 모달 */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 1rem;
}

.modal-content {
  background: white;
  border-radius: 16px;
  max-width: 480px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
}

.delete-modal {
  padding: 2rem;
}

.modal-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: #dc2626;
  margin-bottom: 1.5rem;
  text-align: center;
}

.modal-loading {
  text-align: center;
  padding: 2rem 0;
}

.modal-loading .spinner {
  width: 48px;
  height: 48px;
  border-width: 4px;
  border-top-color: #dc2626;
}

.modal-loading p {
  margin-top: 1rem;
  color: #666;
}

/* 삭제 불가 안내 */
.delete-blockers {
  padding: 1rem 0;
}

.blocker-title {
  font-weight: 600;
  color: #374151;
  margin-bottom: 1rem;
}

.blocker-list {
  list-style: disc;
  padding-left: 1.5rem;
  margin-bottom: 1.5rem;
}

.blocker-list li {
  color: #dc2626;
  margin-bottom: 0.5rem;
  line-height: 1.5;
}

/* 삭제 폼 */
.delete-form {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.warning-box {
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 8px;
  padding: 1rem 1.25rem;
}

.warning-box p {
  margin: 0;
  font-size: 0.875rem;
  line-height: 1.6;
  color: #991b1b;
}

.warning-box ul {
  margin: 0.75rem 0;
  padding-left: 1.5rem;
}

.warning-box li {
  font-size: 0.875rem;
  color: #991b1b;
  margin-bottom: 0.25rem;
}

.preserve-note {
  font-size: 0.8125rem !important;
  color: #6b7280 !important;
  margin-top: 0.75rem !important;
}

.delete-form .form-group {
  margin-bottom: 0;
}

.delete-form .form-group label {
  font-size: 0.875rem;
  font-weight: 600;
  color: #374151;
  margin-bottom: 0.5rem;
  display: block;
}

.delete-form .form-group input,
.delete-form .form-group textarea {
  width: 100%;
  padding: 0.75rem 1rem;
  border: 1.5px solid #e5e7eb;
  border-radius: 8px;
  font-size: 0.9375rem;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.delete-form .form-group input:focus,
.delete-form .form-group textarea:focus {
  outline: none;
  border-color: #dc2626;
  box-shadow: 0 0 0 3px rgba(220, 38, 38, 0.1);
}

.delete-form .form-group textarea {
  resize: vertical;
  min-height: 80px;
}

.delete-form .field-hint {
  font-size: 0.8125rem;
  color: #6b7280;
  margin-bottom: 0.5rem;
}

.delete-form .field-hint strong {
  color: #dc2626;
}

/* 모달 액션 버튼 */
.modal-actions {
  display: flex;
  gap: 0.75rem;
  margin-top: 0.5rem;
}

.btn-modal-delete,
.btn-modal-cancel {
  flex: 1;
  padding: 0.875rem 1.5rem;
  border: none;
  border-radius: 8px;
  font-size: 0.9375rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-modal-delete {
  background: #dc2626;
  color: white;
}

.btn-modal-delete:hover:not(:disabled) {
  background: #b91c1c;
}

.btn-modal-delete:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-modal-cancel {
  background: #f3f4f6;
  color: #374151;
  border: 1px solid #e5e7eb;
}

.btn-modal-cancel:hover:not(:disabled) {
  background: #e5e7eb;
}

.btn-modal-cancel:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 모달 내 에러 메시지 */
.delete-form .error-message {
  margin: 0;
}

@media (max-width: 480px) {
  .modal-content {
    max-height: 95vh;
  }

  .delete-modal {
    padding: 1.5rem;
  }

  .modal-actions {
    flex-direction: column;
  }
}
</style>
