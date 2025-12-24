<template>
  <div class="admin-analytics">
    <header class="page-header">
      <div>
        <p class="eyebrow">전체 관리자</p>
        <h1>통합 지표 · 리스크 모니터링</h1>
        <p class="sub">
          회원, 주문, 매출, 리스크 이벤트를 한 곳에서 관제합니다.
        </p>
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
        <span class="label">유저 구분</span>
        <select v-model="segment">
          <option value="all">전체</option>
          <option value="consumer">일반회원</option>
          <option value="seller">판매자</option>
        </select>
      </div>
      <div class="filter">
        <span class="label">데이터 범위</span>
        <select v-model="dataMode">
          <option value="all">테스트 데이터 + 실데이터</option>
          <option value="real">실데이터만</option>
        </select>
      </div>
      <div class="actions">
        <button class="primary" :disabled="loading" @click="loadData">
          조회
        </button>
        <button class="ghost" :disabled="loading" @click="resetFilters">
          초기화
        </button>
      </div>
    </section>

    <section v-if="errorMessage" class="alert error">
      {{ errorMessage }}
    </section>

    <section id="topline" class="dashboard-section">
      <header class="section-head">
        <div>
          <p class="eyebrow">Top Line Dashboard</p>
          <h2>비즈니스 성과 지표</h2>
          <p class="section-sub">CEO/PM이 가장 먼저 보는 핵심 KPI</p>
        </div>
        <p class="section-meta">
          집계: {{ appliedFilters.start }} ~ {{ appliedFilters.end }} ·
          {{ appliedSegmentLabel }}
        </p>
      </header>

      <div class="kpi-grid">
        <article
          v-for="card in topLineKpiCards"
          :key="card.key"
          class="kpi-card"
        >
          <p class="label">{{ card.label }}</p>
          <div class="value-row">
            <span class="value">{{
              formatNumber(card.value, card.unit, card.decimals)
            }}</span>
            <span :class="['delta', card.delta >= 0 ? 'up' : 'down']">
              {{ card.delta >= 0 ? "▲" : "▼" }}
              {{ Math.abs(card.delta).toFixed(1) }}%
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

    <section class="dashboard-section">
      <header class="section-head">
        <div>
          <p class="eyebrow">Risk & Actions</p>
          <h2>리스크 알림 · 운영 To-do</h2>
          <p class="section-sub">
            주요 지표의 이상 징후와 권장 후속 액션을 한눈에 확인합니다.
          </p>
        </div>
      </header>

      <div class="grid">
        <article class="card">
          <header class="card-head">
            <div>
              <p class="eyebrow">Alert</p>
              <h3>리스크 알림</h3>
            </div>
          </header>

          <ul v-if="riskAlerts.length" class="alert-list">
            <li v-for="alert in riskAlerts" :key="alert.id">
              <span class="pill" :class="alert.level">
                {{
                  alert.level === "high"
                    ? "High"
                    : alert.level === "medium"
                    ? "Medium"
                    : "Low"
                }}
              </span>
              <div>
                <p class="alert-title">{{ alert.title }}</p>
                <p class="alert-desc">{{ alert.description }}</p>
                <p class="alert-meta">{{ alert.meta }}</p>
              </div>
              <span class="alert-meta">{{ alert.metric }}</span>
            </li>
          </ul>
          <p v-else class="hint">
            현재 설정된 임계값을 초과한 리스크가 없습니다.
          </p>
        </article>

        <article class="card">
          <header class="card-head">
            <div>
              <p class="eyebrow">Action</p>
              <h3>운영 To-do</h3>
            </div>
          </header>

          <ul v-if="actionTodos.length" class="todo-list">
            <li v-for="todo in actionTodos" :key="todo.id">
              <input type="checkbox" :checked="todo.done" disabled />
              <div>
                <p class="todo-title">{{ todo.title }}</p>
                <p class="todo-desc">{{ todo.description }}</p>
                <p class="todo-meta">{{ todo.meta }}</p>
              </div>
            </li>
          </ul>
          <p v-else class="hint">
            처리해야 할 우선순위 To-do가 없습니다.
          </p>
        </article>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from "vue";
