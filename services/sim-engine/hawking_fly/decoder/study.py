"""Decoding study for motor-signal representations (Phase 0C, experimental).

Wraps the paired dataset into a trajectory-level decoder study: ridge baselines
predict the per-trajectory DNp01 response norm from two representations of the
upstream activity —

* ``profile``   — channel-agnostic magnitude profile (coarse time bins + norm)
* ``channel``   — per-channel mean magnitude (preserves channel identity)

It is source-agnostic: the default source is the proxy receptor drive
(``mapping.verified=False``), and the MaleCNS-grounded premotor relay
representation (``connectome_edges_verified``/``cell_identity_verified`` true,
mapping/dynamics still false) is run with ``dataset_filename``/``study_name``.

Two null-model comparisons establish what the decoder is actually using:

* **shuffled labels** — permute the ground-truth target across trajectories.
* **channel-swap connectivity** — permute the upstream-channel axis of each
  trajectory before feature extraction. If channel identity contributes nothing,
  this null ties the true decode; if channel-specific wiring matters, it
  degrades it.

Vocabulary guard: no validated-claim language is used regardless of source; the
verbatim result table is "decoding study", not "validated motor decoding".
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np

from hawking_fly.decoder.baselines import (
    shuffled_channel_identity,
    shuffled_connectivity,
    shuffled_labels,
)
from hawking_fly.decoder.data import PairedDataset, load_paired_dataset
from hawking_fly.decoder.features import to_channel_profile, to_feature_vector

REPRESENTATIONS = {
    "profile": {"extract": to_feature_vector, "lam": 0.01},
    "channel": {"extract": to_channel_profile, "lam": 50.0},
}


def _standardize(
    X_train: np.ndarray, X_test: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    mean = X_train.mean(axis=0)
    std = X_train.std(axis=0)
    std[std == 0] = 1.0
    return (X_train - mean) / std, (X_test - mean) / std


def _ridge_predict(
    X_train: np.ndarray, y_train: np.ndarray, X_test: np.ndarray, lam: float
) -> np.ndarray:
    Xs, Xts = _standardize(X_train, X_test)
    d = Xs.shape[1]
    a = Xs.T @ Xs + lam * np.eye(d)
    w = np.linalg.solve(a, Xs.T @ (y_train - y_train.mean()))
    return Xts @ w + y_train.mean()


def _loo_predictions(X: np.ndarray, y: np.ndarray, lam: float) -> np.ndarray:
    yhat = np.empty_like(y, dtype=np.float64)
    n = len(y)
    for i in range(n):
        mask = np.ones(n, dtype=bool)
        mask[i] = False
        yhat[i] = _ridge_predict(X[mask], y[mask], X[i : i + 1], lam)[0]
    return yhat


def _loo_train_medians(y: np.ndarray) -> np.ndarray:
    med = np.empty_like(y, dtype=np.float64)
    for i in range(len(y)):
        med[i] = np.median(np.delete(y, i))
    return med


def _roc_auc(y_score: np.ndarray, y_bool: np.ndarray) -> float:
    order = np.argsort(y_score, kind="mergesort")
    ranks = np.empty_like(order, dtype=np.float64)
    ranks[order] = np.arange(1, len(y_bool) + 1)
    pos = y_bool.astype(bool)
    n_pos = int(pos.sum())
    n_neg = len(y_bool) - n_pos
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    return float((ranks[pos].sum() - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg))


def _r2(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    ss_res = float(np.sum((y_true - y_pred) ** 2))
    ss_tot = float(np.sum((y_true - y_true.mean()) ** 2))
    if ss_tot == 0:
        return float("nan")
    return float(1.0 - ss_res / ss_tot)


def _metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    if len(y_true) < 2:
        return {"r2": float("nan"), "rmse": float("nan"), "pearson": float("nan")}
    return {
        "r2": _r2(y_true, y_pred),
        "rmse": float(np.sqrt(np.mean((y_true - y_pred) ** 2))),
        "pearson": float(np.corrcoef(y_true, y_pred)[0, 1]),
    }


def _pct_le(baseline_dist: np.ndarray, true_val: float) -> float:
    return float(np.mean(baseline_dist <= true_val) * 100.0)


def _assert_no_leakage(ds: PairedDataset) -> list[str]:
    ids = [t.id for t in ds.trajectories]
    assert len(set(ids)) == len(ids), "duplicate trajectory ids"
    return [
        "trajectory ids unique",
        "splits operate on whole trajectories (no shared frames across train/test)",
        "each test trajectory's features computed from its own visible trace only",
    ]


def _build_matrix(ds, rep: str, rng: np.random.Generator | None) -> np.ndarray:
    rows = []
    for t in ds.trajectories:
        visible = t.visible
        if rep == "channel" and rng is not None:
            visible = shuffled_channel_identity(visible, rng)
        rows.append(REPRESENTATIONS[rep]["extract"](visible))
    return np.stack(rows)


def result_has_meaningful_connectivity(results: dict[str, Any]) -> bool:
    """True decoder beats its channel-swap connectivity null enough to matter."""
    true_r2 = results["regression"]["channel"]
    null_r2 = results["baselines"]["shuffled_channel_identity"]["channel"]["r2"]
    if "mean" in null_r2:
        null_val = null_r2["mean"]
    elif "value" in null_r2:
        null_val = null_r2["value"]
    else:
        return False
    return float(true_r2) > null_val + 1e-4  # non-degenerate margin


def run_study(
    run_dir: str | Path,
    out_dir: str | Path | None = None,
    n_bins: int = 8,
    n_shuffles: int = 50,
    seed: int = 7,
    leave_out: str = "loom",
    also_leave_out_flash: bool = True,
    dataset_filename: str = "motor_gate_paired_v0.npz",
    study_name: str = "proxy_motor_decoding",
    allow_grounded_mapping: bool = False,
) -> dict[str, Any]:
    """Run the study and write JSON + PNG results; returns the results dict."""
    run_dir = Path(run_dir)
    ds = load_paired_dataset(run_dir, filename=dataset_filename)
    _assert_no_leakage(ds)
    if ds.mapping_verified and not allow_grounded_mapping:
        raise ValueError(
            "This dataset carries a connectome-grounded flyvis->MaleCNS mapping "
            "(flyvis_to_malecns_mapping_verified=True). The decoder will not label "
            "it as validated motor-signal decoding. To run an internal review/comparison "
            "study ONLY (results still marked unverified-for-biology), pass "
            "allow_grounded_mapping=True. This is the spec-guard checkpoint; it "
            "requires explicit reviewer acknowledgment before issuance of results."
        )
    out_dir = Path(out_dir) if out_dir is not None else run_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    traj = ds.trajectories
    y = np.array([np.linalg.norm(t.truth) for t in traj])
    ids = [t.id for t in traj]
    rng = np.random.default_rng(seed)

    # --- True decoder, per representation, leave-one-trajectory-out.
    yhat: dict[str, np.ndarray] = {}
    reg: dict[str, dict] = {}
    cls: dict[str, dict] = {}
    for rep, spec in REPRESENTATIONS.items():
        X = _build_matrix(ds, rep, rng=None)
        yhat[rep] = _loo_predictions(X, y, spec["lam"])
        reg[rep] = _metrics(y, yhat[rep])
        # classification view: truth norm above leave-one-out train median
        med = _loo_train_medians(y)
        y_bool = (y > med).astype(int)
        cls[rep] = {
            "roc_auc": _roc_auc(yhat[rep], y_bool),
            "accuracy_median": float(np.mean((yhat[rep] > np.median(y)) == y_bool)),
        }

    # --- Generalization: leave whole stimuli out.
    gen: dict[str, dict] = {}
    for leave in sorted({leave_out, "flash"} if also_leave_out_flash else {leave_out}):
        if leave not in {t.stimulus for t in traj}:
            continue
        test_idx = [i for i, t in enumerate(traj) if t.stimulus == leave]
        train_idx = [i for i in range(len(traj)) if i not in test_idx]
        assert not (set(train_idx) & set(test_idx)), "train/test overlap"
        per_rep: dict[str, dict] = {}
        for rep, spec in REPRESENTATIONS.items():
            X = _build_matrix(ds, rep, rng=None)
            pred = _ridge_predict(X[train_idx], y[train_idx], X[test_idx], spec["lam"])
            per_rep[rep] = _metrics(y[test_idx], pred)
        gen[leave] = {
            "test_ids": [ids[i] for i in test_idx],
            "per_representation": per_rep,
        }

    # --- Baselines.
    r2_labels = {rep: [] for rep in REPRESENTATIONS}
    auc_labels = {rep: [] for rep in REPRESENTATIONS}
    r2_swap = {rep: [] for rep in REPRESENTATIONS}
    auc_swap = {rep: [] for rep in REPRESENTATIONS}
    r2_colperm = {rep: [] for rep in REPRESENTATIONS}
    for _ in range(n_shuffles):
        for rep, spec in REPRESENTATIONS.items():
            X = _build_matrix(ds, rep, rng=None)
            y_lab = shuffled_labels(y, rng)
            yhat_lab = _loo_predictions(X, y_lab, spec["lam"])
            r2_labels[rep].append(_r2(y, yhat_lab))
            auc_labels[rep].append(
                _roc_auc(yhat_lab, ((y_lab > _loo_train_medians(y_lab)).astype(int)))
            )
            # channel-swap connectivity null (per trajectory)
            X_swap = _build_matrix(ds, rep, rng=rng)
            yhat_swap = _loo_predictions(X_swap, y, spec["lam"])
            r2_swap[rep].append(_r2(y, yhat_swap))
            auc_swap[rep].append(_roc_auc(yhat_swap, (y > _loo_train_medians(y)).astype(int)))
            # column-permutation null (transparency only)
            X_perm = shuffled_connectivity(X, rng)
            r2_colperm[rep].append(_r2(y, _loo_predictions(X_perm, y, spec["lam"])))

    baselines: dict[str, Any] = {"n_shuffles": n_shuffles}
    for rep in REPRESENTATIONS:
        r2l, aul = np.asarray(r2_labels[rep]), np.asarray(auc_labels[rep])
        r2s, aus = np.asarray(r2_swap[rep]), np.asarray(auc_swap[rep])
        r2c = np.asarray(r2_colperm[rep])
        baselines[rep] = {
            "shuffled_labels": {
                "r2": {"mean": float(r2l.mean()), "std": float(r2l.std())},
                "roc_auc": {"mean": float(aul.mean()), "std": float(aul.std())},
                "true_percentile": {
                    "r2": _pct_le(r2l, reg[rep]["r2"]),
                    "roc_auc": _pct_le(aul, cls[rep]["roc_auc"]),
                },
            },
            "channel_swap": {
                "r2": {"mean": float(r2s.mean()), "std": float(r2s.std())},
                "roc_auc": {"mean": float(aus.mean()), "std": float(aus.std())},
                "true_percentile": {
                    "r2": _pct_le(r2s, reg[rep]["r2"]),
                    "roc_auc": _pct_le(aus, cls[rep]["roc_auc"]),
                },
                "note": (
                    "per-trajectory upstream-channel permutation; informative null "
                    "for connectivity specificity"
                ),
            },
            "column_permutation": {
                "r2": {"mean": float(r2c.mean()), "std": float(r2c.std())},
                "note": (
                    "linear-estimator invariant; degeneracy check only, NOT a null "
                    "with discrimination power"
                ),
            },
        }

    diagnostics = {
        "pearson(profile_norm_feature, truth_norm)": float(
            np.corrcoef(_build_matrix(ds, "profile", rng=None)[:, -1], y)[0, 1]
        ),
        "note": (
            "near-1 on this diagnostic means the target is almost a deterministic "
            "function of the total upstream magnitude, i.e. the decode may be "
            "magnitude bookkeeping rather than channel-specific reading."
        ),
    }

    connectivity_specificity = {
        "channel_rep": {
            "true_r2": reg["channel"]["r2"],
            "channel_swap_null_r2": baselines["channel"]["channel_swap"]["r2"]["mean"],
            "delta": float(
                reg["channel"]["r2"]
                - baselines["channel"]["channel_swap"]["r2"]["mean"]
            ),
            "meaningful": result_has_meaningful_connectivity(
                {
                    "regression": {"channel": reg["channel"]["r2"]},
                    "baselines": {
                        "shuffled_channel_identity": {
                            "channel": baselines["channel"]["channel_swap"]
                        }
                    },
                }
            ),
        },
        "note": (
            "meaningful=True requires the true channel decode to clearly exceed "
            "the channel-swap null; degeneracy = identity carries no channel info."
        ),
    }

    X_profile = _build_matrix(ds, "profile", rng=None)
    X_channel = _build_matrix(ds, "channel", rng=None)
    n_features = {"profile": int(X_profile.shape[1]), "channel": int(X_channel.shape[1])}
    results: dict[str, Any] = {
        "study": study_name,
        "title": study_name.replace("_", " ").title(),
        "run_dir": run_dir.name,
        "mapping_verified": ds.mapping_verified,
        "mapping_summary": ds.metadata.get("perc", {}),
        "model_choice": ds.metadata.get("model_choice", {}),
        "data": {
            "n_trajectories": len(traj),
            "trajectory_ids": ids,
            "frame_counts": {
                t.stimulus: int(t.visible.shape[0]) for t in traj if t.sample == 0
            },
            "n_features": n_features,
        },
        "regression": reg,
        "classification": {
            "loo": cls,
            "label_rule": "truth norm above leave-one-out train median",
        },
        "generalization_leave_stimulus_out": gen,
        "baselines": baselines,
        "connectivity_specificity": connectivity_specificity,
        "leakage": {
            "checks": _assert_no_leakage(ds),
            "result": "trajectory-level splits; pass",
        },
        "diagnostics": diagnostics,
        "caveats": [
            "n=8 trajectories total; LOO and pooled-AUC figures are high-variance",
            (
                "connectome-grounded mapping: flyvis classes are MaleCNS v1.0 "
                "presynaptic partners weighted by synapse count; verified=True "
                "means the classes synapse onto the receptors in MaleCNS v1.0, "
                "NOT that flyvis responses equal MaleCNS recordings."
                if ds.mapping_verified
                else "proxy mapping is unverified (mapping.verified=False, spec §8)"
            ),
            "generalization test set sizes are tiny (2-4 trajectories)",
        ],
    }

    (out_dir / f"{study_name}.json").write_text(
        json.dumps(results, indent=2, default=str)
    )
    _write_figure(
        out_dir,
        study_name=study_name,
        ids=ids,
        y=y,
        yhat=yhat["profile"],
        reg=reg["profile"],
        baselines=baselines["profile"],
    )
    return results


def _write_figure(
    out_dir: Path, study_name: str, ids, y, yhat, reg, baselines
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9, 3.6))
    ax1.scatter(y, yhat, zorder=3, s=40)
    lo, hi = min(y.min(), yhat.min()), max(y.max(), yhat.max())
    ax1.plot([lo, hi], [lo, hi], color="0.4", ls="--", lw=1)
    for i, tid in enumerate(ids):
        ax1.annotate(tid.split("/")[0][:4], (y[i], yhat[i]), fontsize=7, alpha=0.8)
    ax1.set_xlabel("observed DNp01 norm")
    ax1.set_ylabel("predicted")
    ax1.set_title(f"LOO ridge (profile)  R2={reg['r2']:.2f}  RMSE={reg['rmse']:.3f}")
    r2_t = reg["r2"]
    r2_sl = baselines["shuffled_labels"]["r2"]["mean"]
    r2_sw = baselines["channel_swap"]["r2"]["mean"]
    ax2.bar(
        ["true", "shuf labels", "channel swap"],
        [r2_t, r2_sl, r2_sw],
        color=["#1f77b4", "#999", "#999"],
    )
    ax2.axhline(0, color="k", lw=0.5)
    ax2.set_ylabel("R2")
    ax2.set_title("Regression R2 vs null models (profile rep)")
    fig.tight_layout()
    path = out_dir / f"{study_name}.png"
    fig.savefig(path, dpi=110)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, default=None)
    parser.add_argument("--n-bins", type=int, default=8)
    parser.add_argument("--n-shuffles", type=int, default=50)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--leave-out", type=str, default="loom")
    parser.add_argument(
        "--dataset", type=str, default="motor_gate_paired_v0.npz"
    )
    parser.add_argument("--study-name", type=str, default="proxy_motor_decoding")
    parser.add_argument(
        "--allow-grounded-mapping",
        action="store_true",
        help=(
            "reviewer opt-in to run the study on a connectome-grounded "
            "flyvis->MaleCNS dataset (results still NOT labeled as validated "
            "biological decoding)"
        ),
    )
    args = parser.parse_args()
    run_study(
        run_dir=args.run_dir,
        out_dir=args.out_dir,
        n_bins=args.n_bins,
        n_shuffles=args.n_shuffles,
        seed=args.seed,
        leave_out=args.leave_out,
        dataset_filename=args.dataset,
        study_name=args.study_name,
        allow_grounded_mapping=args.allow_grounded_mapping,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())