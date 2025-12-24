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
        <label class="data-mode-toggle">
          <input
            type="checkbox"
            v-model="includeTestData"
            :disabled="loading"
            @change="onDataModeChanged"
          />
          <span>테스트 데이터 포함</span>
        </label>
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
        <section class="chart-container half-width">
          <header class="card-head">
            <div>
              <p class="eyebrow">CTR</p>
              <h3>추천 CTR 추이</h3>
            </div>
          </header>
          <div ref="ctrChartRef" class="trend-chart"></div>
        </section>

        <section class="chart-container half-width">
          <header class="card-head">
            <div>
              <p class="eyebrow">Conversion</p>
              <h3>추천 구매 전환율 추이</h3>
            </div>
          </header>
          <div ref="conversionChartRef" class="trend-chart"></div>
        </section>
      </section>

      <section class="charts-row">
        <section class="chart-container full-width">
          <header class="card-head">
            <div>
              <p class="eyebrow">GMV Contribution</p>
              <h3>추천 기여 GMV 비율 추이</h3>
            </div>
          </header>
          <div ref="gmvChartRef" class="placement-chart"></div>
        </section>
      </section>
    </section>

    <section class="dashboard-section">
      <header class="section-head">
        <div>
          <p class="eyebrow">Placement Summary</p>
          <h2>알고리즘 · 위치별 성과 요약</h2>
          <p class="section-sub">
            추천 위치/알고리즘별 CTR, 구매 전환율, 기여 GMV 비율을 비교합니다.
          </p>
        </div>
      </header>

      <div class="placement-summary-grid">
        <article class="placement-card">
          <header class="section-head">
            <div>
              <p class="eyebrow">Performance</p>
              <h3>Placement별 요약 테이블</h3>
            </div>
          </header>

          <div class="table-wrapper">
            <table v-if="sortedPlacementSummary.length" class="placement-table">
              <thead>
                <tr>
                  <th>Placement</th>
                  <th>노출</th>
                  <th>클릭</th>
                  <th>CTR</th>
                  <th>구매 전환율</th>
                  <th>기여 GMV 비율</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in sortedPlacementSummary" :key="row.placement">
                  <td>{{ placementDisplayLabel(row.placement) }}</td>
                  <td>{{ row.impressions.toLocaleString("ko-KR") }}</td>
                  <td>{{ row.clicks.toLocaleString("ko-KR") }}</td>
                  <td>{{ row.ctr.toFixed(2) }}%</td>
                  <td>{{ row.purchase_conversion.toFixed(2) }}%</td>
                  <td>{{ row.gmv_share.toFixed(2) }}%</td>
                </tr>
              </tbody>
            </table>
            <p v-else class="hint">
              아직 집계된 placement 성과 데이터가 없습니다.
            </p>
          </div>
        </article>

        <article class="placement-card">
          <header class="section-head">
            <div>
              <p class="eyebrow">Insight</p>
              <h3>추천 인사이트</h3>
            </div>
          </header>

          <ul v-if="placementInsights.length" class="insight-list">
            <li v-for="(item, idx) in placementInsights" :key="idx">
              {{ item }}
            </li>
          </ul>
          <p v-else class="hint">추천 성과가 전반적으로 안정적인 수준입니다.</p>
        </article>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from "vue";
import * as echarts from "echarts/core";
import { LineChart } from "echarts/charts";
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  TitleComponent,
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import { adminAnalyticsAPI } from "@/services/api/analytics";
import type { AnalyticsOverview, Granularity } from "@/types/analytics";

