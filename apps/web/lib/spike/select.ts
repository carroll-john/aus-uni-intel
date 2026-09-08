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

const STOPWORDS = new Set([
  "show",
  "the",
  "and",
  "for",
  "by",
  "how",
  "are",
  "what",
  "with",
  "from",
  "over",
  "time",
  "rank",
  "ranked",
  "ranking",
  "provider",
  "providers",
  "university",
  "universities",
  "view",
  "breakdown",
  "compare",
  "tracking",
  "track",
  "also",
  "add",
  "include",
  "now",
  "please",
  "give",
  "me",
  "want",
  "see",
  "split",
  "instead",
  "individual",
  "across",
  "sector",
  "about",
  "into",
  "this",
  "that",
  "year",
  "2024",
  "2023"
]);

const DOMAIN_HINTS: { pattern: RegExp; groups: string[] }[] = [
  { pattern: /\b(revenue|finance|expense|margin|surplus|deficit|fee income|grants|salaries|assets|liabilities|cash flow|hecs)\b/i, groups: ["Finance and funding", "Revenue lines", "Expense lines", "Salaries", "Financial sustainability"] },
  { pattern: /\b(enrol|student load|eftsl|postgraduate|undergraduate|commencing|coursework|hdr|phd)\b/i, groups: ["Students and load", "Demand"] },
  { pattern: /\b(qilt|ses|experience|satisfaction|teaching quality|support services|skills development)\b/i, groups: ["Student experience"] },
  { pattern: /\b(herdc|research income|research load|completions|research degree)\b/i, groups: ["Research", "Students and load"] }
];

type ScoredEntry = {
  entry: InsightCatalogueEntry;
  score: number;
  reasons: string[];
};

function normalize(text: string) {
  return text.toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
}

function tokenize(text: string) {
  return normalize(text)
    .split(/\s+/)
    .filter((token) => token.length > 2 && !STOPWORDS.has(token));
}

function phrasesFrom(text: string) {
  const words = normalize(text).split(/\s+/).filter(Boolean);
  const phrases: string[] = [];
  for (let size = 2; size <= 4; size += 1) {
    for (let index = 0; index <= words.length - size; index += 1) {
      phrases.push(words.slice(index, index + size).join(" "));
    }
  }
  return phrases;
}

function entryKeywords(entry: InsightCatalogueEntry) {
  const overlay = ENRICHMENT_BY_ID[entry.id];
  return [
    ...(overlay?.keywords ?? []),
    entry.name,
    entry.id.replaceAll("_", " "),
    entry.group,
    entry.question
  ].map(normalize);
}

function inferDomainGroups(intent: string) {
  const groups = new Set<string>();
  for (const hint of DOMAIN_HINTS) {
    if (hint.pattern.test(intent)) hint.groups.forEach((group) => groups.add(group));
  }
  return groups;
}

function scoreEntry(entry: InsightCatalogueEntry, intent: string, tokens: string[], domainGroups: Set<string>): ScoredEntry {
  const reasons: string[] = [];
  let score = 0;
  const normalizedIntent = normalize(intent);
  const keywords = entryKeywords(entry);

  for (const keyword of keywords) {
    if (keyword.length < 4) continue;
    if (normalizedIntent.includes(keyword)) {
      score += 12;
      reasons.push(`phrase "${keyword}"`);
    }
  }

  for (const phrase of phrasesFrom(intent)) {
    if (phrase.length < 5 || STOPWORDS.has(phrase)) continue;
    for (const keyword of keywords) {
      if (keyword.includes(phrase) || phrase.includes(keyword)) {
        score += 8;
        reasons.push(`partial phrase "${phrase}"`);
        break;
      }
    }
  }

  for (const token of tokens) {
    const idTokens = entry.id.split("_");
    if (idTokens.includes(token)) {
      score += 6;
      reasons.push(`id token "${token}"`);
      continue;
    }
    for (const keyword of keywords) {
      const keywordTokens = keyword.split(/\s+/);
      if (keywordTokens.includes(token)) {
        score += 3;
        reasons.push(`keyword token "${token}"`);
        break;
      }
    }
  }

  if (domainGroups.size) {
    if (domainGroups.has(entry.group)) {
      score += 5;
      reasons.push(`domain ${entry.group}`);
    } else {
      score -= 8;
      reasons.push(`domain mismatch (${entry.group})`);
    }
  }

  const distinguishing = ["postgraduate", "herdc", "qilt", "overseas", "operating", "commencing", "coursework", "international"];
  for (const word of distinguishing) {
    if (!normalizedIntent.includes(word)) continue;
    const entryText = `${entry.id} ${entry.name}`.toLowerCase();
    if (!entryText.includes(word)) {
      score -= 15;
      reasons.push(`missing qualifier "${word}"`);
    }
  }

  return { entry, score, reasons: [...new Set(reasons)] };
}

