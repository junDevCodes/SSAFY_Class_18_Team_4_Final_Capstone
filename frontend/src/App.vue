<template>
  <div class="relative min-h-screen flex flex-col">
    <AppHeader />
    <main class="flex-grow">
      <HeroSection />
      <CategoryNav />
      <QuickCategories />
      <BrandPromise />
      <TimeDeal />
      <ProductList />
    </main>
    <AppFooter />
    <LoginModal />
    <CartDrawer />
    <Toast />
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import AppHeader from './components/layout/AppHeader.vue'
import AppFooter from './components/layout/AppFooter.vue'
import HeroSection from './components/sections/HeroSection.vue'
import CategoryNav from './components/sections/CategoryNav.vue'
import QuickCategories from './components/sections/QuickCategories.vue'
import BrandPromise from './components/sections/BrandPromise.vue'
import TimeDeal from './components/sections/TimeDeal.vue'
import ProductList from './components/sections/ProductList.vue'
import LoginModal from './components/ui/LoginModal.vue'
import CartDrawer from './components/ui/CartDrawer.vue'
import Toast from './components/ui/Toast.vue'
import { useAuthStore } from './stores/auth'
import { useUIStore } from './stores/ui'

const authStore = useAuthStore()
const uiStore = useUIStore()

// OAuth 성공 시 사용자 정보를 다시 불러오고 모달을 닫는 핸들러
const handleOAuthSuccess = async () => {
  try {
    await authStore.loadUser()
    uiStore.showToast('로그인되었습니다.')
    uiStore.closeLogin()
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
  } catch (error) {
    console.error('초기 사용자 정보 로드 실패:', error)
  }
})

// 전역 인증 관련 이벤트 리스너 등록/해제
onMounted(() => {
  window.addEventListener('oauth:success', handleOAuthSuccess)
  window.addEventListener('auth:logout', handleAuthLogout)
})

onUnmounted(() => {
  window.removeEventListener('oauth:success', handleOAuthSuccess)
  window.removeEventListener('auth:logout', handleAuthLogout)
})
</script>

