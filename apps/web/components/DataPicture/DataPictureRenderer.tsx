import Link from "next/link";
import { MultiProviderTrendChart, RankingBarChart, TrendLineChart } from "@/components/ChartPanels";
import { RankingTable } from "@/components/DataTable";
import type { Caveat, DataPicture, DataPictureBlock, InsightHeaderProps } from "@/lib/api";
import { formatValue } from "@/lib/format";
import { EquityGapPanel } from "./EquityGapPanel";
import { EvidenceCardGrid, OutlierExplorer } from "./EvidenceAndOutliers";
import { MismatchMatrix } from "./MismatchMatrix";
import { DataQualityPanel, SourceTraceDrawer } from "./ProvenancePanels";

export function DataPictureRenderer({ picture }: { picture: DataPicture }) {
  return (
    <div className="space-y-4">
      <CaveatBanner caveats={picture.caveats} />
      {picture.blocks.map((block, index) => (
        <BlockPanel block={block} key={`${block.type}-${index}`} />
      ))}
    </div>
  );
}

function BlockPanel({ block }: { block: DataPictureBlock }) {
  const body = renderBlock(block);
  if (body === null) return null;
  return (
    <section className="panel min-w-0 p-4">
      {block.title ? <h2 className="mb-3 text-base font-semibold">{block.title}</h2> : null}
      {body}
    </section>
  );
}

function renderBlock(block: DataPictureBlock) {
  switch (block.type) {
    case "InsightHeader":
      return <InsightHeader {...block.props} />;
    case "NarrativeBuilder":
      return <NarrativeBuilder paragraphs={block.props.paragraphs} />;
    case "EvidenceCardGrid":
      return <EvidenceCardGrid cards={block.props.cards} />;
    case "RankingBarChart":
      return <RankingBarChart rows={block.props.rows} />;
    case "TrendChart":
      return block.props.variant === "multi" ? (
        <MultiProviderTrendChart rows={block.props.rows} />
      ) : (
        <TrendLineChart rows={block.props.rows} />
      );
    case "MismatchMatrix":
      return <MismatchMatrix metricA={block.props.metric_a} metricB={block.props.metric_b} rows={block.props.rows} />;
    case "EquityGapPanel":
      return <EquityGapPanel items={block.props.items} />;
    case "OutlierExplorer":
      return <OutlierExplorer rows={block.props.rows} />;
    case "MetricComparisonTable":
      return <RankingTable rows={block.props.rows} />;
    case "DataQualityPanel":
      return <DataQualityPanel checks={block.props.checks} />;
    case "SourceTraceDrawer":
      return <SourceTraceDrawer sources={block.props.sources} />;
    case "FollowUpPromptRail":
      return <FollowUpPromptRail prompts={block.props.prompts} />;
    default: {
      const exhaustiveCheck: never = block;
      return exhaustiveCheck;
    }
  }
}

export function InsightHeader({
  title,
  subtitle,
  stat_label: statLabel,
  stat_value: statValue,
  stat_unit: statUnit,
  delta_label: deltaLabel,
  delta_value: deltaValue
}: InsightHeaderProps) {
  return (
    <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h1 className="text-xl font-semibold leading-snug">{title}</h1>
        <p className="mt-1 text-sm text-muted">{subtitle}</p>
      </div>
      <div className="shrink-0 rounded-md border border-line bg-cream/50 px-4 py-3 text-right">
        <div className="text-xs font-medium uppercase text-muted">{statLabel}</div>
        <div className="mt-1 text-2xl font-semibold tabular-nums">{formatValue(statValue, statUnit)}</div>
        {deltaLabel ? (
          <div className={`mt-1 text-xs font-semibold ${(deltaValue ?? 0) < 0 ? "text-coral" : "text-teal"}`}>
            {deltaValue !== null && deltaValue !== undefined ? `${deltaValue >= 0 ? "+" : ""}${deltaValue.toFixed(0)}% · ` : ""}
            {deltaLabel}
          </div>
        ) : null}
      </div>
    </div>
  );
}

export function NarrativeBuilder({ paragraphs }: { paragraphs: string[] }) {
  return (
    <div className="space-y-2 text-sm leading-6 text-ink">
      {paragraphs.map((paragraph, index) => (
        <p key={index}>{paragraph}</p>
      ))}
    </div>
  );
}

export function FollowUpPromptRail({ prompts }: { prompts: string[] }) {
  if (!prompts.length) return null;
  return (
    <div className="flex flex-wrap gap-2">
      {prompts.map((prompt) => (
        <Link
          className="rounded-full border border-line bg-white px-3 py-1.5 text-xs font-semibold text-ink hover:border-teal hover:text-teal"
          href={`/data-picture?q=${encodeURIComponent(prompt)}`}
          key={prompt}
        >
          {prompt}
        </Link>
      ))}
    </div>
  );
}

function CaveatBanner({ caveats }: { caveats: Caveat[] }) {
  if (!caveats.length) return null;
  const worst = caveats.some((caveat) => caveat.severity === "error") ? "error" : "warning";
  return (
    <div
      className={`rounded-md border px-4 py-3 text-sm ${
        worst === "error" ? "border-coral/40 bg-coral/5 text-coral" : "border-amber/40 bg-amber/5 text-amber"
      }`}
    >
      <div className="font-semibold">Caveats to keep in mind</div>
      <ul className="mt-1 list-disc space-y-1 pl-5">
        {caveats.map((caveat, index) => (
          <li key={index}>{caveat.message}</li>
        ))}
      </ul>
    </div>
  );
}
