<template>
  <div class="addresses-page">
    <!-- 헤더 -->
    <div class="page-header">
      <h2 class="section-title">배송지 관리</h2>
      <button class="btn-add" @click="openAddModal">
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
        </svg>
        새 배송지 추가
      </button>
    </div>

    <!-- 로딩 상태 -->
    <div v-if="addressesStore.loading" class="loading-state">
      <div class="spinner"></div>
      <p>배송지 정보를 불러오는 중...</p>
    </div>

    <!-- 에러 상태 -->
    <div v-else-if="addressesStore.error" class="error-state">
      <p>{{ addressesStore.error }}</p>
      <button class="btn-retry" @click="addressesStore.loadAddresses">다시 시도</button>
    </div>

    <!-- 빈 상태 -->
    <div v-else-if="!addressesStore.hasAddresses" class="empty-state">
      <div class="empty-icon">
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M15 10.5a3 3 0 11-6 0 3 3 0 016 0z" />
          <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1115 0z" />
        </svg>
      </div>
      <h3>등록된 배송지가 없습니다</h3>
      <p>새 배송지를 추가해주세요.</p>
      <button class="btn-primary" @click="openAddModal">배송지 추가하기</button>
    </div>

    <!-- 배송지 목록 -->
    <div v-else class="addresses-list">
      <div
        v-for="address in addressesStore.addresses"
        :key="address.id"
        class="address-card"
        :class="{ 'is-default': address.is_default }"
      >
        <div class="address-header">
          <div class="address-name">
            <span class="name">{{ address.address_name }}</span>
            <span v-if="address.is_default" class="default-badge">기본 배송지</span>
          </div>
          <div class="address-actions">
            <button class="btn-icon" @click="openEditModal(address)" title="수정">
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0115.75 21H5.25A2.25 2.25 0 013 18.75V8.25A2.25 2.25 0 015.25 6H10" />
              </svg>
            </button>
            <button class="btn-icon btn-delete" @click="confirmDelete(address)" title="삭제">
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
              </svg>
            </button>
          </div>
        </div>
        <div class="address-body">
          <p class="recipient">
            <strong>{{ address.recipient_name }}</strong>
            <span class="phone">{{ address.recipient_phone }}</span>
          </p>
          <p class="address-text">
            [{{ address.postal_code }}] {{ address.address_line1 }}
            <span v-if="address.address_line2">, {{ address.address_line2 }}</span>
          </p>
        </div>
        <div v-if="!address.is_default" class="address-footer">
          <button class="btn-set-default" @click="setDefault(address.id)">
            기본 배송지로 설정
          </button>
        </div>
      </div>
    </div>

    <!-- 배송지 추가/수정 모달 -->
    <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal-content">
        <div class="modal-header">
          <h3>{{ isEditMode ? '배송지 수정' : '새 배송지 추가' }}</h3>
          <button class="btn-close" @click="closeModal">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <form @submit.prevent="submitForm" class="modal-body">
          <div class="form-group">
            <label for="address_name">배송지 이름 <span class="required">*</span></label>
            <input
              id="address_name"
              v-model="formData.address_name"
              type="text"
              placeholder="예: 집, 회사"
              required
            />
          </div>
          <div class="form-row">
            <div class="form-group">
              <label for="recipient_name">수령인 <span class="required">*</span></label>
              <input
                id="recipient_name"
                v-model="formData.recipient_name"
                type="text"
                placeholder="수령인 이름"
                required
              />
            </div>
            <div class="form-group">
              <label for="recipient_phone">연락처 <span class="required">*</span></label>
              <input
                id="recipient_phone"
                v-model="formData.recipient_phone"
                type="tel"
                placeholder="01012345678"
                required
              />
            </div>
          </div>
          <div class="form-group">
            <label for="postal_code">우편번호 <span class="required">*</span></label>
            <div class="postal-input">
              <input
                id="postal_code"
                v-model="formData.postal_code"
                type="text"
                placeholder="우편번호"
                required
                readonly
              />
              <button type="button" class="btn-search-address" @click="searchAddress">
                주소 검색
              </button>
            </div>
          </div>
          <div class="form-group">
            <label for="address_line1">기본 주소 <span class="required">*</span></label>
            <input
              id="address_line1"
              v-model="formData.address_line1"
              type="text"
              placeholder="기본 주소"
              required
              readonly
            />
          </div>
          <div class="form-group">
            <label for="address_line2">상세 주소</label>
            <input
              id="address_line2"
              v-model="formData.address_line2"
              type="text"
              placeholder="상세 주소 (동/호수 등)"
            />
          </div>
          <div class="form-group">
            <label for="delivery_memo">배송 요청사항</label>
            <select
              id="delivery_memo"
              v-model="formData.delivery_memo"
              class="memo-select"
            >
              <option value="">선택 안함</option>
              <option value="문 앞에 놓아주세요">문 앞에 놓아주세요</option>
              <option value="경비실에 맡겨주세요">경비실에 맡겨주세요</option>
              <option value="택배함에 넣어주세요">택배함에 넣어주세요</option>
              <option value="배송 전 연락 부탁드립니다">배송 전 연락 부탁드립니다</option>
              <option value="부재 시 연락 부탁드립니다">부재 시 연락 부탁드립니다</option>
              <option value="직접 입력">직접 입력</option>
            </select>
            <input
              v-if="formData.delivery_memo === '직접 입력'"
              v-model="customMemo"
              type="text"
              placeholder="배송 요청사항을 입력하세요"
              class="custom-memo-input"
              maxlength="100"
            />
          </div>
          <div class="form-group checkbox-group">
            <label class="checkbox-label">
              <input
                v-model="formData.is_default"
                type="checkbox"
              />
              <span>기본 배송지로 설정</span>
            </label>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn-cancel" @click="closeModal">취소</button>
            <button type="submit" class="btn-submit" :disabled="submitting">
              {{ submitting ? '저장 중...' : (isEditMode ? '수정하기' : '추가하기') }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- 삭제 확인 모달 -->
    <div v-if="showDeleteConfirm" class="modal-overlay" @click.self="closeDeleteConfirm">
      <div class="modal-content modal-confirm">
        <div class="modal-header">
          <h3>배송지 삭제</h3>
        </div>
        <div class="modal-body">
          <p>
            <strong>{{ deleteTarget?.address_name }}</strong> 배송지를 삭제하시겠습니까?
          </p>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn-cancel" @click="closeDeleteConfirm">취소</button>
          <button type="button" class="btn-delete-confirm" @click="deleteAddress" :disabled="submitting">
            {{ submitting ? '삭제 중...' : '삭제' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useAddressesStore } from '@/stores/addresses'
import { useAuthStore } from '@/stores/auth'
import type { UserAddress, UserAddressRequest } from '@/types/auth'

const addressesStore = useAddressesStore()
const authStore = useAuthStore()

// 모달 상태
const showModal = ref(false)
const isEditMode = ref(false)
const editingId = ref<number | null>(null)
const submitting = ref(false)

// 삭제 확인 모달
const showDeleteConfirm = ref(false)
const deleteTarget = ref<UserAddress | null>(null)

// 폼 데이터
const initialFormData: UserAddressRequest = {
  address_name: '',
  recipient_name: '',
  recipient_phone: '',
  postal_code: '',
  address_line1: '',
  address_line2: '',
  delivery_memo: '',
  is_default: false
}

const formData = reactive<UserAddressRequest>({ ...initialFormData })
const customMemo = ref('')  // 직접 입력 시 사용

// 모달 열기 (추가) - 프로필 정보로 수령인/연락처 기본값 설정
const openAddModal = () => {
  isEditMode.value = false
  editingId.value = null
  customMemo.value = ''
  Object.assign(formData, {
    ...initialFormData,
    // 프로필에 이름이 있으면 수령인 기본값으로 설정
    recipient_name: authStore.user?.name || authStore.user?.username || '',
    // 프로필에 연락처가 있으면 기본값으로 설정
    recipient_phone: authStore.user?.phone || ''
  })
  showModal.value = true
}

// 모달 열기 (수정)
const openEditModal = (address: UserAddress) => {
  isEditMode.value = true
  editingId.value = address.id
  formData.address_name = address.address_name
  formData.recipient_name = address.recipient_name
  formData.recipient_phone = address.recipient_phone
  formData.postal_code = address.postal_code
  formData.address_line1 = address.address_line1
  formData.address_line2 = address.address_line2 || ''
  formData.is_default = address.is_default

  // 배송 요청사항 처리
  const memoOptions = ['문 앞에 놓아주세요', '경비실에 맡겨주세요', '택배함에 넣어주세요', '배송 전 연락 부탁드립니다', '부재 시 연락 부탁드립니다']
  if (address.delivery_memo && !memoOptions.includes(address.delivery_memo)) {
    formData.delivery_memo = '직접 입력'
    customMemo.value = address.delivery_memo
  } else {
    formData.delivery_memo = address.delivery_memo || ''
    customMemo.value = ''
  }

  showModal.value = true
}

// 모달 닫기
const closeModal = () => {
  showModal.value = false
  isEditMode.value = false
  editingId.value = null
}

// 삭제 확인 모달
const confirmDelete = (address: UserAddress) => {
  deleteTarget.value = address
  showDeleteConfirm.value = true
}

const closeDeleteConfirm = () => {
  showDeleteConfirm.value = false
  deleteTarget.value = null
}

// 주소 검색 (다음 우편번호 API)
const searchAddress = () => {
  // @ts-ignore - 다음 우편번호 API
  if (window.daum && window.daum.Postcode) {
    // @ts-ignore
    new window.daum.Postcode({
      oncomplete: (data: any) => {
        formData.postal_code = data.zonecode
        formData.address_line1 = data.roadAddress || data.jibunAddress
      }
    }).open()
  } else {
    alert('주소 검색 서비스를 불러오는 중입니다. 잠시 후 다시 시도해주세요.')
  }
}

// 폼 제출
const submitForm = async () => {
  if (submitting.value) return

  submitting.value = true
  try {
    // 직접 입력인 경우 customMemo 사용
    const submitData = {
      ...formData,
      delivery_memo: formData.delivery_memo === '직접 입력' ? customMemo.value : formData.delivery_memo
    }

    if (isEditMode.value && editingId.value) {
      await addressesStore.updateAddress(editingId.value, submitData)
    } else {
      await addressesStore.addAddress(submitData)
    }
    closeModal()
  } catch (error) {
    console.error('배송지 저장 실패:', error)
  } finally {
    submitting.value = false
  }
}

// 배송지 삭제
const deleteAddress = async () => {
  if (!deleteTarget.value || submitting.value) return

  submitting.value = true
  try {
    await addressesStore.deleteAddress(deleteTarget.value.id)
    closeDeleteConfirm()
  } catch (error) {
    console.error('배송지 삭제 실패:', error)
  } finally {
    submitting.value = false
  }
}

// 기본 배송지 설정
const setDefault = async (id: number) => {
  try {
    await addressesStore.setDefaultAddress(id)
  } catch (error) {
    console.error('기본 배송지 설정 실패:', error)
  }
}

// 초기 로드
onMounted(() => {
  addressesStore.loadAddresses()
})
</script>

<style scoped>
.addresses-page {
  max-width: 800px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
}

.section-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: #1a1a1a;
}

.btn-add {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.25rem;
  background: #5f0080;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-add:hover {
  background: #4a0066;
}

.btn-add svg {
  width: 18px;
  height: 18px;
}

/* 상태 표시 */
.loading-state,
.error-state,
.empty-state {
  text-align: center;
  padding: 4rem 2rem;
  color: #666;
}

.spinner {
  width: 40px;
  height: 40px;
  margin: 0 auto 1rem;
  border: 3px solid #f0f0f0;
  border-top-color: #5f0080;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.empty-icon {
  width: 80px;
  height: 80px;
  margin: 0 auto 1.5rem;
  background: #f5f5f5;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.empty-icon svg {
  width: 40px;
  height: 40px;
  color: #999;
}

.empty-state h3 {
  font-size: 1.125rem;
  color: #333;
  margin-bottom: 0.5rem;
}

.empty-state p {
  margin-bottom: 1.5rem;
}

.btn-primary,
.btn-retry {
  padding: 0.75rem 1.5rem;
  background: #5f0080;
  color: white;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
}

/* 배송지 목록 */
.addresses-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.address-card {
  background: #fff;
  border: 1px solid #e5e5e5;
  border-radius: 12px;
  padding: 1.5rem;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.address-card:hover {
  border-color: #5f0080;
}

.address-card.is-default {
  border-color: #5f0080;
  background: linear-gradient(to right, rgba(95, 0, 128, 0.02), transparent);
}

.address-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.address-name {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.address-name .name {
  font-size: 1.125rem;
  font-weight: 700;
  color: #1a1a1a;
}

.default-badge {
  padding: 0.25rem 0.625rem;
  background: #5f0080;
  color: white;
  font-size: 0.75rem;
  font-weight: 600;
  border-radius: 4px;
}

.address-actions {
  display: flex;
  gap: 0.5rem;
}

.btn-icon {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f5f5;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-icon svg {
  width: 18px;
  height: 18px;
  color: #666;
}

.btn-icon:hover {
  background: #e5e5e5;
}

.btn-icon.btn-delete:hover {
  background: #fee2e2;
}

.btn-icon.btn-delete:hover svg {
  color: #dc2626;
}

.address-body {
  color: #666;
}

.recipient {
  margin-bottom: 0.5rem;
}

.recipient strong {
  color: #333;
  margin-right: 0.75rem;
}

.phone {
  color: #888;
}

.address-text {
  font-size: 0.9375rem;
  line-height: 1.5;
}

.address-footer {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #f0f0f0;
}

.btn-set-default {
  padding: 0.5rem 1rem;
  background: transparent;
  color: #5f0080;
  border: 1px solid #5f0080;
  border-radius: 6px;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s, color 0.2s;
}

.btn-set-default:hover {
  background: #5f0080;
  color: white;
}

/* 모달 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
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
  width: 100%;
  max-width: 520px;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-confirm {
  max-width: 400px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  border-bottom: 1px solid #f0f0f0;
}

.modal-header h3 {
  font-size: 1.25rem;
  font-weight: 700;
  color: #1a1a1a;
}

.btn-close {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  border-radius: 8px;
  cursor: pointer;
}

.btn-close svg {
  width: 20px;
  height: 20px;
  color: #666;
}

.btn-close:hover {
  background: #f5f5f5;
}

.modal-body {
  padding: 1.5rem;
}

.form-group {
  margin-bottom: 1.25rem;
}

.form-group label {
  display: block;
  font-size: 0.875rem;
  font-weight: 600;
  color: #333;
  margin-bottom: 0.5rem;
}

.required {
  color: #dc2626;
}

.form-group input[type="text"],
.form-group input[type="tel"] {
  width: 100%;
  padding: 0.75rem 1rem;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  font-size: 0.9375rem;
  transition: border-color 0.2s;
}

.form-group input:focus {
  outline: none;
  border-color: #5f0080;
}

.form-group input[readonly] {
  background: #f9f9f9;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.postal-input {
  display: flex;
  gap: 0.5rem;
}

.postal-input input {
  flex: 1;
}

.btn-search-address {
  padding: 0 1rem;
  background: #333;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
}

.btn-search-address:hover {
  background: #1a1a1a;
}

.memo-select {
  width: 100%;
  padding: 0.75rem 1rem;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  font-size: 0.9375rem;
  background: white;
  cursor: pointer;
  transition: border-color 0.2s;
}

.memo-select:focus {
  outline: none;
  border-color: #5f0080;
}

.custom-memo-input {
  margin-top: 0.5rem;
  width: 100%;
  padding: 0.75rem 1rem;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  font-size: 0.9375rem;
}

.custom-memo-input:focus {
  outline: none;
  border-color: #5f0080;
}

.checkbox-group {
  margin-top: 1rem;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
}

.checkbox-label input {
  width: 18px;
  height: 18px;
  accent-color: #5f0080;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  padding: 1.5rem;
  border-top: 1px solid #f0f0f0;
}

.btn-cancel {
  padding: 0.75rem 1.5rem;
  background: #f5f5f5;
  color: #666;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
}

.btn-cancel:hover {
  background: #e5e5e5;
}

.btn-submit {
  padding: 0.75rem 1.5rem;
  background: #5f0080;
  color: white;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
}

.btn-submit:hover:not(:disabled) {
  background: #4a0066;
}

.btn-submit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-delete-confirm {
  padding: 0.75rem 1.5rem;
  background: #dc2626;
  color: white;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
}

.btn-delete-confirm:hover:not(:disabled) {
  background: #b91c1c;
}

/* 반응형 */
@media (max-width: 640px) {
  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 1rem;
  }

  .btn-add {
    width: 100%;
    justify-content: center;
  }

  .form-row {
    grid-template-columns: 1fr;
  }

  .address-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.75rem;
  }

  .address-actions {
    align-self: flex-end;
  }
}
</style>
