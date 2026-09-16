# MaleCNS-grounded premotor representation (relay layer LC4/LPLC2 → DNp01)

**Naming decision:** this is a *MaleCNS-grounded* premotor representation.
MaleCNS connectivity, relay-cell identity, and the flyvis→MaleCNS input
correspondence are all grounded in live MaleCNS v1.0 connectome evidence; the
rate model remains custom and unvalidated. The flyvis→MaleCNS correspondence is
now *synapse-grounded* (see **flyvis↔MaleCNS correspondence validation** below)
rather than a hand-picked proxy: the flyvis cell classes driving each receptor
are those that actually synapse onto LC4/LPLC2 in MaleCNS v1.0, weighted by
their measured synapse counts. This is NOT a statement that flyvis responses
equal MaleCNS recordings (`dynamics_validated=false`). These facts are tracked
separately in every artifact (see **Provenance flags** below).

## Status

Bounded 3-layer graph extracted from MaleCNS v1.0 and propagated. Relay-layer
activity is the premotor representation: **52 relay neurons** between the
visual circuit and DNp01, of which **21 receive LC4/LPLC2 input** and are the
driven premotor channels fed to the decoder.

## flyvis↔MaleCNS correspondence validation (connectome-grounded drive)

Instead of hand-picking Tm/TmY (LC4) or T4/T5 (LPLC2) as a proxy, we queried
MaleCNS v1.0 for the *actual* presynaptic partners of every LC4 (126 neurons,
305,816 synapses) and LPLC2 (185 neurons, 354,150 synapses), then cross-matched
against the 65 cell types flyvis models. **The legacy proxy was badly wrong for
LC4** and the grounded plan differs materially:

| Receptor | Legacy proxy coverage of non-self input | Connectome-grounded coverage |
|----------|----------------------------------------:|----------------------------:|
| LC4 | **0.4%** (Tm5a/b/c, Tm9, Tm16, TmY10) | **60.1%** (T2, TmY3, Tm4, Tm2, Tm3, T5…) |
| LPLC2 | 36.7% (T4a–d, T5a–d only) | **63.1%** (Tm5Y, T5(d,b,c), T4c, Tm20, T4(b,a), T5a, T4d, TmY5a, Tm4, TmY18) |

LC4's real top inputs are T2 (46,156 syn), TmY3 (40,880), Tm4 (31,134), Tm2
(20,560), Tm3 (17,077) — all flyvis classes, none of which the legacy proxy used.
LPLC2's largest single input is Tm5Y (27,058 syn), then T5d/T5b/T5c/T4c/Tm20…

**Selection rule:** keep flyvis cells among a receptor's MaleCNS-typed
presynaptic partners (excluding self-feedback), ordered by synapse weight, until
90% of the flyvis-representable non-self input is covered (`min_synapses=50`).
Drive aggregation is a **synapse-weighted mean** over those classes (weights =
MaleCNS v1.0 synapse counts for that receptor type), replacing the legacy
equal-mean proxy aggregation.

| Aspect | FlyVis↔MaleCNS cell-class correspondence |
|--------|------------------------------------------|
| ✅ validated | the flyvis classes driving each receptor **do synapse onto** LC4/LPLC2 in MaleCNS v1.0, with measured weights |
| ⚠️ still assumed | ~40% of each receptor's non-self synapse input is non-flyvis (central-brain / non-modeled types) and is dropped |
| ⚠️ still assumed | single-eye flyvis activity is applied bilaterally (flyvis is one optic lobe; MaleCNS has L/R) |
| ❌ not claimed | flyvis *responses* equal MaleCNS *recordings* (`dynamics_validated=false`) |

`flyvis_to_malecns_mapping_verified=true` therefore means *synapse-grounded cell
correspondence*, nothing more. The canonical run uses this mode
(`config_relay.json`: `"mapping": "connectome_grounded"`); the legacy proxy is
retained in code as `legacy_proxy` for comparison/sensitivity only.

## The graph

```
FlyVis visual activity (pretrained flow network, Lappalainen et al. 2024)
   │  connectome-grounded correspondence (MaleCNS v1.0 presynaptic partners,
   │  synapse-count weighted — flyvis_to_malecns_mapping_verified=True)
   ▼
LC4/LPLC2 input representation            311 neurons (126 LC4 + 185 LPLC2)
   │  receptor_to_relay (1,858 edges, 17,889 synapses)
   ▼
MaleCNS relay population                    52 neurons (21 driven)
   │  relay_to_dn (231 edges, 6,996 synapses)
   ▼
DNp01 giant fiber                            2 neurons (ground truth)
```

| Layer | Edges | Synapses |
|-------|-------|----------|
| `receptor_to_dn` (direct, Phase 0A) | 329 | 11,224 |
| `receptor_to_relay` | 1,858 | 17,889 |
| `relay_to_dn` | 231 | 6,996 |
| **full graph** | **2,418** | **36,109** |

