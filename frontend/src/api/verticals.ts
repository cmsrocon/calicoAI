import client from './client'

export async function fetchVerticals(search = '') {
  const { data } = await client.get('/verticals', { params: { search } })
  return data
}

export async function fetchVertical(id: number) {
  const { data } = await client.get(`/verticals/${id}`)
  return data
}

export async function fetchVerticalNews(id: number, page = 1) {
  const { data } = await client.get(`/verticals/${id}/news`, { params: { page } })
  return data
}
