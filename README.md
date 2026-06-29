# Australian University Public Data Intelligence Prototype

Local-first data product for ingesting Australian higher education public datasets into a canonical metric/fact model backed by DuckDB, with a FastAPI API and Next.js dashboard.

## One-command Runs

```bash
make demo
```

Creates/updates the local Python environment, downloads configured public datasets, loads DuckDB, writes data-quality reports, and runs Python tests.

```bash
make dev
```

Runs the full local app:

- FastAPI: <http://127.0.0.1:8000>
- API docs: <http://127.0.0.1:8000/docs>
- Next.js web app: <http://127.0.0.1:3000>

```bash
make verify
```

Runs ingestion, Python tests, frontend build, starts the API, and checks required frontend/API smoke endpoints.

## Implemented Data Sources

- Department of Education finance tables, 2018-2024: <https://www.education.gov.au/collections/financial-reports-higher-education-providers>
- Department student section workbooks, 2018-2024: <https://www.education.gov.au/higher-education-statistics/student-data>
- Department award course completions, 2018-2024 from the 2024 Section 14 workbook: <https://www.education.gov.au/higher-education-statistics/student-data>
- HERDC research income time series: <https://www.education.gov.au/research-block-grants/resources/research-income-time-series>
- QILT Student Experience Survey report tables, 2024: <https://qilt.edu.au/surveys/student-experience-survey-%28ses%29>

QILT is parsed from the ODS file inside the published ZIP because the XLSX contains image-like report sheets.

## Project Structure

```text
apps/web/           Next.js + Tailwind + Recharts web app
data/raw/           Downloaded source files, ignored by git
data/quality/       Ingestion quality reports, ignored by git
data/seed/          Seeded providers and aliases
data/warehouse/     Local DuckDB files, ignored by git
sql/schema.sql      Canonical schema and staging tables
src/uni_intel/api/  FastAPI endpoints
src/uni_intel/ingestion/
                    Dataset parsers, ingestion runners, calculations
tests/              Parser, matching, and ingestion-contract tests
```

## API Surface

- `GET /overview`
- `GET /providers`
- `GET /metrics`
- `GET /metric-catalog`
- `GET /provider/{provider_id}/profile`
- `GET /rankings`
- `GET /compare`
- `GET /trends`
- `GET /years`
- `GET /scopes`
- `GET /sources`
- `GET /quality`

Examples:

```bash
curl "http://127.0.0.1:8000/overview"
curl "http://127.0.0.1:8000/metric-catalog"
curl "http://127.0.0.1:8000/rankings?metric_id=herdc_research_income_total&year=2024&scope=HERDC&limit=10"
curl "http://127.0.0.1:8000/trends?metric_id=student_total_enrolments&provider_id=university_of_sydney&scope=Student"
```

`/metric-catalog` returns a curated, grouped metric list for product selectors. Use
`/metric-catalog?include_missing=true` to include backlog metrics that are not
available yet. `/metrics` remains the full raw metric catalogue for advanced use.

## Canonical Model

The core schema is in `sql/schema.sql`:

- `providers`
- `provider_aliases`
- `metrics`
- `metric_dependencies`
- `facts`
- `source_datasets`
- `source_files`
- `data_quality_checks`
- dataset staging tables for finance, student, HERDC, and QILT

Every metric has source metadata and a definition. Calculated metrics store calculation methods and dependency rows. Every fact keeps source file, source row, source provider name, source line item, reporting year, scope, and `dimensions_json`.

## Current Product Views

The web app includes:

- sector overview
- provider list and university profile
- rankings
- compare
- sources/method/data-quality page

Charts are populated from API responses, not hard-coded values.
Rankings and compare default to the curated metric catalogue. The raw source
catalogue remains available through the “Advanced raw metrics” mode.

## Known Limitations

- Provider scope is intentionally public universities plus a sector aggregate; private/special providers are filtered out of provider-level student section loads.
- Finance history currently uses Department XLSX workbooks for 2018-2021 and CSV extracts for 2022-2024.
- Student data currently covers provider-level enrolments, EFTSL/load, and award course completions for 2018-2024.
- QILT currently ingests provider-level SES undergraduate and postgraduate coursework institution tables with 90% confidence intervals.
- Some npm audit output currently flags Next.js bundled PostCSS; npm’s available fix is a breaking downgrade, so the app stays on the current supported Next.js release.

## Adding A Dataset

1. Add source URLs to `src/uni_intel/config.py`.
2. Add metric definitions in `src/uni_intel/ingestion/metrics.py`.
3. Create a parser under `src/uni_intel/ingestion/parsers/`.
4. Create an ingestion runner that downloads raw files, registers source metadata, stages rows, resolves providers, loads facts, and writes quality checks.
5. Register the runner in `src/uni_intel/ingestion/ingest_all.py`.
6. Add parser and ingestion-contract tests.
7. Expose any new metric family through existing API/frontend selectors.
