# The Hawking Fly

**Working title:** The Hawking Fly (alt: *Can a Brain Speak Without a Body?*)
**Domain:** Connectome-constrained computational neuroscience + interactive simulation

> The precise version of what this project actually does:
> **"Can upstream neural activity reveal a blocked motor command?"**

---

## What this is

A hybrid connectome-constrained simulation with a validated pretrained visual
component (`flyvis`) and custom, **unvalidated** downstream dynamics — built on
real connectivity data from the MaleCNS v1.0 whole-male-CNS connectome
(brain + optic lobes + ventral nerve cord, one animal), with FlyGym /
NeuroMechFly reserved for Phase 1 as the embodied 3D body/world layer.

This is **not** a simulation of "the fly brain" and **not** an exact digital
reconstruction of one individual fly. MaleCNS wiring + FlyVis visual model +
custom rate dynamics + FlyGym body are different modeling layers (different
specimens/data sources). The combined system is a **hybrid simulation**, and
all UI copy must reflect that (§8 honesty policy).

**Layer attribution** (which components are real/validated vs custom):

| Pipeline stage | Component | Status |
|---|---|---|
| Optic lobe (65 columnar types, ~45.7k cells) | `flyvis` pretrained (Lappalainen et al. 2024) | ✅ real + validated |
| Synthetic stimuli (flash / moving edge / loom) | `hawking_fly/sensory` | ⚠️ synthetic, labeled |
| LC4/LPLC2 correspondence | MaleCNS v1.0 synapse-grounded classes + weights | ✅ connectome-verified |
| Receptor→relay→DNp01 propagation | custom rate model (`hawking_fly/propagation`) | ⚠️ custom, `dynamics_validated=false` |
| Motor gate + decoder (replay) | recorded artifacts (Phase 0B/0C) | ⚠️ model-inferred |

Read the full spec: [`docs/spec.md`](docs/spec.md).

---

## Core pipeline

```
FLYGYM 3D WORLD (Phase 1)
   ↓ sensory observations
FLYVIS VISION (pretrained, validated — Phase 0A now)
   ↓
MALECNS GRAPH (real connectivity, awaited token)
   ↓ custom neural dynamics (simplified rate model)
PREMOTOR STATE
   ↓
MOTOR GATE (Phase 0B)
   ├─ decoder-visible activity
   └─ withheld ground truth → DECODER (Phase 0C)
```

## Status

- [x] Repo scaffold, honesty policy, env/token plumbing
- [x] **Phase 0A** — flyvis validation on synthetic stimuli ✅ (see [`docs/phase_0a.md`](docs/phase_0a.md))
- [x] 0A-conn — MaleCNS grounded premotor subgraph (see `docs/connectome/verified_premotor_representation.md`)
- [ ] Phase 0B — motor gate + paired visible/ground-truth traces
- [x] Phase 0C — intent decoder + connectome-grounded mapping ✅
- [x] Phase 0D — minimal single-screen UI (replay, see [`docs/frontend/phase_0d.md`](docs/frontend/phase_0d.md))
- [x] Phase 0E — symbol mapping + wheelchair avatar (see [`docs/frontend/phase_0e.md`](docs/frontend/phase_0e.md)) ✅
- [ ] Phase 1 — FlyGym embodiment, cut-point curve, 3D neural camera
- [ ] Phase 2 / stretch — VIP/manual VNC circuit, multi-fly mode, cinematic brain dive

## Getting started

Prereqs: Python 3.11, git.

```bash
git clone <this repo>
cd <repo>

# 1. Python environment
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip

# 2. Install the sim-engine package (installs flyvis + pinned torch first)
pip install -e "services/sim-engine[dev]"

# 3. Copy env template and (optionally) add your neuPrint token later
cp .env.example .env

# 4. Validate
pytest
jupyter nbconvert --execute --to notebook --inplace notebooks/01_flyvis_validation.ipynb
```

> **neuPrint token:** MaleCNS v1.0 queries need a free personal token from
> <https://neuprint.janelia.org>. The connectome client reads
> `NEUPRINT_TOKEN` from `.env`; until it's set, Phase 0A runs flyvis-only
> validation and skips the circuit fetch with a clear `NoTokenError`.

