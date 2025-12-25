<template>
  <button
    type="button"
    class="flex items-center gap-2 rounded-full bg-white/80 px-3 py-1.5 text-xs font-semibold text-gray-600 shadow-sm ring-1 ring-gray-200 transition hover:-translate-y-0.5 hover:ring-brand-200 hover:text-brand-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-300"
    @click="handleSkip"
  >
    <span>나중에 할게요</span>
  </button>
</template>

<script setup lang="ts">
import { useTutorialState } from '@/composables/useTutorialState'

const emit = defineEmits<{
  (e: 'tutorialCompleted'): void
}>()

const { setSkipDefaultScores } = useTutorialState()

const handleSkip = () => {
  setSkipDefaultScores()
  emit('tutorialCompleted')
}
</script>
