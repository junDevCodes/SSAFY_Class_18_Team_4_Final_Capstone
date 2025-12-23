export interface AdminUser {
  id: number
  email: string
  username: string
  role: 'guest' | 'user' | 'seller' | 'admin'
  is_active: boolean
  date_joined: string
}


