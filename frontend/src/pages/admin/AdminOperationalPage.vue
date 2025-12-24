<template>
  <div class="admin-page">
    <header class="page-header">
      <div>
        <p class="eyebrow">전체 관리자 · Operational</p>
        <h1>운영 건강도 지표</h1>
        <p class="sub">
          크롤링 성공률, EC2 CPU, 네트워크 트래픽, 서비스 가용성을 한눈에 모니터링합니다.
        </p>
      </div>
      <div class="sync">
        <span class="dot" :class="loading ? 'syncing' : 'ok'"></span>
        <span v-if="lastUpdated">동기화: {{ lastUpdated }}</span>
        <span v-if="backendLabel" class="backend-label">
          · 소스: {{ backendLabel }}
        </span>
        <label class="data-mode-toggle">
          <input type="checkbox" disabled />
          <span>테스트 데이터 없음</span>
        </label>
      </div>
    </header>

    <section class="filters">
      <div class="filter">
        <span class="label">조회 기간</span>
        <div class="segmented">
          <button
            v-for="opt in rangeOptions"
            :key="opt.value"
            :class="{ active: range === opt.value }"
            @click="onRangeChange(opt.value)"
          >
            {{ opt.label }}
          </button>
        </div>
      </div>
      <div class="filter">
        <span class="label">시스템</span>
        <select v-model="system">
          <option value="all">전체</option>
          <option value="crawler">크롤러</option>
          <option value="api">백엔드 API</option>
          <option value="model">예측 모델</option>
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

    <section class="dashboard-section">
      <header class="section-head">
        <div>
          <p class="eyebrow">Ops Overview</p>
          <h2>운영 KPI</h2>
          <p class="section-sub">
            크롤링 성공률, EC2 CPU 사용률, 네트워크 트래픽, 서비스 가용성 등 핵심 운영 지표를 요약합니다.
          </p>
        </div>
      </header>

      <div class="kpi-grid">
        <article
          v-for="card in opsKpiCards"
          :key="card.key"
          class="kpi-card"
        >
          <p class="label">{{ card.label }}</p>
          <div class="value-row">
            <span class="value">
              {{ formatNumber(card.value, card.unit, card.decimals) }}
            </span>
          </div>
          <p class="hint">{{ card.hint }}</p>
        </article>
      </div>

      <div class="charts-grid">
        <article class="card">
          <header class="card-head">
            <div>
              <p class="eyebrow">Crawling</p>
              <h3>크롤링 성공률 추이</h3>
            </div>
          </header>
          <div ref="crawlChartRef" class="chart chart-small"></div>
        </article>

        <article class="card">
          <header class="card-head">
            <div>
              <p class="eyebrow">EC2 CPU</p>
              <h3>EC2 CPU 사용률 추이</h3>
            </div>
          </header>
          <div ref="cpuChartRef" class="chart chart-small"></div>
        </article>

        <article class="card">
          <header class="card-head">
            <div>
              <p class="eyebrow">Network</p>
              <h3>네트워크 트래픽 (In) 추이</h3>
            </div>
          </header>
          <div ref="networkChartRef" class="chart chart-small"></div>
        </article>
      </div>

      <article class="card ops-lists-card">
        <header class="card-head">
          <div>
            <p class="eyebrow">Alerts · To-do · Incidents</p>
            <h3>운영 리스크 & 작업 목록</h3>
          </div>
        </header>

        <div class="ops-lists">
          <section class="ops-list-section">
            <h4 class="ops-list-title">리스크 알림</h4>
            <ul v-if="alerts.length" class="alert-list">
              <li v-for="alert in alerts" :key="alert.id" class="alert-item">
                <span class="pill" :class="alert.severity">
                  {{ incidentSeverityLabel(alert.severity) }}
                </span>
                <div class="alert-main">
                  <p class="alert-title">{{ alert.title }}</p>
                  <p class="alert-desc">{{ alert.description }}</p>
                  <p class="alert-meta">
                    기준 지표: {{ alert.metric }}
                  </p>
                </div>
              </li>
            </ul>
            <p v-else class="hint">현재 설정된 임계값을 초과한 리스크가 없습니다.</p>
          </section>

          <section class="ops-list-section">
            <h4 class="ops-list-title">운영 To-do</h4>
            <ul v-if="todos.length" class="todo-list">
              <li v-for="todo in todos" :key="todo.id" class="todo-item">
                <div class="todo-main">
                  <p class="todo-title">{{ todo.title }}</p>
                  <p class="todo-desc">{{ todo.description }}</p>
                  <p class="todo-meta">{{ todo.meta }}</p>
                </div>
              </li>
            </ul>
            <p v-else class="hint">현재 등록된 운영 To-do가 없습니다.</p>
          </section>

          <section class="ops-list-section">
            <h4 class="ops-list-title">최근 장애 이력</h4>
            <ul v-if="incidents.length" class="incident-list">
              <li v-for="incident in incidents" :key="incident.id" class="incident">
                <span class="pill" :class="incident.severity">
                  {{ incidentSeverityLabel(incident.severity) }}
                </span>
                <div class="incident-main">
                  <p class="incident-title">{{ incident.title }}</p>
                  <p class="incident-desc">{{ incident.description }}</p>
                  <p class="incident-meta">
                    {{ incident.service }} · 시작:
                    {{ formatDateTime(incident.started_at) }}
                    <span v-if="incident.resolved_at">
                      · 종료: {{ formatDateTime(incident.resolved_at) }}
                    </span>
                    <span v-else> · 진행 중</span>
                  </p>
                </div>
              </li>
            </ul>
            <p v-else class="hint">최근 7일 내 등록된 장애 이력이 없습니다.</p>
          </section>
        </div>
      </article>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from "vue";
