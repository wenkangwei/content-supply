import apiClient from './client'
import type { RewriteTaskResponse, RewriteType, BatchRewriteRequest, BatchRewriteResponse } from './types'

export const rewriteItem = (itemId: string, rewriteType: RewriteType) =>
  apiClient.post<never, RewriteTaskResponse>(`/rewrite/${itemId}`, { rewrite_type: rewriteType })

export const batchRewrite = (data: BatchRewriteRequest) =>
  apiClient.post<never, BatchRewriteResponse>('/rewrite/batch', data)