echarts.use([
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
const dateRange = ref({ start: getDateNDaysAgo(13), end: getDateNDaysAgo(0) });
const segment = ref("all");
const dataMode = ref<"all" | "real">("all");
const includeTestData = ref(true);

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
const conversionChartRef = ref<HTMLDivElement | null>(null);
const gmvChartRef = ref<HTMLDivElement | null>(null);
const charts: Record<"ctr" | "conversion" | "gmv", echarts.ECharts | null> = {
  ctr: null,
  conversion: null,
  gmv: null,
};

const recoTrendsData = ref<Record<string, RecoPoint[]>>({
  all: [],
  price_model: [],
  personalized: [],
  gapfill: [],
});

type PlacementSummaryRow = {
  placement: string;
  impressions: number;
  clicks: number;
  attributed_orders: number;
  attributed_gmv: number;
  ctr: number;
  purchase_conversion: number;
  gmv_share: number;
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

const onDataModeChanged = () => {
  dataMode.value = includeTestData.value ? "all" : "real";
  loadData();
};

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

const placementSummary = ref<PlacementSummaryRow[]>([]);

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
    const baseParams = {
      start_date: dateRange.value.start,
      end_date: dateRange.value.end,
      granularity: granularity.value,
      segment: segment.value,
      data_mode: dataMode.value,
    };

    const [
      { data: overviewData },
      trendAll,
      trendPriceModel,
      trendPersonalized,
      trendGapfill,
      placementResponse,
    ] = await Promise.all([
      adminAnalyticsAPI.getOverview(baseParams),
      adminAnalyticsAPI.getRecommendationTrend({
        ...baseParams,
        placement: "all",
      }),
      adminAnalyticsAPI.getRecommendationTrend({
        ...baseParams,
        placement: "price_model",
      }),
      adminAnalyticsAPI.getRecommendationTrend({
        ...baseParams,
        placement: "personalized",
      }),
      adminAnalyticsAPI.getRecommendationTrend({
        ...baseParams,
        placement: "gapfill",
      }),
      adminAnalyticsAPI.getRecommendationPlacementSummary(baseParams),
    ]);

    overview.value = overviewData;

    // 모든 트렌드 데이터 저장
    recoTrendsData.value = {
      all: formatRecoSeries(trendAll.data.series ?? [], granularity.value),
      price_model: formatRecoSeries(
        trendPriceModel.data.series ?? [],
        granularity.value
      ),
      personalized: formatRecoSeries(
        trendPersonalized.data.series ?? [],
        granularity.value
      ),
      gapfill: formatRecoSeries(
        trendGapfill.data.series ?? [],
        granularity.value
      ),
    };

    updateCtrChart(recoTrendsData.value);
    updateConversionChart(recoTrendsData.value);
    updateGmvChart(recoTrendsData.value);
    placementSummary.value = placementResponse.data.placements ?? [];
  } catch (err: any) {
    // 조회 실패 시 에러 메시지와 함께 값 0으로 표시
    errorMessage.value =
      err?.response?.data?.detail ||
      "추천 지표를 불러오지 못했습니다. 잠시 후 다시 시도해주세요.";
    overview.value = null;
    recoTrendsData.value = {
      all: [],
      price_model: [],
      personalized: [],
      gapfill: [],
    };
    updateCtrChart(recoTrendsData.value);
    updateConversionChart(recoTrendsData.value);
    updateGmvChart(recoTrendsData.value);
    placementSummary.value = [];
  } finally {
    loading.value = false;
    lastUpdated.value = new Date().toLocaleString();
  }
};

const getChart = (
  key: "ctr" | "conversion" | "gmv",
  el: HTMLDivElement | null
) => {
  if (!el) return null;
  if (!charts[key]) {
    charts[key] = echarts.init(el);
  }
  return charts[key];
};

const updateCtrChart = (trendsData: Record<string, RecoPoint[]>) => {
  nextTick(() => {
    const chart = getChart("ctr", ctrChartRef.value);
    if (!chart) return;

    const dates = trendsData.all.map((p) => p.date);

    const option: echarts.EChartsCoreOption = {
      grid: { top: 32, left: 50, right: 50, bottom: 60 },
      tooltip: {
        trigger: "axis",
        valueFormatter: (value: number | string) =>
          typeof value === "number" ? `${value.toFixed(2)}%` : `${value}`,
      },
      legend: {
        data: [
          "전체 CTR",
          "Price Model CTR",
          "Personalized CTR",
          "GapFill CTR",
        ],
        bottom: 0,
        textStyle: { color: "#1f2933", fontSize: 11 },
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
          name: "전체 CTR",
          type: "line",
          smooth: true,
          data: trendsData.all.map((p) => p.ctr),
          lineStyle: { width: 3, color: "#2563eb" },
          itemStyle: { color: "#2563eb" },
        },
        {
          name: "Price Model CTR",
          type: "line",
          smooth: true,
          data: trendsData.price_model.map((p) => p.ctr),
          lineStyle: { width: 2, color: "#10b981" },
          itemStyle: { color: "#10b981" },
        },
        {
          name: "Personalized CTR",
          type: "line",
          smooth: true,
          data: trendsData.personalized.map((p) => p.ctr),
          lineStyle: { width: 2, color: "#f59e0b" },
          itemStyle: { color: "#f59e0b" },
        },
        {
          name: "GapFill CTR",
          type: "line",
          smooth: true,
          data: trendsData.gapfill.map((p) => p.ctr),
          lineStyle: { width: 2, color: "#8b5cf6" },
          itemStyle: { color: "#8b5cf6" },
        },
      ],
    };

    chart.setOption(option, true);
  });
};

