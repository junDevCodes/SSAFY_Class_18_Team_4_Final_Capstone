<template>
  <main class="bg-gray-50 min-h-screen pt-28 pb-16">
    <section class="max-w-6xl mx-auto px-4 space-y-8">
      <div class="relative rounded-2xl shadow-xl overflow-visible">
        <div class="absolute inset-0 overflow-hidden rounded-2xl">
          <div class="absolute inset-0 bg-gradient-to-r from-indigo-900 via-brand-700 to-brand-500"></div>
          <div class="absolute -right-10 -bottom-16 w-72 h-72 bg-white/10 rounded-full blur-3xl"></div>
        </div>
        <div class="relative z-10 flex flex-col gap-3 w-full text-white pt-4 pb-8 px-6">
          <div class="flex flex-wrap items-start justify-between gap-4">
            <div class="space-y-3 max-w-2xl">
              <p class="text-sm font-semibold uppercase tracking-widest text-white/80">SelF Mall</p>
              <h1 class="text-3xl font-display font-bold">SelF Mall 만의 Fresh 함을 골라보세요</h1>
            </div>
          </div>
          <div class="flex justify-end">
            <button
              class="px-5 py-2 rounded-full bg-white/15 text-white font-semibold border border-white/50 hover:bg-white/25 transition-colors"
              @click="goToAllProducts"
            >
              전체 상품 보기
            </button>
          </div>
        </div>
      </div>

      <div class="grid gap-6 grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
        <ProductCard
          v-for="product in limitedProducts"
          :key="product.id"
          :product="product"
          label="주간 특가"
          best-label="BEST"
        />
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import type { Product } from '@/types/product'
import ProductCard from '@/components/ui/ProductCard.vue'
import { productsAPI } from '@/services/api'

const router = useRouter()

const selfProducts = ref<Product[]>([])

const limitedProducts = computed<Product[]>(() => selfProducts.value.slice(0, 8))

const goToAllProducts = () => {
  router.push({ name: 'products' })
}

onMounted(async () => {
  try {
    const { data } = await productsAPI.getProducts({ product_type: 'main', page_size: 8 })
    selfProducts.value = data.results
  } catch (err) {
    console.error('Failed to load Self Mall products:', err)
    selfProducts.value = []
  }
})
</script>
