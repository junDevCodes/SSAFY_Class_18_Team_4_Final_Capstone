<template>
  <div class="admin-page">
    <header class="page-header">
      <div>
        <p class="eyebrow">전체 관리자 · User Management</p>
        <h1>유저 관리</h1>
        <p class="sub">역할, 상태, 가입일 기준으로 유저를 검색하고 관리하는 화면입니다.</p>
      </div>
      <div class="sync">
        <span class="dot" :class="loading ? 'syncing' : 'ok'"></span>
        <span v-if="lastUpdated">동기화: {{ lastUpdated }}</span>
        <label class="data-mode-toggle">
          <input type="checkbox" disabled />
          <span>테스트 데이터 없음</span>
        </label>
      </div>
    </header>

    <section class="summary" v-if="summary">
      <div class="kpi-grid">
        <article class="kpi-card">
          <p class="label">전체 유저</p>
          <p class="value">{{ summary.total_users.toLocaleString('ko-KR') }}</p>
          <p class="hint">guest 포함 전체 가입 수</p>
        </article>
        <article class="kpi-card">
          <p class="label">활성 / 비활성</p>
          <p class="value">
            {{ summary.active_users.toLocaleString('ko-KR') }}
            <span class="value-sub"> / {{ summary.inactive_users.toLocaleString('ko-KR') }}</span>
          </p>
          <p class="hint">현재 로그인 가능 / 정지 계정</p>
        </article>
        <article class="kpi-card">
          <p class="label">판매자 / 관리자</p>
          <p class="value">
            {{ summary.seller_count.toLocaleString('ko-KR') }}
            <span class="value-sub"> / {{ summary.admin_count.toLocaleString('ko-KR') }}</span>
          </p>
          <p class="hint">판매자 / 운영 관리자 수</p>
        </article>
        <article class="kpi-card">
          <p class="label">최근 7일 신규 가입</p>
          <p class="value">{{ summary.new_users_last_7d.toLocaleString('ko-KR') }}</p>
          <p class="hint">지난 7일 기준 가입자 수</p>
        </article>
      </div>
    </section>

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
              <td>
                <div class="username-cell">
                  <template v-if="editingUserId === user.id">
                    <input
                      v-model="editUsername"
                      type="text"
                      class="username-input"
                      :disabled="saving"
                    />
                    <button type="button" class="link" :disabled="saving" @click="saveUsername(user)">저장</button>
                    <button type="button" class="link ghost" :disabled="saving" @click="cancelEdit">취소</button>
                  </template>
                  <template v-else>
                    <span>{{ user.username }}</span>
                    <button type="button" class="link" @click="startEdit(user)">편집</button>
                  </template>
                </div>
              </td>
              <td>
                <select
                  v-model="user.role"
                  class="inline-select"
                  :disabled="saving"
                  @change="onRoleChange(user)"
                >
                  <option value="user">일반회원</option>
                  <option value="seller">판매자</option>
                  <option value="admin">관리자</option>
                  <option value="guest">비회원</option>
                </select>
              </td>
              <td>
                <button
                  type="button"
                  class="status-toggle"
                  :class="user.is_active ? 'on' : 'off'"
                  :disabled="saving"
                  @click="toggleActive(user)"
                >
                  {{ user.is_active ? '활성' : '정지' }}
                </button>
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
import type { AdminUser, AdminUserSummary } from '@/types/admin'

const search = ref('')
const role = ref<'all' | 'user' | 'seller' | 'admin'>('all')
const status = ref<'all' | 'active' | 'inactive'>('all')

const users = ref<AdminUser[]>([])
const summary = ref<AdminUserSummary | null>(null)
const loading = ref(false)
const saving = ref(false)
const errorMessage = ref<string | null>(null)
const lastUpdated = ref<string | null>(null)

const editingUserId = ref<number | null>(null)
const editUsername = ref('')

// 저장 확인 모달 및 변경 사항 추적
const showConfirmModal = ref(false)

type UserChange = {
  userId: number
  field: 'username' | 'role' | 'is_active'
  value: string | boolean
}

const pendingChanges = ref<UserChange[]>([])

const hasChanges = computed(() => pendingChanges.value.length > 0)

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

    const [userList, summaryData] = await Promise.all([
      adminUserAPI.list(params),
      adminUserAPI.summary(),
    ])
    users.value = userList
    summary.value = summaryData
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

const startEdit = (user: AdminUser) => {
  editingUserId.value = user.id
  editUsername.value = user.username
}

