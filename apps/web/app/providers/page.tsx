import Link from "next/link";
import { getProviders } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function ProvidersPage() {
  const providers = (await getProviders()).filter(
    (provider) => provider.provider_type === "university"
  );
  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-semibold">Providers</h1>
        <p className="mt-1 text-sm text-muted">Seeded public-university provider dimension.</p>
      </div>
      <div className="panel overflow-hidden">
        <table className="w-full border-collapse text-left text-sm">
          <thead className="bg-cream/60 text-xs uppercase text-muted">
            <tr>
              <th className="px-4 py-3">Provider</th>
              <th className="px-4 py-3">Mission group</th>
              <th className="px-4 py-3">Table</th>
              <th className="px-4 py-3">State</th>
              <th className="px-4 py-3">Website</th>
            </tr>
          </thead>
          <tbody>
            {providers.map((provider) => (
              <tr className="border-t border-line" key={provider.provider_id}>
                <td className="px-4 py-3 font-medium">
                  <Link className="hover:text-teal" href={`/providers/${provider.provider_id}`}>
                    {provider.provider_name}
                  </Link>
                </td>
                <td className="px-4 py-3 text-muted">{provider.mission_group ?? "—"}</td>
                <td className="px-4 py-3 text-muted">{provider.table_classification ?? "—"}</td>
                <td className="px-4 py-3 text-muted">{provider.state}</td>
                <td className="px-4 py-3 text-muted">{provider.website}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
