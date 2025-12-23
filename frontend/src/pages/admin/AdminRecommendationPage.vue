<template>
  <div class="admin-page">
    <header class="page-header">
      <div>
        <p class="eyebrow">전체 관리자 · Recommendation</p>
        <h1>추천 알고리즘 성과 지표</h1>
        <p class="sub">추천 CTR, 구매 전환율, 기여 GMV를 한 곳에서 점검합니다.</p>
      </div>
    </header>

    <section class="placeholder">
      <p class="title">추천 지표 확장 준비 중</p>
      <p class="desc">
        이 페이지에서는 홈/상세/장바구니 등 추천 위치별 CTR, 추천 구매 전환율, 추천 기여 GMV 비율을
        시계열과 Top N 분해 그래프로 제공할 예정입니다.
      </p>
      <p class="desc">
        백엔드 이벤트 스키마 및 집계가 준비되는 대로 이 화면에 연결하겠습니다.
      </p>
    </section>
  </div>
</template>

<script setup lang="ts">
</script>

<style scoped>
.admin-page {
  padding: 28px;
}

.page-header {
  margin-bottom: 18px;
}

.page-header h1 {
  font-size: 24px;
  font-weight: 800;
  margin: 6px 0;
}

.sub {
  color: #475569;
}

.eyebrow {
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #22b8cf;
  font-weight: 700;
}

.placeholder {
  margin-top: 12px;
  padding: 18px 16px;
  border-radius: 12px;
  border: 1px dashed #cbd5e1;
  background: #f8fafc;
}

.title {
  font-weight: 700;
  margin: 0 0 8px 0;
  color: #0f172a;
}

.desc {
  margin: 4px 0 0 0;
  color: #64748b;
  font-size: 14px;
}
</style>


