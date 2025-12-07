/// <reference types="vite/client" />

import axios, { AxiosError, AxiosHeaders } from 'axios'
import type { AxiosInstance, AxiosResponse, InternalAxiosRequestConfig } from 'axios'

type RetryableRequest = InternalAxiosRequestConfig & { _retry?: boolean }

const baseURL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const apiClient: AxiosInstance = axios.create({
  baseURL,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

// 요청 인터셉터: access 토큰 삽입
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig): InternalAxiosRequestConfig => {
    const token = localStorage.getItem('access_token')
    if (token) {
      const headers = new AxiosHeaders(config.headers)
      headers.set('Authorization', `Bearer ${token}`)
      config.headers = headers
    }
    return config
  },
  (error: AxiosError) => Promise.reject(error)
)

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

// 동시 401 대응: 단일 refresh 요청만 진행
let refreshPromise: Promise<string | null> | null = null

async function refreshAccessToken(): Promise<string | null> {
  if (!refreshPromise) {
    const refreshToken = localStorage.getItem('refresh_token')

    refreshPromise = (refreshToken
      ? axios.post<{ access?: string }>(`${baseURL}/auth/token/refresh/`, {
          refresh: refreshToken,
        })
      : Promise.resolve({ data: { access: null } })
    )
      .then((response) => response.data?.access ?? null)
      .catch((refreshError: AxiosError<any>) => {
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')

        if (refreshError.response?.data?.code === 'user_not_found') {
          console.warn('사용자가 존재하지 않습니다. 다시 로그인해주세요.')
        }

        if (typeof window !== 'undefined') {
          window.dispatchEvent(new CustomEvent('auth:logout'))
        }

        throw refreshError
      })
      .finally(() => {
        refreshPromise = null
      })
  }

  return refreshPromise
}

// 응답 인터셉터: 401 시 토큰 갱신 후 재시도
apiClient.interceptors.response.use(
  (response: AxiosResponse): AxiosResponse => response,
  async (error: AxiosError): Promise<AxiosResponse | never> => {
    const originalRequest = (error.config || {}) as RetryableRequest

    const shouldSkipRefresh = skipRefreshEndpoints.some((endpoint) =>
      (originalRequest.url || '').includes(endpoint)
    )

    if (
      error.response?.status === 401 &&
      !originalRequest._retry &&
      !shouldSkipRefresh
    ) {
      originalRequest._retry = true

      const newAccessToken = await refreshAccessToken()

      if (newAccessToken) {
        localStorage.setItem('access_token', newAccessToken)
        const headers = new AxiosHeaders(originalRequest.headers)
        headers.set('Authorization', `Bearer ${newAccessToken}`)
        originalRequest.headers = headers
        return apiClient(originalRequest)
      }
    }

    return Promise.reject(error)
  }
)

export default apiClient
