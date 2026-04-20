import client from './client'

export async function fetchOverallTrend() {
  const { data } = await client.get('/trends/overall')
  return data
}

export async function fetchVendorTrends(limit = 10) {
  const { data } = await client.get('/trends/vendors', { params: { limit } })
  return data
}

export async function fetchVerticalTrends(limit = 10) {
  const { data } = await client.get('/trends/verticals', { params: { limit } })
  return data
}