const cancelEdit = () => {
  editingUserId.value = null
  editUsername.value = ''
}

const saveUsername = async (user: AdminUser) => {
  if (!editUsername.value.trim() || saving.value) return

  // 기존 변경사항 제거 후 새로 추가
  pendingChanges.value = pendingChanges.value.filter(
    (c) => !(c.userId === user.id && c.field === 'username')
  )

  pendingChanges.value.push({
    userId: user.id,
    field: 'username',
    value: editUsername.value.trim(),
  })

  // 로컬에서 미리 보여주기
  const idx = users.value.findIndex((u) => u.id === user.id)
  if (idx !== -1) {
    users.value[idx].username = editUsername.value.trim()
  }

  cancelEdit()
}

const onRoleChange = async (user: AdminUser) => {
  if (saving.value) return
  saving.value = true
  errorMessage.value = null
  try {
    const updated = await adminUserAPI.update(user.id, { role: user.role })
    const idx = users.value.findIndex((u) => u.id === user.id)
    if (idx !== -1) {
      users.value[idx] = updated
    }
  } catch (err: any) {
    console.error('역할 변경 실패', err)
    errorMessage.value = err?.response?.data?.detail || '역할을 변경하지 못했습니다.'
    // 실패 시 원래 역할로 롤백
    await loadUsers()
  } finally {
    saving.value = false
  }
}

const toggleActive = async (user: AdminUser) => {
  if (saving.value) return
  saving.value = true
  errorMessage.value = null
  try {
    const updated = await adminUserAPI.update(user.id, { is_active: !user.is_active })
    const idx = users.value.findIndex((u) => u.id === user.id)
    if (idx !== -1) {
      users.value[idx] = updated
    }
  } catch (err: any) {
    console.error('계정 상태 변경 실패', err)
    errorMessage.value = err?.response?.data?.detail || '계정 상태를 변경하지 못했습니다.'
    await loadUsers()
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  loadUsers()
})
</script>

<style scoped>
.admin-page {
  padding: 28px;
}

.summary {
  margin-bottom: 14px;
}

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 10px;
}

.kpi-card {
  padding: 12px 14px;
  background: #fff;
  border-radius: 14px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 6px 20px rgba(15, 23, 42, 0.04);
}

.kpi-card .label {
  font-size: 12px;
  color: #64748b;
  font-weight: 700;
}

.kpi-card .value {
  margin-top: 4px;
  font-size: 20px;
  font-weight: 800;
  color: #0f172a;
}

.kpi-card .value-sub {
  font-size: 13px;
  font-weight: 600;
  color: #64748b;
}

.kpi-card .hint {
  margin-top: 2px;
  font-size: 11px;
  color: #94a3b8;
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

.sync {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.08);
  font-weight: 700;
}

.sync .dot {
  width: 10px;
  height: 10px;
  border-radius: 999px;
}

.sync .ok {
  background: #10b981;
  box-shadow: 0 0 0 6px rgba(16, 185, 129, 0.15);
}

.sync .syncing {
  background: #f59e0b;
  animation: pulse 1.4s infinite;
}

@keyframes pulse {
  0% {
    box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.4);
  }
  70% {
    box-shadow: 0 0 0 8px rgba(245, 158, 11, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(245, 158, 11, 0);
  }
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

.data-mode-toggle {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-left: 10px;
  font-size: 11px;
  color: #64748b;
}

.data-mode-toggle input {
  width: 14px;
  height: 14px;
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

.username-cell {
  display: flex;
  align-items: center;
  gap: 6px;
}

.username-input {
  min-width: 140px;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  padding: 5px 8px;
  font-size: 13px;
}

.inline-select {
  border-radius: 999px;
  border: 1px solid #e2e8f0;
  padding: 4px 8px;
  font-size: 12px;
  background: #f9fafb;
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

.status-toggle {
  border-radius: 999px;
  padding: 4px 10px;
  font-size: 12px;
  font-weight: 600;
  border: 1px solid transparent;
  cursor: pointer;
}

.status-toggle.on {
  background: #dcfce7;
  color: #166534;
  border-color: #bbf7d0;
}

.status-toggle.off {
  background: #fee2e2;
  color: #b91c1c;
  border-color: #fecaca;
}

.status-toggle:disabled {
  opacity: 0.6;
  cursor: default;
}

.link {
  border: none;
  background: none;
  color: #2563eb;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  padding: 0;
}

.link.ghost {
  color: #64748b;
}

.link:disabled {
  opacity: 0.6;
  cursor: default;
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


