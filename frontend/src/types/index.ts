export interface Source {
  id: number
  topic_id: number
  topic_name: string | null
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

export interface StorySourceDocument {
  url: string
  source_name: string | null
  headline: string
  published_at: string | null
  is_primary: boolean
}

export interface NewsItemSummary {
  id: number
  topic_id: number
  topic_name: string
  topic_slug: string
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
  source_documents: StorySourceDocument[]
  vendors: VendorTag[]
  verticals: VerticalTag[]
}

export interface NewsItemDetail extends NewsItemSummary {
  pros: string[]
  cons: string[]
  balanced_take: string | null
  is_processed: boolean
  processing_error: string | null
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
  topic_id: number | null
  topic_name: string | null
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

export interface EntityGraphNode {
  id: string
  entity_id: number
  entity_type: 'vendor' | 'vertical'
  name: string
  article_count: number
  importance_score: number
}

export interface EntityGraphLink {
  source: string
  target: string
  article_count: number
  strength_score: number
  description: string
  sample_headlines: string[]
}

export interface EntityGraphNetwork {
  topic_id: number | null
  scope_label: string
  node_count: number
  link_count: number
  nodes: EntityGraphNode[]
  links: EntityGraphLink[]
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
  llm_calls: number
  tokens_in: number
  tokens_out: number
  estimated_cost_usd: number | null
}

export interface IngestionStatus {
  last_run: IngestionRun | null
  next_run_at: string | null
  is_running: boolean
  current_stage: string | null
  current_stage_detail: string | null
  last_error: string | null
  live_calls: number | null
  live_tokens_in: number | null
  live_tokens_out: number | null
  live_cost_usd: number | null
}

export interface UserQuotaSummary {
  used_tokens: number
  monthly_token_limit: number | null
  remaining_tokens: number | null
  window_days: number
}

export interface CurrentUser {
  id: number
  email: string
  full_name: string
  role: 'user' | 'admin' | 'superadmin'
  is_active: boolean
  last_login_at: string | null
  quota: UserQuotaSummary
}

export interface AdminUser extends CurrentUser {
  created_at: string
  updated_at: string
}

export interface UserActivity {
  id: number
  user_id: number | null
  user_email: string | null
  action: string
  method: string
  path: string
  status_code: number
  ip_address: string | null
  user_agent: string | null
  details: Record<string, unknown> | null
  created_at: string
}

export interface Topic {
  id: number
  name: string
  slug: string
  description: string | null
  is_default: boolean
  source_count: number
  article_count: number
  created_at: string
  updated_at: string
}

export interface TopicCreateResponse {
  topic: Topic
  seeded_sources_count: number
  seed_status: 'ok' | 'warning'
  seed_message: string | null
}
