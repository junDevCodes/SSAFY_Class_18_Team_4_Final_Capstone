<template>
  <section class="reviews">
    <div class="reviews-head">
      <div class="score">{{ displayAverage }}</div>
      <div class="stars" aria-label="평균 별점">
        <span v-for="n in 5" :key="n" class="star" :class="{ filled: n <= averageStars }">★</span>
      </div>
      <div class="count">리뷰 {{ stats.count }}개</div>
    </div>

    <div class="list-wrap">
      <div v-if="ui.isLoadingList" class="muted">불러오는 중...</div>
      <div v-else-if="ui.listError" class="error-row">
        <span>{{ ui.listError }}</span>
        <button class="ghost" @click="loadReviews(1)">다시 시도</button>
      </div>
      <div v-else-if="!reviews.length" class="muted">아직 리뷰가 없습니다.</div>

      <article v-for="review in reviews" :key="review.id" class="review-card">
        <header class="review-header">
          <div class="rating-block">
            <div class="stars-line">
              <span v-for="n in 5" :key="n" class="star" :class="{ filled: n <= review.rating }">★</span>
              <span class="rating-num">{{ review.rating }}</span>
              <span class="rating-label">{{ getRatingLabel(review.rating) }}</span>
            </div>
            <div class="user-row">
              <div class="avatar">{{ getInitial(review) }}</div>
              <div class="user-meta">
                <span class="name">
                  {{ getDisplayName(review) }}
                  <small v-if="isMine(review)" class="me-tag">나</small>
                </span>
              </div>
            </div>
          </div>
          <div class="meta-block">
            <span class="date">{{ formatDateTime(review.created_at) }}</span>
            <button type="button" class="link-report">신고하기</button>
            <template v-if="isMine(review)">
              <button
                type="button"
                class="link-action"
                @click="startEdit(review)"
                :disabled="ui.isUpdatingId === review.id"
              >
                수정
              </button>
              <button
                type="button"
                class="link-action danger"
                @click="confirmDelete(review)"
                :disabled="ui.isDeletingId === review.id"
              >
                {{ ui.isDeletingId === review.id ? '삭제 중...' : '삭제' }}
              </button>
            </template>
          </div>
        </header>

        <div v-if="editState?.id === review.id" class="edit-area">
          <div class="rating-input stars-input">
            <button
              v-for="n in 5"
              :key="n"
              type="button"
              :class="['rate-btn', { active: n <= editState.rating }]"
              @click="editState.rating = n"
            >
              <span class="star" :class="{ filled: n <= editState.rating }">★</span>
            </button>
          </div>
          <textarea v-model="editState.content" rows="3" />
          <div class="edit-upload">
            <label class="sub-label">이미지 첨부 (최대 5개)</label>
            <div class="upload-box">
              <input
                class="file-input"
                type="file"
                accept="image/jpeg,image/png,image/gif,image/webp"
                multiple
                @change="handleEditFileChange"
              />
              <div class="upload-copy">
                <strong>클릭하거나 파일을 선택해 업로드</strong>
                <span>JPEG/PNG/GIF/WebP, 5MB 이하</span>
              </div>
            </div>
            <div v-if="editState.existingUrls.length || editState.files.length" class="preview-grid">
              <div
                v-for="(url, idx) in editState.existingUrls"
                :key="`existing-${idx}`"
                class="preview-card"
              >
                <img :src="url" alt="review image" />
                <div class="preview-meta">
                  <span class="filename">기존 이미지</span>
                  <button type="button" class="remove-btn" @click="removeExistingUrl(idx)">삭제</button>
                </div>
              </div>
              <div
                v-for="(item, idx) in editState.files"
                :key="item.preview"
                class="preview-card"
              >
                <img :src="item.preview" :alt="item.file.name" />
                <div class="preview-meta">
                  <span class="filename" :title="item.file.name">{{ item.file.name }}</span>
                  <button type="button" class="remove-btn" @click="removeEditFile(idx)">삭제</button>
                </div>
              </div>
            </div>
          </div>
          <div class="actions">
            <button
              type="button"
              :disabled="ui.isUpdatingId === review.id"
              @click="handleUpdate(review.id)"
            >
              {{ ui.isUpdatingId === review.id ? '저장 중...' : '저장' }}
            </button>
            <button type="button" class="ghost" @click="cancelEdit">취소</button>
          </div>
        </div>
        <div v-else class="body">
          <div v-if="review.images?.length" class="thumbs large">
            <img v-for="img in review.images" :key="img.id" :src="img.image_url" alt="review" />
          </div>
          <p class="text">{{ review.content }}</p>
        </div>

      </article>

      <div v-if="paging.hasNext && !ui.isLoadingList" class="load-more">
        <button @click="loadReviews(paging.page + 1)" :disabled="ui.isLoadingList">더보기</button>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { reviewApi, type Review } from '@/services/api/reviews'
