import { defineStore } from 'pinia'
import { ref } from 'vue'

// UI 상태 스토어
export const useUIStore = defineStore('ui', () => {
  const isScrolled = ref(false)
  const isCartOpen = ref(false)
  const isLoginOpen = ref(false)
  const isRecentOpen = ref(false)
  const isMobileMenuOpen = ref(false)
  const headerState = ref<'hero' | 'light' | 'green'>('hero')
  const activeTab = ref('추천')
  const authMode = ref<'login' | 'signup' | 'forgot-password'>('login')
  const showVerification = ref(false)
  const showForgotPassword = ref(false)  // 비밀번호 찾기 모달 표시
  const toast = ref({ show: false, message: '' })
  const redirectPath = ref<string | null>(null)

  let toastTimeout: ReturnType<typeof setTimeout> | null = null

  // 스크롤 상태 업데이트
  const setScrolled = (value: boolean) => {
    isScrolled.value = value
  }

  // 헤더 컬러 상태 관리
  const setHeaderState = (state: 'hero' | 'light' | 'green') => {
    headerState.value = state
  }

  // 장바구니 열기/닫기
  const openCart = () => {
    isCartOpen.value = true
  }

  const closeCart = () => {
    isCartOpen.value = false
  }

  // 최근 본 상품 열기/닫기
  const openRecent = () => {
    isRecentOpen.value = true
  }

  const closeRecent = () => {
    isRecentOpen.value = false
  }

  // 모바일 메뉴 열기/닫기
  const openMobileMenu = () => {
    isMobileMenuOpen.value = true
  }

  const closeMobileMenu = () => {
    isMobileMenuOpen.value = false
  }

  // 로그인 모달 열기/닫기
  const openLogin = () => {
    isLoginOpen.value = true
    authMode.value = 'login'
  }

  const closeLogin = () => {
    isLoginOpen.value = false
    showVerification.value = false
  }

  // 로그인 후 리다이렉트 경로 설정/초기화
  const setRedirectPath = (path: string | null) => {
    redirectPath.value = path
  }

  // 인증 모드 변경
  const setAuthMode = (mode: 'login' | 'signup' | 'forgot-password') => {
    authMode.value = mode
    // 비밀번호 찾기 모드일 때 플래그 설정
    showForgotPassword.value = mode === 'forgot-password'
  }

  // 인증번호 입력 표시
  const setShowVerification = (value: boolean) => {
    showVerification.value = value
  }

  // 비밀번호 찾기 모달 표시/숨기기
  const setShowForgotPassword = (value: boolean) => {
    showForgotPassword.value = value
    if (value) {
      authMode.value = 'forgot-password'
    } else {
      authMode.value = 'login'
    }
  }

  // 토스트 표시
  const showToast = (message: string) => {
    if (toastTimeout) {
      clearTimeout(toastTimeout)
    }
    toast.value.message = message
    toast.value.show = true
    toastTimeout = setTimeout(() => {
      toast.value.show = false
    }, 2000)
  }

  // 활성 탭 변경
  const setActiveTab = (tab: string) => {
    activeTab.value = tab
  }

  return {
    isScrolled,
    isCartOpen,
    isLoginOpen,
    isRecentOpen,
    isMobileMenuOpen,
    headerState,
    activeTab,
    authMode,
    showVerification,
    showForgotPassword,
    toast,
    redirectPath,
    setScrolled,
    setHeaderState,
    openCart,
    closeCart,
    openRecent,
    closeRecent,
    openMobileMenu,
    closeMobileMenu,
    openLogin,
    closeLogin,
    setAuthMode,
    setShowVerification,
    setShowForgotPassword,
    showToast,
    setActiveTab,
    setRedirectPath
  }
})
