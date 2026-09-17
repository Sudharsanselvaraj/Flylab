"""Phase 0B preparation — materialize the paired motor-gate dataset.

Scope (user-approved): build the paired dataset ONLY. The intent decoder is a
later step (Phase 0C, `hawking_fly/decoder/`) and is deliberately NOT
implemented here.

Pairing definition
------------------
Both halves are read from the *same* integration run directory, so the pairing
is exact per sample and per frame:

    VISIBLE      = upstream proxy receptor drive, (n_samples, frame, n_receptors)
                   connectome/receptor_drive_<stim>.npz  ("drive")
    GROUND TRUTH = DNp01 resulting activity,     (n_samples, frame, n_DNp01)
                   connectome/dnp01_<stim>.npz           ("trace")

Both are outputs of the MaleCNS connectome leg and therefore inherit its labels
(mapping `correspondence="proxy"`, `verified=False`, model_choice relu/saturating
— recorded in connectome/mapping.json and connectome/dnp01_metrics.json). The
manifest below repeats those labels so a future decoder can never misread the
pairing as validated biophysics (spec §8).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

CONNECTOME_DIR = "connectome"
PAIRED_NPZ = "motor_gate_paired_v0.npz"
PAIRED_MANIFEST = "manifest.json"


def _load_connectome_leg(run_dir: Path) -> dict[str, dict[str, np.ndarray]]:
    """Read the connectome leg artifacts into {stim: {visible, truth}}."""
    conn_dir = run_dir / CONNECTOME_DIR
    if not conn_dir.is_dir():
        raise FileNotFoundError(
            f"connectome leg missing in {run_dir} — re-run with sim.with_connectome"
        )
    paired: dict[str, dict[str, np.ndarray]] = {}
    for drive_path in sorted(conn_dir.glob("receptor_drive_*.npz")):
        stim = drive_path.name.removeprefix("receptor_drive_").removesuffix(".npz")
        trace_path = conn_dir / f"dnp01_{stim}.npz"
        if not trace_path.exists():
            raise FileNotFoundError(f"missing dnp01_{stim}.npz alongside {drive_path.name}")
        paired[stim] = {
            "visible": np.asarray(np.load(drive_path)["drive"]).astype(np.float32),
            "truth": np.asarray(np.load(trace_path)["trace"]).astype(np.float32),
        }
    if not paired:
        raise FileNotFoundError(f"no connectome stimuli found in {conn_dir}")
    return paired


def _manifest(run_dir: Path, paired: dict[str, dict[str, np.ndarray]]) -> dict[str, Any]:
    conn_mapping = json.loads((run_dir / CONNECTOME_DIR / "mapping.json").read_text())
    run_metrics = json.loads((run_dir / "metrics.json").read_text())
    model_choice = (
        run_metrics.get("connectome_provenance", {}).get("model_choice", {})
        or {"note": "see connectome/dnp01_metrics.json and run metrics.json"}
    )
    return {
        "definition": {
            "visible": "upstream proxy receptor drive (aggregate_drive, per sample)",
            "ground_truth": "DNp01 activity from the MaleCNS rate-model leg",
            "alignment": "same integration run, matched per sample and frame",
        },
        "perc": {
            "label": "documented proxy, NOT a verified cell-type correspondence",
            "source": "connectome/mapping.py FLYVIS_RECEPTOR_PROXY",
            "verified": False,
        },
        "model_choice": model_choice,
        "stimuli": {
            stim: {
                "visible_shape": list(v["visible"].shape),
                "truth_shape": list(v["truth"].shape),
                "n_samples": int(v["visible"].shape[0]),
            }
            for stim, v in paired.items()
        },
        "provenance": {
            "run_dir": run_dir.name,
            "mapping_created": conn_mapping.get("created"),
            "built": datetime.now(timezone.utc).isoformat(),
        },
    }


def build_paired_dataset(run_dir: str | Path, out_dir: str | Path | None = None) -> Path:
    """Materialize the paired npz + manifest into ``out_dir`` (default: run_dir)."""
    run_dir = Path(run_dir)
    out_dir = Path(out_dir) if out_dir is not None else run_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    paired = _load_connectome_leg(run_dir)

    npz_path = out_dir / PAIRED_NPZ
    arrays: dict[str, np.ndarray] = {}
    for stim, v in paired.items():
        arrays[f"visible_{stim}"] = v["visible"]
        arrays[f"truth_{stim}"] = v["truth"]
    # Duplicate stimuli would silently overwrite below; only flash/moving_edge/loom expected.
    if len(arrays) != 2 * len(paired):
        raise ValueError("stimulus name collision while writing paired arrays")
    np.savez(npz_path, **arrays)

    manifest_path = out_dir / PAIRED_MANIFEST
    manifest_path.write_text(json.dumps(_manifest(run_dir, paired), indent=2, default=str))

    assert npz_path.is_file() and manifest_path.is_file()
    return npz_path


PAIRED_VERIFIED_NPZ = "motor_gate_verified_v0.npz"
PAIRED_VERIFIED_TYPE_AGG_NPZ = "motor_gate_verified_v0_type_agg.npz"


def build_verified_premotor_dataset(
    run_dir: str | Path,
    out_dir: str | Path | None = None,
    *,
    include_silent_relay: bool = False,
    type_aggregated: bool = False,
) -> Path:
    """Materialize the MaleCNS-grounded premotor paired dataset.

    VISIBLE = relay-neuron activity read off the full 3-layer graph, per-cell
    (n_driven relay channels) or per-type (aggregate of driven relay cells).

    GROUND TRUTH = DNp01 activity, unchanged.

    Provenance is carried per the scientific naming decision: MaleCNS
    connectivity and cell identity are verified from the live connectome, but
    the flyvis -> MaleCNS input mapping and the rate-model dynamics remain
    unverified (proxy / custom dynamics).
    """
    run_dir = Path(run_dir)
    out_dir = Path(out_dir) if out_dir is not None else run_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    conn_dir = run_dir / CONNECTOME_DIR

    if not conn_dir.is_dir():
        raise FileNotFoundError(f"connectome leg missing in {run_dir}")
    relay_meta_path = conn_dir / "relay_neurons.json"
    if not relay_meta_path.is_file():
        raise FileNotFoundError(
            f"relay_neurons.json missing in {conn_dir} — run premotor propagation"
        )
    relay_meta = json.loads(relay_meta_path.read_text())
    driven_mask = np.array([m["has_receptor_input"] for m in relay_meta], dtype=bool)
    channel_mask = np.ones(len(relay_meta), dtype=bool) if include_silent_relay else driven_mask
    type_index: dict[str, int] = {}
    for i, m in enumerate(relay_meta):
        if channel_mask[i]:
            t = m["type"]
            type_index.setdefault(t, len(type_index))
    n_types = len(type_index)

    paired: dict[str, dict[str, np.ndarray]] = {}
    for relay_path in sorted(conn_dir.glob("relay_*.npz")):
        stim = relay_path.name.removeprefix("relay_").removesuffix(".npz")
        trace_path = conn_dir / f"dnp01_{stim}.npz"
        if not trace_path.exists():
            raise FileNotFoundError(f"missing dnp01_{stim}.npz alongside {relay_path.name}")
        relay = np.asarray(np.load(relay_path)["trace"]).astype(np.float32)
        dn = np.asarray(np.load(trace_path)["trace"]).astype(np.float32)
        if not np.any(channel_mask):
            raise ValueError("no relay channels selected for VISIBLE")
        if type_aggregated:
            samples, frames, _ = relay.shape
            visible = np.zeros((samples, frames, n_types), dtype=np.float32)
            for j, m in enumerate(relay_meta):
                if channel_mask[j]:
                    visible[:, :, type_index[m["type"]]] += relay[:, :, j]
        else:
            visible = relay[:, :, channel_mask]
        paired[stim] = {"visible": visible, "truth": dn}

    npz_path = out_dir / (PAIRED_VERIFIED_TYPE_AGG_NPZ if type_aggregated else PAIRED_VERIFIED_NPZ)
    arrays: dict[str, np.ndarray] = {}
    for stim, v in paired.items():
        arrays[f"visible_{stim}"] = v["visible"]
        arrays[f"truth_{stim}"] = v["truth"]
    np.savez(npz_path, **arrays)

    inner_channels = list(type_index) if type_aggregated else [
        m["type"] for i, m in enumerate(relay_meta) if channel_mask[i]
    ]
    mapping_file = conn_dir / "mapping.json"
    mapping_summary = (
        json.loads(mapping_file.read_text()).get("summary", {})
        if mapping_file.is_file()
        else {}
    )
    n_grounded = int(mapping_summary.get("n_connectome_grounded", 0))
    n_receptors = int(mapping_summary.get("n_receptors", 0))
    mapping_grounded = n_grounded == n_receptors and n_receptors > 0
    mapping_note = (
        "flyvis->MaleCNS drive = MaleCNS v1.0-typed presynaptic partners "
        "weighted by synapse count (connectome-grounded). verified=True means "
        "the classes synapse onto the receptor in MaleCNS v1.0, NOT that flyvis "
        "responses equal MaleCNS recordings."
        if mapping_grounded
        else (
            "legacy proxy or partially-unmapped flyvis drive; see "
            "connectome/mapping.json."
        )
    )
    manifest = {
        "definition": {
            "visible": (
                "MaleCNS-grounded premotor relay activity (individual relay "
                "neurons read off the full LC4/LPLC2 -> relay -> DNp01 graph)"
                if not type_aggregated
                else "MaleCNS-grounded premotor relay activity (type-aggregated)"
            ),
            "ground_truth": "DNp01 activity from the MaleCNS rate-model leg",
            "alignment": "same integration run, matched per sample and frame",
        },
        "perc": {
            "label": "MaleCNS-grounded premotor representation",
            "connectome_edges_verified": True,
            "cell_identity_verified": True,
            "flyvis_to_malecns_mapping_verified": mapping_grounded,
            "mapping_verification_note": mapping_note,
            "dynamics_validated": False,
            "channel_source": "relay_neurons.json (bodyId) + relay_<stim>.npz (trace)",
            "n_relay_channels": int(np.sum(channel_mask)),
            "n_silent_excluded": int(np.sum(~channel_mask)),
            "n_type_channels": n_types,
            "channels": inner_channels,
        },
        "stimuli": {
            stim: {
                "visible_shape": list(v["visible"].shape),
                "truth_shape": list(v["truth"].shape),
                "n_samples": int(v["visible"].shape[0]),
            }
            for stim, v in paired.items()
        },
        "provenance": {
            "run_dir": run_dir.name,
            "built": datetime.now(timezone.utc).isoformat(),
            "graph": "loom_escape_full_graph (3-layer, MaleCNS v1.0)",
        },
    }
    if type_aggregated:
        manifest_path = out_dir / "manifest_type_agg.json"
    else:
        manifest_path = out_dir / PAIRED_MANIFEST
    manifest_path.write_text(json.dumps(manifest, indent=2, default=str))

    assert npz_path.is_file() and manifest_path.is_file()
    return npz_path


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, default=None)
    parser.add_argument(
        "--verified",
        action="store_true",
        help=(
            "build the MaleCNS-grounded premotor pairing (relay neurons -> DNp01) "
            "instead of the legacy receptor-drive proxy pairing"
        ),
    )
    parser.add_argument(
        "--type-agg",
        action="store_true",
        help="with --verified, emit the type-aggregated representation (implies --verified)",
    )
    args = parser.parse_args()

    if args.verified or args.type_agg:
        out = build_verified_premotor_dataset(
            args.run_dir, args.out_dir, type_aggregated=bool(args.type_agg)
        )
        kind = "type-aggregated" if args.type_agg else "per-neuron"
        print(f"verified premotor pairing ({kind}) -> {out}")
    else:
        out = build_paired_dataset(args.run_dir, args.out_dir)
        print(f"paired dataset -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())