import { useAuthStore } from '@/stores/auth'
import { useUIStore } from '@/stores/ui'

const props = defineProps<{
  productId: number
  orderItemId?: number | null
  initialAverage?: number | null
  initialCount?: number | null
  initialEditReviewId?: number | null
}>()

const authStore = useAuthStore()
const uiStore = useUIStore()

const reviews = ref<Review[]>([])
const paging = reactive({ page: 1, pageSize: 6, hasNext: false })
const stats = reactive({
  average: props.initialAverage ?? 0,
  count: props.initialCount ?? 0,
})

const ui = reactive({
  isLoadingList: false,
  listError: '',
  isUpdatingId: 0,
  isDeletingId: 0,
})

type UploadItem = { file: File; preview: string }

const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
const MAX_SIZE = 5 * 1024 * 1024
const MAX_IMAGES = 5

const editState = ref<{
  id: number
  rating: number
  content: string
  existingUrls: string[]
  files: UploadItem[]
} | null>(null)

const initialEditApplied = ref(false)

const averageStars = computed(() => {
  const val = Number(stats.average ?? 0)
  const clamped = Math.max(0, Math.min(5, Math.round(val)))
  return clamped
})

const displayAverage = computed(() => {
  const value = Number(stats.average || 0)
  return Number.isFinite(value) ? value.toFixed(1) : '0.0'
})

