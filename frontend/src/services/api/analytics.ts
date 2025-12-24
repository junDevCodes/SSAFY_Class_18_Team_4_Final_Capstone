import apiClient from './client'
import type {
  AnalyticsOverview,
  Granularity,
  AnalyticsTab,
  BehaviorOverview,
  OpsOverview
} from '@/types/analytics'

export const analyticsAPI = {
  getOverview: (params: {
    tab: AnalyticsTab
    start_date: string
    end_date: string
    granularity: Granularity
    device?: string
    region?: string
  }) =>
    apiClient.get<AnalyticsOverview>('/api/seller/analytics/overview/', {
      params
    })
}

export const adminAnalyticsAPI = {
  getOverview: (params: {
    start_date: string
    end_date: string
    granularity: Granularity
    segment?: string
    region?: string
    data_mode?: 'all' | 'real'
  }) =>
    apiClient.get<AnalyticsOverview>('/api/admin/analytics/overview/', {
      params
    }),

  getRecommendationTrend: (params: {
    start_date: string
    end_date: string
    granularity: Granularity
    segment?: string
    placement?: string
    data_mode?: 'all' | 'real'
  }) =>
    apiClient.get<{ series: Array<{
      date: string
      impressions: number
      clicks: number
      attributed_orders: number
      attributed_gmv: number
      ctr: number
      purchase_conversion: number
      gmv_share: number
      total_gmv: number
    }> }>('/api/admin/analytics/recommendation/trend/', {
      params
    }),

  getRecommendationPlacementSummary: (params: {
    start_date: string
    end_date: string
    granularity: Granularity
    segment?: string
    data_mode?: 'all' | 'real'
  }) =>
    apiClient.get<{
      placements: Array<{
        placement: string
        impressions: number
        clicks: number
        attributed_orders: number
        attributed_gmv: number
        ctr: number
        purchase_conversion: number
        gmv_share: number
      }>
    }>('/api/admin/analytics/recommendation/placement-summary/', {
      params
    }),

  getBehaviorOverview: (params: {
    start_date: string
    end_date: string
    segment?: string
    data_mode?: 'all' | 'real'
  }) =>
    apiClient.get<BehaviorOverview>('/api/admin/analytics/behavior/', {
      params
    }),

  getOpsOverview: (params: {
    range?: '1h' | '7d' | '30d'
    start_date?: string
    end_date?: string
    system?: string
  }) =>
    apiClient.get<OpsOverview>('/api/admin/analytics/ops/', {
      params
    })
}
