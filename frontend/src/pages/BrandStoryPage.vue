<template>
  <div class="bg-gray-50 text-gray-900">
    <section class="relative overflow-hidden bg-gradient-to-r from-brand-50 via-white to-white">
      <div class="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-16 md:py-24 grid md:grid-cols-2 gap-12 items-center">
        <div class="space-y-6 md:space-y-8">
          <p class="text-sm font-semibold text-emerald-700 uppercase tracking-[0.18em]">
            Our Philosophy
          </p>
          <h1 class="text-4xl md:text-5xl font-bold leading-tight">
            고민은 줄이고,<br />
            <span class="text-emerald-700 italic font-display">신선함</span>은 채우세요.
          </h1>
          <div class="space-y-4 text-lg text-gray-700 leading-relaxed">
            <p>
              "오늘 저녁 파스타를 하려는데, 바질을 샀나?"<br />
              "삼겹살을 담았는데, 곁들일 채소가 뭐였지?"
            </p>
            <p>
              누구나 겪는 장보기의 고민. <strong class="text-brand-600">SelFresh</strong>는 이 질문에 대한 답을 미리 준비합니다.
              AI 큐레이션이 당신의 파스타 면을 담는 순간, 가장 잘 어울리는 올리브 오일과 허브를 먼저 제안해요. 신선도, 조합,
              동선까지 한 번에.
            </p>
            <p class="font-semibold text-gray-900">
              우리는 식재료를 파는 곳이 아닌, 당신의 요리 과정을 완성하는 동료입니다.
            </p>
          </div>
          <div class="flex flex-wrap items-center gap-4">
            <button
              class="inline-flex items-center gap-2 px-6 py-3 rounded-full text-sm font-semibold text-white bg-brand-600 hover:bg-brand-500 transition-colors shadow-lg shadow-brand-500/25"
            >
              브랜드 스토리 더보기
              <span aria-hidden="true">→</span>
            </button>
            <div class="flex items-center gap-3 text-sm text-gray-600">
              <div class="w-10 h-10 rounded-full overflow-hidden shadow ring-1 ring-black/5 bg-white">
                <img
                  :src="accentImage"
                  alt="SelFresh curated basket"
                  class="w-full h-full object-cover"
                  @error="handleAccentError"
                />
              </div>
              <span class="text-emerald-700 font-medium">오늘의 신선한 영감</span>
            </div>
          </div>
        </div>

        <div class="relative">
          <div class="aspect-[4/3] rounded-3xl overflow-hidden shadow-2xl ring-1 ring-black/5 bg-gray-100">
            <img
              :src="heroImage"
              alt="신선한 재료가 담긴 장바구니"
              class="w-full h-full object-cover transition-transform duration-700 hover:scale-105"
              @error="handleHeroError"
            />
          </div>
          <div
            class="absolute -bottom-8 left-6 md:left-auto md:right-6 bg-brand-600 text-white px-5 py-4 rounded-xl shadow-xl shadow-brand-600/30 flex items-center gap-4 w-[calc(100%-3rem)] md:w-auto"
          >
            <div class="w-16 h-16 rounded-lg overflow-hidden ring-2 ring-white/30 bg-white/10 flex-shrink-0">
              <img
                :src="badgeImage"
                alt="신선 식재료 큐레이션"
                class="w-full h-full object-cover"
                @error="handleBadgeError"
              />
            </div>
            <div class="space-y-1">
              <p class="text-lg font-display italic leading-tight">"Think Fresh"</p>
              <p class="text-xs text-brand-50 leading-snug">단순한 구매가 아닌, 영감의 발견.</p>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section class="py-16 md:py-20 bg-white">
      <div class="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="grid md:grid-cols-3 gap-6 md:gap-8">
          <article class="p-6 rounded-2xl border border-gray-100 shadow-sm bg-white">
            <h3 class="text-lg font-semibold text-gray-900 mb-3">신선도 퍼스트</h3>
            <p class="text-sm text-gray-600 leading-relaxed">
              냉장/실온 조건을 고려해 가장 빠른 동선으로 담아 추천합니다. 실패 없는 신선배송을 위해 유통기한, 입고일을 우선
              순위로 삼아요.
            </p>
          </article>
          <article class="p-6 rounded-2xl border border-gray-100 shadow-sm bg-white">
            <h3 class="text-lg font-semibold text-gray-900 mb-3">맞춤 큐레이션</h3>
            <p class="text-sm text-gray-600 leading-relaxed">
              당신의 장보기 패턴을 학습해 레시피, 페어링 오일, 소스까지 한 번에 제안합니다. 알러지/식단 옵션을 선택하면 바로
              반영돼요.
            </p>
          </article>
          <article class="p-6 rounded-2xl border border-gray-100 shadow-sm bg-white">
            <h3 class="text-lg font-semibold text-gray-900 mb-3">스토리가 있는 재료</h3>
            <p class="text-sm text-gray-600 leading-relaxed">
              산지와 생산자를 투명하게 안내합니다. QR로 생산 이력과 보관 팁까지 확인하고, 셰프 팁을 담은 미니 카드도 함께
              전달해요.
            </p>
          </article>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

// 드라이브 썸네일/뷰 URL 생성기 (썸네일을 기본으로 사용)
const toDriveThumb = (id: string, size = 'w1600') => `https://drive.google.com/thumbnail?id=${id}&sz=${size}`
const toDriveView = (id: string) => `https://drive.google.com/uc?export=view&id=${id}`

const HERO_ID = '1NXAMvfKokU9wq0eVYdSgQMTDJDwKpBiP'
const SECONDARY_ID = '15TPC-Z3zUrZtFyOvXHqfouGsM0xYmFpE'

// 우선 썸네일 URL을 사용하고, 오류 시 뷰 URL로 재시도
const heroImage = ref(toDriveThumb(HERO_ID))
const badgeImage = ref(toDriveThumb(SECONDARY_ID))
const accentImage = ref(toDriveThumb(SECONDARY_ID))

const handleHeroError = (event: Event) => {
  const target = event.target as HTMLImageElement
  if (target.dataset.fallback === 'view') return
  target.dataset.fallback = 'view'
  target.src = toDriveView(HERO_ID)
}

const handleBadgeError = (event: Event) => {
  const target = event.target as HTMLImageElement
  if (target.dataset.fallback === 'view') return
  target.dataset.fallback = 'view'
  target.src = toDriveView(SECONDARY_ID)
}

const handleAccentError = (event: Event) => {
  const target = event.target as HTMLImageElement
  if (target.dataset.fallback === 'view') return
  target.dataset.fallback = 'view'
  target.src = toDriveView(SECONDARY_ID)
}
</script>
