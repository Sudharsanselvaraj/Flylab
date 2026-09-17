# Phase 0B — Motor gate + paired visible/ground-truth traces

Status: **Implemented** (Phase 0B). This is a *documentation and
reproducibility* milestone closure: the pairing was already produced by the
canonical runs; this doc records what the gate means, what the datasets
contain, and what remains unverified, and makes the verified pairing
reproducible from the CLI.

## What Phase 0B is

The **motor gate** (spec §4.4) is the boundary where activity becomes
mechanical: the DNp01 giant-fiber trace is the command output, and the gate
**withholds it from anything downstream**. Phase 0B materializes the paired
dataset a decoder (Phase 0C) trains on:

- **VISIBLE** = upstream premotor activity the decoder is allowed to see.
- **GROUND TRUTH** = DNp01 activity, withheld.
- Both halves come from the **same integration run**, matched **per sample and
  per frame** — the alignment is exact, never interpolated across runs.

Phase 0B builds the dataset only; it trains no decoder (that is Phase 0C) and
makes no biological claim.

## The gate in this codebase

The gate is a **recorded-pairing boundary**, not a live simulator hook: we run
the optic-lobe + MaleCNS premotor leg once, store both halves, and let any
downstream (decoder, Phase 0E communication panel, wheelchair avatar) read the
recorded pairing. This is why `dynamics_validated` is `false` everywhere on
these artifacts — the "gate" is modeled, not implanted in a living fly.

## Two dataset vintages (proxy vs MaleCNS-grounded)

The codebase keeps both explicitly, with distinct provenance flags:

| Vintage | VISIBLE | Builder | Runs | `flyvis_to_malecns_mapping_verified` |
|---|---|---|---|---|
| **Legacy proxy** | receptor drive (311 receptors), `motor_gate_paired_v0.npz` | `build_paired_dataset` | `20260916-210539` | `false` (`mapping.verified=False`) |
| **MaleCNS-grounded, per-neuron** | 21 driven relay channels, `motor_gate_verified_v0.npz` | `build_verified_premotor_dataset` | `20260916-214652` (proxy-tolerant), `20260916-223510` (grounded) | `true` only in the canonical run |
| **MaleCNS-grounded, type-agg** | 5 relay types, `motor_gate_verified_v0_type_agg.npz` | `build_verified_premotor_dataset(type_aggregated=True)` | same as above | `true` only in the canonical run |

> `flyvis_to_malecns_mapping_verified=True` means the flyvis cell classes
> driving each LC4/LPLC2 receptor are the ones MaleCNS v1.0 shows synapsing
> onto it, weighted by measured synapse counts. It is **not** a claim that
> flyvis responses equal MaleCNS recordings — `dynamics_validated` stays
> `false` everywhere.

## Canonical pairing (`20260916-223510`, connectome-grounded)

Per-neuron representation (`manifest.json`):

| Stimulus | n_samples | frames | VISIBLE shape | TRUTH shape |
|---|---|---|---|---|
| flash | 4 | 600 | (4, 600, 21) | (4, 600, 2) |
| moving_edge | 2 | 465 | (2, 465, 21) | (2, 465, 2) |
| loom | 2 | 700 | (2, 700, 21) | (2, 700, 2) |

The 21 visible channels are the **driven relay neurons** (LC4/LPLC2 → relay →
DNp01; types PVLP010, PVLP151, SAD073, PVLP122, SAD064, kept per-cell). 31
input-free relay neurons are **excluded** from VISIBLE (`n_silent_excluded=31`)
so the decoder never trains on constant-zero channels. The type-aggregated
representation collapses the driven subset into 5 channels
(`PVLP010, SAD064, SAD073, PVLP122, PVLP151`).

## Provenance flags (honesty invariants)

| Flag | Value | Meaning |
|---|---|---|
| `connectome_edges_verified` | `true` | edges pulled live from MaleCNS v1.0 |
| `cell_identity_verified` | `true` | relay bodyIds + types from neuPrint |
| `flyvis_to_malecns_mapping_verified` | legacy: `false`; grounded: `true` | synapse-grounded class correspondence only |
| `dynamics_validated` | `false` | rate-model dynamics are custom, never claimed validated |
| `mapping_verification_note` | explicit text | spells out that verified ≠ recording equality |

No artifact in this milestone claims validated motor-signal decoding. The
decoder reading this pairing must carry these labels (spec §8) — the manifest
repeats them so a future consumer can never misread the pairing as validated
biophysics.

## Reproducibility

```bash
# legacy proxy pairing
python -m hawking_fly.motor_gate.dataset \
  --run-dir experiments/loom_escape/20260916-210539 --out-dir /tmp/mg_proxy

# MaleCNS-grounded pairing, per-neuron (21 channels)
python -m hawking_fly.motor_gate.dataset \
  --run-dir experiments/loom_escape/20260916-223510 --out-dir /tmp/mg_percell --verified

# MalCNS-grounded pairing, type-aggregated (5 channels)
python -m hawking_fly.motor_gate.dataset \
  --run-dir experiments/loom_escape/20260916-223510 --out-dir /tmp/mg_typeagg --verified --type-agg
```

Each invocation emits the he same `motor_gate_verified_v0(.type_agg).npz` +
manifest that the canonical run contains, byte-compatible by construction
(stdin/stdout-neutral builders over the same inputs).

## Downstream consumers of the "blocked gate"

- **Phase 0C decoder** — `docs/decoder/proxy_motor_decoding.md`: trains on the
  paired visible/truth (proxy study; grounded study in the canonical run).
  Results are labeled model-inferred.
- **Phase 0E wheelchair avatar** — `docs/frontend/phase_0e.md`: the avatar's
  `gate blocked` state is read from the recorded motor-gate data this
  milestone defines (recorded withholding, not live gating).

## Limitations (reported, not papered over)

- The premotor relay read-out is **near-collinear across stimuli** in channel
  profile space (found property; downstream magnitude ordering loom 1.47 >
  flash 1.43 > moving-edge 1.35 is what discriminates — see
  `docs/connectome/verified_premotor_representation.md` §Phase 3A).
- ~40% of LC4/LPLC2 non-self synapse input is from non-flyvis types and is
  dropped from the grounds drive.
- Rate-model dynamics are **custom and unvalidated**; ablations quantify
  *modeled* contribution, not biophysical necessity.
- FlyGym embodiment is not part of Phase 0B; the gate boundary is recorded,
  not electrically implanted in a simulated body.

## Related artifacts

- Builder + CLI: `hawking_fly/motor_gate/dataset.py`
- Tests: `tests/test_motor_gate_dataset.py` (5 tests incl. verified + type-agg)
- Canonical run: `experiments/loom_escape/20260916-223510/{motor_gate_verified_v0*.npz,manifest*.json}`
- Upstream graph: `docs/connectome/verified_premotor_representation.md`
- Milestone chain: `docs/phase_0a.md` → this doc → `docs/decoder/proxy_motor_decoding.md` → `docs/frontend/phase_0d.md`, `docs/frontend/phase_0e.md`