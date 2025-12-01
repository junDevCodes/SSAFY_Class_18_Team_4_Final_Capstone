<template>
  <Transition name="toast">
    <div v-if="uiStore.toast.show" class="fixed bottom-10 left-1/2 transform -translate-x-1/2 z-[120] bg-gray-900 text-white px-6 py-3 rounded-full shadow-2xl flex items-center gap-3 min-w-[300px]">
      <CheckCircle :size="16" class="text-brand-500" />
      <p class="text-sm font-medium">{{ uiStore.toast.message }}</p>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { CheckCircle } from 'lucide-vue-next'
import { useUIStore } from '@/stores/ui'

const uiStore = useUIStore()
</script>

