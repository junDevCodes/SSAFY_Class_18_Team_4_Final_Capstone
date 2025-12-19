<template>
  <section class="summary">
    <p class="brand" v-if="product.seller?.brand_name">{{ product.seller.brand_name }}</p>
    <h1 class="name">{{ product.name }}</h1>

    <div class="price-row">
      <div class="price-main">
        <span v-if="product.original_price && discountRate > 0" class="original">{{ formatPrice(product.original_price) }}</span>
        <div class="current">
          <span v-if="discountRate > 0" class="badge-discount">{{ discountRate }}%</span>
          <span class="now">{{ formatPrice(product.price) }}</span>
        </div>
      </div>
      <div class="meta" v-if="product.stats?.average_rating">
        <span class="rating">★ {{ product.stats.average_rating.toFixed(1) }}</span>
        <span class="reviews">리뷰 {{ product.stats.review_count ?? 0 }}</span>
      </div>
    </div>

    <div class="benefit">
      <div class="row">
        <span class="label">배송</span>
        <span class="value">{{ product.shipping_fee > 0 ? formatPrice(product.shipping_fee) : '무료배송' }}</span>
      </div>
      <div class="row" v-if="product.free_shipping_threshold">
        <span class="label">무료배송</span>
        <span class="value">{{ formatPrice(product.free_shipping_threshold) }} 이상 구매 시</span>
      </div>
      <div class="row" v-if="product.estimated_delivery_days">
        <span class="label">도착예정</span>
        <span class="value">{{ product.estimated_delivery_days }}일 이내</span>
      </div>
      <div class="row" v-if="product.unit">
        <span class="label">판매단위</span>
        <span class="value">{{ product.unit }}</span>
      </div>
    </div>

    <div class="qty-actions">
      <div class="qty">
        <button @click="$emit('change-qty', Math.max(1, quantity - 1))" :disabled="quantity <= 1">-</button>
        <input type="number" :value="quantity" min="1" @input="onInput" />
        <button @click="$emit('change-qty', quantity + 1)">+</button>
      </div>
      <div class="actions">
        <button class="btn ghost" @click="$emit('toggle-wish')">
          {{ product.is_wishlist ? '찜 해제' : '찜하기' }} ({{ wishlistCount }})
        </button>
        <button class="btn secondary" @click="$emit('add-cart')">장바구니</button>
        <button class="btn primary" @click="$emit('buy-now')">바로구매</button>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { formatPrice, type ProductDetail } from '@/types/product'

defineProps<{
  product: ProductDetail
  discountRate: number
  wishlistCount: number
  quantity: number
}>()

const emit = defineEmits(['change-qty', 'toggle-wish', 'add-cart', 'buy-now'])

const onInput = (e: Event) => {
  const value = parseInt((e.target as HTMLInputElement).value, 10)
  emit('change-qty', Number.isFinite(value) && value > 0 ? value : 1)
}
</script>

<style scoped>
.summary {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.05);
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.brand { color: var(--brand-900, #0f3a2a); font-weight: 700; }
.name { font-size: 24px; font-weight: 800; color: #1a1a1a; line-height: 1.3; }
.price-row { display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; }
.price-main { display: flex; flex-direction: column; gap: 6px; }
.original { text-decoration: line-through; color: #9ca3af; font-size: 14px; }
.current { display: flex; align-items: center; gap: 8px; }
.badge-discount { color: #d32f2f; font-weight: 800; font-size: 18px; }
.now { font-size: 28px; font-weight: 800; color: var(--brand-900, #0f3a2a); }
.meta { display: flex; gap: 12px; color: #6b7280; font-size: 14px; }
.benefit { border: 1px solid var(--gray-200, #e5e7eb); border-radius: 12px; padding: 12px 14px; background: #f8f9fa; display: flex; flex-direction: column; gap: 8px; }
.row { display: flex; justify-content: space-between; font-size: 14px; color: #111827; }
.label { color: #6b7280; }
.qty-actions { display: flex; flex-direction: column; gap: 12px; }
.qty { display: inline-flex; align-items: center; border: 1px solid var(--gray-200, #e5e7eb); border-radius: 8px; overflow: hidden; width: fit-content; }
.qty button { width: 40px; height: 40px; background: white; border: none; cursor: pointer; }
.qty input { width: 64px; text-align: center; border: none; outline: none; }
.actions { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
.btn { padding: 12px; border-radius: 10px; font-weight: 700; border: 1px solid transparent; cursor: pointer; }
.btn.ghost { border-color: var(--gray-200, #e5e7eb); background: white; }
.btn.secondary { border-color: var(--brand-500, #00a86b); color: var(--brand-500, #00a86b); background: white; }
.btn.primary { background: var(--brand-500, #00a86b); color: white; border-color: var(--brand-500, #00a86b); }
@media (max-width: 768px) { .actions { grid-template-columns: 1fr; } }
</style>
