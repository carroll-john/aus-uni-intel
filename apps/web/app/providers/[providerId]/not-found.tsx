import Link from "next/link";

export default function ProviderNotFound() {
  return (
    <div className="panel mx-auto max-w-xl space-y-4 p-6">
      <h1 className="text-xl font-semibold">Provider not found</h1>
      <p className="text-sm text-muted">No provider matches this ID in the warehouse.</p>
      <Link
        className="inline-block text-sm font-medium text-teal hover:underline"
        href="/providers"
      >
        Back to providers
      </Link>
    </div>
  );
}
