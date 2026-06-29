import { RankingBarChart, TrendLineChart } from "@/components/ChartPanels";
import { RankingTable } from "@/components/DataTable";
import { getOverview, getRankings, getTrends } from "@/lib/api";
import type { FactRow } from "@/lib/api";
import { formatValue, groupBy } from "@/lib/format";
import Link from "next/link";

export const dynamic = "force-dynamic";

const kpiDisplay: Record<string, { label: string; order: number }> = {
  finance_total_revenues_from_continuing_operations_including_deferred_superannuation: {
    label: "Total revenue (continuing operations) $",
    order: 1
  },
  student_total_enrolments: {
    label: "Total enrolments",
    order: 2
  },
  herdc_research_income_total: {
    label: "HERDC research income (Cat 1-4) $",
    order: 3
  },
  qilt_overall_educational_experience_positive_rating: {
    label: "Overall educational experience positive rating",
    order: 4
  }
};

export default async function SectorOverviewPage({
  searchParams
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const query = await searchParams;
  const overview = await getOverview();
  const kpis = orderedKpis(overview.kpis);
  const selectedKpi = selectedKpiFromQuery(kpis, query.metric_id);
  const selectedScope = selectedKpi.dimension_scope;
  const [selectedRankings, selectedTrendRows] = await Promise.all([
    getRankings(selectedKpi.metric_id, String(selectedKpi.reporting_year), selectedScope, 10),
    getTrends(selectedKpi.metric_id, undefined, selectedScope)
  ]);
  const selectedTrend = aggregateSectorTrend(selectedTrendRows, selectedKpi.unit);
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
        {kpis.map((kpi) => (
          <KpiLink fact={kpi} href={`/?metric_id=${encodeURIComponent(kpi.metric_id)}`} isActive={kpi.metric_id === selectedKpi.metric_id} key={kpi.metric_id} />
        ))}
      </section>

      <section className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
        <div className="panel min-w-0 p-4">
          <div className="mb-3 flex flex-col gap-1 sm:flex-row sm:items-baseline sm:justify-between">
            <h2 className="text-base font-semibold">Top providers by {selectedKpi.metric_name.toLowerCase()}</h2>
            <span className="text-xs text-muted">{selectedKpi.reporting_year} · {selectedScope}</span>
          </div>
          <RankingBarChart rows={selectedRankings} />
        </div>
        <div className="panel min-w-0 p-4">
          <div className="mb-3 flex flex-col gap-1 sm:flex-row sm:items-baseline sm:justify-between">
            <h2 className="text-base font-semibold">{selectedKpi.metric_name} trend</h2>
            <span className="text-xs text-muted">Public university sector</span>
          </div>
          <TrendLineChart rows={selectedTrend} />
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-3">
        {Object.entries(grouped).map(([metric, rows]) => (
          <div className="panel min-w-0 p-4" key={metric}>
            <h2 className="mb-3 text-base font-semibold">{metric}</h2>
            <RankingTable rows={rows} showMetric={false} />
          </div>
        ))}
      </section>
    </div>
  );
}

function KpiLink({ fact, href, isActive }: { fact: FactRow; href: string; isActive: boolean }) {
  return (
    <Link
      aria-current={isActive ? "true" : undefined}
      className={`panel block p-4 transition hover:-translate-y-0.5 hover:border-teal hover:shadow-md focus:outline-none focus:ring-2 focus:ring-teal ${
        isActive ? "border-teal bg-teal/5" : ""
      }`}
      href={href}
    >
      <div className="text-xs font-medium uppercase text-muted">{fact.metric_name}</div>
      <div className="mt-2 text-2xl font-semibold">{formatValue(fact.value, fact.unit)}</div>
      <div className="mt-1 text-xs text-muted">{fact.reporting_year} · {fact.dimension_scope}</div>
    </Link>
  );
}

function selectedKpiFromQuery(kpis: FactRow[], metricId: string | string[] | undefined) {
  const selectedMetricId = Array.isArray(metricId) ? metricId[0] : metricId;
  return kpis.find((kpi) => kpi.metric_id === selectedMetricId) ?? kpis[0];
}

function orderedKpis(kpis: FactRow[]) {
  return [...kpis]
    .map((kpi) => ({
      ...kpi,
      metric_name: kpiDisplay[kpi.metric_id]?.label ?? kpi.metric_name
    }))
    .sort((a, b) => (kpiDisplay[a.metric_id]?.order ?? 99) - (kpiDisplay[b.metric_id]?.order ?? 99));
}

function aggregateSectorTrend(rows: FactRow[], unit?: string): FactRow[] {
  const recentRows = rows.filter((row) => row.reporting_year >= 2018);
  const sectorRows = recentRows.filter((row) => row.provider_id === "sector_all_pub2");
  const byYear = new Map<number, { count: number; row: FactRow }>();

  for (const row of recentRows) {
    if (row.provider_id === "sector_all_pub2") continue;
    const existing = byYear.get(row.reporting_year);
    if (existing) {
      existing.count += 1;
      existing.row.value += row.value;
      continue;
    }

    byYear.set(row.reporting_year, {
      count: 1,
      row: {
        ...row,
        provider_id: "public_university_sector",
        provider_name: "Public university sector",
        value: row.value
      }
    });
  }

  const aggregatedRows = Array.from(byYear.values())
    .map(({ count, row }) => ({
      ...row,
      value: unit === "percent" && count ? row.value / count : row.value
    }));

  const sectorByYear = new Map(sectorRows.map((row) => [row.reporting_year, row]));
  return aggregatedRows
    .map((row) => (unit === "percent" ? row : sectorByYear.get(row.reporting_year) ?? row))
    .sort((a, b) => a.reporting_year - b.reporting_year);
}
