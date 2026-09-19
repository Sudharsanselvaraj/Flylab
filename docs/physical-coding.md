# Physical coding: contact-driven Chromium

The default app replaces the previous token insertion demo. Its first task starts
with an empty editor and empty preview and constructs `<h1>Hello World</h1>` through
native Chromium input. A single-character policy decision expands to physical
modifier/key down/up actions. No live `fill`, `type`, `insert_text`, editor setter,
DOM text insertion, source-writing API or runtime LLM is used.

## Causal boundary

1. `BrowserComputer` creates an empty textarea IDE before Start. Target rendering is
   privileged environment setup; target source is never sent to the policy.
2. `page.screenshot()` captures the actual 1200×600 Chromium viewport. The monitor
   shows that PNG, not a drawn source listing or DOM-to-SVG approximation.
3. The engineered retina scans fixed glyph windows in the target, editor and preview.
   Each patch drives 101 identified MeTu input sites for 16 ticks in either the
   677-cell subgraph or the full 176,422-cell recurrent network. A learned readout sees only the 576 non-input states. Native red caret
   pixels and visible focus/Run indicators are also visual sensor features.
4. A learned positional copy/literal transducer proposes glyphs; a trained generic
   editing gate chooses Focus, one character, Backspace, Run or Finish. Prefix and
   equality comparisons are explicit engineered features over **visual readings**.
   HTML syntax appears in the offline training teacher, not inference code.
5. `ComputerActuator` moves the foreleg along a deterministic kinematic trajectory.
   The physical key is resolved from contact geometry. Only contact authorizes
   `keyboard.down(code)`. Release lifts the key and emits `keyboard.up(code)`.
   Uppercase and shifted punctuation physically hold Shift with the other foreleg.
6. The web client acknowledges rendering each pose before the server proceeds.
   A missing contact or failed render acknowledgment prevents the key event.
7. Native trusted input changes the textarea. Its ordinary input handler executes
   the resulting source in an isolated preview iframe; F8 explicitly runs it again.
   Auto-preview ensures an erroneous character really reaches execution before
   correction. The Run handler never alters source.
8. A new screenshot returns to the policy. The privileged evaluator separately
   reads source, `isTrusted`, revision and browser event times, and compares rendered
   target/output pixels. None of those audit values enters `observe()`.

The browser, model and motor share an integer clock with **2 ms per tick**.
Playwright's virtual browser clock advances only when the session advances.
Rate dynamics continue during movement and key presses. The UI does not create
scientific events. Display pacing and video frame rate are presentation concerns;
virtual elapsed time is not represented as biological or wall-clock performance.

The browser is a dedicated, headless Chromium process. The 3D monitor receives
viewport screenshots after actions, and keeps the previous captured frame while
the motor moves. It is a sampled viewport, not a remote desktop video stream.
The real editor caret is in the screenshot; Chromium screenshots omit the OS
mouse cursor. The native mouse position/events are in the timeline; no fake cursor
is drawn over the monitor.

## Real, modeled, trained, engineered

- **Real:** the subgraph's 677 identities, 46,149 directed connections and
  534,173 synapses; or the full graph described below. Native spatial coordinates
  and available SWC morphology come from the published dataset. Whole
  CNS, substrate and selected-neuron views reuse measured anatomy. The graph count
  is not evidence of a coding brain.
- **Modeled:** continuous rate dynamics, positive normalized connection weights,
  fixed seeded sensory projections, threshold-integrated spike markers. Biological
  transmitter signs and dynamics are not validated. Spike IDs identify precursors
  in a rate-based controller; individual spike causality is not claimed.
- **Trained:** neural glyph decoder, positional heading transducer and editing gate.
  Parameters and optimizer state are saved, with actual losses and hashes.
- **Engineered:** fixed 20 px Courier retinal windows, generic comparison features,
  US keyboard layout, two foreleg effectors, contact trajectory, IDE, reward and
  experimental fault injector. This is kinematics, not a validated insect body or
  a rigid-body contact solver. Morphology in the brain view is measured; the desk
  fly is an illustrative embodiment.

The native keyboard includes individual labeled keys, Shift, Control, Alt,
Backspace, Enter, space, arrows and Run/F8. The actuator supports separate mouse
move/down/up/right-click and wheel events. Only the small heading controller's
subset has behavioral training evidence. No claim is made for untrained shortcuts,
multiline editing, CSS, JavaScript construction or arbitrary code repair.

## Training and data separation

`python scripts/train_physical_coding.py` captures Chromium glyph fixtures and
trains three supervised models. The transducer learns from an offline heading
curriculum across all supported lengths (1–20 glyphs). The gate learns generic
editing-state examples. These are engineered teacher labels, not reward learning.

