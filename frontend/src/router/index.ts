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
const AllProductsPage = () => import('@/pages/AllProductsPage.vue')
const BestPage = () => import('@/pages/BestPage.vue')
const NewPage = () => import('@/pages/NewPage.vue')
const SelfMallPage = () => import('@/pages/SelfMallPage.vue')
const FreshMallPage = () => import('@/pages/FreshMallPage.vue')

// MyPage
const MyPageLayout = () => import('@/pages/mypage/MyPageLayout.vue')
const MyPageProfile = () => import('@/pages/mypage/ProfilePage.vue')
const MyPageOrders = () => import('@/pages/mypage/OrdersPage.vue')
const MyPageOrderDetail = () => import('@/pages/mypage/OrderDetailPage.vue')
const MyPageAddresses = () => import('@/pages/mypage/AddressesPage.vue')

// Seller
const SellerDashboard = () => import('@/pages/seller/DashboardPage.vue')
const SellerProducts = () => import('@/pages/seller/ProductsPage.vue')
const SellerProductCreate = () => import('@/pages/seller/ProductCreatePage.vue')
const SellerProductEdit = () => import('@/pages/seller/ProductEditPage.vue')
const SellerRegister = () => import('@/pages/seller/RegisterPage.vue')
const SellerAnalytics = () => import('@/pages/seller/AnalyticsPage.vue')
const AdminAnalytics = () => import('@/pages/admin/AdminAnalyticsPage.vue')

// Brand
const BrandMallPage = () => import('@/pages/brand/BrandMallPage.vue')
const BrandDetailPage = () => import('@/pages/brand/BrandDetailPage.vue')
const BrandStoryPage = () => import('@/pages/BrandStoryPage.vue')

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'home',
    component: HomePage,
    meta: { title: '홈' }
  },
  {
    path: '/admin/analytics',
    name: 'admin-analytics',
    component: AdminAnalytics,
    meta: { title: '관리자 분석' }
  },
  {
    path: '/search',
    name: 'search',
    component: SearchPage,
    meta: { title: '검색' }
  },
  {
    path: '/products',
    name: 'products',
    component: AllProductsPage,
    meta: { title: '전체 상품' }
  },
  {
    path: '/best',
    name: 'best-products',
    component: BestPage,
    meta: { title: '베스트' }
  },
  {
    path: '/new',
    name: 'new-products',
    component: NewPage,
    meta: { title: '신상품' }
  },
  {
    path: '/self-mall',
    name: 'self-mall',
    component: SelfMallPage,
    meta: { title: 'SelF 몰' }
  },
  {
    path: '/fresh-mall',
    name: 'fresh-mall',
    component: FreshMallPage,
    meta: { title: 'Fresh 몰' }
  },
  {
    path: '/products/:slug',
    name: 'product-detail',
    component: ProductDetailPage,
    meta: { title: '상품 상세' }
  },
  {
    path: '/cart',
    name: 'cart',
    component: CartPage,
    meta: { title: '장바구니' }
  },
  {
    path: '/wishlist',
    name: 'wishlist',
    component: WishlistPage,
    meta: { title: '위시리스트', requiresAuth: true }
  },
  {
    path: '/checkout',
    name: 'checkout',
    component: CheckoutPage,
    meta: { title: '주문/결제', requiresAuth: true }
  },
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
      },
      {
        path: 'addresses',
        name: 'mypage-addresses',
        component: MyPageAddresses,
        meta: { title: '배송지 관리' }
      }
    ]
  },
  {
    path: '/seller/register',
    name: 'seller-register',
    component: SellerRegister,
    meta: { title: '판매자 등록', requiresAuth: true }
  },
  {
    path: '/seller/dashboard',
    name: 'seller-dashboard',
    component: SellerDashboard,
    meta: { title: '판매자 대시보드', requiresAuth: true, requiresSeller: true }
  },
  {
    path: '/seller/analytics',
    name: 'seller-analytics',
    component: SellerAnalytics,
    meta: { title: '매출·환불 분석', requiresAuth: true, requiresSeller: true }
  },
  {
    path: '/seller/products',
    name: 'seller-products',
    component: SellerProducts,
    meta: { title: '상품 관리', requiresAuth: true, requiresSeller: true }
  },
  {
    path: '/seller/products/create',
    name: 'seller-product-create',
    component: SellerProductCreate,
    meta: { title: '상품 등록', requiresAuth: true, requiresSeller: true }
  },
  {
    path: '/seller/products/:id/edit',
    name: 'seller-product-edit',
    component: SellerProductEdit,
    meta: { title: '상품 수정', requiresAuth: true, requiresSeller: true }
  },
  {
    path: '/brands',
    name: 'brand-mall',
    component: BrandMallPage,
    meta: { title: '브랜드 몰' }
  },
  {
    path: '/brands/:slug',
    name: 'brand-detail',
    component: BrandDetailPage,
    meta: { title: '브랜드 상세' }
  },
  {
    path: '/brand-story',
    name: 'brand-story',
    component: BrandStoryPage,
    meta: { title: '브랜드 스토리' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, _from, savedPosition) {
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
router.beforeEach(async (to, _from, next) => {
  const authStore = useAuthStore()

  // 토큰은 있으나 user가 없는 경우 복구 시도
  if (!authStore.user && localStorage.getItem('access_token')) {
    await authStore.loadUser()
  }

  // 페이지 타이틀
  document.title = to.meta.title ? `${to.meta.title} | 신선한 생활을 위한 커머스` : '신선한 생활을 위한 커머스'

  // 인증이 필요한 페이지
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    window.dispatchEvent(new CustomEvent('auth:required', { detail: { to: to.fullPath } }))
    return next({ name: 'home', query: { redirect: to.fullPath } })
  }

  // 관리자 제한
  if (to.meta.requiresAdmin && !authStore.isAdmin) {
    return next({ name: 'home', query: { redirect: '/' } })
  }

  // 판매자 제한
  if (to.meta.requiresSeller && !authStore.isSeller) {
    if (to.path !== '/seller/register') {
      return next('/seller/register')
    }
  }

  next()
})

export default router
