<template>
  <div class="admin-page">
    <header class="page-header">
      <div>
        <p class="eyebrow">전체 관리자 · Recommendation</p>
        <h1>추천 알고리즘 성과 지표</h1>
        <p class="sub">
          홈 추천 CTR, 구매 전환율, 기여 GMV를 한 곳에서 점검합니다.
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
        <span class="label">알고리즘</span>
        <select v-model="algorithm">
          <option value="all">전체</option>
          <option value="price_model">Price log Model</option>
          <option value="personalized">Personalized Model</option>
          <option value="gapfill">Gap Filling Model</option>
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

    <section v-if="errorMessage" class="alert">
      {{ errorMessage }}
    </section>

    <section class="dashboard-section">
      <header class="section-head">
        <div>
          <p class="eyebrow">Home Recommendation</p>
          <h2>홈 추천 성과 지표</h2>
          <p class="section-sub">
            홈 화면 추천 영역의 핵심 전환 지표를 요약합니다.
          </p>
        </div>
      </header>

      <div class="kpi-grid">
        <article v-for="card in recoKpiCards" :key="card.key" class="kpi-card">
          <p class="label">{{ card.label }}</p>
          <div class="value-row">
            <span class="value">
              {{ formatNumber(card.value, card.unit, card.decimals) }}
            </span>
          </div>
          <p class="hint">
            조회 기준: {{ appliedFilters.start }} ~ {{ appliedFilters.end }} /
            {{ appliedSegmentLabel }}
          </p>
        </article>
      </div>

      <section class="charts-row">
        <section class="trend-section">
          <header class="trend-head">
            <div>
              <p class="eyebrow">CTR & Conversion</p>
              <h3>추천 CTR · 구매 전환율 추이</h3>
              <p class="section-sub">
                선택한 기간 동안 추천 영역의 CTR과 구매 전환율 변화를
                확인합니다.
              </p>
            </div>
          </header>
          <div ref="ctrChartRef" class="trend-chart"></div>
        </section>

        <section class="gmv-section">
          <header class="trend-head">
            <div>
              <p class="eyebrow">Revenue Contribution</p>
              <h3>추천 기여 GMV 비율 추이</h3>
              <p class="section-sub">
                추천을 통해 발생한 매출이 전체 매출에서 차지하는 비율 변화를
                확인합니다.
              </p>
            </div>
          </header>
          <div ref="gmvChartRef" class="placement-chart"></div>
        </section>
      </section>
    </section>
  </div>
</template>

<script setup lang="ts">
import {
  ref,
  computed,
  watch,
  onMounted,
  onBeforeUnmount,
  nextTick,
} from "vue";
import * as echarts from "echarts/core";
import { LineChart } from "echarts/charts";
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import { adminAnalyticsAPI } from "@/services/api/analytics";
import type { AnalyticsOverview, Granularity } from "@/types/analytics";

echarts.use([
  LineChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  CanvasRenderer,
]);

const granularityOptions: Granularity[] = [
  "daily",
  "weekly",
  "monthly",
  "yearly",
];
const granularity = ref<Granularity>("daily");
const dateRange = ref({ start: getDateNDaysAgo(13), end: getDateNDaysAgo(0) });
const segment = ref("all");
const algorithm = ref<"all" | "price_model" | "personalized" | "gapfill">(
  "all"
);

const appliedFilters = ref({
  start: dateRange.value.start,
  end: dateRange.value.end,
  segment: segment.value,
});

const overview = ref<AnalyticsOverview | null>(null);
const loading = ref(false);
const errorMessage = ref<string | null>(null);
const lastUpdated = ref(new Date().toLocaleString());

const ctrChartRef = ref<HTMLDivElement | null>(null);
const gmvChartRef = ref<HTMLDivElement | null>(null);
const charts: Record<"ctr" | "gmv", echarts.ECharts | null> = {
  ctr: null,
  gmv: null,
};

type DashboardKpiCard = {
  key: string;
  label: string;
  value: number;
  unit?: string;
  decimals?: number;
};

const segmentLabel = (value: string) => {
  if (value === "consumer") return "일반회원";
  if (value === "seller") return "판매자";
  return "전체";
};

const appliedSegmentLabel = computed(() =>
  segmentLabel(appliedFilters.value.segment)
);

