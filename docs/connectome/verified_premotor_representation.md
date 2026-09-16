# MaleCNS-grounded premotor representation (relay layer LC4/LPLC2 → DNp01)

**Naming decision:** this is a *MaleCNS-grounded* premotor representation, not a
*verified* one. MaleCNS connectivity and relay-cell identity are verified from
the live connectome, but the flyvis→MaleCNS input correspondence and the rate
model remain unverified (proxy / custom dynamics). These facts are tracked
separately in every artifact (see **Provenance flags** below).

## Status

Bounded 3-layer graph extracted from MaleCNS v1.0 and propagated. Relay-layer
activity is the premotor representation: **52 relay neurons** between the
visual circuit and DNp01, of which **21 receive LC4/LPLC2 input** and are the
driven premotor channels fed to the decoder.

## The graph

```
FlyVis visual activity (pretrained flow network, Lappalainen et al. 2024)
   │  proxy correspondence (LC4↔Tm/TmY, LPLC2↔T4/T5 — mapping.verified=False)
   ▼
LC4/LPLC2 proxy input representation       311 neurons
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
  "flyvis_to_malecns_mapping_verified": false,
  "dynamics_validated": false
}
```

| Aspect | Status | Why |
|--------|--------|-----|
| MaleCNS connectivity (edges) | ✅ verified | pulled live from MaleCNS v1.0, quantifiable synapse counts |
| Relay cell identities | ✅ verified | bodyId + type from neuPrint neuron table |
| FlyVis→cell correspondence | ⚠️ proxy | flyvis cell types don't include LC4/LPLC2 (LC4↔Tm/TmY, LPLC2↔T4/T5); bilateral symmetry assumed |
| Rate dynamics | ⚠️ custom | leaky-integrator + relu rate model, not biophysically validated |
| Decoder result | ⚠️ computational | see `docs/decoder/proxy_motor_decoding.md`; no validated claim made |

## Experiments

Canonical run: `experiments/loom_escape/20260916-214652/`

- `connectome/relay_<stim>.npz` — relay traces `(samples, frames, 52)`
- `connectome/dnp01_<stim>.npz` — DNp01 ground truth `(samples, frames, 2)`
- `connectome/relay_neurons.json` — per-neuron metadata (bodyId, type, driven flag)
- `connectome/premotor_validation.json` — Phase 3A check table
- `motor_gate_verified_v0.npz` + `manifest.json` — decoder dataset (21 driven channels)
- `motor_gate_verified_v0_type_agg.npz` + `manifest_type_agg.json` — 5 type-aggregated channels (secondary)
- `decoding_verified/` — decoder study on individual relay neurons
- `decoding_verified_type_agg/` — decoder study on type-aggregated channels
- `config_relay.json` — experiment config (graph=`relay`, relu nonlinearity)

Reproduce the graph: `discover_malecns_relay_path()` in `connectome/routes.py`.
Reproduce propagation: `python -m hawking_fly.experiments.run --config
experiments/loom_escape/config_relay.json`
Run validation: `python -m
hawking_fly.propagation.premotor_validation --run-dir experiments/loom_escape/20260916-214652`

## Phase 3A validation results (honest read)

| Check | Result | Evidence |
|-------|--------|----------|
| Non-trivial | ✅ | all 21 driven channels have nonzero std; 0 zero-std channels; finite |
| Input-bound, not a scaled copy | ✅ | per-channel corr with aggregate drive median 0.38–0.64 (not 0.99+); no pure-copy stimulus |
| Stimulus sensitivity — magnitude | ✅ | premotor magnitudes: loom 1.47 > flash 1.43 > moving-edge 1.35 |
| Stimulus sensitivity — profile shape | ⚠️ NO | pairwise profile cosine 0.9998+; the flyvis receptor drive itself is near-collinear across stimuli (cos 0.9998), so the relay faithfully propagates collinear input — this is a *found*, not manufactured, property of the current proxy input |
| Relay contributes to DNp01 | ✅ | ablation: removing PVLP122 → DNp01 changes DNp01 by −7.3%; SAD064 −7.2%; SAD073 −6.9% |

**Limitation reported, not papered over:** the proxy flyvis receptor drive does
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
| **Relay premotor (21 neurons)** | **0.980** | **0.810** | meaningful, Δ R² = +0.51 |
| Relay type-aggregated (5 types) | 0.980 | 0.474 | meaningful, Δ R² = +0.67 |

The individual-neuron relay representation improves the channel decode vs the
proxy and beats its channel-swap null by a wide margin (Δ R² = +0.51 vs the
proxy's fragile margin), while type-aggregation keeps profile R² but loses
channel R² — i.e. **channel-specific identity lives at the neuron level, not
the cell-type level**. These are model-computational results under the custom
rate dynamics; no validated decoding claim is made.

## Next steps / open questions

- The collinear-input limitation is upstream (proxy drive). Independently
  verifying the flyvis→MaleCNS correspondence (or mapping true visual-lobe
  responses onto LC4/LPLC2) is the next leg needed for channel-specific
  stimulus discrimination.
- Extended-graph analysis (adding the ~133 other DNp01 upstream partners) is
  deliberately deferred so the 3-layer bounded graph stays interpretable.
- Rate-model dynamics remain unvalidated; ablations quantify *modeled*
  contribution, not biophysical necessity.