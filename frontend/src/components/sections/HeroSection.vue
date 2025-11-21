<template>
  <section class="relative w-full h-[85vh] overflow-hidden bg-gray-900">
    <div class="absolute inset-0 transition-transform duration-700 ease-out scale-105">
      <img :src="heroSlide.image" class="w-full h-full object-cover opacity-90" alt="Hero Image">
      <div class="absolute inset-0 bg-gradient-to-b from-black/40 via-transparent to-black/60"></div>
    </div>

    <div class="absolute inset-0 flex flex-col justify-center items-center text-center text-white px-4 z-10 mt-10">
      <span class="inline-block py-1 px-3 border border-white/30 rounded-full text-xs font-medium tracking-widest uppercase mb-6 backdrop-blur-sm animate-fade-in-up">
        Premium Fresh Market
      </span>
      <h1 class="font-display text-5xl md:text-7xl lg:text-8xl font-bold leading-none mb-8 tracking-tight drop-shadow-lg animate-fade-in-up" style="animation-delay: 0.2s;">
        {{ heroSlide.title }}
      </h1>
      <p class="text-lg md:text-xl font-light text-white/90 max-w-xl leading-relaxed mb-10 animate-fade-in-up" style="animation-delay: 0.4s;">
        {{ heroSlide.desc }}
      </p>
      <button class="group relative px-8 py-4 bg-white text-gray-900 rounded-full font-bold text-sm tracking-wide overflow-hidden transition-all hover:scale-105 animate-fade-in-up shadow-[0_0_20px_rgba(255,255,255,0.3)]" style="animation-delay: 0.6s;">
        <span class="relative z-10 flex items-center gap-2">
          컬렉션 보러가기 <ArrowRight :size="16" class="transition-transform group-hover:translate-x-1" />
        </span>
      </button>
    </div>

    <div class="absolute bottom-10 left-1/2 transform -translate-x-1/2 text-white/50 flex flex-col items-center gap-2 animate-float cursor-pointer" @click="scrollToContent">
      <span class="text-[10px] tracking-widest uppercase">Scroll</span>
      <ChevronDown :size="20" />
    </div>
  </section>
</template>

<script setup lang="ts">
import { reactive } from 'vue'
import { ArrowRight, ChevronDown } from 'lucide-vue-next'
import { useScroll } from '@/composables/useScroll'

const { scrollToContent } = useScroll()

const heroSlide = reactive({
  title: "Season of Freshness",
  desc: "가장 신선한 제철 식재료로 당신의 식탁을 채워보세요. 산지의 생생함을 그대로 전해드립니다.",
  image: "https://images.unsplash.com/photo-1542838132-92c53300491e?q=80&w=2574&auto=format&fit=crop"
})
</script>

