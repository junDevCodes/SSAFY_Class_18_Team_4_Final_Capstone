/**
 * useTokenRefresh - 선제적 JWT 토큰 갱신 Composable
 *
 * 기능:
 * 1. 토큰 만료 전 자동 갱신 (만료 2분 전)
 * 2. 사용자 활동 감지 기반 갱신 (마우스/키보드/터치 이벤트)
 * 3. 탭 포커스 시 토큰 유효성 체크 및 갱신
 * 4. 주기적 갱신 체크 (5분마다)
 */
import { ref, onMounted, onUnmounted } from 'vue'
import axios from 'axios'

// 토큰 갱신 응답 타입
interface TokenRefreshResponse {
  access: string
  refresh?: string
}

// JWT 페이로드에서 만료 시간 추출
const getTokenExpiry = (token: string | null): number | null => {
  if (!token) return null
  try {
    const parts = token.split('.')
    // JWT는 header.payload.signature 형식 (3개 파트)
    if (parts.length !== 3) return null

    // Base64 URL Safe 디코딩
    const base64 = parts[1].replace(/-/g, '+').replace(/_/g, '/')
    const payload = JSON.parse(atob(base64))

    // exp 클레임 검증 (숫자 타입이어야 함)
    if (typeof payload.exp !== 'number') return null

    return payload.exp * 1000 // exp는 초 단위이므로 밀리초로 변환
  } catch {
    return null
  }
}

// 토큰이 곧 만료되는지 확인 (기본 2분 전)
const isTokenExpiringSoon = (token: string | null, thresholdMs: number = 2 * 60 * 1000): boolean => {
  const expiry = getTokenExpiry(token)
  if (!expiry) return true // 토큰이 없거나 파싱 불가하면 갱신 필요
  return Date.now() >= expiry - thresholdMs
}

// 토큰이 이미 만료되었는지 확인
const isTokenExpired = (token: string | null): boolean => {
  const expiry = getTokenExpiry(token)
  if (!expiry) return true
  return Date.now() >= expiry
}

