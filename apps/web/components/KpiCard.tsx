import Link from "next/link";
import type { FactRow } from "@/lib/api";
import { formatValue } from "@/lib/format";

export function KpiCard({
  fact,
  href,
  isActive,
}: {
  fact: FactRow;
  href: string;
  isActive: boolean;
}) {
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
      <div className="mt-1 text-xs text-muted">
        {fact.reporting_year} · {fact.dimension_scope}
      </div>
    </Link>
  );
}
