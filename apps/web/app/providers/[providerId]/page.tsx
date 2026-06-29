import { RankingTable } from "@/components/DataTable";
import { TrendLineChart } from "@/components/ChartPanels";
import { getMetricCatalog, getProfile, getRankings, getTrends } from "@/lib/api";
import type { FactRow, MetricCatalogItem } from "@/lib/api";
import { formatValue, groupBy } from "@/lib/format";

export const dynamic = "force-dynamic";

const profileTrendMetric = "student_total_enrolments";

export default async function ProviderProfilePage({ params }: { params: Promise<{ providerId: string }> }) {
  const { providerId } = await params;
  const [profile, catalog, trend, revenuePeers] = await Promise.all([
    getProfile(providerId),
    getMetricCatalog(),
    getTrends(profileTrendMetric, providerId, "Student"),
    getRankings(
      "finance_total_revenues_from_continuing_operations_including_deferred_superannuation",
      "2024",
      "Total Institution",
      8
    )
  ]);
  const latestYear = Math.max(...profile.facts.map((fact) => fact.reporting_year));
  const latestFacts = curatedLatestFacts(profile.facts, catalog, latestYear);
  const grouped = groupBy(latestFacts, (fact) => fact.metric_group ?? "Metrics");

  return (
    <div className="space-y-6">
      <section className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">{profile.provider.provider_name}</h1>
          <p className="mt-1 text-sm text-muted">{profile.provider.state} · Public university profile</p>
        </div>
        <a className="rounded-md border border-line bg-white px-3 py-2 text-sm" href={profile.provider.website ?? "#"}>
          Provider website
        </a>
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {summaryFacts(latestFacts).map((fact) => (
          <div className="panel p-4" key={fact.metric_id}>
            <div className="text-xs font-medium uppercase text-muted">{fact.metric_name}</div>
            <div className="mt-2 text-2xl font-semibold">{formatValue(fact.value, fact.unit)}</div>
            <div className="mt-1 text-xs text-muted">{fact.reporting_year} · {fact.dimension_scope}</div>
          </div>
        ))}
      </section>

      <section className="grid gap-4 xl:grid-cols-[1fr_1fr]">
        <div className="panel min-w-0 p-4">
          <h2 className="mb-3 text-base font-semibold">Student trend</h2>
          <TrendLineChart rows={trend} />
        </div>
        <div className="panel min-w-0 p-4">
          <h2 className="mb-3 text-base font-semibold">Revenue peer ranking</h2>
          <RankingTable rows={revenuePeers} />
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-2">
        {Object.entries(grouped).map(([group, facts]) => (
          <div className="panel min-w-0 p-4" key={group}>
            <h2 className="mb-3 text-base font-semibold">{group}</h2>
            <div className="space-y-2">
              {facts.map((fact) => (
                <div className="flex items-center justify-between gap-4 border-t border-line pt-2 text-sm" key={fact.metric_id}>
                  <span className="text-muted">{fact.metric_name}</span>
                  <span className="font-medium tabular-nums">{formatValue(fact.value, fact.unit)}</span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </section>
    </div>
  );
}

function curatedLatestFacts(facts: FactRow[], catalog: MetricCatalogItem[], latestYear: number) {
  const latestFacts = facts.filter((fact) => fact.reporting_year === latestYear);
  const rows: FactRow[] = [];

  for (const item of catalog) {
    if (!item.metric_id || !item.selectable) continue;
    const matches = latestFacts.filter((fact) => fact.metric_id === item.metric_id);
    if (!matches.length) continue;
    const preferred = item.preferred_scope ? matches.find((fact) => fact.dimension_scope === item.preferred_scope) : undefined;
    const selected = preferred ?? pickCanonicalFact(matches);
    rows.push({
      ...selected,
      metric_name: item.metric_name,
      metric_group: item.catalog_group
    });
  }

  return rows;
}

function pickCanonicalFact(matches: FactRow[]) {
  const preferredScopeOrder = ["Total Institution", "Student", "HERDC", "QILT undergraduate", "Calculated"];
  return [...matches].sort((a, b) => {
    const scopeDelta = scopeRank(a.dimension_scope, preferredScopeOrder) - scopeRank(b.dimension_scope, preferredScopeOrder);
    if (scopeDelta !== 0) return scopeDelta;
    return Math.abs(b.value) - Math.abs(a.value);
  })[0];
}

function scopeRank(scope: string, preferredScopeOrder: string[]) {
  const index = preferredScopeOrder.indexOf(scope);
  return index === -1 ? preferredScopeOrder.length : index;
}

function summaryFacts(facts: FactRow[]) {
  const summaryMetricIds = [
    "finance_total_revenues_from_continuing_operations_including_deferred_superannuation",
    "student_total_enrolments",
    "herdc_research_income_total",
    "qilt_overall_educational_experience_positive_rating"
  ];
  const byMetricId = new Map(facts.map((fact) => [fact.metric_id, fact]));
  return summaryMetricIds.map((metricId) => byMetricId.get(metricId)).filter((fact): fact is FactRow => Boolean(fact));
}
