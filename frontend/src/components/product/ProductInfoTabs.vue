<template>
  <section class="info-tabs">
    <div class="tabs">
      <button :class="{ active: tab === 'detail' }" @click="setTab('detail')">상품상세</button>
      <button :class="{ active: tab === 'review' }" @click="setTab('review')">상품리뷰</button>
      <button :class="{ active: tab === 'shipping' }" @click="setTab('shipping')">배송/교환/반품</button>
    </div>

    <div class="panel detail-panel" v-if="tab === 'detail'">
      <div v-if="fullDescription" class="detail-text" v-html="fullDescription"></div>
      <p v-else-if="shortDescription" class="detail-text">{{ shortDescription }}</p>
      <p v-else class="empty">상품 정보가 없습니다.</p>

      <div v-if="detailImages?.length" class="detail-images">
        <img
          v-for="(src, idx) in detailImages"
          :key="`${src}-${idx}`"
          :src="src"
          :alt="`상품 상세 이미지 ${idx + 1}`"
          loading="lazy"
        />
      </div>
    </div>

    <div class="panel info" v-else-if="tab === 'review'">
      <slot name="review">
        <p>리뷰 영역은 준비 중입니다.</p>
      </slot>
    </div>
    
    <div class="panel info" v-else>
      <table>
        <tbody>
          <tr v-if="product.unit">
            <th>규격/단위</th>
            <td>{{ product.unit }}</td>
          </tr>
          <tr v-if="product.shipping_required !== undefined">
            <th>배송필수</th>
            <td>{{ product.shipping_required ? '배송 가능' : '배송 불가(직접 수령)' }}</td>
          </tr>
          <tr v-if="product.shipping_fee !== undefined">
            <th>배송비</th>
            <td>{{ product.shipping_fee > 0 ? formatPrice(product.shipping_fee) : '무료' }}</td>
          </tr>
          <tr v-if="product.estimated_delivery_days">
            <th>도착 예정</th>
            <td>{{ product.estimated_delivery_days }}일내</td>
          </tr>

          
          <tr v-if="averageRating !== null">
            <th>평균 평점</th>
            <td>{{ averageRating.toFixed(1) }} ({{ product.stats?.review_count ?? 0 }}개)</td>
          </tr>
          <tr v-else-if="product.stats">
            <th>평균 평점</th>
            <td>- ({{ product.stats?.review_count ?? 0 }}개)</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { formatPrice, type ProductDetail } from '@/types/product'

type Tab = 'detail' | 'review' | 'shipping'

const props = defineProps<{
  product: ProductDetail
  shortDescription: string | null
  fullDescription: string | null
  detailImages?: string[]
  initialTab?: Tab
}>()

const emit = defineEmits<{
  (e: 'change', tab: Tab): void
}>()

const tab = ref<Tab>(props.initialTab ?? 'detail')

const setTab = (next: Tab) => {
  tab.value = next
  emit('change', next)
}

watch(
  () => props.initialTab,
  (val: Tab | undefined) => {
    if (val && val !== tab.value) {
      tab.value = val
      emit('change', val)
    }
  }
)

const averageRating = computed(() => {
  const num = Number(props.product.stats?.average_rating)
  return Number.isFinite(num) ? num : null
})
</script>

<style scoped>
.info-tabs {
  margin-top: 32px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.05);
}
.tabs {
  display: flex;
  border-bottom: 1px solid var(--gray-200, #e5e7eb);
}
.tabs button {
  flex: 1;
  padding: 14px;
  font-weight: 700;
  background: transparent;
  border: none;
  cursor: pointer;
  color: #6b7280;
}
.tabs button.active {
  color: var(--brand-900, #0f3a2a);
  border-bottom: 2px solid var(--brand-500, #00a86b);
}
.panel {
  padding: 20px;
  color: #111827;
}
.detail-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.detail-text {
  white-space: pre-line;
  line-height: 1.6;
}
.detail-images {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
}
.detail-images img {
  width: 100%;
  border-radius: 8px;
  background: #f9fafb;
  border: 1px solid var(--gray-200, #e5e7eb);
  object-fit: contain;
}
.empty {
  color: #6b7280;
}
.info table {
  width: 100%;
  border-collapse: collapse;
}
.info th,
.info td {
  border-bottom: 1px solid var(--gray-200, #e5e7eb);
  padding: 12px 8px;
  text-align: left;
}
.info th {
  width: 140px;
  color: #6b7280;
  font-weight: 700;
  background: #f8f9fa;
}
</style>
