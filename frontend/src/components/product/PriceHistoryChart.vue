<template>
  <div :class="['price-history-chart', { compact }]">
    <!-- 헤더 -->
    <div class="chart-header">
      <div class="title-section">
        <TrendingDown class="icon" :size="compact ? 16 : 20" />
        <h3 class="title">가격 변동 추이</h3>
        <!-- 컴팩트 모드: 지금이 최저가 배지 -->
        <span v-if="compact && statistics?.is_lowest_ever" class="lowest-inline">
          <Flame :size="12" />
          최저가
        </span>
      </div>
      <!-- 기간 선택 -->
      <div class="period-selector">
        <button
          v-for="period in displayPeriods"
          :key="period.value"
          :class="['period-btn', { active: selectedDays === period.value }]"
          @click="selectedDays = period.value"
        >
          {{ period.label }}
        </button>
      </div>
    </div>

    <!-- 로딩 상태 -->
    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <span v-if="!compact">가격 정보를 불러오는 중...</span>
    </div>

    <!-- 데이터 없음 -->
    <div v-else-if="!hasHistory" class="empty-state">
      <Info :size="compact ? 18 : 24" class="empty-icon" />
      <p>가격 변동 이력이 없습니다</p>
    </div>

    <!-- 차트 영역 -->
    <div v-else class="chart-content">
      <!-- 컴팩트 모드: 간략 통계 + 미니 차트 -->
      <template v-if="compact">
        <div class="compact-stats">
          <div class="stat-item">
            <span class="stat-label">현재</span>
            <span class="stat-value">{{ formatPrice(statistics?.current_price || 0) }}</span>
          </div>
          <div class="stat-divider"></div>
          <div class="stat-item">
            <span class="stat-label">최저</span>
            <span class="stat-value lowest">{{ formatPrice(statistics?.min_price || 0) }}</span>
          </div>
          <div class="stat-divider"></div>
          <div class="stat-item">
            <span class="stat-label">평균</span>
            <span class="stat-value">{{ formatPrice(statistics?.avg_price || 0) }}</span>
          </div>
          <div v-if="statistics?.price_change_from_avg !== 0" class="stat-item change">
            <span
              :class="['change-badge', statistics?.price_change_from_avg! < 0 ? 'down' : 'up']"
            >
              {{ statistics?.price_change_from_avg! > 0 ? '+' : '' }}{{ statistics?.price_change_from_avg!.toFixed(1) }}%
            </span>
          </div>
        </div>

        <!-- 미니 차트 -->
        <div class="mini-chart-container" ref="miniChartContainer">
          <svg :width="miniChartWidth" :height="miniChartHeight" class="mini-chart">
            <defs>
              <linearGradient id="miniGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" stop-color="rgb(34, 197, 94)" stop-opacity="0.2" />
                <stop offset="100%" stop-color="rgb(34, 197, 94)" stop-opacity="0" />
              </linearGradient>
            </defs>
            <path :d="miniAreaPath" fill="url(#miniGradient)" />
            <path
              :d="miniLinePath"
              fill="none"
              stroke="rgb(34, 197, 94)"
              stroke-width="2"
              stroke-linejoin="round"
              stroke-linecap="round"
            />
            <!-- 미니 차트 데이터 포인트 (호버용) -->
            <g class="mini-data-points">
              <circle
                v-for="(point, idx) in miniChartPoints"
                :key="'mini-point-' + idx"
                :cx="point.x"
                :cy="point.y"
                :r="miniHoveredIndex === idx ? 5 : 3"
                :class="['mini-data-point', { hovered: miniHoveredIndex === idx }]"
                @mouseenter="miniHoveredIndex = idx"
                @mouseleave="miniHoveredIndex = null"
              />
            </g>
          </svg>
          <!-- 미니 차트 툴팁 -->
          <div
            v-if="miniHoveredIndex !== null && miniChartPoints[miniHoveredIndex]"
            class="mini-tooltip"
            :style="{
              left: miniChartPoints[miniHoveredIndex].x + 'px',
              top: (miniChartPoints[miniHoveredIndex].y - 40) + 'px'
            }"
          >
            <div class="mini-tooltip-date">{{ formatTooltipDate(history[miniHoveredIndex].recorded_at) }}</div>
            <div class="mini-tooltip-price">{{ formatPrice(history[miniHoveredIndex].price) }}</div>
          </div>
        </div>
      </template>

      <!-- 일반 모드: 전체 통계 + 큰 차트 -->
      <template v-else>
        <!-- 통계 카드 -->
        <div v-if="statistics" class="stats-cards">
          <div class="stat-card current">
            <span class="stat-label">현재가</span>
            <span class="stat-value">{{ formatPrice(statistics.current_price) }}</span>
            <span
              v-if="statistics.price_change_from_avg !== 0"
              :class="['stat-change', statistics.price_change_from_avg < 0 ? 'down' : 'up']"
            >
              {{ statistics.price_change_from_avg > 0 ? '+' : '' }}{{ statistics.price_change_from_avg.toFixed(1) }}%
              <span class="vs-avg">평균 대비</span>
            </span>
          </div>
          <div class="stat-card lowest">
            <span class="stat-label">최저가</span>
            <span class="stat-value">{{ formatPrice(statistics.min_price) }}</span>
            <span v-if="statistics.is_lowest_ever" class="lowest-badge">
              <Flame :size="12" />
              지금이 최저가!
            </span>
          </div>
          <div class="stat-card highest">
            <span class="stat-label">최고가</span>
            <span class="stat-value">{{ formatPrice(statistics.max_price) }}</span>
          </div>
          <div class="stat-card average">
            <span class="stat-label">평균가</span>
            <span class="stat-value">{{ formatPrice(statistics.avg_price) }}</span>
          </div>
        </div>

        <!-- SVG 차트 -->
        <div class="chart-container" ref="chartContainer">
          <svg
            :width="chartWidth"
            :height="chartHeight"
            class="price-chart"
          >
            <!-- 그리드 라인 -->
            <g class="grid-lines">
              <line
                v-for="(y, idx) in gridYPositions"
                :key="'grid-' + idx"
                :x1="padding.left"
                :y1="y"
                :x2="chartWidth - padding.right"
                :y2="y"
                class="grid-line"
              />
            </g>

            <!-- Y축 라벨 -->
            <g class="y-axis-labels">
              <text
                v-for="(label, idx) in yAxisLabels"
                :key="'y-label-' + idx"
                :x="padding.left - 8"
                :y="gridYPositions[idx] + 4"
                class="y-label"
              >
                {{ label }}
              </text>
            </g>

            <!-- 평균가 라인 -->
            <line
              v-if="statistics"
              :x1="padding.left"
              :y1="priceToY(statistics.avg_price)"
              :x2="chartWidth - padding.right"
              :y2="priceToY(statistics.avg_price)"
              class="avg-line"
              stroke-dasharray="5,5"
            />
            <text
              v-if="statistics"
              :x="chartWidth - padding.right + 4"
              :y="priceToY(statistics.avg_price) + 4"
              class="avg-label"
            >
              평균
            </text>

            <!-- 가격 영역 (그라데이션) -->
            <defs>
              <linearGradient id="priceGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" stop-color="rgb(34, 197, 94)" stop-opacity="0.3" />
                <stop offset="100%" stop-color="rgb(34, 197, 94)" stop-opacity="0" />
              </linearGradient>
            </defs>
            <path
              :d="areaPath"
              fill="url(#priceGradient)"
            />

            <!-- 가격 라인 -->
            <path
              :d="linePath"
              fill="none"
              stroke="rgb(34, 197, 94)"
              stroke-width="2.5"
              stroke-linejoin="round"
              stroke-linecap="round"
            />

            <!-- 데이터 포인트 -->
            <g class="data-points">
              <circle
                v-for="(point, idx) in chartPoints"
                :key="'point-' + idx"
                :cx="point.x"
                :cy="point.y"
                :r="hoveredIndex === idx ? 6 : 4"
                :class="['data-point', { hovered: hoveredIndex === idx }]"
                @mouseenter="hoveredIndex = idx"
                @mouseleave="hoveredIndex = null"
              />
            </g>

            <!-- X축 라벨 -->
            <g class="x-axis-labels">
              <text
                v-for="(label, idx) in xAxisLabels"
                :key="'x-label-' + idx"
                :x="label.x"
                :y="chartHeight - 8"
                class="x-label"
              >
                {{ label.text }}
              </text>
            </g>
          </svg>

          <!-- 툴팁 -->
          <div
            v-if="hoveredIndex !== null && chartPoints[hoveredIndex]"
            class="tooltip"
            :style="{
              left: chartPoints[hoveredIndex].x + 'px',
              top: (chartPoints[hoveredIndex].y - 50) + 'px'
            }"
          >
            <div class="tooltip-date">{{ formatTooltipDate(history[hoveredIndex].recorded_at) }}</div>
            <div class="tooltip-price">{{ formatPrice(history[hoveredIndex].price) }}</div>
            <div
              v-if="history[hoveredIndex].price_change_rate !== null"
              :class="['tooltip-change', history[hoveredIndex].price_change_rate! < 0 ? 'down' : 'up']"
            >
              {{ history[hoveredIndex].price_change_rate! > 0 ? '+' : '' }}{{ history[hoveredIndex].price_change_rate!.toFixed(1) }}%
            </div>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { TrendingDown, Info, Flame } from 'lucide-vue-next'
