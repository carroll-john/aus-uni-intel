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

## Deployed Prototype

- Web app: <https://web-kohl-nine-76.vercel.app>
- API: <https://you-are-building-a-public-data.vercel.app>

Deployment uses two native Vercel Git projects:

- `aus-uni-intel-api`: root directory `.`, framework `Other`, uses
  `api/index.py` and the repo-root `vercel.json`.
- `aus-uni-intel-web`: root directory `apps/web`, framework `Next.js`, uses
  `apps/web/vercel.json`.

The web project should have `API_BASE_URL` set to the production API URL. The
API deployment reads `data/warehouse/university_intel.duckdb.gz` and inflates it
into `/tmp` in serverless environments. When ingestion changes deployed data,
refresh and commit the archive before pushing:

```bash
make ingest-all
make archive-db
git add data/warehouse/university_intel.duckdb.gz
git commit -m "Refresh warehouse archive"
git push
```

### Hosting the archive off-git (optional)

The committed `~32MB` archive grows git history on every refresh. To avoid this,
upload the archive to object storage and set `UNI_INTEL_DB_URL` on the API
deployment to its URL. On cold start the API downloads and inflates the remote
archive (resolution order: local file, warm `/tmp` file, committed archive, then
`UNI_INTEL_DB_URL`), so you can then stop committing the archive. Removing the
existing archive from git history requires a deliberate history rewrite and is
not done automatically.

For code/data release checks, run:

```bash
make deploy-check
```

There is intentionally no GitHub Actions deployment workflow. Vercel's native
Git integration owns production deploys for both projects.

## Implemented Data Sources

- Department of Education finance tables, 2018-2024: <https://www.education.gov.au/collections/financial-reports-higher-education-providers>
- Department student section workbooks, 2018-2024: <https://www.education.gov.au/higher-education-statistics/student-data>
- Department award course completions and postgraduate research/coursework completion buckets, 2018-2024 from annual Section 14 workbooks: <https://www.education.gov.au/higher-education-statistics/student-data>
- HERDC research income time series: <https://www.education.gov.au/research-block-grants/resources/research-income-time-series>
- QILT Student Experience Survey report tables, 2021-2024: <https://qilt.edu.au/surveys/student-experience-survey-%28ses%29>

QILT is parsed from provider-level national report tables. The 2021 source is
read from the XLSX inside the published ZIP; 2022-2024 are read from ODS files
inside the published ZIPs.

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
- `GET /benchmarks`
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
curl "http://127.0.0.1:8000/rankings?metric_id=finance_international_students&year=2024&mission_group=Go8"
curl "http://127.0.0.1:8000/benchmarks?metric_id=finance_international_students&year=2024&group_by=mission_group"
curl "http://127.0.0.1:8000/trends?metric_id=student_postgraduate_total_enrolments&provider_id=university_of_sydney&scope=Student"
```

`/metric-catalog` returns a curated, grouped metric list for product selectors. Use
`/metric-catalog?include_missing=true` to include backlog metrics that are not
available yet. `/metrics` remains the full raw metric catalogue for advanced use.

`/rankings` accepts optional `mission_group` and `state` filters to rank within a
peer set. `/benchmarks` returns peer-group averages for a metric (one row per
group per year, using each provider's canonical scope), grouped by `mission_group`
(default) or `state`; it powers the rankings reference line and the compare
benchmark series.

### Provider classification

Each university carries a `mission_group` (Go8, ATN, RUN, 2050 Alliance, or
Unaligned) and a `table_classification` (Table A / Table B under the Higher
Education Support Act 2003). Mission-group membership is recorded as the current
(June 2026) membership and back-cast across historical years; pre-membership
years for a group therefore include institutions that joined later (e.g. Deakin
and Newcastle in ATN, and the 2050 Alliance which launched in May 2026 as the
successor to the Innovative Research Universities).

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
- Student data currently covers provider-level enrolments, postgraduate research/coursework enrolments, EFTSL/load, and award course completions for 2018-2024.
- No consistent national provider-level public source is currently selected for postgraduate applications/offers. Commencing postgraduate enrolments are included as the available demand proxy.
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
