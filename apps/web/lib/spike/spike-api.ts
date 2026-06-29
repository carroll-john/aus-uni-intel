import type { BenchmarkResponse, FactRow } from "@/lib/api";
import { getBenchmarks, getRankings, getTrends } from "@/lib/api";
import type { ChartType, InsightCatalogueEntry, SelectedInsight } from "./types";

const API_BASE_URL = process.env.API_BASE_URL || process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";
const DEFAULT_YEAR = "2024";

export type DataFetchResult = {
  chart: ChartType;
  rows: FactRow[];
  benchmark?: { value: number; label: string };
  headline?: { value: number | null; subtitle: string };
  dataSource: "live_api" | "mock_fallback";
};

export async function fetchInsightData(
  entry: InsightCatalogueEntry,
  selection: SelectedInsight
): Promise<DataFetchResult> {
  const year = selection.year ? String(selection.year) : DEFAULT_YEAR;
  const scope = selection.scope ?? entry.scope;

  try {
    if (selection.chart === "metric_card") {
      const rows = await getRankings(entry.metricId, year, scope, 1);
      return {
        chart: selection.chart,
        rows,
        headline: {
          value: rows[0]?.value ?? null,
          subtitle: rows[0]?.provider_name ? `Top provider: ${rows[0].provider_name} (${year})` : `Latest available (${year})`
        },
        dataSource: "live_api"
      };
    }

    if (selection.breakdown === "time" || selection.chart === "trend_line" || selection.chart === "multi_trend") {
      const rows = await getTrends(entry.metricId, undefined, scope);
      return { chart: selection.chart, rows, dataSource: "live_api" };
    }

    if (selection.breakdown === "mission_group" || selection.breakdown === "state" || selection.chart === "benchmark_bar") {
      const groupBy = selection.breakdown === "state" ? "state" : "mission_group";
      const response: BenchmarkResponse = await getBenchmarks(entry.metricId, { year, scope, groupBy });
      const rows = response.rows.map(
        (row) =>
          ({
            provider_id: row.group_value,
            provider_name: row.group_value,
            metric_id: entry.metricId,
            metric_name: entry.name,
            reporting_year: row.reporting_year,
            dimension_scope: scope,
            value: row.average,
            unit: row.unit
          }) satisfies FactRow
      );
      return { chart: selection.chart, rows, dataSource: "live_api" };
    }

    const rows = await getRankings(entry.metricId, year, scope, 25);
    return { chart: selection.chart, rows, dataSource: "live_api" };
  } catch (error) {
    console.error(`[spike] API fetch failed for ${entry.id}:`, error);
    return { chart: selection.chart, rows: mockRows(entry, selection), dataSource: "mock_fallback" };
  }
}

function mockRows(entry: InsightCatalogueEntry, selection: SelectedInsight): FactRow[] {
  const year = selection.year ?? 2024;
  if (selection.breakdown === "time") {
    return [2020, 2021, 2022, 2023, 2024].map((y) => ({
      metric_id: entry.metricId,
      metric_name: entry.name,
      reporting_year: y,
      dimension_scope: entry.scope,
      value: 1000 + y * 10,
      unit: entry.unit
    }));
  }
  return [
    { provider_id: "university_of_sydney", provider_name: "University of Sydney", metric_id: entry.metricId, metric_name: entry.name, reporting_year: year, dimension_scope: entry.scope, value: 1200, unit: entry.unit },
    { provider_id: "university_of_melbourne", provider_name: "University of Melbourne", metric_id: entry.metricId, metric_name: entry.name, reporting_year: year, dimension_scope: entry.scope, value: 1100, unit: entry.unit },
    { provider_id: "university_of_queensland", provider_name: "University of Queensland", metric_id: entry.metricId, metric_name: entry.name, reporting_year: year, dimension_scope: entry.scope, value: 950, unit: entry.unit }
  ];
}

export function apiBaseUrl() {
  return API_BASE_URL;
}
