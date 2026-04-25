import client from './client'

export async function fetchVendors(search = '', page = 1, pageSize = 50, topicId?: number) {
  const { data } = await client.get('/vendors', { params: { search, page, page_size: pageSize, topic_id: topicId } })
  return data
}

export async function fetchVendor(id: number, topicId?: number) {
  const { data } = await client.get(`/vendors/${id}`, { params: { topic_id: topicId } })
  return data
}

export async function fetchVendorNews(id: number, page = 1, topicId?: number) {
  const { data } = await client.get(`/vendors/${id}/news`, { params: { page, topic_id: topicId } })
  return data
}
