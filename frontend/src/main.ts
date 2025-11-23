import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import './styles/main.css'
import { initOAuthCallback } from './utils/oauth'
import router from './router'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)

// OAuth 콜백 처리 초기화
initOAuthCallback()

app.mount('#app')

