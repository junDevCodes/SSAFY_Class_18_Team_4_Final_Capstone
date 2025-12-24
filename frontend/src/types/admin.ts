export interface AdminUser {
  id: number
  email: string
  username: string
  role: 'guest' | 'user' | 'seller' | 'admin'
  is_active: boolean
  date_joined: string
}

export interface AdminUserSummary {
  total_users: number
  active_users: number
  inactive_users: number
  seller_count: number
  admin_count: number
  new_users_last_7d: number
}


