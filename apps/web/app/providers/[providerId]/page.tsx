import { RankingTable } from "@/components/DataTable";
import { TrendLineChart } from "@/components/ChartPanels";
import { getMetricCatalog, getMetricInsight, getProfile, getRankings, getTrends, ApiError } from "@/lib/api";
import type { FactRow, MetricCatalogItem, MetricInsight, MetricInsightRank, Provider } from "@/lib/api";
import type { ReactNode } from "react";
import { formatValue, groupBy } from "@/lib/format";
import Link from "next/link";
import { notFound } from "next/navigation";
import { SafeExternalLink } from "@/components/SafeExternalLink";

export const dynamic = "force-dynamic";

export default async function ProviderProfilePage({
  params,
  searchParams
}: {
  params: Promise<{ providerId: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const { providerId } = await params;
  const query = await searchParams;
  let profile;
  let catalog;
  try {
    [profile, catalog] = await Promise.all([getProfile(providerId), getMetricCatalog()]);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      notFound();
    }
    throw error;
  }
  const hasFacts = profile.facts.length > 0;
  const latestYear = hasFacts ? Math.max(...profile.facts.map((fact) => fact.reporting_year)) : 0;
  const latestFacts = hasFacts ? curatedLatestFacts(profile.facts, catalog, latestYear) : [];
  const kpiFacts = summaryFacts(latestFacts);
  const selectedFact = selectedFactFromQuery(kpiFacts, query.metric_id);

  if (!selectedFact) {
    return (
      <div className="space-y-6">
        <ProviderHeader provider={profile.provider} />
        <section className="panel p-6">
          <h2 className="text-base font-semibold">No metrics available</h2>
          <p className="mt-2 text-sm text-muted">
            This provider has no curated metrics in the warehouse yet. Check back after the next data ingestion run.
          </p>
        </section>
      </div>
    );
  }

  const [insight, trend, peerRankings] = await Promise.all([
    getMetricInsight(selectedFact.provider_id ?? providerId, selectedFact.metric_id, String(selectedFact.reporting_year), selectedFact.dimension_scope),
    getTrends(selectedFact.metric_id, providerId, selectedFact.dimension_scope),
    getRankings(selectedFact.metric_id, String(selectedFact.reporting_year), selectedFact.dimension_scope, 8)
  ]);
  const grouped = groupBy(latestFacts, (fact) => fact.metric_group ?? "Metrics");

  return (
    <div className="space-y-6">
      <ProviderHeader provider={profile.provider} />

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {kpiFacts.map((fact) => (
          <KpiLink
            fact={fact}
            href={`/providers/${providerId}?metric_id=${encodeURIComponent(fact.metric_id)}`}
            isActive={fact.metric_id === selectedFact.metric_id}
            key={fact.metric_id}
          />
        ))}
      </section>

      <MetricInsightPanel insight={insight} />

      <section className="grid gap-4 xl:grid-cols-[1fr_1fr]">
        <div className="panel min-w-0 p-4">
          <div className="mb-3 flex flex-col gap-1 sm:flex-row sm:items-baseline sm:justify-between">
            <h2 className="text-base font-semibold">{selectedFact.metric_name} trend</h2>
            <span className="text-xs text-muted">{profile.provider.provider_name}</span>
          </div>
          <TrendLineChart rows={trend.filter((row) => row.reporting_year >= 2018)} />
        </div>
        <div className="panel min-w-0 p-4">
          <div className="mb-3 flex flex-col gap-1 sm:flex-row sm:items-baseline sm:justify-between">
            <h2 className="text-base font-semibold">Top providers by {selectedFact.metric_name.toLowerCase()}</h2>
            <span className="text-xs text-muted">{selectedFact.reporting_year} · {selectedFact.dimension_scope}</span>
          </div>
          <RankingTable rows={peerRankings} showMetric={false} />
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

function MetricInsightPanel({ insight }: { insight: MetricInsight }) {
  const missionLabel = insight.ranks.mission_group?.label ?? insight.provider.mission_group;
  const stateLabel = insight.ranks.state?.label ?? insight.provider.state;
  const sourceText = [
    insight.metric.source_agency,
    insight.metric.source_dataset,
    insight.source.publication_date ? `published ${insight.source.publication_date}` : null
  ].filter(Boolean).join(" · ");

  return (
    <section className="panel border-l-4 border-l-teal p-5">
      <div className="grid gap-6 xl:grid-cols-[1.05fr_1fr]">
        <div>
          <div className="text-sm font-semibold uppercase text-muted">{insight.metric.metric_name}</div>
          <div className="mt-3 flex flex-wrap items-end gap-x-4 gap-y-1">
            <div className="text-5xl font-semibold tracking-normal text-ink">{formatValue(insight.value, insight.unit)}</div>
            <div className="pb-2 text-lg text-muted">{insight.year}</div>
          </div>
          <div className="mt-5 grid gap-5 md:grid-cols-2">
            <InsightSection title="Rank">
              <InsightRow label="National" value={formatRank(insight.ranks.national)} />
              {missionLabel ? <InsightRow label={`${missionLabel} (mission)`} value={formatRank(insight.ranks.mission_group)} /> : null}
              {stateLabel ? <InsightRow label={`${stateLabel} (state)`} value={formatRank(insight.ranks.state)} /> : null}
              {insight.rank_move ? <InsightRow label="Rank move" value={formatRankMove(insight.rank_move)} mutedValue /> : null}
            </InsightSection>
            <InsightSection title="Medians">
              <InsightRow label="National" value={formatNullableValue(insight.medians.national, insight.unit)} />
              {missionLabel ? <InsightRow label={`${missionLabel} (mission)`} value={formatNullableValue(insight.medians.mission_group, insight.unit)} /> : null}
              {stateLabel ? <InsightRow label={`${stateLabel} (state)`} value={formatNullableValue(insight.medians.state, insight.unit)} /> : null}
            </InsightSection>
          </div>
        </div>

        <div>
          <InsightSection title="Change over time">
            {["1y", "3y", "5y"].map((key) => {
              const change = insight.changes[key];
              return change ? (
                <InsightRow
                  key={key}
                  label={changeLabel(key)}
                  value={formatChange(change.percent)}
                  detail={`from ${formatValue(change.from_value, insight.unit)} in ${change.year}`}
                />
              ) : null;
            })}
            {Object.keys(insight.changes).length === 0 ? <div className="py-2 text-sm text-muted">Not enough history for change calculations.</div> : null}
          </InsightSection>
          <div className="mt-6 border-t border-line pt-4 text-sm text-muted">
            <div>{sourceText}</div>
            {insight.source.source_url ? (
              <SafeExternalLink className="mt-1 inline-block text-teal hover:underline" href={insight.source.source_url}>
                Source file
              </SafeExternalLink>
            ) : null}
          </div>
        </div>
      </div>
    </section>
  );
}

function InsightSection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div>
      <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted">{title}</h2>
      <div className="divide-y divide-line border-y border-line">{children}</div>
    </div>
  );
}

function InsightRow({
  label,
  value,
  detail,
  mutedValue = false
}: {
  label: string;
  value: string;
  detail?: string;
  mutedValue?: boolean;
}) {
  return (
    <div className="grid grid-cols-[minmax(0,1fr)_auto] items-baseline gap-4 py-2 text-sm">
      <div className="text-ink">{label}</div>
      <div className={`text-right font-semibold tabular-nums ${mutedValue ? "text-muted" : "text-ink"}`}>{value}</div>
      {detail ? <div className="col-span-2 text-right text-xs text-muted">{detail}</div> : null}
    </div>
  );
}

function formatRank(rank: MetricInsightRank | null) {
  if (!rank?.rank || !rank.of) return "No data";
  return `${ordinal(rank.rank)} of ${rank.of}`;
}

function formatRankMove(move: NonNullable<MetricInsight["rank_move"]>) {
  if (move.places === 0) return `No change since ${shortYear(move.year)}`;
  const direction = move.places > 0 ? "▲" : "▼";
  const places = Math.abs(move.places);
  return `${direction} ${places} ${places === 1 ? "place" : "places"} since ${shortYear(move.year)}`;
}

function formatNullableValue(value: number | null, unit: string) {
  return value === null ? "No data" : formatValue(value, unit);
}

function formatChange(percent: number) {
  const direction = percent >= 0 ? "▲" : "▼";
  return `${direction} ${Math.abs(percent).toFixed(0)}%`;
}

function changeLabel(key: string) {
  const years = key.replace("y", "");
  return `${years} ${years === "1" ? "year" : "years"}`;
}

function ordinal(value: number) {
  const mod10 = value % 10;
  const mod100 = value % 100;
  const suffix = mod10 === 1 && mod100 !== 11 ? "st" : mod10 === 2 && mod100 !== 12 ? "nd" : mod10 === 3 && mod100 !== 13 ? "rd" : "th";
  return `${value}${suffix}`;
}

function shortYear(year: number) {
  return `'${String(year).slice(-2)}`;
}

function ProviderHeader({ provider }: { provider: Provider }) {
  return (
    <section className="flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-2xl font-semibold">{provider.provider_name}</h1>
        <p className="mt-1 text-sm text-muted">{provider.state} · Public university profile</p>
        <div className="mt-2 flex flex-wrap gap-2">
          {provider.mission_group ? <Badge>{provider.mission_group}</Badge> : null}
          {provider.table_classification ? <Badge>{provider.table_classification}</Badge> : null}
          {provider.state ? <Badge>{provider.state}</Badge> : null}
        </div>
      </div>
      {provider.website ? (
        <SafeExternalLink className="rounded-md border border-line bg-white px-3 py-2 text-sm" href={provider.website}>
          Provider website
        </SafeExternalLink>
      ) : null}
    </section>
  );
}

function Badge({ children }: { children: ReactNode }) {
  return (
    <span className="inline-flex items-center rounded-md border border-line bg-cream/60 px-2 py-0.5 text-xs font-medium text-muted">
      {children}
    </span>
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

function selectedFactFromQuery(facts: FactRow[], metricId: string | string[] | undefined): FactRow | undefined {
  if (!facts.length) return undefined;
  const selectedMetricId = Array.isArray(metricId) ? metricId[0] : metricId;
  return facts.find((fact) => fact.metric_id === selectedMetricId) ?? facts[0];
}
