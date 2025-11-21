<template>
  <footer class="bg-gray-50 border-t border-gray-200 pt-16 pb-12">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="flex flex-col md:flex-row justify-between gap-12 mb-16">
        <div class="max-w-xs">
          <div class="font-display font-bold text-2xl text-gray-900 mb-6">FreshPick</div>
          <p class="text-sm text-gray-500 leading-relaxed mb-6">
            자연의 시간을 존중하며, <br>
            가장 정직한 먹거리를 전합니다.
          </p>
          <div class="flex gap-4">
            <a href="#" class="text-gray-400 hover:text-gray-900">
              <Instagram :size="20" />
            </a>
            <a href="#" class="text-gray-400 hover:text-gray-900">
              <Facebook :size="20" />
            </a>
            <a href="#" class="text-gray-400 hover:text-gray-900">
              <Youtube :size="20" />
            </a>
          </div>
        </div>
        <div class="grid grid-cols-2 sm:grid-cols-3 gap-12 text-sm">
          <div>
            <h4 class="font-bold text-gray-900 mb-4">Customer</h4>
            <ul class="space-y-3 text-gray-500">
              <li><a href="#" class="hover:text-brand-600">고객센터</a></li>
              <li><a href="#" class="hover:text-brand-600">자주 묻는 질문</a></li>
              <li><a href="#" class="hover:text-brand-600">1:1 문의</a></li>
            </ul>
          </div>
          <div>
            <h4 class="font-bold text-gray-900 mb-4">Company</h4>
            <ul class="space-y-3 text-gray-500">
              <li><a href="#" class="hover:text-brand-600">회사소개</a></li>
              <li><a href="#" class="hover:text-brand-600">인재채용</a></li>
              <li><a href="#" class="hover:text-brand-600">이용약관</a></li>
            </ul>
          </div>
        </div>
      </div>
      <div class="border-t border-gray-200 pt-8 flex flex-col md:flex-row justify-between items-center gap-4 text-xs text-gray-400">
        <p>&copy; 2024 FreshPick Corp. All rights reserved.</p>
        <div class="flex gap-6">
          <span>개인정보처리방침</span>
          <span>이용약관</span>
        </div>
      </div>
    </div>
  </footer>
</template>

<script setup lang="ts">
import { Instagram, Facebook, Youtube } from 'lucide-vue-next'
</script>

