<template>
  <div
    id="sticky-nav"
    :class="[
      'sticky top-16 z-40 backdrop-blur-md border-b border-gray-100 transition-all duration-300',
      navToneClass
    ]"
  >
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="flex items-center justify-between h-14">
        <div class="flex gap-1 overflow-x-auto no-scrollbar h-full items-center">
          <button 
            v-for="cat in CATEGORIES" 
            :key="cat"
            class="px-4 py-1.5 rounded-full text-sm font-medium transition-all whitespace-nowrap hover:bg-gray-50"
            :class="uiStore.activeTab === cat ? 'bg-gray-900 text-white shadow-md hover:bg-gray-800' : 'text-gray-500 bg-transparent'"
            @click="uiStore.setActiveTab(cat)"
          >
            {{ cat }}
          </button>
        </div>
        <button class="hidden sm:flex items-center gap-1 text-sm font-medium text-gray-500 hover:text-gray-900">
          <SlidersHorizontal :size="16" /> 필터
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { SlidersHorizontal } from 'lucide-vue-next'
import { useUIStore } from '@/stores/ui'
import { CATEGORIES } from '@/utils/constants'

const uiStore = useUIStore()

const navToneClass = computed(() =>
  uiStore.headerState === 'green' ? 'bg-[#f6f1fb]' : 'bg-white/95'
)
</script>

