<template>
  <!-- Backdrop -->
  <Transition name="drawer-backdrop">
    <div v-if="uiStore.isLoginOpen" class="fixed inset-0 bg-black/60 backdrop-blur-sm z-[100]" @click="uiStore.closeLogin"></div>
  </Transition>

  <!-- Modal -->
  <Transition name="modal">
    <div v-if="uiStore.isLoginOpen" class="fixed inset-0 z-[101] flex items-center justify-center p-4 sm:p-6 pointer-events-none">
      <div class="bg-white w-full max-w-[400px] rounded-2xl shadow-2xl pointer-events-auto overflow-hidden flex flex-col max-h-[90vh]">
        <!-- Modal Header -->
        <div class="flex items-center justify-between px-6 py-4 border-b border-gray-100 shrink-0">
          <div class="text-2xl font-bold font-display text-brand-900">
            Sel<span class="inline-block transform italic text-brand-500 ml-0.5">F</span>
          </div>
          <button @click="uiStore.closeLogin" class="text-gray-400 transition-colors hover:text-gray-900">
            <X :size="24" />
          </button>
        </div>

        <!-- Modal Body -->
        <div class="p-6 overflow-y-auto custom-scrollbar">
          <!-- Tabs -->
          <div class="flex gap-4 mb-8 border-b border-gray-100">
            <button 
              @click="uiStore.setAuthMode('login')" 
              :class="['flex-1 pb-3 text-sm font-bold border-b-2 transition-colors', uiStore.authMode === 'login' ? 'text-gray-900 border-gray-900' : 'text-gray-400 border-transparent hover:text-gray-600']"
            >
              로그인
            </button>
            <button 
              @click="uiStore.setAuthMode('signup')" 
              :class="['flex-1 pb-3 text-sm font-bold border-b-2 transition-colors', uiStore.authMode === 'signup' ? 'text-gray-900 border-gray-900' : 'text-gray-400 border-transparent hover:text-gray-600']"
            >
              회원가입
            </button>
          </div>

          <!-- Login Form -->
          <div v-if="uiStore.authMode === 'login'" class="space-y-4 animate-fade-in">
            <div class="space-y-3">
              <input 
                v-model="loginForm.email"
                type="email" 
                placeholder="이메일을 입력해주세요" 
                @keyup.enter="handleLogin"
                class="w-full px-4 py-3 text-sm transition-all border border-gray-200 rounded-lg bg-gray-50 focus:outline-none focus:ring-1 focus:ring-brand-500 focus:bg-white"
              >
              <input 
                v-model="loginForm.password"
                type="password" 
                placeholder="비밀번호를 입력해주세요" 
                @keyup.enter="handleLogin"
                class="w-full px-4 py-3 text-sm transition-all border border-gray-200 rounded-lg bg-gray-50 focus:outline-none focus:ring-1 focus:ring-brand-500 focus:bg-white"
              >
            </div>
            <div class="flex items-center justify-between px-1 text-xs text-gray-500">
              <label class="flex items-center gap-1.5 cursor-pointer">
                <input v-model="loginForm.rememberMe" type="checkbox" class="border-gray-300 rounded text-brand-600 focus:ring-brand-500">
                <span>로그인 유지</span>
              </label>
              <a href="#" class="hover:underline">비밀번호 찾기</a>
            </div>
            <button 
              @click="handleLogin" 
              :disabled="isSubmitting"
              class="w-full bg-brand-500 hover:bg-brand-600 disabled:bg-gray-400 disabled:cursor-not-allowed text-white font-bold py-3.5 rounded-lg transition-colors text-sm shadow-lg shadow-brand-500/20"
            >
              {{ isSubmitting ? '처리 중...' : '로그인' }}
            </button>
            
            <div class="relative my-6">
              <div class="absolute inset-0 flex items-center"><div class="w-full border-t border-gray-100"></div></div>
              <div class="relative flex justify-center text-xs"><span class="px-2 text-gray-400 bg-white">또는</span></div>
            </div>

            <div class="space-y-2.5">
              <button 
                @click="handleKakaoLogin"
                class="w-full bg-[#FEE500] hover:bg-[#FDD835] text-[#3C1E1E] font-medium py-3 rounded-lg transition-colors text-sm flex items-center justify-center gap-2"
              >
                <MessageCircle :size="16" class="fill-current" /> 카카오로 시작하기
              </button>
              <button 
                @click="handleGoogleLogin"
                class="flex items-center justify-center w-full gap-2 py-3 text-sm font-medium text-gray-700 transition-colors bg-white border border-gray-200 rounded-lg hover:bg-gray-50"
              >
                <svg class="w-4 h-4" viewBox="0 0 24 24">
                  <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
                  <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                  <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
                  <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
                </svg>
                Google로 시작하기
              </button>
            </div>
          </div>

          <!-- Signup Form -->
          <div v-else class="space-y-4 animate-fade-in">
            <div class="flex gap-2">
              <input 
                v-model="signupForm.email"
                type="email" 
                placeholder="이메일" 
                @keyup.enter="handleSignup"
                class="flex-1 px-4 py-3 text-sm transition-all border border-gray-200 rounded-lg bg-gray-50 focus:outline-none focus:ring-1 focus:ring-brand-500 focus:bg-white"
              >
              <button 
                @click="handleRequestVerification" 
                :disabled="isSubmitting"
                class="px-3 py-3 text-xs font-bold text-white bg-gray-800 rounded-lg hover:bg-gray-900 disabled:bg-gray-400 disabled:cursor-not-allowed whitespace-nowrap"
              >
                {{ isSubmitting ? '처리 중...' : '인증요청' }}
              </button>
            </div>
            
            <div v-if="uiStore.showVerification" class="animate-fade-in">
              <input 
                v-model="signupForm.verificationCode"
                type="text" 
                placeholder="인증번호 6자리 입력" 
                @keyup.enter="handleSignup"
                class="w-full px-4 py-3 mb-1 text-sm transition-all border border-gray-200 rounded-lg bg-gray-50 focus:outline-none focus:ring-1 focus:ring-brand-500 focus:bg-white"
              >
              <p class="text-[11px] text-brand-600 pl-1">이메일로 발송된 인증코드를 입력해주세요.</p>
            </div>

            <input 
              v-model="signupForm.password"
              type="password" 
              placeholder="비밀번호 (영문, 숫자, 특수문자 포함 8자 이상)" 
              @keyup.enter="handleSignup"
              class="w-full px-4 py-3 text-sm transition-all border border-gray-200 rounded-lg bg-gray-50 focus:outline-none focus:ring-1 focus:ring-brand-500 focus:bg-white"
            >
            <input 
              v-model="signupForm.passwordConfirm"
              type="password" 
              placeholder="비밀번호 확인" 
              @keyup.enter="handleSignup"
              class="w-full px-4 py-3 text-sm transition-all border border-gray-200 rounded-lg bg-gray-50 focus:outline-none focus:ring-1 focus:ring-brand-500 focus:bg-white"
            >
            
            <div class="pt-2">
              <label class="flex items-start gap-2 cursor-pointer">
                <input v-model="signupForm.agreeTerms" type="checkbox" class="mt-0.5 rounded border-gray-300 text-brand-600 focus:ring-brand-500">
                <span class="text-xs leading-tight text-gray-500">[필수] 만 14세 이상이며, 이용약관 및 개인정보 처리방침에 동의합니다.</span>
              </label>
            </div>

            <button 
              @click="handleSignup" 
              :disabled="isSubmitting"
              class="w-full bg-brand-500 hover:bg-brand-600 disabled:bg-gray-400 disabled:cursor-not-allowed text-white font-bold py-3.5 rounded-lg transition-colors text-sm shadow-lg shadow-brand-500/20 mt-2"
            >
              {{ isSubmitting ? '처리 중...' : '가입하기' }}
            </button>
            
            <div class="relative my-6">
              <div class="absolute inset-0 flex items-center"><div class="w-full border-t border-gray-100"></div></div>
              <div class="relative flex justify-center text-xs"><span class="px-2 text-gray-400 bg-white">간편 회원가입</span></div>
            </div>

            <div class="flex gap-2">
              <button 
                @click="handleKakaoLogin"
                class="flex-1 bg-[#FEE500] hover:bg-[#FDD835] text-[#3C1E1E] font-medium py-3 rounded-lg transition-colors text-sm flex items-center justify-center gap-2"
              >
                <MessageCircle :size="16" class="fill-current" />
              </button>
              <button 
                @click="handleGoogleLogin"
                class="flex items-center justify-center flex-1 gap-2 py-3 text-sm font-medium text-gray-700 transition-colors bg-white border border-gray-200 rounded-lg hover:bg-gray-50"
              >
                <svg class="w-4 h-4" viewBox="0 0 24 24">
                  <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
                  <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                  <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
                  <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { X, MessageCircle } from 'lucide-vue-next'
