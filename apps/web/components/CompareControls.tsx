"use client";

import { useMemo, useState } from "react";
import type { ReactNode } from "react";
import { Calendar, Check, Search, X } from "lucide-react";
import type { Metric, MetricCatalogItem, Provider } from "@/lib/api";

export type SelectableMetric = (Metric | MetricCatalogItem) & {
  metric_id: string;
};

type CompareControlsProps = {
  metrics: SelectableMetric[];
  providers: Provider[];
  selectedMetricId: string;
  selectedProviderIds: string[];
  selectedBenchmark: string;
  year: string;
  catalogMode: "curated" | "raw";
};

const maxProviders = 5;

export function CompareControls({
  metrics,
  providers,
  catalogMode,
  selectedMetricId,
  selectedProviderIds,
  selectedBenchmark,
  year
}: CompareControlsProps) {
  const [providerQuery, setProviderQuery] = useState("");
  const [metricQuery, setMetricQuery] = useState("");
  const [providerIds, setProviderIds] = useState(selectedProviderIds);
  const [metricId, setMetricId] = useState(selectedMetricId);
  const [groupFilter, setGroupFilter] = useState("");
  const [stateFilter, setStateFilter] = useState("");

  const missionGroups = useMemo(() => distinct(providers.map((provider) => provider.mission_group)), [providers]);
  const states = useMemo(() => distinct(providers.map((provider) => provider.state)), [providers]);

  const selectedProviders = useMemo(
    () => providerIds.map((id) => providers.find((provider) => provider.provider_id === id)).filter(Boolean) as Provider[],
    [providerIds, providers]
  );
  const selectedMetric = useMemo(
    () => metrics.find((metric) => metric.metric_id === metricId),
    [metricId, metrics]
  );
  const filteredProviders = useMemo(
    () => filterProviders(providers, providerQuery, providerIds, groupFilter, stateFilter),
    [groupFilter, providerIds, providerQuery, providers, stateFilter]
  );

  const addShown = () =>
    setProviderIds((current) => {
      const next = [...current];
      for (const provider of filteredProviders) {
        if (next.length >= maxProviders) break;
        if (!next.includes(provider.provider_id)) next.push(provider.provider_id);
      }
      return next;
    });
  const filteredMetrics = useMemo(
    () => filterMetrics(metrics, metricQuery, metricId),
    [metricId, metricQuery, metrics]
  );

  return (
    <form className="panel space-y-4 p-4" method="get">
      <input name="providers" type="hidden" value={providerIds.join(",")} />
      <input name="metrics" type="hidden" value={metricId} />
      {catalogMode === "raw" ? <input name="catalog" type="hidden" value="raw" /> : null}

      <div className="grid gap-4 xl:grid-cols-[1fr_1fr_190px]">
        <SelectionPanel
          countLabel={`${providerIds.length}/${maxProviders}`}
          onClear={() => setProviderIds([])}
          onQueryChange={setProviderQuery}
          query={providerQuery}
          title="Providers"
        >
          <SelectedChips
            items={selectedProviders.map((provider) => ({ id: provider.provider_id, label: provider.provider_name }))}
            onRemove={(id) => setProviderIds((current) => current.filter((providerId) => providerId !== id))}
          />
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <select
              aria-label="Filter by mission group"
              className="rounded-md border border-line bg-white px-2 py-1.5 text-xs"
              onChange={(event) => setGroupFilter(event.target.value)}
              value={groupFilter}
            >
              <option value="">All groups</option>
              {missionGroups.map((group) => (
                <option key={group} value={group}>
                  {group}
                </option>
              ))}
            </select>
            <select
              aria-label="Filter by state"
              className="rounded-md border border-line bg-white px-2 py-1.5 text-xs"
              onChange={(event) => setStateFilter(event.target.value)}
              value={stateFilter}
            >
              <option value="">All states</option>
              {states.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
            <button
              className="rounded-md border border-line bg-white px-2 py-1.5 text-xs font-medium text-teal disabled:cursor-not-allowed disabled:text-muted"
              disabled={providerIds.length >= maxProviders || filteredProviders.length === 0}
              onClick={addShown}
              type="button"
            >
              Add shown
            </button>
          </div>
          <div className="mt-3 max-h-64 overflow-y-auto rounded-md border border-line">
            {filteredProviders.map((provider) => (
              <SelectableRow
                disabled={!providerIds.includes(provider.provider_id) && providerIds.length >= maxProviders}
                key={provider.provider_id}
                meta={providerMeta(provider)}
                onToggle={() => setProviderIds((current) => toggleSelection(current, provider.provider_id))}
                selected={providerIds.includes(provider.provider_id)}
                title={provider.provider_name}
              />
            ))}
            {filteredProviders.length === 0 ? <EmptyRow /> : null}
          </div>
        </SelectionPanel>

        <SelectionPanel
          countLabel="1 selected"
          onQueryChange={setMetricQuery}
          query={metricQuery}
          title="Metric"
        >
          <SelectedChips
            items={selectedMetric ? [{ id: selectedMetric.metric_id, label: selectedMetric.metric_name }] : []}
          />
          <div className="mt-3 max-h-64 overflow-y-auto rounded-md border border-line">
            <GroupedMetricRows
              metrics={filteredMetrics}
              onSelect={setMetricId}
              selectedMetricId={metricId}
            />
            {filteredMetrics.length === 0 ? <EmptyRow /> : null}
          </div>
        </SelectionPanel>

        <div className="rounded-md border border-line bg-cream/60 p-3">
          <label className="text-xs font-medium uppercase text-muted" htmlFor="compare-year">
            Year
          </label>
          <div className="mt-2 flex items-center gap-2 rounded-md border border-line bg-white px-3 py-2">
            <Calendar className="h-4 w-4 text-muted" aria-hidden="true" />
            <input
              className="w-full border-0 bg-transparent text-sm outline-none"
              defaultValue={year}
              id="compare-year"
              inputMode="numeric"
              name="year"
            />
          </div>
          <label className="mt-3 block text-xs font-medium uppercase text-muted" htmlFor="compare-benchmark">
            Benchmark group
          </label>
          <select
            className="mt-2 w-full rounded-md border border-line bg-white px-3 py-2 text-sm"
            defaultValue={selectedBenchmark}
            id="compare-benchmark"
            name="benchmark"
          >
            <option value="">None</option>
            {missionGroups.map((group) => (
              <option key={group} value={group}>
                {group} average
              </option>
            ))}
          </select>
          <button
            className="mt-4 w-full rounded-md bg-teal px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-line"
            disabled={providerIds.length === 0 || !metricId}
            type="submit"
          >
            Apply
          </button>
          <a
            className="mt-3 block text-center text-xs font-medium text-teal hover:underline"
            href={catalogMode === "raw" ? "/compare" : "/compare?catalog=raw"}
          >
            {catalogMode === "raw" ? "Use curated metrics" : "Advanced raw metrics"}
          </a>
        </div>
      </div>
    </form>
  );
}

function SelectionPanel({
  children,
  countLabel,
  onClear,
  onQueryChange,
  query,
  title
}: {
  children: ReactNode;
  countLabel: string;
  onClear?: () => void;
  onQueryChange: (value: string) => void;
  query: string;
  title: string;
}) {
  return (
    <fieldset className="min-w-0">
      <div className="flex items-center justify-between gap-3">
        <legend className="text-xs font-medium uppercase text-muted">{title}</legend>
        <div className="flex items-center gap-2">
          <span className="rounded-md border border-line bg-cream/60 px-2 py-1 text-xs text-muted">{countLabel}</span>
          {onClear ? (
            <button
              aria-label={`Clear ${title.toLowerCase()}`}
              className="rounded-md border border-line bg-white p-1 text-muted hover:text-ink"
              onClick={onClear}
              type="button"
            >
              <X className="h-3.5 w-3.5" aria-hidden="true" />
            </button>
          ) : null}
        </div>
      </div>
      <div className="mt-2 flex items-center gap-2 rounded-md border border-line bg-white px-3 py-2">
        <Search className="h-4 w-4 text-muted" aria-hidden="true" />
        <input
          className="w-full border-0 bg-transparent text-sm outline-none"
          onChange={(event) => onQueryChange(event.target.value)}
          placeholder={`Search ${title.toLowerCase()}`}
          value={query}
        />
      </div>
      {children}
    </fieldset>
  );
}

function SelectedChips({ items, onRemove }: { items: Array<{ id: string; label: string }>; onRemove?: (id: string) => void }) {
  return (
    <div className="mt-3 flex min-h-9 flex-wrap gap-2">
      {items.map((item) => (
        <span className="inline-flex max-w-full items-center gap-1 rounded-md border border-line bg-cream/60 px-2 py-1 text-xs" key={item.id}>
          <span className="truncate">{item.label}</span>
          {onRemove ? (
            <button aria-label={`Remove ${item.label}`} className="text-muted hover:text-ink" onClick={() => onRemove(item.id)} type="button">
              <X className="h-3 w-3" aria-hidden="true" />
            </button>
          ) : null}
        </span>
      ))}
    </div>
  );
}

function SelectableRow({
  disabled,
  meta,
  onToggle,
  selected,
  title
}: {
  disabled: boolean;
  meta: string;
  onToggle: () => void;
  selected: boolean;
  title: string;
}) {
  return (
    <button
      className="flex w-full items-start gap-3 border-b border-line px-3 py-2 text-left last:border-b-0 enabled:hover:bg-cream/60 disabled:cursor-not-allowed disabled:opacity-45"
      disabled={disabled}
      onClick={onToggle}
      type="button"
    >
      <span className={`mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded border ${selected ? "border-teal bg-teal text-white" : "border-line bg-white"}`}>
        {selected ? <Check className="h-3 w-3" aria-hidden="true" /> : null}
      </span>
      <span className="min-w-0">
        <span className="block truncate text-sm font-medium text-ink">{title}</span>
        <span className="block truncate text-xs text-muted">{meta}</span>
      </span>
    </button>
  );
}

function EmptyRow() {
  return <div className="px-3 py-6 text-center text-sm text-muted">No matches</div>;
}

function GroupedMetricRows({
  metrics,
  onSelect,
  selectedMetricId
}: {
  metrics: SelectableMetric[];
  onSelect: (metricId: string) => void;
  selectedMetricId: string;
}) {
  const rows: ReactNode[] = [];
  let currentGroup = "";

  for (const metric of metrics) {
    const group = metricGroup(metric);
    const showGroup = group !== currentGroup;
    currentGroup = group;
    rows.push(
      <div key={metric.metric_id}>
        {showGroup ? (
          <div className="border-b border-line bg-cream/60 px-3 py-1.5 text-xs font-semibold uppercase text-muted">
            {group}
          </div>
        ) : null}
        <SelectableRow
          disabled={false}
          meta={rawMetricName(metric) ? `Source: ${rawMetricName(metric)}` : metric.source_dataset}
          onToggle={() => onSelect(metric.metric_id)}
          selected={selectedMetricId === metric.metric_id}
          title={metric.metric_name}
        />
      </div>
    );
  }

  return <>{rows}</>;
}

function toggleSelection(current: string[], id: string) {
  if (current.includes(id)) return current.filter((item) => item !== id);
  if (current.length >= maxProviders) return current;
  return [...current, id];
}

function filterProviders(
  providers: Provider[],
  query: string,
  selectedIds: string[],
  groupFilter: string,
  stateFilter: string
) {
  const normalizedQuery = normalize(query);
  return providers
    .filter((provider) => {
      if (groupFilter && provider.mission_group !== groupFilter) return false;
      if (stateFilter && provider.state !== stateFilter) return false;
      if (!normalizedQuery) return true;
      return normalize(`${provider.provider_name} ${provider.state ?? ""} ${provider.mission_group ?? ""}`).includes(normalizedQuery);
    })
    .sort((a, b) => bySelectedThenName(a.provider_id, b.provider_id, a.provider_name, b.provider_name, selectedIds));
}

function providerMeta(provider: Provider) {
  return [provider.mission_group, provider.state].filter(Boolean).join(" · ") || "University";
}

function distinct(values: Array<string | null>) {
  return Array.from(new Set(values.filter((value): value is string => Boolean(value)))).sort();
}

function filterMetrics(metrics: SelectableMetric[], query: string, selectedId: string) {
  const normalizedQuery = normalize(query);
  return metrics
    .filter((metric) => {
      if (!normalizedQuery) return true;
      return normalize(`${metricGroup(metric)} ${metric.metric_name} ${rawMetricName(metric) ?? ""}`).includes(normalizedQuery);
    })
    .sort((a, b) => {
      const aSelected = a.metric_id === selectedId;
      const bSelected = b.metric_id === selectedId;
      if (aSelected !== bSelected) return aSelected ? -1 : 1;
      const groupCompare = metricGroup(a).localeCompare(metricGroup(b));
      if (groupCompare !== 0) return groupCompare;
      return a.metric_name.localeCompare(b.metric_name);
    })
    .slice(0, 40);
}

function metricGroup(metric: SelectableMetric) {
  return "catalog_group" in metric ? metric.catalog_group : metric.metric_group;
}

function rawMetricName(metric: SelectableMetric) {
  return "raw_metric_name" in metric ? metric.raw_metric_name : null;
}

function bySelectedThenName(aId: string, bId: string, aName: string, bName: string, selectedIds: string[]) {
  const aSelected = selectedIds.includes(aId);
  const bSelected = selectedIds.includes(bId);
  if (aSelected !== bSelected) return aSelected ? -1 : 1;
  return aName.localeCompare(bName);
}

function normalize(value: string) {
  return value.trim().toLowerCase();
}
