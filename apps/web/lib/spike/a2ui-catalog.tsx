"use client";

import { z } from "zod";
import { Catalog } from "@a2ui/web_core/v0_9";
import { BASIC_FUNCTIONS } from "@a2ui/web_core/v0_9/basic_catalog";
import {
  Card,
  Column,
  createBinderlessComponentImplementation,
  Divider,
  Row,
  Text
} from "@a2ui/react/v0_9";
import type { FactRow } from "@/lib/api";
import { RankingBarChart, TrendLineChart } from "@/components/ChartPanels";
import { formatValue } from "@/lib/format";
import type { ChartPayload, MetricCardPayload } from "./types";

export const uniIntelCatalogId = "https://uni-intel.local/spike/catalog/v1.json";

type BinderlessContext = Parameters<Parameters<typeof createBinderlessComponentImplementation>[1]>[0];

function readBoundPayload<T>(context: BinderlessContext["context"], key: string): T | null {
  const binding = context.componentModel.properties[key] as { path: string } | undefined;
  if (!binding?.path) return null;
  return context.dataContext.resolveDynamicValue<T>(binding);
}

const MetricCard = createBinderlessComponentImplementation(
  {
    name: "MetricCard",
    schema: z.object({
      dataPath: z.object({ path: z.string() })
    })
  },
  ({ context }: BinderlessContext) => {
    const payload = readBoundPayload<MetricCardPayload>(context, "dataPath");
    if (!payload) {
      return <div className="rounded-md border border-dashed border-line p-4 text-sm text-muted">No metric data</div>;
    }
    return (
      <div className="space-y-1 p-2">
        <div className="text-xs font-medium uppercase tracking-wide text-muted">{payload.title}</div>
        <div className="text-2xl font-semibold text-ink">
          {payload.value === null ? "—" : formatValue(payload.value, payload.unit)}
        </div>
        <div className="text-xs text-muted">{payload.subtitle}</div>
      </div>
    );
  }
);

const TrendLine = createBinderlessComponentImplementation(
  {
    name: "TrendLine",
    schema: z.object({
      dataPath: z.object({ path: z.string() })
    })
  },
  ({ context }: BinderlessContext) => {
    const payload = readBoundPayload<ChartPayload>(context, "dataPath");
    if (!payload?.rows?.length) return <EmptyChart message="No trend data" />;
    const rows = normalizeFactRows(payload.rows);
    return (
      <div className="space-y-2">
        <ChartHeader payload={payload} />
        <TrendLineChart rows={rows} />
      </div>
    );
  }
);

const RankingBar = createBinderlessComponentImplementation(
  {
    name: "RankingBar",
    schema: z.object({
      dataPath: z.object({ path: z.string() })
    })
  },
  ({ context }: BinderlessContext) => {
    const payload = readBoundPayload<ChartPayload>(context, "dataPath");
    if (!payload?.rows?.length) return <EmptyChart message="No ranking data" />;
    const rows = normalizeFactRows(payload.rows);
    return (
      <div className="space-y-2">
        <ChartHeader payload={payload} />
        <RankingBarChart rows={rows} benchmark={payload.benchmark} />
      </div>
    );
  }
);

const BenchmarkBar = createBinderlessComponentImplementation(
  {
    name: "BenchmarkBar",
    schema: z.object({
      dataPath: z.object({ path: z.string() })
    })
  },
  ({ context }: BinderlessContext) => {
    const payload = readBoundPayload<ChartPayload>(context, "dataPath");
    if (!payload?.rows?.length) return <EmptyChart message="No benchmark data" />;
    const rows = normalizeFactRows(payload.rows);
    return (
      <div className="space-y-2">
        <ChartHeader payload={payload} />
        <RankingBarChart rows={rows} />
      </div>
    );
  }
);

const ClarifyPanel = createBinderlessComponentImplementation(
  {
    name: "ClarifyPanel",
    schema: z.object({
      dataPath: z.object({ path: z.string() }),
      notesPath: z.object({ path: z.string() }).optional()
    })
  },
  ({ context }: BinderlessContext) => {
    const clarify = readBoundPayload<{ question: string; options: string[] }>(context, "dataPath");
    const notes = readBoundPayload<string>(context, "notesPath");
    if (!clarify) return null;
    return (
      <div className="rounded-md border border-amber/40 bg-amber/5 p-4 text-sm">
        {notes ? <p className="mb-2 text-amber">{notes}</p> : null}
        <p className="font-medium text-ink">{clarify.question}</p>
        <ul className="mt-3 list-disc space-y-1 pl-5 text-muted">
          {clarify.options.map((option) => (
            <li key={option}>{option}</li>
          ))}
        </ul>
      </div>
    );
  }
);

function ChartHeader({ payload }: { payload: ChartPayload }) {
  return (
    <div>
      <div className="text-sm font-semibold text-ink">{payload.title}</div>
      {payload.subtitle ? <div className="text-xs text-muted">{payload.subtitle}</div> : null}
    </div>
  );
}

function EmptyChart({ message }: { message: string }) {
  return (
    <div className="flex h-48 items-center justify-center rounded-md border border-dashed border-line bg-slate-50 text-sm text-muted">
      {message}
    </div>
  );
}

function normalizeFactRows(rows: Record<string, unknown>[]): FactRow[] {
  return rows.map((row) => ({
    provider_id: String(row.provider_id ?? ""),
    provider_name: row.provider_name ? String(row.provider_name) : undefined,
    metric_id: String(row.metric_id ?? ""),
    metric_name: String(row.metric_name ?? ""),
    reporting_year: Number(row.reporting_year ?? 0),
    dimension_scope: String(row.dimension_scope ?? ""),
    value: Number(row.value ?? 0),
    unit: String(row.unit ?? "")
  }));
}

const customComponents = [MetricCard, TrendLine, RankingBar, BenchmarkBar, ClarifyPanel];
const layoutComponents = [Row, Column, Text, Card, Divider];

export const uniIntelCatalog = new Catalog(uniIntelCatalogId, [...layoutComponents, ...customComponents], BASIC_FUNCTIONS);
