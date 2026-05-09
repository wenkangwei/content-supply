import apiClient from './client'
import type { HotKeyword, HotPlatform } from './types'

export const getHotKeywords = (params?: { limit?: number; platform?: HotPlatform; category?: string }) =>
  apiClient.get<never, HotKeyword[]>('/hot/keywords', { params })

export const triggerHotCollection = (platforms?: HotPlatform[]) =>
  apiClient.post<never, { status: string; keywords_collected: number; platforms: HotPlatform[]; message: string }>('/hot/trigger', platforms ? { platforms } : undefined)
