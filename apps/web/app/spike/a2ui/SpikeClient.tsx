"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { MessageProcessor } from "@a2ui/web_core/v0_9";
import { A2uiSurface } from "@a2ui/react/v0_9";
import { uniIntelCatalog } from "@/lib/spike/a2ui-catalog";
import { DEFAULT_SURFACE_ID } from "@/lib/spike/compose";
import type { AgentSelection, ChatMessage, ComposeLogEntry, ComposeResponse } from "@/lib/spike/types";

const STARTER_PROMPTS = [
  {
    label: "Finance + research",
    prompt: "Show total revenue ranked by provider and HERDC research income over time"
  },
  {
    label: "Postgraduate demand",
    prompt: "How are postgraduate enrolments and commencing postgraduate enrolments tracking over time?"
  },
  {
    label: "International income",
    prompt: "Rank providers by overseas student fee income for 2024"
  },
  {
    label: "Student experience",
    prompt: "Show QILT overall experience and teaching quality ranked by provider"
  },
  {
    label: "Peer benchmarks",
    prompt: "Show operating margin broken down by mission group"
  }
] as const;

const REFINEMENT_PROMPTS = [
  {
    label: "Add student experience",
    prompt: "Now add QILT overall experience ranked by provider"
  },
  {
    label: "Split by mission group",
    prompt: "Split the view by mission group instead of individual providers"
  },
  {
    label: "Add research load",
    prompt: "Also include postgraduate research load over time"
  },
  {
    label: "Unavailable metric (demo)",
    prompt: "Show retention rate by partner"
  }
] as const;

export function SpikeClient() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [priorSelection, setPriorSelection] = useState<AgentSelection | undefined>();
  const [logs, setLogs] = useState<ComposeLogEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasSurface, setHasSurface] = useState(false);

  const processor = useMemo(() => new MessageProcessor([uniIntelCatalog]), []);
  const [surfaces, setSurfaces] = useState(() => Array.from(processor.model.surfacesMap.values()));

  useEffect(() => {
    const sync = () => setSurfaces(Array.from(processor.model.surfacesMap.values()));
    const createdSub = processor.onSurfaceCreated(sync);
    const deletedSub = processor.onSurfaceDeleted(sync);
    return () => {
      createdSub.unsubscribe();
      deletedSub.unsubscribe();
    };
  }, [processor]);

  const submitIntent = useCallback(
    async (intent: string) => {
      if (!intent.trim()) return;
      setLoading(true);
      setError(null);
      const nextMessages: ChatMessage[] = [...messages, { role: "user", content: intent.trim() }];
      setMessages(nextMessages);
      setInput("");

      try {
        const response = await fetch("/spike/a2ui/api/compose", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            messages: nextMessages,
            priorSelection,
            surfaceId: DEFAULT_SURFACE_ID,
            isRefinement: hasSurface
          })
        });
        if (!response.ok) throw new Error(`Compose failed (${response.status})`);
        const payload = (await response.json()) as ComposeResponse;
        processor.processMessages(payload.messages);
        setPriorSelection(payload.selection);
        setHasSurface(true);
        setLogs((current) => [...current, payload.log]);
        setMessages((current) => [...current, { role: "assistant", content: payload.selection.rationale }]);
      } catch (submitError) {
        setError(submitError instanceof Error ? submitError.message : "Unknown error");
      } finally {
        setLoading(false);
      }
    },
    [hasSurface, messages, priorSelection, processor]
  );

  return (
    <div className="space-y-6">
      <section className="panel space-y-3 p-4">
        <label className="block text-sm font-medium text-ink" htmlFor="intent">
          Describe the insights and view you want
        </label>
        <textarea
          className="min-h-24 w-full rounded-md border border-line px-3 py-2 text-sm"
          id="intent"
          onChange={(event) => setInput(event.target.value)}
          placeholder="e.g. Show postgraduate enrolments over time and rank providers by research income"
          value={input}
        />
        <div className="flex flex-wrap gap-2">
          <button
            className="rounded-md bg-teal px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
            disabled={loading || !input.trim()}
            onClick={() => submitIntent(input)}
            type="button"
          >
            {loading ? "Composing…" : hasSurface ? "Refine view" : "Compose view"}
          </button>
        </div>

        <SamplePrompts
          disabled={loading}
          onSelect={(prompt) => setInput(prompt)}
          onSubmit={submitIntent}
          prompts={hasSurface ? REFINEMENT_PROMPTS : STARTER_PROMPTS}
          title={hasSurface ? "Try a refinement" : "Sample prompts"}
        />

        {error ? <p className="text-sm text-red-600">{error}</p> : null}
      </section>

      <section className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
        <div className="panel min-h-[420px] p-4">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted">Composed view (A2UI)</h2>
          {!surfaces.length ? (
            <div className="flex h-64 items-center justify-center rounded-md border border-dashed border-line text-sm text-muted">
              Submit a request to generate a composition.
            </div>
          ) : (
            surfaces.map((surface) => <A2uiSurface key={surface.id} surface={surface} />)
          )}
        </div>

        <InspectorLog logs={logs} />
      </section>
    </div>
  );
}

