<template>
  <div class="admin-page">
    <header class="page-header">
      <div>
        <p class="eyebrow">전체 관리자 · User Behavior</p>
        <h1>유저 행동 지표</h1>
        <p class="sub">DAU/MAU, 퍼널, 이탈 구간을 집중적으로 모니터링하는 화면입니다.</p>
      </div>
    </header>

    <section class="placeholder">
      <p class="title">행동 지표 대시보드 프로토타입</p>
      <p class="desc">
        이 페이지에서는 DAU/MAU, DAU/MAU 비율, 장바구니/결제 퍼널, 이탈 구간 등을
        Top Line 집계와 사용자 이벤트 데이터를 조합해 시각화할 예정입니다.
      </p>
      <p class="desc">
        우선 Top Line 데이터 연동을 마친 후, 세션/이벤트 로그 설계가 완료되면 이 화면을 확장하겠습니다.
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


