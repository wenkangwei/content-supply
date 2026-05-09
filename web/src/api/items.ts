import apiClient from './client'
import type { Item, ItemSearchParams, ItemStatus } from './types'

export const getItems = (params?: { skip?: number; limit?: number; source_type?: string; category?: string; status?: string }) =>
  apiClient.get<never, Item[]>('/items', { params })

export const getItem = (id: string) =>
  apiClient.get<never, Item>(`/items/${id}`)

export const searchItems = (data: ItemSearchParams) =>
  apiClient.post<never, Item[]>('/items/search', data)

export const updateItemStatus = (id: string, status: ItemStatus) =>
  apiClient.put<never, { message: string }>(`/items/${id}/status`, null, { params: { status } })

export const getItemCount = (params?: { source_type?: string; status?: string }) =>
  apiClient.get<never, { total: number }>('/items/count', { params })
