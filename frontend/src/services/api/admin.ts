import apiClient from './client'
import type { AdminUser, AdminUserSummary } from '@/types/admin'

export const adminUserAPI = {
  // 관리자용 유저 목록 조회
  async list(params?: { q?: string; role?: string; is_active?: string }): Promise<AdminUser[]> {
    const response = await apiClient.get<AdminUser[]>('/api/admin/users/', { params })
    return response.data
  },

  // 관리자용 유저 요약 KPI 조회
  async summary(): Promise<AdminUserSummary> {
    const response = await apiClient.get<AdminUserSummary>('/api/admin/users/summary/')
    return response.data
  },

  // 관리자용 유저 상세/수정
  async update(id: number, payload: Partial<Pick<AdminUser, 'username' | 'role' | 'is_active'>>): Promise<AdminUser> {
    const response = await apiClient.patch<AdminUser>(`/api/admin/users/${id}/`, payload)
    return response.data
  },
}


