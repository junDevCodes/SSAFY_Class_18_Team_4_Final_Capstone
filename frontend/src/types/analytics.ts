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

// ----- Admin Behavior Analytics -----

export interface BehaviorTrendPoint {
  date: string
  buyers: number
  cart_adds: number
  orders: number
  cart_to_order_rate: number
  sessions: number
}

export interface BehaviorFunnelStep {
  name: string
  value: number
  rate?: number | null
}

export interface BehaviorOverview {
  kpis: KPI[]
  trend: BehaviorTrendPoint[]
  funnels: BehaviorFunnelStep[]
  cohorts: Record<string, unknown>[]
}

// ----- Admin Operational Analytics -----

export interface OpsMetricPoint {
  timestamp: string
  crawling_success_rate: number
  api_p95_ms: number
  error_rate: number
  availability: number
}

export type OpsIncidentSeverity = 'low' | 'medium' | 'high'

export interface OpsIncident {
  id: string
  severity: OpsIncidentSeverity | string
  category?: string
  code?: string
  service: string
  title: string
  description: string
  started_at: string
  resolved_at: string | null
}

export type AlertSeverity = 'low' | 'medium' | 'high'

export interface OpsAlert {
  id: string
  severity: AlertSeverity | string
  category?: string
  code?: string
  title: string
  description: string
  metric: string
  metric_value?: number | null
  metric_unit?: string | null
  related_metric_key?: string | null
  source_type?: string | null
  source_id?: string | null
}

export type TodoPriority = 'low' | 'medium' | 'high'

export interface OpsTodo {
  id: string
  title: string
  description: string
  meta: string
  related_alert_id?: string | null
  priority: TodoPriority | string
  category?: string | null
  source_type?: string | null
  source_id?: string | null
  code?: string | null
}

export interface OpsOverview {
  kpis: KPI[]
  timeseries: OpsMetricPoint[]
  incidents: OpsIncident[]
  alerts: OpsAlert[]
  todos: OpsTodo[]
  meta?: {
    backend?: string
    start?: string
    end?: string
    [key: string]: any
  }
}