import * as echarts from "echarts/core";
import { LineChart } from "echarts/charts";
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import { adminAnalyticsAPI } from "@/services/api/analytics";
import type {
  OpsOverview,
  OpsIncident,
  OpsMetricPoint,
  OpsAlert,
  OpsTodo,
} from "@/types/analytics";

echarts.use([LineChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer]);

type RangeKey = "1h" | "7d" | "30d";

const range = ref<RangeKey>("7d");
const system = ref("all");

const overview = ref<OpsOverview | null>(null);
const loading = ref(false);
const errorMessage = ref<string | null>(null);
const lastUpdated = ref<string | null>(null);

const crawlChartRef = ref<HTMLDivElement | null>(null);
const cpuChartRef = ref<HTMLDivElement | null>(null);
const networkChartRef = ref<HTMLDivElement | null>(null);
const charts: Record<"crawl" | "cpu" | "network", echarts.ECharts | null> = {
  crawl: null,
  cpu: null,
  network: null,
};

type OpsKpiCard = {
  key: string;
  label: string;
  value: number;
  unit?: string;
  decimals?: number;
  hint: string;
};

const metrics = computed<OpsMetricPoint[]>(() => overview.value?.timeseries ?? []);
const incidents = computed<OpsIncident[]>(() => overview.value?.incidents ?? []);
const alerts = computed<OpsAlert[]>(() => overview.value?.alerts ?? []);
const todos = computed<OpsTodo[]>(() => overview.value?.todos ?? []);

const backendLabel = computed(() => {
  const backend = overview.value?.meta?.backend;
  if (backend === "cloudwatch") return "CloudWatch (실측)";
  if (backend === "mock") return "Mock 데이터";
  return "";
});

const opsKpiCards = computed<OpsKpiCard[]>(() => {
  const kpis = overview.value?.kpis ?? [];

  const find = (prefix: string) => kpis.find((k) => k.label.startsWith(prefix));

  const crawl = find("크롤링 성공률");
  const cpu = find("EC2 CPU 사용률");
  const network = find("네트워크 트래픽");
  const avail = find("서비스 가용성");

  return [
    {
      key: "crawl_success",
      label: crawl?.label ?? "크롤링 성공률",
      value: crawl?.value ?? 0,
      unit: crawl?.unit ?? "%",
      decimals: 2,
      hint: "최근 집계 기준 전체 크롤링 성공 비율",
    },
    {
      key: "api_p95",
      label: cpu?.label ?? "EC2 CPU 사용률",
      value: cpu?.value ?? 0,
      unit: cpu?.unit ?? "%",
      decimals: 1,
      hint: "백엔드 EC2 인스턴스 CPU 사용률",
    },
    {
      key: "error_rate",
      label: network?.label ?? "네트워크 트래픽 (In)",
      value: network?.value ?? 0,
      unit: network?.unit ?? "bps",
      decimals: 2,
      hint: "EC2 인스턴스 네트워크 In 트래픽(평균, bps 기준)",
    },
    {
      key: "availability",
      label: avail?.label ?? "서비스 가용성",
      value: avail?.value ?? 0,
      unit: avail?.unit ?? "%",
      decimals: 3,
      hint: "서비스 가용 시간 기준 가용성 지표",
    },
  ];
});

