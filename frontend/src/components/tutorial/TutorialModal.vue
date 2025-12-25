<template>
  <Transition name="fade">
    <div
      v-if="isOpen"
      class="fixed inset-0 z-[120] flex items-center justify-center px-4 py-6 sm:px-6"
    >
      <div class="absolute inset-0 bg-black/40 backdrop-blur-sm" @click="handleClose"></div>

      <div
        ref="scrollArea"
        class="relative w-full max-w-4xl max-h-[90vh] overflow-y-auto rounded-3xl bg-gradient-to-br from-brand-50 via-white to-brand-100 p-5 sm:p-8 shadow-2xl ring-1 ring-brand-100/60"
      >
        <div class="flex items-center justify-between gap-3">
          <div>
            <p class="text-xs font-semibold uppercase tracking-[0.2em] text-brand-600">Onboarding</p>
            <p class="text-lg font-bold text-gray-900">나만의 추천을 만들고 있어요</p>
            <p
              v-if="isManual"
              class="mt-1 text-xs font-semibold text-brand-700"
            >
              취향 다시 설정하기
            </p>
          </div>
          <SkipTutorialButton @tutorialCompleted="handleSkip" />
        </div>

        <div class="mt-4 h-2 w-full overflow-hidden rounded-full bg-white/60 ring-1 ring-brand-100">
          <div
            class="h-full bg-brand-500 transition-all duration-300"
            :style="{ width: `${progress}%` }"
          ></div>
        </div>

        <div class="mt-6 space-y-6">
          <!-- Step 1 -->
          <div v-if="step === 1" class="space-y-4">
            <p class="text-sm text-gray-700">어떤 분이신가요?</p>
            <div class="grid grid-cols-2 gap-3 sm:gap-4">
              <button
                type="button"
                class="rounded-2xl bg-white p-4 shadow-sm ring-1 ring-gray-100 transition hover:-translate-y-1 hover:shadow-md hover:ring-brand-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400"
                @click="selectGender('MALE')"
              >
                <p class="text-sm font-semibold text-gray-900">남성</p>
                <p class="text-xs text-gray-600 mt-1">내 성별</p>
              </button>
              <button
                type="button"
                class="rounded-2xl bg-white p-4 shadow-sm ring-1 ring-gray-100 transition hover:-translate-y-1 hover:shadow-md hover:ring-brand-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400"
                @click="selectGender('FEMALE')"
              >
                <p class="text-sm font-semibold text-gray-900">여성</p>
                <p class="text-xs text-gray-600 mt-1">내 성별</p>
              </button>
            </div>
          </div>

          <!-- Step 2 -->
          <div v-else-if="step === 2" class="space-y-4">
            <p class="text-sm text-gray-700">어떤게 맘에 들어요?</p>
            <div class="grid grid-cols-2 gap-3 sm:gap-4">
              <button
                type="button"
                class="rounded-2xl bg-white p-4 shadow-sm ring-1 ring-gray-100 transition hover:-translate-y-1 hover:shadow-md hover:ring-brand-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400"
                @click="selectMode('CELEB')"
              >
                <p class="text-sm font-semibold text-gray-900">이쁘거나 잘생긴 사람과 함께</p>
                <p class="text-xs text-gray-600 mt-1">톤과 멘트는 밝게</p>
              </button>
              <button
                type="button"
                class="rounded-2xl bg-white p-4 shadow-sm ring-1 ring-gray-100 transition hover:-translate-y-1 hover:shadow-md hover:ring-brand-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400"
                @click="selectMode('PARENT')"
              >
                <p class="text-sm font-semibold text-gray-900">부모님과 함께</p>
                <p class="text-xs text-gray-600 mt-1">차분하게</p>
              </button>
            </div>
          </div>

          <!-- Step 3 -->
          <div v-else-if="step === 3" class="space-y-4">
            <TutorialStepHeader
              :step="3"
              :tutorialMode="tutorialMode || 'PARENT'"
              :celebrityName="celebrityDisplayName"
              :celebrityId="selectedCelebrity || undefined"
            />
            <FoodSelectGrid :items="q3Items" :selectedIds="selectedDislikeIds" @select="handleDislikeSelect" />
            <div v-if="selectedDislikeLabels.length" class="flex flex-wrap gap-2 text-xs text-red-700">
              <span class="rounded-full bg-red-50 px-3 py-1 ring-1 ring-red-100" v-for="label in selectedDislikeLabels" :key="label">
                {{ label }} 제외
              </span>
            </div>
            <div class="flex justify-end">
              <button
                type="button"
                class="rounded-full bg-brand-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-brand-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-300"
                @click="goToStep(4)"
              >
                다 골랐어요
              </button>
            </div>
          </div>

          <!-- Step 4 -->
          <div v-else-if="step === 4" class="space-y-4">
            <TutorialStepHeader
              :step="4"
              :tutorialMode="tutorialMode || 'PARENT'"
              :celebrityName="celebrityDisplayName"
              :celebrityId="selectedCelebrity || undefined"
            />
            <p class="text-xs text-gray-600">메인 후보를 골라주세요.</p>
            <FoodSelectGrid :items="q4Items" @select="handleQ4Select" />
          </div>

          <!-- Step 5 -->
          <div v-else-if="step === 5" class="space-y-4">
            <TutorialStepHeader
              :step="5"
              :tutorialMode="tutorialMode || 'PARENT'"
              :celebrityName="celebrityDisplayName"
              :celebrityId="selectedCelebrity || undefined"
            />
            <p class="text-xs text-gray-600">
              방금 선택이 다시 등장할 수 있어요. 정말 좋아하는거라면 또 골라주세요! (추천 서비스에 도움이 돼요)
            </p>
            <FoodSelectGrid :items="q5Items" @select="handleQ5Select" />
          </div>

          <!-- Step 6 -->
          <div v-else-if="step === 6" class="space-y-4">
            <TutorialStepHeader
              :step="6"
              :tutorialMode="tutorialMode || 'PARENT'"
              :celebrityName="celebrityDisplayName"
              :celebrityId="selectedCelebrity || undefined"
            />
            <p class="text-xs text-gray-600">보조 후보를 골라주세요.</p>
            <FoodSelectGrid :items="q6Items" @select="handleQ6Select" />
          </div>

          <!-- Step 7 -->
          <div v-else-if="step === 7" class="space-y-4">
            <TutorialStepHeader
              :step="7"
              :tutorialMode="tutorialMode || 'PARENT'"
              :celebrityName="celebrityDisplayName"
              :celebrityId="selectedCelebrity || undefined"
            />
            <p class="text-xs text-gray-600">
              방금 선택이 다시 등장할 수 있어요. 정말 좋아하는거라면 또 골라주세요! (추천 서비스에 도움이 돼요)
            </p>
            <FoodSelectGrid :items="q7Items" @select="handleQ7Select" />
          </div>

          <!-- Step 8 -->
          <div v-else-if="step === 8" class="space-y-4">
            <SummaryCard
              :scores="scores"
              :tutorialMode="tutorialMode || 'PARENT'"
              :celebrityName="celebrityDisplayName"
              @complete="handleSummaryComplete"
            />
          </div>

          <!-- Step 9 -->
          <div v-else-if="step === 9" class="space-y-4 text-center">
            <div class="rounded-3xl bg-white p-6 shadow-lg ring-1 ring-brand-100">
              <p class="text-sm font-semibold uppercase tracking-[0.2em] text-brand-500">Ready</p>
              <p class="mt-2 text-2xl font-bold text-gray-900">{{ endingMain }}</p>
              <p class="mt-2 text-sm text-gray-700">{{ endingSub }}</p>
            </div>
            <div class="flex justify-center">
              <button
                type="button"
                class="inline-flex items-center justify-center rounded-full bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white shadow-md transition hover:bg-brand-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-300"
                @click="handleComplete"
              >
                추천 시작하기
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useTutorialState } from '@/composables/useTutorialState'
import { useTutorialFlow } from '@/composables/useTutorialFlow'
import { FOOD_ITEMS, type FoodItem } from '@/constants/foodItems'
import { CELEB_LINES, type Celebrity } from '@/constants/celebLines'
import { CATEGORY_LIST, type Category } from '@/constants/categories'
import apiClient from '@/services/api/client'
import { productsAPI } from '@/services/api'
import type { Category as CategoryType } from '@/types/product'
import TutorialStepHeader from '@/components/tutorial/TutorialStepHeader.vue'
import FoodSelectGrid from '@/components/tutorial/FoodSelectGrid.vue'
import SummaryCard from '@/components/tutorial/SummaryCard.vue'
import SkipTutorialButton from '@/components/tutorial/SkipTutorialButton.vue'

