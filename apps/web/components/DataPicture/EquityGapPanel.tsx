import type { EquityGapItem } from "@/lib/api";

export function EquityGapPanel({ items }: { items: EquityGapItem[] }) {
  return (
    <div className="space-y-3">
      <div className="rounded-md border border-amber/40 bg-amber/5 px-4 py-3 text-sm text-amber">
        This prototype has not yet ingested a demographic equity dataset, so this shows the metric backlog
        instead of placeholder numbers.
      </div>
      <ul className="space-y-2">
        {items.map((item, index) => (
          <li className="rounded-md border border-line bg-cream/40 px-3 py-2 text-sm" key={index}>
            <div className="font-medium">{item.label}</div>
            <div className="text-xs text-muted">{item.note}</div>
          </li>
        ))}
      </ul>
    </div>
  );
}
