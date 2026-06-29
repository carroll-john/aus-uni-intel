"use client";

import { useEffect } from "react";

function parseApiError(error: Error): { path?: string; status?: number } {
  const match = error.message.match(/^API (.+) failed with (\d+)$/);
  if (!match) return {};
  return { path: match[1], status: Number(match[2]) };
}

export default function ErrorBoundary({
  error,
  reset
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  const apiError = parseApiError(error);
  const isUnavailable = apiError.status === 503 || (apiError.status !== undefined && apiError.status >= 500);
  const isNotFound = apiError.status === 404;

  return (
    <div className="panel mx-auto max-w-xl space-y-4 p-6">
      <h1 className="text-xl font-semibold">
        {isNotFound ? "Page not found" : isUnavailable ? "Data service unavailable" : "Something went wrong"}
      </h1>
      <p className="text-sm text-muted">
        {isNotFound
          ? "The requested resource could not be found."
          : isUnavailable
            ? "The API warehouse is unavailable. If running locally, start the API with `make api` and ensure ingestion has completed."
            : "An unexpected error occurred while loading this page."}
      </p>
      {apiError.path ? <p className="text-xs text-muted">API path: {apiError.path}</p> : null}
      <button
        className="rounded-md bg-teal px-4 py-2 text-sm font-semibold text-white"
        onClick={() => reset()}
        type="button"
      >
        Try again
      </button>
    </div>
  );
}
