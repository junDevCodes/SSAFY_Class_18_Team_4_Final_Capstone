<template>
  <div class="admin-analytics">
    <header class="page-header">
      <div>
        <p class="eyebrow">전체 관리자</p>
        <h1>통합 지표 · 리스크 모니터링</h1>
        <p class="sub">회원, 주문, 매출, 리스크 이벤트를 한 곳에서 관제합니다.</p>
      </div>
      <div class="sync">
        <span class="dot" :class="loading ? 'syncing' : 'ok'"></span>
        <span>동기화: {{ lastUpdated }}</span>
      </div>
    </header>

    <section class="filters">
      <div class="filter">
        <span class="label">조회 단위</span>
        <div class="segmented">
          <button
            v-for="unit in granularityOptions"
            :key="unit"
            :class="{ active: granularity === unit }"
            @click="granularity = unit"
          >
            {{ unitLabel(unit) }}
          </button>
        </div>
      </div>
      <div class="filter wide">
        <span class="label">조회 기간</span>
        <div class="date-range">
          <input type="date" v-model="dateRange.start" />
          <span class="tilde">~</span>
          <input type="date" v-model="dateRange.end" />
        </div>
      </div>
      <div class="filter">
        <span class="label">세그먼트</span>
        <select v-model="segment">
          <option value="all">전체</option>
          <option value="consumer">일반회원</option>
          <option value="seller">판매자</option>
          <option value="admin">관리자</option>
        </select>
      </div>
      <div class="filter">
        <span class="label">지역</span>
        <select v-model="region">
          <option value="all">전국</option>
          <option value="metro">수도권</option>
          <option value="local">비수도권</option>
        </select>
      </div>
      <div class="actions">
        <button class="primary" :disabled="loading" @click="loadData">조회</button>
        <button class="ghost" :disabled="loading" @click="resetFilters">초기화</button>
      </div>
    </section>

    <section v-if="errorMessage" class="alert error">
      {{ errorMessage }}
    </section>

    <nav class="section-nav" aria-label="Dashboard sections">
      <a v-for="item in sectionLinks" :key="item.id" :href="`#${item.id}`">{{ item.label }}</a>
    </nav>

    <section id="topline" class="dashboard-section">
      <header class="section-head">
        <div>
          <p class="eyebrow">Top Line Dashboard</p>
          <h2>비즈니스 성과 지표</h2>
          <p class="section-sub">CEO/PM이 가장 먼저 보는 핵심 KPI</p>
        </div>
      </header>

      <div class="kpi-grid">
        <article v-for="card in topLineKpiCards" :key="card.key" class="kpi-card">
          <p class="label">{{ card.label }}</p>
          <div class="value-row">
            <span class="value">{{ formatNumber(card.value, card.unit, card.decimals) }}</span>
            <span :class="['delta', card.delta >= 0 ? 'up' : 'down']">
              {{ card.delta >= 0 ? '▲' : '▼' }} {{ Math.abs(card.delta).toFixed(1) }}%
            </span>
          </div>
          <p class="hint">전 기간 대비</p>
        </article>
      </div>

      <div class="grid">
        <article class="card">
          <header class="card-head">
            <div>
              <p class="eyebrow">추이</p>
              <h3>매출 · 주문 · 전환</h3>
            </div>
          </header>
          <div ref="trendChartRef" class="chart"></div>
        </article>

        <article class="card">
          <header class="card-head">
            <div>
              <p class="eyebrow">상위 5개</p>
              <h3>카테고리별 성과</h3>
            </div>
            <span class="hint">매출 / 주문 / 전환율</span>
          </header>
          <div ref="breakdownChartRef" class="chart"></div>
        </article>
      </div>

    </section>

    <section id="recommendation" class="dashboard-section">
      <header class="section-head">
        <div>
          <p class="eyebrow">Recommendation Dashboard</p>
          <h2>추천 알고리즘 성과 지표</h2>
          <p class="section-sub">추천 클릭율/전환율/기여 GMV를 한 눈에</p>
        </div>
      </header>

      <div class="kpi-grid">
        <article v-for="card in recommendationKpiCards" :key="card.key" class="kpi-card">
          <p class="label">{{ card.label }}</p>
          <div class="value-row">
            <span class="value">{{ formatNumber(card.value, card.unit, card.decimals) }}</span>
            <span :class="['delta', card.delta >= 0 ? 'up' : 'down']">
              {{ card.delta >= 0 ? '▲' : '▼' }} {{ Math.abs(card.delta).toFixed(1) }}%
            </span>
          </div>
          <p class="hint">전 기간 대비</p>
        </article>
      </div>

    </section>

    <section id="behavior" class="dashboard-section">
      <header class="section-head">
        <div>
          <p class="eyebrow">User Behavior Dashboard</p>
          <h2>유저 행동 지표</h2>
          <p class="section-sub">활성도/전환/이탈을 빠르게 점검</p>
        </div>
      </header>

      <div class="kpi-grid">
        <article v-for="card in behaviorKpiCards" :key="card.key" class="kpi-card">
          <p class="label">{{ card.label }}</p>
          <div class="value-row">
            <span class="value">{{ formatNumber(card.value, card.unit, card.decimals) }}</span>
            <span :class="['delta', card.delta >= 0 ? 'up' : 'down']">
              {{ card.delta >= 0 ? '▲' : '▼' }} {{ Math.abs(card.delta).toFixed(1) }}%
            </span>
          </div>
          <p class="hint">전 기간 대비</p>
        </article>
      </div>

    </section>

    <section id="operational" class="dashboard-section">
      <header class="section-head">
        <div>
          <p class="eyebrow">Operational Dashboard</p>
          <h2>운영 건강도 지표</h2>
          <p class="section-sub">크롤링/서버/에러 모니터링(DevOps용)</p>
        </div>
      </header>

      <div class="kpi-grid">
        <article v-for="card in operationalKpiCards" :key="card.key" class="kpi-card">
          <p class="label">{{ card.label }}</p>
          <div class="value-row">
            <span class="value">{{ formatNumber(card.value, card.unit, card.decimals) }}</span>
            <span :class="['delta', card.delta >= 0 ? 'up' : 'down']">
              {{ card.delta >= 0 ? '▲' : '▼' }} {{ Math.abs(card.delta).toFixed(1) }}%
            </span>
          </div>
          <p class="hint">전 기간 대비</p>
        </article>
      </div>

      <div class="grid alerts">
        <article class="card">
          <header class="card-head">
            <div>
              <p class="eyebrow">이상 징후</p>
              <h3>리스크 알림</h3>
            </div>
          </header>
          <ul class="alert-list">
            <li v-for="alert in riskAlerts" :key="alert.title">
              <div class="pill" :class="alert.level">{{ alert.level.toUpperCase() }}</div>
              <div class="alert-body">
                <p class="alert-title">{{ alert.title }}</p>
                <p class="alert-desc">{{ alert.desc }}</p>
              </div>
              <span class="alert-meta">{{ alert.time }}</span>
            </li>
          </ul>
        </article>
        <article class="card">
          <header class="card-head">
            <div>
              <p class="eyebrow">운영 체크리스트</p>
              <h3>즉시 조치 항목</h3>
            </div>
          </header>
          <ul class="todo-list">
            <li v-for="item in actionItems" :key="item.title">
              <input type="checkbox" :checked="item.done" @change.prevent />
              <div class="todo-body">
                <p class="todo-title">{{ item.title }}</p>
                <p class="todo-desc">{{ item.desc }}</p>
              </div>
              <span class="todo-meta">{{ item.owner }}</span>
            </li>
          </ul>
        </article>
      </div>

    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import * as echarts from 'echarts/core'
