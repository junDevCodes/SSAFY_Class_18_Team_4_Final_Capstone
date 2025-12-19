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
  verification_code?: string // 개발 환경에서만 제공
}

export interface VerificationResponse {
  detail: string
}

export interface UserProfile {
  profile_image_url: string | null
  phone_number: string | null
  date_of_birth: string | null
  gender: 'male' | 'female' | 'other' | 'prefer_not_to_say' | null
  timezone: string
  language: string
  notification_enabled: boolean
  marketing_agreed: boolean
}

export interface User {
  id: number
  email: string
  username: string
  profile_image_url: string | null
  role: 'guest' | 'user' | 'seller' | 'admin'
  timezone: string
  profile?: UserProfile | null
}

export interface AuthResponse {
  access: string
  refresh: string
  user: User
}

// 별칭 추가 (환형)
export type RegisterRequest = SignupRequest
export interface LoginResponse {
  access: string
  refresh: string
  user: User
  verification_code?: string
  message?: string
}

// ==================== 배송지 타입(ERD V2.1) ====================
export interface UserAddress {
  id: number
  address_name: string // 배송지 이름 (ex. '집', '회사')
  recipient_name: string // 수령인
  recipient_phone: string // 수령인 연락처
  postal_code: string // 우편번호
  address_line1: string // 기본 주소
  address_line2: string | null // 상세 주소
  delivery_memo: string | null // 배송 요청사항
  is_default: boolean // 기본 배송지 여부
  created_at: string // 생성일시
  updated_at: string // 수정일시
}

export interface UserAddressRequest {
  address_name: string // 배송지 이름
  recipient_name: string // 수령인 이름
  recipient_phone: string // 수령인 연락처
  postal_code: string // 우편번호
  address_line1: string // 기본 주소
  address_line2?: string | null // 상세 주소
  delivery_memo?: string | null // 배송 요청사항
  is_default?: boolean // 기본 배송지 여부 (기본: false)
}

export interface AddressListResponse {
  count: number
  next: string | null
  previous: string | null
  results: UserAddress[]
}
