> Historical token prototype, superseded by [physical coding](physical-coding.md).
> It is retained as an archived reproducibility artifact and is not mounted in
> the FlyLab application. Its synthetic DOM events and source mutations do
> **not** meet the real typing acceptance criteria.

# Coding Fly — first bounded learning experiment

The coding task is an engineered benchmark for a connectome-constrained agent.
It is **not evidence that a real fly understands programming**.

The default and only FlyLab application opens the physical coding desk. This
historical prototype remains documented for reproducibility only.

## Implemented scope and measured outcome

This is a small HTML/CSS **token-selection and visual correction benchmark**,
not an autonomous general programmer. A supplied CSS scaffold fixes geometry,
fonts and labels. The policy inserts a heading, a button, and a three-card
section, then appends CSS overrides to match a target's three colours. Source
begins with the scaffold and an empty body. There is no runtime LLM, source
reader, target-ID lookup or scripted action trajectory.

A 48-hidden-unit imitation policy learned from executed browser captures.
The first frozen-checkpoint browser test passed **4/5 held-out colour
compositions**, with three corrective colour edits in each successful episode.
Target 13 failed by repeatedly recolouring its already-correct heading. The
failure is retained, not patched with a task-specific rule.

| Test target (UI number) | Success | Decisions | Corrections | Pixel MAE |
|---|---:|---:|---:|---:|
| 2 | yes | 7 | 3 | 0 |
| 6 | yes | 7 | 3 | 0 |
| 13 | no | 15 | 1 | 0.06457035 |
| 17 | yes | 7 | 3 | 0 |
| 21 | yes | 7 | 3 | 0 |

A successful episode contains 840 primitive events and 19.04 seconds of virtual
clock time. Matched replay reproduced the decisions, neural trajectories,
primitive events and final source exactly. Silencing all 101 visual-input
neurons failed on the same target (15 decisions; pixel MAE 0.27064349).
That is a **computational perturbation**, not a biological lesion prediction.

Measured artifacts:

- `experiments/coding_fly/training_manifest/manifest.json`
- `experiments/coding_fly/metrics/history.json`
- `experiments/coding_fly/metrics/browser_evaluation.json`
- `experiments/coding_fly/trained_policy/policy.npz`

The training manifest's `browser_rollout_verified: false` records that training
itself did not verify the browser loop. The separately recorded browser
assessment above is the evidence for that loop, not training classification.

## Architecture and computer interface

`web/app/src/features/coding/` owns the desk, monitor, virtual computer,
sandboxed page renderer, episode controls, video recording and anatomy view.
`hawking_fly/coding/` owns the single scientific model and training runner.
`api/coding.py` exposes static metadata and a session WebSocket.

The screen is a live CanvasTexture on a physical monitor. Its code pane is a
rendering of the actual textarea source. Its preview is a rasterization of the
executed page. A fly, seat, desk, monitor stand, keyboard, mouse and lamp occupy
the same room. Camera controls offer room, desk close-up and fly view.

The readout selects one of 13 actions: three structural HTML tokens, nine
colour rules, or finish. Tokens are openly **engineered syntax abstractions**.
They expand into pointer events, editor focus, End, per-character keydown/input/
keyup, then a click on Run. Characters mutate the textarea through its keyboard
handler and `setRangeText`; there is no whole-program write operation during
inference. Backspace, Delete, arrows, Home, End, Enter and Tab are also available
at the primitive layer, although this first policy's corrective actions append
CSS overrides rather than selecting/deleting text. Human source inspection is
available in the results drawer. The same event layer is used for evaluation.

The larger requested curriculum—free cursor control, learned syntax, new page
layouts, JavaScript, error-message reading and general debugging—is **not yet
implemented**. The current policy does not learn arbitrary text generation.

## Sensory pipeline and capture boundary

Each page executes in an iframe with `sandbox="allow-scripts"`, without
`allow-same-origin`. A CSP blocks network access, forms and external assets.
An injected capture bridge serializes the executed DOM, removes scripts from
the snapshot, and sends it to the parent. The browser rasterizes that snapshot
using SVG `foreignObject` into a 240×180 canvas. This is a browser DOM snapshot
renderer, **not an OS/browser screenshot API**. It supports this benchmark's
inline HTML/CSS/text; canvas, video, asynchronous applications, external fonts,
complex pseudo-elements and arbitrary pages are not guaranteed.