import * as echarts from "echarts/core";
import { BarChart, LineChart } from "echarts/charts";
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  TitleComponent,
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import { adminAnalyticsAPI } from "@/services/api/analytics";
import type {
  AnalyticsOverview,
  Granularity,
  TimeBucket,
  ChannelBreakdown,
  OpsOverview,
  OpsAlert,
  OpsTodo,
} from "@/types/analytics";

echarts.use([
  BarChart,
  LineChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  TitleComponent,
  CanvasRenderer,
]);

const granularityOptions: Granularity[] = [
  "daily",
  "weekly",
  "monthly",
  "yearly",
];
const granularity = ref<Granularity>("daily");
const appliedGranularity = ref<Granularity>("daily");
const dateRange = ref({ start: getDateNDaysAgo(13), end: getDateNDaysAgo(0) });
const segment = ref("all");
const dataMode = ref<"all" | "real">("all");

const appliedFilters = ref({
  start: dateRange.value.start,
  end: dateRange.value.end,
  segment: segment.value,
});

const overview = ref<AnalyticsOverview | null>(null);
const opsOverview = ref<OpsOverview | null>(null);
const loading = ref(false);
const errorMessage = ref<string | null>(null);
const lastUpdated = ref(new Date().toLocaleString());

const trendChartRef = ref<HTMLDivElement | null>(null);
const breakdownChartRef = ref<HTMLDivElement | null>(null);
const charts: Record<"trend" | "breakdown", echarts.ECharts | null> = {
  trend: null,
  breakdown: null,
};

const mockOverview = buildMockOverview();

const trendData = computed(() =>
  formatTrend(
    overview.value?.trend.source ?? mockOverview.trend.source,
    appliedGranularity.value
  )
);
const breakdownData = computed(
  () => overview.value?.breakdown.product ?? mockOverview.breakdown.product
);

type DashboardKpiCard = {
  key: string;
  label: string;
  value: number;
  unit?: string;
  decimals?: number;
  delta: number;
};

type RiskLevel = "high" | "medium" | "low";

type RiskAlert = {
  id: string;
  level: RiskLevel;
  title: string;
  description: string;
  metric: string;
  meta: string;
};

type TodoItem = {
  id: string;
  title: string;
  description: string;
  meta: string;
  done: boolean;
};

const segmentLabel = (value: string) => {
  if (value === "consumer") return "일반회원";
  if (value === "seller") return "판매자";
  return "전체";
};

const appliedSegmentLabel = computed(() =>
  segmentLabel(appliedFilters.value.segment)
);

const loadData = async () => {
  if (!dateRange.value.start || !dateRange.value.end) {
    errorMessage.value = "조회 기간을 선택해주세요.";
    return;
  }

  loading.value = true;
  errorMessage.value = null;
  appliedFilters.value = {
    start: dateRange.value.start,
    end: dateRange.value.end,
    segment: segment.value,
  };

  try {
    const [overviewResp, opsResp] = await Promise.all([
      adminAnalyticsAPI.getOverview({
        start_date: dateRange.value.start,
        end_date: dateRange.value.end,
        granularity: granularity.value,
        segment: segment.value,
        data_mode: dataMode.value,
      }),
      adminAnalyticsAPI.getOpsOverview({
        start_date: dateRange.value.start,
        end_date: dateRange.value.end,
        system: "all",
      }),
    ]);
    overview.value = overviewResp.data;
    opsOverview.value = opsResp.data;
    appliedGranularity.value = granularity.value;
  } catch (err: any) {
    console.warn("adminAnalyticsAPI 실패, mock 데이터 사용", err);
    overview.value = mockOverview;
    opsOverview.value = null;
    errorMessage.value =
      err?.response?.data?.detail ||
      "실시간 데이터를 불러오지 못해 샘플 데이터를 표시합니다.";
  } finally {
    loading.value = false;
    await nextTick();
    renderCharts();
    lastUpdated.value = new Date().toLocaleString();
  }
};

