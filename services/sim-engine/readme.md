# FlyLab simulation service

Physical keyboard interaction, Chromium workspace, modeled MaleCNS dynamics,
real anatomy, training, recording and replay. See the root README and
`docs/physical-coding.md` for setup and model limitations.

```sh
python3.11 -m venv .venv
.venv/bin/pip install -e "services/sim-engine[dev]"
.venv/bin/python -m playwright install chromium
PYTHONPATH=services/sim-engine .venv/bin/python -m hawking_fly.api.app
```

The internal `hawking_fly` package name remains for compatibility with existing
scripts, environments and recorded provenance. It now serves only FlyLab routes.
Cached anatomy, connectome data, trained checkpoints and saved sessions are preserved.
