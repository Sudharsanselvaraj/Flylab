# Live blocked sensorimotor trials

- `decoder.json`: current frozen multi-cut/multi-representation fits, training protocol, held-out errors and provenance hashes.
- `calibration_samples.npz`: actual camera/FlyVis/LIF rate samples, ungated modeled DNp01 targets and trial groups.
- `trial_acceptance.json`: actual quiet, approaching, relay-cut and sensory-cut runs, including complete sampled results and exact replay verification.
- `trial_recording.json`: replayable four-trial command log and final result.
- `findings.md`: measured results and limits of the scientific interpretation.

Regenerate with `python -m hawking_fly.simulation.calibrate` and
`python scripts/verify_blocked_trials.py`, using the repository virtual environment
and `PYTHONPATH=services/sim-engine`.

`benchmark.json` and `websocket_smoke.json` are historical measurements of the
previous Phase 1 cruise implementation. Their hashes intentionally differ from
the trial revision; they are not current performance or acceptance claims.

The frozen fits are not biologically validated. Confidence is unavailable.
