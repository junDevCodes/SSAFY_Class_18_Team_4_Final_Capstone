import type { Category } from './categories'

export type FoodItem = {
  id: string
  label: string
  emoji: string
  category: Category
}

export const FOOD_ITEMS: FoodItem[] = [
  // GRAIN
  { id: 'grain_rice', label: '쌀', emoji: '🍚', category: 'GRAIN' },
  { id: 'grain_barley', label: '보리', emoji: '🌾', category: 'GRAIN' },
  { id: 'grain_mixed', label: '잡곡', emoji: '🥣', category: 'GRAIN' },

  // NOODLE_FLOUR
  { id: 'noodle_pasta', label: '파스타', emoji: '🍝', category: 'NOODLE_FLOUR' },
  { id: 'noodle_udon', label: '우동', emoji: '🍜', category: 'NOODLE_FLOUR' },
  { id: 'flour_bread', label: '빵', emoji: '🥖', category: 'NOODLE_FLOUR' },

  // VEGETABLE
  { id: 'veg_onion', label: '양파', emoji: '🧅', category: 'VEGETABLE' },
  { id: 'veg_potato', label: '감자', emoji: '🥔', category: 'VEGETABLE' },
  { id: 'veg_tomato', label: '토마토', emoji: '🍅', category: 'VEGETABLE' },

  // FRUIT
  { id: 'fruit_banana', label: '바나나', emoji: '🍌', category: 'FRUIT' },
  { id: 'fruit_apple', label: '사과', emoji: '🍎', category: 'FRUIT' },
  { id: 'fruit_tangerine', label: '귤', emoji: '🍊', category: 'FRUIT' },

  // BEAN_EGG
  { id: 'bean_tofu', label: '두부', emoji: '🍱', category: 'BEAN_EGG' },
  { id: 'bean_chickpea', label: '병아리콩', emoji: '🫘', category: 'BEAN_EGG' },
  { id: 'egg', label: '달걀', emoji: '🥚', category: 'BEAN_EGG' },

  // MEAT
  { id: 'meat_beef', label: '소고기', emoji: '🥩', category: 'MEAT' },
  { id: 'meat_pork', label: '돼지고기', emoji: '🥓', category: 'MEAT' },
  { id: 'meat_chicken', label: '닭가슴살', emoji: '🍗', category: 'MEAT' },

  // SEAFOOD
  { id: 'seafood_salmon', label: '연어', emoji: '🐟', category: 'SEAFOOD' },
  { id: 'seafood_shrimp', label: '새우', emoji: '🍤', category: 'SEAFOOD' },
  { id: 'seafood_squid', label: '오징어', emoji: '🦑', category: 'SEAFOOD' },

  // DAIRY
  { id: 'dairy_milk', label: '우유', emoji: '🥛', category: 'DAIRY' },
  { id: 'dairy_cheese', label: '치즈', emoji: '🧀', category: 'DAIRY' },
  { id: 'dairy_yogurt', label: '요거트', emoji: '🥣', category: 'DAIRY' },

  // KIMCHI_SIDE
  { id: 'kimchi_cabbage', label: '배추김치', emoji: '🥬', category: 'KIMCHI_SIDE' },
  { id: 'kimchi_radish', label: '깍두기', emoji: '🟧', category: 'KIMCHI_SIDE' },
  { id: 'side_spinach', label: '시금치나물', emoji: '🌿', category: 'KIMCHI_SIDE' },

  // SEASONING_SAUCE_OIL
  { id: 'seasoning_soy', label: '간장', emoji: '🧂', category: 'SEASONING_SAUCE_OIL' },
  { id: 'seasoning_gochujang', label: '고추장', emoji: '🌶️', category: 'SEASONING_SAUCE_OIL' },
  { id: 'oil_olive', label: '올리브유', emoji: '🫒', category: 'SEASONING_SAUCE_OIL' },

  // NUT_DRY_ETC
  { id: 'nut_almond', label: '아몬드', emoji: '🥜', category: 'NUT_DRY_ETC' },
  { id: 'nut_walnut', label: '호두', emoji: '🌰', category: 'NUT_DRY_ETC' },
  { id: 'dry_raisin', label: '건포도', emoji: '🍇', category: 'NUT_DRY_ETC' },

  // DRINK
  { id: 'drink_water', label: '생수', emoji: '💧', category: 'DRINK' },
  { id: 'drink_coffee', label: '커피', emoji: '☕', category: 'DRINK' },
  { id: 'drink_sparkling', label: '탄산음료', emoji: '🥤', category: 'DRINK' },

  // INSTANT_FOOD
  { id: 'instant_ramen', label: '라면', emoji: '🍜', category: 'INSTANT_FOOD' },
  { id: 'instant_frozen_pizza', label: '냉동피자', emoji: '🍕', category: 'INSTANT_FOOD' },
  { id: 'instant_nugget', label: '치킨너겟', emoji: '🍗', category: 'INSTANT_FOOD' },
] as const
