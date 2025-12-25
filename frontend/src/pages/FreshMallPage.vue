<template>
  <main class="bg-gray-50 min-h-screen pt-28 pb-16">
    <section class="max-w-6xl mx-auto px-4 space-y-10">
      <header class="space-y-4">
        <p class="text-sm font-semibold text-brand-600">Fresh 몰</p>
        <div class="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div class="space-y-2">
            <h1 class="text-3xl font-display font-bold text-gray-900">동네 셀러의 신선식품을 한눈에</h1>
            <p class="text-gray-600">배송/온도/원산지 필터와 셀러 스토리로 신뢰도를 확인하세요.</p>
          </div>
          <div class="flex flex-wrap gap-2">
            <button
              v-for="opt in sortOptions"
              :key="opt"
              class="px-4 py-2 rounded-full border text-sm font-semibold transition-colors"
              :class="opt === sortOption ? 'bg-brand-600 text-white border-brand-600' : 'bg-white text-gray-700 border-gray-200 hover:border-brand-200 hover:text-brand-600'"
              @click="sortOption = opt"
            >
              {{ opt }}
            </button>
          </div>
        </div>
      </header>

      <section class="space-y-4">
        <div class="flex items-center justify-between">
          <h2 class="text-xl font-bold text-gray-900">셀러 스토리</h2>
          <button class="text-sm font-semibold text-brand-700 hover:text-brand-800" @click="goToAllSellerProducts">모두 보기</button>
        </div>
        <div v-if="sellerStoriesLoading" class="story-state">브랜드 제휴 스토리를 불러오는 중입니다.</div>
        <div v-else-if="sellerStoriesError" class="story-state error">{{ sellerStoriesError }}</div>
        <div v-else-if="!sellerStories.length" class="story-state">등록된 브랜드 제휴 스토리가 없습니다.</div>
        <div v-else class="story-row">
          <article
            v-for="story in sellerStories"
            :key="story.id"
            class="story-card"
          >
            <div class="story-cover">
              <img
                :src="story.banner || DEFAULT_STORY_BANNER"
                :alt="story.name"
                @error="handleStoryBannerError"
              >
              <div class="story-logo">
                <img
                  :src="story.logo || DEFAULT_STORY_LOGO"
                  :alt="`${story.name} 로고`"
                  @error="handleStoryLogoError"
                >
              </div>
            </div>
            <div class="story-body">
              <p class="story-name">{{ story.name }}</p>
              <p class="story-desc line-clamp-2">{{ story.desc }}</p>
              <div class="story-actions">
                <button
                  class="story-link"
                  type="button"
                  :disabled="!story.slug"
                  @click="goToBrandStory(story.slug)"
                >
                  스토어 보기
                </button>
              </div>
            </div>
          </article>
        </div>
      </section>

      <div v-if="loading" class="flex items-center justify-center py-16 text-gray-500">로딩 중...</div>
      <div v-else-if="fetchError" class="flex items-center justify-center py-16 text-red-500">{{ fetchError }}</div>
      <div v-else-if="!visibleProducts.length" class="flex items-center justify-center py-16 text-gray-500">
        등록된 상품이 없습니다.
      </div>
      <div v-else class="grid gap-6 grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
        <ProductCard
          v-for="product in visibleProducts"
          :key="product.id"
          :product="product"
          label="FRESH"
        />
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import type { Product } from '@/types/product'
import ProductCard from '@/components/ui/ProductCard.vue'
import { productsAPI, sellersAPI } from '@/services/api'

const router = useRouter()

type FreshProduct = Product
type SellerStory = {
  id: string
  name: string
  desc: string
  logo: string
  banner: string
  slug: string
}

const sortOptions = ['신규 셀러', '판매순', '리뷰순']
const sortOption = ref('신규 셀러')

const DEFAULT_STORY_BANNER =
  'https://images.unsplash.com/photo-1504674900247-0877df9cc836?auto=format&fit=crop&w=1200&q=80'
const DEFAULT_STORY_LOGO = '/images/default-brand.svg'

const sellerStories = ref<SellerStory[]>([])
const sellerStoriesLoading = ref(false)
const sellerStoriesError = ref<string | null>(null)

const freshProducts = ref<FreshProduct[]>([])
const loading = ref(false)
const fetchError = ref<string | null>(null)

