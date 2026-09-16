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


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, default=None)
    args = parser.parse_args()
    out = build_paired_dataset(args.run_dir, args.out_dir)
    print(f"paired dataset -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())