# Initial blocked-trial findings

These are results from the current engineered hybrid model, not biological validation.

## Held-out reconstruction

Eight complete fixed-body trials trained the frozen ridge models; four different complete trials were held out. All cuts are evaluated against the same ungated modeled DNp01 targets.

| Cut | Individual channels MAE | Mean magnitude MAE | Mean-removed pattern MAE |
|---|---:|---:|---:|
| dn | 1.529 Hz | 1.657 Hz | 1.529 Hz |
| relay | 2.078 Hz | 2.078 Hz | 2.078 Hz |
| sensory | 16.675 Hz | 16.675 Hz | 16.675 Hz |

The constant training-mean baseline is 16.675 Hz MAE. At the DNp01 cut, neuron-specific channels improve MAE over the population mean by only 0.128 Hz. This is not strong evidence for a unique identity-pattern advantage. Mean removal does not remove all amplitude information from heterogeneous population patterns; a stronger normalized-pattern or shuffled-identity study remains warranted.

The relay-input readout uses sensory proxies, not an earlier serial relay chain. The sensory-entry readout has no modeled input channels and reduces to the training mean. These three points are graph-specific controls, not a continuous anatomical cut-depth curve.

## Actual closed-loop acceptance, seed 43

| Condition | Cut | Body fixed | Event latency | MAE | Movement |
|---|---|---|---:|---:|---|
| quiet | dn | False | none | 1.516 Hz | Stationary |
| loom | dn | False | 195 ms | 5.327 Hz | One maneuver, then stopped |
| loom | relay | True | 160 ms | 4.107 Hz | Stationary |
| loom | sensory | True | none | 20.798 Hz | Stationary |

The closed-loop DNp01-cut trial and fixed-body cut trials receive different post-action visual input, so their live errors do not isolate cut position alone. Use fixed-body runs for matched-input comparisons. The detector can respond to object appearance as well as subsequent expansion; these trials do not establish loom-specific biological selectivity.

Every gated DNp01 sample remained zero. Confidence is unavailable. The event is a sustained decrease in reconstructed model firing rate relative to baseline, with an explicitly engineered direction mapping.

The four-trial saved command log reproduced neural rates, the final world state and the final trial result exactly. Total verification wall time, including replay: 96.0 s. This is a functional acceptance run, not a throughput benchmark.

Artifacts: `decoder.json`, `calibration_samples.npz`, `trial_acceptance.json`, `trial_recording.json`.

## Anatomical scope

The whole-CNS overview uses 142,757 measured soma/to-soma locations from 176,422 neuPrint Neuron records (including incomplete/untyped records). 33,665 locations are unavailable. Real public SWC skeletons were retrieved for all 365 simulated neurons. Whole-CNS anatomy is not whole-CNS simulation.

[Source and CC-BY attribution](https://male-cns.janelia.org/download/).
