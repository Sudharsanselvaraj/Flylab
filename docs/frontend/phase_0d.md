# Phase 0D — Interactive Replay Frontend

Status: **Implemented** (Phase 0D).

## What Phase 0D is

Phase 0D replaces the CLI-only experience with the first interactive visual
frontend. It is a **replay client**: it loads real recorded experiment runs
(the canonical connectome-grounded run `20260916-223510`) and shows their
real stored traces. **There is no live simulation** in Phase 0D — the motor
gate state, neural traces, and decoder metrics are all drawn from recorded
artifacts, never fabricated.

## Honesty invariants (mirrors `docs/honesty-policy.md`)

- Decoder results are always labeled **model-inferred**, never "validated".
- `dynamics_validated` is `false` and is displayed as such; it is never
  upgraded to a validated claim in the UI.
- The fly + wheelchair 3D view is labeled **PRESENTATION ONLY** — no motor
  gating is claimed; FlyGym integration is deferred to Phase 1.
- Every neural channel carries a `note` (provenance) in the API response.
- When a metric/panel is unavailable (e.g. run without decoder artifacts) the
  panel shows an empty state, it never synthesizes numbers.

## Architecture

```
web/
  app/
    src/
      api/client.ts          — typed fetch + WebSocket helpers
      state/useStore.ts      — zustand store for UI state
      types/experiment.ts    — shared API types
      components/            — panels (Stimulus, MotorGate, Neural, Decoder, Provenance, Timeline, …)
      features/three/NeuralSubgraph.tsx — real connectivity subgraph (3D, placeholders)
      presentation/FlyPlaceholder.tsx   — labeled fly + wheelchair (Presentation layer)
```

Backend: `hawking_fly/api` (FastAPI) serves recorded runs read from disk:

| Route | Purpose |
| --- | --- |
| `GET /api/health` | replay-mode status banner |
| `GET /api/experiments` | list recorded runs + stimuli |
| `GET /api/experiments/{id}` | run metadata + manifest |
| `GET /api/experiments/{id}/neural?stimulus=…` | real traces (receptor/relay/DNp01) |
| `GET /api/experiments/{id}/decoder` | model-inferred decoder summary |
| `GET /api/experiments/{id}/provenance` | honesty flags + layer statuses |
| `POST /api/experiments/run` | start a replay of a recorded run |
| `WS /api/experiments/{id}/stream` | replays recorded frames |

## Run it

```bash
# Terminal 1 — backend (replay server)
PYTHONPATH=services/sim-engine .venv/bin/python -m hawking_fly.api.app
# → http://127.0.0.1:8050/api/health

# Terminal 2 — frontend (dev)
cd web/app && npm run dev
# → http://localhost:5173  (Vite proxies /api to :8050)
```

Verify endpoints: `npm run build`, `npm run lint`, `npx vitest run` (15 tests),
backend suite `pytest services/sim-engine/tests/test_api.py`.

## Acceptance criteria (from spec §28) — status

| Criteria | Status |
| --- | --- |
| `npm run dev` succeeds | ✅ `vite` ready, proxy :5173 → :8050 |
| Backend connection shown in UI | ✅ header mode + empty states |
| Real recorded experiment loads | ✅ 4 runs, canonical `20260916-223510` |
| Stimulus selection | ✅ flash / moving_edge / loom from recording |
| Real neural traces from data | ✅ receptor + relay + DNp01 series |
| Motor-gate state from experiment | ✅ peak receptor activity from stored traces |
| Decoder labeled model-inferred | ✅ caveat text + `mapping_verified` only connects synapse evidence |
| Provenance visible | ✅ panel shows flags + layer statuses |
| `verified=False` never shown as verified | ✅ `dynamics_validated: no` rendered |
| No fabricated data | ✅ empty states, no synthesized traces |
| Existing Python tests green | ✅ 62 backend tests (incl. 11 API) |
| Frontend tests/build pass | ✅ 15 vitest tests, `tsc -b`, `vite build` |
| At least one complete replay | ✅ loom run, full 700-frame replay via WS |
| Clean FlyGym integration boundary | ✅ `presentation/FlyPlaceholder.tsx` explicit Phase-1 deferral |

## 3D subgraph honesty

The `NeuralSubgraph` viewer uses the **real** loom-escape connectivity
(receptor → relay → DNp01 from `data/connectome/loom_escape_full_graph.circuit.parquet`).
Node positions are procedural for layout; there is **no skeleton/geometry** in
the MaleCNS dataset, so bodies are labeled placeholders. This is written in
the UI copy — no false "reconstruction" claims.