import { recommendationsAPI, type PriceHistoryPoint, type PriceStatistics } from '@/services/api'
import { formatPrice } from '@/utils/formatters'

// Props
const props = withDefaults(defineProps<{
  productId: number
  compact?: boolean
}>(), {
  compact: false
})

// 상태
const loading = ref(false)
const history = ref<PriceHistoryPoint[]>([])
const statistics = ref<PriceStatistics | null>(null)
const selectedDays = ref(30)
const hoveredIndex = ref<number | null>(null)
const miniHoveredIndex = ref<number | null>(null)
const chartContainer = ref<HTMLElement | null>(null)
const miniChartContainer = ref<HTMLElement | null>(null)

// 기간 옵션
const periods = [
  { label: '7일', value: 7 },
  { label: '30일', value: 30 },
  { label: '90일', value: 90 },
]

// 컴팩트 모드에서는 기간 옵션 축소
const displayPeriods = computed(() => {
  if (props.compact) {
    return [
      { label: '7일', value: 7 },
      { label: '30일', value: 30 },
    ]
  }
  return periods
})

// 차트 설정 (일반 모드)
const chartWidth = 600
const chartHeight = 280
const padding = { top: 20, right: 50, bottom: 30, left: 60 }

// 미니 차트 설정 (컴팩트 모드)
const miniChartWidth = computed(() => 320)
const miniChartHeight = computed(() => 60)
const miniPadding = { top: 5, right: 5, bottom: 5, left: 5 }

