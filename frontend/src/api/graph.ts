import client from './client'

export async function fetchEntityGraph(topicId?: number) {
  const { data } = await client.get('/graph/network', {
    params: topicId ? { topic_id: topicId } : {},
  })
  return data
}
