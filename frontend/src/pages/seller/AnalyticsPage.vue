<template>
  <div class="analytics-page">
    <header class="page-header">
      <div>
        <p class="eyebrow">판매자 · 분석</p>
        <h1>유입 · 전환 분석</h1>
        <p class="sub">채널 · 상품 · 시간대별로 주문/전환 흐름을 빠르게 파악하세요.</p>
      </div>
      <div class="badge">데이터 갱신: {{ lastUpdated }}</div>
    </header>

    <section class="control-panel">
      <div class="tab-strip">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          class="tab"
          :class="{ active: activeTab === tab.key }"
          @click="handleTabClick(tab.key)"
        >
          {{ tab.label }}
        </button>
      </div>

      <div class="filters">
        <div class="filter-group">
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

        <div class="filter-group grow">
          <span class="label">조회 기간</span>
          <div class="date-range">
            <input type="date" v-model="dateRange.start" />
            <span class="tilde">~</span>
            <input type="date" v-model="dateRange.end" />
          </div>
        </div>

        <div class="filter-group">
          <span class="label">디바이스</span>
          <select v-model="filters.device">
            <option value="all">전체</option>
            <option value="mobile">모바일</option>
            <option value="desktop">PC</option>
          </select>
        </div>

        <div class="filter-group">
          <span class="label">지역</span>
          <select v-model="filters.region">
            <option value="all">전국</option>
            <option value="metro">수도권</option>
            <option value="local">비수도권</option>
          </select>
        </div>

        <div class="actions">
          <button class="primary" @click="loadData">검색</button>
          <button class="ghost" @click="resetFilters">초기화</button>
        </div>
      </div>
    </section>

    <section class="kpi-grid">
      <article v-for="card in kpiCards" :key="card.label" class="kpi-card">
        <p class="label">{{ card.label }}</p>
        <div class="value-row">
          <span class="value">{{ formatNumber(card.value, card.unit) }}</span>
          <span :class="['delta', card.delta >= 0 ? 'up' : 'down']">
            {{ card.delta >= 0 ? '▲' : '▼' }} {{ Math.abs(card.delta).toFixed(1) }}%
          </span>
        </div>
        <p class="hint">전 기간 대비</p>
      </article>
    </section>

    <section ref="chartsSectionRef" class="chart-grid">
      <article class="card">
        <header>
          <div>
            <p class="eyebrow">추이</p>
            <h3>일·주·월 전환 흐름</h3>
          </div>
          <div class="legend">
            <span class="dot sessions"></span>세션
            <span class="dot orders"></span>주문
            <span class="dot conversion"></span>전환율
          </div>
        </header>
        <div ref="trendChartRef" class="chart"></div>
      </article>

      <article class="card">
        <header>
          <div>
            <p class="eyebrow">상위 {{ breakdownData.length }}개</p>
            <h3>{{ displayTabLabel }} 성과</h3>
          </div>
          <span class="hint">막대: 세션·주문, 선: 전환율</span>
        </header>
        <div ref="breakdownChartRef" class="chart"></div>
      </article>
    </section>

    <section class="table-grid">
      <article class="card">
        <header>
          <div>
            <p class="eyebrow">검색어</p>
            <h3>Top 검색어 전환</h3>
          </div>
        </header>
        <table>
          <thead>
            <tr>
              <th>검색어</th>
              <th>클릭</th>
              <th>전환율</th>
              <th>매출</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in keywords" :key="row.keyword">
              <td>{{ row.keyword }}</td>
              <td>{{ formatNumber(row.clicks) }}</td>
              <td>{{ row.conversion.toFixed(1) }}%</td>
              <td>{{ formatNumber(row.revenue, '원') }}</td>
            </tr>
          </tbody>
        </table>
      </article>

    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import * as echarts from 'echarts/core'
