// OAuth 콜백 처리 유틸리티

/**
 * URL에서 OAuth 토큰 정보를 추출하고 저장
 * 백엔드에서 리다이렉트된 경우 URL 파라미터에서 토큰을 추출
 */
export function handleOAuthCallback(): boolean {
  const urlParams = new URLSearchParams(window.location.search)
  const accessToken = urlParams.get('access_token')
  const refreshToken = urlParams.get('refresh_token')
  const userParam = urlParams.get('user')
  const error = urlParams.get('error')

  if (error) {
    console.error('OAuth 에러:', error)
    return false
  }

  if (accessToken && refreshToken) {
    // 토큰 저장
    localStorage.setItem('access_token', accessToken)
    localStorage.setItem('refresh_token', refreshToken)
    
    // 사용자 정보가 있으면 저장
    if (userParam) {
      try {
        JSON.parse(userParam)
        // 사용자 정보는 나중에 API로 다시 가져올 수 있으므로 선택적 저장
        sessionStorage.setItem('oauth_user', userParam)
      } catch (e) {
        console.warn('사용자 정보 파싱 실패:', e)
      }
    }
    
    // URL에서 토큰 파라미터 제거
    const newUrl = window.location.pathname
    window.history.replaceState({}, document.title, newUrl)
    
    return true
  }

  return false
}

/**
 * 페이지 로드 시 OAuth 콜백 처리
 */
export function initOAuthCallback() {
  if (handleOAuthCallback()) {
    // 토큰이 저장되었으므로 사용자 정보 로드
    window.dispatchEvent(new CustomEvent('oauth:success'))
  }
}

