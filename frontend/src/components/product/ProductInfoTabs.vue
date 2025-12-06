<template>
  <section class="info-tabs">
    <div class="tabs">
      <button :class="{ active: tab === 'detail' }" @click="tab = 'detail'">상품상세</button>
      <button :class="{ active: tab === 'review' }" @click="tab = 'review'">상품리뷰</button>
      <button :class="{ active: tab === 'shipping' }" @click="tab = 'shipping'">배송/교환/반품</button>
    </div>

    <div class="panel" v-if="tab === 'detail'">
      <div v-if="fullDescription" v-html="fullDescription"></div>
      <p v-else-if="shortDescription">{{ shortDescription }}</p>
      <p v-else>상세 정보가 없습니다.</p>
    </div>

    <div class="panel info" v-else-if="tab === 'review'">
      <p>리뷰 영역은 준비 중입니다.</p>
    </div>

    <div class="panel info" v-else>
      <table>
        <tbody>
          <tr v-if="product.unit">
            <th>판매단위</th>
            <td>{{ product.unit }}</td>
          </tr>
          <tr v-if="product.shipping_required !== undefined">
            <th>배송여부</th>
            <td>{{ product.shipping_required ? '배송 가능' : '배송 불가(직접 수령)' }}</td>
          </tr>
          <tr v-if="product.shipping_fee !== undefined">
            <th>배송비</th>
            <td>{{ product.shipping_fee > 0 ? formatPrice(product.shipping_fee) : '무료' }}</td>
          </tr>
          <tr v-if="product.estimated_delivery_days">
            <th>도착 예정</th>
            <td>{{ product.estimated_delivery_days }}일 이내</td>
          </tr>
          <tr v-if="product.stats?.average_rating">
            <th>평균 평점</th>
            <td>{{ product.stats.average_rating.toFixed(1) }} ({{ product.stats.review_count ?? 0 }}개)</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { formatPrice, type ProductDetail } from '@/types/product'

defineProps<{
  product: ProductDetail
  shortDescription: string | null
  fullDescription: string | null
}>()

const tab = ref<'detail' | 'review' | 'shipping'>('detail')
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
