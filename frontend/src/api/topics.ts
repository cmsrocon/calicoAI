import type { Topic, TopicCreateResponse } from '../types'
import client from './client'

export async function fetchTopics(): Promise<Topic[]> {
  const { data } = await client.get('/topics')
  return data
}

export async function createTopic(body: { name: string; description?: string }): Promise<TopicCreateResponse> {
  const { data } = await client.post('/topics', body)
  return data
}

export async function updateTopic(id: number, body: { name?: string; description?: string }): Promise<Topic> {
  const { data } = await client.patch(`/topics/${id}`, body)
  return data
}

export async function deleteTopic(id: number): Promise<void> {
  await client.delete(`/topics/${id}`)
}
