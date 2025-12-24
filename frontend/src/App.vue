<template>
  <div class="relative min-h-screen flex flex-col">
    <AppHeader v-if="showChrome" />
    <main
      class="flex-1"
      :class="mainClass"
      :style="mainStyle"
    >
      <router-view />
    </main>
    <AppFooter v-if="showChrome" />
    <LoginModal />
    <CartDrawer />
    <RecentDrawer />
    <TutorialModal
      :open="autoTutorialOpen"
      mode="AUTO"
      @tutorialCompleted="handleTutorialCompleted"
      @close="handleTutorialClose"
    />
    <Toast />
  </div>
</template>


<script setup lang="ts">
import { onMounted, onUnmounted, computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import AppHeader from './components/layout/AppHeader.vue'
import AppFooter from './components/layout/AppFooter.vue'
import LoginModal from './components/ui/LoginModal.vue'
import CartDrawer from './components/ui/CartDrawer.vue'
import RecentDrawer from './components/ui/RecentDrawer.vue'
import Toast from './components/ui/Toast.vue'
import TutorialModal from './components/tutorial/TutorialModal.vue'
import { useAuthStore } from './stores/auth'
import { useWishlistStore } from './stores/wishlist'
import { useUIStore } from './stores/ui'

const route = useRoute()
const authStore = useAuthStore()
const wishlistStore = useWishlistStore()
const uiStore = useUIStore()

const isHome = computed(() => route.name === 'home')
const isAdminAnalytics = computed(() => route.path.startsWith('/admin'))
const showChrome = computed(() => !isAdminAnalytics.value)
const mainStyle = computed(() => {
  if (isHome.value || isAdminAnalytics.value) return {}
  return { paddingTop: 'var(--app-content-top)' }
})
const mainClass = computed(() => (isHome.value ? '' : 'bg-gray-50'))

const TUTORIAL_COMPLETED_KEY = 'tutorialCompleted'
const autoTutorialOpen = ref(false)
const tutorialCompleted = ref(false)

const syncTutorialCompleted = () => {
  if (typeof window === 'undefined') return
  tutorialCompleted.value = localStorage.getItem(TUTORIAL_COMPLETED_KEY) === 'true'
}

const tryOpenAutoTutorial = () => {
  syncTutorialCompleted()
  if (authStore.isAuthenticated && !tutorialCompleted.value) {
    autoTutorialOpen.value = true
  }
}

const handleTutorialCompleted = () => {
  tutorialCompleted.value = true
  autoTutorialOpen.value = false
  if (typeof window !== 'undefined') {
    localStorage.setItem(TUTORIAL_COMPLETED_KEY, 'true')
  }
}

const handleTutorialClose = () => {
  autoTutorialOpen.value = false
}

// 인증 필요 시 로그인 모달 열고 리다이렉트 경로 저장
const handleAuthRequired = (e: Event) => {
  const detail = (e as CustomEvent).detail as { to?: string } | undefined
  if (detail?.to) {
    uiStore.setRedirectPath(detail.to)
  }
  uiStore.openLogin()
}

// OAuth 성공 시 사용자 정보를 다시 불러오고 모달을 닫는 핸들러
const handleOAuthSuccess = async () => {
  try {
    await authStore.loadUser()
    uiStore.showToast('로그인되었습니다.')
    uiStore.closeLogin()
    tryOpenAutoTutorial()
  } catch (error) {
    console.error('사용자 정보 로드 실패:', error)
  }
}

// 토큰 만료 등으로 로그아웃이 필요한 경우 처리 핸들러
const handleAuthLogout = async () => {
  try {
    await authStore.logout()
  } catch (error) {
    console.error('로그아웃 처리 중 오류:', error)
  }
  uiStore.showToast('로그인이 만료되었습니다. 다시 로그인해주세요.')
  uiStore.openLogin()
}

// 앱 마운트 시 기존 토큰이 있다면 사용자 정보를 로드
onMounted(async () => {
  try {
    await authStore.loadUser()
    if (authStore.isAuthenticated) {
      await wishlistStore.loadWishlist()
      tryOpenAutoTutorial()
    }
  } catch (error) {
    console.error('초기 사용자 정보 로드 실패:', error)
  }
})

// 전역 인증 관련 이벤트 리스너 등록/해제
onMounted(() => {
  window.addEventListener('auth:required', handleAuthRequired as EventListener)
  window.addEventListener('oauth:success', handleOAuthSuccess)
  window.addEventListener('auth:logout', handleAuthLogout)
})

onUnmounted(() => {
  window.removeEventListener('auth:required', handleAuthRequired as EventListener)
  window.removeEventListener('oauth:success', handleOAuthSuccess)
  window.removeEventListener('auth:logout', handleAuthLogout)
})

watch(
  () => authStore.isAuthenticated,
  (authed) => {
    if (authed) {
      tryOpenAutoTutorial()
    } else {
      autoTutorialOpen.value = false
    }
  },
)
</script>

