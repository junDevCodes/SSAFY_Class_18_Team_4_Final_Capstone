import { FOOD_ITEMS, type FoodItem } from '@/constants/foodItems'
import type { Category } from '@/constants/categories'
import { useTutorialState } from '@/composables/useTutorialState'

type StepKey = 'Q4' | 'Q5' | 'Q6' | 'Q7'

const STEP_CATEGORY_MAP: Record<StepKey, Category[]> = {
  Q4: ['MEAT', 'SEAFOOD', 'VEGETABLE', 'FRUIT', 'NOODLE_FLOUR'],
  Q5: ['DAIRY', 'BEAN_EGG', 'GRAIN', 'SEASONING_SAUCE_OIL'],
  Q6: ['DRINK', 'INSTANT_FOOD', 'NUT_DRY_ETC', 'KIMCHI_SIDE'],
  Q7: ['GRAIN', 'BEAN_EGG', 'VEGETABLE', 'MEAT', 'SEAFOOD', 'FRUIT', 'DAIRY', 'INSTANT_FOOD'],
}

const dedupe = (categories: Category[]): Category[] => Array.from(new Set(categories))

export const useTutorialFlow = () => {
  const { scores, EXCLUDE_SCORE } = useTutorialState()

  const filterExcluded = (categories: Category[]): Category[] =>
    categories.filter((cat) => scores[cat] !== EXCLUDE_SCORE)

  const buildItems = (categories: Category[]): FoodItem[] => {
    const allowed = filterExcluded(dedupe(categories))
    return FOOD_ITEMS.filter((item) => allowed.includes(item.category))
  }

  const buildQ4Items = (): FoodItem[] => {
    return buildItems(STEP_CATEGORY_MAP.Q4)
  }

  const buildQ5Items = (previousCategories: Category[]): FoodItem[] => {
    const merged = [...STEP_CATEGORY_MAP.Q5, ...previousCategories]
    return buildItems(merged)
  }

  const buildQ6Items = (): FoodItem[] => {
    return buildItems(STEP_CATEGORY_MAP.Q6)
  }

  const buildQ7Items = (previousCategories: Category[]): FoodItem[] => {
    const merged = [...STEP_CATEGORY_MAP.Q7, ...previousCategories]
    return buildItems(merged)
  }

  return {
    buildQ4Items,
    buildQ5Items,
    buildQ6Items,
    buildQ7Items,
    STEP_CATEGORY_MAP,
  }
}
