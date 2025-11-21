// 인증 타입 정의
export interface LoginRequest {
  email: string
  password: string
}

export interface SignupRequest {
  email: string
  password: string
  username?: string
}

export interface EmailVerificationRequest {
  email: string
  code: string
}

export interface RegisterResponse {
  email: string
  detail: string
  expires_at: string
  verification_code?: string  // 개발 환경에서만 제공
}

export interface VerificationResponse {
  detail: string
}

export interface AuthResponse {
  access: string
  refresh: string
  user: User
}

export interface User {
  id: number
  email: string
  username: string | null
  first_name: string | null
  last_name: string | null
  profile_image_url: string | null
  provider: string
  role: 'guest' | 'user' | 'seller' | 'admin'  // Role: guest(비회원) > user(일반회원) > seller(판매자) > admin(관리자)
  timezone: string | null
}

