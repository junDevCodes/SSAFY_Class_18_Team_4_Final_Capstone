/**
 * Auth Store - 완전히 개선된 버전
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authAPI } from '@/services/api'
import type { User } from '@/types/auth'
import { useCartStore } from './cart'
import { useWishlistStore } from './wishlist'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  // Computed
  const isAuthenticated = computed(() => {
    return !!user.value && !!localStorage.getItem('access_token')
  })

  const isSeller = computed(() => {
    return user.value?.role === 'seller'
  })

  const isAdmin = computed(() => {
    return user.value?.role === 'admin'
  })

  // 로그인
  const login = async (email: string, password: string) => {
    isLoading.value = true
    error.value = null
    try {
      const response = await authAPI.login({ email, password })
      user.value = response.data.user

      // 토큰 저장
      if (response.data.access) {
        localStorage.setItem('access_token', response.data.access)
      }
      if (response.data.refresh) {
        localStorage.setItem('refresh_token', response.data.refresh)
      }

      // 로그인 후 장바구니/찜 목록 로드
      const cartStore = useCartStore()
      const wishlistStore = useWishlistStore()
      await Promise.all([
        cartStore.loadCart(),
        wishlistStore.loadWishlist()
      ])

      return response.data
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.response?.data?.email?.[0] || '로그인에 실패했습니다.'
      error.value = errorMessage
      throw new Error(errorMessage)
    } finally {
      isLoading.value = false
    }
  }

  // 회원가입
  const register = async (email: string, password: string, username?: string) => {
    isLoading.value = true
    error.value = null
    try {
      const response = await authAPI.register({ email, password, username })

      // 개발 환경에서 인증 코드 출력
      if (import.meta.env.DEV && response.data.verification_code) {
        console.log(`[개발 환경] 인증 코드: ${response.data.verification_code}`)
      }

      return response.data
    } catch (err: any) {
      let errorMessage = '회원가입에 실패했습니다.'
      if (err.response?.data) {
        if (err.response.data.detail) {
          errorMessage = err.response.data.detail
        } else if (err.response.data.email) {
          errorMessage = Array.isArray(err.response.data.email)
            ? err.response.data.email[0]
            : err.response.data.email
        } else if (err.response.data.password) {
          errorMessage = Array.isArray(err.response.data.password)
            ? err.response.data.password[0]
            : err.response.data.password
        }
      }
      error.value = errorMessage
      throw new Error(errorMessage)
    } finally {
      isLoading.value = false
    }
  }

  // 이메일 인증
  const verifyEmail = async (email: string, code: string) => {
    isLoading.value = true
    error.value = null
    try {
      const response = await authAPI.verifyEmail({ email, code })
      return response.data
    } catch (err: any) {
      let errorMessage = '이메일 인증에 실패했습니다.'
      if (err.response?.data?.detail) {
        errorMessage = err.response.data.detail
      }
      error.value = errorMessage
      throw new Error(errorMessage)
    } finally {
      isLoading.value = false
    }
  }

  // 로그아웃
  const logout = async () => {
    isLoading.value = true
    error.value = null
    try {
      await authAPI.logout()
    } catch (err: any) {
      console.error('로그아웃 요청 실패:', err)
    } finally {
      // 로컬 상태 초기화
      user.value = null
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')

      // 다른 store 초기화
      const cartStore = useCartStore()
      const wishlistStore = useWishlistStore()
      cartStore.reset()
      wishlistStore.reset()

      isLoading.value = false
    }
  }

  // 현재 사용자 정보 로드
  const loadUser = async () => {
    if (!localStorage.getItem('access_token')) {
      user.value = null
      return null
    }

    isLoading.value = true
    error.value = null
    try {
      const response = await authAPI.getCurrentUser()
      user.value = response.data
      return response.data
    } catch (err: any) {
      // 토큰이 만료된 경우 자동 로그아웃
      if (err.response?.status === 401) {
        await logout()
      }
      error.value = err.response?.data?.detail || '사용자 정보를 불러오는데 실패했습니다.'
      return null
    } finally {
      isLoading.value = false
    }
  }

  // 사용자 정보 수정
  const updateUser = async (data: Partial<User>) => {
    isLoading.value = true
    error.value = null
    try {
      const response = await authAPI.updateUser(data)
      user.value = response.data
      return response.data
    } catch (err: any) {
      error.value = err.response?.data?.detail || '정보 수정에 실패했습니다.'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  // 비밀번호 변경
  const changePassword = async (oldPassword: string, newPassword: string) => {
    isLoading.value = true
    error.value = null
    try {
      await authAPI.changePassword({
        old_password: oldPassword,
        new_password: newPassword
      })
    } catch (err: any) {
      error.value = err.response?.data?.detail || '비밀번호 변경에 실패했습니다.'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  // 초기화
  const reset = () => {
    user.value = null
    isLoading.value = false
    error.value = null
  }

  return {
    user,
    isLoading,
    error,
    isAuthenticated,
    isSeller,
    isAdmin,
    login,
    register,
    verifyEmail,
    logout,
    loadUser,
    updateUser,
    changePassword,
    reset,
  }
})
