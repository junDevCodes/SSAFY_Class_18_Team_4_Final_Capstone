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
        <p v-if="isOutOfStock" class="soldout-hint">품절된 상품입니다</p>
        <p v-else-if="stockLabel" class="stock-badge">{{ stockLabel }}</p>
      </div>
    </div>

    <div class="controls">
      <div class="qty" :class="{ disabled: isOutOfStock }">
        <button @click="$emit('change-qty', Math.max(1, quantity - 1))" :disabled="quantity <= 1 || isOutOfStock">-</button>
        <span>{{ quantity }}</span>
        <button @click="$emit('change-qty', quantity + 1)" :disabled="isOutOfStock">+</button>
      </div>
      <div class="btns">
        <button class="wish-icon" @click="$emit('toggle-wish')" :aria-pressed="product.is_wishlist">
          <span class="heart" :class="{ filled: product.is_wishlist }">♥</span>
          <span v-if="product.stats" class="wish-count">{{ product.stats.wishlist_count }}</span>
        </button>
        <button class="secondary" @click="$emit('add-cart')" :disabled="isOutOfStock">
          {{ isOutOfStock ? '품절' : '장바구니' }}
        </button>
        <button class="primary" @click="$emit('buy-now')" :disabled="isOutOfStock">
          {{ isOutOfStock ? '품절' : '바로구매' }}
        </button>
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
  soldOut?: boolean
  stockLabel?: string | null
}>()

const thumb = computed(() => getProductImage(props.product))

const isSellerOutOfStock = (product: ProductDetail | null | undefined) => {
  if (!product || product.product_type !== 'seller') return false
  const stock = product.inventory?.stock_quantity
  if (stock === null) return true
  if (typeof stock === 'number') return stock <= 0
  return false
}

const isOutOfStock = computed(() => {
  if (typeof props.soldOut === 'boolean') return props.soldOut
  return isSellerOutOfStock(props.product)
})

const onError = (e: Event) => {
  ;(e.target as HTMLImageElement).src = DEFAULT_PRODUCT_IMAGE
}
</script>

<style scoped>
.sticky-bar { position: sticky; bottom: 0; left: 0; right: 0; z-index: 40; background: white; box-shadow: 0 -12px 30px rgba(0, 0, 0, 0.12); padding: 12px 16px; display: flex; flex-direction: column; gap: 12px; }
.info { display: flex; gap: 12px; align-items: center; }
.info img { width: 48px; height: 48px; object-fit: cover; border-radius: 10px; border: 1px solid var(--gray-200, #e5e7eb); }
.name { font-weight: 700; color: #111827; }
.price { display: flex; gap: 6px; align-items: center; }
.discount { color: #d32f2f; font-weight: 800; }
.now { font-weight: 800; color: var(--brand-900, #0f3a2a); }
.soldout-hint { color: #ef4444; font-size: 12px; margin-top: 4px; }
.stock-badge { color: #b45309; background: #fff5e6; display: inline-flex; align-items: center; padding: 4px 8px; border-radius: 999px; font-size: 12px; font-weight: 700; margin-top: 4px; }
.controls { display: flex; gap: 12px; align-items: center; justify-content: space-between; flex-wrap: wrap; }
.qty { display: inline-flex; border: 1px solid var(--gray-200, #e5e7eb); border-radius: 8px; overflow: hidden; }
.qty.disabled { opacity: 0.6; }
.qty button { width: 36px; height: 36px; border: none; background: white; }
.qty span { width: 44px; text-align: center; line-height: 36px; }
.btns { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; flex: 1; min-width: 260px; }
button { padding: 10px; border-radius: 10px; font-weight: 700; border: 1px solid transparent; cursor: pointer; }
.wish-icon { border: 1px solid var(--gray-200, #e5e7eb); background: white; display: inline-flex; align-items: center; justify-content: center; gap: 4px; border-radius: 10px; }
.wish-icon .heart { color: #d1d5db; font-size: 18px; line-height: 1; }
.wish-icon .heart.filled { color: #d14343; }
.wish-count { font-size: 12px; color: #374151; }
.ghost { border-color: var(--gray-200, #e5e7eb); background: white; }
.secondary { border-color: var(--brand-500, #00a86b); color: var(--brand-500, #00a86b); background: white; }
.primary { background: var(--brand-500, #00a86b); color: white; border-color: var(--brand-500, #00a86b); }
@media (min-width: 1024px) { .sticky-bar { display: none; } }
</style>
