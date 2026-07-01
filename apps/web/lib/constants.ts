// Shared domain defaults and presentation constants. Avoid hard-coding these
// values inline across pages/components.

export const DEFAULT_METRIC_ID =
  "finance_total_revenues_from_continuing_operations_including_deferred_superannuation";

export const DEFAULT_YEAR = "2024";

export const DEFAULT_COMPARE_PROVIDER_IDS = [
  "university_of_sydney",
  "university_of_melbourne",
  "monash_university",
];

export const MAX_COMPARE_PROVIDERS = 5;

// Provider id of the committed public-university sector aggregate row.
export const SECTOR_PROVIDER_ID = "sector_all_pub2";

// The four headline metrics surfaced as KPI cards on overview and provider pages.
export const SUMMARY_METRIC_IDS = [
  "finance_total_revenues_from_continuing_operations_including_deferred_superannuation",
  "student_total_enrolments",
  "herdc_research_income_total",
  "qilt_overall_educational_experience_positive_rating",
];

// Prefix used to tag synthetic benchmark rows so charts can style them.
export const BENCHMARK_KEY_PREFIX = "benchmark:";

// Keypath-aligned chart palette (kept in sync with tailwind.config.ts / globals.css).
export const CHART_GRID_COLOR = "#ecedf0";
export const BENCHMARK_COLOR = "#5a6779";
export const PRIMARY_CHART_COLOR = "#0070c0";
export const SECONDARY_CHART_COLOR = "#d9a514";
export const CHART_COLORS = ["#0070c0", "#fdcf41", "#e35a4f", "#02c6fa", "#0d3e7f"];
