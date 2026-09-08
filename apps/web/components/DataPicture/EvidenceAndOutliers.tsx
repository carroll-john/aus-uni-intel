import Link from "next/link";
import type { EvidenceCard, OutlierRow } from "@/lib/api";
import { formatValue } from "@/lib/format";

export function EvidenceCardGrid({ cards }: { cards: EvidenceCard[] }) {
  if (!cards.length) {
    return <p className="text-sm text-muted">No supporting evidence available.</p>;
  }
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {cards.map((card, index) => (
        <div className="rounded-md border border-line bg-cream/40 p-3" key={index}>
          <div className="text-xs font-medium uppercase text-muted">{card.label}</div>
          <div className="mt-1 text-lg font-semibold tabular-nums">{formatValue(card.value, card.unit)}</div>
          {card.caption ? <div className="mt-1 text-xs text-muted">{card.caption}</div> : null}
        </div>
      ))}
    </div>
  );
}

export function OutlierExplorer({ rows }: { rows: OutlierRow[] }) {
  if (!rows.length) {
    return <p className="text-sm text-muted">No statistical outliers were found (all values are within ~1.5 standard deviations of the mean).</p>;
  }
  return (
    <div className="space-y-2">
      {rows.map((row) => (
        <div className="flex items-center justify-between rounded-md border border-line bg-cream/40 px-3 py-2" key={row.provider_id}>
          <div>
            <Link className="font-medium hover:text-teal" href={`/providers/${row.provider_id}`}>
              {row.provider_name}
            </Link>
            <div className="text-xs text-muted">{formatValue(row.value, row.unit)}</div>
          </div>
          <div className={`rounded-full px-2 py-1 text-xs font-semibold ${row.zscore > 0 ? "bg-teal/10 text-teal" : "bg-coral/10 text-coral"}`}>
            {row.zscore > 0 ? "+" : ""}
            {row.zscore.toFixed(1)}σ
          </div>
        </div>
      ))}
    </div>
  );
}
