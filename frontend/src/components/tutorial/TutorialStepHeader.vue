<template>
  <header class="space-y-2">
    <p class="text-xs font-semibold uppercase tracking-wide text-brand-500">
      Step {{ step }}
    </p>
    <div class="rounded-2xl bg-white/80 p-4 shadow-sm ring-1 ring-gray-100">
      <p class="text-lg font-semibold text-gray-900">
        {{ questionText }}
      </p>
      <p v-if="tutorialMode === 'CELEB' && celebrityLine" class="mt-2 text-sm text-gray-600">
        <span class="font-semibold text-brand-600">{{ celebrityName }}:</span>
        <span class="ml-1">{{ celebrityLine }}</span>
      </p>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { CELEB_LINES, type Celebrity } from '@/constants/celebLines'

type StepKey = '3' | '4' | '5' | '6' | '7'

const props = defineProps<{
  step: number
  tutorialMode: 'CELEB' | 'PARENT'
  celebrityName?: string
  celebrityId?: Celebrity
}>()

const stepQuestions: Record<number, string> = {
  3: '혹시 정말 싫어하는 음식이 있나요?',
  4: '요즘 자주 찾게 되는 맛이나 향은 무엇인가요?',
  5: '오늘은 어떤 기분이죠? 그 기분에 어떤 식재료를 고르고 싶으신가요?',
  6: '또 좋아하는게 있으세요?',
  7: '마지막으로 꼭 챙기고 싶은 포인트가 있을까요?',
}

const stepKey = computed<StepKey | null>(() => {
  const key = String(props.step) as StepKey
  return ['3', '4', '5', '6', '7'].includes(key) ? key : null
})

const questionText = computed(() => {
  if (props.tutorialMode === 'CELEB' && props.celebrityId && stepKey.value) {
    return CELEB_LINES[props.celebrityId][stepKey.value].question
  }
  return stepQuestions[props.step] ?? ''
})

const celebrityLine = computed(() => {
  if (props.tutorialMode !== 'CELEB') return ''
  if (!props.celebrityId || !stepKey.value) return ''
  return CELEB_LINES[props.celebrityId][stepKey.value].reaction
})
</script>