import { BarChart, LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, TitleComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { analyticsAPI } from '@/services/api/analytics'
import type {
  AnalyticsTab,
  AnalyticsOverview,
  ChannelBreakdown,
  TimeBucket,
  Granularity
} from '@/types/analytics'

echarts.use([
  BarChart,
  LineChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  TitleComponent,
  CanvasRenderer
])

const tabs = [
  { key: 'source', label: '유입경로별' },
  { key: 'product', label: '상품별' },
  { key: 'keyword', label: '검색어' },
  { key: 'time', label: '시간대별' },
  { key: 'device', label: '디바이스별' },
  { key: 'region', label: '지역별' },
  { key: 'retention', label: '신규/재방문' }
] as const

const activeTab = ref<AnalyticsTab>('source')
const granularityOptions: Granularity[] = ['daily', 'weekly', 'monthly']
const granularity = ref<Granularity>('daily')
const dateRange = ref({ start: getDateNDaysAgo(6), end: getDateNDaysAgo(0) })
const filters = ref({ device: 'all', region: 'all' })
const lastUpdated = computed(() => new Date().toLocaleString())

const overview = ref<AnalyticsOverview | null>(null)
const loading = ref(false)

const trendChartRef = ref<HTMLDivElement | null>(null)
const breakdownChartRef = ref<HTMLDivElement | null>(null)
const chartsSectionRef = ref<HTMLElement | null>(null)
const chartInstances: Record<string, echarts.ECharts | null> = {
  trend: null,
  breakdown: null
}

const mockOverview = buildMockOverview()

const activeTabLabel = computed(() => tabs.find(t => t.key === activeTab.value)?.label || '')
const displayTabLabel = computed(() => {
  const label = activeTabLabel.value
  // "별별"이 연속으로 있으면 "별" 하나로 변경 (예: "지역별별" -> "지역별")
  return label.replace(/별별+/g, '별')
})
const kpiCards = computed(() => overview.value?.kpis ?? mockOverview.kpis)
const breakdownData = computed(() => overview.value?.breakdown[activeTab.value] ?? mockOverview.breakdown[activeTab.value])
const trendData = computed(() => formatTrend(overview.value?.trend[activeTab.value] ?? mockOverview.trend[activeTab.value], granularity.value))
const keywords = computed(() => overview.value?.keywords ?? mockOverview.keywords)

const loadData = async () => {
  loading.value = true
  try {
    const { data } = await analyticsAPI.getOverview({
      tab: activeTab.value,
      start_date: dateRange.value.start,
      end_date: dateRange.value.end,
      granularity: granularity.value,
      device: filters.value.device,
      region: filters.value.region
    })
    overview.value = data
  } catch (err) {
    console.warn('analyticsAPI 실패, mock 데이터 사용', err)
    overview.value = mockOverview
  } finally {
    loading.value = false
    await nextTick()
    renderAllCharts()
  }
}

const handleTabClick = (tabKey: AnalyticsTab) => {
  activeTab.value = tabKey
  // 탭 변경 시 그래프만 업데이트 (데이터는 이미 로드되어 있음)
  nextTick(() => {
    renderAllCharts()
    // 그래프 섹션으로 스크롤
    if (chartsSectionRef.value) {
      chartsSectionRef.value.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  })
}

const resetFilters = () => {
  filters.value = { device: 'all', region: 'all' }
  dateRange.value = { start: getDateNDaysAgo(6), end: getDateNDaysAgo(0) }
  granularity.value = 'daily'
  loadData()
}

const unitLabel = (unit: Granularity) => (unit === 'daily' ? '일간' : unit === 'weekly' ? '주간' : '월간')

const formatNumber = (value: number, unit?: string) => {
  const formatted = value.toLocaleString('ko-KR')
  return unit ? `${formatted}${unit}` : formatted
}

const renderAllCharts = () => {
  renderTrendChart()
  renderBreakdownChart()
}

const getChart = (key: 'trend' | 'breakdown', el: HTMLDivElement | null) => {
  if (!el) return null
  if (!chartInstances[key]) {
    chartInstances[key] = echarts.init(el)
  }
  return chartInstances[key]
}

const renderTrendChart = () => {
  const chart = getChart('trend', trendChartRef.value)
  if (!chart) return
  const data = trendData.value
  chart.setOption({
    grid: { top: 32, left: 40, right: 36, bottom: 40 },
    tooltip: { trigger: 'axis' },
    legend: { data: ['세션', '주문', '전환율'], top: 0 },
    xAxis: { type: 'category', data: data.map(d => d.date) },
    yAxis: [
      { type: 'value', name: '세션/주문' },
      { type: 'value', name: '전환율(%)', position: 'right', min: 0, max: 20 }
    ],
    series: [
      { name: '세션', type: 'bar', data: data.map(d => d.sessions), itemStyle: { color: '#7bc67e' }, barWidth: 14 },
      { name: '주문', type: 'bar', data: data.map(d => d.orders), itemStyle: { color: '#2f9e44' }, barWidth: 14, barGap: '30%' },
      { name: '전환율', type: 'line', yAxisIndex: 1, data: data.map(d => d.conversion), smooth: true, lineStyle: { width: 3, color: '#3b5bdb' }, symbolSize: 8 }
    ]
  })
}

const renderBreakdownChart = () => {
  const chart = getChart('breakdown', breakdownChartRef.value)
  if (!chart) return
  const data = breakdownData.value
  chart.setOption({
    grid: { top: 32, left: 40, right: 36, bottom: 52 },
    tooltip: { trigger: 'axis' },
    legend: { data: ['세션', '주문', '전환율'], top: 0 },
    xAxis: { type: 'category', data: data.map(d => d.name), axisLabel: { rotate: 20 } },
    yAxis: [
      { type: 'value', name: '세션/주문' },
      { type: 'value', name: '전환율(%)', position: 'right', min: 0, max: 25 }
    ],
    series: [
      { name: '세션', type: 'bar', data: data.map(d => d.sessions), itemStyle: { color: '#66d9e8' }, barWidth: 12 },
      { name: '주문', type: 'bar', data: data.map(d => d.orders), itemStyle: { color: '#22b8cf' }, barWidth: 12, barGap: '20%' },
      { name: '전환율', type: 'line', yAxisIndex: 1, data: data.map(d => d.conversion), smooth: true, lineStyle: { width: 3, color: '#f59f00' }, symbolSize: 8 }
    ]
  })
}

const handleResize = () => {
  Object.values(chartInstances).forEach(c => c?.resize())
}

watch(granularity, () => {
  nextTick(() => {
    renderAllCharts()
  })
})
watch(
  () => [dateRange.value.start, dateRange.value.end, filters.value],
  () => {},
  { deep: true }
)

onMounted(() => {
  loadData()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  Object.values(chartInstances).forEach(c => c?.dispose())
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
    const conversion = sessions ? (orders / sessions) * 100 : 0
    buckets.push({
      date: unit === 'weekly' ? `${Math.floor(i / 7) + 1}주차` : `${Math.floor(i / 30) + 1}개월차`,
      sessions,
      orders,
      conversion
    })
  }
  return buckets
}


function buildMockOverview(): AnalyticsOverview {
  const baseTrend: TimeBucket[] = [
    { date: '02-01', sessions: 620, orders: 48, conversion: 7.7 },
    { date: '02-02', sessions: 580, orders: 44, conversion: 7.6 },
    { date: '02-03', sessions: 640, orders: 50, conversion: 7.8 },
    { date: '02-04', sessions: 700, orders: 54, conversion: 7.7 },
    { date: '02-05', sessions: 720, orders: 58, conversion: 8.0 },
    { date: '02-06', sessions: 680, orders: 55, conversion: 8.1 },
    { date: '02-07', sessions: 710, orders: 60, conversion: 8.5 },
    { date: '02-08', sessions: 690, orders: 52, conversion: 7.5 },
    { date: '02-09', sessions: 650, orders: 50, conversion: 7.7 },
    { date: '02-10', sessions: 630, orders: 49, conversion: 7.8 },
    { date: '02-11', sessions: 610, orders: 47, conversion: 7.7 },
    { date: '02-12', sessions: 700, orders: 56, conversion: 8.0 },
    { date: '02-13', sessions: 740, orders: 60, conversion: 8.1 },
    { date: '02-14', sessions: 760, orders: 65, conversion: 8.6 }
  ]

  const channelBreakdown: ChannelBreakdown[] = [
    { name: '검색/SEO', sessions: 3200, orders: 260, revenue: 12500000, conversion: 8.1 },
    { name: '광고/퍼포먼스', sessions: 2800, orders: 210, revenue: 9800000, conversion: 7.5 },
    { name: 'SNS/콘텐츠', sessions: 2100, orders: 150, revenue: 7300000, conversion: 7.1 },
    { name: '직접/북마크', sessions: 1600, orders: 140, revenue: 6400000, conversion: 8.8 },
    { name: '제휴/파트너', sessions: 900, orders: 70, revenue: 3100000, conversion: 7.8 }
  ]

  const productBreakdown: ChannelBreakdown[] = [
    { name: '베스트: 제주 하귤', sessions: 1400, orders: 180, revenue: 8200000, conversion: 12.8 },
    { name: '신규: 제주 레몬', sessions: 900, orders: 96, revenue: 5100000, conversion: 10.7 },
    { name: '정기: 감귤 구독', sessions: 760, orders: 82, revenue: 6200000, conversion: 10.8 },
    { name: '기획전: 선물세트', sessions: 620, orders: 58, revenue: 4700000, conversion: 9.4 },
    { name: '번들: 잼 세트', sessions: 540, orders: 45, revenue: 2300000, conversion: 8.3 }
  ]

  const keywordBreakdown: ChannelBreakdown[] = [
    { name: '제주 감귤', sessions: 800, orders: 76, revenue: 4200000, conversion: 9.5 },
    { name: '제주 레몬', sessions: 620, orders: 58, revenue: 3300000, conversion: 9.4 },
    { name: '감귤 선물세트', sessions: 540, orders: 52, revenue: 2900000, conversion: 9.6 },
    { name: '감귤 구독', sessions: 420, orders: 46, revenue: 3100000, conversion: 11.0 },
    { name: '친환경 과일', sessions: 380, orders: 30, revenue: 1800000, conversion: 7.9 }
  ]

  const regionBreakdown: ChannelBreakdown[] = [
    { name: '수도권', sessions: 3100, orders: 260, revenue: 12800000, conversion: 8.4 },
    { name: '충청권', sessions: 1100, orders: 82, revenue: 4200000, conversion: 7.5 },
    { name: '호남권', sessions: 900, orders: 74, revenue: 3500000, conversion: 8.2 },
    { name: '영남권', sessions: 1500, orders: 120, revenue: 6100000, conversion: 8.0 },
    { name: '제주', sessions: 500, orders: 52, revenue: 2800000, conversion: 10.4 }
  ]

  const retentionBreakdown: ChannelBreakdown[] = [
    { name: '신규', sessions: 2600, orders: 180, revenue: 8200000, conversion: 6.9 },
    { name: '재방문 1회', sessions: 1800, orders: 190, revenue: 10200000, conversion: 10.6 },
    { name: '재방문 2회+', sessions: 1300, orders: 160, revenue: 9400000, conversion: 12.3 }
  ]

  const keywords: { keyword: string; clicks: number; conversion: number; revenue: number }[] = [
    { keyword: '제주 감귤', clicks: 340, conversion: 7.8, revenue: 4300000 },
    { keyword: '감귤 선물세트', clicks: 280, conversion: 9.1, revenue: 3900000 },
    { keyword: '제주 레몬', clicks: 210, conversion: 6.4, revenue: 2200000 },
    { keyword: '감귤 구독', clicks: 190, conversion: 10.2, revenue: 3100000 },
    { keyword: '친환경 과일', clicks: 150, conversion: 5.9, revenue: 1400000 }
  ]

  return {
    kpis: [
      { label: '세션수', value: 7700, delta: 6.8 },
      { label: '주문수', value: 620, delta: 4.2 },
      { label: '전환율', value: 8.1, delta: 0.7, unit: '%' },
      { label: '매출', value: 27900000, delta: 5.5, unit: '원' },
      { label: '객단가', value: 45000, delta: 1.8, unit: '원' },
      { label: '재방문율', value: 38, delta: 2.1, unit: '%' }
    ],
    breakdown: {
      source: channelBreakdown,
      product: productBreakdown,
      keyword: keywordBreakdown,
      time: channelBreakdown,
      device: channelBreakdown,
      region: regionBreakdown,
      retention: retentionBreakdown
    },
    trend: {
      source: baseTrend,
      product: baseTrend,
      keyword: baseTrend,
      time: baseTrend,
      device: baseTrend,
      region: baseTrend,
      retention: baseTrend
    },
    heatmap: [],
    keywords
  }
}
</script>

<style scoped>
.analytics-page {
  padding: 32px;
  background: #f5f7fb;
  min-height: 100vh;
  color: #0f172a;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
  gap: 12px;
}
.page-header h1 {
  font-size: 32px;
  font-weight: 800;
  margin: 4px 0;
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
.badge {
  background: #e6fcf5;
  color: #0b7285;
  padding: 8px 12px;
  border-radius: 12px;
  font-size: 13px;
  font-weight: 600;
}
.control-panel {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 16px;
  margin-bottom: 16px;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.05);
}
.tab-strip {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 8px;
  margin-bottom: 14px;
}
.tab {
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 10px 12px;
  background: #f8fafc;
  font-weight: 700;
  color: #334155;
}
.tab.active {
  background: linear-gradient(135deg, #12b886, #099268);
  color: #fff;
  border-color: transparent;
  box-shadow: 0 8px 20px rgba(9, 146, 104, 0.25);
}
.filters {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 12px;
  align-items: flex-end;
}
.filter-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.filter-group .label {
  font-size: 12px;
  color: #64748b;
  font-weight: 700;
}
.filter-group select,
.filter-group input[type='date'] {
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 10px 12px;
  background: #fff;
}
.filter-group.grow {
  grid-column: span 2;
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
  background: #0ca678;
  color: #fff;
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
.actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}
.actions .primary {
  background: #0ca678;
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
  background: linear-gradient(135deg, #f8fafc, #f1f5f9);
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
.chart-grid {
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
.card header {
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
.legend {
  display: flex;
  gap: 12px;
  align-items: center;
  color: #475569;
  font-size: 13px;
}
.legend .dot {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  display: inline-block;
}
.dot.sessions {
  background: #66d9e8;
}
.dot.orders {
  background: #22b8cf;
}
.dot.conversion {
  background: #f59f00;
}
.chart {
  width: 100%;
  height: 320px;
}
.chart.tall {
  height: 360px;
}
.table-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
table {
  width: 100%;
  border-collapse: collapse;
}
th,
td {
  padding: 10px;
  border-bottom: 1px solid #e2e8f0;
  text-align: left;
}
th {
  color: #475569;
  font-size: 13px;
}
@media (max-width: 1100px) {
  .chart-grid,
  .table-grid {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 768px) {
  .filters {
    grid-template-columns: 1fr;
  }
  .filter-group.grow {
    grid-column: span 1;
  }
}
</style>
