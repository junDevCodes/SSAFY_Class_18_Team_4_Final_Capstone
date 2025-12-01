import axios from 'axios'

// Axios 인스턴스 생성
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  timeout: 30000,  // 이메일 발송 대기 시간을 고려하여 30초로 증가
  headers: {
    'Content-Type': 'application/json',
  },
})

// 요청 인터셉터 - 토큰 추가
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 응답 인터셉터 - 에러 처리 및 토큰 갱신
apiClient.interceptors.response.use(
  (response) => {
    return response
  },
  async (error) => {
    const originalRequest = error.config

    // 회원가입/로그인 엔드포인트는 토큰 갱신 시도하지 않음
    const skipRefreshEndpoints = [
      '/auth/register/',
      '/auth/login/',
      '/auth/register/verify/',
      '/auth/token/refresh/',
      '/auth/google/',
      '/auth/google/callback/',
      '/auth/kakao/',
      '/auth/kakao/callback/',
    ]
    
    const shouldSkipRefresh = skipRefreshEndpoints.some(endpoint => 
      originalRequest.url?.includes(endpoint)
    )

    // 401 에러이고 토큰 갱신이 아직 시도되지 않은 경우
    if (
      error.response?.status === 401 && 
      !originalRequest._retry && 
      !shouldSkipRefresh
    ) {
      originalRequest._retry = true

      try {
        const refreshToken = localStorage.getItem('refresh_token')
        if (refreshToken) {
          // 토큰 갱신 시도
          const response = await axios.post(
            `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/auth/token/refresh/`,
            { refresh: refreshToken }
          )

          if (response.data.access) {
            localStorage.setItem('access_token', response.data.access)
            // 원래 요청 재시도
            originalRequest.headers.Authorization = `Bearer ${response.data.access}`
            return apiClient(originalRequest)
          }
        }
      } catch (refreshError: any) {
        // 토큰 갱신 실패 시 로그아웃 처리
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        
        // user_not_found 에러인 경우 명확한 메시지
        if (refreshError.response?.data?.code === 'user_not_found') {
          console.warn('사용자가 존재하지 않습니다. 다시 로그인해주세요.')
        }
        
        // 로그인 모달 열기 (SPA이므로 페이지 리다이렉트 대신)
        // 단, 회원가입/로그인 요청 중에는 모달을 열지 않음
        if (!shouldSkipRefresh) {
          window.dispatchEvent(new CustomEvent('auth:logout'))
        }
        return Promise.reject(refreshError)
      }
    }

    return Promise.reject(error)
  }
)

export default apiClient

