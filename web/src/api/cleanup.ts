import apiClient from './client'
import type { CleanupLog, CleanupReviewRequest } from './types'

export const getCleanupPolicies = () =>
  apiClient.get<never, Array<{ source_type: string; ttl_days: number; max_items: number; min_quality: number }>>('/cleanup/policies')

export const triggerCleanupScan = () =>
  apiClient.post<never, { scan_results: Array<{ policy: string; source_type: string; items_scanned: number; items_to_delete: number }>; total_pending: number; message: string }>('/cleanup/trigger')

export const getPendingCleanups = () =>
  apiClient.get<never, CleanupLog[]>('/cleanup/pending')

export const confirmCleanup = (logId: number, data: CleanupReviewRequest) =>
  apiClient.post<never, { log_id: number; status: string; items_deleted?: number; space_freed_mb?: number; message: string }>(`/cleanup/${logId}/confirm`, data)

export const rejectCleanup = (logId: number, data: CleanupReviewRequest) =>
  apiClient.post<never, { log_id: number; status: string; message: string }>(`/cleanup/${logId}/reject`, data)

export const getCleanupLogs = (params?: { skip?: number; limit?: number }) =>
  apiClient.get<never, CleanupLog[]>('/cleanup/logs', { params })