`python scripts/train_physical_coding.py --episodes` additionally runs three real
contact-driven training episodes: Learn Keys, Neural Lab and Blue Sky (one fault).
Their recorded screenshots and audited labels augment training of the neural
visual readout. These are training episodes, not held-out results.

`python scripts/train_physical_coding.py --resume` loads component weights **and
Adam optimizer state**, verifies the dataset hash, and performs 100 additional
epochs per component. Checkpoints preserve initial/final parameter hashes and
measured loss history. Training modifies weights; inference does not.

Validation words: Green Lab. Held-out word combinations: Hello Fly and Fly World.
Acceptance: Hello World. All glyph identities and supported string lengths appear
in the curriculum: held-out results test **word recombination**, not new syntax,
fonts, layouts, application types or broad programming. Offline component accuracy
is never the displayed coding-agent success rate.

`python scripts/evaluate_physical_coding.py` runs live Chromium acceptance,
wrong-key, validation, held-out, visual-input-silenced and restored episodes. It
writes `experiments/physical_coding/evaluation.json`, with session IDs, actual
rewards, success/failure, action counts, corrections, timing and checkpoint hashes.
The restoration comparison checks full decisions (including neural event IDs and
observation hashes), not only final text.

## Evidence and replay

Every session stores:

- `episode.json`: empty initial audit, decisions, checkpoint and graph hashes,
  observation hashes, result and timing.
- `timeline.json.gz`: clocked neural frames, modeled spike IDs, motor poses,
  contact, key-down/up, trusted native browser input, editor revisions, source,
  screenshot hashes and evaluator scores. Neural state frames are sampled; complete
  threshold crossings are stored separately in `spikes.bin`. Older version-1
  episodes only retain a bounded recent spike window and are not relabeled lossless.
- PNGs: actual Chromium screenshots, including incorrect intermediate source
  and preview. Source is never reconstructed from policy intentions.
- `index.html` and `project.zip`: exported **after** execution from the audited
  editor. Saving an artifact does not write into the live editor.

Replay displays the recorded monitor PNGs, key states, fly poses and neural frames
in their original order. It does not claim to re-run a new browser episode. The
separate restored run tests deterministic behavior. Click a character in the
source inspector to see its decision, neural precursor IDs, physical contacts and
timestamps. Native events with revision/caret information remain in the full audit.

The Record control captures the actual desk canvas and the synchronized full-CNS
instrument (or the expanded brain canvas while inspecting). It saves WebM locally. This is a sampled presentation of the running model;
recording never chooses actions or edits source.

## Start locally

```sh
.venv/bin/python -m pip install -e 'services/sim-engine[dev]'
.venv/bin/python -m playwright install chromium
PYTHONPATH=services/sim-engine .venv/bin/python -m uvicorn hawking_fly.api.app:app --host 127.0.0.1 --port 8050
npm --prefix web/app run dev
```

Open `http://localhost:5173/`. World/Desk/Fly/Keyboard/Follow Action change the
observer camera; Brain opens actual anatomy. Evidence & source contains exports
and full replay. Population silencing takes effect on the next session.

FlyLab is the only application. The retired motor-gate and wheelchair experiment
screens and API routes have been removed. The internal `hawking_fly` Python
namespace remains for script and environment compatibility.

## Known limits

Fixed font/layout, single-line headings and a small symbol/length envelope. The
visual parser depends on visible caret and fixed regions. Corruption away from the
end can require deleting/retyping the suffix. The heading transducer is an explicit
small learned architecture; these results do not establish spontaneous coding or
biological programming. Subsequent HTML/CSS/JavaScript curricula remain future work.

The historical `coding/` token prototype and its synthetic-event results are kept
for reproducibility; the default app does not import or run that autonomous path. Its old inference
endpoints are not mounted in the production API; only the recording-artifact
endpoints are retained.

## Full CNS runtime and live instrument (2026-09-19)

The physical coding lab now has an always-visible CNS instrument beside the room.
The anatomy cache contains **176,422 neuPrint Neuron records**, including incomplete
and untyped records. **142,757** have published soma/tosoma coordinates; **33,665**
have none and are counted but never placed at invented positions. These counts are
not the publication's approximately 166,700 curated-neuron figure.

`prepare_full_cns.py` reads the official MaleCNS v1.0 segment graph in Arrow batches,
keeps every positive connection whose two endpoints are cached Neuron records, and
builds CSR matrices. This retains **25,862,574 directed connections representing
125,024,863 synapses**. Non-neuron segment fragments are explicitly excluded; there
is no degree, region or edge-weight downsampling. Source and CSR SHA-256 hashes are
in `data/full_cns/manifest.json`. Reproduce from the official download URL recorded
there; the large public cache is ignored by Git.

