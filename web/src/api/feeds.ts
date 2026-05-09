import apiClient from './client'
import type { Feed, FeedCreate, FeedUpdate } from './types'

export const getFeeds = (params?: { skip?: number; limit?: number }) =>
  apiClient.get<never, Feed[]>('/feeds', { params })

export const getFeed = (id: number) =>
  apiClient.get<never, Feed>(`/feeds/${id}`)

export const createFeed = (data: FeedCreate) =>
  apiClient.post<never, Feed>('/feeds', data)

export const updateFeed = (id: number, data: FeedUpdate) =>
  apiClient.put<never, Feed>(`/feeds/${id}`, data)

export const deleteFeed = (id: number) =>
  apiClient.delete(`/feeds/${id}`)

export const toggleFeed = (id: number) =>
  apiClient.post<never, { id: number; name: string; status: string; message: string }>(`/feeds/${id}/toggle`)