function inferBreakdown(intent: string, entry: InsightCatalogueEntry): Breakdown {
  const lower = intent.toLowerCase();
  if (/\b(mission group|go8|atn|peer group|peer benchmark)\b/.test(lower) && entry.breakdowns.includes("mission_group")) {
    return "mission_group";
  }
  if (/\b(state|nsw|vic|qld|wa|sa|tas|act|nt)\b/.test(lower) && entry.breakdowns.includes("state")) {
    return "state";
  }
  if (/\b(over time|trend|histor|year on year|time series)\b/.test(lower) && entry.breakdowns.includes("time")) {
    return "time";
  }
  if (/\b(by provider|rank|ranked|universit|compare providers|provider level)\b/.test(lower) && entry.breakdowns.includes("provider")) {
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

function intentClauses(intent: string) {
  return intent
    .split(/\band\b|,|;/i)
    .map((part) => part.trim())
    .filter((part) => part.length > 0);
}

function pickInsightsFromRanked(ranked: ScoredEntry[], intent: string, maxPicks: number) {
  if (!ranked.length) return [];

  const clauses = intentClauses(intent);
  const picks: ScoredEntry[] = [];

  if (clauses.length > 1) {
    for (const clause of clauses) {
      const clauseTokens = tokenize(clause);
      const clauseDomains = inferDomainGroups(clause);
      const clauseRanked = ranked
        .map((item) => scoreEntry(item.entry, clause, clauseTokens, clauseDomains))
        .filter((item) => item.score >= 8)
        .sort((a, b) => b.score - a.score);
      if (clauseRanked[0]) picks.push(clauseRanked[0]);
    }
  }

  if (!picks.length) {
    const top = ranked[0];
    const threshold = Math.max(10, top.score * 0.65);
    const limit = intentClauses(intent).length > 1 ? maxPicks : 1;
    for (const item of ranked) {
      if (item.score < threshold) break;
      if (picks.length >= limit) break;
      picks.push(item);
    }
    if (!picks.length && top.score >= 6) picks.push(top);
  }

  const unique = new Map<string, ScoredEntry>();
  for (const pick of picks) unique.set(pick.entry.id, pick);
  return [...unique.values()].slice(0, maxPicks);
}

export function heuristicSelect(
  intent: string,
  catalogue: InsightCatalogueEntry[],
  priorSelection?: AgentSelection
): { selection: AgentSelection; selector: SelectorKind } {
  const { notes, closestIds } = detectUnavailable(intent, catalogue);
  const tokens = tokenize(intent);
  const domainGroups = inferDomainGroups(intent);
  const lower = intent.toLowerCase();

  const addMatch = /\b(add|include|also|plus)\b/.test(lower);
  const priorInsights = addMatch && priorSelection ? priorSelection.insights : [];
  const maxPicks = addMatch ? 1 : 2;

  const ranked = catalogue
    .map((entry) => scoreEntry(entry, intent, tokens, domainGroups))
    .filter((item) => item.score > 0 || closestIds.includes(item.entry.id))
    .sort((a, b) => b.score - a.score);

  if (!ranked.length && !priorInsights.length) {
    const options = catalogue.slice(0, 6).map((entry) => `${entry.name} (${entry.group})`);
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

  const chosen = pickInsightsFromRanked(ranked, intent, maxPicks);
  const picks = chosen.map(({ entry }) => {
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

  const matchSummary = chosen
    .map((item) => `${item.entry.name} (score ${item.score}: ${item.reasons.slice(0, 3).join(", ")})`)
    .join("; ");

  const itemIds = merged.map((item) => item.id);
  const title =
    merged.length === 1
      ? catalogue.find((entry) => entry.id === merged[0].id)?.name ?? "Insight view"
      : "Composed insight view";

  const lowConfidence = chosen.length === 0 || (ranked[0]?.score ?? 0) < 8;

  return {
    selector: "heuristic",
    selection: {
      insights: merged,
      layout: {
        title,
        sections: [{ heading: "Selected insights", itemIds }]
      },
      rationale: lowConfidence
        ? `Low-confidence heuristic match. Top candidates: ${ranked
            .slice(0, 4)
            .map((item) => `${item.entry.name} (${item.score})`)
            .join(", ")}. Selected: ${merged.map((item) => item.id).join(", ") || "none"}.`
        : `Heuristic match: ${matchSummary || merged.map((item) => item.id).join(", ")}.`,
      unavailableNotes: notes.length ? notes : undefined,
      clarify:
        lowConfidence && !merged.length
          ? {
              question: "I'm not confident which insight you mean. Did you want one of these?",
              options: ranked.slice(0, 5).map((item) => item.entry.name)
            }
          : notes.length && !merged.length
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

  const system = `You select pre-computed university intelligence insights from a fixed catalogue for Australian higher education public data.

Rules:
- Only use insight ids from the catalogue. Never invent metrics or numbers.
- Select the MINIMUM set of insights that answer the user's question — usually 1-2, rarely 3.
- Match on the specific metric asked for (e.g. "total revenue" -> total_revenue, NOT total_enrolments).
- Do NOT select insights just because they share a word like "total" or "postgraduate".
- If the user asks for unavailable metrics (retention, applications, partner-specific data not in catalogue), set clarify with alternatives and return empty insights.
- Map "by partner" to provider breakdown when possible.
- On refinement ("add X", "split by Y"), merge with prior selection when provided.
- Return empty insights with clarify when ambiguous.
- Pick breakdown and chart type from allowed options based on intent (time -> trend_line, by provider -> ranking_bar, by mission group -> benchmark_bar).`;

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
