<template>
  <div class="mypage-layout">
    <div class="container">
      <!-- Page Header -->
      <div class="page-header">
        <div class="header-content">
          <h1 class="page-title">마이페이지</h1>
          <p v-if="authStore.user" class="user-greeting">
            안녕하세요, <strong>{{ authStore.displayName || authStore.user?.email }}</strong>님
          </p>
        </div>
      </div>

      <div class="mypage-content">
        <!-- Sidebar Navigation -->
        <aside class="mypage-sidebar">
          <nav class="sidebar-nav">
            <div class="nav-section">
              <h2 class="nav-title">내 정보</h2>
              <ul class="nav-list">
                <li>
                  <router-link
                    to="/mypage/profile"
                    class="nav-link"
                    active-class="active"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
                    </svg>
                    <span>프로필 관리</span>
                  </router-link>
                </li>
                <li>
                  <router-link
                    to="/mypage/addresses"
                    class="nav-link"
                    active-class="active"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M15 10.5a3 3 0 11-6 0 3 3 0 016 0z" />
                      <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1115 0z" />
                    </svg>
                    <span>배송지 관리</span>
                  </router-link>
                </li>
                <li>
                  <router-link
                    to="/mypage/orders"
                    class="nav-link"
                    active-class="active"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M9 12h3.75M9 15h3.75M9 18h3.75M3 6h3m2.5-6h7A2.5 2.5 0 0116.5 2.5v19A2.5 2.5 0 0114 24H6a2.5 2.5 0 01-2.5-2.5v-19A2.5 2.5 0 016 0z" />
                    </svg>
                    <span>주문 내역</span>
                  </router-link>
                </li>
                <li>
                  <router-link
                    to="/wishlist"
                    class="nav-link"
                    active-class="active"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M21 8.25c0-2.485-2.099-4.5-4.688-4.5-1.935 0-3.597 1.126-4.312 2.733-.715-1.607-2.377-2.733-4.313-2.733C5.1 3.75 3 5.765 3 8.25c0 7.22 9 12 9 12s9-4.78 9-12z" />
                    </svg>
                    <span>찜 목록</span>
                  </router-link>
                </li>
                <li>
                  <router-link
                    to="/cart"
                    class="nav-link"
                    active-class="active"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M2.25 3h1.386c.51 0 .955.343 1.087.835l.383 1.437M7.5 14.25a3 3 0 00-3 3h15.75m-12.75-3h11.218c1.121-2.3 2.1-4.684 2.924-7.138a60.114 60.114 0 00-16.536-1.84M7.5 14.25L5.106 5.272M6 20.25a.75.75 0 11-1.5 0 .75.75 0 011.5 0zm12.75 0a.75.75 0 11-1.5 0 .75.75 0 011.5 0z" />
                    </svg>
                    <span>장바구니</span>
                    <span v-if="cartStore.count > 0" class="badge">{{ cartStore.count }}</span>
                  </router-link>
                </li>
              </ul>
            </div>

            <div v-if="authStore.isSeller" class="nav-section">
              <h2 class="nav-title">판매자 메뉴</h2>
              <ul class="nav-list">
                <li>
                  <router-link
                    to="/seller/dashboard"
                    class="nav-link"
                    active-class="active"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" />
                    </svg>
                    <span>판매자 대시보드</span>
                  </router-link>
                </li>
                <li>
                  <router-link
                    to="/seller/products"
                    class="nav-link"
                    active-class="active"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M20.25 7.5l-.625 10.632a2.25 2.25 0 01-2.247 2.118H6.622a2.25 2.25 0 01-2.247-2.118L3.75 7.5M10 11.25h4M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125z" />
                    </svg>
                    <span>상품 관리</span>
                  </router-link>
                </li>
              </ul>
            </div>

            <div v-else class="seller-cta">
              <div class="seller-cta-icon">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M13.5 21v-7.5a.75.75 0 01.75-.75h3a.75.75 0 01.75.75V21m-4.5 0H2.36m11.14 0H18m0 0h3.64m-1.39 0V9.349m-16.5 11.65V9.35m0 0a3.001 3.001 0 003.75-.615A2.993 2.993 0 009.75 9.75c.896 0 1.7-.393 2.25-1.016a2.993 2.993 0 002.25 1.016c.896 0 1.7-.393 2.25-1.016a3.001 3.001 0 003.75.614m-16.5 0a3.004 3.004 0 01-.621-4.72L4.911 3.69A3 3 0 017.5 3.75h9a3 3 0 012.589 1.44l1.21 1.389a3 3 0 01.621 4.72m-16.5 0a3 3 0 00-.621 4.72L4.911 12.75m0 0l1.529 1.756m0 0l1.39 1.597m-2.919-3.353l-1.39-1.597m0 0A3.001 3.001 0 003.75 9.75a3 3 0 00-.621 4.72" />
                </svg>
              </div>
              <p class="seller-cta-text">판매자로 등록하고<br>상품을 판매해보세요</p>
              <router-link to="/seller/register" class="btn-seller-register">
                판매자 등록하기
              </router-link>
            </div>
          </nav>
        </aside>

        <!-- Main Content -->
        <main class="mypage-main">
          <router-view />
        </main>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useCartStore } from '@/stores/cart'

const authStore = useAuthStore()
const cartStore = useCartStore()

onMounted(() => {
  // Load cart count for badge
  if (authStore.isAuthenticated) {
    cartStore.loadSummary()
  }
})
</script>

