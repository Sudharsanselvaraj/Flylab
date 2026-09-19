# Contributing to FlyLab

Thank you for improving FlyLab. This repository mixes research evidence, simulation code, a React application, and large reproducible artifacts. Small, well-scoped pull requests are easiest to review and reproduce.

## Before you begin

Open an issue for changes that alter the benchmark, neural model, data pipeline, or public claims. State the question, the proposed change, and the evidence you will add. Please do not treat UI polish as evidence of a new scientific result.

For local setup, follow the [README](README.md). The `hawking_fly` Python module name remains for compatibility; new public-facing copy should call the project **FlyLab**.

## Development workflow

1. Create a branch from `main`.
2. Keep code, documentation, tests, and generated evidence in separate commits when they answer different review questions.
3. Run the relevant checks:

   ```sh
   PYTHONPATH=services/sim-engine .venv/bin/python -m pytest services/sim-engine/tests -q
   npm --prefix web/app run build
   npm --prefix web/app run lint
   npm --prefix web/app exec vitest run
   ```

4. In the pull request, describe the behavior change, validation performed, and any effect on checkpoints, saved evidence, runtime, or data requirements.

## Evidence and data rules

- Keep source, browser input, screenshots, motor contacts, clock ticks, and neural events traceable in a session artifact.
- Label real anatomy/connectivity, engineered dynamics, trained models, and UI presentation separately. Do not generate activity, spikes, morphology, or biological claims for visual effect.
- Do not commit credentials, neuPrint tokens, private datasets, or large generated video/session archives. The repository ignores local caches and lossless spike archives for this reason.
- If a run changes a reported metric, include the command, checkpoint/data hashes, hardware context when relevant, and the failed cases as well as passes.
- Preserve historical artifacts unless an issue explains why replacement is necessary. Do not rewrite evidence to make a result look cleaner.

## Code conventions

- TypeScript uses the existing compact formatting and runs through `oxlint`.
- Python modules should keep data access explicit and fail rather than fabricate unavailable records.
- Tests should test externally visible behavior or a material scientific invariant. Avoid tests that only restate implementation details.

## Pull requests

Use the pull-request template. A maintainer may request that broad changes be split into implementation, evidence, and documentation pull requests so each can be reviewed independently.

By contributing, you agree to follow the [Code of Conduct](CODE_OF_CONDUCT.md).