export function useTokenRefresh() {
  // API Base URL (client.ts와 동일한 로직)
  const baseURL =
    import.meta.env.VITE_API_BASE_URL ||
    (import.meta.env.DEV ? 'http://localhost:8000' : '')

  const isRefreshing = ref(false)
  const lastRefreshTime = ref<number>(0)
  const lastActivityTime = ref<number>(Date.now())

  // 갱신 간격 제한: 최소 30초 간격
  const MIN_REFRESH_INTERVAL = 30 * 1000
  // 주기적 체크 간격: 5분
  const CHECK_INTERVAL = 5 * 60 * 1000
  // 활동 기반 갱신 쿨다운: 1분
  const ACTIVITY_COOLDOWN = 60 * 1000

  let checkIntervalId: number | undefined
  let activityTimeoutId: number | undefined

  // 토큰 갱신 실행
  const refreshToken = async (): Promise<boolean> => {
    // 이미 갱신 중이거나 최근에 갱신했으면 스킵
    if (isRefreshing.value) return false
    if (Date.now() - lastRefreshTime.value < MIN_REFRESH_INTERVAL) return false

    const refreshTokenValue = localStorage.getItem('refresh_token')
    if (!refreshTokenValue) return false

    // 리프레시 토큰도 만료되었으면 갱신 불가 - 로그아웃 필요
    if (isTokenExpired(refreshTokenValue)) {
      console.warn('리프레시 토큰이 만료되었습니다. 다시 로그인이 필요합니다.')
      // 토큰 삭제 및 로그아웃 이벤트 발생
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      if (typeof window !== 'undefined') {
        window.dispatchEvent(new CustomEvent('auth:logout'))
      }
      return false
    }

    isRefreshing.value = true

    try {
      const response = await axios.post<TokenRefreshResponse>(
        `${baseURL}/auth/token/refresh/`,
        { refresh: refreshTokenValue }
      )

      if (response.data.access) {
        localStorage.setItem('access_token', response.data.access)
      }
      // ROTATE_REFRESH_TOKENS 설정 시 새 리프레시 토큰도 저장
      if (response.data.refresh) {
        localStorage.setItem('refresh_token', response.data.refresh)
      }

      lastRefreshTime.value = Date.now()
      return true
    } catch (error: any) {
      console.error('토큰 갱신 실패:', error)
      // 401/403 에러 시 토큰 무효화 및 로그아웃 처리
      if (error.response?.status === 401 || error.response?.status === 403) {
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        if (typeof window !== 'undefined') {
          window.dispatchEvent(new CustomEvent('auth:logout'))
        }
      }
      return false
    } finally {
      isRefreshing.value = false
    }
  }

  // 토큰 상태 체크 및 필요시 갱신
  const checkAndRefreshToken = async (): Promise<void> => {
    const accessToken = localStorage.getItem('access_token')
    const refreshTokenValue = localStorage.getItem('refresh_token')

    // 로그인 상태가 아니면 스킵
    if (!accessToken || !refreshTokenValue) return

    // 액세스 토큰이 곧 만료되면 갱신
    if (isTokenExpiringSoon(accessToken)) {
      await refreshToken()
    }
  }

  // 사용자 활동 감지 핸들러
  const handleUserActivity = (): void => {
    lastActivityTime.value = Date.now()

    // 이미 타이머가 있으면 클리어
    if (activityTimeoutId) {
      clearTimeout(activityTimeoutId)
    }

    // 활동 후 쿨다운 시간이 지난 뒤 토큰 체크
    activityTimeoutId = window.setTimeout(() => {
      checkAndRefreshToken()
    }, ACTIVITY_COOLDOWN)
  }

  // 탭 포커스 핸들러 (다른 탭에서 돌아왔을 때)
  const handleVisibilityChange = (): void => {
    if (document.visibilityState === 'visible') {
      // 탭이 활성화되면 즉시 토큰 체크
      checkAndRefreshToken()
    }
  }

  // 주기적 체크 시작
  const startPeriodicCheck = (): void => {
    if (checkIntervalId) return

    checkIntervalId = window.setInterval(() => {
      checkAndRefreshToken()
    }, CHECK_INTERVAL)
  }

  // 주기적 체크 중지
  const stopPeriodicCheck = (): void => {
    if (checkIntervalId) {
      clearInterval(checkIntervalId)
      checkIntervalId = undefined
    }
  }

  // 활동 이벤트 리스너 등록
  const registerActivityListeners = (): void => {
    // 사용자 활동 이벤트 (passive: true로 성능 최적화)
    const options = { passive: true }
    window.addEventListener('mousemove', handleUserActivity, options)
    window.addEventListener('mousedown', handleUserActivity, options)
    window.addEventListener('keydown', handleUserActivity, options)
    window.addEventListener('touchstart', handleUserActivity, options)
    window.addEventListener('scroll', handleUserActivity, options)

    // 탭 포커스 이벤트
    document.addEventListener('visibilitychange', handleVisibilityChange)
  }

  // 활동 이벤트 리스너 해제
  const unregisterActivityListeners = (): void => {
    window.removeEventListener('mousemove', handleUserActivity)
    window.removeEventListener('mousedown', handleUserActivity)
    window.removeEventListener('keydown', handleUserActivity)
    window.removeEventListener('touchstart', handleUserActivity)
    window.removeEventListener('scroll', handleUserActivity)
    document.removeEventListener('visibilitychange', handleVisibilityChange)

    if (activityTimeoutId) {
      clearTimeout(activityTimeoutId)
      activityTimeoutId = undefined
    }
  }

  // Composable 시작
  const start = (): void => {
    // 초기 토큰 체크
    checkAndRefreshToken()
    // 주기적 체크 시작
    startPeriodicCheck()
    // 활동 리스너 등록
    registerActivityListeners()
  }

  // Composable 중지
  const stop = (): void => {
    stopPeriodicCheck()
    unregisterActivityListeners()
  }

  // 컴포넌트 마운트/언마운트 시 자동 시작/중지
  onMounted(() => {
    start()
  })

  onUnmounted(() => {
    stop()
  })

  return {
    isRefreshing,
    lastRefreshTime,
    lastActivityTime,
    refreshToken,
    checkAndRefreshToken,
    start,
    stop,
  }
}
