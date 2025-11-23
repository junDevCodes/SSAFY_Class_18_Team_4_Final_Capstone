<template>
  <div class="mypage-layout">
    <div class="container">
      <!-- Page Header -->
      <div class="page-header">
        <h1 class="page-title">마이페이지</h1>
        <p v-if="authStore.user" class="user-greeting">
          안녕하세요, <strong>{{ authStore.user.name || authStore.user.email }}</strong>님
        </p>
      </div>

      <div class="mypage-content">
        <!-- Sidebar Navigation -->
        <aside class="mypage-sidebar">
          <nav class="sidebar-nav">
            <h2 class="nav-title">내 정보</h2>
            <ul class="nav-list">
              <li>
                <router-link
                  to="/mypage/profile"
                  class="nav-link"
                  active-class="active"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                  </svg>
                  <span>프로필 관리</span>
                </router-link>
              </li>
              <li>
                <router-link
                  to="/mypage/orders"
                  class="nav-link"
                  active-class="active"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z" />
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
                  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
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
                  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" />
                  </svg>
                  <span>장바구니</span>
                  <span v-if="cartStore.count > 0" class="badge">{{ cartStore.count }}</span>
                </router-link>
              </li>
            </ul>

            <h2 v-if="authStore.isSeller" class="nav-title">판매자 메뉴</h2>
            <ul v-if="authStore.isSeller" class="nav-list">
              <li>
                <router-link
                  to="/seller/dashboard"
                  class="nav-link"
                  active-class="active"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
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
                  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
                  </svg>
                  <span>상품 관리</span>
                </router-link>
              </li>
            </ul>

            <div v-else class="seller-cta">
              <p>판매자로 등록하고 상품을 판매하세요</p>
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
  min-height: 100vh;
  background: #f8f9fa;
  padding: 2rem 0;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1rem;
}

/* Page Header */
.page-header {
  margin-bottom: 2rem;
}

.page-title {
  font-size: 2rem;
  font-weight: 700;
  color: #1a1a1a;
  margin-bottom: 0.5rem;
}

.user-greeting {
  font-size: 1rem;
  color: #666;
}

.user-greeting strong {
  color: #00a86b;
  font-weight: 600;
}

/* MyPage Content */
.mypage-content {
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: 2rem;
  align-items: start;
}

/* Sidebar */
.mypage-sidebar {
  background: white;
  border-radius: 8px;
  padding: 1.5rem;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  position: sticky;
  top: 2rem;
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.nav-title {
  font-size: 0.875rem;
  font-weight: 700;
  color: #999;
  text-transform: uppercase;
  letter-spacing: 0.05em;
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
  gap: 0.75rem;
  padding: 0.875rem 1rem;
  color: #666;
  text-decoration: none;
  border-radius: 6px;
  font-size: 0.9375rem;
  font-weight: 500;
  transition: all 0.2s;
  position: relative;
}

.nav-link svg {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
}

.nav-link:hover {
  background: #f8f9fa;
  color: #00a86b;
}

.nav-link.active {
  background: #e8f5f1;
  color: #00a86b;
  font-weight: 600;
}

.nav-link .badge {
  margin-left: auto;
  padding: 0.125rem 0.5rem;
  background: #00a86b;
  color: white;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 700;
  min-width: 20px;
  text-align: center;
}

/* Seller CTA */
.seller-cta {
  padding: 1.5rem;
  background: linear-gradient(135deg, #00a86b 0%, #008c5a 100%);
  border-radius: 8px;
  text-align: center;
  color: white;
}

.seller-cta p {
  font-size: 0.875rem;
  line-height: 1.5;
  margin-bottom: 1rem;
}

.btn-seller-register {
  display: inline-block;
  padding: 0.625rem 1.25rem;
  background: white;
  color: #00a86b;
  text-decoration: none;
  border-radius: 6px;
  font-size: 0.875rem;
  font-weight: 700;
  transition: all 0.2s;
}

.btn-seller-register:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
}

/* Main Content */
.mypage-main {
  background: white;
  border-radius: 8px;
  padding: 2rem;
  min-height: 600px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

/* Responsive */
@media (max-width: 968px) {
  .mypage-content {
    grid-template-columns: 240px 1fr;
  }

  .mypage-sidebar {
    padding: 1.25rem;
  }
}

@media (max-width: 768px) {
  .mypage-layout {
    padding: 1rem 0;
  }

  .page-title {
    font-size: 1.5rem;
  }

  .mypage-content {
    grid-template-columns: 1fr;
  }

  .mypage-sidebar {
    position: static;
  }

  .mypage-main {
    padding: 1.5rem;
  }
}

@media (max-width: 480px) {
  .mypage-main {
    padding: 1rem;
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
    padding: 1.25rem;
  }
}
</style>
