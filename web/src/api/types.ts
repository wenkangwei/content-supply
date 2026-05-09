// ===== Enums =====
export type SourceType = 'rss' | 'atom' | 'web' | 'hot_search'
export type FeedStatus = 'active' | 'paused' | 'error'
export type ItemSourceType = 'rss' | 'web' | 'hot_keyword' | 'manual' | 'jimeng'
export type ItemStatus = 'draft' | 'published' | 'archived'
export type ContentType = 'article' | 'video' | 'post'
export type TaskType = 'rss' | 'web' | 'manual' | 'hot_keyword'
export type TaskStatus = 'pending' | 'running' | 'done' | 'failed'
export type HotPlatform = 'hackernews' | 'reddit' | 'google' | 'baidu' | 'weibo' | 'zhihu' | 'douyin' | 'twitter'
export type RewriteType = 'paraphrase' | 'summarize' | 'expand'
export type CleanupStatus = 'pending_review' | 'approved' | 'rejected' | 'executing' | 'done' | 'expired'

// ===== Feed =====
export interface Feed {
  id: number
  name: string
  url: string
  source_type: SourceType
  category?: string
  poll_interval: number
  status: FeedStatus
  last_fetched_at?: string
  last_error?: string
  error_count: number
  created_at: string
  updated_at?: string
}

export interface FeedCreate {
  name: string
  url: string
  source_type: SourceType
  category?: string
  poll_interval?: number
}

export interface FeedUpdate {
  name?: string
  url?: string
  source_type?: SourceType
  category?: string
  poll_interval?: number
}

// ===== Item =====
export interface Item {
  id: string
  title: string
  summary?: string
  content?: string
  original_content?: string
  url: string
  image_url?: string
  author?: string
  source_name?: string
  source_type: ItemSourceType
  feed_id?: number
  hot_keyword_id?: number
  content_type?: ContentType
  category?: string
  tags?: string
  quality_score: number
  content_hash?: string
  is_rewritten: boolean
  rewrite_task_id?: number
  exposure_count: number
  click_count: number
  status: ItemStatus
  published_at?: string
  created_at: string
  updated_at?: string
}

export interface ItemListParams {
  skip?: number
  limit?: number
  source_type?: ItemSourceType
  category?: string
  status?: ItemStatus
}

export interface ItemSearchParams {
  query: string
  page_size?: number
  page?: number
  source_type?: ItemSourceType
  category?: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

// ===== Crawl =====
export interface CrawlTask {
  id: number
  feed_id?: number
  hot_keyword_id?: number
  url: string
  task_type: TaskType
  status: TaskStatus
  items_found: number
  items_new: number
  error_message?: string
  started_at?: string
  finished_at?: string
  created_at: string
}

export interface CrawlUrlRequest {
  url: string
  category?: string
}

export interface CrawlUrlResponse {
  task: CrawlTask
  item?: {
    title: string
    url: string
    content?: string
    author?: string
    image_url?: string
    published_at?: string
    source_type: string
    tags?: string[]
  }
}

// ===== Hot =====
export interface HotKeyword {
  id: number
  keyword: string
  platform: HotPlatform
  rank: number
  hot_score: number
  category?: string
  status: 'pending' | 'fetched' | 'processing' | 'done'
  content_fetched: boolean
  fetched_at?: string
  created_at: string
}

export interface HotTriggerResponse {
  status: string
  keywords_collected: number
  platforms: HotPlatform[]
  message: string
}

// ===== Rewrite =====
export interface RewriteTaskResponse {
  task_id: number
  item_id: string
  rewrite_type: RewriteType
  status: TaskStatus
  llm_model?: string
  message: string
}

export interface BatchRewriteRequest {
  source_type?: ItemSourceType
  rewrite_type: RewriteType
  limit?: number
}

export interface BatchRewriteResponse {
  tasks_created: number
  rewrite_type: RewriteType
  message: string
}

// ===== Cleanup =====
export interface CleanupPolicy {
  source_type: string
  ttl_days: number
  max_items: number
  min_quality: number
  cold_start_ttl_days?: number
}

export interface CleanupLog {
  id: number
  policy: string
  source_type: string
  status: CleanupStatus
  items_scanned: number
  items_to_delete: number
  items_deleted?: number
  space_freed_mb?: number
  auto_confirm_at?: string
  reviewed_by?: string
  reviewed_at?: string
  created_at: string
}

export interface CleanupReviewRequest {
  reviewer: string
  comment?: string
}

// ===== Tags =====
export interface TagMiningStatus {
  status: 'idle' | 'running'
  last_run?: string
  items_processed: number
}
