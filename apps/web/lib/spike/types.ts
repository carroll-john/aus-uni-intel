export type ChartType = "metric_card" | "trend_line" | "multi_trend" | "ranking_bar" | "benchmark_bar";

export type Breakdown = "time" | "provider" | "mission_group" | "state";

export interface InsightCatalogueEntry {
  id: string;
  metricId: string;
  name: string;
  group: string;
  question: string;
  description: string;
  breakdowns: Breakdown[];
  defaultChart: ChartType;
  allowedCharts: ChartType[];
  scope: string;
  unit: string;
  sourceNote: string;
}

export interface SelectedInsight {
  id: string;
  breakdown: Breakdown;
  scope?: string;
  year?: number;
  chart: ChartType;
}

export interface AgentLayout {
  title: string;
  sections: { heading?: string; itemIds: string[] }[];
}

export interface AgentSelection {
  insights: SelectedInsight[];
  layout: AgentLayout;
  rationale: string;
  clarify?: { question: string; options: string[] };
  unavailableNotes?: string[];
}

export type SelectorKind = "llm" | "heuristic";

export interface ResolvedInsightSelection extends SelectedInsight {
  name: string;
  metricId: string;
  group: string;
}

export interface CompositionNode {
  component: string;
  id: string;
  insightId?: string;
  title?: string;
}

export interface ComposeLogEntry {
  turn: number;
  intent: string;
  selector: SelectorKind;
  rationale: string;
  resolvedInsights: ResolvedInsightSelection[];
  compositionTree: CompositionNode[];
  clarify?: { question: string; options: string[] };
  unavailableNotes?: string[];
  rawMessages: A2UIMessage[];
  dataSource: "live_api" | "mock_fallback";
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ComposeRequest {
  messages: ChatMessage[];
  priorSelection?: AgentSelection;
  surfaceId?: string;
  isRefinement?: boolean;
}

export interface ComposeResponse {
  selection: AgentSelection;
  messages: A2UIMessage[];
  log: ComposeLogEntry;
}

export type A2UIMessage =
  | { version: "v0.9"; createSurface: { surfaceId: string; catalogId: string } }
  | {
      version: "v0.9";
      updateComponents: {
        surfaceId: string;
        components: Record<string, unknown>[];
      };
    }
  | {
      version: "v0.9";
      updateDataModel: {
        surfaceId: string;
        path: string;
        value: unknown;
      };
    };

export interface ChartPayload {
  rows: Record<string, unknown>[];
  unit?: string;
  title: string;
  subtitle?: string;
  benchmark?: { value: number; label: string };
}

export interface MetricCardPayload {
  title: string;
  value: number | null;
  unit: string;
  subtitle: string;
}
