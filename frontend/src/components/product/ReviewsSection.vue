<template>
  <section class="reviews">
    <div class="reviews-head">
      <div class="score">{{ average.toFixed(1) }}</div>
      <div class="count">리뷰 {{ count }}개</div>
    </div>
    <div class="reviews-grid">
      <article v-for="r in reviews" :key="r.id" class="review-card">
        <div class="rating">★ {{ r.rating }}</div>
        <p class="text">{{ r.content }}</p>
        <div class="meta">{{ r.author }} · {{ r.date }}</div>
        <div v-if="r.images?.length" class="thumbs">
          <img v-for="(img, i) in r.images" :key="i" :src="img" />
        </div>
      </article>
      <p v-if="!reviews.length" class="empty">아직 리뷰가 없습니다.</p>
    </div>
  </section>
</template>

<script setup lang="ts">
interface Review {
  id: number
  rating: number
  content: string
  author: string
  date: string
  images?: string[]
}

defineProps<{
  reviews: Review[]
  average: number
  count: number
}>()
</script>

<style scoped>
.reviews { margin-top: 32px; display: flex; flex-direction: column; gap: 16px; }
.reviews-head { display: flex; gap: 12px; align-items: baseline; }
.score { font-size: 32px; font-weight: 800; color: #0f3a2a; }
.count { color: #6b7280; }
.reviews-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 16px; }
.review-card { border: 1px solid #e5e7eb; border-radius: 10px; padding: 12px; background: #fff; display: flex; flex-direction: column; gap: 8px; }
.rating { color: #d32f2f; font-weight: 700; }
.text { color: #111827; font-size: 14px; line-height: 1.5; }
.meta { color: #6b7280; font-size: 12px; }
.thumbs { display: flex; gap: 6px; flex-wrap: wrap; }
.thumbs img { width: 64px; height: 64px; object-fit: cover; border-radius: 6px; border: 1px solid #e5e7eb; }
.empty { grid-column: 1 / -1; text-align: center; color: #6b7280; padding: 12px 0; }
</style>
