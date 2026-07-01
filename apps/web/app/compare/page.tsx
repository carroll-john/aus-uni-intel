import { CompareBarChart, MultiProviderTrendChart } from "@/components/ChartPanels";
import { CompareControls } from "@/components/CompareControls";
import type { SelectableMetric } from "@/components/CompareControls";
import {
  getBenchmarks,
  getCompare,
  getMetricCatalog,
  getMetrics,
  getProviders,
  getTrends,
} from "@/lib/api";
import type { BenchmarkRow, FactRow } from "@/lib/api";
import { formatValue } from "@/lib/format";

export const dynamic = "force-dynamic";

const defaultProviders = ["university_of_sydney", "university_of_melbourne", "monash_university"];
const defaultMetric =
  "finance_total_revenues_from_continuing_operations_including_deferred_superannuation";
const benchmarkKeyPrefix = "benchmark:";

export default async function ComparePage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const query = await searchParams;
  const catalogMode = one(query.catalog) === "raw" ? "raw" : "curated";
  const [providers, metricRows] = await Promise.all([
    getProviders(),
    catalogMode === "raw" ? getMetrics() : getMetricCatalog(),
  ]);
  const metrics = selectableMetrics(metricRows);
  const universities = providers.filter((provider) => provider.provider_type === "university");
  const missionGroups = new Set(
    universities.map((provider) => provider.mission_group).filter(Boolean) as string[]
  );
  const selectedProviders = many(query.providers, defaultProviders).slice(0, 5);
  const requestedMetric = many(query.metrics, [defaultMetric])[0] ?? defaultMetric;
  const selectedMetric = metrics.some((metric) => metric.metric_id === requestedMetric)
    ? requestedMetric
    : defaultMetric;
  const year = one(query.year) ?? "2024";
  const benchmarkGroup = missionGroups.has(one(query.benchmark) ?? "")
    ? (one(query.benchmark) as string)
    : "";

  const [rows, trendGroups, benchmarkResult] = await Promise.all([
    getCompare(selectedProviders, [selectedMetric], year),
    Promise.all(selectedProviders.map((providerId) => getTrends(selectedMetric, providerId))),
    benchmarkGroup
      ? getBenchmarks(selectedMetric, { groupBy: "mission_group", missionGroup: benchmarkGroup })
          .then((data) => ({ data, error: false as const }))
          .catch((error) => {
            if (process.env.NODE_ENV !== "production") {
              console.error(error);
            }
            return { data: undefined, error: true as const };
          })
      : Promise.resolve({ data: undefined, error: false as const }),
  ]);
  const trendRows = trendGroups.flat();
  const benchmark = benchmarkResult.data;
  const benchmarkUnavailable = benchmarkResult.error;

  const benchmarkRows = benchmark?.rows ?? [];
  const benchmarkBar = benchmarkRows.find((row) => String(row.reporting_year) === year);
  const compareRows = benchmarkBar ? [...rows, benchmarkFact(benchmarkGroup, benchmarkBar)] : rows;
  const trendWithBenchmark = benchmarkRows.length
    ? [...trendRows, ...benchmarkRows.map((row) => benchmarkFact(benchmarkGroup, row))]
    : trendRows;

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-semibold">Compare</h1>
        <p className="mt-1 text-sm text-muted">
          Compare multiple providers for one metric and reporting year. Filter the picker by mission
          group or state, and overlay a peer-group average as a benchmark.
        </p>
      </div>
      <CompareControls
        metrics={metrics}
        catalogMode={catalogMode}
        providers={universities}
        selectedMetricId={selectedMetric}
        selectedProviderIds={selectedProviders}
        selectedBenchmark={benchmarkGroup}
        year={year}
      />
      {benchmarkUnavailable ? (
        <p className="text-sm text-amber">Benchmark unavailable for the selected peer group.</p>
      ) : null}
      <section className="panel p-4">
        <div className="mb-3 flex flex-col gap-1 sm:flex-row sm:items-baseline sm:justify-between">
          <h2 className="text-base font-semibold">Metric history</h2>
          <p className="text-sm text-muted">
            {benchmarkGroup
              ? `Dashed grey line: ${benchmarkGroup} average.`
              : "Available source years for the selected providers and metric."}
          </p>
        </div>
        <MultiProviderTrendChart rows={trendWithBenchmark} />
      </section>
      <section className="grid gap-4 xl:grid-cols-[1fr_1fr]">
        <div className="panel p-4">
          <div className="mb-3 flex items-baseline justify-between gap-3">
            <h2 className="text-base font-semibold">{year} comparison</h2>
            <p className="text-sm text-muted">Canonical scope per provider</p>
          </div>
          <CompareBarChart rows={compareRows} />
        </div>
        <div className="panel overflow-hidden">
          <table className="w-full border-collapse text-left text-sm">
            <thead className="bg-cream/60 text-xs uppercase text-muted">
              <tr>
                <th className="px-3 py-2">Provider</th>
                <th className="px-3 py-2">Metric</th>
                <th className="px-3 py-2 text-right">Value</th>
              </tr>
            </thead>
            <tbody>
              {compareRows.map((row) => (
                <tr
                  className="border-t border-line"
                  key={`${row.provider_id}-${row.metric_id}-${row.dimension_scope}`}
                >
                  <td className="px-3 py-2 font-medium">{row.provider_name}</td>
                  <td className="px-3 py-2 text-muted">{row.metric_name}</td>
                  <td className="px-3 py-2 text-right">{formatValue(row.value, row.unit)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function benchmarkFact(group: string, row: BenchmarkRow): FactRow {
  return {
    provider_id: `${benchmarkKeyPrefix}${group}`,
    provider_name: `${group} average`,
    metric_id: "benchmark",
    metric_name: `${group} average`,
    reporting_year: row.reporting_year,
    dimension_scope: "Group average",
    value: row.average,
    unit: row.unit,
  };
}

function one(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

function many(value: string | string[] | undefined, fallback: string[]) {
  if (Array.isArray(value)) return value.flatMap((item) => item.split(",")).filter(Boolean);
  if (value) return value.split(",").filter(Boolean);
  return fallback;
}

function selectableMetrics(
  metrics: Awaited<ReturnType<typeof getMetrics>> | Awaited<ReturnType<typeof getMetricCatalog>>
): SelectableMetric[] {
  return metrics.filter((metric): metric is SelectableMetric =>
    Boolean(metric.metric_id && ("selectable" in metric ? metric.selectable : true))
  );
}