const formatDateTime = (value: string) => {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('ko-KR', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const getRatingLabel = (rating: number) => {
  const labels: Record<number, string> = {
    5: '아주 좋아요!',
    4: '좋아요',
    3: '보통이에요',
    2: '별로예요',
    1: '추천하지 않아요',
  }
  return labels[rating] || ''
}

const getDisplayName = (review: Review) => {
  const raw = (review.user_name || '').trim()
  if (raw) return raw
  if (review.user) return `User #${review.user}`
  return 'User'
}

const getInitial = (review: Review) => {
  const name = getDisplayName(review)
  const first = Array.from(name)[0]
  return first ? first.toUpperCase() : 'U'
}

const isMine = (review: Review) => {
  const me = authStore.user
  if (!me) return false

  const sameId = review.user && me.id && review.user === me.id
  const sameOrderItem = props.orderItemId && review.order_item === props.orderItemId

  // 백엔드에서 사용자 id가 안 내려오는 경우 주문 아이템 id로 보조 판별
  return Boolean(sameId || sameOrderItem)
}

const updateAverageOnReplace = (prevRating: number, nextRating: number) => {
  const total = stats.average * stats.count - prevRating + nextRating
  stats.average = stats.count ? total / stats.count : 0
}

const updateAverageOnDelete = (rating: number) => {
  if (stats.count <= 1) {
    stats.count = 0
    stats.average = 0
    return
  }
  const total = stats.average * stats.count - rating
  stats.count -= 1
  stats.average = total / stats.count
}

const loadReviews = async (page = 1) => {
  ui.isLoadingList = true
  ui.listError = ''
  try {
    const data = await reviewApi.getProductReviews(props.productId, {
      page,
      page_size: paging.pageSize,
      ordering: '-created_at',
    })
    if (page === 1) {
      reviews.value = data.results
      stats.count = data.count
      if (props.initialAverage === undefined || props.initialAverage === null) {
        const avg = data.results.length
          ? data.results.reduce((sum, r) => sum + r.rating, 0) / data.results.length
          : 0
        stats.average = avg
      }
    } else {
      reviews.value = [...reviews.value, ...data.results]
    }
    paging.page = page
    paging.hasNext = Boolean(data.next)
    applyInitialEdit()
  } catch (error: any) {
    ui.listError = error?.response?.data?.detail || 'Failed to load reviews.'
  } finally {
    ui.isLoadingList = false
  }
}

const applyInitialEdit = () => {
  if (initialEditApplied.value) return
  const targetId = props.initialEditReviewId
  if (!targetId) return
  const target = reviews.value.find((r) => r.id === targetId)
  if (!target) return
  startEdit(target)
  initialEditApplied.value = true
}

const handleReviewCreated = (e: CustomEvent<{ productId?: number }>) => {
  if (!e.detail?.productId || e.detail.productId !== props.productId) return
  loadReviews(1)
}

const startEdit = (review: Review) => {
  editState.value = {
    id: review.id,
    rating: review.rating,
    content: review.content,
    existingUrls: review.images?.map((img) => img.image_url) || [],
    files: [],
  }
}

const cancelEdit = () => {
  clearEditFiles()
  editState.value = null
}

const handleUpdate = async (reviewId: number) => {
  if (!editState.value) return
  const current = reviews.value.find((r) => r.id === reviewId)
  if (!current) return
  ui.isUpdatingId = reviewId
  try {
    const total = editState.value.existingUrls.length + editState.value.files.length
    if (total > MAX_IMAGES) {
      uiStore.showToast(`이미지는 최대 ${MAX_IMAGES}개까지 업로드할 수 있습니다.`)
      return
    }

    let uploadedUrls: string[] = []
    if (editState.value.files.length) {
      const res = await reviewApi.uploadReviewImages(editState.value.files.map((f) => f.file))
      uploadedUrls = res.image_urls || []
    }

    const payload = {
      rating: editState.value.rating,
      content: editState.value.content.trim(),
      image_urls: [...editState.value.existingUrls, ...uploadedUrls],
    }
    const updated = await reviewApi.updateReview(reviewId, payload)
    reviews.value = reviews.value.map((r) => (r.id === updated.id ? updated : r))
    if (updated.rating !== current.rating) {
      updateAverageOnReplace(current.rating, updated.rating)
    }
    clearEditFiles()
    editState.value = null
    uiStore.showToast('Review updated')
  } catch (error: any) {
    uiStore.showToast(error?.response?.data?.detail || 'Failed to update review')
  } finally {
    ui.isUpdatingId = 0
  }
}

const clearEditFiles = () => {
  if (!editState.value) return
  editState.value.files.forEach((item) => URL.revokeObjectURL(item.preview))
  editState.value.files = []
}

const handleEditFileChange = (event: Event) => {
  if (!editState.value) return
  const files = (event.target as HTMLInputElement)?.files
  if (!files) return
  const next = [...editState.value.files]
  for (const file of Array.from(files)) {
    const currentTotal = editState.value.existingUrls.length + next.length
    if (currentTotal >= MAX_IMAGES) {
      uiStore.showToast(`이미지는 최대 ${MAX_IMAGES}개까지 업로드할 수 있습니다.`)
      break
    }
    if (!ALLOWED_TYPES.includes(file.type)) {
      uiStore.showToast('JPEG, PNG, GIF, WebP 형식만 업로드할 수 있습니다.')
      continue
    }
    if (file.size > MAX_SIZE) {
      uiStore.showToast('이미지는 5MB 이하 파일만 업로드해 주세요.')
      continue
    }
    next.push({ file, preview: URL.createObjectURL(file) })
  }
  editState.value.files = next
  ;(event.target as HTMLInputElement).value = ''
}

const removeExistingUrl = (index: number) => {
  if (!editState.value) return
  editState.value.existingUrls.splice(index, 1)
}

const removeEditFile = (index: number) => {
  if (!editState.value) return
  const removed = editState.value.files.splice(index, 1)
  removed.forEach((item) => URL.revokeObjectURL(item.preview))
}

const confirmDelete = async (review: Review) => {
  const ok = window.confirm('Delete this review?')
  if (!ok) return
  ui.isDeletingId = review.id
  try {
    await reviewApi.deleteReview(review.id)
    reviews.value = reviews.value.filter((r) => r.id !== review.id)
    updateAverageOnDelete(review.rating)
    uiStore.showToast('Review deleted')
  } catch (error: any) {
    uiStore.showToast(error?.response?.data?.detail || 'Failed to delete review')
  } finally {
    ui.isDeletingId = 0
  }
}

onMounted(() => {
  loadReviews(1)
  window.addEventListener('review:created', handleReviewCreated as EventListener)
})

onBeforeUnmount(() => {
  window.removeEventListener('review:created', handleReviewCreated as EventListener)
  clearEditFiles()
})

watch(
  () => props.initialEditReviewId,
  () => {
    initialEditApplied.value = false
    applyInitialEdit()
  }
)

defineExpose({
  loadReviews,
})
</script>

<style scoped>
.reviews { margin-top: 32px; display: flex; flex-direction: column; gap: 16px; }
.reviews-head { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
.score { font-size: 28px; font-weight: 800; color: #0f3a2a; }
.count { color: #374151; font-weight: 600; }
.stars { display: flex; gap: 2px; align-items: center; }
.star { color: #d1d5db; font-size: 16px; line-height: 1; }
.star.filled { color: #f59e0b; }
.badge.stars { gap: 4px; }
.rating-num { margin-left: 4px; font-weight: 700; color: #111827; }
.muted { color: #6b7280; font-size: 14px; }
.error { color: #b91c1c; font-size: 14px; }
.rating-input { display: flex; gap: 6px; flex-wrap: wrap; }
.stars-input .rate-btn { border: 1px solid #d1d5db; background: #fff; width: 44px; height: 44px; display: grid; place-items: center; border-radius: 8px; cursor: pointer; }
.stars-input .rate-btn .star { font-size: 18px; color: #d1d5db; }
.stars-input .rate-btn.active { border-color: #0f3a2a; background: #e8f5ee; }
.stars-input .rate-btn.active .star { color: #f59e0b; }
.actions { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.actions button { padding: 10px 14px; border-radius: 8px; border: none; background: #0f3a2a; color: #fff; cursor: pointer; }
.actions button:disabled { opacity: 0.6; cursor: not-allowed; }
.actions .error { margin-left: 4px; }
.ghost { border: 1px solid #d1d5db; background: #fff; color: #111827; padding: 8px 12px; border-radius: 8px; cursor: pointer; }
.danger { border: 1px solid #b91c1c; background: #b91c1c; color: #fff; padding: 8px 12px; border-radius: 8px; cursor: pointer; }
.list-wrap { display: flex; flex-direction: column; gap: 12px; }
.review-card { border: 1px solid #e5e7eb; border-radius: 10px; padding: 14px; background: #fff; display: flex; flex-direction: column; gap: 10px; }
.review-header { display: flex; justify-content: space-between; gap: 12px; align-items: flex-start; }
.user { display: flex; gap: 10px; align-items: center; }
.avatar { width: 36px; height: 36px; border-radius: 50%; background: #e5e7eb; display: grid; place-items: center; font-weight: 700; color: #111827; }
.user-meta { display: flex; flex-direction: column; }
.name { font-weight: 700; color: #111827; }
.me-tag { margin-left: 6px; padding: 2px 6px; border-radius: 999px; background: #e5f3ff; color: #0b5ed7; font-size: 11px; font-weight: 700; }
.date { color: #6b7280; font-size: 12px; }
.badge { padding: 6px 10px; border-radius: 8px; background: #e8f5ee; color: #0f3a2a; font-weight: 700; }
.header-right { display: flex; flex-direction: column; gap: 6px; align-items: flex-end; }
.actions-inline { display: flex; gap: 6px; }
.actions-inline .ghost, .actions-inline .danger { padding: 6px 10px; border-radius: 8px; cursor: pointer; }
.actions-inline .ghost { border: 1px solid #d1d5db; background: #fff; color: #111827; }
.actions-inline .danger { border: 1px solid #b91c1c; background: #b91c1c; color: #fff; }
.actions-inline .ghost:disabled,
.actions-inline .danger:disabled { opacity: 0.6; cursor: not-allowed; }
.body { display: flex; flex-direction: column; gap: 8px; }
.text { color: #111827; font-size: 14px; line-height: 1.5; }
.thumbs { display: flex; gap: 10px; flex-wrap: wrap; }
.thumbs.large img { width: 120px; height: 120px; }
.thumbs img { width: 64px; height: 64px; object-fit: cover; border-radius: 8px; border: 1px solid #e5e7eb; }
.actions-row { display: flex; gap: 8px; }
.load-more { display: flex; justify-content: center; }
.error-row { display: flex; gap: 10px; align-items: center; }
.edit-area { display: flex; flex-direction: column; gap: 10px; }
.edit-upload { display: flex; flex-direction: column; gap: 8px; }
.sub-label { font-size: 12px; color: #374151; font-weight: 700; }
.upload-box { position: relative; padding: 12px; border: 1px dashed #d1d5db; border-radius: 10px; background: #f9fafb; cursor: pointer; transition: border-color 0.2s, background 0.2s; }
.upload-box:hover { border-color: #0f3a2a; background: #f4faf6; }
.file-input { position: absolute; inset: 0; opacity: 0; cursor: pointer; }
.upload-copy { display: flex; flex-direction: column; gap: 4px; color: #4b5563; text-align: center; }
.upload-copy strong { color: #111827; }
.preview-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 10px; margin-top: 6px; }
.preview-card { border: 1px solid #e5e7eb; border-radius: 8px; overflow: hidden; background: #fff; }
.preview-card img { width: 100%; height: 120px; object-fit: cover; }
.preview-meta { display: flex; justify-content: space-between; align-items: center; gap: 6px; padding: 6px 8px; }
.filename { flex: 1; font-size: 12px; color: #374151; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.remove-btn { border: none; background: #f3f4f6; color: #111827; padding: 6px 10px; border-radius: 6px; cursor: pointer; font-size: 12px; }
.remove-btn:hover { background: #e5e7eb; }
.rating-block { display: flex; flex-direction: column; gap: 8px; }
.stars-line { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.rating-label { color: #4b5563; font-weight: 600; }
.user-row { display: flex; align-items: center; gap: 8px; }
.meta-block { display: flex; align-items: center; gap: 10px; color: #6b7280; }
.link-report { border: none; background: none; color: #2563eb; cursor: pointer; font-size: 13px; padding: 0; }
.link-report:hover { text-decoration: underline; }
.link-action { border: none; background: none; padding: 0; font-size: 13px; color: #9ca3af; cursor: pointer; }
.link-action:hover { color: #6b7280; text-decoration: underline; }
.link-action.danger { color: #f87171; }
.link-action:disabled { color: #d1d5db; cursor: not-allowed; text-decoration: none; }
.thumbs.large { margin-top: 4px; }
</style>

