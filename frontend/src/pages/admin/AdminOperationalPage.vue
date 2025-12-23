<template>
  <div class="admin-page">
    <header class="page-header">
      <div>
        <p class="eyebrow">전체 관리자 · Operational</p>
        <h1>운영 건강도 지표</h1>
        <p class="sub">크롤링 성공률, 서버 응답 시간, 에러율 등 운영 상태를 한눈에 확인합니다.</p>
      </div>
    </header>

    <section class="placeholder">
      <p class="title">운영 지표 대시보드 프로토타입</p>
      <p class="desc">
        이 페이지에서는 크롤링 성공률, API 응답 P95, 5xx 에러율, 가격 예측 MAPE, 서비스 가용성 등
        운영 관련 지표를 시계열과 알림 카드 형태로 제공할 예정입니다.
      </p>
      <p class="desc">
        이후 Sentry/APM/크롤러 로그와 연동하여 실시간에 가까운 모니터링 화면으로 확장할 수 있습니다.
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