## Phase 0A run

Validate that the pipeline produces *sane* activity before any decoder work:

```bash
source .venv/bin/activate
python -m hawking_fly.experiments.run --config experiments/loom_escape/config.json
```

Success bar (Phase 0A): `flyvis` produces finite, distinguishable activity
traces for loom / flash / moving-edge stimuli, with the loom stimulus
activating its known responsive read-out cells. Nothing is claimed about
decodability at this stage.

Report + reproducibility: [`docs/phase_0a.md`](docs/phase_0a.md). Re-run the
Phase 0A validation against an existing run:

```bash
python -m hawking_fly.sensory.validation \
  --run-dir experiments/loom_escape/20260916-223510 \
  --out experiments/loom_escape/phase_0a_validation
```

**Phase 0A completed (Sept 16 2026).** Results in `experiments/loom_escape/`:

| Stimulus       | mean\|r\| | finite | signature norm |
|----------------|----------|--------|----------------|
| flash          | 0.676    | true   | 9.88           |
| moving_edge    | 0.692    | true   | 8.72           |
| loom           | 0.743    | true   | 11.20          |

Pairwise trace MSE confirms loom is clearly distinguishable from flash and
moving edge (~250× higher MSE than flash-vs-moving-edge).

## Real vs. designed (keep visible in every UI surface)

| Layer                                                 | Status                              |
| ----------------------------------------------------- | ----------------------------------- |
| Optic lobe connectivity & visual dynamics             | **Real, pretrained** (`flyvis`)     |
| Whole-brain / VNC connectivity structure              | Real data, custom simplified dynamics |
| Motor-intent decoder                                  | Real prediction task, novel method  |
| "Teach the fly to communicate" discovery mechanic     | Designed UX, not neuroscience       |
| Multi-fly behavioral fingerprinting                   | Exploratory, stretch                |
| Wheelchair avatar / neural camera / cinematic dive    | Presentation layer (Phase 0E/1+)    |

## Tech stack

`flyvis` (PyTorch) · `neuprint-python` · `navis` · PyTorch · `networkx` /
`scipy.sparse` · `scikit-learn` · FastAPI + WebSocket · React + TS +
Tailwind + three.js (`web/app`, Phase 0D/0E) · FlyGym / NeuroMechFly + MuJoCo
(Phase 1) · SQLite · Docker.

## Run the Phase 0D/0E frontend

```bash
# Terminal 1 — replay API (serves recorded runs, no live sim)
PYTHONPATH=services/sim-engine .venv/bin/python -m hawking_fly.api.app
# → http://127.0.0.1:8050/api/health

# Terminal 2 — React + TS + Tailwind + three.js UI
cd web/app && npm install && npm run dev
# → http://localhost:5173  (Vite proxies /api to :8050)
```

Docs: [`docs/frontend/phase_0d.md`](docs/frontend/phase_0d.md) · [`docs/frontend/phase_0e.md`](docs/frontend/phase_0e.md).

## Repo layout

```
data/connectome/          # cached connectome pulls (gitignored)
data/stimuli/             # synthetic stimulus definitions
services/sim-engine/      # hawking_fly Python package
  hawking_fly/connectome/ # neuPrint/MaleCNS client + circuit queries + cache
  hawking_fly/sensory/    # stimulus generators + flyvis wrapper
  hawking_fly/propagation/# custom rate model over the connectome graph
  hawking_fly/motor_gate/ # (Phase 0B)
  hawking_fly/decoder/    # (Phase 0C)
  hawking_fly/embodiment/ # (Phase 1 — FlyGym)
  hawking_fly/api/        # FastAPI app + websocket (Phase 0D)
notebooks/                # exploration / validation
experiments/              # every decoder/baseline run, reproducible
docs/spec.md              # the project specification
docs/honesty-policy.md
```

## Honesty policy

Every screen showing a decoded/inferred value must use "model-inferred state" /
"decoded signal" — never "the fly wants X". Full policy in
[`docs/honesty-policy.md`](docs/honesty-policy.md).