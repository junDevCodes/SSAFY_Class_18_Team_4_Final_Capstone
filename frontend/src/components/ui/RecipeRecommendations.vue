<template>
  <section class="bg-gradient-to-br from-orange-50 to-amber-50 border border-orange-100 rounded-xl shadow-sm overflow-hidden">
    <!-- 헤더 -->
    <div class="flex items-start justify-between px-4 pt-4">
      <div class="space-y-1">
        <div class="flex items-center gap-2">
          <ChefHat :size="18" class="text-orange-500" />
          <p class="text-[11px] font-semibold text-orange-600 tracking-tight uppercase">레시피 추천</p>
        </div>
        <p class="text-sm text-gray-600">장바구니 재료로 만들 수 있는 요리예요</p>
      </div>
      <div class="flex items-center gap-2">
        <!-- 토글 버튼 -->
        <button
          type="button"
          :aria-label="recipeRecommendationEnabled ? '레시피 추천 끄기' : '레시피 추천 켜기'"
          class="p-2 rounded-full border text-gray-500 hover:text-gray-800 transition-colors"
          :class="recipeRecommendationEnabled
            ? 'border-orange-300 bg-orange-100 text-orange-600'
            : 'border-gray-200 bg-white'"
          @click="cartStore.toggleRecipeRecommendation"
        >
          <Power :size="16" />
        </button>
        <!-- 네비게이션 -->
        <button
          type="button"
          :aria-label="'이전 레시피'"
          class="p-2 rounded-full border border-gray-200 text-gray-500 hover:text-gray-800 hover:border-gray-300 disabled:opacity-40 disabled:cursor-not-allowed transition-colors bg-white"
          :disabled="!hasPrev || recipeLoading"
          @click="cartStore.prevRecipe"
        >
          <ChevronLeft :size="18" />
        </button>
        <button
          type="button"
          :aria-label="'다음 레시피'"
          class="p-2 rounded-full border border-gray-200 text-gray-500 hover:text-gray-800 hover:border-gray-300 disabled:opacity-40 disabled:cursor-not-allowed transition-colors bg-white"
          :disabled="!hasNext || recipeLoading"
          @click="cartStore.nextRecipe"
        >
          <ChevronRight :size="18" />
        </button>
      </div>
    </div>

    <!-- 콘텐츠 -->
    <div class="px-4 pb-4">
      <!-- 비활성화 상태 -->
      <div v-if="!recipeRecommendationEnabled" class="mt-4 py-8 text-center text-sm text-gray-400">
        <Power :size="24" class="mx-auto mb-2 opacity-50" />
        <p>레시피 추천이 꺼져 있어요</p>
        <button
          type="button"
          class="mt-2 text-orange-600 font-medium hover:text-orange-500"
          @click="cartStore.toggleRecipeRecommendation"
        >
          켜기
        </button>
      </div>

      <!-- 로딩 상태 -->
      <div v-else-if="recipeLoading" class="mt-4 space-y-4">
        <div class="h-24 rounded-lg bg-orange-100/50 border border-orange-200 animate-pulse" />
        <div class="grid grid-cols-3 gap-3">
          <div v-for="n in 3" :key="`skeleton-${n}`" class="h-[120px] rounded-lg bg-orange-100/50 border border-orange-200 animate-pulse" />
        </div>
      </div>

      <!-- 에러 상태 -->
      <div v-else-if="recipeError" class="mt-4 flex items-center justify-between text-xs text-gray-500">
        <span>{{ recipeError }}</span>
        <button type="button" class="text-orange-600 font-semibold hover:text-orange-500" @click="cartStore.fetchRecipeRecommendations()">
          다시 시도
        </button>
      </div>

      <!-- 빈 상태 (재료는 인식됐지만 레시피 없음) -->
      <div v-else-if="!hasRecipeRecommendations && cartIngredients.length > 0" class="mt-4 py-6 text-center text-sm text-gray-500">
        <UtensilsCrossed :size="24" class="mx-auto mb-2 opacity-50" />
        <p>매칭되는 레시피가 없어요</p>
        <div class="mt-2 text-xs text-gray-400">
          <span>인식된 재료: </span>
          <span class="text-orange-500">{{ cartIngredients.join(', ') }}</span>
        </div>
        <p class="text-xs mt-2 text-gray-400">다른 재료를 더 담아보세요</p>
      </div>

      <!-- 빈 상태 (재료 인식 못함) -->
      <div v-else-if="!hasRecipeRecommendations" class="mt-4 py-8 text-center text-sm text-gray-400">
        <UtensilsCrossed :size="24" class="mx-auto mb-2 opacity-50" />
        <p>요리 재료를 담아보세요</p>
        <p class="text-xs mt-1">육류, 채소, 해산물 등을 담으면 레시피를 추천해드려요</p>
      </div>

      <!-- 레시피 추천 콘텐츠 -->
      <div v-else-if="selectedRecipe" class="mt-4 space-y-4">
        <!-- 레시피 정보 카드 -->
        <div
          class="bg-white rounded-lg border p-4 shadow-sm"
          :class="selectedRecipe.is_dish_matched
            ? 'border-amber-400 ring-1 ring-amber-200'
            : 'border-orange-200'"
        >
          <!-- 요리명 매칭 배지 -->
          <div v-if="selectedRecipe.matched_dish" class="mb-2">
            <span class="inline-flex items-center px-2 py-1 rounded-full text-[10px] font-semibold bg-amber-100 text-amber-700 border border-amber-300">
              <Sparkles :size="10" class="mr-1" />
              {{ selectedRecipe.matched_dish }} 재료 감지!
            </span>
          </div>

          <div class="flex items-start justify-between">
            <div class="flex-1">
              <h3 class="font-bold text-gray-900 text-base">{{ selectedRecipe.name }}</h3>
              <p v-if="selectedRecipe.title" class="text-xs text-gray-500 mt-0.5">{{ selectedRecipe.title }}</p>
            </div>
            <div class="text-right">
              <div class="flex items-center gap-1">
                <span class="text-2xl font-bold text-orange-500">{{ Math.round(selectedRecipe.match_ratio * 100) }}</span>
                <span class="text-xs text-gray-500">%</span>
              </div>
              <p class="text-[10px] text-gray-400">재료 일치</p>
            </div>
          </div>

          <!-- 매칭 재료 -->
          <div class="mt-3 flex flex-wrap gap-1.5">
            <span
              v-for="ing in selectedRecipe.matched_ingredients.slice(0, 5)"
              :key="ing"
              class="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] bg-green-100 text-green-700"
            >
              <Check :size="10" class="mr-0.5" />
              {{ ing }}
            </span>
            <span
              v-if="selectedRecipe.matched_ingredients.length > 5"
              class="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] bg-gray-100 text-gray-500"
            >
              +{{ selectedRecipe.matched_ingredients.length - 5 }}
            </span>
          </div>

          <!-- 부족 재료 -->
          <div v-if="selectedRecipe.gap_count > 0" class="mt-2 flex flex-wrap gap-1.5">
            <span
              v-for="ing in selectedRecipe.gap_ingredients.slice(0, 4)"
              :key="ing"
              class="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] bg-orange-100 text-orange-700"
            >
              <ShoppingCart :size="10" class="mr-0.5" />
              {{ ing }}
            </span>
            <span
              v-if="selectedRecipe.gap_ingredients.length > 4"
              class="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] bg-gray-100 text-gray-500"
            >
              +{{ selectedRecipe.gap_ingredients.length - 4 }}
            </span>
          </div>
        </div>

        <!-- 추천 상품 (부족 재료) -->
        <div v-if="selectedRecipe.recommended_products.length > 0">
          <p class="text-xs font-medium text-gray-600 mb-2">
            <ShoppingBasket :size="14" class="inline mr-1" />
            이 재료만 더 있으면 완성!
          </p>
          <div class="grid grid-cols-3 gap-2">
            <article
              v-for="product in selectedRecipe.recommended_products.slice(0, 3)"
              :key="product.product_id"
              class="group relative rounded-lg bg-white border border-gray-200 hover:border-orange-400 hover:shadow-md transition-all overflow-hidden"
            >
              <div class="aspect-square overflow-hidden bg-gray-50">
                <img
                  :src="product.main_image || '/images/default-product.svg'"
                  :alt="product.name"
                  loading="lazy"
                  class="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
                />
              </div>
              <div class="p-2 space-y-1">
                <span class="inline-block px-1.5 py-0.5 rounded text-[9px] font-medium bg-orange-100 text-orange-600">
                  {{ product.ingredient }}
                </span>
                <p class="text-[10px] text-gray-700 leading-snug line-clamp-2">{{ product.name }}</p>
                <div class="flex items-center justify-between">
                  <span class="font-bold text-xs text-gray-900">{{ formatPrice(product.price) }}</span>
                  <button
                    type="button"
                    class="w-6 h-6 inline-flex items-center justify-center rounded-full bg-orange-500 text-white hover:bg-orange-600 transition-colors"
                    :class="isAdding(product.product_id) ? 'opacity-60 cursor-not-allowed' : ''"
                    :disabled="isAdding(product.product_id)"
                    @click.stop="addGapProduct(product.product_id)"
                  >
                    <Plus :size="14" stroke-width="2.5" />
                  </button>
                </div>
              </div>
            </article>
          </div>
        </div>

        <!-- 슬라이드 인디케이터 -->
        <div v-if="recipeRecommendations.length > 1" class="flex justify-center gap-1.5 mt-3">
          <button
            v-for="(_, idx) in recipeRecommendations"
            :key="`dot-${idx}`"
            type="button"
            class="h-1.5 rounded-full transition-all"
            :class="idx === selectedRecipeIndex
              ? 'w-4 bg-orange-500'
              : 'w-1.5 bg-gray-300 hover:bg-gray-400'"
            @click="cartStore.selectRecipe(idx)"
          />
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import {
  ChefHat,
  ChevronLeft,
  ChevronRight,
  Plus,
  Power,
  Check,
  ShoppingCart,
  ShoppingBasket,
  UtensilsCrossed,
  Sparkles,
} from 'lucide-vue-next'
import { computed, ref, onMounted, watch } from 'vue'
import { useCartStore } from '@/stores/cart'
import { useUIStore } from '@/stores/ui'
import { formatPrice } from '@/utils/formatters'