The direct LC4/LPLC2 → DNp01 path is kept in the graph alongside the relay
layer, so DNp01's modeled activity reflects both routes.

## Relay population (52 neurons; 21 driven, 31 input-free)

Neuron identity and synapse counts come from the live MaleCNS v1.0 adjacency
query (`fetch_adjacencies`), cached in `loom_escape_relay_neurons`,
`loom_escape_receptor_to_relay_edges`, `loom_escape_relay_to_dn_edges`, and
`loom_escape_full_graph` under `data/connectome/`.

### Driven relay neurons (receive LC4/LPLC2 input AND project to DNp01)

| Cell type | Neurons | LC4/LPLC2 → relay syn | relay → DNp01 syn |
|-----------|--------:|----------------------:|------------------:|
| SAD064 | 6 | 1,844 | 1,193 |
| PVLP122 | 6 | 5,506 | 1,052 |
| PVLP151 | 4 | 8,297 | 567 |
| SAD073 | 3 | 34 | 988 |
| PVLP010 | 2 | 2,208 | 628 |
| **total** | **21** | 17,889 (full type) | 4,428 (driven) |

### Input-free relay neurons (project to DNp01, no LC4/LPLC2 input)

31 neurons across JO-B1_a (14), AN08B098 (10), IN00A062 (3), AN12B001 (2),
SAD091 (1), and one SAD073. They are retained as structural nodes in the graph
but carry **no flyvis-derived drive** and are statically silent (relay trace
norm = 0), so they are **excluded from the decoder VISIBLE channels** to avoid
diluting the signal (31 of 52 channels would be constant zeros).

## Provenance flags (spec §8 / honesty policy)

Every artifact (manifest, validation JSON, run metrics) carries four separate
flags:

```json
{
  "connectome_edges_verified": true,
  "cell_identity_verified": true,
  "flyvis_to_malecns_mapping_verified": true,
  "dynamics_validated": false
}
```

| Aspect | Status | Why |
|--------|--------|-----|
| MaleCNS connectivity (edges) | ✅ verified | pulled live from MaleCNS v1.0, quantifiable synapse counts |
| Relay cell identities | ✅ verified | bodyId + type from neuPrint neuron table |
| FlyVis→cell correspondence | ✅ verified (synapse-grounded) | flyvis classes = MaleCNS v1.0 presynaptic partners of each receptor, synapse-count weighted; ~40% non-flyvis input dropped, bilateral application assumed |
| Rate dynamics | ⚠️ custom | leaky-integrator + relu rate model, not biophysically validated |
| Decoder result | ⚠️ computational | see `docs/decoder/proxy_motor_decoding.md`; no validated claim made |

## Experiments

Canonical run: `experiments/loom_escape/20260916-223510/` (**connectome-grounded
mapping**). Prior baseline: `experiments/loom_escape/20260916-214652/` (legacy
proxy, frozen at tag `milestone-malecns-grounded-premotor`).

New run contents:

- `connectome/relay_<stim>.npz` — relay traces `(samples, frames, 52)`
- `connectome/dnp01_<stim>.npz` — DNp01 ground truth `(samples, frames, 2)`
- `connectome/relay_neurons.json` — per-neuron metadata (bodyId, type, driven flag)
- `connectome/premotor_validation.json` — Phase 3A check table
- `motor_gate_verified_v0.npz` + `manifest.json` — decoder dataset (21 driven channels)
- `motor_gate_verified_v0_type_agg.npz` + `manifest_type_agg.json` — 5 type-aggregated channels (secondary)
- `metrics.json` → `connectome_provenance.mapping_summary` — per-run mapping mode, n_grounded/n_legacy_proxy, avg_coverage
- `grounded_premotor_decoding.json` / `grounded_premotor_type_agg.json` — decoder studies (see table)
- `config_relay.json` — experiment config (graph=`relay`, mapping=`connectome_grounded`)

Reproduce the graph: `discover_malecns_relay_path()` + `discover_receptor_upstream_evidence()`
in `connectome/routes.py`.
Reproduce propagation: `python -m hawking_fly.experiments.run --config
experiments/loom_escape/config_relay.json`
Run validation: `python -m
hawking_fly.propagation.premotor_validation --run-dir experiments/loom_escape/20260916-223510`

## Phase 3A validation results (honest read)