const resetFilters = () => {
  granularity.value = "daily";
  appliedGranularity.value = "daily";
  dateRange.value = { start: getDateNDaysAgo(13), end: getDateNDaysAgo(0) };
  segment.value = "all";
   dataMode.value = "all";
  loadData();
};

const unitLabel = (unit: Granularity) =>
  unit === "daily"
    ? "일간"
    : unit === "weekly"
    ? "주간"
    : unit === "monthly"
    ? "월간"
    : "연간";

const formatNumber = (value: number, unit?: string, decimals?: number) => {
  const resolvedDecimals = decimals ?? (unit === "%" ? 1 : 0);
  const formatted = value.toLocaleString("ko-KR", {
    minimumFractionDigits: resolvedDecimals,
    maximumFractionDigits: resolvedDecimals,
  });
  return unit ? `${formatted}${unit}` : formatted;
};

function percentChange(current: number, previous: number) {
  if (!Number.isFinite(current) || !Number.isFinite(previous)) return 0;
  if (previous === 0) return 0;
  return ((current - previous) / previous) * 100;
}

function periodDelta(
  data: TimeBucket[],
  calc: (slice: TimeBucket[]) => number
) {
  if (data.length < 2) return 0;
  const mid = Math.max(1, Math.floor(data.length / 2));
  const prev = calc(data.slice(0, mid));
  const curr = calc(data.slice(mid));
  return percentChange(curr, prev);
}

const toplineSummary = computed(() => {
  const data = trendData.value;
  const sessions = data.reduce((s, v) => s + v.sessions, 0);
  const orders = data.reduce((s, v) => s + v.orders, 0);
  const revenue = data.reduce((s, v) => s + (v.revenue ?? 0), 0);
  const conversion = sessions ? (orders / sessions) * 100 : 0;
  const aov = orders ? revenue / orders : 0;
  return { sessions, orders, revenue, conversion, aov };
});

const topLineKpiCards = computed<DashboardKpiCard[]>(() => {
  const data = trendData.value;
  const sumRevenue = (slice: TimeBucket[]) =>
    slice.reduce((s, v) => s + (v.revenue ?? 0), 0);
  const sumOrders = (slice: TimeBucket[]) =>
    slice.reduce((s, v) => s + v.orders, 0);
  const sumSessions = (slice: TimeBucket[]) =>
    slice.reduce((s, v) => s + v.sessions, 0);
  const conversionRate = (slice: TimeBucket[]) => {
    const sessions = sumSessions(slice);
    const orders = sumOrders(slice);
    return sessions ? (orders / sessions) * 100 : 0;
  };
  const aovValue = (slice: TimeBucket[]) => {
    const orders = sumOrders(slice);
    const revenue = sumRevenue(slice);
    return orders ? revenue / orders : 0;
  };

  const toplineKpis = overview.value?.kpis ?? [];
  const findKpi = (prefix: string) =>
    toplineKpis.find((k) => k.label.startsWith(prefix));

  const cartConvKpi = findKpi("장바구니→구매 전환율");

  const repeatPurchaseRate = 38.7;

  return [
    {
      key: "gmv",
      label: "GMV",
      value: toplineSummary.value.revenue,
      unit: "원",
      decimals: 0,
      delta: periodDelta(data, sumRevenue),
    },
    {
      key: "orders",
      label: "주문 수",
      value: toplineSummary.value.orders,
      decimals: 0,
      delta: periodDelta(data, sumOrders),
    },
    {
      key: "aov",
      label: "객단가 (AOV)",
      value: toplineSummary.value.aov,
      unit: "원",
      decimals: 0,
      delta: periodDelta(data, aovValue),
    },
    {
      key: "conversion",
      label: "전환율",
      value: toplineSummary.value.conversion,
      unit: "%",
      decimals: 1,
      delta: periodDelta(data, conversionRate),
    },
    {
      key: "repeat",
      label: "재구매율 (30D)",
      value: repeatPurchaseRate,
      unit: "%",
      decimals: 1,
      delta: 1.2,
    },
    {
      key: "cart_conversion",
      label: cartConvKpi?.label ?? "장바구니→구매 전환율",
      value: cartConvKpi?.value ?? 0,
      unit: cartConvKpi?.unit ?? "%",
      decimals: 1,
      delta: cartConvKpi?.delta ?? 0,
    },
  ];
});

