import type { Metric, MetricCatalogItem, Provider } from "@/lib/api";
import { MAX_COMPARE_PROVIDERS } from "@/lib/constants";

export type SelectableMetric = (Metric | MetricCatalogItem) & {
  metric_id: string;
};

export function toggleSelection(current: string[], id: string) {
  if (current.includes(id)) return current.filter((item) => item !== id);
  if (current.length >= MAX_COMPARE_PROVIDERS) return current;
  return [...current, id];
}

export function filterProviders(
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
      return normalize(
        `${provider.provider_name} ${provider.state ?? ""} ${provider.mission_group ?? ""}`
      ).includes(normalizedQuery);
    })
    .sort((a, b) =>
      bySelectedThenName(
        a.provider_id,
        b.provider_id,
        a.provider_name,
        b.provider_name,
        selectedIds
      )
    );
}

export function providerMeta(provider: Provider) {
  return [provider.mission_group, provider.state].filter(Boolean).join(" · ") || "University";
}

export function filterMetrics(metrics: SelectableMetric[], query: string, selectedId: string) {
  const normalizedQuery = normalize(query);
  return metrics
    .filter((metric) => {
      if (!normalizedQuery) return true;
      return normalize(
        `${metricGroup(metric)} ${metric.metric_name} ${rawMetricName(metric) ?? ""}`
      ).includes(normalizedQuery);
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

export function metricGroup(metric: SelectableMetric) {
  return "catalog_group" in metric ? metric.catalog_group : metric.metric_group;
}

export function rawMetricName(metric: SelectableMetric) {
  return "raw_metric_name" in metric ? metric.raw_metric_name : null;
}

function bySelectedThenName(
  aId: string,
  bId: string,
  aName: string,
  bName: string,
  selectedIds: string[]
) {
  const aSelected = selectedIds.includes(aId);
  const bSelected = selectedIds.includes(bId);
  if (aSelected !== bSelected) return aSelected ? -1 : 1;
  return aName.localeCompare(bName);
}

function normalize(value: string) {
  return value.trim().toLowerCase();
}
