import client from './client'
import type { AdminUser, UserActivity } from '../types'

export async function fetchUsers(): Promise<AdminUser[]> {
  const { data } = await client.get('/admin/users')
  return data
}

export async function createUser(body: {
  email: string
  full_name: string
  password: string
  role: 'user' | 'admin' | 'superadmin'
  monthly_token_limit?: number | null
}): Promise<AdminUser> {
  const { data } = await client.post('/admin/users', body)
  return data
}

export async function updateUser(
  id: number,
  body: {
    full_name?: string
    password?: string
    role?: 'user' | 'admin' | 'superadmin'
    is_active?: boolean
    monthly_token_limit?: number | null
    clear_monthly_token_limit?: boolean
  },
): Promise<AdminUser> {
  const { data } = await client.patch(`/admin/users/${id}`, body)
  return data
}

export async function deleteUser(id: number): Promise<void> {
  await client.delete(`/admin/users/${id}`)
}

export async function fetchActivity(limit = 100): Promise<UserActivity[]> {
  const { data } = await client.get('/admin/activity', { params: { limit } })
  return data
}
