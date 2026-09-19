# FlyLab

A connectome-constrained coding agent at a 3D desk, with physical keyboard
interaction and a synchronized MaleCNS instrument.

The learned controller reads actual Chromium screenshots, selects individual
characters and moves a kinematic foreleg to a physical key. Contact gates native
browser key events. The browser's resulting screenshots return as visual input.

The full network contains **176,422 cached MaleCNS neuron records** and
**25,862,574 directed connections**. Its instrument distinguishes anatomy,
simulated neurons and current activity. Full float32, full float64 and a
677-neuron subgraph are explicit execution modes. Pause, neuron inspection,
source-to-contact traces and complete-session replay share one simulation clock.

The current curriculum is single-line HTML headings. Wrong-key correction and
held-out “Hello Fly” trials passed. All-positive rate dynamics, the sensory
adapter and the kinematic body are engineered and unvalidated; this is not a
biological fly brain or a general programming agent. Full simulation is slower
than real time on the tested Mac.

## Run locally

With the project's Python environment and cached data prepared:

```sh
.venv/bin/python -m playwright install chromium
PYTHONPATH=services/sim-engine .venv/bin/python -m hawking_fly.api.app
```

In another terminal:

```sh
cd web/app
npm install
npm run demo
```

Open [FlyLab](http://localhost:5173/). Start begins with an empty editor.
Use **Brain** for anatomy and activity inspection, and **Evidence & source** for
training, measured results, recorded source and saved replays.

The production demo avoids React development profiling overhead on large neural
buffers. Use `npm run dev` for editing instead; both use port 5173.

## Protocol and evidence

The home/workroom, dark instruments, continuous typing and measured-baseline CNS
view are described in [the 2.0 implementation state](docs/coding-v2.md). The
multi-element webpage controller is not implemented; the active checkpoint still
supports the heading benchmark.

- [Physical coding protocol, data preparation and training](docs/physical-coding.md)
- [Full-network validation evidence](experiments/full_cns/evidence_index.json)
- [Web client instructions](web/app/README.md)

```sh
PYTHONPATH=services/sim-engine .venv/bin/python -m pytest services/sim-engine/tests -q
cd web/app
npm run build
npm run lint
npx vitest run
```
