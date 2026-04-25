import client from './client'

export async function fetchOverallTrend(topicId?: number) {
  const { data } = await client.get('/trends/overall', { params: { topic_id: topicId } })
  return data
}

export async function fetchVendorTrends(limit = 10, topicId?: number) {
  const { data } = await client.get('/trends/vendors', { params: { limit, topic_id: topicId } })
  return data
}

export async function fetchVerticalTrends(limit = 10, topicId?: number) {
  const { data } = await client.get('/trends/verticals', { params: { limit, topic_id: topicId } })
  return data
}
