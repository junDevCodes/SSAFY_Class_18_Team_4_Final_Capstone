<template>
  <header
    class="sticky top-0 z-40 bg-white/80 backdrop-blur border-b border-gray-100"
    style="height: var(--app-header-height)"
  >
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-full flex items-center justify-between gap-6">
      <router-link
        to="/"
        class="flex items-center gap-2 font-display text-2xl font-semibold text-gray-900"
        aria-label="SelF 홈으로 이동"
      >
        <span>Sel</span>
        <span class="italic text-brand-500">F</span>
      </router-link>

      <nav class="hidden md:flex items-center gap-6 text-sm text-gray-600">
        <router-link class="hover:text-brand-600 transition-colors" to="/products">
          상품
        </router-link>
        <router-link class="hover:text-brand-600 transition-colors" to="/recommend">
          추천
        </router-link>
        <router-link class="hover:text-brand-600 transition-colors" to="/about">
          소개
        </router-link>
      </nav>

      <div class="flex items-center gap-3 text-sm font-medium">
        <router-link
          to="/login"
          class="px-3 py-2 rounded-lg text-gray-700 hover:text-brand-600 transition-colors"
        >
          로그인
        </router-link>
        <router-link
          to="/cart"
          class="px-4 py-2 rounded-lg bg-brand-600 text-white hover:bg-brand-700 shadow-sm transition-colors"
        >
          장바구니
        </router-link>
      </div>
    </div>
  </header>
</template>
