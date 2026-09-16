"""Reproducible Phase 0A experiment runner.

Usage:
    python -m hawking_fly.experiments.run [--config experiments/loom_escape/config.json]

Each run writes an output directory containing:
    config.json            the exact config used
    metrics.json           sanity metrics for this run
    stimuli_responses.npz  stimulus+response arrays
    plots/                 response figure(s)
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path
from typing import Any

import numpy as np
import xarray as xr

from hawking_fly.sensory import FlyVisWrapper, ensure_pretrained_ensemble
from hawking_fly.sensory.stimuli import STIMULI

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("hawking_fly.experiments.run")

REPO_ROOT = Path(__file__).resolve().parents[4]  # services/sim-engine/hawking_fly/experiments → repo root
DEFAULT_CONFIG = Path("experiments/loom_escape/config.json")


def _responses_to_npz(resp: xr.Dataset, path: Path) -> dict[str, Any]:
    """Dump a flyvis response Dataset to a compact npz + return summary arrays."""
    path.parent.mkdir(parents=True, exist_ok=True)

    responses = None
    if "responses" in resp:
        responses = np.asarray(resp["responses"].values)
    stimulus = None
    if "stimulus" in resp:
        stimulus = np.asarray(resp["stimulus"].values)

    try:
        import xarray as _xr

        coords: dict[str, Any] = {}
        for name, da in resp.coords.items():
            values = np.asarray(da.values)
            if values.ndim == 0:
                coords[name] = str(values.item()) if values.dtype.kind == "O" else values.item()
            else:
                coords[name] = values
    except Exception:  # pragma: no cover
        coords = {}

    with open(path, "wb") as f:
        np.savez(f, responses=responses, stimulus=stimulus)
    return coords


def _summary_metrics(stimuli_responses: dict[str, tuple[np.ndarray, Any]]) -> dict[str, Any]:
    """Compute Phase 0A sanity metrics — not decodability metrics."""
    metrics: dict[str, Any] = {}
    signatures: dict[str, float] = {}

    baseline_traces: dict[str, np.ndarray] = {}
    for name, (responses, _coords) in stimuli_responses.items():
        if responses is None:
            metrics[name] = {"status": "no_response_data"}
            continue
        finite = bool(np.all(np.isfinite(responses)))
        mean_abs = float(np.mean(np.abs(responses)))
        std = float(np.std(responses))
        metrics[name] = {
            "finite": finite,
            "shape": list(responses.shape),
            "mean_abs_response": round(mean_abs, 6),
            "std_response": round(std, 6),
        }
        # mean activity over time across samples & central neurons -> trace
        # responses shape from flyvis: (network_id, sample, frame, neuron)
        if responses.ndim == 4:
            trace = responses[0].mean(axis=(0, -1))
        else:
            trace = responses.reshape(responses.shape[0], -1).mean(axis=1)
        baseline_traces[name] = trace
        signatures[name] = float(np.linalg.norm(trace))

    # Pairwise dissimilarity of mean-response traces (distinguishable?).
    names = list(baseline_traces)
    pairwise: dict[str, float] = {}
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            ta, tb = baseline_traces[a], baseline_traces[b]
            min_len = min(len(ta), len(tb))
            ta, tb = ta[:min_len], tb[:min_len]
            dist = float(np.mean((ta - tb) ** 2)) if min_len else 0.0
            pairwise[f"{a}_vs_{b}_mse"] = round(dist, 8)
    metrics["pairwise_trace_mse"] = pairwise
    metrics["signature_norms"] = {k: round(v, 6) for k, v in signatures.items()}
    return metrics


def run_experiment(config: dict[str, Any]) -> Path:
    sim = config.get("sim", {})
    stimuli_cfg = config.get("stimuli", [])

    seed = int(config.get("seed", 0))
    np.random.seed(seed)

    out_root = REPO_ROOT / sim.get("output_root", "experiments")
    run_dir = out_root / sim.get("experiment", "run") / time.strftime("%Y%m%d-%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "plots").mkdir(exist_ok=True)

    # Ground truth injected into metrics so the run is self-describing.
    provenance = {
        "seed": seed,
        "experiment": sim.get("experiment"),
        "flyvis_pretrained_used": sim.get("use_pretrained", True),
        "neuprint_circuit_status": "pending_token"
        if sim.get("await_token", False)
        else "not_configured",
        "labels": "flyvis forward responses on synthetic stimuli; no decoder claims.",
    }

    logger.info("Ensuring pretrained flyvis ensemble.")
    ensure_pretrained_ensemble(download=bool(sim.get("download_pretrained", False)))

    wrapper = FlyVisWrapper()
    stimuli_responses: dict[str, Any] = {}
    for s in stimuli_cfg:
        name = s["name"]
        if name not in STIMULI:
            logger.warning("Unknown stimulus %s — skipped.", name)
            continue
        logger.info("Running %s.", name)
        resp = wrapper.responses(name, **s.get("cfg", {}))
        coords = _responses_to_npz(resp, run_dir / f"{name}_responses.npz")
        stimuli_responses[name] = (resp.get("responses"), coords)

    metrics = _summary_metrics(stimuli_responses)
    metrics["provenance"] = provenance

    # 5. Connectome propagation leg (if configured).
    if config.get("with_connectome", False):
        logger.info("Running MaleCNS connectome propagation leg.")
        conn_out = run_connectome_propagation(stimuli_responses, config, run_dir)
        metrics["connectome"] = conn_out.get("dnp01_metrics", {})
        metrics["connectome_provenance"] = {
            "edge_cache": conn_out.get("edge_cache"),
            "mapping_summary": conn_out.get("mapping", {}).get("summary", {}),
        }

    (run_dir / "config.json").write_text(json.dumps(config, indent=2))
    (run_dir / "metrics.json").write_text(json.dumps(metrics, indent=2))

    _write_plots(stimuli_responses, run_dir / "plots")

    logger.info("Run complete -> %s", run_dir)
    return run_dir


def _write_plots(stimuli_responses: dict[str, Any], plot_dir: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 4))
    for name, (responses, _coords) in stimuli_responses.items():
        if responses is None:
            continue
        trace = (
            responses[0].mean(axis=(0, -1)) if responses.ndim == 4 else responses.mean(axis=1)
        )
        ax.plot(trace, label=name)
    ax.set_xlabel("frame")
    ax.set_ylabel("mean response (arb. units)")
    ax.set_title("Phase 0A — mean optic-lobe response per stimulus")
    ax.legend()
    fig.tight_layout()
    fig.savefig(plot_dir / "responses_overview.png", dpi=110)
    plt.close(fig)


def run_connectome_propagation(
    stimuli_responses: dict[str, Any],
    config: dict[str, Any],
    run_dir: Path,
) -> dict[str, Any]:
    """Carry flyvis responses through the MaleCNS circuit to DNp01.

    Called only when config['with_connectome'] is true. Uses the cached direct
    adjacency (LC4/LPLC2 → DNp01) and the explicit proxy receptor mapping
    (connectome/mapping.py, verified=False).
    """
    import numpy as np

    from hawking_fly.connectome.cache import load_cached_circuit
    from hawking_fly.connectome.mapping import (
        build_receptor_drive_plan,
        aggregate_drive,
        mapping_provenance,
        receptor_drive_plan_frame,
    )
    from hawking_fly.connectome.routes import dominant_routes
    from hawking_fly.connectome.client import ConnectomeClient
    from hawking_fly.propagation.rate_model import RateModel

    # 1. Load the cached direct adjacency.
    edges, info = load_cached_circuit("loom_escape_direct_lc4_lplc2_to_dnp01")
    if edges is None:
        raise RuntimeError(
            "direct adjacency cache missing — run build_loom_escape_subgraph first"
        )
    # 2. Load receptor neurons table (cached by routes.py).
    receptor_neurons, _ = load_cached_circuit("loom_escape_receptor_neurons")
    if receptor_neurons is None:
        raise RuntimeError("receptor_neurons cache missing — run run_discovery first")

    # 3. Build the receptor drive plan from flyvis response cell types.
    # Gather all available flyvis cell types from the response dataset.
    sample_resp = next(
        (r for (r, _) in stimuli_responses.values() if r is not None), None
    )
    if sample_resp is None:
        raise RuntimeError("no flyvis responses available")
    import xarray as xr
    cell_types: set[str] = set(
        np.asarray(
            # responses shape: (network_id, sample, frame, neuron); coords on dim 'neuron'
            # cell_type is a (neuron,) coordinate in flyvis >= 0.2.0
            sample_resp.cell_type.values
            if "cell_type" in sample_resp.coords
            else []
        )
    )

    plan = build_receptor_drive_plan(receptor_neurons, available_cell_types=cell_types)
    receptor_ids = [p.body_id for p in plan]
    node_ids = sorted(set(edges["pre"]) | set(edges["post"]))
    node_index = {n: i for i, n in enumerate(node_ids)}
    n = len(node_ids)
    receptor_idx = [node_index[bid] for bid in receptor_ids]
    dnp01_idx = [node_index[bid] for bid in sorted(set(edges["post"]))]

    # 4. Build the rate model once.
    pre = edges["pre"].map(node_index).to_numpy()
    post = edges["post"].map(node_index).to_numpy()
    w = edges["syn_count"].to_numpy().astype(np.float64)
    model = RateModel.from_edge_list(pre, post, w, n_nodes=n, node_ids=node_ids)

    # 5. Propagate each stimulus; store DNp01 traces + receptor drive.
    out: dict[str, Any] = {"mapping": mapping_provenance(plan)}
    dn_traces: dict[str, list[Any]] = {}
    drive_frames: dict[str, list[Any]] = {}
    for name, (resp_ds, _coords) in stimuli_responses.items():
        if resp_ds is None:
            continue
        drive = aggregate_drive(resp_ds, plan)  # (frames, n_receptors)
        drive_frames[name] = [drive]
        frames = drive.shape[0]
        r = np.zeros(n, dtype=np.float64)
        dn_trace = np.zeros((frames, len(dnp01_idx)), dtype=np.float64)
        for t in range(frames):
            ext = np.zeros(n, dtype=np.float64)
            for k, idx in enumerate(receptor_idx):
                ext[idx] = drive[t, k]
            r = model.step(r, ext)
            dn_trace[t] = r[dnp01_idx]
        dn_traces[name] = [dn_trace]

    # 6. Compute DNp01 sanity metrics.
    dnp01_metrics: dict[str, Any] = {}
    traces_ns = {k: v[0] for k, v in dn_traces.items()}
    for stim_name, tr in traces_ns.items():
        dnp01_metrics[stim_name] = {
            "shape": list(tr.shape),
            "peak_rate": float(np.max(tr)),
            "norm": float(np.linalg.norm(tr)),
            "finite": bool(np.all(np.isfinite(tr))),
        }
    pairwise_dnp01: dict[str, float] = {}
    names = list(traces_ns)
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            ta, tb = traces_ns[a], traces_ns[b]
            min_len = min(len(ta), len(tb))
            pairwise_dnp01[f"{a}_vs_{b}_mse"] = round(
                float(np.mean((ta[:min_len] - tb[:min_len]) ** 2)), 8
            )
    dnp01_metrics["pairwise_trace_mse"] = pairwise_dnp01
    out["dnp01_metrics"] = dnp01_metrics
    out["edge_cache"] = info.path.name if info else None

    # 7. Write out the propagation results.
    prop_dir = run_dir / "connectome"
    prop_dir.mkdir(exist_ok=True)
    for name in traces_ns:
        np.savez(prop_dir / f"dnp01_{name}.npz", trace=traces_ns[name])
    for name, drive_list in drive_frames.items():
        np.savez(prop_dir / f"receptor_drive_{name}.npz", drive=drive_list[0])
    (prop_dir / "mapping.json").write_text(
        json.dumps(out["mapping"], indent=2, default=str)
    )
    (prop_dir / "dnp01_metrics.json").write_text(
        json.dumps(out["dnp01_metrics"], indent=2, default=str)
    )
    # Propagation plot: DNp01 traces per stimulus.
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 4))
    for name, tr in traces_ns.items():
        ax.plot(tr[:, 0], label=f"{name} (DNp01_R)", alpha=0.8)
        if tr.shape[1] > 1:
            ax.plot(tr[:, 1], label=f"{name} (DNp01_L)", alpha=0.5, linestyle="--")
    ax.set_xlabel("frame")
    ax.set_ylabel("rate (a.u.)")
    ax.set_title("DNp01 responses (MaleCNS v1.0, proxy drive from flyvis)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(prop_dir / "dn01_traces.png", dpi=110)
    plt.close(fig)

    logger.info("Connectome propagation complete -> %s", prop_dir)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()

    config_path = args.config
    if not config_path.is_absolute():
        config_path = REPO_ROOT / config_path
    if not config_path.exists():
        logger.error("Config not found: %s", config_path)
        return 1

    config: dict[str, Any] = json.loads(config_path.read_text())
    run_experiment(config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())