import { reactive, ref } from 'vue'
import { CATEGORY_LIST, type Category } from '@/constants/categories'
import type { Celebrity } from '@/constants/celebLines'

type Gender = 'MALE' | 'FEMALE'
type TutorialMode = 'CELEB' | 'PARENT'
type ScoreState = Record<Category, number>

const EXCLUDE_SCORE = -1
const SCORE_MAX = 10
const SKIP_DEFAULT_SCORE = 5

const createScoreState = (initialScore = 0): ScoreState => {
  const base = {} as ScoreState
  for (const category of CATEGORY_LIST) {
    base[category] = initialScore
  }
  return base
}

const scores = reactive<ScoreState>(createScoreState())
const step = ref<number>(1)
const gender = ref<Gender | null>(null)
const tutorialMode = ref<TutorialMode | null>(null)
const selectedCelebrity = ref<Celebrity | null>(null)

const addScore = (category: Category, value: number): void => {
  if (value === EXCLUDE_SCORE) {
    scores[category] = EXCLUDE_SCORE
    return
  }

  if (scores[category] === EXCLUDE_SCORE) return

  const nextScore = scores[category] + value
  scores[category] = nextScore > SCORE_MAX ? SCORE_MAX : nextScore
}

const resetTutorial = (): void => {
  step.value = 1
  gender.value = null
  tutorialMode.value = null
  selectedCelebrity.value = null
  const freshScores = createScoreState()
  for (const category of CATEGORY_LIST) {
    scores[category] = freshScores[category]
  }
}

const setSkipDefaultScores = (): void => {
  for (const category of CATEGORY_LIST) {
    if (scores[category] === EXCLUDE_SCORE) continue
    scores[category] = SKIP_DEFAULT_SCORE
  }
}

const startManualTutorial = (): void => {
  resetTutorial()
}

export const useTutorialState = () => ({
  step,
  gender,
  tutorialMode,
  selectedCelebrity,
  scores,
  addScore,
  resetTutorial,
  startManualTutorial,
  setSkipDefaultScores,
  EXCLUDE_SCORE,
  SCORE_MAX,
})
