<template>
  <div class="gallery">
    <div class="main">
      <img :src="activeImage" :alt="product.name" @error="onError" />
    </div>
    <div v-if="images.length > 1" class="thumbs">
      <button
        v-for="(img, i) in images"
        :key="i"
        :class="['thumb', { active: i === activeIdx }]"
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
const onError = (e: Event) => {
  ;(e.target as HTMLImageElement).src = DEFAULT_PRODUCT_IMAGE
}
</script>

<style scoped>
.gallery {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.main {
  border: 1px solid var(--gray-200, #e5e7eb);
  border-radius: 12px;
  overflow: hidden;
  background: white;
}
.main img {
  width: 100%;
  display: block;
}
.thumbs {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(64px, 1fr));
  gap: 8px;
}
.thumb {
  border: 1px solid var(--gray-200, #e5e7eb);
  border-radius: 8px;
  padding: 4px;
  background: white;
}
.thumb.active {
  border-color: var(--brand-500, #00a86b);
  box-shadow: 0 0 0 2px rgba(0, 168, 107, 0.2);
}
.thumb img {
  width: 100%;
  display: block;
}
</style>
