"""Phase 0A validation — flyvis forward inference on synthetic stimuli.

Phase 0A ("propagation validation, no gate, no decoder") establishes that
the pipeline produces *sane* activity before any decodability claims:

  1. **Finite, distinguishable traces** — each stimulus gives a finite,
     non-degenerate optic-lobe response (mean|r| ~ 0.7, nonzero pairwise MSE).
  2. **Known responsive read-out cells** — the flyvis cell classes that
     MaleCNS v1.0 shows synapse onto LC4/LPLC2 (the loom-escape receptors)
     should carry measurable drive, with stimulus-ordered magnitudes.

Everything here reads **recorded artifacts** (``*_responses.npz`` from a run,
``connectome/mapping.json`` grounded plan) so validation never re-runs flyvis
inference. The per-column ``cell_type`` labels are recovered from a ~5 s
minimal flash on the pretrained ensemble (neuron ordering is a static
property of the network) and cached next to the output.

No decoder claims are made in Phase 0A; see `docs/phase_0a.md`.

Usage::

    python -m hawking_fly.sensory.validation \\
        --run-dir experiments/loom_escape/20260916-223510 \\
        --out experiments/loom_escape/phase_0a_validation
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np

STIMULI = ("flash", "moving_edge", "loom")


def recover_cell_type_labels() -> list[str]:
    """Return the 65 per-column cell-type labels of the pretrained ensemble.

    Runs one minimal flash through the pretrained flyvis network (~5 s) purely
    to recover the static per-neuron cell_type coordinate that flyvis attaches
    to every response dataset. The neuron ordering is a fixed property of the
    network, so the labels align with any stored response npz from the same
    ensemble.
    """
    from hawking_fly.sensory import FlyVisWrapper

    wrapper = FlyVisWrapper()
    resp = wrapper.responses(
        "flash", t_pre=0.2, t_stim=0.2, dt=0.005, alternations=(0, 1, 0)
    )
    labels = np.asarray(resp["cell_type"].values)
    if labels.ndim != 1 or len(labels) == 0:
        raise RuntimeError("flyvis response dataset has no cell_type coordinate")
    return [str(x) for x in labels]


def _load_run_responses(run_dir: Path) -> dict[str, np.ndarray]:
    """Load recorded ``*_responses.npz`` arrays for all three stimuli."""
    out: dict[str, np.ndarray] = {}
    for name in STIMULI:
        path = run_dir / f"{name}_responses.npz"
        if not path.is_file():
            raise FileNotFoundError(f"missing {path}")
        with np.load(path) as z:
            out[name] = np.asarray(z["responses"])
    return out


def _load_readout_plan(mapping_path: Path) -> dict[str, Any]:
    """Aggregate the grounded LC4/LPLC2 flyvis classes + synapse weights."""
    if not mapping_path.is_file():
        raise FileNotFoundError(f"missing {mapping_path}")
    mapping = json.loads(mapping_path.read_text())
    rows = mapping.get("receptor_drive_mapping") or []
    class_weight: dict[str, float] = {}
    n_receptors = 0
    for row in rows:
        classes = row.get("flyvis_cell_types") or []
        weights = row.get("flyvis_cell_type_weights") or []
        if not classes:
            continue
        n_receptors += 1
        total = float(sum(weights)) or 1.0
        for cls, w in zip(classes, weights):
            class_weight[cls] = class_weight.get(cls, 0.0) + float(w) * (float(w) / total)
    return {
        "n_receptors": n_receptors,
        "summary_note": mapping.get("summary", {}).get("note", ""),
        "class_weight": class_weight,
    }


def _sanity_metrics(responses: dict[str, np.ndarray]) -> dict[str, Any]:
    """Finite-ness, magnitude, and pairwise distinction of mean traces."""
    metrics: dict[str, Any] = {}
    traces: dict[str, np.ndarray] = {}
    for name, arr in responses.items():
        finite = bool(np.all(np.isfinite(arr)))
        metrics[name] = {
            "finite": finite,
            "shape": list(arr.shape),
            "mean_abs_response": round(float(np.mean(np.abs(arr))), 6),
            "std_response": round(float(np.std(arr)), 6),
            "max_abs_response": round(float(np.max(np.abs(arr))), 6),
        }
        trace = (
            arr[0].mean(axis=(0, -1)) if arr.ndim == 4 else arr.reshape(arr.shape[0], -1).mean(axis=1)
        )
        traces[name] = trace
    pairwise: dict[str, float] = {}
    names = list(traces)
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            ta, tb = traces[a], traces[b]
            ln = min(len(ta), len(tb))
            pairwise[f"{a}_vs_{b}_mse"] = round(float(np.mean((ta[:ln] - tb[:ln]) ** 2)), 8)
    metrics["pairwise_trace_mse"] = pairwise
    return metrics


def _cell_type_norms(
    responses: dict[str, np.ndarray], labels: list[str]
) -> dict[str, dict[str, float]]:
    """Per-cell-type mean-|response| per stimulus, matching column order."""
    n_columns = len(labels)
    per_stimulus: dict[str, dict[str, float]] = {}
    for name, arr in responses.items():
        last_dim = arr.shape[-1]
        if last_dim != n_columns:
            raise ValueError(
                f"{name}: stored responses have {last_dim} neuron columns but "
                f"the ensemble exposes {n_columns} cell types"
            )
        # mean |response| over samples & frames per column
        col = float(np.mean(np.abs(arr)))
        per_type: dict[str, float] = {}
        for t in set(labels):
            idx = [i for i, lab in enumerate(labels) if lab == t]
            per_type[t] = round(float(np.mean(np.abs(arr)[..., idx])), 6)
        per_type["__all_columns__"] = round(col, 6)
        per_stimulus[name] = per_type
    return per_stimulus


def _readout_drive(
    per_stimulus: dict[str, dict[str, float]], plan: dict[str, Any]
) -> dict[str, Any]:
    """Weighted read-out drive of the LC4/LPLC2-correspondent flyvis classes."""
    class_weight = plan["class_weight"]
    total = sum(class_weight.values()) or 1.0
    drive: dict[str, float] = {}
    raw: dict[str, dict[str, float]] = {}
    covered: set[str] = set(class_weight)
    for name, per_type in per_stimulus.items():
        present = covered & set(per_type)
        raw[name] = {t: per_type[t] for t in sorted(present, key=lambda t: -class_weight[t])}
        drive[name] = float(sum(class_weight[t] * per_type[t] for t in present) / total)
    ordered = sorted(drive, key=lambda k: -drive[k])
    return {
        "n_classes": len(covered),
        "classes": sorted(covered),
        "weighted_drive_per_stimulus": {k: round(v, 6) for k, v in drive.items()},
        "drive_ordering": ordered,
        "loom_maximal": bool(drive.get("loom", 0.0) == max(drive.values(), default=0.0)),
        "raw_per_class": raw,
    }


def phase_0a_validation(
    run_dir: Path, out_dir: Path, labels: list[str] | None = None
) -> Path:
    """Run the Phase 0A checks against a recorded run and write artifacts."""
    responses = _load_run_responses(run_dir)
    if labels is None:
        labels = recover_cell_type_labels()

    # sanity: finite, non-degenerate, distinguishable
    metrics = _sanity_metrics(responses)

    # read-out: correlated classes + weighted drive per stimulus
    plan = _load_readout_plan(run_dir / "connectome" / "mapping.json")
    per_type = _cell_type_norms(responses, labels)
    readout = _readout_drive(per_type, plan)

    report: dict[str, Any] = {
        "run_dir": str(run_dir),
        "stage": "Phase 0A — flyvis forward inference on synthetic stimuli",
        "no_decoder_claims": (
            "Phase 0A validates sanity only; nothing here is a decodability claim. "
            "Loom read-out weights come from MaleCNS v1.0 synapse counts "
            "(connectome-grounded plan); flyvis responses do not equal MaleCNS "
            "recordings (dynamics_validated=false)."
        ),
        "cell_type_columns": len(labels),
        "sanity": metrics,
        "readout": readout,
        "limitations": [
            "flyvis models 65 optic-lobe cell types and contains no LC4/LPLC2; "
            "the read-out is the union of flyvis classes that MaleCNS v1.0 shows "
            "synapsing onto LC4/LPLC2 (~60% of non-self input weight; the rest "
            "is non-flyvis and dropped).",
            "per-column cell_type labels are recovered from a fresh minimal run "
            "and aligned to stored responses by static neuron ordering; a network "
            "change invalidates both.",
            "single-eye flyvis activity is applied bilaterally in the MaleCNS leg; "
            "not re-verified in this stage.",
        ],
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "cell_type_labels.json").write_text(
        json.dumps({"cell_types": labels}, indent=2)
    )
    (out_dir / "validation.json").write_text(json.dumps(report, indent=2))

    try:
        _write_plot(per_type, readout, out_dir / "validation.png")
    except Exception:  # pragma: no cover - plot failure must not fail validation
        pass

    return out_dir


def _write_plot(
    per_stimulus: dict[str, dict[str, float]],
    readout: dict[str, Any],
    path: Path,
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    names = list(per_stimulus)
    # left: weighted read-out drive
    drive = readout["weighted_drive_per_stimulus"]
    axes[0].bar(names, [drive[n] for n in names], color="#334155")
    axes[0].set_title("LC4/LPLC2-correspondent read-out, weighted drive")
    axes[0].set_ylabel("weighted mean |response|")
    # right: top 6 classes by synapse weight, per stimulus
    top = sorted(readout["classes"], key=lambda c: -readout["raw_per_class"].get("loom", {}).get(c, 0))[:6]
    xpos = np.arange(len(top))
    width = 0.25
    for i, name in enumerate(names):
        vals = [readout["raw_per_class"].get(name, {}).get(t, 0.0) for t in top]
        axes[1].bar(xpos + (i - 1) * width, vals, width, label=name)
    axes[1].set_xticks(xpos)
    axes[1].set_xticklabels(top, rotation=45, ha="right", fontsize=7)
    axes[1].set_ylabel("mean |response|")
    axes[1].set_title("Top mapped classes (loom-ordered)")
    axes[1].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--labels-from-cache",
        type=Path,
        default=None,
        help="reuse cell_type_labels.json instead of a fresh minimal flash",
    )
    args = parser.parse_args()

    labels: list[str] | None = None
    if args.labels_from_cache and args.labels_from_cache.is_file():
        labels = json.loads(args.labels_from_cache.read_text())["cell_types"]

    out = phase_0a_validation(args.run_dir, args.out, labels=labels)
    if labels is not None:
        (out / "cell_type_labels.json").write_text(
            json.dumps({"cell_types": labels}, indent=2)
        )

    report = json.loads((out / "validation.json").read_text())
    print(json.dumps({"sanity": report["sanity"], "readout": report["readout"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())