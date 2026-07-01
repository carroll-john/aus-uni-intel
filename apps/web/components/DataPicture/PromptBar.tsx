"use client";

import Link from "next/link";
import { useState } from "react";
import type { DataPictureExample } from "@/lib/api";

export function PromptBar({
  examples,
  defaultQuestion
}: {
  examples: DataPictureExample[];
  defaultQuestion: string;
}) {
  const [value, setValue] = useState(defaultQuestion);

  return (
    <div className="space-y-3">
      <form action="/data-picture" className="space-y-3" method="get">
        <label className="block text-xs font-semibold uppercase tracking-wide text-muted" htmlFor="data-picture-question">
          Ask a strategic question
        </label>
        <div className="flex flex-col gap-2 sm:flex-row">
          <textarea
            className="min-h-[3rem] flex-1 rounded-md border border-line px-3 py-2 text-sm focus:border-teal focus:outline-none focus:ring-1 focus:ring-teal"
            id="data-picture-question"
            name="q"
            onChange={(event) => setValue(event.target.value)}
            placeholder="e.g. Which universities have high revenue but a low student experience rating?"
            rows={2}
            value={value}
          />
          <button
            className="h-fit rounded-md bg-teal px-4 py-2 text-sm font-semibold text-white hover:bg-teal/90"
            type="submit"
          >
            Compose
          </button>
        </div>
      </form>
      <div className="flex flex-wrap gap-2">
        {examples.map((example) => (
          <Link
            className="rounded-full border border-line bg-white px-3 py-1 text-xs font-semibold text-ink hover:border-teal hover:text-teal"
            href={`/data-picture?q=${encodeURIComponent(example.question)}`}
            key={example.id}
          >
            {example.label}: {example.question}
          </Link>
        ))}
      </div>
    </div>
  );
}