import { BarChart, LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, TitleComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { adminAnalyticsAPI } from '@/services/api/analytics'
import type { AnalyticsOverview, Granularity, TimeBucket, ChannelBreakdown } from '@/types/analytics'

echarts.use([BarChart, LineChart, GridComponent, TooltipComponent, LegendComponent, TitleComponent, CanvasRenderer])

const granularityOptions: Granularity[] = ['daily', 'weekly', 'monthly']
const granularity = ref<Granularity>('daily')
const dateRange = ref({ start: getDateNDaysAgo(13), end: getDateNDaysAgo(0) })
const segment = ref('all')
const region = ref('all')

const overview = ref<AnalyticsOverview | null>(null)
const loading = ref(false)
const errorMessage = ref<string | null>(null)
const lastUpdated = ref(new Date().toLocaleString())

const trendChartRef = ref<HTMLDivElement | null>(null)
const breakdownChartRef = ref<HTMLDivElement | null>(null)
const charts: Record<'trend' | 'breakdown', echarts.ECharts | null> = {
  trend: null,
  breakdown: null,
}

const mockOverview = buildMockOverview()

const trendData = computed(() => formatTrend(overview.value?.trend.source ?? mockOverview.trend.source, granularity.value))
const breakdownData = computed(() => overview.value?.breakdown.product ?? mockOverview.breakdown.product)

type DashboardKpiCard = {
  key: string
  label: string
  value: number
  unit?: string
  decimals?: number
  delta: number
}

const sectionLinks = [
  { id: 'topline', label: 'Top Line' },
  { id: 'recommendation', label: 'Recommendation' },
  { id: 'behavior', label: 'User Behavior' },
  { id: 'operational', label: 'Operational' },
]

const riskAlerts = computed(() => [
  { level: 'high', title: '반품률 급등 (주간 +2.8%)', desc: '카테고리: 과일·채소, 특정 판매자 3곳 집중', time: '5분 전' },
  { level: 'medium', title: '장바구니 이탈 증가', desc: '결제 단계 세션 대비 -6.2%', time: '18분 전' },
  { level: 'low', title: '신규 가입 일시 감소', desc: '어제 대비 -3.1%, 광고 소재 점검 권고', time: '1시간 전' },
])

const actionItems = computed(() => [
  { title: '광고 채널 성과 리밸런싱', desc: 'CPC 상승 채널 예산 10% 이관', owner: '마케팅', done: false },
  { title: '반품 사유 샘플링', desc: '상위 반품 주문 20건 원인 조사', owner: 'CS', done: false },
  { title: '야간 트래픽 튜닝', desc: '22~01시 서버 응답 지연 모니터링', owner: '플랫폼', done: true },
])

const loadData = async () => {
  if (!dateRange.value.start || !dateRange.value.end) {
    errorMessage.value = '조회 기간을 선택해주세요.'
    return
  }

  loading.value = true
  errorMessage.value = null

  try {
    const { data } = await adminAnalyticsAPI.getOverview({
      start_date: dateRange.value.start,
      end_date: dateRange.value.end,
      granularity: granularity.value,
      segment: segment.value,
      region: region.value,
    })
    overview.value = data
  } catch (err: any) {
    console.warn('adminAnalyticsAPI 실패, mock 데이터 사용', err)
    overview.value = mockOverview
    errorMessage.value = err?.response?.data?.detail || '실시간 데이터를 불러오지 못해 샘플 데이터를 표시합니다.'
  } finally {
    loading.value = false
    await nextTick()
    renderCharts()
    lastUpdated.value = new Date().toLocaleString()
  }
}

const resetFilters = () => {
  granularity.value = 'daily'
  dateRange.value = { start: getDateNDaysAgo(13), end: getDateNDaysAgo(0) }
  segment.value = 'all'
  region.value = 'all'
  loadData()
}

const unitLabel = (unit: Granularity) => (unit === 'daily' ? '일간' : unit === 'weekly' ? '주간' : '월간')

const formatNumber = (value: number, unit?: string, decimals?: number) => {
  const resolvedDecimals = decimals ?? (unit === '%' ? 1 : 0)
  const formatted = value.toLocaleString('ko-KR', {
    minimumFractionDigits: resolvedDecimals,
    maximumFractionDigits: resolvedDecimals,
  })
  return unit ? `${formatted}${unit}` : formatted
}

function percentChange(current: number, previous: number) {
  if (!Number.isFinite(current) || !Number.isFinite(previous)) return 0
  if (previous === 0) return 0
  return ((current - previous) / previous) * 100
}

function periodDelta(data: TimeBucket[], calc: (slice: TimeBucket[]) => number) {
  if (data.length < 2) return 0
  const mid = Math.max(1, Math.floor(data.length / 2))
  const prev = calc(data.slice(0, mid))
  const curr = calc(data.slice(mid))
  return percentChange(curr, prev)
}

const toplineSummary = computed(() => {
  const data = trendData.value
  const sessions = data.reduce((s, v) => s + v.sessions, 0)
  const orders = data.reduce((s, v) => s + v.orders, 0)
  const revenue = data.reduce((s, v) => s + (v.revenue ?? 0), 0)
  const conversion = sessions ? (orders / sessions) * 100 : 0
  const aov = orders ? revenue / orders : 0
  return { sessions, orders, revenue, conversion, aov }
})

const topLineKpiCards = computed<DashboardKpiCard[]>(() => {
  const data = trendData.value
  const sumRevenue = (slice: TimeBucket[]) => slice.reduce((s, v) => s + (v.revenue ?? 0), 0)
  const sumOrders = (slice: TimeBucket[]) => slice.reduce((s, v) => s + v.orders, 0)
  const sumSessions = (slice: TimeBucket[]) => slice.reduce((s, v) => s + v.sessions, 0)
  const conversionRate = (slice: TimeBucket[]) => {
    const sessions = sumSessions(slice)
    const orders = sumOrders(slice)
    return sessions ? (orders / sessions) * 100 : 0
  }
  const aovValue = (slice: TimeBucket[]) => {
    const orders = sumOrders(slice)
    const revenue = sumRevenue(slice)
    return orders ? revenue / orders : 0
  }

  const repeatPurchaseRate = 38.7
  const cartAbandonmentRate = 62.4

  return [
    {
      key: 'gmv',
      label: 'GMV',
      value: toplineSummary.value.revenue,
      unit: '원',
      decimals: 0,
      delta: periodDelta(data, sumRevenue),
    },
    {
      key: 'orders',
      label: '주문 수',
      value: toplineSummary.value.orders,
      decimals: 0,
      delta: periodDelta(data, sumOrders),
    },
    {
      key: 'aov',
      label: '객단가 (AOV)',
      value: toplineSummary.value.aov,
      unit: '원',
      decimals: 0,
      delta: periodDelta(data, aovValue),
    },
    {
      key: 'conversion',
      label: '전환율',
      value: toplineSummary.value.conversion,
      unit: '%',
      decimals: 1,
      delta: periodDelta(data, conversionRate),
    },
    {
      key: 'repeat',
      label: '재구매율 (30D)',
      value: repeatPurchaseRate,
      unit: '%',
      decimals: 1,
      delta: 1.2,
    },
    {
      key: 'cart_abandon',
      label: '장바구니 포기율',
      value: cartAbandonmentRate,
      unit: '%',
      decimals: 1,
      delta: -0.8,
    },
  ]
})

const recommendationKpiCards: DashboardKpiCard[] = [
  { key: 'rec_exposure', label: '추천 노출 비율', value: 72.8, unit: '%', decimals: 1, delta: 2.1 },
  { key: 'rec_ctr', label: '추천 CTR', value: 8.6, unit: '%', decimals: 1, delta: 0.4 },
  { key: 'rec_cvr', label: '추천 구매 전환율', value: 3.2, unit: '%', decimals: 1, delta: 0.2 },
  { key: 'rec_gmv', label: '추천 기여 GMV 비율', value: 18.9, unit: '%', decimals: 1, delta: 1.1 },
  { key: 'airscout', label: 'AIRScout 채택률', value: 12.4, unit: '%', decimals: 1, delta: 0.6 },
  { key: 'gapfill', label: 'Gap Filling 담기율', value: 21.3, unit: '%', decimals: 1, delta: -0.3 },
]

const behaviorKpiCards: DashboardKpiCard[] = [
  { key: 'dau', label: 'DAU', value: 18450, unit: '명', decimals: 0, delta: 3.8 },
  { key: 'mau', label: 'MAU', value: 126300, unit: '명', decimals: 0, delta: 2.2 },
  { key: 'dau_mau', label: 'DAU/MAU', value: 14.6, unit: '%', decimals: 1, delta: 0.7 },
  { key: 'behavior_cvr', label: '구매 전환율', value: toplineSummary.value.conversion, unit: '%', decimals: 1, delta: 0.6 },
  { key: 'cart_abandon_2', label: '장바구니 포기율', value: 62.4, unit: '%', decimals: 1, delta: -0.8 },
  { key: 'repeat_2', label: '재구매율 (30D)', value: 38.7, unit: '%', decimals: 1, delta: 1.2 },
]

const operationalKpiCards: DashboardKpiCard[] = [
  { key: 'crawl', label: '크롤링 성공률', value: 97.4, unit: '%', decimals: 1, delta: 0.3 },
  { key: 'p95', label: '서버 응답(P95)', value: 420, unit: 'ms', decimals: 0, delta: -4.6 },
  { key: 'error', label: '에러율(5xx)', value: 0.38, unit: '%', decimals: 2, delta: -0.1 },
  { key: 'mape', label: '가격 예측 MAPE', value: 9.6, unit: '%', decimals: 1, delta: 0.4 },
  { key: 'sellers', label: '생산자 onboard', value: 342, unit: '명', decimals: 0, delta: 1.5 },
  { key: 'uptime', label: '서비스 가용성', value: 99.92, unit: '%', decimals: 2, delta: 0.02 },
]

const getChart = (key: 'trend' | 'breakdown', el: HTMLDivElement | null) => {
  if (!el) return null
  if (!charts[key]) {
    charts[key] = echarts.init(el)
  }
  return charts[key]
}

const renderTrendChart = () => {
  const chart = getChart('trend', trendChartRef.value)
  if (!chart) return
  const data = trendData.value
  chart.setOption({
    grid: { top: 30, left: 40, right: 36, bottom: 32 },
    tooltip: { trigger: 'axis' },
    legend: { data: ['매출', '주문', '전환율'], top: 0 },
    xAxis: { type: 'category', data: data.map(d => d.date) },
    yAxis: [
      { type: 'value', name: '매출(원) / 주문' },
      { type: 'value', name: '전환율(%)', position: 'right', min: 0, max: 20 },
    ],
    series: [
      { name: '매출', type: 'line', data: data.map(d => d.revenue ?? 0), smooth: true, lineStyle: { width: 3, color: '#0ea5e9' }, areaStyle: { color: 'rgba(14,165,233,0.12)' } },
      { name: '주문', type: 'bar', data: data.map(d => d.orders), itemStyle: { color: '#4c1d95' }, barWidth: 12 },
      { name: '전환율', type: 'line', yAxisIndex: 1, data: data.map(d => d.conversion), smooth: true, lineStyle: { width: 2.5, color: '#f97316' }, symbolSize: 7 },
    ],
  })
}

const renderBreakdownChart = () => {
  const chart = getChart('breakdown', breakdownChartRef.value)
  if (!chart) return
  const data = breakdownData.value
  chart.setOption({
    grid: { top: 30, left: 48, right: 36, bottom: 60 },
    tooltip: { trigger: 'axis' },
    legend: { data: ['매출', '주문', '전환율'], top: 0 },
    xAxis: { type: 'category', data: data.map(d => d.name), axisLabel: { rotate: 18 } },
    yAxis: [
      { type: 'value', name: '매출/주문' },
      { type: 'value', name: '전환율(%)', position: 'right', min: 0, max: 25 },
    ],
    series: [
      { name: '매출', type: 'bar', data: data.map(d => d.revenue), itemStyle: { color: '#22c55e' }, barWidth: 12 },
      { name: '주문', type: 'bar', data: data.map(d => d.orders), itemStyle: { color: '#a855f7' }, barWidth: 12, barGap: '25%' },
      { name: '전환율', type: 'line', yAxisIndex: 1, data: data.map(d => d.conversion), smooth: true, lineStyle: { width: 2.5, color: '#f59e0b' }, symbolSize: 7 },
    ],
  })
}

const renderCharts = () => {
  renderTrendChart()
  renderBreakdownChart()
}

const handleResize = () => {
  Object.values(charts).forEach(c => c?.resize())
}

watch([granularity], () => nextTick(renderCharts))

onMounted(() => {
  loadData()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  Object.values(charts).forEach(c => c?.dispose())
})

function getDateNDaysAgo(n: number) {
  const d = new Date()
  d.setDate(d.getDate() - n)
  return d.toISOString().slice(0, 10)
}

function formatTrend(data: TimeBucket[], unit: Granularity): TimeBucket[] {
  if (unit === 'daily') return data
  const bucketSize = unit === 'weekly' ? 7 : 30
  const buckets: TimeBucket[] = []
  for (let i = 0; i < data.length; i += bucketSize) {
    const slice = data.slice(i, i + bucketSize)
    if (!slice.length) continue
    const sessions = slice.reduce((s, v) => s + v.sessions, 0)
    const orders = slice.reduce((s, v) => s + v.orders, 0)
    const revenue = slice.reduce((s, v) => s + (v.revenue ?? 0), 0)
    const conversion = sessions ? (orders / sessions) * 100 : 0
    buckets.push({
      date: unit === 'weekly' ? `${Math.floor(i / 7) + 1}주차` : `${Math.floor(i / 30) + 1}개월차`,
      sessions,
      orders,
      conversion,
      revenue,
    })
  }
  return buckets
}

function buildMockOverview(): AnalyticsOverview {
  const trend: TimeBucket[] = [
    { date: '03-01', sessions: 920, orders: 140, revenue: 18000000, conversion: 15.2 },
    { date: '03-02', sessions: 880, orders: 128, revenue: 17200000, conversion: 14.5 },
    { date: '03-03', sessions: 960, orders: 152, revenue: 18600000, conversion: 15.8 },
    { date: '03-04', sessions: 1010, orders: 160, revenue: 19200000, conversion: 15.8 },
    { date: '03-05', sessions: 980, orders: 155, revenue: 18800000, conversion: 15.8 },
    { date: '03-06', sessions: 940, orders: 150, revenue: 18300000, conversion: 16.0 },
    { date: '03-07', sessions: 990, orders: 162, revenue: 19700000, conversion: 16.4 },
    { date: '03-08', sessions: 970, orders: 154, revenue: 18900000, conversion: 15.9 },
    { date: '03-09', sessions: 950, orders: 150, revenue: 18400000, conversion: 15.8 },
    { date: '03-10', sessions: 930, orders: 144, revenue: 17900000, conversion: 15.5 },
    { date: '03-11', sessions: 960, orders: 152, revenue: 18600000, conversion: 15.8 },
    { date: '03-12', sessions: 1020, orders: 166, revenue: 20100000, conversion: 16.3 },
    { date: '03-13', sessions: 1050, orders: 170, revenue: 20800000, conversion: 16.2 },
    { date: '03-14', sessions: 1100, orders: 182, revenue: 21800000, conversion: 16.5 },
  ]

  const product: ChannelBreakdown[] = [
    { name: '과일 · 채소', sessions: 2200, orders: 360, revenue: 42000000, conversion: 16.4 },
    { name: '정육 · 수산', sessions: 1800, orders: 290, revenue: 39000000, conversion: 16.1 },
    { name: '곡물 · 건강', sessions: 1400, orders: 220, revenue: 25000000, conversion: 15.7 },
    { name: '간편식', sessions: 1200, orders: 180, revenue: 21000000, conversion: 15.0 },
    { name: '기타', sessions: 900, orders: 140, revenue: 14000000, conversion: 15.6 },
  ]

  return {
    kpis: [
      { label: '총 매출', value: 218000000, delta: 6.2, unit: '원' },
      { label: '주문 수', value: 2540, delta: 4.1 },
      { label: '전환율', value: 15.9, delta: 0.6, unit: '%' },
      { label: '신규 가입', value: 1840, delta: -1.9 },
      { label: '재방문율', value: 42.5, delta: 1.2, unit: '%' },
      { label: '반품률', value: 3.8, delta: 0.4, unit: '%' },
    ],
    breakdown: {
      source: product,
      product,
      campaign: product,
      keyword: product,
      time: product,
      device: product,
      region: product,
      retention: product,
    },
    trend: {
      source: trend,
      product: trend,
      campaign: trend,
      keyword: trend,
      time: trend,
      device: trend,
      region: trend,
      retention: trend,
    },
    heatmap: [],
    keywords: [],
  }
}
</script>

<style scoped>
.admin-analytics {
  padding: 28px;
  background: #f6f7fb;
  min-height: 100vh;
  color: #0f172a;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 18px;
}

.page-header h1 {
  font-size: 30px;
  font-weight: 800;
  margin: 6px 0;
}

.page-header .sub {
  color: #475569;
}

.eyebrow {
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #22b8cf;
  font-weight: 700;
}

.sync {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.08);
  font-weight: 700;
}

