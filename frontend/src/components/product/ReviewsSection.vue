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
          <div class="user">
            <div class="avatar">
              {{ getInitial(review) }}
            </div>
            <div class="user-meta">
              <span class="name">
                {{ getDisplayName(review) }}
                <small v-if="isMine(review)" class="me-tag">나</small>
              </span>
              <span class="date">{{ formatDate(review.created_at) }}</span>
            </div>
          </div>
          <div class="header-right">
            <div class="badge stars">
              <span v-for="n in 5" :key="n" class="star" :class="{ filled: n <= review.rating }">★</span>
              <span class="rating-num">{{ review.rating }}</span>
            </div>
            <div v-if="isMine(review)" class="actions-below">
              <button class="ghost" @click="startEdit(review)" :disabled="ui.isUpdatingId === review.id">
                수정
              </button>
              <button
                class="danger"
                @click="confirmDelete(review)"
                :disabled="ui.isDeletingId === review.id"
              >
                {{ ui.isDeletingId === review.id ? '삭제 중...' : '삭제' }}
              </button>
            </div>
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
          <input
            v-model="editState.imagesInput"
            type="text"
            placeholder="https://... , https://..."
          />
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
          <p class="text">{{ review.content }}</p>
          <div v-if="review.images?.length" class="thumbs">
            <img v-for="img in review.images" :key="img.id" :src="img.image_url" alt="review" />
          </div>
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

const editState = ref<{
  id: number
  rating: number
  content: string
  imagesInput: string
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

const formatDate = (value: string) => {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleDateString()
}

const parseImagesInput = (input: string) =>
  input
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)

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
    imagesInput: review.images?.map((img) => img.image_url).join(', ') || '',
  }
}

const cancelEdit = () => {
  editState.value = null
}

const handleUpdate = async (reviewId: number) => {
  if (!editState.value) return
  const current = reviews.value.find((r) => r.id === reviewId)
  if (!current) return
  ui.isUpdatingId = reviewId
  try {
    const payload = {
      rating: editState.value.rating,
      content: editState.value.content.trim(),
      image_urls: parseImagesInput(editState.value.imagesInput),
    }
    const updated = await reviewApi.updateReview(reviewId, payload)
    reviews.value = reviews.value.map((r) => (r.id === updated.id ? updated : r))
    if (updated.rating !== current.rating) {
      updateAverageOnReplace(current.rating, updated.rating)
    }
    editState.value = null
    uiStore.showToast('Review updated')
  } catch (error: any) {
    uiStore.showToast(error?.response?.data?.detail || 'Failed to update review')
  } finally {
    ui.isUpdatingId = 0
  }
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
.actions-below { display: flex; gap: 6px; }
.actions-below .ghost, .actions-below .danger { padding: 6px 10px; border-radius: 8px; cursor: pointer; }
.actions-below .ghost { border: 1px solid #d1d5db; background: #fff; color: #111827; }
.actions-below .danger { border: 1px solid #b91c1c; background: #b91c1c; color: #fff; }
.actions-below .ghost:disabled,
.actions-below .danger:disabled { opacity: 0.6; cursor: not-allowed; }
.actions-inline .ghost:disabled,
.actions-inline .danger:disabled { opacity: 0.6; cursor: not-allowed; }
.body { display: flex; flex-direction: column; gap: 8px; }
.text { color: #111827; font-size: 14px; line-height: 1.5; }
.thumbs { display: flex; gap: 8px; flex-wrap: wrap; }
.thumbs img { width: 64px; height: 64px; object-fit: cover; border-radius: 8px; border: 1px solid #e5e7eb; }
.actions-row { display: flex; gap: 8px; }
.load-more { display: flex; justify-content: center; }
.error-row { display: flex; gap: 10px; align-items: center; }
.edit-area { display: flex; flex-direction: column; gap: 10px; }
</style>
