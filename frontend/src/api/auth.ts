import client from './client'
import type { CurrentUser } from '../types'

export async function fetchCurrentUser(): Promise<CurrentUser> {
  const { data } = await client.get('/auth/me')
  return data
}

export async function login(body: { email: string; password: string }): Promise<CurrentUser> {
  const { data } = await client.post('/auth/login', body)
  return data
}

export async function logout(): Promise<void> {
  await client.post('/auth/logout')
}
