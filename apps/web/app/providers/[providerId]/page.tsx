import { RankingTable } from "@/components/DataTable";
import { TrendLineChart } from "@/components/ChartPanels";
import { getProfile, getRankings, getTrends } from "@/lib/api";
import { formatValue, groupBy } from "@/lib/format";

export const dynamic = "force-dynamic";

const profileTrendMetric = "student_total_enrolments";

export default async function ProviderProfilePage({ params }: { params: Promise<{ providerId: string }> }) {
  const { providerId } = await params;
  const profile = await getProfile(providerId);
  const latestFacts = profile.facts.filter((fact) => fact.reporting_year === 2024);
  const grouped = groupBy(latestFacts, (fact) => fact.metric_group ?? "Metrics");
  const trend = await getTrends(profileTrendMetric, providerId, "Student");
  const revenuePeers = await getRankings(
    "finance_total_revenues_from_continuing_operations_including_deferred_superannuation",
    "2024",
    "Total Institution",
    8
  );

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
        {latestFacts
          .filter((fact) =>
            [
              "finance_total_revenues_from_continuing_operations_including_deferred_superannuation",
              "student_total_enrolments",
              "herdc_research_income_total",
              "qilt_overall_educational_experience_positive_rating"
            ].includes(fact.metric_id)
          )
          .slice(0, 4)
          .map((fact) => (
            <div className="panel p-4" key={`${fact.metric_id}-${fact.dimension_scope}`}>
              <div className="text-xs font-medium uppercase text-muted">{fact.metric_name}</div>
              <div className="mt-2 text-2xl font-semibold">{formatValue(fact.value, fact.unit)}</div>
              <div className="mt-1 text-xs text-muted">{fact.dimension_scope}</div>
            </div>
          ))}
      </section>

      <section className="grid gap-4 xl:grid-cols-[1fr_1fr]">
        <div className="panel p-4">
          <h2 className="mb-3 text-base font-semibold">Student trend</h2>
          <TrendLineChart rows={trend} />
        </div>
        <div className="panel p-4">
          <h2 className="mb-3 text-base font-semibold">Revenue peer ranking</h2>
          <RankingTable rows={revenuePeers} />
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-2">
        {Object.entries(grouped).map(([group, facts]) => (
          <div className="panel p-4" key={group}>
            <h2 className="mb-3 text-base font-semibold">{group}</h2>
            <div className="space-y-2">
              {facts.slice(0, 12).map((fact) => (
                <div className="flex items-center justify-between gap-4 border-t border-line pt-2 text-sm" key={`${fact.metric_id}-${fact.dimension_scope}`}>
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
