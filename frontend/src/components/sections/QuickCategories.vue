<template>
  <section class="py-12 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
    <div class="grid grid-cols-5 md:grid-cols-10 gap-4 md:gap-8">
      <div
        v-for="cat in categories"
        :key="cat.id"
        class="flex flex-col items-center gap-2 cursor-pointer group"
        @click="goToCategory(cat.id)"
      >
        <div class="w-16 h-16 sm:w-20 sm:h-20 rounded-full overflow-hidden border border-gray-100 shadow-sm group-hover:shadow-md group-hover:border-brand-200 transition-all duration-300 relative bg-gray-50">
          <img :src="getCategoryImage(cat.name)" :alt="displayName(cat.name)" class="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110">
        </div>
        <span class="mt-2 text-xs sm:text-[13px] text-gray-600 font-medium group-hover:text-brand-700 transition-colors">
          {{ displayName(cat.name) }}
        </span>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useProductStore } from '@/stores/products'
import { getCategoryImage } from '@/utils/constants'

const router = useRouter()
const productStore = useProductStore()

const categories = computed(() => productStore.categories)

const displayName = (name: string) => {
  return name === '과일' ? '과일/견과' : name
}

const goToCategory = (id: number) => {
  router.push({ name: 'search', query: { category: id } })
}

onMounted(async () => {
  if (productStore.categories.length === 0) {
    try {
      await productStore.fetchCategories()
    } catch {
      // ignore
    }
  }
})
</script>

