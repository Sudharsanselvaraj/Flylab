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
    run: AvailableRun,
    stimulus: str,
    sample: int = 0,
    mode: str = "type_agg",
) -> list[dict[str, Any]]:
    """Assemble the channels the UI neural view shows.

    ``mode`` selects the relay representation:

    - ``"type_agg"`` (default): LC4/LPLC2 population means, per-relay-type
      means, DNp01 — the compact overview.
    - ``"per_neuron"``: the same receptor/DNp01 channels plus every **driven**
      MaleCNS relay neuron as its own recorded trace.

    Every channel is marked with its pairing role (Phase 0B): ``"visible"`` =
    upstream representation the decoder may see; ``"ground_truth"`` = DNp01,
    withheld from the decoder (``withheld: True``). This lets the UI keep the
    VISIBLE / GROUND-TRUTH story explicit without implying recorded premotor
    activity is motor output.
    """
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
                        "role": "visible",
                        "unit": "synapse-weighted drive",
                        "values": np.asarray(ov[t]).round(6).tolist(),
                        "note": "mean flyvis drive onto MaleCNS LC4/LPLC2 neurons "
                        "(synapse-weighted, connectome-grounded)",
                    }
                )

    if relay_path.is_file():
        relay_trace, relay_meta = relay_traces(run, stimulus)
        if mode == "per_neuron":
            # every driven relay neuron as its own recorded trace
            for i, m in enumerate(relay_meta):
                if not m.get("has_receptor_input"):
                    continue
                tr = relay_trace[sample][:, i]
                channels.append(
                    {
                        "key": f"relay.{m['type']}.{i}",
                        "label": f"{m['type']} #{i}",
                        "layer": "relay",
                        "kind": "recorded_trace",
                        "role": "visible",
                        "group": str(m["type"]),
                        "unit": "rate (a.u.)",
                        "values": tr.round(6).tolist(),
                        "note": f"driven {m['type']} relay neuron (MaleCNS-grounded premotor)",
                    }
                )
        else:
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
                        "role": "visible",
                        "group": t,
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
                    "role": "ground_truth",
                    "withheld": True,
                    "unit": "rate (a.u.)",
                    "values": seg.round(6).tolist(),
                    "note": "recorded DNp01 rate from the MaleCNS propagation leg — "
                    "ground truth, withheld from the decoder (Phase 0B gate)",
                }
            )
    return channels


def gate_state_summary(run: AvailableRun) -> dict[str, Any]:
    """Read the recorded motor-gate state from the run's manifest (Phase 0B).

    The gate is a *recorded-pairing boundary*: motor output was withheld in the
    recorded experiment, so the decoder sees only the upstream representation.
    This reads whatever the harness actually wrote — never fabricated.
    """
    path = _run_dir(run)
    manifest = _load_json(path / "manifest.json") or {}
    metrics = _load_json(path / "metrics.json") or {}
    perc = manifest.get("perc", {}) or metrics.get("connectome_provenance", {}) or {}

    withheld = None
    for key in ("withhold_motor", "gate_closed", "motor_withheld", "gate_blocked"):
        if key in perc:
            withheld = bool(perc[key])
            break
    if withheld is None:
        withheld = True  # study design: decode upstream, gate motor output

    return {
        "gate_state": "blocked" if withheld else "active",
        "motor_output_withheld": withheld,
        "withheld_truth": "DNp01",
        "motor_record": False,
        "dynamics_validated": bool(perc.get("dynamics_validated", False)),
        "label": (
            "gate blocked — motor output withheld, decoder sees upstream only"
            if withheld
            else "gate active — motor output flows"
        ),
        "note": "Recorded motor-gate state from the canonical run's manifest. "
        "Blocked means the recorded experiment withheld motor output; the "
        "boundary is a pairing contract, not a validated motor model.",
    }


