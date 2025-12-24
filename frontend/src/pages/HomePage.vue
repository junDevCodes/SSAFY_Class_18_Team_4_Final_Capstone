<template>
  <main class="flex-grow">
    <HeroSection />
    <div id="nav-sentinel" class="h-4"></div>
    <CategoryNav />
    <QuickCategories />
    <TimeDeal />
    <ProductList />
    <RecentProductsBar
      placement-class="fixed right-10 top-44"
      :placement-style="{
        right: 'calc((100vw - min(1280px, 100vw)) / 2 - 100px)'
      }"
    />
    <BrandPromise />
  </main>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import HeroSection from '@/components/sections/HeroSection.vue'
import CategoryNav from '@/components/sections/CategoryNav.vue'
import QuickCategories from '@/components/sections/QuickCategories.vue'
import BrandPromise from '@/components/sections/BrandPromise.vue'
import TimeDeal from '@/components/sections/TimeDeal.vue'
import ProductList from '@/components/sections/ProductList.vue'
import RecentProductsBar from '@/components/ui/RecentProductsBar.vue'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const authStore = useAuthStore()

const IDLE_DELAY_MS = 2000
const SESSION_FLAG = 'home-auto-scroll-recommend'
const cancelEvents = ['scroll', 'keydown', 'click', 'touchstart']

let idleTimer: ReturnType<typeof setTimeout> | null = null

const clearIdleTimer = () => {
  if (idleTimer) {
    clearTimeout(idleTimer)
    idleTimer = null
  }
}

const removeCancelListeners = () => {
  cancelEvents.forEach(evt => window.removeEventListener(evt, onUserAction))
}

const onUserAction = () => {
  clearIdleTimer()
  removeCancelListeners()
}

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

const scrollToRecommend = () => {
  const el = document.getElementById('recommend')
  if (!el) return

  const header = document.querySelector('header') as HTMLElement | null
  const catNav = document.getElementById('sticky-nav')
  const headerHeight = header?.offsetHeight ?? 0
  const navHeight = catNav?.offsetHeight ?? 0
  // 헤더는 스크롤 시 축소되므로 과도한 보정을 피하려고 최대 72px만 반영
  const stickyHeaderHeight = headerHeight ? Math.min(headerHeight, 72) : 72
  const offset = stickyHeaderHeight + navHeight + 8 // 소량 여유만 추가

  const top = el.getBoundingClientRect().top + window.scrollY - offset
  smoothScrollTo(top, 1200)
}

const startIdleScroll = () => {
  if (authStore.isAuthenticated) return
  if (route.name !== 'home') return
  if (sessionStorage.getItem(SESSION_FLAG)) return

  idleTimer = setTimeout(() => {
    sessionStorage.setItem(SESSION_FLAG, '1')
    removeCancelListeners()
    scrollToRecommend()
  }, IDLE_DELAY_MS)

  cancelEvents.forEach(evt => window.addEventListener(evt, onUserAction, { once: true }))
}

onMounted(startIdleScroll)
onBeforeUnmount(() => {
  clearIdleTimer()
  removeCancelListeners()
})
</script>