const recoKpiCards = computed<DashboardKpiCard[]>(() => {
  const src = overview.value?.kpis ?? [];

  const findByPrefix = (prefix: string) =>
    src.find((k) => k.label.startsWith(prefix));

  const ctr = findByPrefix("홈 추천 CTR");
  const purchaseConv = findByPrefix("홈 추천 구매 전환율");
  const gmvShare = findByPrefix("홈 추천 기여 GMV 비율");

  return [
    {
      key: "home_ctr",
      label: ctr?.label ?? "홈 추천 CTR",
      value: ctr?.value ?? 0,
      unit: ctr?.unit ?? "%",
      decimals: 2,
    },
    {
      key: "home_purchase_conv",
      label: purchaseConv?.label ?? "홈 추천 구매 전환율",
      value: purchaseConv?.value ?? 0,
      unit: purchaseConv?.unit ?? "%",
      decimals: 2,
    },
    {
      key: "home_reco_gmv_share",
      label: gmvShare?.label ?? "홈 추천 기여 GMV 비율",
      value: gmvShare?.value ?? 0,
      unit: gmvShare?.unit ?? "%",
      decimals: 2,
    },
  ];
});

type RecoPoint = {
  date: string;
  impressions: number;
  clicks: number;
  attributed_orders: number;
  attributed_gmv: number;
  ctr: number;
  purchase_conversion: number;
  gmv_share: number;
  total_gmv: number;
};

const formatRecoSeries = (raw: RecoPoint[], unit: Granularity): RecoPoint[] => {
  if (unit === "daily") return raw;
  const bucketSize = unit === "weekly" ? 7 : unit === "monthly" ? 30 : 365;
  const buckets: RecoPoint[] = [];

  for (let i = 0; i < raw.length; i += bucketSize) {
    const slice = raw.slice(i, i + bucketSize);
    if (!slice.length) continue;

    const impressions = slice.reduce((s, v) => s + v.impressions, 0);
    const clicks = slice.reduce((s, v) => s + v.clicks, 0);
    const attributed_orders = slice.reduce(
      (s, v) => s + v.attributed_orders,
      0
    );
    const attributed_gmv = slice.reduce((s, v) => s + v.attributed_gmv, 0);
    const total_gmv = slice.reduce((s, v) => s + v.total_gmv, 0);

    const ctr = impressions > 0 ? (clicks / impressions) * 100.0 : 0.0;
    const purchase_conversion =
      clicks > 0 ? (attributed_orders / clicks) * 100.0 : 0.0;
    const gmv_share =
      total_gmv > 0 ? (attributed_gmv / total_gmv) * 100.0 : 0.0;

    const label =
      unit === "weekly"
        ? `${Math.floor(i / 7) + 1}주차`
        : unit === "monthly"
        ? `${Math.floor(i / 30) + 1}개월차`
        : `${Math.floor(i / 365) + 1}년차`;

    buckets.push({
      date: label,
      impressions,
      clicks,
      attributed_orders,
      attributed_gmv,
      ctr: Number(ctr.toFixed(2)),
      purchase_conversion: Number(purchase_conversion.toFixed(2)),
      gmv_share: Number(gmv_share.toFixed(2)),
      total_gmv,
    });
  }

  return buckets;
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
    const [{ data: overviewData }, trendResponse] = await Promise.all([
      adminAnalyticsAPI.getOverview({
        start_date: dateRange.value.start,
        end_date: dateRange.value.end,
        granularity: granularity.value,
        segment: segment.value,
      }),
      adminAnalyticsAPI.getRecommendationTrend({
        start_date: dateRange.value.start,
        end_date: dateRange.value.end,
        granularity: granularity.value,
        segment: segment.value,
        placement: algorithm.value === "all" ? "all" : algorithm.value,
      }),
    ]);

    overview.value = overviewData;
    const rawSeries = (trendResponse.data.series ?? []) as RecoPoint[];
    const series = formatRecoSeries(rawSeries, granularity.value);
    updateCtrChart(series);
    updateGmvChart(series);
  } catch (err: any) {
    // 조회 실패 시 에러 메시지와 함께 값 0으로 표시
    errorMessage.value =
      err?.response?.data?.detail ||
      "추천 지표를 불러오지 못했습니다. 잠시 후 다시 시도해주세요.";
    overview.value = null;
    updateCtrChart([]);
    updateGmvChart([]);
  } finally {
    loading.value = false;
    lastUpdated.value = new Date().toLocaleString();
  }
};

const getChart = (key: "ctr" | "gmv", el: HTMLDivElement | null) => {
  if (!el) return null;
  if (!charts[key]) {
    charts[key] = echarts.init(el);
  }
  return charts[key];
};