const props = defineProps<{
  open?: boolean
  forceOpen?: boolean
  mode?: 'AUTO' | 'MANUAL'
}>()

const emit = defineEmits<{
  (e: 'tutorialCompleted'): void
  (e: 'close'): void
}>()

const router = useRouter()

const {
  step,
  gender,
  tutorialMode,
  selectedCelebrity,
  scores,
  addScore,
  resetTutorial,
} = useTutorialState()

const { buildQ4Items, buildQ5Items, buildQ6Items, buildQ7Items } = useTutorialFlow()

type Gender = 'MALE' | 'FEMALE'
type TutorialMode = 'CELEB' | 'PARENT'

const currentMode = computed(() => props.mode ?? 'AUTO')
const isManual = computed(() => currentMode.value === 'MANUAL')

const selectedDislikeIds = ref<string[]>([])
const mainCategory = ref<Category | null>(null)
const secondaryCategory = ref<Category | null>(null)

const STORAGE_KEY = 'tutorialCompleted'
const tutorialCompleted = ref<boolean>(false)
const scrollArea = ref<HTMLElement | null>(null)

const isOpen = computed(() => {
  if (props.forceOpen) return true
  if (isManual.value) {
    return props.open ?? false
  }
  const baseOpen = props.open ?? true
  if (tutorialCompleted.value) return false
  return baseOpen
})

