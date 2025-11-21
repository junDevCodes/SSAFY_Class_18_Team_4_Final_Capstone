<template>
  <section class="py-20 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
    <div class="flex flex-col md:flex-row justify-between items-start md:items-end mb-10 gap-4">
      <div>
        <h3 class="text-3xl font-display font-bold text-gray-900 mb-3">MD's Pick</h3>
        <p class="text-gray-500">전문 MD가 엄선한 가장 신선한 제철 상품</p>
      </div>
      <a href="#" class="text-sm font-bold border-b border-gray-900 pb-0.5 hover:text-brand-600 hover:border-brand-600 transition-colors">전체보기</a>
    </div>

    <div class="grid grid-cols-2 lg:grid-cols-4 gap-x-6 gap-y-12">
      <ProductCard 
        v-for="product in productStore.products" 
        :key="product.id" 
        :product="product"
      />
    </div>
  </section>
</template>

<script setup lang="ts">
import { useProductStore } from '@/stores/products'
import ProductCard from '@/components/ui/ProductCard.vue'

const productStore = useProductStore()
</script>

