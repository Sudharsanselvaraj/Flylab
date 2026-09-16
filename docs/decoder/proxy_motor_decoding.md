# Phase 0C — Experimental decoder study (proxy motor-signal decoding)

> **Status: EXPERIMENTAL.** This study decodes the DNp01 ground-truth response
> from the current *proxy* upstream drive (flyvis receptor proxy, `mapping.verified
> = False`, spec §8). It must not be reported as validated motor-signal decoding.
> The verified MaleCNS premotor representation can later replace the proxy via
> `hawking_fly/decoder/data.py` without changing the decoder API.

## Proxy motor-signal decoding

### Setup

- Source: integration run `experiments/loom_escape/20260916-210539`
  (paired dataset `motor_gate_paired_v0.npz`; manifest carries
  `mapping.verified=False` and `model_choice=relu`).
- Units: whole trajectories — flash ×4, moving_edge ×2, loom ×2 (n=8).
- VISIBLE = upstream proxy receptor drive; GROUND TRUTH = per-trajectory norm of
  the DNp01 trace.
- Representations:
  - `profile` — channel-agnostic magnitude profile (8 time bins + total norm).
  - `channel` — per-channel mean |drive| (preserves channel identity; ridge λ=50).
- Model: linear ridge, leave-one-trajectory-out (LOO) and leave-one-stimulus-out.
- Splits are trajectory-level only (no shared frames between train and test).

### Regression (LOO)

| rep | R² | RMSE | Pearson |
|----|----|-----|---------|
| profile | 0.674 | 1.11 | 0.917 |
| channel | 0.547 | 1.30 | 0.752 |

Classification view (truth norm above leave-one-out train median): ROC-AUC 1.00
for both reps — **n=8, high variance; treat as information-limited.**

### Generalization (leave whole stimulus out)

| leave out | rep | R² | RMSE | Pearson |
|-----------|-----|----|------|---------|
| flash (n=4) | profile | 0.982 | 0.22 | 0.998 |
| flash (n=4) | channel | 0.466 | 1.19 | 0.928 |
| loom (n=2) | profile | 0.850 | 0.89 | 1.000 |
| loom (n=2) | channel | 0.570 | 1.50 | 1.000 |

### Null-model comparisons (200 shuffles)

| baseline | rep | R² mean (std) | true percentile |
|----------|-----|---------------|-----------------|
| shuffled labels | profile | −38.8 (±42) | R² 100%, AUC 100% |
| shuffled labels | channel | −0.51 (±0.9) | R² 90%, AUC 100% |
| channel swap | profile | 0.674 (±0) | 100% — **degenerate** |
| channel swap | channel | −6.80 (±2.3) | 100% (true beats null by +7.34 R²) |
| column permutation | profile/channel | ties true exactly | — degeneracy check only |

### What this means (honest read)

1. **The profile decode is magnitude bookkeeping, not channel reading.**
   `pearson(total visible norm, truth norm) = 0.983`, and `channel_swap` on the
   profile representation ties the true model exactly — by construction the
   profile erases channel identity, so "generalization" R² of 0.85–0.98 on
   held-out stimuli reflects the near-deterministic relation *bigger upstream
   drive → bigger DNp01 norm* (a consequence of the relu + leaky-integrator
   pipeline), not informative wiring.
2. **A weak channel-specificity signal exists but is fragile.** The channel
   representation beats its channel-swap null by a wide margin, yet with n=8
   trajectories and 311 features that margin is high-variance and may be
   dominated by the 7-point training folds.
3. **Per instruction: stop and report rather than overclaim.** The proxy mapping
   is unverified, n is tiny, and the dominant signal is structural magnitude — so
   no validated motor-signal decoding claim is made here.

### Leakage and temporal sanity checks

- Trajectory ids unique; splits operate on whole trajectories; test features are
  computed from the test trajectory's own VISIBLE trace only (asserted).
- Temporal generalization via leave-one-stimulus-out (flash, loom) above.
- Diagnostics explicitly record the norm-truth correlation as a leakage risk flag
  rather than hiding it.

### Next step

Obtain/verify the MaleCNS premotor representation, then re-point `load_paired_dataset`
at it (same API) and rerun this study. Only then do Phase 0D/0E and any UI-facing
description of a conclusive decoder.