/**
 * Vue Router 설정
 */
import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

// Lazy load pages
const HomePage = () => import('@/pages/HomePage.vue')
const SearchPage = () => import('@/pages/SearchPage.vue')
const ProductDetailPage = () => import('@/pages/ProductDetailPage.vue')
const CartPage = () => import('@/pages/CartPage.vue')
const WishlistPage = () => import('@/pages/WishlistPage.vue')
const CheckoutPage = () => import('@/pages/CheckoutPage.vue')

// MyPage
const MyPageLayout = () => import('@/pages/mypage/MyPageLayout.vue')
const MyPageProfile = () => import('@/pages/mypage/ProfilePage.vue')
const MyPageOrders = () => import('@/pages/mypage/OrdersPage.vue')
const MyPageOrderDetail = () => import('@/pages/mypage/OrderDetailPage.vue')

// Seller
const SellerDashboard = () => import('@/pages/seller/DashboardPage.vue')
const SellerProducts = () => import('@/pages/seller/ProductsPage.vue')
const SellerProductCreate = () => import('@/pages/seller/ProductCreatePage.vue')
const SellerProductEdit = () => import('@/pages/seller/ProductEditPage.vue')
const SellerRegister = () => import('@/pages/seller/RegisterPage.vue')

// Brand Mall
const BrandMallPage = () => import('@/pages/brand/BrandMallPage.vue')
const BrandDetailPage = () => import('@/pages/brand/BrandDetailPage.vue')

const routes: RouteRecordRaw[] = [
  // 메인
  {
    path: '/',
    name: 'home',
    component: HomePage,
    meta: { title: '홈' }
  },

  // 검색
  {
    path: '/search',
    name: 'search',
    component: SearchPage,
    meta: { title: '검색' }
  },

  // 상품 상세
  {
    path: '/products/:slug',
    name: 'product-detail',
    component: ProductDetailPage,
    meta: { title: '상품 상세' }
  },

  // 장바구니
  {
    path: '/cart',
    name: 'cart',
    component: CartPage,
    meta: { title: '장바구니', requiresAuth: true }
  },

  // 찜 목록
  {
    path: '/wishlist',
    name: 'wishlist',
    component: WishlistPage,
    meta: { title: '찜 목록', requiresAuth: true }
  },

  // 주문/결제
  {
    path: '/checkout',
    name: 'checkout',
    component: CheckoutPage,
    meta: { title: '주문/결제', requiresAuth: true }
  },

  // 마이페이지
  {
    path: '/mypage',
    component: MyPageLayout,
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        redirect: '/mypage/profile'
      },
      {
        path: 'profile',
        name: 'mypage-profile',
        component: MyPageProfile,
        meta: { title: '프로필 관리' }
      },
      {
        path: 'orders',
        name: 'mypage-orders',
        component: MyPageOrders,
        meta: { title: '주문 내역' }
      },
      {
        path: 'orders/:id',
        name: 'mypage-order-detail',
        component: MyPageOrderDetail,
        meta: { title: '주문 상세' }
      }
    ]
  },

  // 판매자 등록
  {
    path: '/seller/register',
    name: 'seller-register',
    component: SellerRegister,
    meta: { title: '판매자 등록', requiresAuth: true }
  },

  // 판매자 대시보드
  {
    path: '/seller/dashboard',
    name: 'seller-dashboard',
    component: SellerDashboard,
    meta: { title: '판매자 대시보드', requiresAuth: true, requiresSeller: true }
  },

  // 판매자 상품 관리
  {
    path: '/seller/products',
    name: 'seller-products',
    component: SellerProducts,
    meta: { title: '상품 관리', requiresAuth: true, requiresSeller: true }
  },

  // 판매자 상품 등록
  {
    path: '/seller/products/create',
    name: 'seller-product-create',
    component: SellerProductCreate,
    meta: { title: '상품 등록', requiresAuth: true, requiresSeller: true }
  },

  // 판매자 상품 수정
  {
    path: '/seller/products/:id/edit',
    name: 'seller-product-edit',
    component: SellerProductEdit,
    meta: { title: '상품 수정', requiresAuth: true, requiresSeller: true }
  },

  // 브랜드몰
  {
    path: '/brands',
    name: 'brand-mall',
    component: BrandMallPage,
    meta: { title: '브랜드몰' }
  },

  // 브랜드 상세
  {
    path: '/brands/:slug',
    name: 'brand-detail',
    component: BrandDetailPage,
    meta: { title: '브랜드 상세' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) {
      return savedPosition
    }
    if (to.hash) {
      return { el: to.hash, behavior: 'smooth' }
    }
    return { top: 0 }
  }
})

// Navigation Guard
router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()

  // 페이지 타이틀 설정
  document.title = to.meta.title
    ? `${to.meta.title} | 농산물 전자상거래`
    : '농산물 전자상거래'

  // 인증이 필요한 페이지
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    // 로그인 모달 열기 이벤트 발생
    window.dispatchEvent(new CustomEvent('auth:required'))
    return next(false)
  }

  // 판매자 권한이 필요한 페이지
  if (to.meta.requiresSeller && !authStore.isSeller) {
    // 판매자가 아니면 판매자 등록 페이지로
    if (to.path !== '/seller/register') {
      return next('/seller/register')
    }
  }

  next()
})

export default router
