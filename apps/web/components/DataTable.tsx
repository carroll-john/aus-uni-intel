import Link from "next/link";
import type { FactRow } from "@/lib/api";
import { formatValue } from "@/lib/format";

export function RankingTable({
  rows,
  showMetric = true,
}: {
  rows: FactRow[];
  showMetric?: boolean;
}) {
  return (
    <div className="overflow-x-auto rounded-md border border-line">
      <table
        className={`${showMetric ? "min-w-[640px]" : "min-w-[420px]"} w-full border-collapse text-left text-sm`}
      >
        <thead className="bg-cream/60 text-xs uppercase text-muted">
          <tr>
            <th className="px-3 py-2">Rank</th>
            <th className="px-3 py-2">Provider</th>
            {showMetric ? <th className="px-3 py-2">Metric</th> : null}
            <th className="px-3 py-2 text-right">Value</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr
              className="border-t border-line"
              key={`${row.provider_id}-${row.metric_id}-${row.reporting_year}-${row.dimension_scope}`}
            >
              <td className="px-3 py-2 text-muted">{index + 1}</td>
              <td className="px-3 py-2 font-medium">
                {row.provider_id ? (
                  <Link className="hover:text-teal" href={`/providers/${row.provider_id}`}>
                    {row.provider_name}
                  </Link>
                ) : (
                  row.provider_name
                )}
              </td>
              {showMetric ? <td className="px-3 py-2 text-muted">{row.metric_name}</td> : null}
              <td className="px-3 py-2 text-right tabular-nums">
                {formatValue(row.value, row.unit)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