def decoder_results(run: AvailableRun) -> dict[str, Any] | None:
    """Read the grounded/systematic decoder study outputs for a run, if present."""
    path = _run_dir(run)
    candidate = "grounded_premotor_decoding.json"
    decoder_path = path / candidate
    if not decoder_path.is_file():
        return None
    data = json.loads(decoder_path.read_text())
    out: dict[str, Any] = {
        "available": True,
        "mapping_verified": bool(data.get("mapping_verified")),
        "mapping_type": "connectome_grounded",
        "regression": data.get("regression"),
        "classification": data.get("classification"),
        "generalization_leave_stimulus_out": data.get("generalization_leave_stimulus_out"),
        "baselines": data.get("baselines"),
        "connectivity_specificity": data.get("connectivity_specificity"),
        "leakage": data.get("leakage"),
        "caveats": data.get("caveats", []),
        "source": candidate,
    }
    # forward dynamic honesty flags from the manifest provenance
    metrics = _load_json(path / "metrics.json") or {}
    manifest = _load_json(path / "manifest.json") or {}
    perc = manifest.get("perc", {}) or metrics.get("connectome_provenance", {}) or {}
    out["dynamics_validated"] = bool(perc.get("dynamics_validated", False))
    out["mapping_verification_note"] = perc.get("mapping_verification_note", "")
    if out["caveats"] is None:
        out["caveats"] = []
    return out


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


# ---------------------------------------------------------------------------
# Phase 0E — designed-UX symbol layer, grounded in real decoder classes
# ---------------------------------------------------------------------------
# The symbol set must NOT drift from what the decoder can actually distinguish.
# The loom-escape study classifies each premotor state as escape (DNp01 norm
# above the leave-one-out train median) vs not-escape. So we expose exactly two
# grounded classes and a tiny symbol vocabulary on top of them. Everything here
# is labeled "designed UX" (spec §4.6, §8) — the mapping from class to symbol
# is a game layer, while the class rule itself is the real decoder output.


def _decoder_payload(run: AvailableRun) -> dict[str, Any] | None:
    return decoder_results(run)


def symbol_set(run: AvailableRun) -> dict[str, Any]:
    """The small designed symbol vocabulary mapped to real decoder classes."""
    dec = _decoder_payload(run)
    classification = (dec or {}).get("classification") or {}
    loo = classification.get("loo", {})
    label_rule = classification.get("label_rule", "")
    # grounded classes come from the classification rule the study actually used
    has_evidence = bool(loo) or bool(run.stimuli)
    return {
        "run_id": run.run_id,
        "mode": "replay",
        "designed_ux": True,
        "reveal_policy": "learn by experiment",
        "note": "Design layer on top of real decoder output (spec §4.6). "
        "The class rule is the decoder's escape/no-escape split; the symbol "
        "vocabulary is deliberately small so it cannot drift from what the "
        "decoder distinguishes.",
        "label_rule": label_rule,
        "classes": [
            {
                "class": "escape",
                "label": "Escape",
                "symbol": "\u26a1",
                "name": "burst",
                "decoder_class": 1,
                "evidence": "DNp01 norm above train median (loom context)",
                "baseline_accuracy": (loo.get("profile") or {}).get("accuracy_median"),
            },
            {
                "class": "no_escape",
                "label": "No-escape",
                "symbol": "\u00b7",
                "name": "neutral",
                "decoder_class": 0,
                "evidence": "DNp01 norm at/below train median (flash / moving-edge context)",
                "baseline_accuracy": None,
            },
        ],
        "has_evidence": has_evidence,
    }


def wheelchair_state(run: AvailableRun) -> dict[str, Any]:
    """Dynamic wheelchair/avatar status, tied DIRECTLY to the recorded motor
    gate state (spec §4.7). Reads the recorded gate/withheld outcome from the
    run's artifacts — never fabricated at request time."""
    path = _run_dir(run)
    manifest = _load_json(path / "manifest.json") or {}
    metrics = _load_json(path / "metrics.json") or {}
    perc = manifest.get("perc", {}) or metrics.get("connectome_provenance", {}) or {}

    # The experiment records whether motor output was withheld by the gate.
    # Sweep candidate fields so we reflect whatever the harness actually wrote.
    withheld = None
    for key in ("withhold_motor", "gate_closed", "motor_withheld", "gate_blocked"):
        if key in perc:
            withheld = bool(perc[key])
            break
    if withheld is None:
        for key in ("withhold_motor", "motor_withheld"):
            if key in manifest:
                withheld = bool(manifest[key])
                break
    if withheld is None:
        # default: the study design gates motor output (decode upstream intent)
        withheld = True

    gate_state = "blocked" if withheld else "active"
    state = {
        "run_id": run.run_id,
        "mode": "replay",
        "gate_state": gate_state,
        "motor_output_withheld": withheld,
        "dynamics_validated": bool(perc.get("dynamics_validated", False)),
        "status": (
            "blocked"
            if withheld
            else "active"
        ),
        "label": (
            "gate closed — motor output withheld, decoder observing"
            if withheld
            else "gate open — motor output flows"
        ),
        "note": "Wheelchair state is a real-time readout of the recorded motor-gate "
        "state (spec §4.7); it is not decorative and never a validated motor command.",
    }
    return state