Three explicit dynamics choices are available:

- Subgraph: the original 677-neuron physical-coding checkpoint.
- Full CNS float32: every one of the 176,422 states and all retained connections.
- Full CNS float64: the same topology/equations at higher numeric precision.

These are **engineered, all-positive, incoming-normalized rate dynamics**, not a
validated electrophysiological reconstruction. They do not model transmitter sign,
conduction delay, ion channels or validated insect biomechanics. Float64 is not
advertised as biological accuracy. The time step is 2 ms; the fixed recurrence is
not suitable for changing dt without reparameterization and retraining.

The full model has the same 101 identified visual input sites and 576 identified
readout sites, embedded in the entire recurrent graph. All other neurons still
update and contribute through the complete CSR matrix on every tick. The glyph
readout is trained separately on full-network responses. The learned heading
transducer/edit gate are inherited with their checkpoint hash recorded. No runtime
HTML template or source/DOM input is introduced. Full-network weights live under
`experiments/physical_coding/full_network`, separate from the tested subgraph weights.
A 128-tick neutral-input settling interval advances the actual browser/neural clock
before the first full-network observation.

The measured CPU kernel benchmark on this Mac was 0.120× real time for float32 and
0.115× for float64 (100 ticks, after warmup), using ~208 MB of sparse arrays. See
`experiments/full_cns/benchmark.json` for machine, hashes, timings and peak RSS.
These are compute-only numbers: live display, archives and browser operations make
the complete loop slower. Its instrument reports measured simulation-time/wall-time,
excluding intentional pauses. PyTorch MPS rejected native sparse CSR; no GPU speedup
is claimed. Event-only updates would change this continuous-rate model, so no such
approximation is silently substituted.

### Instrument, trace and clock

Static anatomy is uploaded once to a point buffer; body IDs map into a float activity
texture. A separate dim cool-gray layer shows anatomy. Modeled rates above 1 Hz
use muted blue → cyan → blue-white, saturating visually at 40 Hz; recorded threshold
crossings flash white with a default 12 ms simulation-time decay (8–100 ms selectable).
Amber is reserved for selected neurons and connectivity. Optional baseline response
shows absolute rate changes, saturated at 8 Hz. Anatomy-only cells have no dynamic
color. Compact anatomy samples one in eight cells, while activity includes every
located cell. The full view includes all located anatomy. No animation uses
wall time to create neural activity. Display LOD caps recent event markers at 20,000
and the raster at 1,000 actual sampled marks; these caps do **not** affect dynamics,
exact event counts or the complete spike archive. Selected real SWCs and published
upstream/downstream partner tables remain inspectable. Connectivity lines are not
fabricated neurite trajectories or synaptic coordinates.

A versioned binary packet (`CNS1`) transports little-endian tick, rate count and event
count, followed by float32 rates and uint32 `(tick, neuron_index)` event pairs. The
backend archives **every threshold event** in `spikes.bin`, plus its body-ID mapping
and hash in `episode.json`. Full-network activity packets are also stored individually
for synchronized replay. This can produce substantial local recordings; none are
uploaded. Subgraph timelines retain their rate snapshots and exact full spike archive.

Pause waits at a simulation boundary, captures the real Chromium screen/audit and
current neural state, and freezes the shared clock. A motor pose still needs a rendered
acknowledgment before its native key event is allowed. Resume continues the same state.
Replay restores the recorded browser image, neural packet, pose, source and timestamp;
it does not reinfer or regenerate source. Neuron trace queries scan the lossless archive,
not the display sample. Their following-decision windows are temporal associations,
not proof of causal necessity. The explicit silencing controls provide intervention
experiments for both modes.

Each new decision also saves an 80 × 576 float32 `readout-XXX.bin` containing the actual
neural state values passed into the trained glyph readout for every retinal slot. Its
shape, indices and hash are recorded with the decision. Key/source inspection links
these values, checkpoint identity, observation hash and physical contact timestamp.
The model consumes continuous rates; its threshold markers are derived recordings,
not claims that individual spikes alone caused a key.

### Observable training

The evidence drawer shows real logged loss values. “Train a new full-network readout”
launches the local CPU training script and reports actual feature-capture ticks and
optimizer epochs. Candidate weights, Adam state, standardized features, hashes and
job logs are saved under `experiments/physical_coding/training_runs/<id>`. Resume uses
the saved dataset and optimizer for 100 more epochs with a dataset hash check. New
candidates do not replace the tested active policy automatically. The original active
full checkpoint was trained before feature-cache/resume support was added; its optimizer
is retained, but it has no saved feature cache and is not presented as a resumable job.