const rangeOptions: { value: RangeKey; label: string }[] = [
  { value: "1h", label: "최근 1시간" },
  { value: "7d", label: "최근 7일" },
  { value: "30d", label: "최근 30일" },
];

const getChart = (key: "crawl" | "cpu" | "network", el: HTMLDivElement | null) => {
  if (!el) return null;
  if (!charts[key]) {
    charts[key] = echarts.init(el);
  }
  return charts[key];
};

const renderCrawlChart = () => {
  const chart = getChart("crawl", crawlChartRef.value);
  if (!chart) return;

  const data = metrics.value;
  const labels = data.map((d) => formatTimeLabel(d.timestamp));

  const option: echarts.EChartsCoreOption = {
    grid: { top: 32, left: 56, right: 32, bottom: 56 },
    tooltip: {
      trigger: "axis",
    },
    xAxis: {
      type: "category",
      data: labels,
    },
    yAxis: {
      type: "value",
      name: "크롤링 성공률(%)",
      min: 90,
      max: 100,
    },
    series: [
      {
        name: "크롤링 성공률",
        type: "line",
        data: data.map((d) => d.crawling_success_rate),
        smooth: true,
        lineStyle: { width: 2.5, color: "#22c55e" },
        symbolSize: 5,
      },
    ],
  };

  chart.setOption(option, true);
};

const renderCpuChart = () => {
  const chart = getChart("cpu", cpuChartRef.value);
  if (!chart) return;

  const data = metrics.value;
  const labels = data.map((d) => formatTimeLabel(d.timestamp));

  const option: echarts.EChartsCoreOption = {
    grid: { top: 32, left: 56, right: 32, bottom: 56 },
    tooltip: {
      trigger: "axis",
    },
    xAxis: {
      type: "category",
      data: labels,
    },
    yAxis: {
      type: "value",
      name: "EC2 CPU 사용률(%)",
      min: 0,
      max: 100,
    },
    series: [
      {
        name: "EC2 CPU 사용률",
        type: "line",
        data: data.map((d) => d.api_p95_ms),
        smooth: true,
        lineStyle: { width: 2.5, color: "#f97316" },
        symbolSize: 5,
      },
    ],
  };

  chart.setOption(option, true);
};

const formatBpsShort = (value: number) => {
  const absV = Math.abs(value);
  if (absV >= 1_000_000_000) {
    return `${(value / 1_000_000_000).toFixed(1)} Gbps`;
  }
  if (absV >= 1_000_000) {
    return `${(value / 1_000_000).toFixed(1)} Mbps`;
  }
  if (absV >= 1_000) {
    return `${(value / 1_000).toFixed(1)} Kbps`;
  }
  return `${value.toFixed(0)} bps`;
};

const renderNetworkChart = () => {
  const chart = getChart("network", networkChartRef.value);
  if (!chart) return;

  const data = metrics.value;
  const labels = data.map((d) => formatTimeLabel(d.timestamp));

  const option: echarts.EChartsCoreOption = {
    grid: { top: 32, left: 88, right: 32, bottom: 56 },
    tooltip: {
      trigger: "axis",
      formatter: (params: any) => {
        if (!params || !params.length) return '';
        const item = params[0];
        return `${item.axisValueLabel}<br/>${item.marker}${item.seriesName}: ${formatBpsShort(item.value)}`;
      },
    },
    xAxis: {
      type: "category",
      data: labels,
    },
    yAxis: {
      type: "value",
      name: "네트워크 트래픽 (bps)",
      min: 0,
      axisLabel: {
        formatter: (val: number) => formatBpsShort(val),
      },
    },
    series: [
      {
        name: "네트워크 트래픽 (In)",
        type: "line",
        data: data.map((d) => d.error_rate),
        smooth: true,
        lineStyle: { width: 2, color: "#ef4444" },
        symbolSize: 5,
      },
    ],
  };

  chart.setOption(option, true);
};

const renderCharts = () => {
  renderCrawlChart();
  renderCpuChart();
  renderNetworkChart();
};

const onRangeChange = (value: RangeKey) => {
  if (range.value === value) return;
  range.value = value;
};

const handleResize = () => {
  Object.values(charts).forEach((c) => c?.resize());
};

