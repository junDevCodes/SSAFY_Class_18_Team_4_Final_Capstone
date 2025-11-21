<template>
  <section class="py-16 bg-gray-50">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
        <div class="bg-white p-8 rounded-2xl shadow-sm flex flex-col items-center text-center hover:shadow-md transition-shadow">
          <div class="w-12 h-12 bg-brand-50 rounded-full flex items-center justify-center text-brand-600 mb-4">
            <Leaf :size="24" />
          </div>
          <h3 class="font-bold text-lg mb-2">산지 직송의 원칙</h3>
          <p class="text-sm text-gray-500 leading-relaxed">중간 유통 과정 없이<br>농부의 땀을 식탁까지 전달합니다.</p>
        </div>
        <div class="bg-white p-8 rounded-2xl shadow-sm flex flex-col items-center text-center hover:shadow-md transition-shadow">
          <div class="w-12 h-12 bg-brand-50 rounded-full flex items-center justify-center text-brand-600 mb-4">
            <Truck :size="24" />
          </div>
          <h3 class="font-bold text-lg mb-2">풀 콜드체인 배송</h3>
          <p class="text-sm text-gray-500 leading-relaxed">포장부터 배송까지 적정 온도를<br>100% 유지하여 신선함을 지킵니다.</p>
        </div>
        <div class="bg-white p-8 rounded-2xl shadow-sm flex flex-col items-center text-center hover:shadow-md transition-shadow">
          <div class="w-12 h-12 bg-brand-50 rounded-full flex items-center justify-center text-brand-600 mb-4">
            <ShieldCheck :size="24" />
          </div>
          <h3 class="font-bold text-lg mb-2">100% 환불 보장</h3>
          <p class="text-sm text-gray-500 leading-relaxed">상품의 품질이 만족스럽지 않다면<br>조건 없이 교환/환불해 드립니다.</p>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { Leaf, Truck, ShieldCheck } from 'lucide-vue-next'
</script>