The new chair has a pedestal/caster base, seat below the desk, back/lumbar support,
armrests and a foot bar. The fly's abdomen rests on the seat; middle/rear tarsi have
support points. An inverse transform maps the canonical world-space foreleg contact
positions into the seated body frame, preserving the actual keyboard contact gate.

### Verified parallel CPU path

On this Mac, `python scripts/build_full_cns_native.py` compiles the small local
`csr_parallel.c` kernel with Clang and GCD. It partitions rows across CPU workers;
each row still sums **every stored edge in the same order**. There is no graph
pruning or skipped neural tick. Compiler FMA contraction matches this SciPy build.
The builder verifies all 176,422 rates and threshold events for 256 changing-input
ticks against SciPy, bit for bit, before setting the verified-build flag. Runtime
also checks the kernel source hash. A stale/unavailable build uses portable SciPy,
and the instrument reports which engine is actually running. Float64 uses SciPy.

Under concurrent validation load, the measured matrix update was 36.02 ms in SciPy
and 8.32 ms with GCD (100 updates each). This is a kernel comparison, not an end-to-end
speed guarantee. See `experiments/full_cns/native_verification.json`. Dynamic state,
retinal dwell, policy weights, contact gates and 2 ms simulation steps are unchanged.
The isolated earlier SciPy benchmark and the concurrent-load comparison are distinct
measurements and must not be combined into an invented speedup figure.

Full-network trials can be reproduced with:

```sh
.venv/bin/python scripts/evaluate_full_cns.py --case wrong-key
.venv/bin/python scripts/evaluate_full_cns.py --case heldout
.venv/bin/python scripts/evaluate_full_cns.py --case silenced
.venv/bin/python scripts/verify_full_cns_evidence.py SESSION_ID
```

The evidence drawer labels full-network and subgraph results separately. Completed
runs remain selectable for replay after a page reload. Neuron inspection can query
the complete spike archive and recorded rate history, even when the display's
recent-event sample omitted a cell. The full-network visual-input ablation measured
zero decisions and zero key-down events while all other neural states continued
updating; it abstained rather than executing a default action sequence.

### Measured full-network acceptance

The parallel float32 wrong-key trial `80459902543e4b6b8b53d622060ed651` completed
`<h1>Hello World</h1>` with **29 trusted native key-down events**, one learned
Backspace correction, and **zero final pixel error**. It simulated 75.276 seconds
in 695.39 wall seconds under concurrent validation load (0.108× real time).
All **71,938,227 threshold events** matched the streamed binary packets and the
lossless archive. This was a headless contact-gated acceptance run; it did not
claim live 3D render acknowledgments. Separately, interactive full-CNS trial
`a0c8750019e744d394b95aaf90e8d984` verified ten native key-downs, all preceded by
acknowledged rendered contact poses, before it was intentionally stopped to test
the faster runtime. Its partial result is not labeled a completed coding trial.

The native rate/threshold trajectory comparison, contact-gate browser tests,
complete model run, and interactive render proof test distinct boundaries. None
alone is presented as a validated biological fly or a general programming agent.

The held-out full-network trial `89be0379fe174413919b5c6f0432e2ee` completed
`<h1>Hello Fly</h1>` from an empty editor: **25 trusted native key-downs**, no
corrections, and zero final pixel error. It simulated 63.556 seconds in 481.44 wall
seconds. All **60,730,249 threshold events** matched the streamed packets and archive.
This was also a headless contact-gated run. These two heading tasks establish a
narrow benchmark result, not general coding ability or validated physiology.

The compact instrument renders every eighth actual located cell to reduce display
cost, with that sampling stated in the panel. The expanded whole-CNS inspector
renders all 142,757 available positions. Neither display choice changes the
176,422-neuron computation or the lossless event archive. Cells without coordinates
remain counted but are never assigned synthetic positions. Replay uses saved neural
packets, screen captures and physical poses; it does not rerun the controller.

For the full-CNS browser demo, use `cd web/app && npm run demo` (stop an existing
Vite server on port 5173 first). This serves the production build with the same API
and WebSocket proxy. React development profiling can clone large neural-state
props into performance entries, causing substantial memory/latency overhead; use
`npm run dev` for editing, and the production demo for full-network sessions.


### Coding Fly 2.0 runtime update

See [the current implementation state](coding-v2.md). New sessions measure a
128-tick resting baseline, use continuous 84 ms unmodified-key strokes, and reuse
previously measured glyphs only when retinal pixels are unchanged. Each decision
records refreshed slot indices and the original sample tick for every cached
readout. Older timing figures above describe the previous observation schedule.
The new dark workspace preserves glyph rasterization through compositor inversion
and explicit retinal normalization. Completed sessions flush a final neural
packet so the archived tail of the spike stream is available to replay.