const sortedProducts = computed(() => {
  const recentFirst = (a: FreshProduct, b: FreshProduct) =>
    new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  const oneMonthAgo = (() => {
    const base = new Date()
    base.setMonth(base.getMonth() - 1)
    return base.getTime()
  })()

  if (sortOption.value === '신규 셀러') {
    return freshProducts.value
      .filter((p) => {
        const created = new Date(p.created_at).getTime()
        return !Number.isNaN(created) && created >= oneMonthAgo
      })
      .sort(recentFirst)
  }

  if (sortOption.value === '판매순') {
    // 실제 판매량(order_event_count) 기준 정렬
    return [...freshProducts.value].sort((a, b) => {
      const salesDiff = (b.order_event_count || 0) - (a.order_event_count || 0)
      if (salesDiff !== 0) return salesDiff
      return recentFirst(a, b)
    })
  }
  if (sortOption.value === '리뷰순') {
    return [...freshProducts.value].sort((a, b) => {
      const reviewDiff = (b.review_count || 0) - (a.review_count || 0)
      if (reviewDiff !== 0) return reviewDiff
      return recentFirst(a, b)
    })
  }
  // 신규 셀러: 최근 등록 순
  return [...freshProducts.value].sort(recentFirst)
})

const visibleProducts = computed(() => sortedProducts.value.slice(0, 8))

const goToBrandStory = (slug: string) => {
  if (!slug) return
  router.push(`/brands/${slug}`)
}

const goToAllSellerProducts = () => {
  router.push({ name: 'products', query: { product_type: 'seller' } })
}

const handleStoryLogoError = (event: Event) => {
  const target = event.target as HTMLImageElement
  target.src = DEFAULT_STORY_LOGO
}

const handleStoryBannerError = (event: Event) => {
  const target = event.target as HTMLImageElement
  target.src = DEFAULT_STORY_BANNER
}

const loadSellerStories = async () => {
  sellerStoriesLoading.value = true
  sellerStoriesError.value = null
  try {
    const { data } = await sellersAPI.getSellers()
    const list = (data.results || data || []) as any[]

    sellerStories.value = list
      .filter(
        (seller: any) =>
          !!seller?.brand_name && !!seller?.brand_description && !!(seller?.brand_slug || seller?.slug)
      )
      .map((seller: any, index: number) => ({
        id: String(seller.id ?? seller.brand_slug ?? index),
        name: seller.brand_name,
        desc: seller.brand_description,
        logo: seller.brand_logo_url || DEFAULT_STORY_LOGO,
        banner: seller.brand_banner_url || seller.brand_logo_url || DEFAULT_STORY_BANNER,
        slug: seller.brand_slug || seller.slug || '',
      }))
  } catch (error) {
    console.error('Failed to load seller stories:', error)
    sellerStoriesError.value = '셀러 스토리를 불러오지 못했습니다.'
    sellerStories.value = []
  } finally {
    sellerStoriesLoading.value = false
  }
}

const fetchFreshProducts = async () => {
  loading.value = true
  fetchError.value = null
  try {
    const { data } = await productsAPI.getProducts({
      product_type: 'seller',
      page_size: 24,
      ordering: '-created_at',
    })
    freshProducts.value = data.results
  } catch (error) {
    console.error('Failed to load seller products:', error)
    fetchError.value = '상품을 불러오는 데 실패했습니다.'
    freshProducts.value = []
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchFreshProducts()
  loadSellerStories()
})
</script>

<style scoped>
.chip {
  @apply px-4 py-2 rounded-full border text-sm font-medium transition-colors;
}
.story-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 14px;
}
.story-card {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 16px;
  padding: 12px;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.06);
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
  overflow: hidden;
}
.story-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 16px 40px rgba(0, 0, 0, 0.08);
  border-color: #c7ead8;
}
.story-cover {
  position: relative;
  height: 148px;
  border-radius: 12px;
  overflow: hidden;
  background: linear-gradient(135deg, #f8fafc 0%, #eef2ff 100%);
}
.story-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.story-cover::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, rgba(17, 24, 39, 0.15) 0%, rgba(17, 24, 39, 0.45) 100%);
  pointer-events: none;
}
.story-logo {
  position: absolute;
  left: 14px;
  bottom: 14px;
  width: 56px;
  height: 56px;
  border-radius: 14px;
  background: white;
  border: 3px solid #fff;
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.12);
  overflow: hidden;
  display: grid;
  place-items: center;
}
.story-logo img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.story-body {
  margin-top: 14px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.story-name {
  font-size: 1rem;
  font-weight: 800;
  color: #111827;
}
.story-desc {
  font-size: 0.9rem;
  color: #4b5563;
  min-height: 44px;
}
.story-actions {
  margin-top: 4px;
}
.story-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 0.5rem 0.9rem;
  border-radius: 999px;
  border: 1px solid #c7ead8;
  background: #e6f4ec;
  color: #0f5132;
  font-weight: 700;
  font-size: 0.85rem;
  transition: background 0.2s ease, transform 0.2s ease;
}
.story-link:hover {
  background: #d7f0e3;
  transform: translateY(-1px);
}
.story-link:disabled {
  opacity: 0.55;
  cursor: not-allowed;
  transform: none;
}
.story-state {
  padding: 1rem 1.25rem;
  background: #f8fafc;
  border: 1px dashed #d1d5db;
  border-radius: 12px;
  color: #4b5563;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.story-state.error {
  background: #fff5f5;
  border-color: #fecdd3;
  color: #b91c1c;
}
</style>