.sync .dot {
  width: 10px;
  height: 10px;
  border-radius: 999px;
}

.sync .ok {
  background: #10b981;
  box-shadow: 0 0 0 6px rgba(16, 185, 129, 0.15);
}

.sync .syncing {
  background: #f59e0b;
  animation: pulse 1.4s infinite;
}

.admin-tabs {
  display: flex;
  gap: 8px;
  align-items: center;
  padding: 10px;
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.05);
  margin-bottom: 12px;
  backdrop-filter: blur(8px);
}

.tab {
  appearance: none;
  border: 1px solid transparent;
  background: transparent;
  color: #334155;
  border-radius: 12px;
  padding: 10px 12px;
  font-weight: 800;
  cursor: pointer;
  text-decoration: none;
  line-height: 1;
}

.tab:hover {
  background: #f1f5f9;
}

.tab.active {
  background: linear-gradient(135deg, #2563eb, #0ea5e9);
  color: #fff;
}

.tab:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

@keyframes pulse {
  0% { box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.4); }
  70% { box-shadow: 0 0 0 8px rgba(245, 158, 11, 0); }
  100% { box-shadow: 0 0 0 0 rgba(245, 158, 11, 0); }
}

.section-nav {
  position: sticky;
  top: 12px;
  z-index: 5;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  padding: 10px;
  margin: 12px 0;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  background: rgba(246, 247, 251, 0.8);
  backdrop-filter: blur(8px);
}

