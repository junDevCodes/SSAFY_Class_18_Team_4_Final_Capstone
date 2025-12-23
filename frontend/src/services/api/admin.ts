import apiClient from './client'
import type { AdminUser } from '@/types/admin'

export const adminUserAPI = {
  // 관리자용 유저 목록 조회
  async list(params?: { q?: string; role?: string; is_active?: string }): Promise<AdminUser[]> {
    const response = await apiClient.get<AdminUser[]>('/api/admin/users/', { params })
    return response.data
  },
}