const loadData = async () => {
  loading.value = true;
  errorMessage.value = null;

  try {
    const { data } = await adminAnalyticsAPI.getOpsOverview({
      range: range.value,
      system: system.value,
    });
    overview.value = data;
    await nextTick();
    renderCharts();
    lastUpdated.value = new Date().toLocaleString();
  } catch (err: any) {
    console.error("AdminOpsOverview 조회 실패", err);
    errorMessage.value =
      err?.response?.data?.detail ||
      "운영 지표를 불러오지 못했습니다. 잠시 후 다시 시도해주세요.";
    overview.value = null;
  } finally {
    loading.value = false;
  }
};

const resetFilters = () => {
  range.value = "7d";
  system.value = "all";
  loadData();
};

const formatNumber = (value: number, unit?: string, decimals?: number) => {
  const resolvedDecimals = decimals ?? (unit === "%" ? 2 : 0);
  const formatted = value.toLocaleString("ko-KR", {
    minimumFractionDigits: resolvedDecimals,
    maximumFractionDigits: resolvedDecimals,
  });
  return unit ? `${formatted}${unit}` : formatted;
};

const incidentSeverityLabel = (severity: string) => {
  if (severity === "high") return "High";
  if (severity === "medium") return "Medium";
  if (severity === "low") return "Low";
  return severity;
};

const formatDateTime = (value: string | null) => {
  if (!value) return "";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString("ko-KR");
};

const formatTimeLabel = (value: string) => {
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;

  // 최근 1시간 범위일 때는 시:분 중심으로 표시
  if (range.value === "1h") {
    return d.toLocaleTimeString("ko-KR", {
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  return `${d.getMonth() + 1}/${d.getDate()}`;
};

onMounted(() => {
  loadData();
  window.addEventListener("resize", handleResize);
});
</script>

<style scoped>
.admin-page {
  padding: 28px;
  background: #f6f7fb;
  min-height: 100vh;
}

.page-header {
  margin-bottom: 18px;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.page-header h1 {
  font-size: 24px;
  font-weight: 800;
  margin: 6px 0;
}

.sub {
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

.data-mode-toggle {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-left: 10px;
  font-size: 11px;
  color: #64748b;
}

.data-mode-toggle input {
  width: 14px;
  height: 14px;
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
  margin-bottom: 18px;
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

.filter select {
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 10px 12px;
  background: #fff;
}

.filter.wide {
  grid-column: span 2;
}

.segmented {
  display: inline-flex;
  padding: 2px;
  border-radius: 999px;
  background: #f1f5f9;
  gap: 4px;
}

.segmented button {
  border: none;
  background: transparent;
  padding: 6px 10px;
  border-radius: 999px;
  font-size: 12px;
  color: #64748b;
  font-weight: 600;
  cursor: pointer;
}

.segmented button.active {
  background: #2563eb;
  color: #f9fafb;
  box-shadow: 0 4px 10px rgba(37, 99, 235, 0.35);
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

.alert {
  padding: 12px 14px;
  border-radius: 12px;
  border: 1px solid #fecdd3;
  background: #fff1f2;
  color: #be123c;
  font-weight: 700;
  margin-bottom: 12px;
}

.dashboard-section {
  margin-top: 20px;
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

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
  margin: 14px 0 12px 0;
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

.hint {
  color: #94a3b8;
  font-size: 12px;
}

.card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 18px;
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
  height: 260px;
}

.chart-small {
  height: 260px;
}

.charts-grid {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 12px;
}

.ops-lists-card {
  margin-top: 12px;
}

.ops-lists {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 12px;
}

.ops-list-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.ops-list-title {
  margin: 0 0 4px 0;
  font-size: 14px;
  font-weight: 800;
  color: #0f172a;
}

.alert-list,
.todo-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.alert-item,
.todo-item {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 8px;
  align-items: flex-start;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  background: #f8fafc;
}

.alert-main,
.todo-main {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.alert-title,
.todo-title {
  margin: 0;
  font-weight: 800;
  color: #0f172a;
}

.alert-desc,
.todo-desc {
  margin: 0;
  font-size: 13px;
  color: #475569;
}

.alert-meta,
.todo-meta {
  margin: 0;
  font-size: 12px;
  color: #94a3b8;
}

.incident-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.incident {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 10px;
  align-items: flex-start;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
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

.incident-main {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.incident-title {
  margin: 0;
  font-weight: 800;
  color: #0f172a;
}

.incident-desc {
  margin: 0;
  font-size: 13px;
  color: #475569;
}

.incident-meta {
  margin: 0;
  font-size: 12px;
  color: #94a3b8;
}
</style>


