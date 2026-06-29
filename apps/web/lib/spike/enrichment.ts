import type { ChartType, Breakdown } from "./types";

export interface EnrichmentOverlay {
  question: string;
  description: string;
  breakdowns: Breakdown[];
  defaultChart: ChartType;
  allowedCharts: ChartType[];
  keywords?: string[];
}

const FINANCE_BREAKDOWNS: Breakdown[] = ["time", "provider", "mission_group", "state"];
const STUDENT_BREAKDOWNS: Breakdown[] = ["time", "provider", "mission_group", "state"];
const QILT_BREAKDOWNS: Breakdown[] = ["time", "provider"];

export const ENRICHMENT_BY_ID: Record<string, EnrichmentOverlay> = {
  total_enrolments: {
    question: "How many students are enrolled across the sector?",
    description: "Total student headcount enrolments by provider and over time from Department student Section 2.",
    breakdowns: STUDENT_BREAKDOWNS,
    defaultChart: "trend_line",
    allowedCharts: ["trend_line", "ranking_bar", "benchmark_bar", "metric_card"],
    keywords: ["enrolments", "enrollment", "students", "headcount"]
  },
  total_student_load: {
    question: "What is total student load (EFTSL)?",
    description: "Equivalent full-time student load across providers and years.",
    breakdowns: STUDENT_BREAKDOWNS,
    defaultChart: "trend_line",
    allowedCharts: ["trend_line", "ranking_bar", "benchmark_bar", "metric_card"],
    keywords: ["load", "eftsl", "student load"]
  },
  postgraduate_enrolments: {
    question: "How are postgraduate enrolments tracking?",
    description: "Postgraduate research plus coursework enrolments by provider and over time.",
    breakdowns: STUDENT_BREAKDOWNS,
    defaultChart: "trend_line",
    allowedCharts: ["trend_line", "ranking_bar", "benchmark_bar", "metric_card"],
    keywords: ["postgraduate", "pg", "masters", "research students"]
  },
  postgraduate_load: {
    question: "What is postgraduate student load (EFTSL)?",
    description: "Combined postgraduate research and coursework load.",
    breakdowns: STUDENT_BREAKDOWNS,
    defaultChart: "trend_line",
    allowedCharts: ["trend_line", "ranking_bar", "benchmark_bar", "metric_card"],
    keywords: ["postgraduate load", "pg load", "eftsl"]
  },
  pg_coursework_load: {
    question: "What is postgraduate coursework load?",
    description: "EFTSL for postgraduate coursework students.",
    breakdowns: STUDENT_BREAKDOWNS,
    defaultChart: "ranking_bar",
    allowedCharts: ["trend_line", "ranking_bar", "benchmark_bar", "metric_card"],
    keywords: ["coursework", "pg coursework"]
  },
  pg_research_load: {
    question: "What is postgraduate research load?",
    description: "EFTSL for postgraduate research students.",
    breakdowns: STUDENT_BREAKDOWNS,
    defaultChart: "ranking_bar",
    allowedCharts: ["trend_line", "ranking_bar", "benchmark_bar", "metric_card"],
    keywords: ["research load", "hdr", "phd load"]
  },
  commencing_postgraduate_enrolments: {
    question: "How is postgraduate demand tracking via commencing enrolments?",
    description: "Commencing postgraduate enrolments as a demand proxy where applications/offers are unavailable.",
    breakdowns: STUDENT_BREAKDOWNS,
    defaultChart: "trend_line",
    allowedCharts: ["trend_line", "ranking_bar", "benchmark_bar", "metric_card"],
    keywords: ["commencing", "demand", "postgraduate demand", "new pg"]
  },
  total_revenue: {
    question: "What is total university revenue?",
    description: "Total revenues from continuing operations including deferred superannuation.",
    breakdowns: FINANCE_BREAKDOWNS,
    defaultChart: "ranking_bar",
    allowedCharts: ["trend_line", "ranking_bar", "benchmark_bar", "metric_card"],
    keywords: ["revenue", "income", "finance", "total revenue"]
  },
  total_expenses: {
    question: "What are total university expenses?",
    description: "Total expenses from continuing operations.",
    breakdowns: FINANCE_BREAKDOWNS,
    defaultChart: "trend_line",
    allowedCharts: ["trend_line", "ranking_bar", "benchmark_bar", "metric_card"],
    keywords: ["expenses", "costs", "spending"]
  },
  operating_margin: {
    question: "What is the operating margin across providers?",
    description: "Calculated operating margin percentage from operating result and total revenue.",
    breakdowns: FINANCE_BREAKDOWNS,
    defaultChart: "ranking_bar",
    allowedCharts: ["trend_line", "ranking_bar", "benchmark_bar", "metric_card"],
    keywords: ["margin", "operating margin", "profitability"]
  },
  net_operating_result: {
    question: "What is the net operating result?",
    description: "Operating result from continuing operations in dollars.",
    breakdowns: FINANCE_BREAKDOWNS,
    defaultChart: "trend_line",
    allowedCharts: ["trend_line", "ranking_bar", "benchmark_bar", "metric_card"],
    keywords: ["operating result", "surplus", "deficit"]
  },
  overseas_fee_income: {
    question: "How much overseas student fee income do universities earn?",
    description: "International student fee revenue from finance tables.",
    breakdowns: FINANCE_BREAKDOWNS,
    defaultChart: "ranking_bar",
    allowedCharts: ["trend_line", "ranking_bar", "benchmark_bar", "metric_card"],
    keywords: ["international", "overseas", "fee income", "international students"]
  },
  herdc_research_income: {
    question: "How much HERDC research income do universities receive?",
    description: "HERDC categories 1–4 research income time series.",
    breakdowns: FINANCE_BREAKDOWNS,
    defaultChart: "ranking_bar",
    allowedCharts: ["trend_line", "ranking_bar", "benchmark_bar", "metric_card"],
    keywords: ["research income", "herdc", "research funding"]
  },
  qilt_overall_experience: {
    question: "How do students rate overall educational experience?",
    description: "QILT SES positive rating for overall educational experience (undergraduate).",
    breakdowns: QILT_BREAKDOWNS,
    defaultChart: "ranking_bar",
    allowedCharts: ["ranking_bar", "trend_line", "metric_card"],
    keywords: ["experience", "qilt", "ses", "satisfaction", "student experience"]
  },
  qilt_teaching_quality: {
    question: "How do students rate teaching quality and engagement?",
    description: "QILT SES teaching quality positive rating.",
    breakdowns: QILT_BREAKDOWNS,
    defaultChart: "ranking_bar",
    allowedCharts: ["ranking_bar", "trend_line", "metric_card"],
    keywords: ["teaching", "engagement", "qilt"]
  },
  qilt_student_support: {
    question: "How do students rate support and services?",
    description: "QILT SES student support and services positive rating.",
    breakdowns: QILT_BREAKDOWNS,
    defaultChart: "ranking_bar",
    allowedCharts: ["ranking_bar", "trend_line", "metric_card"],
    keywords: ["support", "services", "student support"]
  },
  research_degree_completions: {
    question: "How many research degree completions occur?",
    description: "PhD and research masters completions from Section 14.",
    breakdowns: STUDENT_BREAKDOWNS,
    defaultChart: "trend_line",
    allowedCharts: ["trend_line", "ranking_bar", "benchmark_bar", "metric_card"],
    keywords: ["completions", "phd", "research degree"]
  },
  postgraduate_coursework_completions: {
    question: "How many postgraduate coursework completions occur?",
    description: "Postgraduate coursework award completions.",
    breakdowns: STUDENT_BREAKDOWNS,
    defaultChart: "trend_line",
    allowedCharts: ["trend_line", "ranking_bar", "benchmark_bar", "metric_card"],
    keywords: ["coursework completions", "pg completions"]
  }
};

