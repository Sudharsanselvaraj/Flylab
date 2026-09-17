# Phase 0E — Symbol Mapping + Wheelchair Avatar

Status: **Implemented** (Phase 0E).

## What Phase 0E is

Phase 0E turns the Phase 0D replay client into a small **discovery puzzle**:
the wheelchair avatar's motor gate is blocked, and the user must learn whether
upstream recorded activity can reveal a blocked escape command. The gameplay
uses **symbols mapped onto the real decoder output classes** (escape / no-escape
from the canonical run `20260916-223510`) — the symbols are a **designed layer**,
never claimed as discovered biology.

## Honesty invariants (mirrors `docs/honesty-policy.md`, spec §4.6/§4.7/§8)

- The symbol map is labeled **DESIGNED UX**; `design layer on top of real decoder
  output` is in the API note. It is never presented as discovered meaning.
- Every decoded symbol is framed **model-inferred**; confidence is the held-out
  channel R² from the leave-one-stimulus-out generalization fold of the real
  decoder study (loom 0.54, flash 0.90).
- Wheelchair state is **tied to the recorded motor-gate data** (`motor_gate`/
  `npz` files, see [`docs/phase_0b.md`](../phase_0b.md)): when the recorded run
  withheld motor output, the avatar shows `gate blocked`; presentation stays
  nil — no live motor record, no fabricated gating. `dynamics_validated`
  remains `false`.
- The **DISCOVERY** console builds an **in-session correlation table** from the
  user's own TEST actions via `POST /test-action`. There are no pre-scripted
  reveals; a blank session is a blank table.
- Missing/partial data renders empty states — numbers are never invented.

## What was added

Backend (`hawking_fly/api/`):

| Route | Purpose |
| --- | --- |
| `GET /api/experiments/{id}/symbols` | designed-UX symbol set grounded in decoder weight (⚡ escape / · no-escape), `designed_ux`, `label_rule`, `reveal_policy` |
| `GET /api/experiments/{id}/wheelchair` | real recorded gate state → `gate_state` `blocked`/`active`, `motor_output_withheld`, `dynamics_validated` |
| `GET /api/experiments/{id}/communication?stimulus=…` | model-inferred decode: symbol + label + confidence (= held-out channel R²) + framing |
| `POST /api/experiments/{id}/test-action` | logs the user's guessed symbol for a stimulus (in-memory, per session) |
| `GET /api/experiments/{id}/test-actions` | in-session correlation table |

Grounding for `symbols`/`communication`: `experiments/loom_escape/20260916-223510/grounded_premotor_decoding.json`
(regression, classification with leave-one-out AUC 1.0, `generalization_leave_stimulus_out`
fold → channel R² confidence, caveats, `dynamics_validated: false`).

Frontend (`web/app/src/`):

- `components/SymbolMapPanel.tsx` — the designed-UX symbol legend (badge + evidence lines)
- `components/CommunicationPanel.tsx` — symbol, label, confidence bar, "model-inferred" framing
- `components/DiscoveryConsole.tsx` — TEST buttons + live in-session correlation table
- `presentation/FlyPlaceholder.tsx` — avatar reads store wheelchair gate; fly color/wing-beat
  reflect `gate active` vs `gate blocked` (presentation layer, marked not-validated)
- store: loads symbols/wheelchair on run selection, loads communication on stimulus change,
  `logTestAction` pipelines to `POST /test-action`

## Run it

(same as Phase 0D)

```bash
# Terminal 1 — backend (replay server)
PYTHONPATH=services/sim-engine .venv/bin/python -m hawking_fly.api.app

# Terminal 2 — frontend (dev)
cd web/app && npm run dev
```

## Tests

- Backend: `pytest services/sim-engine/tests/test_api.py` → 18 API tests (7 new for
  Phase 0E: designed-UX labeling, `dynamics_validated: false`, model-inferred framing,
  unknown-stimulus 404, session correlation build + fetch).
- Frontend: `npx vitest run` → 27 tests (Phase 0E: SymbolMapPanel DESIGNED-UX badge,
  CommunicationPanel confidence + framing, DiscoveryConsole action logging, dashboard
  integration asserting `symbolSet`, `wheelchair`, `communication` populate on run select).
- Full: `npm run build` (tsc + vite) green.

## Acceptance criteria (Phase 0E, mirroring spec §4.6/§4.7)

| Criteria | Status |
| --- | --- |
| Symbols never drift from decoder classes | ✅ ⚡/· map 1:1 to escape/no-escape weight classes |
| Symbol mapping labeled designed UX | ✅ `designed_ux: true` + API note + badge |
| Decode framed as model-inferred | ✅ `framing: model-inferred` + panel copy |
| Confidence quantitative & grounded | ✅ held-out channel R² from real generalization fold |
| Wheelchair state tied to recorded gate | ✅ reads recorded `motor_gate`/withheld flag |
| `dynamics_validated` stays false | ✅ returned and displayed `no` |
| In-session discovery (no scripted reveals) | ✅ POST test-action → correlation table from real actions |
| Presentation vs real boundary | ✅ avatar is presentation-only with gate badge |