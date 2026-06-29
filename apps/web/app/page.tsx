import { RankingBarChart, TrendLineChart } from "@/components/ChartPanels";
import { RankingTable } from "@/components/DataTable";
import { getOverview, getRankings, getTrends } from "@/lib/api";
import type { FactRow } from "@/lib/api";
import { formatValue, groupBy } from "@/lib/format";

export const dynamic = "force-dynamic";

const revenueMetric = "finance_total_revenues_from_continuing_operations_including_deferred_superannuation";
const trendMetric = "student_total_enrolments";

export default async function SectorOverviewPage() {
  const [overview, revenueRankings, enrolmentRows] = await Promise.all([
    getOverview(),
    getRankings(revenueMetric, "2024", "Total Institution", 10),
    getTrends(trendMetric, undefined, "Student")
  ]);
  const sectorTrend = aggregateSectorTrend(enrolmentRows);
  const grouped = groupBy(overview.top_rankings, (row) => row.metric_name);

  return (
    <div className="space-y-6">
      <section className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-normal">Sector overview</h1>
          <p className="mt-1 text-sm text-muted">Canonical facts loaded from official public data sources.</p>
        </div>
        <div className="grid grid-cols-2 gap-2 text-xs text-muted sm:grid-cols-4">
          <span className="rounded-md border border-line bg-white px-3 py-2">Providers {overview.summary.providers}</span>
          <span className="rounded-md border border-line bg-white px-3 py-2">Metrics {overview.summary.metrics}</span>
          <span className="rounded-md border border-line bg-white px-3 py-2">Facts {overview.summary.facts}</span>
          <span className="rounded-md border border-line bg-white px-3 py-2">Sources {overview.summary.sources}</span>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {overview.kpis.map((kpi) => (
          <div className="panel p-4" key={kpi.metric_id}>
            <div className="text-xs font-medium uppercase text-muted">{kpi.metric_name}</div>
            <div className="mt-2 text-2xl font-semibold">{formatValue(kpi.value, kpi.unit)}</div>
            <div className="mt-1 text-xs text-muted">{kpi.reporting_year} · {kpi.dimension_scope}</div>
          </div>
        ))}
      </section>

      <section className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
        <div className="panel p-4">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-base font-semibold">Top revenue providers</h2>
            <span className="text-xs text-muted">Finance 2024</span>
          </div>
          <RankingBarChart rows={revenueRankings} />
        </div>
        <div className="panel p-4">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-base font-semibold">Student enrolment trend</h2>
            <span className="text-xs text-muted">Public university sector</span>
          </div>
          <TrendLineChart rows={sectorTrend} />
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-3">
        {Object.entries(grouped).map(([metric, rows]) => (
          <div className="panel p-4" key={metric}>
            <h2 className="mb-3 text-base font-semibold">{metric}</h2>
            <RankingTable rows={rows} />
          </div>
        ))}
      </section>
    </div>
  );
}

function aggregateSectorTrend(rows: FactRow[]): FactRow[] {
  const byYear = new Map<number, FactRow>();

  for (const row of rows) {
    if (row.provider_id === "sector_all_pub2") continue;

    const existing = byYear.get(row.reporting_year);
    if (existing) {
      existing.value += row.value;
      continue;
    }

    byYear.set(row.reporting_year, {
      ...row,
      provider_id: "public_university_sector",
      provider_name: "Public university sector",
      value: row.value
    });
  }

  return Array.from(byYear.values()).sort((a, b) => a.reporting_year - b.reporting_year);
}
