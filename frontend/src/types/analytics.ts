export type AnalyticsTab =
  | 'source'
  | 'product'
  | 'campaign'
  | 'keyword'
  | 'time'
  | 'device'
  | 'region'
  | 'retention'

export type Granularity = 'daily' | 'weekly' | 'monthly' | 'yearly'

export interface KPI {
  label: string
  value: number
  delta: number
  unit?: string
}

export interface ChannelBreakdown {
  name: string
  sessions: number
  orders: number
  conversion: number
  revenue: number
}

export interface TimeBucket {
  date: string
  sessions: number
  orders: number
  conversion: number
  revenue?: number
}

export interface HeatmapPoint {
  hour: number
  day: number
  value: number
  label: string
}

export interface KeywordRow {
  keyword: string
  clicks: number
  conversion: number
  revenue: number
}

export interface AnalyticsOverview {
  kpis: KPI[]
  breakdown: Record<AnalyticsTab, ChannelBreakdown[]>
  trend: Record<AnalyticsTab, TimeBucket[]>
  heatmap: HeatmapPoint[]
  keywords: KeywordRow[]
}
