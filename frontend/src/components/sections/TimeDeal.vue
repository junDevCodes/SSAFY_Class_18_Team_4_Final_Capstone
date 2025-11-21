<template>
  <section class="py-20 border-b border-gray-100">
    <div class="max-w-7xl mx-auto">
      <div class="px-4 sm:px-6 lg:px-8 mb-8 flex justify-between items-end">
        <div>
          <div class="text-brand-600 font-bold text-sm mb-2 tracking-wider uppercase">Time Offer</div>
          <h3 class="text-3xl font-display font-bold text-gray-900">24시간 한정 특가</h3>
        </div>
        <div class="flex items-center gap-2 text-2xl font-bold text-gray-900 font-mono bg-gray-100 px-4 py-2 rounded-lg">
          <Timer :size="20" class="text-brand-600" />
          <span>{{ timer.hours }}:{{ timer.minutes }}:{{ timer.seconds }}</span>
        </div>
      </div>

      <div class="overflow-x-auto no-scrollbar px-4 sm:px-6 lg:px-8 pb-8 -mx-4 sm:mx-0">
        <div class="flex gap-6 w-max">
          <div v-for="product in timeDealProducts" :key="product.id" class="w-[220px] group cursor-pointer">
            <div class="relative aspect-[4/5] rounded-xl overflow-hidden bg-gray-100 mb-4 shadow-sm">
              <img :src="product.image" :alt="product.name" class="w-full h-full object-cover transition-transform duration-700 group-hover:scale-110">
              <div class="absolute top-3 left-3 bg-red-500 text-white text-xs font-bold px-2 py-1 rounded">-{{ product.discount }}%</div>
            </div>
            <h4 class="text-base font-medium text-gray-900 mb-1 line-clamp-1 group-hover:text-brand-600 transition-colors">{{ product.name }}</h4>
            <div class="flex items-baseline gap-2">
              <span class="font-bold text-lg">{{ formatPrice(product.price) }}</span>
              <span class="text-sm text-gray-400 line-through">{{ formatPrice(product.originalPrice) }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Timer } from 'lucide-vue-next'
import { useTimer } from '@/composables/useTimer'
import { useProductStore } from '@/stores/products'
import { formatPrice } from '@/utils/formatters'

const { timer } = useTimer()
const productStore = useProductStore()

const timeDealProducts = computed(() => {
  return productStore.products.slice(4, 9)
})
</script>