function SamplePrompts({
  title,
  prompts,
  disabled,
  onSelect,
  onSubmit
}: {
  title: string;
  prompts: ReadonlyArray<{ label: string; prompt: string }>;
  disabled: boolean;
  onSelect: (prompt: string) => void;
  onSubmit: (prompt: string) => void;
}) {
  return (
    <div className="space-y-2 border-t border-line pt-3">
      <p className="text-xs font-medium uppercase tracking-wide text-muted">{title}</p>
      <div className="flex flex-wrap gap-2">
        {prompts.map((sample) => (
          <div className="flex overflow-hidden rounded-md border border-line text-xs" key={sample.label}>
            <button
              className="px-3 py-1.5 font-medium text-ink hover:bg-slate-50 disabled:opacity-60"
              disabled={disabled}
              onClick={() => onSelect(sample.prompt)}
              title={sample.prompt}
              type="button"
            >
              {sample.label}
            </button>
            <button
              className="border-l border-line bg-slate-50 px-2 py-1.5 text-teal hover:bg-teal/10 disabled:opacity-60"
              disabled={disabled}
              onClick={() => onSubmit(sample.prompt)}
              title={`Run: ${sample.prompt}`}
              type="button"
            >
              Run
            </button>
          </div>
        ))}
      </div>
      <p className="text-xs text-muted">Click a label to load it into the box, or Run to compose immediately.</p>
    </div>
  );
}

function InspectorLog({ logs }: { logs: ComposeLogEntry[] }) {
  if (!logs.length) {
    return (
      <div className="panel p-4 text-sm text-muted">
        <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted">Selection log</h2>
        Intent → insights selected → composition will appear here.
      </div>
    );
  }

  return (
    <div className="panel max-h-[720px] space-y-4 overflow-y-auto p-4">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">Intent → selection → composition</h2>
      {[...logs].reverse().map((log) => (
        <article className="rounded-md border border-line bg-slate-50 p-3 text-sm" key={log.turn}>
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <span className="rounded bg-teal/10 px-2 py-0.5 text-xs font-semibold text-teal">Turn {log.turn}</span>
            <span className="rounded bg-slate-200 px-2 py-0.5 text-xs font-medium">{log.selector}</span>
            <span className="rounded bg-slate-200 px-2 py-0.5 text-xs font-medium">{log.dataSource}</span>
          </div>
          <p className="font-medium text-ink">Intent</p>
          <p className="mb-2 text-muted">{log.intent}</p>
          <p className="font-medium text-ink">Rationale</p>
          <p className="mb-2 text-muted">{log.rationale}</p>
          {log.unavailableNotes?.length ? (
            <>
              <p className="font-medium text-amber">Unavailable (not fabricated)</p>
              <ul className="mb-2 list-disc pl-5 text-amber">
                {log.unavailableNotes.map((note) => (
                  <li key={note}>{note}</li>
                ))}
              </ul>
            </>
          ) : null}
          {log.clarify ? (
            <>
              <p className="font-medium text-ink">Clarify</p>
              <p className="text-muted">{log.clarify.question}</p>
              <ul className="mb-2 list-disc pl-5 text-muted">
                {log.clarify.options.map((option) => (
                  <li key={option}>{option}</li>
                ))}
              </ul>
            </>
          ) : null}
          <p className="font-medium text-ink">Insights selected</p>
          <ul className="mb-2 space-y-1 text-muted">
            {log.resolvedInsights.map((insight) => (
              <li key={`${insight.id}-${insight.breakdown}`}>
                <span className="font-medium text-ink">{insight.name}</span> · {insight.breakdown} · {insight.chart}
              </li>
            ))}
          </ul>
          <p className="font-medium text-ink">Composition tree</p>
          <ul className="mb-2 space-y-1 text-muted">
            {log.compositionTree.map((node) => (
              <li key={node.id}>
                {node.component}
                {node.insightId ? ` → ${node.insightId}` : ""}
                {node.title ? ` (${node.title})` : ""}
              </li>
            ))}
          </ul>
          <details>
            <summary className="cursor-pointer font-medium text-ink">Raw A2UI messages</summary>
            <pre className="mt-2 overflow-x-auto rounded bg-white p-2 text-xs">{JSON.stringify(log.rawMessages, null, 2)}</pre>
          </details>
        </article>
      ))}
    </div>
  );
}