export const UNAVAILABLE_CONCEPTS: { pattern: RegExp; label: string; closestIds: string[] }[] = [
  {
    pattern: /\bretention\b/i,
    label: "Retention rate",
    closestIds: ["commencing_postgraduate_enrolments", "qilt_overall_experience"]
  },
  {
    pattern: /\battrition\b/i,
    label: "Attrition rate",
    closestIds: ["commencing_postgraduate_enrolments"]
  },
  {
    pattern: /\bcompletion rate\b/i,
    label: "Completion rate (cohort)",
    closestIds: ["research_degree_completions", "postgraduate_coursework_completions"]
  },
  {
    pattern: /\b(applicant|offer rate|applications)\b/i,
    label: "Postgraduate applications/offers",
    closestIds: ["commencing_postgraduate_enrolments"]
  },
  {
    pattern: /\b(counsell|placement|partner)\b/i,
    label: "Counselling placements / partner breakdown",
    closestIds: ["postgraduate_enrolments", "commencing_postgraduate_enrolments"]
  }
];

export function defaultEnrichment(label: string, group: string, sourceNote: string): EnrichmentOverlay {
  const isQilt = group === "Student experience";
  const breakdowns = isQilt ? QILT_BREAKDOWNS : group.includes("Finance") ? FINANCE_BREAKDOWNS : STUDENT_BREAKDOWNS;
  return {
    question: `What does ${label} show?`,
    description: sourceNote,
    breakdowns,
    defaultChart: isQilt ? "ranking_bar" : "trend_line",
    allowedCharts: isQilt
      ? ["ranking_bar", "trend_line", "metric_card"]
      : ["trend_line", "ranking_bar", "benchmark_bar", "metric_card"]
  };
}