// 데이터 존재 여부
const hasHistory = computed(() => history.value.length > 0)

// 가격 범위 계산
const priceRange = computed(() => {
  if (!hasHistory.value) return { min: 0, max: 0 }
  const prices = history.value.map(p => p.price)
  const min = Math.min(...prices)
  const max = Math.max(...prices)
  const margin = (max - min) * 0.1 || max * 0.1
  return {
    min: Math.max(0, min - margin),
    max: max + margin
  }
})

// 가격을 Y 좌표로 변환 (일반 모드)
const priceToY = (price: number): number => {
  const { min, max } = priceRange.value
  if (max === min) return chartHeight / 2
  const ratio = (price - min) / (max - min)
  return chartHeight - padding.bottom - ratio * (chartHeight - padding.top - padding.bottom)
}

// 가격을 Y 좌표로 변환 (미니 차트)
const miniPriceToY = (price: number): number => {
  const { min, max } = priceRange.value
  if (max === min) return miniChartHeight.value / 2
  const ratio = (price - min) / (max - min)
  return miniChartHeight.value - miniPadding.bottom - ratio * (miniChartHeight.value - miniPadding.top - miniPadding.bottom)
}

// 인덱스를 X 좌표로 변환 (일반 모드)
const indexToX = (idx: number): number => {
  const count = history.value.length
  if (count <= 1) return (chartWidth - padding.left - padding.right) / 2 + padding.left
  const step = (chartWidth - padding.left - padding.right) / (count - 1)
  return padding.left + idx * step
}

