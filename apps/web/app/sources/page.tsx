import { SafeExternalLink } from "@/components/SafeExternalLink";
import { getMetricCatalog, getMetrics, getQuality, getSources } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function SourcesPage() {
  const [sources, catalog, metrics, quality] = await Promise.all([
    getSources(),
    getMetricCatalog(true),
    getMetrics(),
    getQuality(),
  ]);
  const unavailable = catalog.filter((metric) => metric.source_status !== "available");
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Sources</h1>
        <p className="mt-1 text-sm text-muted">
          Method, source files, metric definitions, and latest data-quality checks.
        </p>
      </div>

      <section className="panel overflow-hidden">
        <table className="w-full border-collapse text-left text-sm">
          <thead className="bg-cream/60 text-xs uppercase text-muted">
            <tr>
              <th className="px-3 py-2">Source</th>
              <th className="px-3 py-2">Rows</th>
              <th className="px-3 py-2">Year</th>
              <th className="px-3 py-2">URL</th>
            </tr>
          </thead>
          <tbody>
            {sources.map((source) => (
              <tr className="border-t border-line" key={source.source_file_id}>
                <td className="px-3 py-2 font-medium">{source.source_name}</td>
                <td className="px-3 py-2 tabular-nums">{source.row_count}</td>
                <td className="px-3 py-2">{source.reporting_year ?? "multi-year"}</td>
                <td className="px-3 py-2 text-teal">
                  <SafeExternalLink href={source.source_url}>Open</SafeExternalLink>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="panel overflow-hidden">
        <div className="border-b border-line p-4">
          <h2 className="text-base font-semibold">Curated metric catalogue</h2>
          <p className="mt-1 text-sm text-muted">
            Default product metrics grouped from the source-site taxonomy. Missing rows are backlog
            items, not selectable chart metrics.
          </p>
        </div>
        <table className="w-full border-collapse text-left text-sm">
          <thead className="bg-cream/60 text-xs uppercase text-muted">
            <tr>
              <th className="px-3 py-2">Group</th>
              <th className="px-3 py-2">Metric</th>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2">Source note</th>
            </tr>
          </thead>
          <tbody>
            {catalog.map((metric) => (
              <tr className="border-t border-line align-top" key={metric.catalog_item_id}>
                <td className="px-3 py-2 text-muted">{metric.catalog_group}</td>
                <td className="px-3 py-2 font-medium">{metric.metric_name}</td>
                <td className="px-3 py-2">
                  <span
                    className={`rounded-md px-2 py-1 text-xs font-medium ${metric.source_status === "available" ? "bg-emerald-50 text-teal" : "bg-amber-50 text-amber"}`}
                  >
                    {metric.source_status === "available" ? "Available" : "Not available yet"}
                  </span>
                </td>
                <td className="px-3 py-2 text-muted">{metric.source_note}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {unavailable.length > 0 ? (
        <section className="panel p-4">
          <h2 className="text-base font-semibold">Missing OOTB metrics</h2>
          <p className="mt-1 text-sm text-muted">
            These are present in the reference taxonomy but not currently available as live
            source-backed or calculated metrics.
          </p>
          <div className="mt-3 grid gap-2 md:grid-cols-2">
            {unavailable.map((metric) => (
              <div
                className="rounded-md border border-line p-3"
                key={`missing-${metric.catalog_item_id}`}
              >
                <div className="text-sm font-medium">{metric.metric_name}</div>
                <div className="mt-1 text-xs uppercase text-muted">
                  {metric.catalog_group} · {metric.source_status.replace("_", " ")}
                </div>
              </div>
            ))}
          </div>
        </section>
      ) : null}

      <section className="panel overflow-hidden">
        <div className="border-b border-line p-4">
          <h2 className="text-base font-semibold">Raw metric definitions</h2>
          <p className="mt-1 text-sm text-muted">
            Full source-backed catalogue used for advanced inspection.
          </p>
        </div>
        <table className="w-full border-collapse text-left text-sm">
          <thead className="bg-cream/60 text-xs uppercase text-muted">
            <tr>
              <th className="px-3 py-2">Metric</th>
              <th className="px-3 py-2">Source</th>
              <th className="px-3 py-2">Definition</th>
            </tr>
          </thead>
          <tbody>
            {metrics.map((metric) => (
              <tr className="border-t border-line align-top" key={metric.metric_id}>
                <td className="px-3 py-2 font-medium">{metric.metric_name}</td>
                <td className="px-3 py-2 text-muted">{metric.source_dataset}</td>
                <td className="px-3 py-2 text-muted">
                  {metric.definition}
                  {metric.calculation_method ? (
                    <span className="block pt-1 text-amber">
                      Calculation: {metric.calculation_method}
                    </span>
                  ) : null}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="panel overflow-hidden">
        <table className="w-full border-collapse text-left text-sm">
          <thead className="bg-cream/60 text-xs uppercase text-muted">
            <tr>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2">Check</th>
              <th className="px-3 py-2">Source</th>
              <th className="px-3 py-2">Details</th>
            </tr>
          </thead>
          <tbody>
            {quality.map((check) => (
              <tr
                className="border-t border-line align-top"
                key={`${check.run_id}-${check.check_name}-${check.source_file_id}`}
              >
                <td className="px-3 py-2 font-medium">{check.status}</td>
                <td className="px-3 py-2">{check.check_name}</td>
                <td className="px-3 py-2 text-muted">
                  {check.source_name ?? check.source_file_id}
                </td>
                <td className="px-3 py-2 text-muted">{check.details}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
