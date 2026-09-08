import { getMetricCatalog, type MetricCatalogItem } from "@/lib/api";
import { defaultEnrichment, ENRICHMENT_BY_ID } from "./enrichment";
import type { InsightCatalogueEntry } from "./types";

function mergeEntry(item: MetricCatalogItem & { metric_id: string }): InsightCatalogueEntry {
  const overlay = ENRICHMENT_BY_ID[item.catalog_item_id] ?? defaultEnrichment(item.metric_name, item.catalog_group, item.source_note);
  return {
    id: item.catalog_item_id,
    metricId: item.metric_id,
    name: item.metric_name,
    group: item.catalog_group,
    question: overlay.question,
    description: overlay.description,
    breakdowns: overlay.breakdowns,
    defaultChart: overlay.defaultChart,
    allowedCharts: overlay.allowedCharts,
    scope: item.preferred_scope ?? "Student",
    unit: item.unit,
    sourceNote: item.source_note
  };
}

export async function loadCatalogue(): Promise<{ entries: InsightCatalogueEntry[]; source: "live_api" | "mock_fallback" }> {
  try {
    const items = await getMetricCatalog();
    const selectable = items.filter(
      (item): item is MetricCatalogItem & { metric_id: string } => Boolean(item.metric_id && item.selectable)
    );
    if (!selectable.length) {
      return { entries: buildFallbackCatalogue(), source: "mock_fallback" };
    }
    const entries = selectable.map(mergeEntry);
    const missingOverlay = entries.filter((entry) => !ENRICHMENT_BY_ID[entry.id]);
    if (process.env.NODE_ENV !== "production" && missingOverlay.length) {
      console.warn(
        "[spike] Catalogue entries without hand-authored enrichment:",
        missingOverlay.map((entry) => entry.id)
      );
    }
    return { entries, source: "live_api" };
  } catch (error) {
    console.error("[spike] Failed to load /metric-catalog, using fallback catalogue:", error);
    return { entries: buildFallbackCatalogue(), source: "mock_fallback" };
  }
}

function buildFallbackCatalogue(): InsightCatalogueEntry[] {
  const stubs: Array<{ id: string; metricId: string; name: string; group: string; scope: string; unit: string; sourceNote: string }> = [
    {
      id: "total_enrolments",
      metricId: "student_total_enrolments",
      name: "Total enrolments",
      group: "Students and load",
      scope: "Student",
      unit: "count",
      sourceNote: "Department student Section 2 provider table."
    },
    {
      id: "postgraduate_enrolments",
      metricId: "student_postgraduate_total_enrolments",
      name: "Postgraduate enrolments",
      group: "Students and load",
      scope: "Student",
      unit: "count",
      sourceNote: "Department student Section 2 provider table."
    },
    {
      id: "total_revenue",
      metricId: "finance_total_revenues_from_continuing_operations_including_deferred_superannuation",
      name: "Total revenue (continuing operations) $",
      group: "Finance and funding",
      scope: "Total Institution",
      unit: "AUD",
      sourceNote: "Department provider finance tables."
    },
    {
      id: "herdc_research_income",
      metricId: "herdc_research_income_total",
      name: "HERDC research income (Cat 1-4) $",
      group: "Research",
      scope: "HERDC",
      unit: "AUD",
      sourceNote: "HERDC research income time series."
    },
    {
      id: "qilt_overall_experience",
      metricId: "qilt_overall_educational_experience_positive_rating",
      name: "Overall educational experience positive rating",
      group: "Student experience",
      scope: "QILT undergraduate",
      unit: "%",
      sourceNote: "QILT SES provider-level tables."
    }
  ];
  return stubs.map((stub) => {
    const overlay = ENRICHMENT_BY_ID[stub.id] ?? defaultEnrichment(stub.name, stub.group, stub.sourceNote);
    return {
      id: stub.id,
      metricId: stub.metricId,
      name: stub.name,
      group: stub.group,
      question: overlay.question,
      description: overlay.description,
      breakdowns: overlay.breakdowns,
      defaultChart: overlay.defaultChart,
      allowedCharts: overlay.allowedCharts,
      scope: stub.scope,
      unit: stub.unit,
      sourceNote: stub.sourceNote
    };
  });
}

export function catalogueById(entries: InsightCatalogueEntry[]): Map<string, InsightCatalogueEntry> {
  return new Map(entries.map((entry) => [entry.id, entry]));
}

export function catalogueForAgent(entries: InsightCatalogueEntry[]) {
  return entries.map((entry) => ({
    id: entry.id,
    name: entry.name,
    group: entry.group,
    question: entry.question,
    description: entry.description,
    breakdowns: entry.breakdowns,
    defaultChart: entry.defaultChart,
    allowedCharts: entry.allowedCharts
  }));
}
