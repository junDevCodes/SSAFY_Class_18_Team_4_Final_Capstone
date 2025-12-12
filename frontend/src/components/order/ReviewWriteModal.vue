<template>
  <div v-if="open" class="modal-backdrop">
    <div class="modal">
      <header class="modal-header">
        <h3>리뷰 작성</h3>
        <button class="close" type="button" @click="$emit('close')">×</button>
      </header>
      <div class="modal-body">
        <p class="muted">{{ productName }}</p>
        <div class="field">
          <label>별점</label>
          <div class="rating">
            <button
              v-for="n in 5"
              :key="n"
              type="button"
              :class="['rate', { active: n <= form.rating }]"
              @click="form.rating = n"
              aria-label="별점 선택"
            >
              <span class="star">{{ n <= form.rating ? '★' : '☆' }}</span>
            </button>
          </div>
        </div>
        <div class="field">
          <label>내용</label>
          <textarea v-model="form.content" rows="4" placeholder="리뷰를 입력하세요" />
        </div>
        <div class="field">
          <label>이미지 URL (콤마구분, 선택)</label>
          <input v-model="form.imagesInput" type="text" placeholder="https://..., https://..." />
        </div>
        <p v-if="error" class="error">{{ error }}</p>
      </div>
      <footer class="modal-footer">
        <button class="ghost" type="button" @click="$emit('close')" :disabled="submitting">취소</button>
        <button class="primary" type="button" :disabled="!canSubmit || submitting" @click="handleSubmit">
          {{ submitting ? '작성 중...' : '작성하기' }}
        </button>
      </footer>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { reviewApi } from '@/services/api/reviews'

const props = defineProps<{
  open: boolean
  productId: number | null
  orderItemId: number | null
  productName?: string
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'submitted', payload?: { message?: string; alreadyReviewed?: boolean }): void
}>()

const form = reactive({
  rating: 0,
  content: '',
  imagesInput: '',
})

const submitting = ref(false)
const error = ref<string | null>(null)

const canSubmit = computed(() => {
  if (!props.productId || !props.orderItemId) return false
  if (form.rating < 1 || form.rating > 5) return false
  if (!form.content.trim()) return false
  return true
})

const parseImages = () =>
  form.imagesInput
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean)

const resetForm = () => {
  form.rating = 0
  form.content = ''
  form.imagesInput = ''
  error.value = null
}

watch(
  () => props.open,
  (val) => {
    if (!val) resetForm()
  }
)

const handleSubmit = async () => {
  if (!props.productId || !props.orderItemId) {
    error.value = '주문 정보가 부족해 리뷰를 작성할 수 없습니다.'
    return
  }
  if (!canSubmit.value) {
    error.value = '별점과 내용을 입력해 주세요.'
    return
  }
  submitting.value = true
  error.value = null
  try {
    await reviewApi.createReview({
      product: props.productId,
      order_item: props.orderItemId,
      rating: form.rating,
      content: form.content.trim(),
      image_urls: parseImages(),
    })
    if (props.productId) {
      window.dispatchEvent(
        new CustomEvent('review:created', { detail: { productId: props.productId } })
      )
    }
    emit('submitted')
    emit('close')
  } catch (e: any) {
    const detail =
      e?.response?.data?.detail ||
      e?.response?.data?.rating?.[0] ||
      e?.response?.data?.order_item?.[0] ||
      e?.response?.data?.product?.[0]
    const msg = detail || '리뷰 작성에 실패했습니다.'
    // 중복 리뷰인 경우에도 has_review를 반영해 버튼 비활성화/토스트 표시
    if (msg.includes('이미 이 상품에 리뷰를 작성하셨습니다')) {
      emit('submitted', { message: msg, alreadyReviewed: true })
      emit('close')
      return
    }
    error.value = msg
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.35);
  display: grid;
  place-items: center;
  z-index: 1000;
}
.modal {
  width: min(480px, 90vw);
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.12);
  overflow: hidden;
}
.modal-header,
.modal-footer {
  padding: 14px 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.modal-body {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.close {
  border: none;
  background: transparent;
  font-size: 18px;
  cursor: pointer;
}
.muted {
  color: #6b7280;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.field label {
  font-weight: 700;
  color: #111827;
}
.rating {
  display: flex;
  gap: 8px;
}
.rate {
  border: 1px solid #d1d5db;
  background: #fff;
  width: 44px;
  height: 44px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  cursor: pointer;
  font-size: 20px;
}
.rate.active {
  border-color: #0f3a2a;
  background: #e8f5ee;
  color: #0f3a2a;
  font-weight: 700;
}
.star {
  line-height: 1;
}
textarea,
input {
  border: 1px solid #d1d5db;
  border-radius: 8px;
  padding: 10px;
  font-size: 14px;
}
.modal-footer {
  gap: 10px;
}
.ghost,
.primary {
  padding: 10px 14px;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 700;
}
.ghost {
  border: 1px solid #d1d5db;
  background: #fff;
  color: #111827;
}
.primary {
  border: none;
  background: #0f3a2a;
  color: #fff;
}
.primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.error {
  color: #b91c1c;
  font-size: 14px;
}
</style>
