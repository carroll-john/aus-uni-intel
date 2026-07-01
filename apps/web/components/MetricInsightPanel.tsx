import type { ReactNode } from "react";
import { SafeExternalLink } from "@/components/SafeExternalLink";
import type { MetricInsight, MetricInsightRank } from "@/lib/api";
import { formatValue } from "@/lib/format";

export function MetricInsightPanel({ insight }: { insight: MetricInsight }) {
  const missionLabel = insight.ranks.mission_group?.label ?? insight.provider.mission_group;
  const stateLabel = insight.ranks.state?.label ?? insight.provider.state;
  const sourceText = [
    insight.metric.source_agency,
    insight.metric.source_dataset,
    insight.source.publication_date ? `published ${insight.source.publication_date}` : null,
  ]
    .filter(Boolean)
    .join(" · ");

  return (
    <section className="panel border-l-4 border-l-teal p-5">
      <div className="grid gap-6 xl:grid-cols-[1.05fr_1fr]">
        <div>
          <div className="text-sm font-semibold uppercase text-muted">
            {insight.metric.metric_name}
          </div>
          <div className="mt-3 flex flex-wrap items-end gap-x-4 gap-y-1">
            <div className="text-5xl font-semibold tracking-normal text-ink">
              {formatValue(insight.value, insight.unit)}
            </div>
            <div className="pb-2 text-lg text-muted">{insight.year}</div>
          </div>
          <div className="mt-5 grid gap-5 md:grid-cols-2">
            <InsightSection title="Rank">
              <InsightRow label="National" value={formatRank(insight.ranks.national)} />
              {missionLabel ? (
                <InsightRow
                  label={`${missionLabel} (mission)`}
                  value={formatRank(insight.ranks.mission_group)}
                />
              ) : null}
              {stateLabel ? (
                <InsightRow
                  label={`${stateLabel} (state)`}
                  value={formatRank(insight.ranks.state)}
                />
              ) : null}
              {insight.rank_move ? (
                <InsightRow
                  label="Rank move"
                  value={formatRankMove(insight.rank_move)}
                  mutedValue
                />
              ) : null}
            </InsightSection>
            <InsightSection title="Medians">
              <InsightRow
                label="National"
                value={formatNullableValue(insight.medians.national, insight.unit)}
              />
              {missionLabel ? (
                <InsightRow
                  label={`${missionLabel} (mission)`}
                  value={formatNullableValue(insight.medians.mission_group, insight.unit)}
                />
              ) : null}
              {stateLabel ? (
                <InsightRow
                  label={`${stateLabel} (state)`}
                  value={formatNullableValue(insight.medians.state, insight.unit)}
                />
              ) : null}
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
            {Object.keys(insight.changes).length === 0 ? (
              <div className="py-2 text-sm text-muted">
                Not enough history for change calculations.
              </div>
            ) : null}
          </InsightSection>
          <div className="mt-6 border-t border-line pt-4 text-sm text-muted">
            <div>{sourceText}</div>
            {insight.source.source_url ? (
              <SafeExternalLink
                className="mt-1 inline-block text-teal hover:underline"
                href={insight.source.source_url}
              >
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
  mutedValue = false,
}: {
  label: string;
  value: string;
  detail?: string;
  mutedValue?: boolean;
}) {
  return (
    <div className="grid grid-cols-[minmax(0,1fr)_auto] items-baseline gap-4 py-2 text-sm">
      <div className="text-ink">{label}</div>
      <div
        className={`text-right font-semibold tabular-nums ${mutedValue ? "text-muted" : "text-ink"}`}
      >
        {value}
      </div>
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
  const suffix =
    mod10 === 1 && mod100 !== 11
      ? "st"
      : mod10 === 2 && mod100 !== 12
        ? "nd"
        : mod10 === 3 && mod100 !== 13
          ? "rd"
          : "th";
  return `${value}${suffix}`;
}

function shortYear(year: number) {
  return `'${String(year).slice(-2)}`;
}