The visible target and current preview are downsampled into a combined 32×24
RGB observation. Fixed 4×4 spatial pooling produces 144 features. A seeded,
fixed projection injects these into 101 MeTu2a/MeTu2b cells. This is an
**engineered RGB sensory adapter**, not an established biological mapping.
It intentionally does not reuse FlyVis's motion pathway for static colour
reconstruction. The existing FlyVis pathway remains untouched.

The normal inference schema accepts only `kind`, `tick`, and pixel bytes.
Source, target ID/HTML, DOM, error strings, reward and teacher labels are rejected.
Training and evaluation can access privileged state; their code is separate
from `Policy.infer`. The target itself is visible on the monitor and is therefore
part of the visual observation.

## Neural substrate and dynamics

`prepare_coding_graph.py` selects a separate MaleCNS v1.0 graph by annotated
visual/central-complex type, not the looming experiment's 21 readout channels:

- MeTu2a/MeTu2b, TuBu01–10, ER types, EPG, PEN1/PEN2, PFL1–3;
- **677 neurons, 46,149 directed connections, 534,173 synapses**;
- no DNp01 cells; no reuse of the blocked decoder or withheld ground truth;
- IDs, types, sides, positions and connection weights are real dataset records.

The bounded anatomy is chosen for engineering an accessible visual/central
reservoir. Its suitability for coding is not biologically validated. All
connections are assigned a positive sign and normalized by the recipient's
incoming synapse count. Neurotransmitter signs are not modeled.

For each observation, the model resets a stimulus-locked response window and
performs 16 updates at 20 ms:

```
r_next = 0.35*r + 0.65*tanh(visual_drive + 0.85*W*r + fixed_bias)
```

Silenced cells are clamped to zero at every step. The readout uses the signed
states of the 576 non-input cells; displayed rates rectify those states.
Threshold-integrated markers are emitted from the modeled positive rates and
recorded with neuron IDs and ticks. These are model events, not measured
biological spikes. Connectivity propagates **rates**, not conductance-based
spikes. No fake traveling particles are substituted for model events.

## Clock and replay

A session has one integer clock with 20 ms ticks. Neural observation windows
advance 16 ticks. Each emitted primitive event advances one tick and records
its originating neural decision tick. Rendering waits do not advance the clock.
The WebSocket requires each action to be acknowledged before accepting the
next observation, and rejects out-of-order observations and motor timestamps.

This first implementation is a **hybrid, stimulus-locked controller**: neural
integration occurs in the observation window; the resulting macro action is
then executed while its neural decision is held. It is not a continuously
integrating spiking nervous system throughout every keystroke. The distinction
is material and must remain visible when presenting the experiment.

Normal demonstration paces characters at 25 ms wall time. Evaluation removes
that presentation delay and labels its monitor `UNPACED EVALUATION`. Simulation
time and last-run measured real-time factor are displayed. Wall pacing does
not change the event sequence or model input. Replay reruns the frozen policy
through the actual computer and checks full decision/event equality; it does
not just replay a typing animation. Exported episode JSON includes observations,
checkpoint/graph hashes, all neural windows, events, source and reward.

## Learning, curriculum and procedural task split

`train_coding_policy.py` runs deterministic supervised imitation with PyTorch
Adam (learning rate .005, weight decay .00001, seed 37). It optimizes the
576 → 48 tanh → 13 readout: **28,333 trainable parameters**. The graph, sensory
projection, dynamics and HTML/CSS vocabulary stay fixed. There is no transformer
or LLM. This is not reinforcement learning, online adaptation or plasticity.

The browser executes and captures all 125 current-page states: each of three
slots can be absent, neutral grey, or one of three colours. It generates 27
target colour triples. A deterministic composition split assigns 17 training,
5 validation and 5 test targets. The privileged offline teacher labels the next
missing element or incorrect colour; it is not called during inference.

Training therefore has 2,125 examples, validation 625 and test 625. Current
page states can appear in multiple splits; **target-role colour compositions**
are held out. This is recombination on a fixed template, not held-out layouts,
unseen syntax, words or task families. It must not be advertised as broad
programming generalization.

After 900 epochs, training cross entropy fell from 2.5420 to 0.00168.
Action accuracy was 100% train, 94.4% validation and 96.64% test. The checkpoint
was selected by validation loss, before browser testing. No task-specific
correction was added after observing the failed test target.

