"""Replay API — serve recorded experiment artifacts (Phase 0D).

Phase 0D is replay-based: the heavy flyvis inference and MaleCNS propagation
happen offline in reproducible run directories under ``experiments/<name>/<run>``.
This module reads those artifacts and serves them over HTTP without re-running
any model, so the scientific claims never change at request time.

Everything returned here is **recorded data** (``mode="replay"``). There is no
fake streaming: a "stream" endpoint re-emits recorded per-frame values at the
run's real timestep.

Layer labels follow the honesty policy (see ``assemble_provenance``) so the UI
can never label a proxy or custom layer as verified biology by accident.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[4]
EXPERIMENTS_ROOT = REPO_ROOT / "experiments"

RELAY_TYPES_EXPECTED = ("PVLP010", "PVLP151", "SAD064", "SAD073", "PVLP122")
DATASET_VERSION = "MaleCNS v1.0"


class RunNotFoundError(KeyError):
    """Requested experiment run directory does not exist."""


@dataclass(frozen=True)
class AvailableRun:
    run_id: str
    path: Path
    experiment: str
    stimuli: tuple[str, ...]
    has_decoder: bool
    has_premotor: bool


def _is_run_dir(path: Path) -> bool:
    return (path / "config.json").is_file() and (path / "metrics.json").is_file()


def list_runs(experiment: str = "loom_escape") -> list[AvailableRun]:
    """Return recorded runs for ``experiment``, newest first."""
    root = EXPERIMENTS_ROOT / experiment
    if not root.is_dir():
        return []
    runs: list[AvailableRun] = []
    for path in sorted(root.iterdir(), reverse=True):
        if not path.is_dir() or not _is_run_dir(path):
            continue
        run_id = path.name
        cfg: dict[str, Any] = json.loads((path / "config.json").read_text())
        stimuli = tuple(s["name"] for s in cfg.get("stimuli", []))
        has_premotor = (path / "motor_gate_verified_v0.npz").is_file()
        has_decoder = any(
            p.suffix == ".json" and p.stem.startswith(("grounded", "proxy"))
            for p in path.glob("*.json")
        )
        runs.append(
            AvailableRun(
                run_id=run_id,
                path=path,
                experiment=experiment,
                stimuli=stimuli,
                has_decoder=has_decoder,
                has_premotor=has_premotor,
            )
        )
    return runs


def latest_premotor_run(experiment: str = "loom_escape") -> AvailableRun | None:
    for r in list_runs(experiment):
        if r.has_premotor:
            return r
    return None


def resolve_run(run_id: str, experiment: str = "loom_escape") -> AvailableRun:
    for r in list_runs(experiment):
        if r.run_id == run_id:
            return r
    # allow full dir names like "experiments/loom_escape/20260916-223510"
    raise RunNotFoundError(run_id)


def _run_dir(run: AvailableRun) -> Path:
    return run.path


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text())


def run_metadata(run: AvailableRun) -> dict[str, Any]:
    path = _run_dir(run)
    cfg = _load_json(path / "config.json") or {}
    metrics = _load_json(path / "metrics.json") or {}
    manifest = _load_json(path / "manifest.json")
    mapping = _load_json(path / "connectome" / "mapping.json")
    conn_metrics = _load_json(path / "connectome" / "dnp01_metrics.json")
    return {
        "run_id": run.run_id,
        "experiment": run.experiment,
        "mode": "replay",
        "dataset_version": DATASET_VERSION,
        "stimuli": list(run.stimuli),
        "config": cfg,
        "metrics": {
            "phase0a": metrics.get("signature_norms"),
            "dnp01": conn_metrics,
            "relay_phase3a": _relay_phase3a(metrics),
        },
        "manifest": manifest,
        "mapping": mapping,
    }


def _relay_phase3a(metrics: dict[str, Any]) -> dict[str, Any] | None:
    return metrics.get("relay_phase3a")


def receptor_overview_trace(
    drive: np.ndarray, mapping_records: list[dict[str, Any]]
) -> dict[str, Any]:
    """Split the per-receptor drive for one sample (frames, n_receptors) into
    LC4 / LPLC2 population means following the mapping's per-bodyId types."""
    if drive.ndim != 2:
        raise ValueError(f"expected (frames, receptors), got {drive.shape}")
    if len(mapping_records) != drive.shape[1]:
        mapping_records = mapping_records[: drive.shape[1]]
    types = np.array([r["receptor_type"] for r in mapping_records])
    out: dict[str, Any] = {}
    for t in ("LC4", "LPLC2"):
        idx = np.where(types == t)[0]
        out[t] = drive[:, idx].mean(axis=-1) if len(idx) else None
    out["n_receptors"] = int(len(mapping_records))
    out["per_type"] = {
        t: int((types == t).sum()) for t in ("LC4", "LPLC2")
    }
    return out


