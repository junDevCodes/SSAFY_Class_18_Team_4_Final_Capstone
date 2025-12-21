<template>
  <section class="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-gray-100">
    <div class="flex items-start justify-between gap-3">
      <div class="space-y-1">
        <p class="text-sm font-semibold text-gray-900">내 식재료 취향 다시 설정하기</p>
        <p class="text-sm text-gray-600">
          취향이 바뀌었나요? 다시 선택하면 추천이 더 정확해져요.
        </p>
      </div>
      <button
        type="button"
        class="rounded-full bg-brand-600 px-4 py-2 text-xs font-semibold text-white shadow-sm transition hover:bg-brand-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-300"
        @click="$emit('reset-tutorial')"
      >
        다시 선택하기
      </button>
    </div>
  </section>
</template>

<script setup lang="ts">
defineEmits<{
  (e: 'reset-tutorial'): void
}>()
</script>
