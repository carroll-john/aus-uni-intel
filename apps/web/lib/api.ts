export type Provider = {
  provider_id: string;
  provider_name: string;
  state: string | null;
  provider_type: string;
  is_public: boolean;
  website: string | null;
  mission_group: string | null;
  table_classification: string | null;
};

export type Metric = {
  metric_id: string;
  metric_name: string;
  metric_group: string;
  unit: string;
  value_type: string;
  definition: string;
  source_agency: string;
  source_dataset: string;
  source_table: string | null;
  source_line_item: string | null;
  is_calculated: boolean;
  calculation_method: string | null;
};

export type MetricCatalogItem = Omit<Metric, "metric_id"> & {
  metric_id: string | null;
  raw_metric_name: string | null;
  raw_metric_group: string | null;
  catalog_group: string;
  catalog_item_id: string;
  preferred_scope: string | null;
  source_status: "available" | "calculated_needed" | "missing";
  source_note: string;
  selectable: boolean;
};

export type FactRow = {
  provider_id?: string;
  provider_name?: string;
  metric_id: string;
  metric_name: string;
  metric_group?: string;
  reporting_year: number;
  dimension_scope: string;
  value: number;
  unit: string;
  definition?: string;
  source_dataset?: string;
  calculation_method?: string | null;
};

export type SourceFile = {
  source_file_id: string;
  dataset_id: string;
  source_name: string;
  source_url: string;
  file_format: string;
  reporting_year: number | null;
  downloaded_at: string;
  checksum_sha256: string;
  row_count: number;
  license: string | null;
  publication_date: string | null;
  notes: string | null;
};

export type QualityCheck = {
  run_id?: string;
  source_file_id?: string | null;
  source_name?: string | null;
  check_name: string;
  status: "pass" | "warn" | "fail";
  severity: "info" | "warning" | "error";
  observed_value: string | null;
  expected_value: string | null;
  details: string | null;
  created_at?: string;
};

export type Overview = {
  summary: Record<string, number | string | null>;
  kpis: FactRow[];
  top_rankings: FactRow[];
  quality: QualityCheck[];
};

export type BenchmarkRow = {
  group_value: string;
  reporting_year: number;
  average: number;
  median: number;
  minimum: number;
  maximum: number;
  provider_count: number;
  unit: string;
};

export type BenchmarkResponse = {
  group_by: "mission_group" | "state";
  rows: BenchmarkRow[];
};

export type MetricInsightRank = {
  label?: string | null;
  rank?: number;
  of?: number;
  value?: number;
};

export type MetricInsightChange = {
  year: number;
  from_value: number;
  absolute: number;
  percent: number;
};

export type MetricInsight = {
  provider: Provider;
  metric: Metric;
  year: number;
  scope: string;
  value: number;
  unit: string;
  current: FactRow;
  trend: FactRow[];
  ranks: {
    national: MetricInsightRank | null;
    mission_group: MetricInsightRank | null;
    state: MetricInsightRank | null;
  };
  rank_move: {
    year: number;
    from_rank: number;
    to_rank: number;
    places: number;
  } | null;
  medians: {
    national: number | null;
    mission_group: number | null;
    state: number | null;
  };
  changes: Record<string, MetricInsightChange>;
  source: {
    source_name: string | null;
    source_url: string | null;
    license: string | null;
    publication_date: string | null;
  };
};

const API_BASE_URL =
  process.env.API_BASE_URL || process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

export class ApiError extends Error {
  status: number;
  path: string;

  constructor(path: string, status: number) {
    super(`API ${path} failed with ${status}`);
    this.name = "ApiError";
    this.path = path;
    this.status = status;
  }
}

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, { cache: "no-store" });
  if (!response.ok) {
    throw new ApiError(path, response.status);
  }
  return response.json() as Promise<T>;
}

export function getOverview() {
  return getJson<Overview>("/overview");
}

export function getProviders() {
  return getJson<Provider[]>("/providers");
}

export function getMetrics() {
  return getJson<Metric[]>("/metrics");
}

export function getMetricCatalog(includeMissing = false) {
  const params = new URLSearchParams();
  if (includeMissing) params.set("include_missing", "true");
  const query = params.toString();
  return getJson<MetricCatalogItem[]>(`/metric-catalog${query ? `?${query}` : ""}`);
}

export function getRankings(
  metricId: string,
  year?: string,
  scope?: string,
  limit = 25,
  filters: { missionGroup?: string; state?: string } = {}
) {
  const params = new URLSearchParams({ metric_id: metricId, limit: String(limit) });
  if (year) params.set("year", year);
  if (scope) params.set("scope", scope);
  if (filters.missionGroup) params.set("mission_group", filters.missionGroup);
  if (filters.state) params.set("state", filters.state);
  return getJson<FactRow[]>(`/rankings?${params.toString()}`);
}

export function getBenchmarks(
  metricId: string,
  options: {
    year?: string;
    scope?: string;
    groupBy?: "mission_group" | "state";
    missionGroup?: string;
  } = {}
) {
  const params = new URLSearchParams({ metric_id: metricId });
  if (options.year) params.set("year", options.year);
  if (options.scope) params.set("scope", options.scope);
  if (options.groupBy) params.set("group_by", options.groupBy);
  if (options.missionGroup) params.set("mission_group", options.missionGroup);
  return getJson<BenchmarkResponse>(`/benchmarks?${params.toString()}`);
}

export function getProfile(providerId: string) {
  return getJson<{ provider: Provider; facts: FactRow[] }>(`/provider/${providerId}/profile`);
}

export function getMetricInsight(
  providerId: string,
  metricId: string,
  year?: string,
  scope?: string
) {
  const params = new URLSearchParams({ metric_id: metricId });
  if (year) params.set("year", year);
  if (scope) params.set("scope", scope);
  return getJson<MetricInsight>(`/provider/${providerId}/metric-insight?${params.toString()}`);
}

export function getCompare(providerIds: string[], metricIds: string[], year?: string) {
  const params = new URLSearchParams({
    provider_ids: providerIds.join(","),
    metric_ids: metricIds.join(","),
  });
  if (year) params.set("year", year);
  return getJson<FactRow[]>(`/compare?${params.toString()}`);
}

export function getTrends(metricId: string, providerId?: string, scope?: string) {
  const params = new URLSearchParams({ metric_id: metricId });
  if (providerId) params.set("provider_id", providerId);
  if (scope) params.set("scope", scope);
  return getJson<FactRow[]>(`/trends?${params.toString()}`);
}

export function getSources() {
  return getJson<SourceFile[]>("/sources");
}

export function getQuality() {
  return getJson<QualityCheck[]>("/quality?limit=100");
}