const celebrityNameMap: Record<Celebrity, string> = {
  CHA_EUNWOO: '차은우',
  KARINA: '카리나',
}

const buildScorePayload = (): Record<Category, number> => {
  const payload = {} as Record<Category, number>
  for (const category of CATEGORY_LIST) {
    payload[category] = scores[category]
  }
  return payload
}

const saveScoresToServer = async () => {
  // Backend guide: POST /users/tutorial/complete (overwrite=true for reset) or POST /users/tutorial/reset
  try {
    await apiClient.post('/users/tutorial/complete', {
      scores: buildScorePayload(),
      overwrite: currentMode.value === 'MANUAL',
    })
  } catch (error) {
    console.error('Failed to save tutorial scores', error)
  }
}

const markCompleted = () => {
  tutorialCompleted.value = true
  if (typeof window !== 'undefined') {
    localStorage.setItem(STORAGE_KEY, 'true')
  }
}

const celebrityDisplayName = computed(() =>
  selectedCelebrity.value ? celebrityNameMap[selectedCelebrity.value] : '',
)

const q3Items = computed(() => FOOD_ITEMS)
const q4Items = computed(() => buildQ4Items())
const q5Items = computed(() =>
  buildQ5Items(mainCategory.value ? [mainCategory.value] : []),
)
const q6Items = computed(() => buildQ6Items())
const q7Items = computed(() =>
  buildQ7Items(secondaryCategory.value ? [secondaryCategory.value] : []),
)

const progress = computed(() => (step.value / 9) * 100)

const selectedDislikeLabels = computed(() =>
  selectedDislikeIds.value
    .map((id) => FOOD_ITEMS.find((item) => item.id === id)?.label)
    .filter(Boolean) as string[],
)

const endingMain = computed(() => {
  if (tutorialMode.value === 'CELEB') {
    const celeb = selectedCelebrity.value ?? 'CHA_EUNWOO'
    return CELEB_LINES[celeb]['7'].ending
  }
  return '이제 부모님과 함께 장보기 준비 완료!'
})

const endingSub = computed(() =>
  tutorialMode.value === 'CELEB'
    ? '추천을 바로 준비했어요. 함께 담으러 가볼까요?'
    : '편하게 담으실 수 있도록 취향에 맞춰 준비했어요.',
)

const selectGender = (value: Gender) => {
  gender.value = value
  selectedCelebrity.value = value === 'FEMALE' ? 'CHA_EUNWOO' : 'KARINA'
  step.value = 2
}

const selectMode = (mode: TutorialMode) => {
  tutorialMode.value = mode
  step.value = 3
}

const handleDislikeSelect = (item: FoodItem) => {
  const index = selectedDislikeIds.value.indexOf(item.id)
  if (index > -1) {
    // 이미 선택된 경우 토글하여 제거
    selectedDislikeIds.value = selectedDislikeIds.value.filter(id => id !== item.id)
    // 점수 복구 (제외 취소 - 초기값 0으로 복구)
    scores[item.category] = 0
  } else {
    // 선택되지 않은 경우 추가
    selectedDislikeIds.value = [...selectedDislikeIds.value, item.id]
    addScore(item.category, -1)
  }
}

const handleQ4Select = (item: FoodItem) => {
  mainCategory.value = item.category
  addScore(item.category, 4)
  step.value = 5
}

const handleQ5Select = (item: FoodItem) => {
  addScore(item.category, 3)
  step.value = 6
}

