<template>
  <div class="admin-page">
    <header class="page-header">
      <div>
        <p class="eyebrow">전체 관리자 · User Behavior</p>
        <h1>유저 행동 지표</h1>
        <p class="sub">
          구매 DAU/MAU, 장바구니·결제 퍼널, 이탈 구간을 집중적으로 모니터링합니다.
        </p>
      </div>
      <div class="sync">
        <span class="dot" :class="loading ? 'syncing' : 'ok'"></span>
        <span v-if="lastUpdated">동기화: {{ lastUpdated }}</span>
      </div>
    </header>

    <section class="filters">
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
          <p class="eyebrow">Behavior Overview</p>
          <h2>구매 DAU/MAU · 장바구니/구매 전환</h2>
          <p class="section-sub">
            세그먼트별 활성 구매자와 장바구니·구매 전환 성과를 요약합니다.
          </p>
        </div>
      </header>

      <div class="kpi-grid">
        <article
          v-for="card in behaviorKpiCards"
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

      <div class="grid">
        <article class="card">
          <header class="card-head">
            <div>
              <p class="eyebrow">Trend</p>
              <h3>구매자 · 장바구니 · 주문 추이</h3>
            </div>
          </header>
          <div ref="trendChartRef" class="chart"></div>
        </article>

        <article class="card">
          <header class="card-head">
            <div>
              <p class="eyebrow">Funnel</p>
              <h3>세션 → 장바구니 → 구매 퍼널</h3>
            </div>
          </header>
          <ul v-if="funnels.length" class="funnel-list">
            <li v-for="step in funnels" :key="step.name" class="funnel-step">
              <div class="funnel-header">
                <span class="funnel-name">{{ step.name }}</span>
                <span class="funnel-value">
                  {{ step.value.toLocaleString("ko-KR") }}
                  <span v-if="step.rate != null">({{ step.rate.toFixed(1) }}%)</span>
                </span>
              </div>
              <div class="funnel-bar">
                <div
                  class="funnel-bar-fill"
                  :style="{ width: Math.min(stepRate(step), 100) + '%' }"
                ></div>
              </div>
            </li>
          </ul>
          <p v-else class="hint">
            아직 퍼널을 계산할 수 있는 집계 데이터가 없습니다.
          </p>
        </article>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from "vue";
import * as echarts from "echarts/core";
import { LineChart, BarChart } from "echarts/charts";
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import { adminAnalyticsAPI } from "@/services/api/analytics";
import type {
  BehaviorOverview,
  BehaviorTrendPoint,
  BehaviorFunnelStep,
} from "@/types/analytics";

echarts.use([
  LineChart,
  BarChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  CanvasRenderer,
]);

const dateRange = ref({ start: getDateNDaysAgo(13), end: getDateNDaysAgo(0) });
const segment = ref("all");

const appliedFilters = ref({
  start: dateRange.value.start,
  end: dateRange.value.end,
  segment: segment.value,
});

const overview = ref<BehaviorOverview | null>(null);
const loading = ref(false);
const errorMessage = ref<string | null>(null);
const lastUpdated = ref<string | null>(null);

const trendChartRef = ref<HTMLDivElement | null>(null);
const charts: Record<"trend", echarts.ECharts | null> = {
  trend: null,
};

type BehaviorKpiCard = {
  key: string;
  label: string;
  value: number;
  unit?: string;
  decimals?: number;
  hint: string;
};

const segmentLabel = (value: string) => {
  if (value === "consumer") return "일반회원";
  if (value === "seller") return "판매자";
  return "전체";
};

const appliedSegmentLabel = computed(() =>
  segmentLabel(appliedFilters.value.segment)
);

const trendData = computed<BehaviorTrendPoint[]>(
  () => overview.value?.trend ?? []
);
const funnels = computed<BehaviorFunnelStep[]>(
  () => overview.value?.funnels ?? []
);

