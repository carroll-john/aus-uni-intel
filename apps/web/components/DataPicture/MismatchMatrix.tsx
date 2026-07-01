import Link from "next/link";
import type { MetricRef, MismatchRow } from "@/lib/api";
import { formatValue } from "@/lib/format";

export function MismatchMatrix({
  metricA,
  metricB,
  rows
}: {
  metricA: MetricRef;
  metricB: MetricRef;
  rows: MismatchRow[];
}) {
  if (!rows.length) {
    return <p className="text-sm text-muted">No universities have comparable data on both metrics yet.</p>;
  }
  return (
    <div className="overflow-x-auto rounded-md border border-line">
      <table className="min-w-[640px] w-full border-collapse text-left text-sm">
        <thead className="bg-cream/60 text-xs uppercase text-muted">
          <tr>
            <th className="px-3 py-2">Provider</th>
            <th className="px-3 py-2 text-right">{metricA.metric_name}</th>
            <th className="px-3 py-2 text-right">{metricB.metric_name}</th>
            <th className="px-3 py-2 text-right">Rank gap</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr className="border-t border-line" key={row.provider_id}>
              <td className="px-3 py-2 font-medium">
                <Link className="hover:text-teal" href={`/providers/${row.provider_id}`}>
                  {row.provider_name}
                </Link>
              </td>
              <td className="px-3 py-2 text-right tabular-nums">
                #{row.rank_a} · {formatValue(row.value_a, metricA.unit)}
              </td>
              <td className="px-3 py-2 text-right tabular-nums">
                #{row.rank_b} · {formatValue(row.value_b, metricB.unit)}
              </td>
              <td
                className={`px-3 py-2 text-right font-semibold tabular-nums ${
                  Math.abs(row.rank_delta) >= 15 ? "text-coral" : "text-muted"
                }`}
              >
                {Math.abs(row.rank_delta)} places
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