const opsAlerts = computed<OpsAlert[]>(() => opsOverview.value?.alerts ?? []);
const opsTodos = computed<OpsTodo[]>(() => opsOverview.value?.todos ?? []);

const topRiskAlert = computed<OpsAlert | null>(() => {
  const alerts = opsAlerts.value;
  if (!alerts.length) return null;
  const order: Record<string, number> = { high: 0, medium: 1, low: 2 };
  return [...alerts].sort(
    (a, b) => (order[a.severity as string] ?? 3) - (order[b.severity as string] ?? 3)
  )[0];
});

const riskAlerts = computed<RiskAlert[]>(() => {
  const alert = topRiskAlert.value;
  if (!alert) return [];

  return [
    {
      id: alert.id,
      level: (alert.severity as RiskLevel) ?? "low",
      title: alert.title,
      description: alert.description,
      metric: alert.metric,
      meta: `집계: ${appliedFilters.value.start} ~ ${appliedFilters.value.end}`,
    },
  ];
});

const actionTodos = computed<TodoItem[]>(() => {
  const alert = topRiskAlert.value;
  const todos: TodoItem[] = [];
  const sourceTodos = opsTodos.value;

  if (alert) {
    const related =
      sourceTodos.find((t) => t.related_alert_id === alert.id) ?? sourceTodos[0];
    if (related) {
      todos.push({
        id: related.id,
        title: related.title,
        description: related.description,
        meta: related.meta,
        done: false,
      });
      return todos;
    }
  }

  if (sourceTodos.length) {
    const t = sourceTodos[0];
    todos.push({
      id: t.id,
      title: t.title,
      description: t.description,
      meta: t.meta,
      done: false,
    });
  }

  return todos;
});

const getChart = (key: "trend" | "breakdown", el: HTMLDivElement | null) => {
  if (!el) return null;
  if (!charts[key]) {
    charts[key] = echarts.init(el);
  }
  return charts[key];
};

const renderTrendChart = () => {
  const chart = getChart("trend", trendChartRef.value);
  if (!chart) return;
  const data = trendData.value;
  chart.setOption({
    grid: { top: 40, left: 56, right: 40, bottom: 72 },
    tooltip: { trigger: "axis" },
    legend: { data: ["매출", "주문", "전환율"], bottom: 8 },
    xAxis: { type: "category", data: data.map((d) => d.date) },
    yAxis: [
      { type: "value", name: "매출(원) / 주문" },
      { type: "value", name: "전환율(%)", position: "right", min: 0, max: 20 },
    ],
    series: [
      {
        name: "매출",
        type: "line",
        data: data.map((d) => d.revenue ?? 0),
        smooth: true,
        lineStyle: { width: 3, color: "#0ea5e9" },
        areaStyle: { color: "rgba(14,165,233,0.12)" },
      },
      {
        name: "주문",
        type: "bar",
        data: data.map((d) => d.orders),
        itemStyle: { color: "#4c1d95" },
        barWidth: 12,
      },
      {
        name: "전환율",
        type: "line",
        yAxisIndex: 1,
        data: data.map((d) => d.conversion),
        smooth: true,
        lineStyle: { width: 2.5, color: "#f97316" },
        symbolSize: 7,
      },
    ],
  });
};