import { useUIStore } from '@/stores/ui'
import { useAuthStore } from '@/stores/auth'

const uiStore = useUIStore()
const authStore = useAuthStore()
const router = useRouter()

const loginForm = reactive({
  email: '',
  password: '',
  rememberMe: false
})

const signupForm = reactive({
  email: '',
  password: '',
  passwordConfirm: '',
  verificationCode: '',
  agreeTerms: false
})

const isSubmitting = ref(false)

// 로그인 처리
const handleLogin = async () => {
  if (!loginForm.email || !loginForm.password) {
    uiStore.showToast('이메일과 비밀번호를 입력해주세요.')
    return
  }

  isSubmitting.value = true
  try {
    await authStore.login(loginForm.email, loginForm.password)
    uiStore.showToast('로그인되었습니다.')
    uiStore.closeLogin()

    // 로그인 후 리다이렉트 처리
    const target = uiStore.redirectPath
    // 권한 기반 기본 경로
    const fallback =
      authStore.isAdmin ? '/admin/analytics' :
      authStore.isSeller ? '/seller/dashboard' :
      '/mypage/profile'

    // 리다이렉트 경로가 있으면 우선 이동
    if (target) {
      router.push(target)
      uiStore.setRedirectPath(null)
    } else {
      router.push(fallback)
    }

    // 폼 초기화
    loginForm.email = ''
    loginForm.password = ''
    loginForm.rememberMe = false
  } catch (error: any) {
    uiStore.showToast(error.message || '로그인에 실패했습니다.')
  } finally {
    isSubmitting.value = false
  }
}

