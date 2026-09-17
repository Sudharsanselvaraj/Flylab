# Phase 0D — Interactive Replay Frontend

Status: **Implemented** (Phase 0D).

## What Phase 0D is

Phase 0D replaces the CLI-only experience with the first interactive visual
frontend. It is a **replay client**: it loads real recorded experiment runs
(the canonical connectome-grounded run `20260916-223510`) and shows their
real stored traces. **There is no live simulation** in Phase 0D — the motor
gate state, neural traces, and decoder metrics are all drawn from recorded
artifacts, never fabricated.

## Main experiment view

The dashboard is a two-zone theatrical composition, not a card wall:

- **Observed upstream** (left): the neural scene — `NeuralActivityPanel` with a
  relay representation toggle (**type-agg** per-type means / **per-neuron**
  per recorded driven relay neuron), the recorded timeline, the experiment
  explainer, and the real premotor subgraph (3D connectivity, positional
  placeholders only).
- **Gate + downstream** (right): the **motor gate boundary** — a fixed diagram
  OBSERVED → **GATE BLOCKED** → DNp01 (withheld ground truth) → **No motor
  record** — with the fly presentation, decoder results, and full provenance.

Channel identity is explicit (per-type/per-cell labels and legend). The
neural view keeps the pairing contract visually honest: the **VISIBLE /
upstream** zone (receptor + relay) is separate from the **GROUND TRUTH / DNp01**
zone, which is labeled *withheld behind the gate — shown here for reference*.
DNp01 is never presented as a signal the decoder can see.

The 0E exploration panels (symbols, communication, discovery) live in one
collapsed **designed-UX layer** section so they don't crowd the main view.

## Honesty invariants (mirrors `docs/honesty-policy.md`)

- Decoder results are always labeled **model-inferred**, never "validated".
- `dynamics_validated` is `false` and is displayed as such; it is never
  upgraded to a validated claim in the UI.
- The fly + wheelchair 3D view is labeled **PRESENTATION ONLY** — no motor
  gating is claimed; FlyGym integration is deferred to Phase 1.
- Every neural channel carries a `note` (provenance) in the API response.
- When a metric/panel is unavailable (e.g. run without decoder artifacts) the
  panel shows an empty state, it never synthesizes numbers.
- `flyvis_to_malecns_mapping_verified` is shown from the artifact, never
  assumed; the dataset vintage (grounded premotor / legacy proxy) is derived
  from `mapping_verified`, not hard-coded.

## Architecture

```
web/
  app/
    src/
      api/client.ts          — typed fetch + WebSocket helpers
      state/useStore.ts      — zustand store for UI state
      types/experiment.ts    — shared API types
      components/            — panels (Stimulus, MotorGateBoundary, Neural, Decoder, Provenance, Timeline, ExperimentContext, …)
      features/three/NeuralSubgraph.tsx — real connectivity subgraph (3D, placeholders)
      presentation/FlyPlaceholder.tsx   — labeled fly + wheelchair (Presentation layer)
```

Backend: `hawking_fly/api` (FastAPI) serves recorded runs read from disk:

| Route | Purpose |
| --- | --- |
| `GET /api/health` | replay-mode status banner |
| `GET /api/experiments` | list recorded runs + stimuli |
| `GET /api/experiments/{id}` | run metadata + manifest |
| `GET /api/experiments/{id}/neural?stimulus=…&mode=type_agg\|per_neuron` | real traces; `mode` switches relay type-means ↔ per driven relay neuron; response includes `gate` (recorded blocked/active boundary) and per-channel `role` (`visible` / `ground_truth`) + `withheld` |
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

Verify endpoints: `npm run build`, `npm run lint`, `npx vitest run` (38 tests),
backend suite `pytest services/sim-engine/tests/test_api.py`.

## Acceptance criteria (from spec §28) — status

| Criteria | Status |
| --- | --- |
| `npm run dev` succeeds | ✅ `vite` ready, proxy :5173 → :8050 |
| Backend connection shown in UI | ✅ header mode + empty states |
| Real recorded experiment loads | ✅ 4 runs, canonical `20260916-223510` |
| Stimulus selection | ✅ flash / moving_edge / loom from recording |
| Real neural traces from data | ✅ receptor + relay + DNp01 series |
| Relay representation toggle | ✅ type-agg / per-neuron (recorded per-cell traces) |
| VISIBLE vs GROUND TRUTH honest split | ✅ separate zones; DNp01 labeled withheld, shown for reference |
| Motor-gate state from experiment | ✅ blocked-boundary diagram from recorded gate/manifest; motor = no record |
| Decoder labeled model-inferred | ✅ caveat text + `mapping_verified` only connects synapse evidence |
| Provenance visible | ✅ panel shows flags + layer statuses |
| Provenance complete | ✅ `flyvis_to_malecns_mapping_verified` + dataset vintage shown |
| Experiment explained | ✅ observed / blocked / ground truth / inferred panel |
| `verified=False` never shown as verified | ✅ `dynamics_validated: no` rendered |
| No fabricated data | ✅ empty states, no synthesized traces |
| Existing Python tests green | ✅ 80 backend tests (incl. 20 API) |
| Frontend tests/build pass | ✅ 38 vitest tests, `tsc -b`, `vite build` |
| At least one complete replay | ✅ loom run, full 700-frame replay via WS |
| Clean FlyGym integration boundary | ✅ `presentation/FlyPlaceholder.tsx` explicit Phase-1 deferral |

## 3D subgraph honesty

The `NeuralSubgraph` viewer uses the **real** loom-escape connectivity
(receptor → relay → DNp01 from `data/connectome/loom_escape_full_graph.circuit.parquet`).
Node positions are procedural for layout; there is **no skeleton/geometry** in
the MaleCNS dataset, so bodies are labeled placeholders. This is written in
the UI copy — no false "reconstruction" claims.