Artifacts include capture hashes, graph hash, seed, configuration, optimizer
state (every 100 optimization epochs), metric history, model version and
reproducible run ID. Stop cancels capture/optimization without inventing a
finished checkpoint. `--resume` loads
the local optimizer state and continues optimization. The browser says
`TRAINED CHECKPOINT`; only Capture & train actually optimizes parameters.

## Reward and evaluation

The independent evaluator computes RGB mean absolute pixel error divided by
255 over the 240×180 preview, similarity = 1 − MAE, and action cost = .001 per
policy decision. Reward = similarity − action cost. Success requires MAE < .005.
No reward enters the inference request. There is no fake progress percentage,
HTML-validity score or fabricated error-recovery metric.

Colour correction count increments only when a colour edit decreases actual
pixel error. It measures visual mismatch correction, not compiler-error
repair. The run ends when the learned policy chooses finish or at 15 decisions.
The entire held-out test, exact rerun and matched input-silencing control can
be rerun from Training & results. Failures remain in the table and artifacts.

## CNS visualization and provenance

Whole CNS reuses the real 142,757 located-cell overview. It is not all simulated.
The coding view uses all available measured soma positions and a disclosed
24-body SWC morphology sample; an individual selected neuron uses its full
published skeleton. This is an initial three-level anatomy view, not a complete
automatic active-pathway LOD system. Missing morphology is reported rather than
invented. Gold soma markers follow recorded threshold events; skeleton opacity
shows modeled rate. Selected-neuron lines show actual connections between soma
anchors, not the locations of synapses. Partner/synapse totals come from
neuPrint. Coordinates are native 8 nm voxels; display axes map X, −Z, −Y.

Population/individual silencing applies on the next run, with restore controls.
The evidence compares the same task and checkpoint with and without visual
input. More extensive matched population ablations remain future work.

Source: [MaleCNS downloads](https://male-cns.janelia.org/download/), CC-BY,
FlyEM / HHMI Janelia and collaborators. Both coding flags remain false:
`dynamics_validated` and `flyvis_to_malecns_mapping_verified`. This does not
change the different existing motor-gate mapping flag.

## Reproduction

```sh
# Existing .venv and web/app node_modules are required.
PYTHONPATH=services/sim-engine .venv/bin/python scripts/prepare_coding_graph.py
PYTHONPATH=services/sim-engine .venv/bin/python -m uvicorn hawking_fly.api.app:app --host 127.0.0.1 --port 8050
npm --prefix web/app run dev
```

Open `http://localhost:5173/?view=coding`. The committed graph/checkpoint/captures
allow inference without requerying neuPrint. Anatomy uses the existing public
cache and fetches missing published skeletons. Regenerating the graph requires
the locally configured neuPrint token; it never goes to the browser.

To regenerate training images, select **Training & results → Capture & train**.
To optimize the saved browser captures offline:

```sh
PYTHONPATH=services/sim-engine .venv/bin/python scripts/train_coding_policy.py --seed 37 --epochs 900
# Optional continuation (local checkpoint only):
PYTHONPATH=services/sim-engine .venv/bin/python scripts/train_coding_policy.py --seed 37 --epochs 100 --resume
```

Then run **Evaluate held-out tasks + perturbation** in the browser. It uses the
same actual editor, action layer, sandbox and capture mechanism as Start.
Checkpoints bind graph hash and model version; a mismatch or absent checkpoint
fails explicitly. Browser captures are renderer-dependent; re-capture and
reevaluate after changing rendering assumptions.

## Tests and remaining work

Tests cover graph identity/separation, determinism, visual sensitivity, actual
connectivity contribution, silencing, checkpoint mismatch, split separation,
strict inference schema, WebSocket ordering, primitive input/editor mutations,
and reexecution of saved observations against the frozen model. Actual browser
episodes supply capture, execution, feedback, correction and replay evidence.

The complete master brief is **not finished**. Remaining research includes
broader curriculum and layouts, primitive motor learning, learned visual
reading, continuous neural dynamics, general JavaScript/debugging, full active
morphology/propagation, and unified event scrubbing of source/world/brain.
The current timeline inspects neural state at an event; it does not rewind the
live world/source to that point. Recording composites the actual desk canvas and a small real-anatomy view
using the same neural state and virtual tick. WebM takes are saved by content
hash under `experiments/coding_fly/recordings/` (ignored by Git) and opened with
View recording. It records wall-time execution,
with unpaced evaluation explicitly labeled; it does not manufacture typing.
Full active-pathway anatomy, biological spike propagation and broad coding
remain limitations, not secretly implemented substitutes.
