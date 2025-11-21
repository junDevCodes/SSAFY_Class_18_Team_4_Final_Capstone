<template>
  <section class="py-12 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
    <div class="grid grid-cols-5 md:grid-cols-10 gap-4 md:gap-8">
      <div v-for="(cat, idx) in QUICK_CATEGORIES" :key="idx" class="flex flex-col items-center group cursor-pointer">
        <div class="w-16 h-16 rounded-2xl bg-gray-50 flex items-center justify-center text-2xl shadow-sm group-hover:shadow-md group-hover:-translate-y-1 transition-all duration-300 border border-gray-100">
          {{ cat.icon }}
        </div>
        <span class="mt-3 text-xs font-medium text-gray-600 group-hover:text-gray-900">{{ cat.name }}</span>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { QUICK_CATEGORIES } from '@/utils/constants'
</script>

