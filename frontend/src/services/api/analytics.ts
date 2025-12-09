import apiClient from './client'
import type { AnalyticsOverview, Granularity, AnalyticsTab } from '@/types/analytics'

export const analyticsAPI = {
  getOverview: (params: {
    tab: AnalyticsTab
    start_date: string
    end_date: string
    granularity: Granularity
    store?: string
    device?: string
    region?: string
  }) =>
    apiClient.get<AnalyticsOverview>('/api/seller/analytics/overview/', {
      params
    })
}