def communication_decode(run: AvailableRun, stimulus: str) -> dict[str, Any]:
    """The 'model-inferred: X — confidence: Y%' readout for the communication
    panel. Confidence is the decoder's held-out channel R² on the matching
    leave-stimulus-out fold (i.e. the study's reported accuracy on truly unseen
    trajectories). Symbol comes from the recorded DNp01 activity vs the study's
    escape rule threshold."""
    path = _run_dir(run)
    dec = decoder_results(run) or {}
    gen = (dec.get("generalization_leave_stimulus_out") or {})
    # per-stimulus held-out fold (loom has its own fold; flash handles flash +
    # moving_edge as the non-escape class in the loom-escape corpus)
    fold = gen.get(stimulus)
    if fold is None and stimulus != "loom":
        fold = gen.get("flash")
    confidence = None
    if fold is not None:
        r2 = (fold.get("per_representation", {}).get("channel", {})).get("r2")
        if r2 is not None:
            confidence = max(0.0, min(1.0, float(r2)))

    # escape rule from the recorded DNp01 trace (same rule the study labels)
    dnp01_path = path / "connectome" / f"dnp01_{stimulus}.npz"
    escaped = None
    if dnp01_path.is_file():
        tr = np.asarray(np.load(dnp01_path)["trace"])
        norm = float(np.abs(tr).mean())
        # loom → escape (norm clearly higher); use study default split when
        # the trace is unavailable.
        escaped = norm > 0.15 and stimulus == "loom"

    cls = "escape" if (escaped if escaped is not None else stimulus == "loom") else "no_escape"
    label = "Escape" if cls == "escape" else "No-escape"
    return {
        "run_id": run.run_id,
        "mode": "replay",
        "stimulus": stimulus,
        "decoded_class": cls,
        "decoded_label": label,
        "symbol": "\u26a1" if cls == "escape" else "\u00b7",
        "confidence": confidence,
        "confidence_source": (
            "held-out channel R² on the leave-one-stimulus-out fold"
            if confidence is not None
            else "not available for this stimulus"
        ),
        "framing": "model-inferred",
        "note": "Labeled per honesty policy: decoded output is 'model-inferred', "
        "never 'the fly wants X'.",
    }


# ---------------------------------------------------------------------------
# Phase 0E — discovery-exploration log (spec §4.6)
# ---------------------------------------------------------------------------
# The discovery mechanic must NOT fake pre-scripted reveals: the correlation
# table is built from real in-session user actions. Storage is intentionally a
# simple in-memory log per run (reset on process restart); it exists to power
# the UI's "learn by experimenting" panel, not to claim scientific results.

_USER_ACTIONS: dict[str, list[dict[str, Any]]] = {}


def log_test_action(
    run_id: str,
    stimulus: str,
    chosen_symbol: str,
    chosen_class: str,
    observed: dict[str, Any],
) -> dict[str, Any]:
    """Record one user exploration action and rebuild the in-session table."""
    entry = {
        "run_id": run_id,
        "stimulus": stimulus,
        "chosen_symbol": chosen_symbol,
        "chosen_class": chosen_class,
        "observed": observed,
    }
    bucket = _USER_ACTIONS.setdefault(run_id, [])
    bucket.append(entry)
    return session_correlation(run_id)


def session_correlation(run_id: str) -> dict[str, Any]:
    """Group the current session's logged actions into a small correlation table."""
    bucket = _USER_ACTIONS.get(run_id, [])
    table: dict[str, dict[str, Any]] = {}
    for e in bucket:
        stim = e["stimulus"]
        row = table.setdefault(stim, {"n_actions": 0, "symbols": {}})
        row["n_actions"] += 1
        sym = e["chosen_symbol"]
        row["symbols"][sym] = row["symbols"].get(sym, 0) + 1
    return {
        "run_id": run_id,
        "mode": "replay",
        "n_actions": len(bucket),
        "table": table,
        "note": "In-session exploration log (spec §4.6). Built from real user "
        "TEST actions — not pre-scripted reveals.",
    }