const handleQ6Select = (item: FoodItem) => {
  secondaryCategory.value = item.category
  addScore(item.category, 2)
  step.value = 7
}

const handleQ7Select = (item: FoodItem) => {
  addScore(item.category, 1)
  step.value = 8
}

const handleSummaryComplete = () => {
  step.value = 9
}

const handleComplete = async () => {
  await saveScoresToServer()
  markCompleted()
  emit('tutorialCompleted')
  emit('close')

  // 가장 높은 점수를 받은 카테고리 찾기
  let topCategory: Category | null = null
  let topScore = -Infinity

  for (const category of CATEGORY_LIST) {
    const score = scores[category]
    if (score > topScore) {
      topScore = score
      topCategory = category
    }
  }

  // 카테고리 ID 찾기
  let categoryId: number | null = null
  if (topCategory) {
    try {
      const { data } = await productsAPI.getCategories()
      const categoryNameMap: Record<string, string> = {
        GRAIN: '쌀/잡곡',
        NOODLE_FLOUR: '면/가루/베이커리/제빵',
        VEGETABLE: '채소/샐러드/버섯/나물',
        FRUIT: '과일',
        BEAN_EGG: '두부/콩/계란',
        MEAT: '육류',
        SEAFOOD: '수산물/해산물/건어물',
        DAIRY: '우유/유제품',
        KIMCHI_SIDE: '김치/반찬/절임',
        SEASONING_SAUCE_OIL: '양념/조미/소스/오일',
        NUT_DRY_ETC: '견과/건과/간식',
        DRINK: '음료',
        INSTANT_FOOD: '라면/간편식품/통조림',
      }
      const targetName = categoryNameMap[topCategory]
      if (targetName && data.results) {
        const matchedCategory = data.results.find((cat: CategoryType) => cat.name === targetName)
        if (matchedCategory) {
          categoryId = matchedCategory.id
        }
      }
    } catch (error) {
      console.error('카테고리 목록 조회 실패:', error)
    }
  }

  // 메인페이지로 이동
  const query: Record<string, string> = {}
  if (categoryId) {
    query.category_id = String(categoryId)
  }

  // 현재 페이지가 홈이 아니면 홈으로 이동
  if (router.currentRoute.value.name !== 'home') {
    router.push({ name: 'home', query })
  } else {
    // 이미 홈이면 query만 업데이트
    router.push({ query })
  }

  // 스크롤 함수 호출 (약간의 지연 후)
  await nextTick()
  setTimeout(() => {
    const el = document.getElementById('recommend')
    if (el) {
      const header = document.querySelector('header') as HTMLElement | null
      const catNav = document.getElementById('sticky-nav')
      const headerHeight = header?.offsetHeight ?? 0
      const navHeight = catNav?.offsetHeight ?? 0
      const stickyHeaderHeight = headerHeight ? Math.min(headerHeight, 72) : 72
      const offset = stickyHeaderHeight + navHeight + 8

      const top = el.getBoundingClientRect().top + window.scrollY - offset
      
      const smoothScrollTo = (targetY: number, duration = 1200) => {
        const startY = window.scrollY
        const delta = targetY - startY
        if (delta === 0) return

        const startTime = performance.now()
        const easeInOut = (t: number) => (t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t)

        const step = (now: number) => {
          const elapsed = now - startTime
          const progress = Math.min(1, elapsed / duration)
          const eased = easeInOut(progress)
          window.scrollTo({ top: startY + delta * eased })
          if (progress < 1) {
            requestAnimationFrame(step)
          }
        }

        requestAnimationFrame(step)
      }

      smoothScrollTo(top, 1200)
    }
  }, 100)
}

const handleSkip = () => {
  markCompleted()
  emit('tutorialCompleted')
  emit('close')
}

const handleClose = () => {
  emit('close')
}

const goToStep = (next: number) => {
  step.value = next
}

watch(
  () => isOpen.value,
  (value) => {
    if (value) {
      resetTutorial()
      selectedDislikeIds.value = []
      mainCategory.value = null
      secondaryCategory.value = null
      if (isManual.value) {
        step.value = 1
      }
    }
  },
)

watch(
  () => step.value,
  async () => {
    await nextTick()
    scrollArea.value?.scrollTo({ top: 0, behavior: 'auto' })
  },
)

onMounted(() => {
  const stored = typeof window !== 'undefined' ? localStorage.getItem(STORAGE_KEY) : null
  tutorialCompleted.value = stored === 'true'
  resetTutorial()
})
</script>
