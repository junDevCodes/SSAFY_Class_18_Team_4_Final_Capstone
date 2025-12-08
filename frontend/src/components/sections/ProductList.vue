<template>
  <section
    id="recommend"
    class="pt-0 pb-16 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8"
  >
    <div class="flex flex-col md:flex-row justify-between items-start md:items-end mb-4 gap-4">
      <div>
        <h3 class="text-3xl font-display font-bold text-gray-900 mb-3">MD's Pick</h3>
        <p class="text-gray-500">전문 MD가 엄선한 가장 신선한 제철 상품</p>
      </div>
      <a href="#" class="text-sm font-bold border-b border-gray-900 pb-0.5 hover:text-brand-600 hover:border-brand-600 transition-colors">전체보기</a>
    </div>

    <div v-if="productStore.loading" class="flex justify-center items-center py-20">
      <div class="text-gray-500">로딩 중...</div>
    </div>

    <div v-else-if="productStore.error" class="flex justify-center items-center py-20">
      <div class="text-red-500">{{ productStore.error }}</div>
    </div>

    <div v-else class="grid grid-cols-2 lg:grid-cols-4 gap-x-6 gap-y-12">
      <ProductCard
        v-for="product in productStore.products"
        :key="product.id"
        :product="product"
      />
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useProductStore } from '@/stores/products'
import ProductCard from '@/components/ui/ProductCard.vue'

const productStore = useProductStore()

onMounted(async () => {
  try {
    await productStore.fetchProducts({ page_size: 8 })
  } catch (error) {
    console.error('Failed to fetch products:', error)
  }
})
</script>