<style scoped>
.mypage-layout {
  min-height: calc(100vh - 4rem);
  background: linear-gradient(to bottom, #fafafa 0%, #ffffff 100%);
  padding-top: 5rem; /* 헤더 높이(64px) + 여백 */
  padding-bottom: 4rem;
}

.container {
  max-width: 1280px;
  margin: 0 auto;
  padding: 0 1.5rem;
}

/* Page Header */
.page-header {
  margin-bottom: 3rem;
}

.header-content {
  padding-bottom: 1.5rem;
  border-bottom: 1px solid rgba(95, 0, 128, 0.1);
}

.page-title {
  font-size: 2.25rem;
  font-weight: 700;
  color: #1a1a1a;
  margin-bottom: 0.75rem;
  letter-spacing: -0.02em;
}

.user-greeting {
  font-size: 1rem;
  color: #666;
  line-height: 1.6;
}

.user-greeting strong {
  color: #5f0080;
  font-weight: 600;
}

/* MyPage Content */
.mypage-content {
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: 2.5rem;
  align-items: start;
}

/* Sidebar */
.mypage-sidebar {
  background: white;
  border-radius: 12px;
  padding: 2rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05), 0 4px 12px rgba(0, 0, 0, 0.03);
  position: sticky;
  top: 5rem;
  border: 1px solid rgba(0, 0, 0, 0.04);
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.nav-section {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.nav-title {
  font-size: 0.75rem;
  font-weight: 700;
  color: #999;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  margin-bottom: 0.5rem;
}

.nav-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: 0.875rem;
  padding: 0.875rem 1rem;
  color: #666;
  text-decoration: none;
  border-radius: 8px;
  font-size: 0.9375rem;
  font-weight: 500;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
}

.nav-link svg {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
  stroke-width: 1.5;
  transition: transform 0.2s;
}

.nav-link:hover {
  background: rgba(95, 0, 128, 0.05);
  color: #5f0080;
  transform: translateX(2px);
}

.nav-link:hover svg {
  transform: scale(1.05);
}

.nav-link.active {
  background: linear-gradient(135deg, rgba(95, 0, 128, 0.1) 0%, rgba(95, 0, 128, 0.05) 100%);
  color: #5f0080;
  font-weight: 600;
}

.nav-link.active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 60%;
  background: #5f0080;
  border-radius: 0 2px 2px 0;
}

.nav-link .badge {
  margin-left: auto;
  padding: 0.125rem 0.5rem;
  background: #5f0080;
  color: white;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 700;
  min-width: 20px;
  text-align: center;
  line-height: 1.4;
}

/* Seller CTA */
.seller-cta {
  padding: 1.75rem 1.5rem;
  background: linear-gradient(135deg, #5f0080 0%, #4c0066 100%);
  border-radius: 12px;
  text-align: center;
  color: white;
  position: relative;
  overflow: hidden;
}

.seller-cta::before {
  content: '';
  position: absolute;
  top: -50%;
  right: -50%;
  width: 200%;
  height: 200%;
  background: radial-gradient(circle, rgba(255, 255, 255, 0.1) 0%, transparent 70%);
  animation: pulse 4s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { transform: scale(1); opacity: 0.5; }
  50% { transform: scale(1.1); opacity: 0.8; }
}

.seller-cta-icon {
  width: 48px;
  height: 48px;
  margin: 0 auto 1rem;
  background: rgba(255, 255, 255, 0.15);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  z-index: 1;
}

.seller-cta-icon svg {
  width: 24px;
  height: 24px;
  stroke-width: 1.5;
}

.seller-cta-text {
  font-size: 0.875rem;
  line-height: 1.6;
  margin-bottom: 1.25rem;
  position: relative;
  z-index: 1;
}

.btn-seller-register {
  display: inline-block;
  padding: 0.75rem 1.5rem;
  background: white;
  color: #5f0080;
  text-decoration: none;
  border-radius: 8px;
  font-size: 0.875rem;
  font-weight: 700;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  z-index: 1;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.btn-seller-register:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

/* Main Content */
.mypage-main {
  background: white;
  border-radius: 12px;
  padding: 2.5rem;
  min-height: 600px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05), 0 4px 12px rgba(0, 0, 0, 0.03);
  border: 1px solid rgba(0, 0, 0, 0.04);
}

/* Responsive */
@media (max-width: 1024px) {
  .mypage-content {
    grid-template-columns: 260px 1fr;
    gap: 2rem;
  }

  .mypage-sidebar {
    padding: 1.5rem;
  }
}

@media (max-width: 768px) {
  .mypage-layout {
    padding-top: 4.5rem;
    padding-bottom: 2rem;
  }

  .container {
    padding: 0 1rem;
  }

  .page-header {
    margin-bottom: 2rem;
  }

  .page-title {
    font-size: 1.75rem;
  }

  .mypage-content {
    grid-template-columns: 1fr;
    gap: 1.5rem;
  }

  .mypage-sidebar {
    position: static;
    order: -1;
  }

  .mypage-main {
    padding: 1.5rem;
  }
}

@media (max-width: 480px) {
  .mypage-layout {
    padding-top: 4rem;
  }

  .mypage-main {
    padding: 1.25rem;
    border-radius: 8px;
  }

  .mypage-sidebar {
    padding: 1.25rem;
    border-radius: 8px;
  }

  .nav-link {
    padding: 0.75rem;
    font-size: 0.875rem;
  }

  .nav-link svg {
    width: 18px;
    height: 18px;
  }

  .seller-cta {
    padding: 1.5rem 1.25rem;
  }
}
</style>
