<template>
  <section class="rounded-3xl bg-white/90 p-6 shadow-xl ring-1 ring-gray-100">
    <header class="mb-4 flex items-start justify-between gap-3">
      <div>
        <p class="text-xs font-semibold uppercase tracking-wide text-brand-500">Tutorial Summary</p>
        <p class="mt-1 text-lg font-bold text-gray-900">
          {{ introText }}
        </p>
        <p class="text-sm text-gray-600">
          숫자 대신 말로 정리했어요. 바로 추천으로 넘어갈게요.
        </p>
      </div>
      <span
        v-if="tutorialMode === 'CELEB'"
        class="inline-flex items-center rounded-full bg-brand-50 px-3 py-1 text-xs font-semibold text-brand-700 ring-1 ring-brand-100"
      >
        {{ celebrityName ?? '파트너' }} 모드
      </span>
    </header>

    <div class="space-y-3 text-sm text-gray-800">
      <div class="rounded-2xl bg-brand-50/70 p-4 ring-1 ring-brand-100">
        <p class="font-semibold text-brand-800">선호</p>
        <p class="mt-1 text-gray-800">
          {{ preferredLine }}
        </p>
      </div>
      <div class="rounded-2xl bg-gray-50 p-4 ring-1 ring-gray-100">
        <p class="font-semibold text-gray-900">보통</p>
        <p class="mt-1 text-gray-800">
          {{ neutralLine }}
        </p>
      </div>
      <div class="rounded-2xl bg-orange-50 p-4 ring-1 ring-orange-100">
        <p class="font-semibold text-orange-800">불호</p>
        <p class="mt-1 text-orange-800">
          {{ dislikeLine }}
        </p>
      </div>
      <div v-if="excludedLine" class="rounded-2xl bg-red-50 p-4 ring-1 ring-red-100">
        <p class="font-semibold text-red-800">완전히 제외</p>
        <p class="mt-1 text-red-800">
          {{ excludedLine }}
        </p>
      </div>
    </div>

    <div class="mt-6 flex justify-end">
      <button
        type="button"
        class="inline-flex items-center justify-center rounded-full bg-brand-600 px-4 py-2 text-sm font-semibold text-white shadow-md transition hover:bg-brand-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-300"
        @click="$emit('complete')"
      >
        추천 보러가기
      </button>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { CATEGORY_LIST, type Category } from '@/constants/categories'

const props = defineProps<{
  scores: Record<Category, number>
  tutorialMode: 'CELEB' | 'PARENT'
  celebrityName?: string
}>()

const displayLabel: Record<Category, string> = {
  GRAIN: '곡류',
  NOODLE_FLOUR: '면 · 밀가루',
  VEGETABLE: '채소',
  FRUIT: '과일',
  BEAN_EGG: '콩 · 달걀',
  MEAT: '고기',
  SEAFOOD: '해산물',
  DAIRY: '유제품',
  KIMCHI_SIDE: '김치 · 반찬',
  SEASONING_SAUCE_OIL: '양념 · 소스 · 오일',
  NUT_DRY_ETC: '견과 · 건과',
  DRINK: '음료',
  INSTANT_FOOD: '즉석식품',
}

const sortedByGroup = computed(() => {
  const preferred: string[] = []
  const neutral: string[] = []
  const dislike: string[] = []
  const excluded: string[] = []

  for (const category of CATEGORY_LIST) {
    const score = props.scores[category]
    if (score === -1) {
      excluded.push(displayLabel[category])
      continue
    }
    if (score >= 7) {
      preferred.push(displayLabel[category])
    } else if (score >= 3) {
      neutral.push(displayLabel[category])
    } else {
      dislike.push(displayLabel[category])
    }
  }

  return { preferred, neutral, dislike, excluded }
})

const introText = computed(() =>
  props.tutorialMode === 'CELEB'
    ? `${props.celebrityName ?? '파트너'}가 함께 정리했어요.`
    : '취향을 간단히 정리했어요.',
)

const preferredLine = computed(() => {
  const items = sortedByGroup.value.preferred
  return items.length
    ? `특히 좋아하는 건 ${items.join(', ')} 쪽이에요.`
    : '아직 뚜렷하게 좋아하는 항목은 없어요.'
})

const neutralLine = computed(() => {
  const items = sortedByGroup.value.neutral
  return items.length
    ? `${items.join(', ')} 정도는 무난하게 괜찮아요.`
    : '무난한 항목은 아직 없어요.'
})

const dislikeLine = computed(() => {
  const items = sortedByGroup.value.dislike
  return items.length
    ? `${items.join(', ')} 쪽은 선호도가 낮아요.`
    : '선호도가 낮은 항목은 거의 없어요.'
})

const excludedLine = computed(() => {
  const items = sortedByGroup.value.excluded
  if (!items.length) return ''
  return `${items.join(', ')}는 추천에서 완전히 제외했어요.`
})
</script>
