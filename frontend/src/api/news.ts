import type { NewsItemDetail, NewsListResponse } from '../types'
import client from './client'

export interface NewsFilters {
  page?: number
  page_size?: number
  date_from?: string
  date_to?: string
  vendor_id?: number
  vertical_id?: number
  source_id?: number
  language?: string
  min_importance?: number
  search?: string
  sort_by?: 'importance' | 'date'
}

export async function fetchNews(filters: NewsFilters = {}): Promise<NewsListResponse> {
  const params = Object.fromEntries(Object.entries(filters).filter(([, v]) => v !== undefined && v !== ''))
  const { data } = await client.get('/news', { params })
  return data
}

export async function fetchNewsItem(id: number): Promise<NewsItemDetail> {
  const { data } = await client.get(`/news/${id}`)
  return data
}
