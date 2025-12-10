<template>
  <header 
    :class="[
      'fixed w-full z-50 top-0 left-0 header-transition px-4 lg:px-12 flex items-center justify-between',
      headerToneClass
    ]"
  >
    <!-- Left: Logo -->
    <div class="flex items-center gap-4 lg:gap-12 shrink-0">
      <a href="#" class="flex items-center gap-1 group" @click.prevent="handleLogoClick">
        <span :class="['font-display font-bold text-3xl tracking-tight transition-colors', isLightMode ? 'text-brand-900' : 'text-white']">
          Sel<span :class="['inline-block transform italic ml-0.5', isLightMode ? 'text-brand-500' : 'text-brand-200']">F</span>
        </span>
      </a>
      
      <!-- Desktop Nav -->
      <nav class="hidden xl:flex gap-7 text-[15px] font-semibold tracking-tight" :class="isLightMode ? 'text-gray-700' : 'text-white/90'">
        <RouterLink
          v-for="link in navLinks"
          :key="link.name"
          :to="link.to"
          :class="linkClass(link.name)"
        >
          <template v-if="link.name === 'self-mall'">
            <span class="whitespace-nowrap">
              <span
                class="font-display font-bold text-[15px] transition-colors"
                :class="selfBaseClass(link.name)"
              >
                Sel
              </span><span
                class="font-display font-bold text-[15px] italic transition-colors -ml-1"
                :class="selfAccentClass(link.name)"
              >
                F
              </span>
            </span>
            <span
              class="ml-1 font-semibold transition-colors"
              :class="selfBaseClass(link.name)"
            >
              Mall
            </span>
          </template>
          <template v-else>
            {{ link.label }}
          </template>
        </RouterLink>
      </nav>
    </div>

    <!-- Center: Search Bar (Persistent) -->
    <div class="flex-1 max-w-xl mx-4 lg:mx-8 transition-all duration-300">
      <div class="relative group">
        <input 
          type="text" 
          placeholder="검색어를 입력해주세요" 
          v-model="searchQuery"
          @keyup.enter="handleSearch"
          :class="[
            'w-full py-2.5 pl-4 pr-10 rounded-full text-sm transition-all focus:outline-none focus:ring-2 focus:ring-brand-500/50',
            isLightMode 
              ? 'bg-gray-100 text-gray-900 placeholder-gray-400' 
              : 'bg-white/20 text-white placeholder-white/70 backdrop-blur-sm border border-white/30 focus:bg-white/30'
          ]"
        >
        <button :class="['absolute right-3 top-2.5 transition-colors', isLightMode ? 'text-gray-500' : 'text-white']" @click="handleSearch">
          <Search :size="20" />
        </button>
      </div>
    </div>

    <!-- Right: Actions -->
    <div class="flex items-center gap-3 shrink-0">
      <!-- Authenticated actions -->
      <template v-if="authStore.isAuthenticated">
        <button
          v-if="authStore.isSeller"
          @click="goTo('/seller/dashboard')"
          class="hidden md:block text-sm font-medium hover:opacity-70 transition-opacity mr-2"
          :class="isLightMode ? 'text-gray-600' : 'text-white'"
        >
          판매자 센터
        </button>
        <button
          @click="goTo('/mypage/profile')"
          class="hidden md:block text-sm font-medium hover:opacity-70 transition-opacity mr-2"
          :class="isLightMode ? 'text-gray-600' : 'text-white'"
        >
          마이페이지
        </button>
        <button
          @click="handleLogout"
          class="hidden md:block text-sm font-medium hover:opacity-70 transition-opacity mr-2"
          :class="isLightMode ? 'text-gray-600' : 'text-white'"
        >
          로그아웃
        </button>
        <button class="md:hidden p-2" :class="isLightMode ? 'text-gray-600' : 'text-white'" @click="goTo('/mypage/profile')">
          <User :size="24" />
        </button>
      </template>

      <!-- Guest actions -->
      <template v-else>
        <button @click="uiStore.openLogin" class="hidden md:block text-sm font-medium hover:opacity-70 transition-opacity mr-2" :class="isLightMode ? 'text-gray-600' : 'text-white'">
          로그인
        </button>
        <button class="md:hidden p-2" :class="isLightMode ? 'text-gray-600' : 'text-white'" @click="uiStore.openLogin">
          <User :size="24" />
        </button>
      </template>
      
      <button @click="uiStore.openCart" :class="['relative p-2 rounded-full transition-colors', isLightMode ? 'text-gray-900 hover:bg-gray-100' : 'text-white hover:bg-white/10']">
        <ShoppingCart :size="24" />
        <span v-if="cartStore.count > 0" class="absolute top-0 right-0 w-4 h-4 bg-brand-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center ring-2 ring-white">
          {{ cartStore.count }}
        </span>
      </button>
    </div>
  </header>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Search, User, ShoppingCart } from 'lucide-vue-next'
