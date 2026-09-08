# A2UI insight-composition spike

Throwaway spike at `/spike/a2ui` — **not linked from production nav**.

## What it tests

Natural-language intent → selection from the fixed insight catalogue → A2UI composition rendered with `@a2ui/react` (v0.9 protocol). Includes a visible intent → selection → composition log.

## Run locally

```bash
# Terminal 1 — API (read-only DuckDB)
make dev   # or run FastAPI on :8000 separately

# Terminal 2 — web app
cd apps/web
npm run dev
```

Open http://127.0.0.1:3000/spike/a2ui

## Environment variables

| Variable | Purpose |
| --- | --- |
| `API_BASE_URL` or `NEXT_PUBLIC_API_BASE_URL` | FastAPI base URL (default `http://127.0.0.1:8000`) |
| `OPENAI_API_KEY` | Optional — enables LLM selection via AI SDK |
| `GOOGLE_GENERATIVE_AI_API_KEY` | Optional — fallback LLM provider |

Without an LLM key, a deterministic **heuristic selector** runs so the loop is demoable offline.

## Isolation guarantees

- Code only under `apps/web/app/spike/a2ui/` and `apps/web/lib/spike/`
- Read-only HTTP to existing FastAPI endpoints (`/metric-catalog`, `/trends`, `/rankings`, `/benchmarks`)
- Agent emits insight IDs + layout only; numbers come from API fetches in `compose.ts`
- No Python or production dashboard changes

## Fallback behaviour

If `/metric-catalog` or data endpoints are unreachable, the spike uses a small mock catalogue / mock series and flags `mock_fallback` in the inspector log.
