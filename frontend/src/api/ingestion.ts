import client from './client'

export async function fetchIngestionStatus() {
  const { data } = await client.get('/ingestion/status')
  return data
}

export async function triggerIngestion(topicId?: number) {
  const { data } = await client.post('/ingestion/trigger', null, {
    params: topicId ? { topic_id: topicId } : {},
  })
  return data
}

export async function fetchIngestionRuns(page = 1) {
  const { data } = await client.get('/ingestion/runs', { params: { page } })
  return data
}