const updateConversionChart = (trendsData: Record<string, RecoPoint[]>) => {
  nextTick(() => {
    const chart = getChart("conversion", conversionChartRef.value);
    if (!chart) return;

    const dates = trendsData.all.map((p) => p.date);

    const option: echarts.EChartsCoreOption = {
      grid: { top: 32, left: 50, right: 50, bottom: 60 },
      tooltip: {
        trigger: "axis",
        valueFormatter: (value: number | string) =>
          typeof value === "number" ? `${value.toFixed(2)}%` : `${value}`,
      },
      legend: {
        data: [
          "전체 구매 전환율",
          "Price Model 구매 전환율",
          "Personalized 구매 전환율",
          "GapFill 구매 전환율",
        ],
        bottom: 0,
        textStyle: { color: "#1f2933", fontSize: 11 },
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
          name: "전체 구매 전환율",
          type: "line",
          smooth: true,
          data: trendsData.all.map((p) => p.purchase_conversion),
          lineStyle: { width: 3, color: "#2563eb" },
          itemStyle: { color: "#2563eb" },
        },
        {
          name: "Price Model 구매 전환율",
          type: "line",
          smooth: true,
          data: trendsData.price_model.map((p) => p.purchase_conversion),
          lineStyle: { width: 2, color: "#10b981" },
          itemStyle: { color: "#10b981" },
        },
        {
          name: "Personalized 구매 전환율",
          type: "line",
          smooth: true,
          data: trendsData.personalized.map((p) => p.purchase_conversion),
          lineStyle: { width: 2, color: "#f59e0b" },
          itemStyle: { color: "#f59e0b" },
        },
        {
          name: "GapFill 구매 전환율",
          type: "line",
          smooth: true,
          data: trendsData.gapfill.map((p) => p.purchase_conversion),
          lineStyle: { width: 2, color: "#8b5cf6" },
          itemStyle: { color: "#8b5cf6" },
        },
      ],
    };

    chart.setOption(option, true);
  });
};

const updateGmvChart = (trendsData: Record<string, RecoPoint[]>) => {
  nextTick(() => {
    const chart = getChart("gmv", gmvChartRef.value);
    if (!chart) return;

    const dates = trendsData.all.map((p) => p.date);

    const option: echarts.EChartsCoreOption = {
      grid: { top: 32, left: 50, right: 50, bottom: 60 },
      tooltip: {
        trigger: "axis",
        valueFormatter: (value: number | string) =>
          typeof value === "number" ? `${value.toFixed(2)}%` : `${value}`,
      },
      legend: {
        data: ["전체 GMV 기여율", "Price Model", "Personalized", "GapFill"],
        bottom: 0,
        textStyle: { color: "#1f2933", fontSize: 11 },
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
          name: "전체 GMV 기여율",
          type: "line",
          smooth: true,
          data: trendsData.all.map((p) => p.gmv_share),
          lineStyle: { width: 3, color: "#2563eb" },
          itemStyle: { color: "#2563eb" },
          areaStyle: { color: "rgba(37, 99, 235, 0.1)" },
        },
        {
          name: "Price Model",
          type: "line",
          smooth: true,
          data: trendsData.price_model.map((p) => p.gmv_share),
          lineStyle: { width: 2, color: "#10b981" },
          itemStyle: { color: "#10b981" },
        },
        {
          name: "Personalized",
          type: "line",
          smooth: true,
          data: trendsData.personalized.map((p) => p.gmv_share),
          lineStyle: { width: 2, color: "#f59e0b" },
          itemStyle: { color: "#f59e0b" },
        },
        {
          name: "GapFill",
          type: "line",
          smooth: true,
          data: trendsData.gapfill.map((p) => p.gmv_share),
          lineStyle: { width: 2, color: "#8b5cf6" },
          itemStyle: { color: "#8b5cf6" },
        },
      ],
    };

    chart.setOption(option, true);
  });
};

