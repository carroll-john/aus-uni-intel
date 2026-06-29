import { generateObject } from "ai";
import { createOpenAI } from "@ai-sdk/openai";
import { createGoogleGenerativeAI } from "@ai-sdk/google";
import { z } from "zod";
import { ENRICHMENT_BY_ID, UNAVAILABLE_CONCEPTS } from "./enrichment";
import type {
  AgentSelection,
  Breakdown,
  ChartType,
  ChatMessage,
  InsightCatalogueEntry,
  SelectorKind,
  SelectedInsight
} from "./types";

const breakdownSchema = z.enum(["time", "provider", "mission_group", "state"]);
const chartSchema = z.enum(["metric_card", "trend_line", "multi_trend", "ranking_bar", "benchmark_bar"]);

const selectionSchema = z.object({
  insights: z.array(
    z.object({
      id: z.string(),
      breakdown: breakdownSchema,
      scope: z.string().optional(),
      year: z.number().optional(),
      chart: chartSchema
    })
  ),
  layout: z.object({
    title: z.string(),
    sections: z.array(
      z.object({
        heading: z.string().optional(),
        itemIds: z.array(z.string())
      })
    )
  }),
  rationale: z.string(),
  clarify: z
    .object({
      question: z.string(),
      options: z.array(z.string())
    })
    .optional()
});

function tokenize(text: string) {
  return text
    .toLowerCase()
    .split(/[^a-z0-9]+/)
    .filter((token) => token.length > 2);
}

function scoreEntry(entry: InsightCatalogueEntry, tokens: string[]) {
  const haystack = [
    entry.name,
    entry.group,
    entry.question,
    entry.description,
    ...(ENRICHMENT_BY_ID[entry.id]?.keywords ?? [])
  ]
    .join(" ")
    .toLowerCase();
  let score = 0;
  for (const token of tokens) {
    if (haystack.includes(token)) score += 2;
  }
  return score;
}

function inferBreakdown(intent: string, entry: InsightCatalogueEntry): Breakdown {
  const lower = intent.toLowerCase();
  if (/\b(mission group|go8|atn|peer group)\b/.test(lower) && entry.breakdowns.includes("mission_group")) {
    return "mission_group";
  }
  if (/\b(state|nsw|vic|qld)\b/.test(lower) && entry.breakdowns.includes("state")) {
    return "state";
  }
  if (/\b(over time|trend|year|histor)\b/.test(lower) && entry.breakdowns.includes("time")) {
    return "time";
  }
  if (/\b(by provider|universit|rank|compare providers|partner)\b/.test(lower) && entry.breakdowns.includes("provider")) {
    return "provider";
  }
  return entry.defaultChart === "trend_line" ? "time" : "provider";
}

function inferChart(breakdown: Breakdown, entry: InsightCatalogueEntry): ChartType {
  if (breakdown === "time") return entry.allowedCharts.includes("trend_line") ? "trend_line" : entry.defaultChart;
  if (breakdown === "mission_group" || breakdown === "state") {
    return entry.allowedCharts.includes("benchmark_bar") ? "benchmark_bar" : entry.defaultChart;
  }
  return entry.allowedCharts.includes("ranking_bar") ? "ranking_bar" : entry.defaultChart;
}

function detectUnavailable(intent: string, catalogue: InsightCatalogueEntry[]) {
  const notes: string[] = [];
  const closestIds = new Set<string>();
  for (const concept of UNAVAILABLE_CONCEPTS) {
    if (concept.pattern.test(intent)) {
      notes.push(`${concept.label} is not available in the catalogue (no fabricated metrics).`);
      concept.closestIds.forEach((id) => closestIds.add(id));
    }
  }
  return { notes, closestIds: [...closestIds].filter((id) => catalogue.some((entry) => entry.id === id)) };
}

