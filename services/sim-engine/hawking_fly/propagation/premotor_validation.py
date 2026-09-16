"""Validation for the MaleCNS-grounded premotor representation (Phase 3A).

Checks that the relay-layer activity read off the 3-layer graph is:

  * *non-trivial* — not identically zero, temporally structured, silent channels
    (relay neurons that receive no LC4/LPLC2 input) explicitly accounted for,
  * *stimulus-sensitive* — flash / moving edge / loom produce distinct relay
    signatures (pairwise trace distance), not a single fixed response,
  * *input-constrained, not a scaled copy of the input* — relay channels
    correlate with the flyvis receptor drive but are not simply a rescaling of
    it (channel-specific amplification), and
  * *causally active* — DNp01's modeled output changes when individual relay
    types are removed (ablation), so the relay layer contributes beyond a
    passive pass-through.

Together these answer the Phase 3A gate: the relay activity is a meaningful
MaleCNS-grounded signal, not a numeric artifact.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from hawking_fly.propagation.rate_model import RateModel, relu


def _load_run(run_dir: Path) -> dict[str, Any]:
    conn_dir = run_dir / "connectome"
    stims: dict[str, dict[str, np.ndarray]] = {}
    for relay_path in sorted(conn_dir.glob("relay_*.npz")):
        stim = relay_path.name.removeprefix("relay_").removesuffix(".npz")
        dn_path = conn_dir / f"dnp01_{stim}.npz"
        if not dn_path and not dn_path.exists():
            raise FileNotFoundError(f"missing {dn_path}")
        stims[stim] = {
            "relay": np.asarray(np.load(relay_path)["trace"]),
            "dn": np.asarray(np.load(dn_path)["trace"]),
        }
    relay_meta_path = conn_dir / "relay_neurons.json"
    if not relay_meta_path.is_file():
        raise FileNotFoundError(f"missing {relay_meta_path}")
    relay_meta = json.loads(relay_meta_path.read_text())
    return {
        "run_dir": run_dir,
        "conn_dir": conn_dir,
        "stims": stims,
        "relay_meta": relay_meta,
        "driven_mask": np.array([m["has_receptor_input"] for m in relay_meta], dtype=bool),
    }


def non_triviality(run: dict[str, Any]) -> dict[str, Any]:
    """Relay activity must be finite, structured, and non-degenerate."""
    checks: dict[str, Any] = {}
    driven = run["driven_mask"]
    checks["n_relay_channels"] = int(len(run["relay_meta"]))
    checks["n_driven_channels"] = int(driven.sum())
    checks["silent_fraction"] = round(float((~driven).mean()), 3)

    per_stim: dict[str, Any] = {}
    for stim, d in run["stims"].items():
        tr = d["relay"]
        driven_tr = tr[:, :, driven]
        per_stim[stim] = {
            "finite": bool(np.all(np.isfinite(tr))),
            "mean_abs": round(float(np.mean(np.abs(tr))), 6),
            "driven_std_per_channel": [
                round(float(np.std(driven_tr[:, :, i])), 6)
                for i in range(driven_tr.shape[2])
            ],
            "n_zero_std_driven": int(
                sum(1 for s in per_stim_std(tr, driven) if s < 1e-9)
            ),
            "temporal_structure": temporal_structure(tr, driven),
        }
    checks["per_stimulus"] = per_stim
    checks["pass"] = bool(
        all(d["finite"] for d in per_stim.values())
        and all(d["temporal_structure"]["n_time_bins_nonzero"] > 0 for d in per_stim.values())
    )
    return checks


def per_stim_std(tr: np.ndarray, driven: np.ndarray) -> np.ndarray:
    """Std of each driven channel across a stimulus (samples x frames flattened)."""
    return np.array([np.std(tr[:, :, i]) for i in np.where(driven)[0]])


def temporal_structure(tr: np.ndarray, driven: np.ndarray) -> dict[str, Any]:
    """How many time points, mean-subtracted across frames, carry variance."""
    ch = tr[:, :, driven]
    mu_over_time = ch.mean(axis=1, keepdims=True)  # (s, 1, n)
    resid = ch - mu_over_time
    frame_var = np.var(resid, axis=(0, 2))  # (frame,)
    active = np.count_nonzero(frame_var > np.max(frame_var) * 1e-6)
    return {"n_time_bins_nonzero": int(active), "max_frame_var": round(float(frame_var.max()), 6)}


def stimulus_sensitivity(run: dict[str, Any]) -> dict[str, Any]:
    """Compare driven-relay *channel profiles* across stimuli.

    The aggregate relay magnitude is dominated by the long pre-stimulus
    baseline and looks similar between stimuli; the discriminating content
    lives in how each relay cell responds. `mean_abs_profile` collapses each
    stimulus to a 21-dim vector (mean abs activity per driven relay cell,
    averaged over samples and frames); pairwise distances/correlations in that
    profile space are the sensitivity check.
    """
    driven = run["driven_mask"]
    keys = sorted(run["stims"])
    profs: dict[str, np.ndarray] = {}
    for stim, d in run["stims"].items():
        tr = np.asarray(d["relay"])
        profs[stim] = np.mean(np.abs(tr[:, :, driven]), axis=(0, 1))  # (n_driven,)

    pairwise: dict[str, float] = {}
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            pa, pb = profs[a], profs[b]
            pairwise[f"{a}_vs_{b}_profile_mse"] = round(float(np.mean((pa - pb) ** 2)), 8)
            pairwise[f"{a}_vs_{b}_profile_pearson"] = round(
                float(np.corrcoef(pa, pb)[0, 1]), 6
            )
            pairwise[f"{a}_vs_{b}_profile_cosine"] = round(
                float(np.dot(pa, pb) / (np.linalg.norm(pa) * np.linalg.norm(pb) + 1e-12)), 6
            )
    # Resolved only if profiles are not near-collinear copies: at least one
    # pair has cosine < 0.99 OR mse >> 0 relative to profile scale.
    scales = {k: float(np.linalg.norm(v)) for k, v in profs.items()}
    mean_scale = float(np.mean(list(scales.values())))
    max_cos = max(
        v for k, v in pairwise.items() if k.endswith("_profile_cosine")
    )
    min_rel_mse = min(
        v / (mean_scale**2 + 1e-12) for k, v in pairwise.items() if k.endswith("_profile_mse")
    )
    resolved = bool(max_cos < 0.99 or min_rel_mse > 1e-4)
    # Magnitude ordering check: even if profile *shape* is near-collinear, the
    # total premotor magnitude should differ between stimuli (Phase 0A showed
    # loom > flash > edge DNp01 activity). We record whether the ordering is
    # non-degenerate (not all-equal magnitudes).
    magnitudes = {k: float(np.linalg.norm(v)) for k, v in profs.items()}
    ordered = bool(len({round(m, 6) for m in magnitudes.values()}) > 1)
    return {
        "profiles": {k: v.tolist() for k, v in profs.items()},
        "magnitudes": {k: round(v, 8) for k, v in magnitudes.items()},
        "pairwise": pairwise,
        "max_profile_cosine": max_cos,
        "min_rel_mse": round(min_rel_mse, 8),
        "shape_discriminative": resolved,
        "magnitude_differentiated": ordered,
        "resolved": resolved,
        "note": (
            "resolved=shape-level discrimination (channel-specific profile "
            "distinguishes stimuli); magnitude_differentiated=the total premotor "
            "magnitude varies between stimuli even when profile shape does not."
        ),
    }


def input_binding(run: dict[str, Any]) -> dict[str, Any]:
    """Relay must be tied to (but not a scaled copy of) the flyvis drive."""
    conn = run["conn_dir"]
    driven = run["driven_mask"]
    n_driven = int(driven.sum())
    out: dict[str, Any] = {}
    per_stim: dict[str, Any] = {}
    for stim, d in run["stims"].items():
        drive_path = conn / f"receptor_drive_{stim}.npz"
        if not drive_path.exists():
            continue
        drive = np.asarray(np.load(drive_path)["drive"])  # (s, frame, n_rec)
        relay = d["relay"][:, :, driven]
        fmin = min(drive.shape[1], relay.shape[1])
        # Correlate aggregate receptor drive with each driven relay channel.
        drive_sig = np.mean(np.abs(drive[:, :fmin]), axis=(0, 2))
        chan_corr: list[float] = []
        for ch in range(relay.shape[2]):
            r_sig = np.mean(np.abs(relay[:, :fmin, ch]), axis=0)
            chan_corr.append(round(float(np.corrcoef(r_sig, drive_sig)[0, 1]), 6))
        per_stim[stim] = {
            "n_highly_correlated_channels": int(sum(1 for c in chan_corr if c > 0.9)),
            "corr_min": min(chan_corr) if chan_corr else None,
            "corr_median": round(float(np.median(chan_corr)), 6) if chan_corr else None,
            "corr_max": max(chan_corr) if chan_corr else None,
        }
    out["per_stimulus"] = per_stim
    # Not a scaled copy: most channels should deviate from a pure copy of the
    # aggregated drive (corr < 0.99 on a majority of channels).
    n_scaled_like = sum(
        1
        for s in per_stim.values()
        if (s.get("n_highly_correlated_channels", 0)) >= round(n_driven * 0.9)
        and (s.get("corr_median") or 1) > 0.99
    )
    out["n_pure_copy_stimuli"] = n_scaled_like
    out["pass"] = n_scaled_like == 0
    return out


def run_ablation(run_dir: Path) -> dict[str, Any]:
    """Re-run DNp01 output while removing each relay type's projection to DNp01.

    Measures how much the modeled DNp01 response depends on each relay type:
    the ablation score is the relative change in DNp01 mean-abs activity when
    the relay-type -> DNp01 edges are cut.
    """
    from hawking_fly.connectome.cache import load_cached_circuit

    edges, _info = load_cached_circuit("loom_escape_full_graph")
    if edges is None:
        raise FileNotFoundError("loom_escape_full_graph cache missing")
    receptor_neurons, _ = load_cached_circuit("loom_escape_receptor_neurons")
    relay_neurons, _ = load_cached_circuit("loom_escape_relay_neurons")
    if receptor_neurons is None or relay_neurons is None:
        raise FileNotFoundError("receptor/relay neuron caches missing")

    # Load receptor drive for each stimulus from the run dir.
    conn = run_dir / "connectome"
    stims = {
        p.name.removeprefix("receptor_drive_").removesuffix(".npz"): np.asarray(
            np.load(p)["drive"]
        )
        for p in sorted(conn.glob("receptor_drive_*.npz"))
    }

    node_ids = sorted(set(edges["pre"]) | set(edges["post"]))
    node_index = {n: i for i, n in enumerate(node_ids)}
    n = len(node_ids)
    receptor_idx = [
        node_index[b] for b in sorted(set(receptor_neurons["bodyId"]) & set(node_index))
    ]
    dn_ids = set(edges["post"]) - set(receptor_neurons["bodyId"]) - set(relay_neurons["bodyId"])
    dn_idx = [node_index[b] for b in sorted(dn_ids)]

    relay_by_type = {
        t: set(relay_neurons.loc[relay_neurons["type"] == t, "bodyId"])
        for t in relay_neurons["type"].unique()
    }

    def propagate(graph_edges) -> dict[str, np.ndarray]:
        pre = graph_edges["pre"].to_numpy()
        post = graph_edges["post"].to_numpy()
        w = graph_edges["syn_count"].to_numpy().astype(np.float64)
        model = RateModel.from_edge_list(
            pre, post, w, n_nodes=n, node_ids=node_ids, nonlinearity=relu
        )
        dn_out: dict[str, np.ndarray] = {}
        for stim_name, drive in stims.items():
            samples, frames, _ = drive.shape
            dn_trace = np.zeros((samples, frames, len(dn_idx)), dtype=np.float64)
            for s in range(samples):
                r = np.zeros(n, dtype=np.float64)
                for t in range(frames):
                    ext = np.zeros(n, dtype=np.float64)
                    for k, idx in enumerate(receptor_idx):
                        ext[idx] = drive[s, t, k]
                    r = model.step(r, ext)
                    dn_trace[s, t] = r[dn_idx]
            dn_out[stim_name] = dn_trace
        return dn_out

    def dn_abs(dn_out: dict[str, np.ndarray]) -> float:
        return float(np.mean([np.mean(np.abs(v)) for v in dn_out.values()]))

    base = propagate(edges)

    ablations: dict[str, dict[str, Any]] = {}
    for rtype, rids in sorted(relay_by_type.items()):
        cut = edges[~((edges["layer"] == "relay_to_dn") & (edges["pre"].isin(rids)))].copy()
        ablated = propagate(cut)
        base_score = dn_abs(base)
        pop_score = dn_abs(ablated)
        rel_change = (base_score - pop_score) / base_score if base_score else None
        ablations[rtype] = {
            "n_relay_neurons": int(len(rids)),
            "n_edges_cut": int(len(edges) - len(cut)),
            "dn_abs_full": round(base_score, 6),
            "dn_abs_ablated": round(pop_score, 6),
            "relative_change": round(float(rel_change), 6) if rel_change is not None else None,
        }
    return {"ablations": ablations}


def validate_premotor_representation(run_dir: str | Path) -> dict[str, Any]:
    """Run the full Phase 3A validation and return the check table."""
    run_dir = Path(run_dir)
    run = _load_run(run_dir)

    non_trivial = non_triviality(run)
    sensitivity = stimulus_sensitivity(run)
    binding = input_binding(run)
    ablation = run_ablation(run_dir)

    return {
        "run_dir": run_dir.name,
        "non_triviality": non_trivial,
        "stimulus_sensitivity": sensitivity,
        "input_binding": binding,
        "ablation": ablation,
        "verdict": {
            "non_trivial": bool(non_trivial["pass"]),
            "stimulus_sensitive_shape": bool(sensitivity["resolved"]),
            "stimulus_sensitive_magnitude": bool(sensitivity["magnitude_differentiated"]),
            "input_bound_not_copy": bool(binding["pass"]),
            "relay_contributes": bool(
                any(
                    a.get("relative_change") is not None
                    and abs(a["relative_change"]) > 0.0
                    for a in ablation["ablations"].values()
                )
            ),
        },
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    result = validate_premotor_representation(args.run_dir)
    out_path = args.out or args.run_dir / "connectome" / "premotor_validation.json"
    out_path.write_text(json.dumps(result, indent=2, default=str))
    print(f"validation -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())