import apiClient from './client'
import type { CrawlTask, CrawlUrlRequest, CrawlUrlResponse } from './types'

export const triggerFeedCrawl = (feedId: number) =>
  apiClient.post<never, CrawlTask>(`/crawl/feed/${feedId}`)

export const crawlUrl = (data: CrawlUrlRequest) =>
  apiClient.post<never, CrawlUrlResponse>('/crawl/url', data)

export const getCrawlTasks = (params?: { skip?: number; limit?: number }) =>
  apiClient.get<never, CrawlTask[]>('/tasks', { params })