// 인덱스를 X 좌표로 변환 (미니 차트)
const miniIndexToX = (idx: number): number => {
  const count = history.value.length
  if (count <= 1) return miniChartWidth.value / 2
  const step = (miniChartWidth.value - miniPadding.left - miniPadding.right) / (count - 1)
  return miniPadding.left + idx * step
}

// 차트 포인트 계산 (일반 모드)
const chartPoints = computed(() => {
  return history.value.map((point, idx) => ({
    x: indexToX(idx),
    y: priceToY(point.price)
  }))
})

// 라인 경로 생성 (일반 모드)
const linePath = computed(() => {
  if (chartPoints.value.length === 0) return ''
  return chartPoints.value
    .map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`)
    .join(' ')
})

// 영역 경로 생성 (일반 모드)
const areaPath = computed(() => {
  if (chartPoints.value.length === 0) return ''
  const points = chartPoints.value
  const baseline = chartHeight - padding.bottom
  let path = `M ${points[0].x} ${baseline}`
  points.forEach(p => {
    path += ` L ${p.x} ${p.y}`
  })
  path += ` L ${points[points.length - 1].x} ${baseline} Z`
  return path
})

// 미니 차트 라인 경로
const miniLinePath = computed(() => {
  if (history.value.length === 0) return ''
  return history.value
    .map((p, i) => `${i === 0 ? 'M' : 'L'} ${miniIndexToX(i)} ${miniPriceToY(p.price)}`)
    .join(' ')
})

// 미니 차트 영역 경로
const miniAreaPath = computed(() => {
  if (history.value.length === 0) return ''
  const baseline = miniChartHeight.value - miniPadding.bottom
  let path = `M ${miniIndexToX(0)} ${baseline}`
  history.value.forEach((p, i) => {
    path += ` L ${miniIndexToX(i)} ${miniPriceToY(p.price)}`
  })
  path += ` L ${miniIndexToX(history.value.length - 1)} ${baseline} Z`
  return path
})

// 미니 차트 포인트 계산
const miniChartPoints = computed(() => {
  return history.value.map((point, idx) => ({
    x: miniIndexToX(idx),
    y: miniPriceToY(point.price)
  }))
})

// Y축 그리드 위치
const gridYPositions = computed(() => {
  const count = 5
  const positions: number[] = []
  for (let i = 0; i < count; i++) {
    const y = padding.top + (i / (count - 1)) * (chartHeight - padding.top - padding.bottom)
    positions.push(y)
  }
  return positions
})

// Y축 라벨
const yAxisLabels = computed(() => {
  const { min, max } = priceRange.value
  const count = 5
  const labels: string[] = []
  for (let i = 0; i < count; i++) {
    const value = max - (i / (count - 1)) * (max - min)
    labels.push(formatCompactPrice(value))
  }
  return labels
})

// X축 라벨
const xAxisLabels = computed(() => {
  if (history.value.length === 0) return []
  const count = Math.min(5, history.value.length)
  const step = Math.max(1, Math.floor((history.value.length - 1) / (count - 1)))
  const labels: { x: number; text: string }[] = []

  for (let i = 0; i < history.value.length; i += step) {
    if (labels.length >= count) break
    const date = new Date(history.value[i].recorded_at)
    labels.push({
      x: indexToX(i),
      text: `${date.getMonth() + 1}/${date.getDate()}`
    })
  }
  return labels
})

// 가격 포맷 (간략화)
const formatCompactPrice = (price: number): string => {
  if (price >= 10000) {
    return `${(price / 10000).toFixed(1)}만`
  }
  return `${Math.round(price / 1000)}천`
}

// 툴팁 날짜 포맷
const formatTooltipDate = (dateStr: string): string => {
  const date = new Date(dateStr)
  return `${date.getMonth() + 1}월 ${date.getDate()}일`
}

// 데이터 로드
const loadHistory = async () => {
  loading.value = true
  try {
    const { data } = await recommendationsAPI.getPriceHistory(props.productId, selectedDays.value)
    history.value = data.history
    statistics.value = data.statistics
  } catch (e) {
    console.error('가격 히스토리 로드 실패:', e)
    history.value = []
    statistics.value = null
  } finally {
    loading.value = false
  }
}

// 기간 변경 시 재로드
watch(selectedDays, () => {
  loadHistory()
})

// 상품 ID 변경 시 재로드
watch(() => props.productId, () => {
  loadHistory()
})

onMounted(() => {
  loadHistory()
})
</script>

<style scoped>
.price-history-chart {
  background: white;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.06);
}

/* 컴팩트 모드 스타일 */
.price-history-chart.compact {
  padding: 14px;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  box-shadow: none;
}

.compact .chart-header {
  margin-bottom: 12px;
}

.compact .title {
  font-size: 14px;
}

.compact .period-btn {
  padding: 4px 8px;
  font-size: 11px;
}

.compact .loading-state,
.compact .empty-state {
  padding: 20px 0;
}

.compact .spinner {
  width: 20px;
  height: 20px;
  border-width: 2px;
}

/* 컴팩트 통계 */
.compact-stats {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  background: #f9fafb;
  border-radius: 8px;
  margin-bottom: 10px;
}

.compact-stats .stat-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.compact-stats .stat-label {
  font-size: 10px;
  color: #9ca3af;
  font-weight: 500;
}

.compact-stats .stat-value {
  font-size: 13px;
  font-weight: 700;
  color: #1a1a1a;
}

.compact-stats .stat-value.lowest {
  color: #22c55e;
}

.compact-stats .stat-divider {
  width: 1px;
  height: 24px;
  background: #e5e7eb;
}

.compact-stats .stat-item.change {
  margin-left: auto;
}

.change-badge {
  font-size: 11px;
  font-weight: 600;
  padding: 3px 6px;
  border-radius: 4px;
}

.change-badge.down {
  background: #dcfce7;
  color: #16a34a;
}

.change-badge.up {
  background: #fee2e2;
  color: #dc2626;
}

/* 미니 차트 */
.mini-chart-container {
  width: 100%;
  overflow: visible;
  position: relative;
}

.mini-chart {
  display: block;
  width: 100%;
  height: auto;
}

.mini-data-point {
  fill: white;
  stroke: #22c55e;
  stroke-width: 1.5;
  cursor: pointer;
  transition: all 0.15s;
}

.mini-data-point.hovered {
  fill: #22c55e;
  stroke-width: 2;
}

.mini-tooltip {
  position: absolute;
  transform: translateX(-50%);
  background: #1a1a1a;
  color: white;
  padding: 6px 10px;
  border-radius: 6px;
  font-size: 11px;
  white-space: nowrap;
  pointer-events: none;
  z-index: 10;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

.mini-tooltip::after {
  content: '';
  position: absolute;
  bottom: -4px;
  left: 50%;
  transform: translateX(-50%);
  border-width: 4px 4px 0;
  border-style: solid;
  border-color: #1a1a1a transparent transparent;
}

.mini-tooltip-date {
  color: #9ca3af;
  font-size: 10px;
  margin-bottom: 1px;
}

.mini-tooltip-price {
  font-weight: 700;
  font-size: 12px;
}

/* 헤더 최저가 인라인 배지 */
.lowest-inline {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 11px;
  font-weight: 600;
  color: #dc2626;
  background: #fee2e2;
  padding: 2px 6px;
  border-radius: 4px;
  animation: pulse 2s infinite;
}

/* 일반 모드 스타일 */
.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.title-section {
  display: flex;
  align-items: center;
  gap: 8px;
}

.title-section .icon {
  color: #22c55e;
}

.title {
  font-size: 18px;
  font-weight: 700;
  color: #1a1a1a;
  margin: 0;
}

.period-selector {
  display: flex;
  gap: 4px;
  background: #f3f4f6;
  padding: 4px;
  border-radius: 8px;
}

.period-btn {
  padding: 6px 12px;
  border: none;
  background: transparent;
  color: #6b7280;
  font-size: 13px;
  font-weight: 500;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.period-btn:hover {
  color: #374151;
}

.period-btn.active {
  background: white;
  color: #22c55e;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 60px 0;
  color: #9ca3af;
}

.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid #e5e7eb;
  border-top-color: #22c55e;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.empty-icon {
  color: #d1d5db;
}

.chart-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.compact .chart-content {
  gap: 0;
}

.stats-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.stat-card {
  background: #f9fafb;
  border-radius: 12px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-label {
  font-size: 12px;
  color: #6b7280;
  font-weight: 500;
}

.stat-value {
  font-size: 18px;
  font-weight: 700;
  color: #1a1a1a;
}

.stat-change {
  font-size: 12px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 4px;
}

.stat-change.down {
  color: #22c55e;
}

.stat-change.up {
  color: #ef4444;
}

.vs-avg {
  color: #9ca3af;
  font-weight: 400;
}

.stat-card.current {
  background: linear-gradient(135deg, #f0fdf4, #dcfce7);
  border: 1px solid #bbf7d0;
}

.stat-card.lowest {
  background: linear-gradient(135deg, #fef2f2, #fee2e2);
  border: 1px solid #fecaca;
}

.lowest-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  font-weight: 600;
  color: #dc2626;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

.chart-container {
  position: relative;
  overflow: visible;
}

.price-chart {
  display: block;
  width: 100%;
  height: auto;
}

.grid-line {
  stroke: #e5e7eb;
  stroke-width: 1;
}

.y-label,
.x-label {
  fill: #9ca3af;
  font-size: 11px;
  text-anchor: end;
}

.x-label {
  text-anchor: middle;
}

.avg-line {
  stroke: #f59e0b;
  stroke-width: 1.5;
}

.avg-label {
  fill: #f59e0b;
  font-size: 10px;
  font-weight: 500;
}

.data-point {
  fill: white;
  stroke: #22c55e;
  stroke-width: 2;
  cursor: pointer;
  transition: all 0.2s;
}

.data-point.hovered {
  fill: #22c55e;
  stroke-width: 3;
}

.tooltip {
  position: absolute;
  transform: translateX(-50%);
  background: #1a1a1a;
  color: white;
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 12px;
  white-space: nowrap;
  pointer-events: none;
  z-index: 10;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

.tooltip::after {
  content: '';
  position: absolute;
  bottom: -6px;
  left: 50%;
  transform: translateX(-50%);
  border-width: 6px 6px 0;
  border-style: solid;
  border-color: #1a1a1a transparent transparent;
}

.tooltip-date {
  color: #9ca3af;
  margin-bottom: 2px;
}

.tooltip-price {
  font-weight: 700;
  font-size: 14px;
}

.tooltip-change {
  font-size: 11px;
  font-weight: 600;
}

.tooltip-change.down {
  color: #4ade80;
}

.tooltip-change.up {
  color: #f87171;
}

@media (max-width: 768px) {
  .price-history-chart {
    padding: 16px;
  }

  .chart-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .stats-cards {
    grid-template-columns: repeat(2, 1fr);
  }

  .stat-value {
    font-size: 16px;
  }
}
</style>
