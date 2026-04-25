import type { Source } from '../types'
import client from './client'

export async function fetchSources(topicId?: number): Promise<Source[]> {
  const { data } = await client.get('/sources', { params: topicId ? { topic_id: topicId } : {} })
  return data
}

export async function createSource(body: Partial<Source>): Promise<Source> {
  const { data } = await client.post('/sources', body)
  return data
}

export async function updateSource(id: number, body: Partial<Source>): Promise<Source> {
  const { data } = await client.patch(`/sources/${id}`, body)
  return data
}

export async function deleteSource(id: number): Promise<void> {
  await client.delete(`/sources/${id}`)
}

export async function testSource(id: number) {
  const { data } = await client.post(`/sources/${id}/test`)
  return data
}
