import { RankingBarChart } from "@/components/ChartPanels";
import { RankingTable } from "@/components/DataTable";
import { getMetricCatalog, getMetrics, getRankings } from "@/lib/api";
import type { Metric, MetricCatalogItem } from "@/lib/api";

export const dynamic = "force-dynamic";

const defaultMetric = "finance_total_revenues_from_continuing_operations_including_deferred_superannuation";

export default async function RankingsPage({
  searchParams
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const query = await searchParams;
  const catalogMode = one(query.catalog) === "raw" ? "raw" : "curated";
  const metrics = catalogMode === "raw" ? await getMetrics() : selectableCatalogItems(await getMetricCatalog());
  const requestedMetricId = one(query.metric_id) ?? defaultMetric;
  const metricId = metrics.some((metric) => metric.metric_id === requestedMetricId) ? requestedMetricId : defaultMetric;
  const year = one(query.year) ?? "2024";
  const scope = one(query.scope);
  const rows = await getRankings(metricId, year, scope, 50);
  const selected = metrics.find((metric) => metric.metric_id === metricId);

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-semibold">Rankings</h1>
        <p className="mt-1 text-sm text-muted">Provider rankings from canonical facts.</p>
      </div>
      <form className="panel grid gap-3 p-4 md:grid-cols-[1fr_140px_220px_auto]">
        {catalogMode === "raw" ? <input name="catalog" type="hidden" value="raw" /> : null}
        <select className="rounded-md border border-line px-3 py-2 text-sm" defaultValue={metricId} name="metric_id">
          {groupMetrics(metrics).map(([group, groupedMetrics]) => (
            <optgroup key={group} label={group}>
              {groupedMetrics.map((metric) => (
                <option key={metric.metric_id} value={metric.metric_id}>
                  {metric.metric_name}
                </option>
              ))}
            </optgroup>
          ))}
        </select>
        <input className="rounded-md border border-line px-3 py-2 text-sm" defaultValue={year} name="year" />
        <input className="rounded-md border border-line px-3 py-2 text-sm" defaultValue={scope ?? ""} name="scope" placeholder="Scope optional" />
        <button className="rounded-md bg-teal px-4 py-2 text-sm font-semibold text-white">Apply</button>
      </form>
      <div className="flex justify-end">
        <a className="text-sm font-medium text-teal hover:underline" href={catalogMode === "raw" ? "/rankings" : "/rankings?catalog=raw"}>
          {catalogMode === "raw" ? "Use curated metrics" : "Advanced raw metrics"}
        </a>
      </div>
      {selected ? (
        <div className="panel p-4 text-sm text-muted">
          <span className="font-medium text-ink">{selected.metric_name}</span> · {selected.definition}
          {selected.calculation_method ? <span> Calculation: {selected.calculation_method}</span> : null}
        </div>
      ) : null}
      <section className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
        <div className="panel p-4">
          <RankingBarChart rows={rows} />
        </div>
        <div className="panel p-4">
          <RankingTable rows={rows} />
        </div>
      </section>
    </div>
  );
}

function one(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

type SelectableMetric = Metric | (MetricCatalogItem & { metric_id: string });

function selectableCatalogItems(metrics: MetricCatalogItem[]): Array<MetricCatalogItem & { metric_id: string }> {
  return metrics.filter((metric): metric is MetricCatalogItem & { metric_id: string } => Boolean(metric.metric_id && metric.selectable));
}

function groupMetrics(metrics: SelectableMetric[]) {
  const groups = new Map<string, SelectableMetric[]>();
  for (const metric of metrics) {
    const group = "catalog_group" in metric ? metric.catalog_group : metric.metric_group;
    groups.set(group, [...(groups.get(group) ?? []), metric]);
  }
  return [...groups.entries()];
}
