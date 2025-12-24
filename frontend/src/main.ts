import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import './styles/main.css'
import { initOAuthCallback } from './utils/oauth'
import router from './router'
import { useAuthStore } from './stores/auth'
import { useCartStore } from './stores/cart'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)


// 토큰 있으면 사용자 복구
const authStore = useAuthStore(pinia) // pinia 인스턴스 전달
await authStore.loadUser()

// 장바구니 상태 초기 로드 (비회원 로컬/회원 서버 포함)
const cartStore = useCartStore(pinia)
await cartStore.loadCart()

// OAuth 콜백 처리 초기화
initOAuthCallback()

app.mount('#app')

