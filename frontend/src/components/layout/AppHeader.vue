<template>
  <header 
    :class="[
      'fixed w-full z-50 top-0 left-0 header-transition px-4 lg:px-12 flex items-center justify-between',
      uiStore.isScrolled ? 'h-16 bg-white/95 backdrop-blur-md shadow-sm text-gray-900' : 'h-24 bg-transparent text-white'
    ]"
  >
    <!-- Left: Logo -->
    <div class="flex items-center gap-4 lg:gap-12 shrink-0">
      <a href="#" class="flex items-center gap-2 group" @click.prevent="scrollToTop">
        <span :class="['font-display font-bold text-2xl tracking-tighter transition-colors', uiStore.isScrolled ? 'text-brand-500' : 'text-white']">
          FreshPick
        </span>
      </a>
      
      <!-- Desktop Nav (Minimal) -->
      <nav class="hidden xl:flex gap-8 text-[15px] font-medium tracking-tight" :class="uiStore.isScrolled ? 'text-gray-600' : 'text-white/90'">
        <a href="#" class="hover:opacity-70 transition-opacity">브랜드 스토리</a>
        <a href="#" class="hover:opacity-70 transition-opacity">베스트</a>
        <a href="#" class="hover:opacity-70 transition-opacity">신상품</a>
        <a href="#" class="hover:opacity-70 transition-opacity">이벤트</a>
      </nav>
    </div>

    <!-- Center: Search Bar (Persistent) -->
    <div class="flex-1 max-w-xl mx-4 lg:mx-8 transition-all duration-300">
      <div class="relative group">
        <input 
          type="text" 
          placeholder="검색어를 입력해주세요" 
          :class="[
            'w-full py-2.5 pl-4 pr-10 rounded-full text-sm transition-all focus:outline-none focus:ring-2 focus:ring-brand-500/50',
            uiStore.isScrolled 
              ? 'bg-gray-100 text-gray-900 placeholder-gray-400' 
              : 'bg-white/20 text-white placeholder-white/70 backdrop-blur-sm border border-white/30 focus:bg-white/30'
          ]"
        >
        <button :class="['absolute right-3 top-2.5 transition-colors', uiStore.isScrolled ? 'text-gray-500' : 'text-white']">
          <Search :size="20" />
        </button>
      </div>
    </div>

    <!-- Right: Actions -->
    <div class="flex items-center gap-3 shrink-0">
      <!-- Login Button -->
      <button @click="uiStore.openLogin" class="hidden md:block text-sm font-medium hover:opacity-70 transition-opacity mr-2" :class="uiStore.isScrolled ? 'text-gray-600' : 'text-white'">
        로그인
      </button>
      <button class="md:hidden p-2" :class="uiStore.isScrolled ? 'text-gray-600' : 'text-white'" @click="uiStore.openLogin">
        <User :size="24" />
      </button>
      
      <button @click="uiStore.openCart" :class="['relative p-2 rounded-full transition-colors', uiStore.isScrolled ? 'text-gray-900 hover:bg-gray-100' : 'text-white hover:bg-white/10']">
        <ShoppingCart :size="24" />
        <span v-if="cartStore.count > 0" class="absolute top-0 right-0 w-4 h-4 bg-brand-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center ring-2 ring-white">
          {{ cartStore.count }}
        </span>
      </button>
    </div>
  </header>
</template>

<script setup lang="ts">
import { Search, User, ShoppingCart } from 'lucide-vue-next'
import { useUIStore } from '@/stores/ui'
import { useCartStore } from '@/stores/cart'
import { useScroll } from '@/composables/useScroll'

const uiStore = useUIStore()
const cartStore = useCartStore()
const { scrollToTop } = useScroll()
</script>

