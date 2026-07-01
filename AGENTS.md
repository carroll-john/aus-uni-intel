# AGENTS.md

## Cursor Cloud specific instructions

This repo is a local-first data product: a **FastAPI + DuckDB API** (`src/uni_intel`, entry `uni_intel.api.main:app`) and a **Next.js dashboard** (`apps/web`). Standard commands live in `README.md`, the `Makefile`, and `apps/web/package.json` — reference those rather than re-deriving them.

### Running the two services (do NOT use `make dev` / `make verify`)

`make dev`, `make verify`, and `make demo` all run `make ingest-all`, which downloads public datasets from external government / QILT websites. That network egress is slow and unreliable in the cloud VM and is **not needed** for development. Start the services directly instead:

- API (port 8000): `.venv/bin/python -m uvicorn uni_intel.api.main:app --host 127.0.0.1 --port 8000`
- Web (port 3000), from `apps/web`: `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000 API_BASE_URL=http://127.0.0.1:8000 npm run dev`

The web app fetches the API **server-side**, so `API_BASE_URL` (or `NEXT_PUBLIC_API_BASE_URL`, default `http://127.0.0.1:8000`) must point at the running API.

### Data: no ingestion required

The committed warehouse archive `data/warehouse/university_intel.duckdb.gz` is the source of data for local runs. On the first request, the API auto-inflates it to `/tmp/university_intel.duckdb` (see `_resolve_db_path` in `src/uni_intel/api/main.py`) whenever `data/warehouse/university_intel.duckdb` is absent — which it normally is (the raw `.duckdb` is git-ignored). So the API serves real data out of the box without running any ingestion. Override the DB location with `UNI_INTEL_DB_PATH` if needed.

### Lint / test / build

- Python lint: `make lint` (ruff). Python tests: `make test` (pytest, 42 tests). These use `.venv`.
- Web: `npm run lint`, `npm run typecheck`, `npm run build` in `apps/web`. `apps/web/components/AppShell.tsx` emits one pre-existing eslint `no-img-element` **warning** (not an error).
- `apps/web/scripts/smoke.mjs` (`npm run smoke`) checks core API endpoints and requires the API to be running.