def relay_traces(run: AvailableRun, stimulus: str) -> tuple[np.ndarray, list[dict[str, Any]]]:
    """Return (trace, neuron_meta) for a stimulus: relay_<stim>.npz."""
    path = _run_dir(run)
    npz_path = path / "connectome" / f"relay_{stimulus}.npz"
    meta_path = path / "connectome" / "relay_neurons.json"
    if not npz_path.is_file() or not meta_path.is_file():
        raise FileNotFoundError(f"relay artifact missing for {stimulus} in {run.run_id}")
    data = np.load(npz_path)
    trace = np.asarray(data["trace"], dtype=np.float64)
    meta = json.loads(meta_path.read_text())
    return trace, meta


def overview_channels(
    run: AvailableRun, stimulus: str, sample: int = 0
) -> list[dict[str, Any]]:
    """Assemble the small set of named overview channels the UI timelns chart
    shows: LC4, LPLC2, per-relay-type means, DNp01."""
    path = _run_dir(run)
    drive: np.ndarray | None = None
    if (path / "connectome" / f"receptor_drive_{stimulus}.npz").is_file():
        drive = np.asarray(np.load(path / "connectome" / f"receptor_drive_{stimulus}.npz")["drive"])
    mapping = _load_json(path / "connectome" / "mapping.json") or {}
    mapping_records = mapping.get("receptor_drive_mapping", [])
    dnp01_path = path / "connectome" / f"dnp01_{stimulus}.npz"
    relay_path = path / "connectome" / f"relay_{stimulus}.npz"

    channels: list[dict[str, Any]] = []

    if drive is not None and mapping_records:
        ov = receptor_overview_trace(drive[sample], mapping_records)
        for t in ("LC4", "LPLC2"):
            if ov[t] is not None:
                channels.append(
                    {
                        "key": t,
                        "label": t,
                        "layer": "receptor",
                        "kind": "recorded_drive",
                        "unit": "synapse-weighted drive",
                        "values": np.asarray(ov[t]).round(6).tolist(),
                        "note": "mean flyvis drive onto MaleCNS LC4/LPLC2 neurons "
                        "(synapse-weighted, connectome-grounded)",
                    }
                )

    if relay_path.is_file():
        relay_trace, relay_meta = relay_traces(run, stimulus)
        # type-aggregate driven relay neurons by their MaleCNS type
        by_type: dict[str, list[int]] = {}
        for i, m in enumerate(relay_meta):
            if not m.get("has_receptor_input"):
                continue
            by_type.setdefault(m["type"], []).append(i)
        for t, idx in by_type.items():
            tr = relay_trace[sample][:, idx].mean(axis=-1)
            channels.append(
                {
                    "key": f"relay.{t}",
                    "label": t,
                    "layer": "relay",
                    "kind": "recorded_trace",
                    "unit": "rate (a.u.)",
                    "values": tr.round(6).tolist(),
                    "note": f"mean over driven {t} relay neurons (MaleCNS-grounded premotor)",
                    "n_neurons": int(len(idx)),
                }
            )

    if dnp01_path.is_file():
        dnp01 = np.asarray(np.load(dnp01_path)["trace"])
        for i in range(dnp01.shape[2]):
            seg = dnp01[sample, :, i]
            channels.append(
                {
                    "key": f"DNp01.{i}",
                    "label": f"DNp01 ({'R' if i == 0 else 'L'})",
                    "layer": "dnp01",
                    "kind": "recorded_trace",
                    "unit": "rate (a.u.)",
                    "values": seg.round(6).tolist(),
                    "note": "recorded DNp01 rate from the MaleCNS propagation leg",
                }
            )
    return channels