.section-nav a {
  text-decoration: none;
  padding: 8px 10px;
  border-radius: 999px;
  border: 1px solid #e2e8f0;
  background: #fff;
  font-weight: 800;
  color: #334155;
  font-size: 13px;
}

.section-nav a:hover {
  border-color: #cbd5e1;
  background: #f8fafc;
}

.dashboard-section {
  margin-top: 18px;
}

.section-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.section-head h2 {
  margin: 6px 0 0 0;
  font-size: 22px;
  font-weight: 900;
  color: #0f172a;
}

.section-sub {
  margin: 6px 0 0 0;
  color: #64748b;
  font-weight: 700;
}

.filters {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
  align-items: end;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 16px;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.05);
  margin-bottom: 14px;
}

.filter {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.filter .label {
  font-size: 12px;
  color: #64748b;
  font-weight: 700;
}

.segmented {
  display: inline-flex;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  overflow: hidden;
}

.segmented button {
  padding: 10px 12px;
  border: none;
  background: #fff;
  font-weight: 700;
  color: #334155;
}

.segmented button.active {
  background: linear-gradient(135deg, #2563eb, #0ea5e9);
  color: #fff;
  border-color: transparent;
}

.date-range {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  gap: 8px;
  align-items: center;
}

.date-range .tilde {
  color: #94a3b8;
  font-weight: 700;
}

.filter select,
.filter input[type='date'] {
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 10px 12px;
  background: #fff;
}

.filter.wide {
  grid-column: span 2;
}

.actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

.actions .primary {
  background: #2563eb;
  color: #fff;
  border: none;
  border-radius: 10px;
  padding: 12px 14px;
  font-weight: 800;
}

.actions .ghost {
  border: 1px solid #e2e8f0;
  background: #fff;
  color: #334155;
  border-radius: 10px;
  padding: 12px 14px;
  font-weight: 700;
}

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 10px;
  margin: 14px 0;
}

.kpi-card {
  background: linear-gradient(135deg, #f8fafc, #eef2ff);
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  padding: 14px;
}

.kpi-card .label {
  font-size: 13px;
  color: #475569;
  font-weight: 700;
}

.value-row {
  display: flex;
  align-items: baseline;
  gap: 10px;
  margin: 4px 0;
}

.value-row .value {
  font-size: 22px;
  font-weight: 800;
}

.delta {
  font-weight: 800;
  font-size: 13px;
}

.delta.up {
  color: #0ca678;
}

.delta.down {
  color: #e03131;
}

.hint {
  color: #94a3b8;
  font-size: 12px;
}

.grid {
  display: grid;
  grid-template-columns: 1.2fr 1fr;
  gap: 12px;
  margin-bottom: 12px;
}

.card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 14px;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.05);
}

