import client from './client'

export async function fetchIngestionStatus() {
  const { data } = await client.get('/ingestion/status')
  return data
}

export async function triggerIngestion() {
  const { data } = await client.post('/ingestion/trigger')
  return data
}

export async function fetchIngestionRuns(page = 1) {
  const { data } = await client.get('/ingestion/runs', { params: { page } })
  return data
}