import { useUIStore } from '@/stores/ui'
import { useCartStore } from '@/stores/cart'
import { useAuthStore } from '@/stores/auth'
import { useScroll } from '@/composables/useScroll'

const uiStore = useUIStore()
const cartStore = useCartStore()
const authStore = useAuthStore()
const { scrollToTop } = useScroll()
const router = useRouter()
const route = useRoute()

const LIGHT_SCROLL_Y = 48
let observer: IntersectionObserver | null = null

const navState = computed({
  get: () => uiStore.headerState,
  set: (state: 'hero' | 'light' | 'green') => uiStore.setHeaderState(state)
})

const navLinks = [
  { name: 'brand-story', label: '브랜드 스토리', to: { name: 'brand-story' } },
  { name: 'best-products', label: '베스트', to: { name: 'best-products' } },
  { name: 'new-products', label: '신상품', to: { name: 'new-products' } },
  { name: 'self-mall', label: 'SelF Mall', to: { name: 'self-mall' } },
  { name: 'fresh-mall', label: 'Fresh Mall', to: { name: 'fresh-mall' } }
] as const

const isHome = computed(() => route.name === 'home')
const isLightMode = computed(() => navState.value === 'light')

const headerToneClass = computed(() => {
  if (navState.value === 'green') {
    return 'h-16 bg-brand-600 text-white shadow-lg shadow-brand-600/30'
  }
  if (navState.value === 'light') {
    return 'h-16 bg-white/95 backdrop-blur-md shadow-sm text-gray-900'
  }
  return 'h-24 bg-transparent text-white'
})

const searchQuery = ref('')

const handleSearch = () => {
  const q = searchQuery.value.trim()
  router.push({ name: 'search', query: q ? { q } : {} })
}

const handleLogoClick = () => {
  if (route.name === 'home') {
    scrollToTop()
  } else {
    router.push({ name: 'home' })
  }
}

const goTo = (path: string) => {
  router.push(path)
}

const linkClass = (name: string) => {
  const isActive = route.name === name
  const base = 'pb-2 border-b-2 transition-colors'
  const color = isLightMode.value ? 'hover:text-brand-500' : 'hover:text-brand-200'
  const active = isActive
    ? isLightMode.value
      ? 'text-brand-600 border-brand-600'
      : 'text-white border-white/80'
    : 'border-transparent'
  return [base, color, active]
}

const selfBaseClass = (name: string) => {
  const isActive = route.name === name
  if (isActive) return isLightMode.value ? 'text-brand-600' : 'text-white'
  return isLightMode.value ? 'text-gray-800' : 'text-white/80'
}

const selfAccentClass = (name: string) => {
  const isActive = route.name === name
  if (isActive) return isLightMode.value ? 'text-brand-500' : 'text-brand-200'
  return isLightMode.value ? 'text-brand-500' : 'text-brand-200'
}

const handleLogout = async () => {
  await authStore.logout()
}

const applyScrollState = () => {
  if (!isHome.value) {
    navState.value = 'light'
    return
  }

  const sentinel = document.getElementById('nav-sentinel')
  if (sentinel) {
    const top = sentinel.getBoundingClientRect().top
    if (top <= 0) {
      navState.value = 'green'
      return
    }
  }

  navState.value = window.scrollY > LIGHT_SCROLL_Y ? 'light' : 'hero'
}

const handleIntersect: IntersectionObserverCallback = (entries) => {
  if (!isHome.value) return
  const entry = entries[0]
  if (!entry) return

  const isAboveViewport = entry.boundingClientRect.top <= 0

  if (!entry.isIntersecting && isAboveViewport) {
    navState.value = 'green'
  } else {
    applyScrollState()
  }
}

const initObserver = () => {
  if (!isHome.value) return
  if (observer) {
    observer.disconnect()
    observer = null
  }
  const sentinel = document.getElementById('nav-sentinel')
  if (!sentinel) return

  observer = new IntersectionObserver(handleIntersect, {
    root: null,
    threshold: 0,
    rootMargin: '-72px 0px 0px 0px'
  })
  observer.observe(sentinel)
}

onMounted(() => {
  applyScrollState()
  window.addEventListener('scroll', applyScrollState, { passive: true })
  initObserver()
})

onBeforeUnmount(() => {
  window.removeEventListener('scroll', applyScrollState)
  if (observer) {
    observer.disconnect()
    observer = null
  }
})

watch(
  () => route.name,
  () => {
    if (!isHome.value) {
      navState.value = 'light'
      if (observer) {
        observer.disconnect()
        observer = null
      }
      return
    }
    applyScrollState()
    initObserver()
  }
)
</script>
