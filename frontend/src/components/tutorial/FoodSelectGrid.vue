<template>
  <div class="grid grid-cols-2 gap-3 sm:gap-4">
    <button
      v-for="item in items"
      :key="item.id"
      type="button"
      class="group flex flex-col items-center justify-center rounded-2xl border border-brand-100 bg-white/90 px-3 py-4 shadow-sm transition duration-200 hover:-translate-y-1 hover:border-brand-300 hover:shadow-md active:translate-y-0 active:shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-300"
      @click="handleSelect(item)"
    >
      <div class="flex h-12 w-12 items-center justify-center rounded-full bg-brand-50 text-2xl shadow-inner transition duration-200 group-hover:scale-105">
        {{ item.emoji }}
      </div>
      <div class="mt-2 text-sm font-semibold text-gray-800">
        {{ item.label }}
      </div>
    </button>
  </div>
</template>

<script setup lang="ts">
import type { FoodItem } from '@/constants/foodItems'

defineProps<{
  items: FoodItem[]
}>()

const emit = defineEmits<{
  (e: 'select', item: FoodItem): void
}>()

const handleSelect = (item: FoodItem) => {
  emit('select', item)
}
</script>