.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.card h3 {
  font-size: 18px;
  font-weight: 800;
  color: #0f172a;
}

.chart {
  width: 100%;
  height: 320px;
}

.alert-list,
.todo-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.alert-list li,
.todo-list li {
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 10px;
  align-items: center;
  padding: 10px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  background: #f8fafc;
}

.pill {
  padding: 6px 10px;
  border-radius: 999px;
  font-weight: 800;
  font-size: 12px;
  color: #fff;
}

.pill.high { background: #ef4444; }
.pill.medium { background: #f59e0b; }
.pill.low { background: #10b981; }

.alert-title {
  font-weight: 800;
  margin: 0;
  color: #0f172a;
}

.alert-desc {
  margin: 4px 0 0 0;
  color: #475569;
  font-size: 13px;
}

.alert-meta {
  color: #94a3b8;
  font-size: 12px;
}

.todo-list input[type='checkbox'] {
  width: 18px;
  height: 18px;
}

.todo-title {
  font-weight: 800;
  margin: 0;
}

.todo-desc {
  margin: 4px 0 0 0;
  color: #475569;
  font-size: 13px;
}

.todo-meta {
  color: #94a3b8;
  font-size: 12px;
}

.alert {
  padding: 12px 14px;
  border-radius: 12px;
  border: 1px solid #fecdd3;
  background: #fff1f2;
  color: #be123c;
  font-weight: 700;
}

@media (max-width: 1100px) {
  .grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .filters {
    grid-template-columns: 1fr;
  }

  .filter.wide {
    grid-column: span 1;
  }
}
</style>
