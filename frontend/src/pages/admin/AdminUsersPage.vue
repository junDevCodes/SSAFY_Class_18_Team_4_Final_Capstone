<template>
  <div class="admin-page">
    <header class="page-header">
      <div>
        <p class="eyebrow">전체 관리자 · User Management</p>
        <h1>유저 관리</h1>
        <p class="sub">역할, 상태, 가입일 기준으로 유저를 검색하고 관리하는 화면입니다.</p>
      </div>
      <p v-if="lastUpdated" class="updated">최근 동기화: {{ lastUpdated }}</p>
    </header>

    <section class="filters">
      <div class="filter">
        <span class="label">검색</span>
        <input v-model="search" type="text" placeholder="이메일 / 닉네임 검색" />
      </div>
      <div class="filter">
        <span class="label">역할</span>
        <select v-model="role">
          <option value="all">전체</option>
          <option value="user">일반회원</option>
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
      <div class="actions">
        <button type="button" class="btn primary" @click="loadUsers" :disabled="loading">
          {{ loading ? '조회 중...' : '조회' }}
        </button>
        <button type="button" class="btn ghost" @click="resetFilters" :disabled="loading">
          초기화
        </button>
      </div>
    </section>

    <section class="user-list">
      <header class="user-list-head">
        <div>
          <h2>유저 목록</h2>
          <p class="meta">
            총 <strong>{{ users.length }}</strong>명
            <span v-if="appliedSummary"> · {{ appliedSummary }}</span>
          </p>
        </div>
      </header>

      <p v-if="errorMessage" class="error">{{ errorMessage }}</p>
      <p v-else-if="loading" class="loading">유저 목록을 불러오는 중입니다...</p>

      <div v-else class="table-wrapper">
        <table class="user-table" v-if="users.length">
          <thead>
            <tr>
              <th>이메일</th>
              <th>닉네임</th>
              <th>역할</th>
              <th>상태</th>
              <th>가입일</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="user in users" :key="user.id">
              <td>{{ user.email }}</td>
              <td>{{ user.username }}</td>
              <td>{{ roleLabel(user.role) }}</td>
              <td>
                <span :class="['status-chip', user.is_active ? 'active' : 'inactive']">
                  {{ user.is_active ? '활성' : '비활성' }}
                </span>
              </td>
              <td>{{ formatDate(user.date_joined) }}</td>
            </tr>
          </tbody>
        </table>
        <p v-else class="empty">조건에 해당하는 유저가 없습니다.</p>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { adminUserAPI } from '@/services/api/admin'
import type { AdminUser } from '@/types/admin'

const search = ref('')
const role = ref<'all' | 'user' | 'seller' | 'admin'>('all')
const status = ref<'all' | 'active' | 'inactive'>('all')

const users = ref<AdminUser[]>([])
const loading = ref(false)
const errorMessage = ref<string | null>(null)
const lastUpdated = ref<string | null>(null)

const appliedSummary = computed(() => {
  const parts: string[] = []
  if (search.value.trim()) {
    parts.push(`검색: "${search.value.trim()}"`)
  }
  if (role.value !== 'all') {
    parts.push(`역할: ${roleLabel(role.value)}`)
  }
  if (status.value === 'active') {
    parts.push('상태: 활성')
  } else if (status.value === 'inactive') {
    parts.push('상태: 비활성')
  }
  return parts.join(' · ')
})

const roleLabel = (value: AdminUser['role'] | 'all'): string => {
  if (value === 'admin') return '관리자'
  if (value === 'seller') return '판매자'
  if (value === 'user') return '일반회원'
  if (value === 'guest') return '비회원'
  return '전체'
}

const formatDate = (value: string): string => {
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return value
  return d.toLocaleString('ko-KR')
}

const loadUsers = async () => {
  if (loading.value) return
  loading.value = true
  errorMessage.value = null

  try {
    const params: { q?: string; role?: string; is_active?: string } = {}
    if (search.value.trim()) {
      params.q = search.value.trim()
    }
    if (role.value !== 'all') {
      params.role = role.value
    }
    if (status.value === 'active') {
      params.is_active = 'true'
    } else if (status.value === 'inactive') {
      params.is_active = 'false'
    }

    users.value = await adminUserAPI.list(params)
    lastUpdated.value = new Date().toLocaleString()
  } catch (err: any) {
    console.error('관리자 유저 목록 조회 실패', err)
    errorMessage.value = err?.response?.data?.detail || '유저 목록을 불러오지 못했습니다.'
  } finally {
    loading.value = false
  }
}

const resetFilters = () => {
  search.value = ''
  role.value = 'all'
  status.value = 'all'
  loadUsers()
}

onMounted(() => {
  loadUsers()
})
</script>

<style scoped>
.admin-page {
  padding: 28px;
}

.page-header {
  margin-bottom: 18px;
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
}

.page-header h1 {
  font-size: 24px;
  font-weight: 800;
  margin: 6px 0;
}

.updated {
  font-size: 12px;
  color: #64748b;
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

.actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

.btn {
  border-radius: 999px;
  padding: 8px 14px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid transparent;
}

.btn.primary {
  background: #2563eb;
  color: #f9fafb;
}

.btn.ghost {
  background: #fff;
  color: #1e293b;
  border-color: #e2e8f0;
}

.btn:disabled {
  opacity: 0.6;
  cursor: default;
}

.user-list {
  margin-top: 12px;
  background: #fff;
  border-radius: 16px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.05);
  padding: 16px 16px 18px;
}

.user-list-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 10px;
}

.user-list-head h2 {
  margin: 0;
  font-size: 18px;
}

.meta {
  margin: 4px 0 0 0;
  font-size: 13px;
  color: #64748b;
}

.table-wrapper {
  width: 100%;
  overflow-x: auto;
}

.user-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.user-table th,
.user-table td {
  padding: 8px 10px;
  border-bottom: 1px solid #e2e8f0;
  text-align: left;
  white-space: nowrap;
}

.user-table thead th {
  background: #f8fafc;
  font-weight: 700;
  color: #475569;
}

.status-chip {
  display: inline-flex;
  align-items: center;
  padding: 3px 8px;
  border-radius: 999px;
  font-size: 12px;
}

.status-chip.active {
  background: #dcfce7;
  color: #166534;
}

.status-chip.inactive {
  background: #fee2e2;
  color: #b91c1c;
}

.error {
  margin-top: 4px;
  font-size: 13px;
  color: #b91c1c;
}

.loading {
  margin-top: 4px;
  font-size: 13px;
  color: #475569;
}

.empty {
  margin-top: 8px;
  font-size: 13px;
  color: #64748b;
}
</style>


