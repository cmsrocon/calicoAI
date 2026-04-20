import client from './client'

export async function fetchSettings(): Promise<Record<string, string>> {
  const { data } = await client.get('/settings')
  return data
}

export async function updateSettings(body: Record<string, string>) {
  const { data } = await client.patch('/settings', body)
  return data
}

export async function checkHealth() {
  const { data } = await client.get('/settings/health')
  return data
}
