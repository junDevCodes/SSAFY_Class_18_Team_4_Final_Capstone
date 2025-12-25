<template>
  <!-- Backdrop -->
  <Transition name="drawer-backdrop">
    <div
      v-if="uiStore.isMobileMenuOpen"
      class="fixed inset-0 bg-black/40 backdrop-blur-sm z-[130]"
      @click="uiStore.closeMobileMenu"
    />
  </Transition>

  <!-- Drawer (오른쪽 슬라이드) -->
  <Transition name="drawer-slide">
    <aside
      v-if="uiStore.isMobileMenuOpen"
      class="fixed top-0 right-0 h-full w-full sm:w-[320px] bg-white z-[131] shadow-2xl flex flex-col"
    >
      <!-- 헤더 -->
      <div class="h-16 px-5 flex items-center justify-between border-b border-gray-100">
        <span class="font-display font-bold text-xl text-brand-900">
          Sel<span class="italic text-brand-500">F</span>
        </span>
        <button
          @click="uiStore.closeMobileMenu"
          class="p-2 -mr-2 text-gray-400 hover:text-gray-900 transition-colors"
          aria-label="메뉴 닫기"
        >
          <X :size="24" />
        </button>
      </div>

      <!-- 사용자 정보 섹션 (로그인 시) -->
      <div v-if="authStore.isAuthenticated" class="px-5 py-4 bg-gray-50 border-b border-gray-100">
        <p class="text-sm font-medium text-gray-900">
          {{ authStore.user?.email }}님
        </p>
        <div class="flex gap-3 mt-3">
          <button
            @click="navigateAndClose('/mypage/profile')"
            class="text-xs text-brand-600 font-medium hover:text-brand-700 transition-colors"
          >
            마이페이지
          </button>
          <span class="text-gray-300">|</span>
          <button
            @click="handleLogout"
            class="text-xs text-gray-500 font-medium hover:text-gray-700 transition-colors"
          >
            로그아웃
          </button>
        </div>
      </div>

      <!-- 로그인 유도 (비로그인 시) -->
      <div v-else class="px-5 py-4 bg-gray-50 border-b border-gray-100">
        <button
          @click="openLoginAndClose"
          class="w-full bg-brand-500 text-white font-bold py-3 rounded-lg text-sm hover:bg-brand-600 transition-colors"
        >
          로그인 / 회원가입
        </button>
      </div>

      <!-- 네비게이션 링크 -->
      <nav class="flex-1 overflow-y-auto py-4">
        <RouterLink
          v-for="link in navLinks"
          :key="link.name"
          :to="link.to"
          class="flex items-center justify-between px-5 py-4 text-[15px] font-semibold text-gray-800 hover:bg-gray-50 transition-colors"
          @click="uiStore.closeMobileMenu"
        >
          <template v-if="link.name === 'self-mall'">
            <span class="flex items-center">
              <span class="font-display font-bold">Sel</span>
              <span class="font-display font-bold italic text-brand-500">F</span>
              <span class="ml-1">Mall</span>
            </span>
          </template>
          <template v-else>
            {{ link.label }}
          </template>
          <ChevronRight :size="18" class="text-gray-400" />
        </RouterLink>
      </nav>

      <!-- 하단 유틸리티 링크 -->
      <div class="px-5 py-4 border-t border-gray-100 space-y-1">
        <button
          @click="openRecentAndClose"
          class="flex items-center gap-3 w-full py-3 text-sm text-gray-600 hover:text-gray-900 transition-colors"
        >
          <Clock3 :size="20" />
          <span>최근 본 상품</span>
        </button>
        <button
          v-if="authStore.isSeller"
          @click="navigateAndClose('/seller/dashboard')"
          class="flex items-center gap-3 w-full py-3 text-sm text-gray-600 hover:text-gray-900 transition-colors"
        >
          <Store :size="20" />
          <span>판매자 센터</span>
        </button>
      </div>
    </aside>
  </Transition>
</template>

<script setup lang="ts">
import { X, ChevronRight, Clock3, Store } from 'lucide-vue-next'
import { useRouter } from 'vue-router'
import { useUIStore } from '@/stores/ui'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const uiStore = useUIStore()
const authStore = useAuthStore()

// 네비게이션 링크 (AppHeader와 동일)
const navLinks = [
  { name: 'brand-story', label: '브랜드 스토리', to: { name: 'brand-story' } },
  { name: 'best-products', label: '베스트', to: { name: 'best-products' } },
  { name: 'new-products', label: '신상품', to: { name: 'new-products' } },
  { name: 'self-mall', label: 'SelF Mall', to: { name: 'self-mall' } },
  { name: 'fresh-mall', label: 'Fresh Mall', to: { name: 'fresh-mall' } }
] as const

const navigateAndClose = (path: string) => {
  uiStore.closeMobileMenu()
  router.push(path)
}

const openLoginAndClose = () => {
  uiStore.closeMobileMenu()
  uiStore.openLogin()
}

const openRecentAndClose = () => {
  uiStore.closeMobileMenu()
  uiStore.openRecent()
}

const handleLogout = async () => {
  await authStore.logout()
  uiStore.closeMobileMenu()
}
</script>
