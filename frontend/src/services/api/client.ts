/// <reference types="vite/client" />

import axios, { AxiosError, AxiosHeaders } from "axios";
import type {
  AxiosInstance,
  AxiosResponse,
  InternalAxiosRequestConfig,
} from "axios";

type RetryableRequest = InternalAxiosRequestConfig & { _retry?: boolean };

// 프로덕션에서는 동일 Origin(빈 문자열)을 사용하고,
// 개발 환경에서는 기본값으로 Django 개발 서버 주소를 사용
const baseURL =
  import.meta.env.VITE_API_BASE_URL ||
  (import.meta.env.DEV ? "http://localhost:8000" : "");

const apiClient: AxiosInstance = axios.create({
  baseURL,
  timeout: 30000,
  headers: { "Content-Type": "application/json" },
});

// 요청 인터셉터: access 토큰 삽입
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig): InternalAxiosRequestConfig => {
    const token = localStorage.getItem("access_token");
    if (token) {
      const headers = new AxiosHeaders(config.headers);
      headers.set("Authorization", `Bearer ${token}`);
      config.headers = headers;
    }
    return config;
  },
  (error: AxiosError) => Promise.reject(error)
);

const skipRefreshEndpoints = [
  "/auth/register/",
  "/auth/login/",
  "/auth/register/verify/",
  "/auth/token/refresh/",
  "/auth/google/",
  "/auth/google/callback/",
  "/auth/kakao/",
  "/auth/kakao/callback/",
];

// 동시 401 대응: 단일 refresh 요청만 진행
let refreshPromise: Promise<string | null> | null = null;

// 토큰 갱신 응답 타입 (SimpleJWT ROTATE_REFRESH_TOKENS 설정 시 새 refresh 토큰도 반환)
interface TokenRefreshResponse {
  access?: string;
  refresh?: string;
}

async function refreshAccessToken(): Promise<string | null> {
  if (!refreshPromise) {
    const refreshToken = localStorage.getItem("refresh_token");

    refreshPromise = (
      refreshToken
        ? axios.post<TokenRefreshResponse>(
            `${baseURL}/auth/token/refresh/`,
            { refresh: refreshToken }
          )
        : Promise.resolve({ data: { access: null, refresh: null } })
    )
      .then((response) => {
        // ROTATE_REFRESH_TOKENS 설정으로 새 리프레시 토큰이 발급되면 저장
        // 저장하지 않으면 기존 토큰이 블랙리스트되어 다음 갱신 시 실패
        if (response.data?.refresh) {
          localStorage.setItem("refresh_token", response.data.refresh);
        }
        return response.data?.access ?? null;
      })
      .catch((refreshError: AxiosError<any>) => {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");

        if (refreshError.response?.data?.code === "user_not_found") {
          console.warn("사용자가 존재하지 않습니다. 다시 로그인해주세요.");
        }

        if (typeof window !== "undefined") {
          window.dispatchEvent(new CustomEvent("auth:logout"));
        }

        throw refreshError;
      })
      .finally(() => {
        refreshPromise = null;
      });
  }

  return refreshPromise;
}

// 응답 인터셉터: 401 시 토큰 갱신 후 재시도
apiClient.interceptors.response.use(
  (response: AxiosResponse): AxiosResponse => response,
  async (error: AxiosError): Promise<AxiosResponse | never> => {
    const originalRequest = (error.config || {}) as RetryableRequest;

    const shouldSkipRefresh = skipRefreshEndpoints.some((endpoint) =>
      (originalRequest.url || "").includes(endpoint)
    );

    if (
      error.response?.status === 401 &&
      !originalRequest._retry &&
      !shouldSkipRefresh
    ) {
      originalRequest._retry = true;

      const newAccessToken = await refreshAccessToken();

      if (newAccessToken) {
        // 토큰은 refreshAccessToken() 내부에서 이미 저장됨
        const headers = new AxiosHeaders(originalRequest.headers);
        headers.set("Authorization", `Bearer ${newAccessToken}`);
        originalRequest.headers = headers;
        return apiClient(originalRequest);
      }
    }

    return Promise.reject(error);
  }
);

export default apiClient;
