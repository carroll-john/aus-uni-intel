import { RankingBarChart } from "@/components/ChartPanels";
import { RankingTable } from "@/components/DataTable";
import { getBenchmarks, getMetricCatalog, getMetrics, getProviders, getRankings } from "@/lib/api";
import type { Metric, MetricCatalogItem, Provider } from "@/lib/api";

export const dynamic = "force-dynamic";

const defaultMetric = "finance_total_revenues_from_continuing_operations_including_deferred_superannuation";

export default async function RankingsPage({
  searchParams
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const query = await searchParams;
  const catalogMode = one(query.catalog) === "raw" ? "raw" : "curated";
  const [metricRows, providers] = await Promise.all([
    catalogMode === "raw" ? getMetrics() : selectableCatalogItems(await getMetricCatalog()),
    getProviders()
  ]);
  const metrics = metricRows;
  const universities = providers.filter((provider) => provider.provider_type === "university");
  const missionGroups = distinct(universities.map((provider) => provider.mission_group));
  const states = distinct(universities.map((provider) => provider.state));

  const requestedMetricId = one(query.metric_id) ?? defaultMetric;
  const metricId = metrics.some((metric) => metric.metric_id === requestedMetricId) ? requestedMetricId : defaultMetric;
  const year = one(query.year) ?? "2024";
  const scope = one(query.scope);
  const missionGroup = pickOption(one(query.mission_group), missionGroups);
  const state = pickOption(one(query.state), states);

  const rows = await getRankings(metricId, year, scope, 50, { missionGroup, state });
  const selected = metrics.find((metric) => metric.metric_id === metricId);

  const benchmark = missionGroup
    ? await getBenchmarks(metricId, { year, scope, groupBy: "mission_group", missionGroup })
        .then((response) => response.rows.find((row) => row.group_value === missionGroup))
        .catch(() => undefined)
    : undefined;
  const benchmarkLine =
    benchmark && benchmark.provider_count > 0
      ? { value: benchmark.average, label: `${missionGroup} avg (${benchmark.provider_count})` }
      : undefined;

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-semibold">Rankings</h1>
        <p className="mt-1 text-sm text-muted">
          Provider rankings from canonical facts. Filter by mission group or state to rank within a peer set.
        </p>
      </div>
      <form className="panel grid gap-3 p-4 md:grid-cols-[1fr_120px_180px_160px_110px_auto]">
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
        <select className="rounded-md border border-line px-3 py-2 text-sm" defaultValue={missionGroup ?? ""} name="mission_group">
          <option value="">All groups</option>
          {missionGroups.map((group) => (
            <option key={group} value={group}>
              {group}
            </option>
          ))}
        </select>
        <select className="rounded-md border border-line px-3 py-2 text-sm" defaultValue={state ?? ""} name="state">
          <option value="">All states</option>
          {states.map((value) => (
            <option key={value} value={value}>
              {value}
            </option>
          ))}
        </select>
        <input className="rounded-md border border-line px-3 py-2 text-sm" defaultValue={year} name="year" placeholder="Year" />
        <input className="rounded-md border border-line px-3 py-2 text-sm" defaultValue={scope ?? ""} name="scope" placeholder="Scope" />
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
          {benchmarkLine ? <span> · Dashed line shows the {benchmarkLine.label} for this metric and year.</span> : null}
        </div>
      ) : null}
      <section className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
        <div className="panel p-4">
          <RankingBarChart rows={rows} benchmark={benchmarkLine} />
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

function pickOption(value: string | undefined, allowed: string[]) {
  return value && allowed.includes(value) ? value : undefined;
}

function distinct(values: Array<string | null>) {
  return Array.from(new Set(values.filter((value): value is string => Boolean(value)))).sort();
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
