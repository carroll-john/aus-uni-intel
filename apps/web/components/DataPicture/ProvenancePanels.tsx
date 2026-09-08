import type { QualityCheck, SourceTraceItem } from "@/lib/api";
import { SafeExternalLink } from "@/components/SafeExternalLink";

const STATUS_STYLES: Record<QualityCheck["status"], string> = {
  pass: "bg-teal/10 text-teal",
  warn: "bg-amber/10 text-amber",
  fail: "bg-coral/10 text-coral"
};

export function DataQualityPanel({ checks }: { checks: QualityCheck[] }) {
  if (!checks.length) {
    return <p className="text-sm text-muted">No data quality checks are recorded for this picture.</p>;
  }
  return (
    <div className="overflow-x-auto rounded-md border border-line">
      <table className="min-w-[560px] w-full border-collapse text-left text-sm">
        <thead className="bg-cream/60 text-xs uppercase text-muted">
          <tr>
            <th className="px-3 py-2">Check</th>
            <th className="px-3 py-2">Status</th>
            <th className="px-3 py-2">Details</th>
          </tr>
        </thead>
        <tbody>
          {checks.map((check, index) => (
            <tr className="border-t border-line" key={index}>
              <td className="px-3 py-2 font-medium">{check.check_name}</td>
              <td className="px-3 py-2">
                <span className={`rounded-full px-2 py-1 text-xs font-semibold uppercase ${STATUS_STYLES[check.status]}`}>
                  {check.status}
                </span>
              </td>
              <td className="px-3 py-2 text-muted">{check.details ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function SourceTraceDrawer({ sources }: { sources: SourceTraceItem[] }) {
  if (!sources.length) {
    return <p className="text-sm text-muted">No source files are linked to this picture.</p>;
  }
  return (
    <details className="rounded-md border border-line" open>
      <summary className="cursor-pointer bg-cream/60 px-3 py-2 text-sm font-semibold">
        {sources.length} source {sources.length === 1 ? "file" : "files"}
      </summary>
      <ul className="divide-y divide-line">
        {sources.map((source) => (
          <li className="px-3 py-2 text-sm" key={source.source_file_id}>
            <div className="font-medium">{source.source_name}</div>
            <div className="mt-0.5 text-xs text-muted">
              {source.dataset_name ?? "Unknown dataset"} · {source.publication_date ?? "n/d"}
              {source.license ? ` · ${source.license}` : ""}
            </div>
            <SafeExternalLink className="mt-0.5 inline-block text-xs text-teal hover:underline" href={source.source_url}>
              View source
            </SafeExternalLink>
          </li>
        ))}
      </ul>
    </details>
  );
}
