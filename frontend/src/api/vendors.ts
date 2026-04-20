import client from './client'

export async function fetchVendors(search = '', page = 1, pageSize = 50) {
  const { data } = await client.get('/vendors', { params: { search, page, page_size: pageSize } })
  return data
}

export async function fetchVendor(id: number) {
  const { data } = await client.get(`/vendors/${id}`)
  return data
}

export async function fetchVendorNews(id: number, page = 1) {
  const { data } = await client.get(`/vendors/${id}/news`, { params: { page } })
  return data
}