const renderBreakdownChart = () => {
  const chart = getChart("breakdown", breakdownChartRef.value);
  if (!chart) return;
  const data = breakdownData.value;
  chart.setOption({
    grid: { top: 40, left: 56, right: 40, bottom: 92 },
    tooltip: { trigger: "axis" },
    legend: { data: ["매출", "주문", "전환율"], bottom: 8 },
    xAxis: {
      type: "category",
      data: data.map((d) => d.name),
      axisLabel: { rotate: 18 },
    },
    yAxis: [
      { type: "value", name: "매출/주문" },
      { type: "value", name: "전환율(%)", position: "right", min: 0, max: 25 },
    ],
    series: [
      {
        name: "매출",
        type: "bar",
        data: data.map((d) => d.revenue),
        itemStyle: { color: "#22c55e" },
        barWidth: 12,
      },
      {
        name: "주문",
        type: "bar",
        data: data.map((d) => d.orders),
        itemStyle: { color: "#a855f7" },
        barWidth: 12,
        barGap: "25%",
      },
      {
        name: "전환율",
        type: "line",
        yAxisIndex: 1,
        data: data.map((d) => d.conversion),
        smooth: true,
        lineStyle: { width: 2.5, color: "#f59e0b" },
        symbolSize: 7,
      },
    ],
  });
};

const renderCharts = () => {
  renderTrendChart();
  renderBreakdownChart();
};

const handleResize = () => {
  Object.values(charts).forEach((c) => c?.resize());
};

onMounted(() => {
  loadData();
  window.addEventListener("resize", handleResize);
});

onBeforeUnmount(() => {
  window.removeEventListener("resize", handleResize);
  Object.values(charts).forEach((c) => c?.dispose());
});

function getDateNDaysAgo(n: number) {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return d.toISOString().slice(0, 10);
}

function formatTrend(data: TimeBucket[], unit: Granularity): TimeBucket[] {
  if (unit === "daily") return data;
  const bucketSize = unit === "weekly" ? 7 : unit === "monthly" ? 30 : 365;
  const buckets: TimeBucket[] = [];
  for (let i = 0; i < data.length; i += bucketSize) {
    const slice = data.slice(i, i + bucketSize);
    if (!slice.length) continue;
    const sessions = slice.reduce((s, v) => s + v.sessions, 0);
    const orders = slice.reduce((s, v) => s + v.orders, 0);
    const revenue = slice.reduce((s, v) => s + (v.revenue ?? 0), 0);
    const conversion = sessions ? (orders / sessions) * 100 : 0;
    buckets.push({
      date:
        unit === "weekly"
          ? `${Math.floor(i / 7) + 1}주차`
          : unit === "monthly"
          ? `${Math.floor(i / 30) + 1}개월차`
          : `${Math.floor(i / 365) + 1}년차`,
      sessions,
      orders,
      conversion,
      revenue,
    });
  }
  return buckets;
}

