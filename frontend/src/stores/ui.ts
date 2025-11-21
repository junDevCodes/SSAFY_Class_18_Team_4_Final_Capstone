import { defineStore } from 'pinia'
import { ref } from 'vue'

// UI 상태 스토어
export const useUIStore = defineStore('ui', () => {
  const isScrolled = ref(false)
  const isCartOpen = ref(false)
  const isLoginOpen = ref(false)
  const activeTab = ref('추천')
  const authMode = ref<'login' | 'signup'>('login')
  const showVerification = ref(false)
  const toast = ref({ show: false, message: '' })

  let toastTimeout: ReturnType<typeof setTimeout> | null = null

  // 스크롤 상태 업데이트
  const setScrolled = (value: boolean) => {
    isScrolled.value = value
  }

  // 장바구니 열기/닫기
  const openCart = () => {
    isCartOpen.value = true
  }

  const closeCart = () => {
    isCartOpen.value = false
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

  // 인증 모드 변경
  const setAuthMode = (mode: 'login' | 'signup') => {
    authMode.value = mode
  }

  // 인증번호 입력 표시
  const setShowVerification = (value: boolean) => {
    showVerification.value = value
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
    activeTab,
    authMode,
    showVerification,
    toast,
    setScrolled,
    openCart,
    closeCart,
    openLogin,
    closeLogin,
    setAuthMode,
    setShowVerification,
    showToast,
    setActiveTab
  }
})