// 회원가입 처리 (이메일 인증 확인)
const handleSignup = async () => {
  // 유효성 검사
  if (!signupForm.email) {
    uiStore.showToast('이메일을 입력해주세요.')
    return
  }

  if (!signupForm.password) {
    uiStore.showToast('비밀번호를 입력해주세요.')
    return
  }

  if (signupForm.password !== signupForm.passwordConfirm) {
    uiStore.showToast('비밀번호가 일치하지 않습니다.')
    return
  }

  if (signupForm.password.length < 8) {
    uiStore.showToast('비밀번호는 8자 이상이어야 합니다.')
    return
  }

  if (!signupForm.agreeTerms) {
    uiStore.showToast('이용약관에 동의해주세요.')
    return
  }

  if (!uiStore.showVerification) {
    uiStore.showToast('이메일 인증을 먼저 진행해주세요.')
    return
  }

  if (!signupForm.verificationCode) {
    uiStore.showToast('인증번호를 입력해주세요.')
    return
  }

  isSubmitting.value = true
  try {
    // 이메일 인증 확인 및 회원가입 완료
    await authStore.verifyEmail(signupForm.email, signupForm.verificationCode)
    
    uiStore.showToast('회원가입이 완료되었습니다. 로그인해주세요.')
    uiStore.setAuthMode('login')
    uiStore.setShowVerification(false)
    
    // 폼 초기화
    signupForm.email = ''
    signupForm.password = ''
    signupForm.passwordConfirm = ''
    signupForm.verificationCode = ''
    signupForm.agreeTerms = false
  } catch (error: any) {
    uiStore.showToast(error.message || '회원가입에 실패했습니다.')
  } finally {
    isSubmitting.value = false
  }
}

// 인증 요청 처리
const handleRequestVerification = async () => {
  if (!signupForm.email) {
    uiStore.showToast('이메일을 입력해주세요.')
    return
  }

  // 이메일 형식 검증
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  if (!emailRegex.test(signupForm.email)) {
    uiStore.showToast('올바른 이메일 형식을 입력해주세요.')
    return
  }

  if (!signupForm.password) {
    uiStore.showToast('비밀번호를 입력해주세요.')
    return
  }

  if (signupForm.password.length < 8) {
    uiStore.showToast('비밀번호는 8자 이상이어야 합니다.')
    return
  }

  isSubmitting.value = true
  try {
    // 회원가입 요청 (이메일 인증 메일 발송)
    await authStore.register(signupForm.email, signupForm.password)
    uiStore.showToast('인증번호가 이메일로 발송되었습니다. 메일함을 확인해주세요.')
    uiStore.setShowVerification(true)
  } catch (error: any) {
    const errorMessage = error.message || error.response?.data?.detail || error.response?.data?.email?.[0] || '인증번호 발송에 실패했습니다.'
    uiStore.showToast(errorMessage)
    console.error('인증 요청 에러:', error)
  } finally {
    isSubmitting.value = false
  }
}

// 구글 로그인 처리
const handleGoogleLogin = () => {
  // 백엔드 OAuth 엔드포인트로 리다이렉트 (ui=web으로 설정하여 프론트엔드로 리다이렉트)
  // 프로덕션: 빈 문자열 → 상대 경로 (Nginx 프록시)
  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'
  const frontendUrl = window.location.origin
  window.location.href = `${apiBaseUrl}/auth/google/?ui=web&next=${encodeURIComponent(frontendUrl)}`
}

// 카카오 로그인 처리
const handleKakaoLogin = () => {
  // 백엔드 OAuth 엔드포인트로 리다이렉트 (ui=web으로 설정하여 프론트엔드로 리다이렉트)
  // 프로덕션: 빈 문자열 → 상대 경로 (Nginx 프록시)
  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'
  const frontendUrl = window.location.origin
  window.location.href = `${apiBaseUrl}/auth/kakao/?ui=web&next=${encodeURIComponent(frontendUrl)}`
}

</script>

