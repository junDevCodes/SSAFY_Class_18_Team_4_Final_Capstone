<template>
  <div class="sticky-bar">
    <div class="info">
      <img :src="thumb" :alt="product.name" @error="onError" />
      <div>
        <p class="name">{{ product.name }}</p>
        <p class="price">
          <span v-if="discountRate > 0" class="discount">{{ discountRate }}%</span>
          <span class="now">{{ formatPrice(product.price) }}</span>
        </p>
      </div>
    </div>

    <div class="controls">
      <div class="qty">
        <button @click="$emit('change-qty', Math.max(1, quantity - 1))" :disabled="quantity <= 1">-</button>
        <span>{{ quantity }}</span>
        <button @click="$emit('change-qty', quantity + 1)">+</button>
      </div>
      <div class="btns">
        <button class="ghost" @click="$emit('toggle-wish')">찜</button>
        <button class="secondary" @click="$emit('add-cart')">장바구니</button>
        <button class="primary" @click="$emit('buy-now')">바로구매</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { getProductImage, DEFAULT_PRODUCT_IMAGE, formatPrice, type ProductDetail } from '@/types/product'

defineEmits(['change-qty', 'toggle-wish', 'add-cart', 'buy-now'])

const props = defineProps<{
  product: ProductDetail
  discountRate: number
  quantity: number
}>()

const thumb = computed(() => getProductImage(props.product))
const onError = (e: Event) => {
  ;(e.target as HTMLImageElement).src = DEFAULT_PRODUCT_IMAGE
}
</script>

<style scoped>
.sticky-bar {
  position: sticky;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 40;
  background: white;
  box-shadow: 0 -12px 30px rgba(0, 0, 0, 0.12);
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.info {
  display: flex;
  gap: 12px;
  align-items: center;
}
.info img {
  width: 48px;
  height: 48px;
  object-fit: cover;
  border-radius: 10px;
  border: 1px solid var(--gray-200, #e5e7eb);
}
.name {
  font-weight: 700;
  color: #111827;
}
.price {
  display: flex;
  gap: 6px;
  align-items: center;
}
.discount {
  color: #d32f2f;
  font-weight: 800;
}
.now {
  font-weight: 800;
  color: var(--brand-900, #0f3a2a);
}
.controls {
  display: flex;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
}
.qty {
  display: inline-flex;
  border: 1px solid var(--gray-200, #e5e7eb);
  border-radius: 8px;
  overflow: hidden;
}
.qty button {
  width: 36px;
  height: 36px;
  border: none;
  background: white;
}
.qty span {
  width: 44px;
  text-align: center;
  line-height: 36px;
}
.btns {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  flex: 1;
  min-width: 260px;
}
button {
  padding: 10px;
  border-radius: 10px;
  font-weight: 700;
  border: 1px solid transparent;
  cursor: pointer;
}
.ghost {
  border-color: var(--gray-200, #e5e7eb);
  background: white;
}
.secondary {
  border-color: var(--brand-500, #00a86b);
  color: var(--brand-500, #00a86b);
  background: white;
}
.primary {
  background: var(--brand-500, #00a86b);
  color: white;
  border-color: var(--brand-500, #00a86b);
}
@media (min-width: 1024px) {
  .sticky-bar {
    display: none;
  }
}
</style>