| Check | Result | Evidence |
|-------|--------|----------|
| Non-trivial | ✅ | all 21 driven channels have nonzero std; 0 zero-std channels; finite |
| Input-bound, not a scaled copy | ✅ | per-channel corr with aggregate drive median 0.38–0.64 (not 0.99+); no pure-copy stimulus |
| Stimulus sensitivity — magnitude | ✅ | premotor magnitudes: loom 1.47 > flash 1.43 > moving-edge 1.35 |
| Stimulus sensitivity — profile shape | ⚠️ NO | pairwise profile cosine 0.9998+; the flyvis receptor drive itself is near-collinear across stimuli (cos 0.9998), so the relay faithfully propagates collinear input — this is a *found*, not manufactured, property of the grounded input |
| Relay contributes to DNp01 | ✅ | ablation: removing PVLP122 → DNp01 changes DNp01 by −7.3%; SAD064 −7.2%; SAD073 −6.9% |

**Limitation reported, not papered over:** the flyvis receptor drive does
not discriminate stimuli in channel-profile space, so downstream relay activity
inherits that collinearity. The premotor representation is a faithful
MaleCNS-grounded signal for the *magnitude* of loom-escape drive, but
channel-specific stimulus discrimination is not demonstrated. This is exactly
the Phase 0C diagnostic (`pearson(profile_norm, truth_norm) = 0.999`): the
decode is largely magnitude bookkeeping.

## Threshold sensitivity (same 21-channel readout, per-neuron input cutoffs)

| Min LC4/LPLC2 input/relay neuron | Kept channels | Retained receptor→relay syn | Relay mean-abs norm (loom) |
|------:|-----:|--------:|--------:|
| 0 (all) | 52 | 17,889 | 0.118 |
| ≥ 10 | 19 | 17,883 | 0.282 |
| ≥ 50 | 16 | 17,773 | 0.288 |
| ≥ 100 | 15 | 17,723 | 0.280 |
| ≥ 250 | 14 | 17,612 | 0.272 |
| ≥ 500 | 10 | 15,929 | 0.235 |
| ≥ 1,000 | 9 | 14,978 | 0.218 |

> Note: thresholds ≥10 remove input-free cells but keep the driven 21's bulk
> (>99% of receptor→relay synapse weight). Reads are stable between ≥10 and
> ≥250; SAD064 and SAD073 drop out only at ≥500+ (their weakest cells carry
> single-digit to ~100-syn input). Keeping **all 10 relay types for the primary
> graph** is supported: every relay route contributes model-visible DNp01
> change under ablation, and the sensitivity surface is flat across plausible
> cutoffs.

## Decoder comparison (relay representation vs Phase 0C proxy)

| Study | Profile R² (LOO) | Channel R² (LOO) | Connectivity specificity |
|-------|-----------------:|------------------:|--------------------------|
| Proxy (311 receptor channels) | 0.674 | 0.547 | meaningful (fragile, n=8) |
| Relay premotor (21 neurons, legacy proxy) | 0.980 | 0.810 | meaningful, Δ R² = +0.51 |
| Relay premotor (21 neurons, **connectome-grounded**) | 0.984 | 0.731 | meaningful, Δ R² = +0.52 |
| Relay type-aggregated (5 types, grounded) | 0.984 | 0.412 | meaningful, Δ R² = +0.68 |

Profile R² (magnitude bookkeeping) is unchanged between mapping modes. Channel
R² *drops* slightly under the grounded mapping (0.810→0.731): the corrected
aggregation is a *synapse-weighted* mean over each receptor's real input classes
and drops the ~40% non-flyvis input, so some channel-discriminative structure
the legacy proxy happened to carry is gone — the extra discriminability was
partly an artifact of the wrong mapping. Both modes still beat their
channel-swap nulls by a wide margin (Δ R² ≈ +0.5), and individual-neuron
channels retain channel identity that type-aggregation loses. These are
model-computational results under the custom rate dynamics; no validated
decoding claim is made, and the grounded study requires an explicit
`--allow-grounded-mapping` reviewer opt-in (spec guard) to run.

## Next steps / open questions

- The collinear-input limitation persists even with the *correct* grounded
  mapping: relay channel-profiles remain near-collinear across stimuli because
  the underlying LC4/LPLC2 input is itself near-collinear (cos 0.9998). The
  correspondence is now synapse-grounded, so the remaining path to
  channel-specific stimulus discrimination is richer upstream dynamics, not a
  better mapping.
- ~40% of LC4/LPLC2 input is from non-flyvis (central-brain / non-modeled)
  types and is dropped. Modeling those inputs, or grounding flyvis *dynamic*
  response (not just class correspondence), would improve coverage.
- Bilateral symmetry remains an assumption (flyvis is one optic lobe; MaleCNS
  has L/R) — recorded, not verified.
- Extended-graph analysis (adding the ~133 other DNp01 upstream partners) is
  deliberately deferred so the 3-layer bounded graph stays interpretable.
- Rate-model dynamics remain unvalidated; ablations quantify *modeled*
  contribution, not biophysical necessity.