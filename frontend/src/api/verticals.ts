import client from './client'

export async function fetchVerticals(search = '', topicId?: number) {
  const { data } = await client.get('/verticals', { params: { search, topic_id: topicId } })
  return data
}

export async function fetchVertical(id: number, topicId?: number) {
  const { data } = await client.get(`/verticals/${id}`, { params: { topic_id: topicId } })
  return data
}

export async function fetchVerticalNews(id: number, page = 1, topicId?: number) {
  const { data } = await client.get(`/verticals/${id}/news`, { params: { page, topic_id: topicId } })
  return data
}
