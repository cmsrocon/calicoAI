export interface Source {
  id: number
  url: string
  name: string
  feed_type: string
  is_active: boolean
  trust_weight: number
  css_selector: string | null
  last_fetched_at: string | null
  last_error: string | null
  created_at: string
  updated_at: string
}

export interface VendorTag {
  id: number
  name: string
  slug: string
  confidence: number
}

export interface VerticalTag {
  id: number
  name: string
  slug: string
  confidence: number
}

export interface NewsItemSummary {
  id: number
  headline: string
  external_url: string
  source_id: number | null
  source_name: string | null
  published_at: string | null
  ingested_at: string
  language: string
  summary: string | null
  why_it_matters: string | null
  importance_rank: number | null
  ai_relevance_score: number | null
  vendors: VendorTag[]
  verticals: VerticalTag[]
}

export interface NewsItemDetail extends NewsItemSummary {
  pros: string[]
  cons: string[]
  balanced_take: string | null
  is_processed: boolean
}

export interface NewsListResponse {
  items: NewsItemSummary[]
  total: number
  page: number
  page_size: number
}

export interface Vendor {
  id: number
  name: string
  slug: string
  description: string | null
  aliases: string[]
  is_active: boolean
  news_count: number
}

export interface VendorSummary {
  id: number
  name: string
  slug: string
  description: string | null
  news_count: number
}

export interface Vertical {
  id: number
  name: string
  slug: string
  description: string | null
  icon_name: string | null
  news_count: number
}

export interface Trend {
  id: number
  trend_type: string
  entity_id: number | null
  period_start: string
  period_end: string
  narrative: string | null
  sentiment_score: number | null
  top_themes: string[]
  item_count: number
  generated_at: string
}

export interface IngestionRun {
  id: number
  started_at: string
  finished_at: string | null
  status: string
  items_fetched: number
  items_new: number
  items_duplicate: number
  triggered_by: string
  error_message: string | null
}

export interface IngestionStatus {
  last_run: IngestionRun | null
  next_run_at: string | null
  is_running: boolean
}