export function heuristicSelect(
  intent: string,
  catalogue: InsightCatalogueEntry[],
  priorSelection?: AgentSelection
): { selection: AgentSelection; selector: SelectorKind } {
  const { notes, closestIds } = detectUnavailable(intent, catalogue);
  const tokens = tokenize(intent);
  const lower = intent.toLowerCase();

  const addMatch = /\b(add|include|also|plus)\b/.test(lower);
  const priorInsights = addMatch && priorSelection ? priorSelection.insights : [];

  const ranked = catalogue
    .map((entry) => ({ entry, score: scoreEntry(entry, tokens) }))
    .filter((item) => item.score > 0 || closestIds.includes(item.entry.id))
    .sort((a, b) => b.score - a.score);

  if (!ranked.length && !priorInsights.length) {
    const options = catalogue.slice(0, 5).map((entry) => `${entry.name} (${entry.group})`);
    return {
      selector: "heuristic",
      selection: {
        insights: [],
        layout: { title: "Clarify your request", sections: [] },
        rationale: "No catalogue match from keywords; asking user to clarify.",
        clarify: {
          question: "I couldn't match your request to a known insight. Which area do you want?",
          options
        },
        unavailableNotes: notes.length ? notes : undefined
      }
    };
  }

  const picks = ranked.slice(0, addMatch ? 2 : 3).map(({ entry }) => {
    const breakdown = inferBreakdown(intent, entry);
    const chart = inferChart(breakdown, entry);
    return {
      id: entry.id,
      breakdown,
      chart,
      scope: entry.scope,
      year: 2024
    } satisfies SelectedInsight;
  });

  const merged = [...priorInsights];
  for (const pick of picks) {
    if (!merged.some((item) => item.id === pick.id)) merged.push(pick);
  }

  const itemIds = merged.map((item) => item.id);
  const title =
    merged.length === 1
      ? catalogue.find((entry) => entry.id === merged[0].id)?.name ?? "Insight view"
      : "Composed insight view";

  return {
    selector: "heuristic",
    selection: {
      insights: merged,
      layout: {
        title,
        sections: [{ heading: "Selected insights", itemIds }]
      },
      rationale: `Heuristic keyword match selected ${merged.map((item) => item.id).join(", ")}.`,
      unavailableNotes: notes.length ? notes : undefined,
      clarify: notes.length && !merged.length
        ? {
            question: `${notes.join(" ")} Did you mean one of these available insights?`,
            options: closestIds.map((id) => catalogue.find((entry) => entry.id === id)?.name ?? id)
          }
        : undefined
    }
  };
}

function resolveLlmProvider() {
  if (process.env.OPENAI_API_KEY) {
    return createOpenAI({ apiKey: process.env.OPENAI_API_KEY })("gpt-4o-mini");
  }
  if (process.env.GOOGLE_GENERATIVE_AI_API_KEY) {
    return createGoogleGenerativeAI({ apiKey: process.env.GOOGLE_GENERATIVE_AI_API_KEY })("gemini-2.0-flash");
  }
  return null;
}

export async function llmSelect(
  messages: ChatMessage[],
  catalogue: InsightCatalogueEntry[],
  priorSelection?: AgentSelection
): Promise<{ selection: AgentSelection; selector: SelectorKind } | null> {
  const model = resolveLlmProvider();
  if (!model) return null;

  const catalogueJson = catalogue.map((entry) => ({
    id: entry.id,
    name: entry.name,
    group: entry.group,
    question: entry.question,
    description: entry.description,
    breakdowns: entry.breakdowns,
    allowedCharts: entry.allowedCharts
  }));

  const system = `You select pre-computed university intelligence insights from a fixed catalogue.
Rules:
- Only use insight ids from the catalogue. Never invent metrics or numbers.
- If the user asks for unavailable metrics (retention, applications, partner-specific data not in catalogue), set clarify with alternatives.
- Map "by partner" to provider breakdown when possible.
- On refinement ("add X", "split by Y"), merge with prior selection when provided.
- Return empty insights with clarify when ambiguous.`;

  const userContext = [
    `Catalogue:\n${JSON.stringify(catalogueJson, null, 2)}`,
    priorSelection ? `Prior selection:\n${JSON.stringify(priorSelection, null, 2)}` : null
  ]
    .filter(Boolean)
    .join("\n\n");

  try {
    const result = await generateObject({
      model,
      schema: selectionSchema,
      system,
      messages: [
        { role: "system", content: userContext },
        ...messages.map((message) => ({ role: message.role, content: message.content }))
      ]
    });
    return { selection: result.object as AgentSelection, selector: "llm" };
  } catch (error) {
    console.error("[spike] LLM selection failed:", error);
    return null;
  }
}

export function validateSelection(selection: AgentSelection, catalogue: InsightCatalogueEntry[]): AgentSelection {
  const byId = new Map(catalogue.map((entry) => [entry.id, entry]));
  const validInsights = selection.insights.filter((insight) => {
    const entry = byId.get(insight.id);
    if (!entry) return false;
    return entry.breakdowns.includes(insight.breakdown) && entry.allowedCharts.includes(insight.chart);
  });

  if (!validInsights.length && !selection.clarify) {
    return {
      ...selection,
      insights: [],
      clarify: {
        question: "I couldn't validate the selected insights against the catalogue. Please choose an available insight.",
        options: catalogue.slice(0, 6).map((entry) => entry.name)
      }
    };
  }

  return { ...selection, insights: validInsights };
}

export async function runSelection(
  messages: ChatMessage[],
  catalogue: InsightCatalogueEntry[],
  priorSelection?: AgentSelection
): Promise<{ selection: AgentSelection; selector: SelectorKind }> {
  const latestIntent = [...messages].reverse().find((message) => message.role === "user")?.content ?? "";
  const llmResult = await llmSelect(messages, catalogue, priorSelection);
  const raw = llmResult ?? heuristicSelect(latestIntent, catalogue, priorSelection);
  return { ...raw, selection: validateSelection(raw.selection, catalogue) };
}
