# FlyLab legacy cleanup

Removed the separate Hawking Fly wheelchair/motor-gate application: its frontend
screens, state store, presentation models, backend live/replay routes, simulation
modules, legacy-only tests, notebooks and design documents.

Retained FlyLab's coding controllers, physical fly and chair, room, keyboard,
Chromium workspace, MaleCNS viewer, training/recording APIs and connectome helpers.
The shared fly body and anatomy renderer now live in `web/app/src/features/coding/`.
Anatomy preparation now uses the coding graph instead of the retired motor-gate graph.

All 9,719 pre-existing files under `data/` and `experiments/` were checked for
unchanged size and modification time after cleanup. Historical scientific data
is retained alongside FlyLab's recordings and checkpoints. The internal Python
namespace `hawking_fly` is retained for compatibility; it no longer exposes the
retired application's routes.

Validation: frontend build/lint, 10 retained frontend tests, 40 backend tests,
and a browser check of FlyLab's desk, fly, live full-CNS view and typing session.
Docker configuration points to FlyLab; a container build was not run.

Recovery copy (outside the project):
/Users/sudharsan/.codex/backups/FlyLab-legacy-cleanup-20260919-181905

`removed-files.json` lists removed paths; shared-file originals are also saved.
