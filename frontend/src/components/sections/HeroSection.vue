<template>
  <section class="relative w-full h-[85vh] overflow-hidden bg-gray-900">
    <div class="absolute inset-0 transition-transform duration-700 ease-out scale-105">
      <img :src="heroSlide.image" class="w-full h-full object-cover opacity-90" alt="Hero Image">
      <div class="absolute inset-0 bg-gradient-to-b from-black/40 via-transparent to-black/60"></div>
    </div>

    <div class="absolute inset-0 flex flex-col justify-center items-center text-center text-white px-4 z-10 mt-10">
      <span class="inline-block py-1 px-3 border border-white/30 rounded-full text-xs font-medium tracking-widest uppercase mb-6 backdrop-blur-sm animate-fade-in-up">
        Premium Curation Service
      </span>

      <h1 class="font-display font-bold leading-none mb-8 tracking-tight drop-shadow-lg animate-fade-in-up" style="animation-delay: 0.2s;">
        <span class="block md:hidden text-5xl leading-tight">
          Special<br>Selection<br>All<br>For<br>You
        </span>
        <span class="hidden md:block lg:hidden text-7xl leading-tight">
          Special Selection<br>All<br>For You
        </span>
        <span class="hidden lg:block text-6xl xl:text-7xl 2xl:text-8xl whitespace-nowrap">
          Special Selection All For You
        </span>
      </h1>

      <p class="text-lg md:text-xl font-medium text-white drop-shadow-[0_2px_6px_rgba(0,0,0,0.6)] max-w-xl leading-relaxed mb-10 animate-fade-in-up" style="animation-delay: 0.4s;">
        {{ heroSlide.desc }}
      </p>
      <button class="group relative px-8 py-4 bg-white text-gray-900 rounded-full font-bold text-sm tracking-wide overflow-hidden transition-all hover:scale-105 animate-fade-in-up shadow-[0_0_20px_rgba(255,255,255,0.3)]" style="animation-delay: 0.6s;" @click="goToAllProducts">
        <span class="relative z-10 flex items-center gap-2">
          상품 더보기<ArrowRight :size="16" class="transition-transform group-hover:translate-x-1" />
        </span>
      </button>
    </div>

    <div class="absolute bottom-10 left-[48.8%] transform -translate-x-1/2 text-white/50 flex flex-col items-center gap-2 animate-float cursor-pointer" @click="scrollToContent">
      <span class="text-[10px] tracking-widest uppercase">Scroll</span>
      <ChevronDown :size="20" />
    </div>
  </section>
</template>

<script setup lang="ts">
import { reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowRight, ChevronDown } from 'lucide-vue-next'
import { useScroll } from '@/composables/useScroll'

const { scrollToContent } = useScroll()
const router = useRouter()

const goToAllProducts = () => {
  router.push({ name: 'search' })
}

const heroSlide = reactive({
  title: 'Special Selection All For You',
  desc: '더 이상 선택을 위해 소중한 시간을 낭비하지 마세요.',
  image: 'https://images.unsplash.com/photo-1542838132-92c53300491e?q=80&w=2574&auto=format&fit=crop'
})
</script>
