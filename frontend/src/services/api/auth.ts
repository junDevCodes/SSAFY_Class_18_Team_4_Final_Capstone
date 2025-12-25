import apiClient from './client'
import type {
  LoginRequest,
  SignupRequest,
  EmailVerificationRequest,
  RegisterResponse,
  VerificationResponse,
  AuthResponse,
  User,
} from '@/types/auth'

// 인증 API 서비스
export const authApi = {
  // 회원가입 (이메일 인증 메일 발송)
  register: async (data: SignupRequest): Promise<RegisterResponse> => {
    const response = await apiClient.post<RegisterResponse>('/auth/register/', data)
    return response.data
  },

  // 이메일 인증 확인
  verifyEmail: async (data: EmailVerificationRequest): Promise<VerificationResponse> => {
    const response = await apiClient.post<VerificationResponse>('/auth/register/verify/', data)
    return response.data
  },

  // 로그인
  login: async (data: LoginRequest): Promise<AuthResponse> => {
    const response = await apiClient.post<AuthResponse>('/auth/login/', data)
    // JWT 토큰 저장
    if (response.data.access) {
      localStorage.setItem('access_token', response.data.access)
      localStorage.setItem('refresh_token', response.data.refresh)
    }
    return response.data
  },

  // 로그아웃
  logout: async (): Promise<void> => {
    const refreshToken = localStorage.getItem('refresh_token')
    if (refreshToken) {
      try {
        await apiClient.post('/auth/logout/', { refresh: refreshToken })
      } catch (error) {
        // 에러가 발생해도 토큰은 삭제
        console.error('로그아웃 에러:', error)
      }
    }
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  },

  // 토큰 갱신 (ROTATE_REFRESH_TOKENS 설정 시 새 리프레시 토큰도 저장)
  refreshToken: async (): Promise<{ access: string; refresh?: string }> => {
    const refreshToken = localStorage.getItem('refresh_token')
    if (!refreshToken) {
      throw new Error('리프레시 토큰이 없습니다.')
    }
    const response = await apiClient.post<{ access: string; refresh?: string }>(
      '/auth/token/refresh/',
      { refresh: refreshToken }
    )
    if (response.data.access) {
      localStorage.setItem('access_token', response.data.access)
    }
    // ROTATE_REFRESH_TOKENS 설정으로 새 리프레시 토큰이 발급되면 저장
    if (response.data.refresh) {
      localStorage.setItem('refresh_token', response.data.refresh)
    }
    return response.data
  },

  // 현재 사용자 정보 조회
  getCurrentUser: async (): Promise<User> => {
    const response = await apiClient.get<User>('/auth/user/')
    return response.data
  },

  // 사용자 정보 수정
  updateUser: async (data: Partial<User>): Promise<User> => {
    const response = await apiClient.patch<User>('/auth/user/', data)
    return response.data
  },
}