function buildMockOverview(): AnalyticsOverview {
  const trend: TimeBucket[] = [
    {
      date: "03-01",
      sessions: 920,
      orders: 140,
      revenue: 18000000,
      conversion: 15.2,
    },
    {
      date: "03-02",
      sessions: 880,
      orders: 128,
      revenue: 17200000,
      conversion: 14.5,
    },
    {
      date: "03-03",
      sessions: 960,
      orders: 152,
      revenue: 18600000,
      conversion: 15.8,
    },
    {
      date: "03-04",
      sessions: 1010,
      orders: 160,
      revenue: 19200000,
      conversion: 15.8,
    },
    {
      date: "03-05",
      sessions: 980,
      orders: 155,
      revenue: 18800000,
      conversion: 15.8,
    },
    {
      date: "03-06",
      sessions: 940,
      orders: 150,
      revenue: 18300000,
      conversion: 16.0,
    },
    {
      date: "03-07",
      sessions: 990,
      orders: 162,
      revenue: 19700000,
      conversion: 16.4,
    },
    {
      date: "03-08",
      sessions: 970,
      orders: 154,
      revenue: 18900000,
      conversion: 15.9,
    },
    {
      date: "03-09",
      sessions: 950,
      orders: 150,
      revenue: 18400000,
      conversion: 15.8,
    },
    {
      date: "03-10",
      sessions: 930,
      orders: 144,
      revenue: 17900000,
      conversion: 15.5,
    },
    {
      date: "03-11",
      sessions: 960,
      orders: 152,
      revenue: 18600000,
      conversion: 15.8,
    },
    {
      date: "03-12",
      sessions: 1020,
      orders: 166,
      revenue: 20100000,
      conversion: 16.3,
    },
    {
      date: "03-13",
      sessions: 1050,
      orders: 170,
      revenue: 20800000,
      conversion: 16.2,
    },
    {
      date: "03-14",
      sessions: 1100,
      orders: 182,
      revenue: 21800000,
      conversion: 16.5,
    },
  ];

  const product: ChannelBreakdown[] = [
    {
      name: "과일 · 채소",
      sessions: 2200,
      orders: 360,
      revenue: 42000000,
      conversion: 16.4,
    },
    {
      name: "정육 · 수산",
      sessions: 1800,
      orders: 290,
      revenue: 39000000,
      conversion: 16.1,
    },
    {
      name: "곡물 · 건강",
      sessions: 1400,
      orders: 220,
      revenue: 25000000,
      conversion: 15.7,
    },
    {
      name: "간편식",
      sessions: 1200,
      orders: 180,
      revenue: 21000000,
      conversion: 15.0,
    },
    {
      name: "기타",
      sessions: 900,
      orders: 140,
      revenue: 14000000,
      conversion: 15.6,
    },
  ];

  return {
    kpis: [
      { label: "총 매출", value: 218000000, delta: 6.2, unit: "원" },
      { label: "주문 수", value: 2540, delta: 4.1 },
      { label: "전환율", value: 15.9, delta: 0.6, unit: "%" },
      { label: "신규 가입", value: 1840, delta: -1.9 },
      { label: "재방문율", value: 42.5, delta: 1.2, unit: "%" },
      { label: "반품률", value: 3.8, delta: 0.4, unit: "%" },
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
  };
}
</script>

<style scoped>
.admin-analytics {
  padding: 24px 22px 48px;
  background: #f6f7fb;
  min-height: 100vh;
  color: #0f172a;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 16px;
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
  0% {
    box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.4);
  }
  70% {
    box-shadow: 0 0 0 8px rgba(245, 158, 11, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(245, 158, 11, 0);
  }
}

.dashboard-section {
  margin-top: 16px;
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

.section-meta {
  font-size: 12px;
  color: #94a3b8;
}

.filters {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 10px;
  align-items: end;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 10px 12px;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.05);
  margin-bottom: 16px;
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
.filter input[type="date"] {
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
  padding: 9px 13px;
  font-weight: 800;
}

.actions .ghost {
  border: 1px solid #e2e8f0;
  background: #fff;
  color: #334155;
  border-radius: 10px;
  padding: 9px 13px;
  font-weight: 700;
}

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 10px;
  margin: 10px 0 8px 0;
}

.kpi-card {
  background: linear-gradient(135deg, #f8fafc, #eef2ff);
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  padding: 12px;
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
  padding: 14px 14px 16px;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.05);
}

.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
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

.summary-card {
  margin-top: 22px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px 18px;
}

.summary-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.summary-label {
  font-size: 14px;
  color: #64748b;
  font-weight: 600;
}

.summary-value {
  font-size: 16px;
  font-weight: 700;
  color: #0f172a;
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

.pill.high {
  background: #ef4444;
}
.pill.medium {
  background: #f59e0b;
}
.pill.low {
  background: #10b981;
}

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

.todo-list input[type="checkbox"] {
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