const resetFilters = () => {
  granularity.value = "daily";
  dateRange.value = { start: getDateNDaysAgo(13), end: getDateNDaysAgo(0) };
  segment.value = "all";
  dataMode.value = "all";
  includeTestData.value = true;
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

const placementDisplayLabel = (placement: string) => {
  if (placement === "price_model") return "Price Log Model";
  if (placement === "personalized") return "Personalized Model";
  if (placement === "gapfill") return "Gap Filling Model";
  if (placement === "home") return "Home Recommendation";
  if (placement === "all") return "전체 Placement";
  return placement;
};

const sortedPlacementSummary = computed(() =>
  [...placementSummary.value].sort((a, b) => b.gmv_share - a.gmv_share)
);

const placementInsights = computed(() => {
  const rows = sortedPlacementSummary.value;
  const trendsData = recoTrendsData.value;

  if (!rows.length) return ["모든 추천 알고리즘이 안정적으로 작동 중입니다."];

  const insights: string[] = [];

  // === 1. 성과 기준 인사이트 ===

  // GMV 기준 최고 성과
  const topByGmv = rows[0];
  if (topByGmv && topByGmv.gmv_share > 0) {
    insights.push(
      `[성과] 기여 GMV 기준 최고 성과: "${placementDisplayLabel(
        topByGmv.placement
      )}" (${topByGmv.gmv_share.toFixed(1)}%)`
    );
  }

  // CTR 기준 최고 성과
  const sortedByCtr = [...rows].sort((a, b) => b.ctr - a.ctr);
  const topByCtr = sortedByCtr[0];
  if (
    topByCtr &&
    topByCtr.placement !== topByGmv.placement &&
    topByCtr.ctr > 0
  ) {
    insights.push(
      `[성과] CTR 최고: "${placementDisplayLabel(
        topByCtr.placement
      )}" (${topByCtr.ctr.toFixed(
        1
      )}%), 하지만 GMV 기여는 ${topByCtr.gmv_share.toFixed(
        1
      )}%로 상대적으로 낮음`
    );
  }

  // 전환율 기준 최저 성과
  const sortedByConv = [...rows].sort(
    (a, b) => a.purchase_conversion - b.purchase_conversion
  );
  const bottomByConv = sortedByConv[0];
  if (
    bottomByConv &&
    bottomByConv.purchase_conversion > 0 &&
    bottomByConv.placement !== "all"
  ) {
    insights.push(
      `[성과] 구매 전환율 최저: "${placementDisplayLabel(
        bottomByConv.placement
      )}" (${bottomByConv.purchase_conversion.toFixed(1)}%) - 개선 필요`
    );
  }

  // === 2. 트렌드 기준 인사이트 ===

  Object.entries(trendsData).forEach(([placement, series]) => {
    if (series.length < 3 || placement === "all") return;

    // 최근 3일 vs 초기 3일 비교
    const recentCtr = series.slice(-3).map((p) => p.ctr);
    const oldCtr = series.slice(0, 3).map((p) => p.ctr);

    const recentAvg = recentCtr.reduce((a, b) => a + b, 0) / recentCtr.length;
    const oldAvg = oldCtr.reduce((a, b) => a + b, 0) / oldCtr.length;

    const change = ((recentAvg - oldAvg) / Math.max(oldAvg, 0.01)) * 100;

    if (change > 20) {
      insights.push(
        `[추세] "${placementDisplayLabel(placement)}" CTR이 ${change.toFixed(
          0
        )}% 상승 중 (${oldAvg.toFixed(1)}% → ${recentAvg.toFixed(1)}%)`
      );
    } else if (change < -20) {
      insights.push(
        `[추세] "${placementDisplayLabel(placement)}" CTR이 ${Math.abs(
          change
        ).toFixed(0)}% 하락 중 (${oldAvg.toFixed(1)}% → ${recentAvg.toFixed(
          1
        )}%) - 원인 분석 필요`
      );
    }
  });

  // === 3. 임계값 기준 인사이트 ===

  rows.forEach((row) => {
    if (row.placement === "all") return;

    const label = placementDisplayLabel(row.placement);

    // CTR 임계값 (2%)
    if (row.ctr < 2.0 && row.ctr > 0) {
      insights.push(
        `[경고] "${label}" CTR이 ${row.ctr.toFixed(
          2
        )}%로 임계값(2%) 미만 - 즉시 점검 필요`
      );
    }

    // 전환율 임계값 (5%)
    if (row.purchase_conversion < 5.0 && row.purchase_conversion > 0) {
      insights.push(
        `[경고] "${label}" 구매 전환율이 ${row.purchase_conversion.toFixed(
          2
        )}%로 임계값(5%) 미만 - 추천 품질 개선 필요`
      );
    }

    // GMV 기여율 임계값 (1%)
    if (row.gmv_share < 1.0 && row.gmv_share > 0) {
      insights.push(
        `[경고] "${label}" GMV 기여율이 ${row.gmv_share.toFixed(
          2
        )}%로 매우 낮음 - 알고리즘 재검토 권장`
      );
    }
  });

  // === 4. 비교 기준 인사이트 ===

  const allPlacement = rows.find((r) => r.placement === "all");
  if (allPlacement) {
    const algorithms = rows.filter(
      (r) => r.placement !== "all" && r.placement !== "home"
    );

    // 높은 CTR, 낮은 전환율
    const highCtrLowConv = algorithms.find(
      (algo) =>
        algo.ctr > allPlacement.ctr * 1.1 &&
        algo.purchase_conversion < allPlacement.purchase_conversion * 0.8
    );

    if (highCtrLowConv) {
      insights.push(
        `[비교] "${placementDisplayLabel(
          highCtrLowConv.placement
        )}"는 CTR은 높지만(${highCtrLowConv.ctr.toFixed(
          1
        )}%) 전환율은 낮음(${highCtrLowConv.purchase_conversion.toFixed(
          1
        )}%) - 추천 품질 vs 클릭 유도성 균형 검토`
      );
    }

    // 전반적 저성과 알고리즘
    const underperformer = algorithms.find(
      (algo) =>
        algo.ctr < allPlacement.ctr * 0.7 &&
        algo.purchase_conversion < allPlacement.purchase_conversion * 0.7
    );

    if (underperformer) {
      insights.push(
        `[비교] "${placementDisplayLabel(
          underperformer.placement
        )}"가 전체 평균 대비 CTR/전환율 모두 저조 - 알고리즘 가중치 조정 또는 비활성화 검토`
      );
    }
  }

  // 빈 상태
  if (insights.length === 0) {
    return ["모든 추천 알고리즘이 안정적으로 작동 중입니다."];
  }

  // 우선순위 정렬: 경고 → 추세 → 비교 → 성과
  return insights.sort((a, b) => {
    const severityOrder: Record<string, number> = {
      "[경고]": 0,
      "[추세]": 1,
      "[비교]": 2,
      "[성과]": 3,
    };
    const aPrefix =
      (Object.keys(severityOrder).find((k) => a.startsWith(k)) as string) ||
      "[성과]";
    const bPrefix =
      (Object.keys(severityOrder).find((k) => b.startsWith(k)) as string) ||
      "[성과]";
    return severityOrder[aPrefix] - severityOrder[bPrefix];
  });
});

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

.charts-row {
  display: flex;
  gap: 16px;
  margin-top: 16px;
}

.chart-container.half-width {
  width: 50%;
  flex: 1;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 18px;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.05);
}

.chart-container.full-width {
  width: 100%;
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

.card-head h3 {
  font-size: 18px;
  font-weight: 800;
  color: #0f172a;
}

.trend-chart,
.placement-chart {
  width: 100%;
  height: 260px;
}

.placement-summary-grid {
  margin-top: 14px;
  display: grid;
  grid-template-columns: minmax(0, 1.6fr) minmax(0, 1.1fr);
  gap: 12px;
}

.placement-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 16px 16px 18px;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.05);
}

.table-wrapper {
  width: 100%;
  overflow-x: auto;
  margin-top: 8px;
}

.placement-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.placement-table th,
.placement-table td {
  padding: 8px 10px;
  border-bottom: 1px solid #e2e8f0;
  text-align: left;
  white-space: nowrap;
}

.placement-table thead th {
  background: #f8fafc;
  font-weight: 700;
  color: #475569;
}

.insight-list {
  margin: 10px 0 0 0;
  padding-left: 18px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 13px;
  color: #475569;
}
</style>
