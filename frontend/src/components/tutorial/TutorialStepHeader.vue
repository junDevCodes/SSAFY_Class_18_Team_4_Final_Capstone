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

// 새로운 순서: Step 3-5 좋아하는 음식, Step 6 좋아하는 음식(복수 선택), Step 7 싫어하는 음식(단일 선택)
const stepQuestions: Record<number, string> = {
  3: '요즘 자주 찾게 되는 맛이나 향은 무엇인가요?',
  4: '더 좋아하는게 있으세요? 솔직하게 말해주세요!',
  5: '오늘은 어떤 기분이죠? 그 기분에 어떤 식재료를 고르고 싶으신가요?',
  6: '마지막으로 좋아하는 것! 여러 개 골라주세요!',
  7: '혹시 정말 싫어하는 음식이 있나요? (추천에서 제외됩니다)',
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
