import { fetchInsightData } from "./spike-api";
import { uniIntelCatalogId } from "./a2ui-catalog";
import type {
  AgentSelection,
  A2UIMessage,
  ChartPayload,
  CompositionNode,
  InsightCatalogueEntry,
  MetricCardPayload,
  ResolvedInsightSelection,
  SelectedInsight
} from "./types";

export const DEFAULT_SURFACE_ID = "spike-insights";

function chartComponent(chart: SelectedInsight["chart"]) {
  switch (chart) {
    case "metric_card":
      return "MetricCard";
    case "trend_line":
    case "multi_trend":
      return "TrendLine";
    case "benchmark_bar":
      return "BenchmarkBar";
    default:
      return "RankingBar";
  }
}

function breakdownLabel(breakdown: SelectedInsight["breakdown"]) {
  switch (breakdown) {
    case "time":
      return "Over time";
    case "provider":
      return "By provider";
    case "mission_group":
      return "By mission group";
    case "state":
      return "By state";
  }
}

export function resolveSelection(
  selection: AgentSelection,
  catalogue: Map<string, InsightCatalogueEntry>
): ResolvedInsightSelection[] {
  return selection.insights
    .map((insight) => {
      const entry = catalogue.get(insight.id);
      if (!entry) return null;
      return {
        ...insight,
        name: entry.name,
        metricId: entry.metricId,
        group: entry.group
      };
    })
    .filter((item): item is ResolvedInsightSelection => item !== null);
}

export async function buildComposition(
  selection: AgentSelection,
  catalogue: Map<string, InsightCatalogueEntry>,
  options: { surfaceId?: string; isRefinement?: boolean } = {}
): Promise<{ messages: A2UIMessage[]; compositionTree: CompositionNode[]; dataSource: "live_api" | "mock_fallback" }> {
  const surfaceId = options.surfaceId ?? DEFAULT_SURFACE_ID;
  const messages: A2UIMessage[] = [];
  const compositionTree: CompositionNode[] = [];
  let dataSource: "live_api" | "mock_fallback" = "live_api";

  if (!options.isRefinement) {
    messages.push({
      version: "v0.9",
      createSurface: { surfaceId, catalogId: uniIntelCatalogId }
    });
  }

  const components: Record<string, unknown>[] = [];
  const dataModel: Record<string, unknown> = {
    title: selection.layout.title,
    rationale: selection.rationale
  };

  components.push({ id: "root", component: "Column", children: ["title", "rationale", "body"] });
  components.push({ id: "title", component: "Text", text: { path: "/title" }, variant: "h2" });
  components.push({ id: "rationale", component: "Text", text: { path: "/rationale" }, variant: "caption" });
  compositionTree.push({ component: "Column", id: "root" });

  if (selection.clarify && !selection.insights.length) {
    dataModel.clarify = selection.clarify;
    if (selection.unavailableNotes?.length) {
      dataModel.unavailableNotes = selection.unavailableNotes.join(" ");
    }
    components.push({ id: "body", component: "ClarifyPanel", dataPath: { path: "/clarify" }, notesPath: { path: "/unavailableNotes" } });
    compositionTree.push({ component: "ClarifyPanel", id: "body" });
  } else {
    components.push({ id: "body", component: "Column", children: [] });
    compositionTree.push({ component: "Column", id: "body" });

    const sectionIds: string[] = [];
    for (const [sectionIndex, section] of selection.layout.sections.entries()) {
      const sectionId = `section-${sectionIndex}`;
      sectionIds.push(sectionId);
      const cardIds: string[] = [];

      if (section.heading) {
        const headingId = `${sectionId}-heading`;
        dataModel[headingId] = section.heading;
        components.push({ id: headingId, component: "Text", text: { path: `/${headingId}` }, variant: "h3" });
        cardIds.push(headingId);
        compositionTree.push({ component: "Text", id: headingId, title: section.heading });
      }

      for (const itemId of section.itemIds) {
        const insight = selection.insights.find((item) => item.id === itemId);
        const entry = catalogue.get(itemId);
        if (!insight || !entry) continue;

        const cardId = `card-${itemId}`;
        const chartId = `chart-${itemId}`;
        cardIds.push(cardId);

        const fetched = await fetchInsightData(entry, insight);
        if (fetched.dataSource === "mock_fallback") dataSource = "mock_fallback";

        const dataPath = `/insights/${itemId}`;
        if (insight.chart === "metric_card") {
          const payload: MetricCardPayload = {
            title: entry.name,
            value: fetched.headline?.value ?? fetched.rows[0]?.value ?? null,
            unit: entry.unit,
            subtitle: fetched.headline?.subtitle ?? entry.sourceNote
          };
          dataModel[`insights`] = dataModel[`insights`] ?? {};
          (dataModel.insights as Record<string, unknown>)[itemId] = payload;
          components.push({
            id: cardId,
            component: "Card",
            child: chartId
          });
          components.push({
            id: chartId,
            component: "MetricCard",
            dataPath: { path: `${dataPath}` }
          });
          compositionTree.push({ component: "MetricCard", id: chartId, insightId: itemId, title: entry.name });
        } else {
          const payload: ChartPayload = {
            title: entry.name,
            subtitle: `${breakdownLabel(insight.breakdown)} · ${entry.group}`,
            rows: fetched.rows,
            unit: entry.unit,
            benchmark: fetched.benchmark
          };
          dataModel[`insights`] = dataModel[`insights`] ?? {};
          (dataModel.insights as Record<string, unknown>)[itemId] = payload;
          components.push({ id: cardId, component: "Card", child: chartId });
          components.push({
            id: chartId,
            component: chartComponent(insight.chart),
            dataPath: { path: `${dataPath}` }
          });
          compositionTree.push({
            component: chartComponent(insight.chart),
            id: chartId,
            insightId: itemId,
            title: entry.name
          });
        }
      }

      components.push({ id: sectionId, component: "Column", children: cardIds });
      compositionTree.push({ component: "Column", id: sectionId });
    }

    const bodyComponent = components.find((component) => component.id === "body");
    if (bodyComponent) bodyComponent.children = sectionIds;
  }

  messages.push({
    version: "v0.9",
    updateComponents: { surfaceId, components }
  });
  messages.push({
    version: "v0.9",
    updateDataModel: { surfaceId, path: "/", value: dataModel }
  });

  return { messages, compositionTree, dataSource };
}
