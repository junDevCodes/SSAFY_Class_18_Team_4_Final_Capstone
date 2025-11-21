import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/services/api/auth'
import type { User } from '@/types/auth'

// 인증 스토어
export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  // 로그인 상태 확인
  const isAuthenticated = computed(() => {
    return !!user.value && !!localStorage.getItem('access_token')
  })

  // 로그인
  const login = async (email: string, password: string) => {
    isLoading.value = true
    error.value = null
    try {
      const response = await authApi.login({ email, password })
      user.value = response.user
      return response
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.response?.data?.email?.[0] || '로그인에 실패했습니다.'
      error.value = errorMessage
      throw new Error(errorMessage)
    } finally {
      isLoading.value = false
    }
  }

  // 회원가입 (이메일 인증 메일 발송)
  const register = async (email: string, password: string, username?: string) => {
    isLoading.value = true
    error.value = null
    try {
      const response = await authApi.register({ email, password, username })
      
      // 개발 환경에서 인증 코드가 응답에 포함된 경우에만 콘솔에 출력
      if (import.meta.env.DEV && response.verification_code) {
        console.log(`[개발 환경] 인증 코드: ${response.verification_code}`)
      }
      
      return response
    } catch (err: any) {
      // 타임아웃 에러 처리
      if (err.code === 'ECONNABORTED' || err.message?.includes('timeout')) {
        const errorMessage = '이메일 발송 중 타임아웃이 발생했습니다. 백엔드 설정을 확인하세요.'
        error.value = errorMessage
        throw new Error(errorMessage)
      }
      
      // 상세한 에러 메시지 추출
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
      } else if (err.message) {
        errorMessage = err.message
      }
      error.value = errorMessage
      throw new Error(errorMessage)
    } finally {
      isLoading.value = false
    }
  }

  // 이메일 인증 확인
  const verifyEmail = async (email: string, code: string) => {
    isLoading.value = true
    error.value = null
    try {
      const response = await authApi.verifyEmail({ email, code })
      return response
    } catch (err: any) {
      // 상세한 에러 메시지 추출
      let errorMessage = '이메일 인증에 실패했습니다.'
      if (err.response?.data) {
        if (err.response.data.detail) {
          errorMessage = err.response.data.detail
        } else if (err.response.data.code) {
          errorMessage = err.response.data.code === 'invalid_verification_code' 
            ? '인증번호가 일치하지 않습니다.'
            : err.response.data.detail || errorMessage
        } else if (err.response.data.email) {
          errorMessage = Array.isArray(err.response.data.email) 
            ? err.response.data.email[0] 
            : err.response.data.email
        }
      } else if (err.message) {
        errorMessage = err.message
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
      await authApi.logout()
    } catch (err) {
      console.error('로그아웃 에러:', err)
    } finally {
      user.value = null
      isLoading.value = false
    }
  }

  // 현재 사용자 정보 로드
  const loadUser = async () => {
    const token = localStorage.getItem('access_token')
    if (!token) {
      user.value = null
      return
    }

    isLoading.value = true
    error.value = null
    try {
      user.value = await authApi.getCurrentUser()
    } catch (err) {
      // 토큰이 유효하지 않은 경우
      user.value = null
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
    } finally {
      isLoading.value = false
    }
  }

  // 사용자 정보 업데이트
  const updateUser = async (data: Partial<User>) => {
    isLoading.value = true
    error.value = null
    try {
      user.value = await authApi.updateUser(data)
      return user.value
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || '사용자 정보 업데이트에 실패했습니다.'
      error.value = errorMessage
      throw new Error(errorMessage)
    } finally {
      isLoading.value = false
    }
  }

  // 에러 초기화
  const clearError = () => {
    error.value = null
  }

  return {
    user,
    isLoading,
    error,
    isAuthenticated,
    login,
    register,
    verifyEmail,
    logout,
    loadUser,
    updateUser,
    clearError,
  }
})