def decoder_results(run: AvailableRun) -> dict[str, Any] | None:
    if not run.has_decoder:
        return None
    found: dict[str, Any] | None = None
    for p in sorted(_run_dir(run).glob("*_decoding.json")) + sorted(
        _run_dir(run).glob("*decoding*.json")
    ):
        found = _load_json(p)
        if found:
            return found
    return None


def assemble_provenance(run: AvailableRun) -> dict[str, Any]:
    """The 'What is real?' panel payload (spec §8, §11)."""
    cfg = _load_json(_run_dir(run) / "config.json") or {}
    manifest = _load_json(_run_dir(run) / "manifest.json") or {}
    metrics = _load_json(_run_dir(run) / "metrics.json") or {}
    perc = manifest.get("perc", {})
    conn_prov = metrics.get("connectome_provenance", {})
    mapping_summary = conn_prov.get("mapping_summary", {})
    mode = conn_prov.get("mapping_mode", "unknown")

    layers = [
        {
            "layer": "MaleCNS connectivity",
            "status": "REAL DATA",
            "detail": "LC4/LPLC2 -> relay -> DNp01 edges and synapse counts pulled "
            "from the live MaleCNS v1.0 connectome (cached parquet).",
            "verified": bool(perc.get("connectome_edges_verified", False)),
        },
        {
            "layer": "FlyVis visual model",
            "status": "PRETRAINED MODEL",
            "detail": "Lappalainen et al. 2024 optic-lobe model, pretrained "
            "connectome-constrained weights (flow/0000/000).",
            "verified": bool(cfg.get("sim", {}).get("use_pretrained", True)),
        },
        {
            "layer": "Downstream dynamics",
            "status": "CUSTOM MODEL",
            "detail": "connectivity-informed leaky rate model over the MaleCNS "
            "graph; not biophysically validated.",
            "verified": bool(perc.get("dynamics_validated", False)),
        },
        {
            "layer": "Decoder output",
            "status": "MODEL-INFERRED" if run.has_decoder else "UNAVAILABLE",
            "detail": "ridge LOO decoder on recorded premotor traces; result is "
            "model-inferred, never reported as intent.",
            "verified": False,
        },
        {
            "layer": "Wheelchair / avatar",
            "status": "PRESENTATION",
            "detail": "designed visual layer; no scientific content.",
            "verified": False,
        },
    ]

    return {
        "run_id": run.run_id,
        "dataset": DATASET_VERSION,
        "flags": {
            "connectome_edges_verified": bool(perc.get("connectome_edges_verified")),
            "cell_identity_verified": bool(perc.get("cell_identity_verified")),
            "flyvis_to_malecns_mapping_verified": bool(
                perc.get("flyvis_to_malecns_mapping_verified")
            ),
            "dynamics_validated": bool(perc.get("dynamics_validated", False)),
        },
        "mapping": {
            "mode": mode,
            "summary": mapping_summary,
            "note": perc.get("mapping_verification_note", ""),
        },
        "layers": layers,
        "model_choice": (conn_prov.get("model_choice") or {}),
        "decoder": {
            "available": run.has_decoder,
            "mapping_verified": bool(manifest.get("perc", {}).get("verified")),
        },
    }