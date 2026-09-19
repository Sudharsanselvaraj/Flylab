# FlyLab web client

FlyLab is the only app view. The 3D desk contains a seated fly, a physical
keyboard and a monitor showing actual Chromium screenshots. A live MaleCNS
instrument displays neural activity on the same simulation clock.

Start the Python API on port 8050, then run:

```sh
npm install
npm run demo
```

The production demo opens on port 5173 and proxies API and WebSocket traffic.
Use `npm run dev` for editing; production avoids development profiling overhead
on full-network neural buffers. Stop either server before starting the other.

Start begins from an empty editor. Choose full-CNS float32, full-CNS float64 or
the 677-neuron subgraph. Wrong-key trial injects one physical key substitution;
subsequent repair comes from the learned controller. Pause freezes the shared
clock. Brain opens anatomy and recorded neuron traces. Evidence & source shows
training losses, measured trials, saved replays and source-to-contact traces.

The controller supports a narrow single-heading curriculum. Its rate dynamics
and kinematic body are engineered models, not validated insect physiology.
See [the physical coding protocol](../../docs/physical-coding.md).

```sh
npm run build
npm run lint
npx vitest run
```