const updateCtrChart = (
  placements: Array<{
    date: string;
    impressions: number;
    clicks: number;
    attributed_orders: number;
    attributed_gmv: number;
    ctr: number;
    purchase_conversion: number;
    gmv_share: number;
  }>
) => {
  nextTick(() => {
    const chart = getChart("ctr", ctrChartRef.value);
    if (!chart) return;

    const dates = placements.map((p) => p.date);

    const option: echarts.EChartsCoreOption = {
      title: {
        text: "CTR & Conversion",
        subtext:
          "추천 CTR · 구매 전환율 추이\n선택한 기간 동안 추천 영역의 CTR과 구매 전환율 변화를 확인합니다.",
        left: 20,
        top: 10,
        textStyle: { fontSize: 16, fontWeight: 800, color: "#111827" },
        subtextStyle: { fontSize: 11, color: "#6b7280", lineHeight: 16 },
      },
      grid: { top: 96, left: 40, right: 36, bottom: 40 },
      tooltip: {
        trigger: "axis",
        valueFormatter: (value) =>
          typeof value === "number" ? `${value.toFixed(2)}%` : `${value}`,
      },
      legend: {
        data: ["CTR", "구매 전환율"],
        bottom: 0,
        textStyle: { color: "#1f2933" },
      },
      xAxis: {
        type: "category",
        data: dates,
      },
      yAxis: {
        type: "value",
        axisLabel: {
          formatter: "{value}%",
          color: "#4b5563",
        },
      },
      series: [
        {
          name: "CTR",
          type: "line",
          smooth: true,
          data: placements.map((p) => p.ctr),
        },
        {
          name: "구매 전환율",
          type: "line",
          smooth: true,
          data: placements.map((p) => p.purchase_conversion),
        },
      ],
    };

    chart.setOption(option, true);
  });
};

const updateGmvChart = (
  placements: Array<{
    date: string;
    impressions: number;
    clicks: number;
    attributed_orders: number;
    attributed_gmv: number;
    ctr: number;
    purchase_conversion: number;
    gmv_share: number;
  }>
) => {
  nextTick(() => {
    const chart = getChart("gmv", gmvChartRef.value);
    if (!chart) return;

    const dates = placements.map((p) => p.date);

    const option: echarts.EChartsCoreOption = {
      title: {
        text: "추천 기여 GMV 비율 추이",
        subtext:
          "추천을 통해 발생한 매출이 전체 매출에서 차지하는 비율 변화를 확인합니다.",
        left: 20,
        top: 10,
        textStyle: { fontSize: 14, fontWeight: 700, color: "#111827" },
        subtextStyle: { fontSize: 11, color: "#6b7280" },
      },
      grid: { top: 80, left: 40, right: 36, bottom: 40 },
      tooltip: {
        trigger: "axis",
        valueFormatter: (value) =>
          typeof value === "number" ? `${value.toFixed(2)}%` : `${value}`,
      },
      legend: {
        data: ["기여 GMV 비율"],
        bottom: 0,
        textStyle: { color: "#1f2933" },
      },
      xAxis: {
        type: "category",
        data: dates,
      },
      yAxis: {
        type: "value",
        axisLabel: {
          formatter: "{value}%",
          color: "#4b5563",
        },
      },
      series: [
        {
          name: "기여 GMV 비율",
          type: "line",
          smooth: true,
          data: placements.map((p) => p.gmv_share),
        },
      ],
    };

    chart.setOption(option, true);
  });
};

watch(algorithm, () => {
  // 알고리즘 변경 시에는 조회 버튼을 눌러야 실제 데이터가 변경되므로
  // 여기서는 기존 차트를 유지하고, 다음 조회에서 새로운 placement 값이 적용되도록 둔다.
});

const resetFilters = () => {
  granularity.value = "daily";
  dateRange.value = { start: getDateNDaysAgo(13), end: getDateNDaysAgo(0) };
  segment.value = "all";
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
  const resolvedDecimals = decimals ?? (unit === "%" ? 2 : 0);
  const formatted = value.toLocaleString("ko-KR", {
    minimumFractionDigits: resolvedDecimals,
    maximumFractionDigits: resolvedDecimals,
  });
  return unit ? `${formatted}${unit}` : formatted;
};

function getDateNDaysAgo(n: number) {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return d.toISOString().slice(0, 10);
}

onMounted(() => {
  loadData();
});

onBeforeUnmount(() => {
  Object.values(charts).forEach((chart) => {
    if (chart) {
      chart.dispose();
    }
  });
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

.trend-chart {
  margin-top: 10px;
  width: 100%;
  height: 440px;
  border-radius: 14px;
  background: #ffffff;
  padding: 10px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.05);
}

.placement-chart {
  margin-top: 10px;
  width: 100%;
  height: 440px;
  border-radius: 14px;
  background: #ffffff;
  padding: 10px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.05);
}
</style>
