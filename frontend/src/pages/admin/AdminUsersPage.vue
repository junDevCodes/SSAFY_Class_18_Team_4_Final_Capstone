<template>
  <div class="admin-page">
    <header class="page-header">
      <div>
        <p class="eyebrow">전체 관리자 · User Management</p>
        <h1>유저 관리</h1>
        <p class="sub">역할, 상태, 가입일 기준으로 유저를 검색하고 관리하는 화면입니다.</p>
      </div>
    </header>

    <section class="filters">
      <div class="filter">
        <span class="label">검색</span>
        <input v-model="search" type="text" placeholder="이메일 / 이름 / 전화번호" />
      </div>
      <div class="filter">
        <span class="label">역할</span>
        <select v-model="role">
          <option value="all">전체</option>
          <option value="consumer">일반회원</option>
          <option value="seller">판매자</option>
          <option value="admin">관리자</option>
        </select>
      </div>
      <div class="filter">
        <span class="label">상태</span>
        <select v-model="status">
          <option value="all">전체</option>
          <option value="active">활성</option>
          <option value="inactive">비활성</option>
        </select>
      </div>
    </section>

    <section class="placeholder">
      <p class="title">유저 관리 프로토타입</p>
      <p class="desc">
        이 페이지에서는 유저 목록/상세/상태 변경을 제공할 예정입니다.
        현재는 Admin API 스펙을 정의한 뒤, 목록/상세용 컴포넌트를 점진적으로 연결할 계획입니다.
      </p>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const search = ref('')
const role = ref('all')
const status = ref('all')
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

.filters {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
  align-items: end;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 16px;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.05);
  margin-bottom: 16px;
}

.filter {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.label {
  font-size: 12px;
  color: #64748b;
  font-weight: 700;
}

input,
select {
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 9px 11px;
  background: #fff;
  font-size: 14px;
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


