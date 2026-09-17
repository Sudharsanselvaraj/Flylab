# Phase 0A — flyvis validation on synthetic stimuli

Status: **Pass (with documented limitation)** — flyvis forward inference on
synthetic stimuli produces sane, distinguishable optic-lobe activity, and the
LC4/LPLC2-correspondent read-out cells carry measurable drive. The synthetic
*loom* does **not** produce the largest optic-lobe read-out; that is reported
below, not papered over.

## Precise question

*Can upstream neural activity reveal a blocked motor command?* Phase 0A only
asks the foundation question — does the pipeline produce **sane activity**
(finite, non-degenerate, distinguishable across stimuli, with measurable
drive in the cells that feed the loom-escape receptors) — **before any
decodability claim** (that is Phase 0C). Phase 0A is a go/no-go: no decoder
claims are made here.

## Method

1. The **pretrained flyvis optic-lobe ensemble** (`flow/0000/000`,
   Lappalainen et al., *Nature*, 2024 — the one validated component) runs
   forward inference on three synthetic stimuli: `flash`, `moving_edge`, and
   a custom `loom` (expanding disk rendered on the same hexagonal receptor
   lattice flyvis uses).
2. Responses are stored per stimulus (`*_responses.npz`) at run time.
3. `python -m hawking_fly.sensory.validation` reads those saved artifacts
   (plus the MaleCNS-grounded drive plan `connectome/mapping.json`) and
   checks sanity + read-out without re-running inference. Per-column
   `cell_type` labels are recovered once from a ~5 s minimal flash (neuron
   ordering is a static network property) and cached.

Reproduce:
```bash
python -m hawking_fly.sensory.validation \
  --run-dir experiments/loom_escape/20260916-223510 \
  --out experiments/loom_escape/phase_0a_validation
```
Artifacts: `validation.json`, `cell_type_labels.json`, `validation.png`.

## Evidence (canonical run `20260916-223510`)

### 1. Finite, non-degenerate, distinguishable — ✅

| Stimulus | finite | shape | mean |response|| std | max |response||
|----------|:------:|-------|------:|-----:|--------:|
| flash | ✅ | (1, 4, 600, 65) | 0.676 | 0.901 | 6.558 |
| moving_edge | ✅ | (1, 2, 465, 65) | 0.691 | 0.915 | 5.442 |
| loom | ✅ | (1, 2, 700, 65) | 0.681 | 0.910 | 5.675 |

Pairwise mean-trace MSE (nonzero ⇒ distinguishable): flash×edge 5.43e−05,
flash×loom 4.54e−05, edge×loom 2.93e−05.

### 2. LC4/LPLC2-correspondent read-out cells carry drive — ✅

The read-out is the union of flyvis cell classes that MaleCNS v1.0 shows
**synapsing onto LC4/LPLC2** (connectome-grounded plan, 311 receptors, ~56%
mean synapse-weight coverage), driven by a **synapse-weighted mean** of their
flyvis responses:

| Stimulus | weighted read-out drive |
|----------|------------------------:|
| moving_edge | 1.041 |
| loom | 1.012 |
| flash | 1.010 |

Top mapped classes (mapped flyvis ← MaleCNS synapse weight) behave as
expected optically: T2/TmY3/Tm4 drive LC4; Tm5Y/T5d…/T4c drive LPLC2. All are
nonzero for every stimulus.

### 3. Loom maximally activates its known read-out cells — ⚠️ NOT OBSERVED

On this synthetic stimulus set the **loom read-out is *not* maximal at the
optic lobe** (`moving_edge` 1.041 > `loom` 1.012 > `flash` 1.010). Loom drive
is clearly present and measurable but not the largest.

Two honest observations:

- The synthetic loom is an **expanding *bright* disk** (`intensity=1.0` on
  `baseline=0.5`). The canonical escape trigger in the literature is a
  *dark* expanding disk; a bright loom is less ethologically potent for the
  escape pathway.
- The loom-vs-flash ordering **flips downstream**: at the MaleCNS premotor
  representation DNp01 magnitudes are loom 1.47 > flash 1.43 > moving-edge
  1.35 (see `verified_premotor_representation.md`). The loom advantage is a
  *propagated* property of the connectome-grounded front-end, not an
  optic-lobe feature already present at the first read-out.

This is reported as a **found** property, exactly what Phase 3A flagged:
the flyvis read-out is near-collinear across stimuli (profile cos ≈ 0.9998);
downstream magnitude discrimination is what survives/emerges.

## Layer attribution (spec §3 / §8)

This repo is a **hybrid connectome-constrained simulation with a validated
pretrained visual component and custom, unvalidated downstream dynamics** —
not "a simulation of the fly brain".

| Pipeline stage | Component | Status |
|---|---|---|
| Optic lobe (65 columnar types, ~45.7k cells) | `flyvis` pretrained, published, peer-reviewed | ✅ **real + validated** |
| Stimulus encoding (flash / moving edge / loom) | `hawking_fly/sensory` (+ synthetic loom renderer) | ⚠️ synthetic, labeled |
| Optic-lobe responses | flyvis forward inference | ✅ finite, distinguishable (this doc) |
| LC4/LPLC2 correspondence | MaleCNS v1.0 synapse-grounded classes, weighted | ✅ **connectome-verified** (class identity + weights) |
| Receptor → relay → DNp01 propagation | custom leaky-integrator rate model (`hawking_fly/propagation`) | ⚠️ custom, `dynamics_validated=false` |
| Motor gate + decoder | recorded-artifact replay (Phase 0B/0C) | ⚠️ model-inferred, no validated claim |

## Honesty invariants

- `dynamics_validated=false` everywhere; never upgraded in the UI or docs.
- Decoder/motor results are labeled **model-inferred**; Phase 0A makes no
  decoder claims.
- Limitations (bright loom, ~40% non-flyvis input dropped, single-eye
  bilateral assumption, static label alignment) are recorded in
  `validation.json` and above.
- Coverage gaps are explicit (§3): the flyvis↔MaleCNS class correspondence is
  synapse-grounded but *not* a claim that flyvis responses equal MaleCNS
  recordings.

## Related artifacts

- Run: `experiments/loom_escape/20260916-223510/` (flyvis npz, connectome,
  grounded decoder study).
- Validation: `experiments/loom_escape/phase_0a_validation/{validation,cell_type_labels}.json`, `validation.png`.
- Notebook: `notebooks/01_flyvis_validation.ipynb`.
- Premotor representation (Phase 0A-hop continued): `docs/connectome/verified_premotor_representation.md`.
- Next gate: Phase 0B (motor gate pairing, [`docs/phase_0b.md`](phase_0b.md)) then Phase 0C (decoder) — see `docs/decoder/proxy_motor_decoding.md`.