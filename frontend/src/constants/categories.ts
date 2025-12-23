export const CATEGORY_LIST = [
  'GRAIN',
  'NOODLE_FLOUR',
  'VEGETABLE',
  'FRUIT',
  'BEAN_EGG',
  'MEAT',
  'SEAFOOD',
  'DAIRY',
  'KIMCHI_SIDE',
  'SEASONING_SAUCE_OIL',
  'NUT_DRY_ETC',
  'DRINK',
  'INSTANT_FOOD',
] as const;

export type Category = typeof CATEGORY_LIST[number];
