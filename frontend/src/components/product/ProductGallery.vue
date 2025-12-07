<template>
  <div class="gallery">
    <div class="main" :class="{ 'is-sold-out': isOutOfStock }">
      <img :src="activeImage" :alt="product.name" @error="onError" />
      <div v-if="isOutOfStock" class="sold-out-overlay">SOLD OUT</div>
    </div>
    <div v-if="images.length > 1" class="thumbs">
      <button
        v-for="(img, i) in images"
        :key="i"
        :class="['thumb', { active: i === activeIdx, 'is-sold-out': isOutOfStock }]"
        @click="activeIdx = i"
      >
        <img :src="img" :alt="`${product.name}-${i}`" @error="onError" />
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { getProductImage, DEFAULT_PRODUCT_IMAGE, type ProductDetail, type ProductImage } from '@/types/product'

const props = defineProps<{ product: ProductDetail }>()

const activeIdx = ref(0)
const images = computed(() => {
  const list = (props.product?.images ?? []) as ProductImage[]
  return list.length ? list.map((img) => img.image_url) : [getProductImage(props.product)]
})
const activeImage = computed(() => images.value[activeIdx.value] || DEFAULT_PRODUCT_IMAGE)
const isOutOfStock = computed(() => {
  const stock = props.product?.inventory?.stock_quantity
  return typeof stock === 'number' ? stock <= 0 : false
})
const onError = (e: Event) => {
  ;(e.target as HTMLImageElement).src = DEFAULT_PRODUCT_IMAGE
}
</script>

<style scoped>
.gallery { display: flex; flex-direction: column; gap: 12px; }
.main {
  position: relative;
  border: 1px solid var(--gray-200, #e5e7eb);
  border-radius: 12px;
  overflow: hidden;
  background: white;
}
.main img {
  width: 100%;
  display: block;
  transition: filter 0.2s ease, opacity 0.2s ease;
}
.main.is-sold-out img { filter: grayscale(1); opacity: 0.55; }
.sold-out-overlay {
  position: absolute; inset: 0;
  display: flex; align-items: center; justify-content: center;
  background: rgba(17, 24, 39, 0.55);
  color: #fff; font-weight: 800; letter-spacing: 2px; font-size: 1.1rem;
}
.thumbs { display: grid; grid-template-columns: repeat(auto-fit, minmax(64px, 1fr)); gap: 8px; }
.thumb {
  border: 1px solid var(--gray-200, #e5e7eb);
  border-radius: 8px; padding: 4px; background: white;
  transition: filter 0.2s ease, opacity 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
}
.thumb.active { border-color: var(--brand-500, #00a86b); box-shadow: 0 0 0 2px rgba(0, 168, 107, 0.2); }
.thumb.is-sold-out { filter: grayscale(1); opacity: 0.6; }
.thumb img { width: 100%; display: block; }
</style>
