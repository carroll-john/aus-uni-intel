import { CompareBarChart, MultiProviderTrendChart } from "@/components/ChartPanels";
import { CompareControls } from "@/components/CompareControls";
import type { SelectableMetric } from "@/components/CompareControls";
import { getCompare, getMetricCatalog, getMetrics, getProviders, getTrends } from "@/lib/api";
import { formatValue } from "@/lib/format";

export const dynamic = "force-dynamic";

const defaultProviders = ["university_of_sydney", "university_of_melbourne", "monash_university"];
const defaultMetric = "finance_total_revenues_from_continuing_operations_including_deferred_superannuation";

export default async function ComparePage({
  searchParams
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const query = await searchParams;
  const catalogMode = one(query.catalog) === "raw" ? "raw" : "curated";
  const [providers, metricRows] = await Promise.all([
    getProviders(),
    catalogMode === "raw" ? getMetrics() : getMetricCatalog()
  ]);
  const metrics = selectableMetrics(metricRows);
  const selectedProviders = many(query.providers, defaultProviders).slice(0, 5);
  const requestedMetric = many(query.metrics, [defaultMetric])[0] ?? defaultMetric;
  const selectedMetric = metrics.some((metric) => metric.metric_id === requestedMetric) ? requestedMetric : defaultMetric;
  const year = one(query.year) ?? "2024";
  const [rows, trendGroups] = await Promise.all([
    getCompare(selectedProviders, [selectedMetric], year),
    Promise.all(selectedProviders.map((providerId) => getTrends(selectedMetric, providerId)))
  ]);
  const trendRows = trendGroups.flat();

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-semibold">Compare</h1>
        <p className="mt-1 text-sm text-muted">Compare multiple providers for one metric and reporting year.</p>
      </div>
      <CompareControls
        metrics={metrics}
        catalogMode={catalogMode}
        providers={providers.filter((provider) => provider.provider_type === "university")}
        selectedMetricId={selectedMetric}
        selectedProviderIds={selectedProviders}
        year={year}
      />
      <section className="panel p-4">
        <div className="mb-3 flex flex-col gap-1 sm:flex-row sm:items-baseline sm:justify-between">
          <h2 className="text-base font-semibold">Metric history</h2>
          <p className="text-sm text-muted">Available source years for the selected providers and metric.</p>
        </div>
        <MultiProviderTrendChart rows={trendRows} />
      </section>
      <section className="grid gap-4 xl:grid-cols-[1fr_1fr]">
        <div className="panel p-4">
          <div className="mb-3 flex items-baseline justify-between gap-3">
            <h2 className="text-base font-semibold">{year} comparison</h2>
            <p className="text-sm text-muted">Canonical scope per provider</p>
          </div>
          <CompareBarChart rows={rows} />
        </div>
        <div className="panel overflow-hidden">
          <table className="w-full border-collapse text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase text-muted">
              <tr>
                <th className="px-3 py-2">Provider</th>
                <th className="px-3 py-2">Metric</th>
                <th className="px-3 py-2 text-right">Value</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr className="border-t border-line" key={`${row.provider_id}-${row.metric_id}-${row.dimension_scope}`}>
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

function one(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

function many(value: string | string[] | undefined, fallback: string[]) {
  if (Array.isArray(value)) return value.flatMap((item) => item.split(",")).filter(Boolean);
  if (value) return value.split(",").filter(Boolean);
  return fallback;
}

function selectableMetrics(metrics: Awaited<ReturnType<typeof getMetrics>> | Awaited<ReturnType<typeof getMetricCatalog>>): SelectableMetric[] {
  return metrics.filter((metric): metric is SelectableMetric => Boolean(metric.metric_id && ("selectable" in metric ? metric.selectable : true)));
}