const cartStore = useCartStore()
const uiStore = useUIStore()

const addingIds = ref<number[]>([])

// Store에서 상태 가져오기
const recipeRecommendations = computed(() => cartStore.recipeRecommendations)
const recipeLoading = computed(() => cartStore.recipeLoading)
const recipeError = computed(() => cartStore.recipeError)
const recipeRecommendationEnabled = computed(() => cartStore.recipeRecommendationEnabled)
const selectedRecipe = computed(() => cartStore.selectedRecipe)
const selectedRecipeIndex = computed(() => cartStore.selectedRecipeIndex)
const hasRecipeRecommendations = computed(() => cartStore.hasRecipeRecommendations)
const cartIngredients = computed(() => cartStore.cartIngredients)

// 네비게이션
const hasPrev = computed(() => selectedRecipeIndex.value > 0)
const hasNext = computed(() => selectedRecipeIndex.value < recipeRecommendations.value.length - 1)

// Gap 상품 추가
const addGapProduct = async (productId: number) => {
  if (addingIds.value.includes(productId)) return
  addingIds.value = [...addingIds.value, productId]

  try {
    await cartStore.addGapProductToCart(productId, 1)
    uiStore.showToast('장바구니에 담았어요!')
  } catch (err) {
    console.error('Gap 상품 추가 실패:', err)
    uiStore.showToast('상품 담기에 실패했어요.')
  } finally {
    addingIds.value = addingIds.value.filter(id => id !== productId)
  }
}

const isAdding = (id: number) => addingIds.value.includes(id)

// 장바구니 아이템 변경 시 레시피 추천 갱신
watch(
  () => cartStore.items.length,
  () => {
    if (cartStore.recipeRecommendationEnabled) {
      cartStore.fetchRecipeRecommendations()
    }
  }
)

// 초기 로드
onMounted(() => {
  if (cartStore.items.length > 0 && cartStore.recipeRecommendationEnabled) {
    cartStore.fetchRecipeRecommendations()
  }
})
</script>