const behaviorKpiCards = computed<BehaviorKpiCard[]>(() => {
  const kpis = overview.value?.kpis ?? [];

  const find = (prefix: string) => kpis.find((k) => k.label.startsWith(prefix));

  const dau = find("구매 DAU");
  const mau = find("구매 MAU");
  const cartConv = find("장바구니→구매 전환율");
  const cartAbandon = find("장바구니 포기율");

  return [
    {
      key: "dau",
      label: dau?.label ?? "구매 DAU(추정)",
      value: dau?.value ?? 0,
      unit: dau?.unit ?? "명",
      decimals: 0,
      hint: `${appliedSegmentLabel.value} / 일 평균 구매자 수`,
    },
    {
      key: "mau",
      label: mau?.label ?? "구매 MAU(합산 기준 추정)",
      value: mau?.value ?? 0,
      unit: mau?.unit ?? "명",
      decimals: 0,
      hint: `${appliedSegmentLabel.value} / 기간 내 구매자 합계(근사치)`,
    },
    {
      key: "cart_conv",
      label: cartConv?.label ?? "장바구니→구매 전환율",
      value: cartConv?.value ?? 0,
      unit: cartConv?.unit ?? "%",
      decimals: 1,
      hint: "장바구니 담기 중 실제 주문으로 이어진 비율",
    },
    {
      key: "cart_abandon",
      label: cartAbandon?.label ?? "장바구니 포기율(추정)",
      value: cartAbandon?.value ?? 0,
      unit: cartAbandon?.unit ?? "%",
      decimals: 1,
      hint: "장바구니 도달 후 구매로 이어지지 않은 비율",
    },
  ];
});

const getChart = (key: "trend", el: HTMLDivElement | null) => {
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
  const dates = data.map((d) => d.date);

  const option: echarts.EChartsCoreOption = {
    grid: { top: 40, left: 56, right: 40, bottom: 56 },
    tooltip: { trigger: "axis" },
    legend: {
      data: ["구매자 수", "장바구니 담기", "주문 수"],
      bottom: 8,
    },
    xAxis: {
      type: "category",
      data: dates,
    },
    yAxis: {
      type: "value",
      name: "건수",
    },
    series: [
      {
        name: "구매자 수",
        type: "line",
        data: data.map((d) => d.buyers),
        smooth: true,
        lineStyle: { width: 2.5, color: "#2563eb" },
        symbolSize: 6,
      },
      {
        name: "장바구니 담기",
        type: "bar",
        data: data.map((d) => d.cart_adds),
        itemStyle: { color: "#a855f7" },
        barWidth: 10,
      },
      {
        name: "주문 수",
        type: "bar",
        data: data.map((d) => d.orders),
        itemStyle: { color: "#22c55e" },
        barWidth: 10,
        barGap: "20%",
      },
    ],
  };

  chart.setOption(option, true);
};

const renderCharts = () => {
  renderTrendChart();
};

const handleResize = () => {
  Object.values(charts).forEach((c) => c?.resize());
};

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
    const { data } = await adminAnalyticsAPI.getBehaviorOverview({
      start_date: dateRange.value.start,
      end_date: dateRange.value.end,
      segment: segment.value,
    });
    overview.value = data;
    await nextTick();
    renderCharts();
    lastUpdated.value = new Date().toLocaleString();
  } catch (err: any) {
    console.error("AdminBehaviorOverview 조회 실패", err);
    errorMessage.value =
      err?.response?.data?.detail ||
      "유저 행동 지표를 불러오지 못했습니다. 잠시 후 다시 시도해주세요.";
    overview.value = null;
  } finally {
    loading.value = false;
  }
};

const resetFilters = () => {
  dateRange.value = { start: getDateNDaysAgo(13), end: getDateNDaysAgo(0) };
  segment.value = "all";
  loadData();
};

const formatNumber = (value: number, unit?: string, decimals?: number) => {
  const resolvedDecimals = decimals ?? (unit === "%" ? 1 : 0);
  const formatted = value.toLocaleString("ko-KR", {
    minimumFractionDigits: resolvedDecimals,
    maximumFractionDigits: resolvedDecimals,
  });
  return unit ? `${formatted}${unit}` : formatted;
};

const stepRate = (step: BehaviorFunnelStep) => {
  if (step.rate != null) return step.rate;
  return 0;
};

function getDateNDaysAgo(n: number) {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return d.toISOString().slice(0, 10);
}

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
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 24px;
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

.grid {
  display: grid;
  grid-template-columns: 1.3fr 1fr;
  gap: 12px;
  margin-top: 12px;
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
  height: 360px;
}

.funnel-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.funnel-step {
  padding: 8px 10px;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
  background: #f8fafc;
}

.funnel-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 6px;
}

.funnel-name {
  font-weight: 700;
  color: #0f172a;
}

.funnel-value {
  font-size: 13px;
  color: #475569;
}

.funnel-bar {
  position: relative;
  width: 100%;
  height: 8px;
  border-radius: 999px;
  background: #e5e7eb;
  overflow: hidden;
}

.funnel-bar-fill {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  border-radius: 999px;
  background: linear-gradient(90deg, #2563eb, #22c55e);
}
</style>

