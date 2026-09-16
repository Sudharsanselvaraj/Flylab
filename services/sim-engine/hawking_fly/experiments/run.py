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
    if config.get("sim", {}).get("with_connectome", False):
        graph_mode = config.get("sim", {}).get("connectome", {}).get("graph", "direct")
        if graph_mode == "relay":
            logger.info("Running MaleCNS-grounded premotor propagation (3-layer graph).")
            conn_out = run_malecns_premotor_propagation(stimuli_responses, config, run_dir)
        else:
            logger.info("Running MaleCNS connectome propagation leg (direct graph).")
            conn_out = run_connectome_propagation(stimuli_responses, config, run_dir)
        metrics["connectome"] = conn_out.get("dnp01_metrics", {})
        metrics["connectome_provenance"] = {
            "edge_cache": conn_out.get("edge_cache"),
            "graph_mode": graph_mode,
            "model_choice": conn_out.get("model_choice", {}),
            "graph_summary": conn_out.get("graph_summary", {}),
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
    )
    from hawking_fly.propagation.rate_model import RateModel, relu, saturating

    # Recorded modeling choice (spec §8): the default `saturating` nonlinearity
    # drives every stimulus to the same equilibrium at DNp01 (pairwise MSE ~ 0),
    # which is not informative for the Phase 0B/0C gate. `relu` keeps the readout
    # proportional to the real weighted input so stimulus differences survive.
    _NL = {"relu": relu, "saturating": saturating}
    nonlinearity_name = (
        config.get("sim", {}).get("connectome", {}).get("nonlinearity", "relu")
    )
    nonlinearity = _NL.get(nonlinearity_name, relu)

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
    pre = edges["pre"].to_numpy()
    post = edges["post"].to_numpy()
    w = edges["syn_count"].to_numpy().astype(np.float64)
    model = RateModel.from_edge_list(
        pre, post, w, n_nodes=n, node_ids=node_ids, nonlinearity=nonlinearity
    )

    # 5. Propagate each stimulus; store DNp01 traces + receptor drive (per sample).
    out: dict[str, Any] = {"mapping": mapping_provenance(plan)}
    out["model_choice"] = {
        "nonlinearity": nonlinearity_name,
        "note": (
            "saturating makes every stimulus saturate at the same DNp01 ceiling; "
            "relu keeps the readout proportional to weighted input (spec §8 label)."
        ),
    }
    dn_traces: dict[str, list[Any]] = {}
    drive_frames: dict[str, list[Any]] = {}
    for name, (resp_ds, _coords) in stimuli_responses.items():
        if resp_ds is None:
            continue
        drive = aggregate_drive(resp_ds, plan)  # (samples, frames, n_receptors)
        drive_frames[name] = [drive]
        n_samples, frames, _ = drive.shape
        dn_trace = np.zeros((n_samples, frames, len(dnp01_idx)), dtype=np.float64)
        for s in range(n_samples):
            r = np.zeros(n, dtype=np.float64)
            for t in range(frames):
                ext = np.zeros(n, dtype=np.float64)
                for k, idx in enumerate(receptor_idx):
                    ext[idx] = drive[s, t, k]
                r = model.step(r, ext)
                dn_trace[s, t] = r[dnp01_idx]
        dn_traces[name] = [dn_trace]

    # 6. Compute DNp01 sanity metrics (per-sample + mean-abs across samples).
    dnp01_metrics: dict[str, Any] = {}
    traces_ns: dict[str, np.ndarray] = {k: v[0] for k, v in dn_traces.items()}
    mean_abs: dict[str, np.ndarray] = {}
    for stim_name, tr in traces_ns.items():
        tr = np.asarray(tr)
        dnp01_metrics[stim_name] = {
            "shape": list(tr.shape),
            "n_samples": int(tr.shape[0]),
            "peak_rate": float(np.max(tr)),
            "mean_peak_rate": float(np.mean(np.max(tr, axis=1))),
            "mean_abs_norm": float(np.linalg.norm(np.abs(tr).mean(axis=0))),
            "finite": bool(np.all(np.isfinite(tr))),
        }
        mean_abs[stim_name] = np.abs(tr).mean(axis=0)  # (frame, n_dnp01)
    pairwise_dnp01: dict[str, float] = {}
    names = list(mean_abs)
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            ta, tb = mean_abs[a], mean_abs[b]
            min_len = min(len(ta), len(tb))
            pairwise_dnp01[f"{a}_vs_{b}_mse"] = round(
                float(np.mean((ta[:min_len] - tb[:min_len]) ** 2)), 8
            )
    dnp01_metrics["pairwise_abs_trace_mse"] = pairwise_dnp01
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
        mean_tr = np.asarray(tr).mean(axis=0)  # mean over samples
        ax.plot(mean_tr[:, 0], label=f"{name} (DNp01_R)", alpha=0.8)
        if mean_tr.shape[1] > 1:
            ax.plot(mean_tr[:, 1], label=f"{name} (DNp01_L)", alpha=0.5, linestyle="--")
    ax.set_xlabel("frame")
    ax.set_ylabel("rate (a.u.)")
    ax.set_title("DNp01 responses (MaleCNS v1.0, proxy drive from flyvis)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(prop_dir / "dn01_traces.png", dpi=110)
    plt.close(fig)

    logger.info("Connectome propagation complete -> %s", prop_dir)
    return out


def run_malecns_premotor_propagation(
    stimuli_responses: dict[str, Any],
    config: dict[str, Any],
    run_dir: Path,
) -> dict[str, Any]:
    """Propagate through the full MaleCNS-grounded premotor graph.

    Loads the cached 3-layer graph (LC4/LPLC2 -> relay layer -> DNp01),
    runs the rate model over all nodes, and extracts per-relay-neuron activity
    traces as the MaleCNS-grounded premotor representation, alongside DNp01
    traces for the decoder ground truth.
    """
    from hawking_fly.connectome.cache import load_cached_circuit
    from hawking_fly.connectome.mapping import (
        build_receptor_drive_plan,
        aggregate_drive,
        mapping_provenance,
    )
    from hawking_fly.connectome.circuits import RELAY_TYPES
    from hawking_fly.propagation.rate_model import RateModel, relu, saturating

    _NL = {"relu": relu, "saturating": saturating}
    nonlinearity_name = (
        config.get("sim", {}).get("connectome", {}).get("nonlinearity", "relu")
    )
    nonlinearity = _NL.get(nonlinearity_name, relu)

    # 1. Load cached 3-layer graph + relay neuron table.
    full_graph, graph_info = load_cached_circuit("loom_escape_full_graph")
    if full_graph is None:
        raise RuntimeError(
            "Full graph cache missing — run discover_malecns_relay_path first"
        )
    relay_neurons, _ = load_cached_circuit("loom_escape_relay_neurons")
    if relay_neurons is None:
        raise RuntimeError("relay_neurons cache missing — run discover_malecns_relay_path first")
    receptor_neurons, _ = load_cached_circuit("loom_escape_receptor_neurons")
    if receptor_neurons is None:
        raise RuntimeError("receptor_neurons cache missing — run run_discovery first")

    # 2. Build node list: all unique bodyIds from the full graph.
    node_ids = sorted(set(full_graph["pre"]) | set(full_graph["post"]))
    node_index = {n: i for i, n in enumerate(node_ids)}
    n = len(node_ids)

    # 3. Identify node populations by role.
    receptor_ids = set(receptor_neurons["bodyId"])
    relay_ids = set(relay_neurons["bodyId"])
    dn_ids = set(full_graph["post"]) - relay_ids - receptor_ids

    receptor_idx = [node_index[bid] for bid in sorted(receptor_ids & set(node_index))]
    relay_df = relay_neurons[relay_neurons["bodyId"].isin(node_index)].copy()
    relay_idx = [node_index[bid] for bid in relay_df["bodyId"].tolist()]
    dn_idx = [node_index[bid] for bid in sorted(dn_ids)]

    # Driven relay subset: those that actually receive LC4/LPLC2 input.
    r2r_edges = full_graph[full_graph["layer"] == "receptor_to_relay"]
    driven_relay_ids = set(r2r_edges["post"])
    driven_mask = [i for i, bid in enumerate(relay_df["bodyId"]) if bid in driven_relay_ids]

    # 4. Build rate model on the full graph.
    pre = full_graph["pre"].to_numpy()
    post = full_graph["post"].to_numpy()
    w = full_graph["syn_count"].to_numpy().astype(np.float64)
    model = RateModel.from_edge_list(
        pre, post, w, n_nodes=n, node_ids=node_ids, nonlinearity=nonlinearity
    )

    # 5. Build flyvis drive plan (same proxy as direct graph).
    sample_resp = next(
        (r for (r, _) in stimuli_responses.values() if r is not None), None
    )
    if sample_resp is None:
        raise RuntimeError("no flyvis responses available")
    cell_types: set[str] = set(
        np.asarray(
            sample_resp.cell_type.values if "cell_type" in sample_resp.coords else []
        )
    )
    plan = build_receptor_drive_plan(receptor_neurons, available_cell_types=cell_types)

    # 6. Propagate each stimulus; extract relay + DNp01 traces.
    out: dict[str, Any] = {"mapping": mapping_provenance(plan)}
    out["model_choice"] = {"nonlinearity": nonlinearity_name}
    out["graph_summary"] = {
        "n_nodes": n,
        "n_receptor_nodes": len(receptor_idx),
        "n_relay_nodes": len(relay_idx),
        "n_driven_relay_nodes": len(driven_mask),
        "n_dn_nodes": len(dn_idx),
        "edge_cache": graph_info.path.name if graph_info else None,
        "layer_synapses": full_graph.groupby("layer")["syn_count"].sum().to_dict(),
    }

    prop_dir = run_dir / "connectome"
    prop_dir.mkdir(exist_ok=True)

    relay_traces: dict[str, np.ndarray] = {}
    dn_traces: dict[str, np.ndarray] = {}
    for name, (resp_ds, _coords) in stimuli_responses.items():
        if resp_ds is None:
            continue
        drive = aggregate_drive(resp_ds, plan)  # (samples, frames, n_receptors)
        n_samples, frames, _ = drive.shape
        relay_trace = np.zeros((n_samples, frames, len(relay_idx)), dtype=np.float64)
        dn_trace = np.zeros((n_samples, frames, len(dn_idx)), dtype=np.float64)
        for s in range(n_samples):
            r = np.zeros(n, dtype=np.float64)
            for t in range(frames):
                ext = np.zeros(n, dtype=np.float64)
                for k, idx in enumerate(receptor_idx):
                    ext[idx] = drive[s, t, k]
                r = model.step(r, ext)
                relay_trace[s, t] = r[relay_idx]
                dn_trace[s, t] = r[dn_idx]
        relay_traces[name] = relay_trace
        dn_traces[name] = dn_trace
        np.savez(prop_dir / f"relay_{name}.npz", trace=relay_trace)
        np.savez(prop_dir / f"dnp01_{name}.npz", trace=dn_trace)
        np.savez(prop_dir / f"receptor_drive_{name}.npz", drive=drive)

    # 7. Save relay neuron metadata.
    relay_meta = relay_df[["bodyId", "type", "instance"]].reset_index(drop=True)
    relay_meta["node_index"] = relay_idx
    relay_meta["has_receptor_input"] = [bid in driven_relay_ids for bid in relay_meta["bodyId"]]
    relay_meta.to_json(prop_dir / "relay_neurons.json", orient="records", indent=2)

    # 8. Compute metrics.
    metrics: dict[str, Any] = {}
    for stim_name, tr in dn_traces.items():
        tr = np.asarray(tr)
        metrics[f"dnp01_{stim_name}"] = {
            "shape": list(tr.shape),
            "mean_abs_norm": float(np.mean(np.abs(tr).mean(axis=0))),
            "finite": bool(np.all(np.isfinite(tr))),
        }
    for stim_name, tr in relay_traces.items():
        tr = np.asarray(tr)
        driven = tr[:, :, driven_mask] if driven_mask else tr[:, :, :0]
        metrics[f"relay_{stim_name}"] = {
            "shape": list(tr.shape),
            "driven_shape": list(driven.shape),
            "driven_mean_abs_norm": float(np.mean(np.abs(driven).mean(axis=0))) if driven_mask else 0.0,
            "silent_fraction": round(1.0 - (len(driven_mask) / len(relay_idx)), 3) if relay_idx else 1.0,
            "finite": bool(np.all(np.isfinite(tr))),
        }

    # Pairwise abs-trace MSE.
    pairwise: dict[str, float] = {}
    all_means: dict[str, np.ndarray] = {}
    for k, tr in {**dn_traces, **{f"relay_{k}": v for k, v in relay_traces.items()}}.items():
        all_means[k] = np.abs(np.asarray(tr)).mean(axis=0).ravel()
    keys = list(all_means)
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            ta, tb = all_means[a], all_means[b]
            min_len = min(len(ta), len(tb))
            pairwise[f"{a}_vs_{b}_mse"] = round(
                float(np.mean((ta[:min_len] - tb[:min_len]) ** 2)), 8
            )
    metrics["pairwise_abs_trace_mse"] = pairwise

    out["dnp01_metrics"] = metrics
    out["edge_cache"] = graph_info.path.name if graph_info else None
    (prop_dir / "mapping.json").write_text(json.dumps(out["mapping"], indent=2, default=str))
    (prop_dir / "dnp01_metrics.json").write_text(json.dumps(metrics, indent=2, default=str))

    # 9. Propagation plot: relay neurons + DNp01 traces per stimulus.
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    ax_relay, ax_dn = axes
    for name, tr in relay_traces.items():
        tr_driven = np.asarray(tr)[:, :, driven_mask] if driven_mask else np.asarray(tr)[:, :, :0]
        mean_tr = tr_driven.mean(axis=0)
        for ch in range(mean_tr.shape[1]):
            lbl = f"{name} ch{ch}" if ch < 3 else None
            ax_relay.plot(mean_tr[:, ch], label=lbl, alpha=0.6)
    ax_relay.set_title("Driven relay neuron traces (MaleCNS-grounded premotor)")
    ax_relay.set_xlabel("frame")
    ax_relay.set_ylabel("rate (a.u.)")
    ax_relay.legend(fontsize=6, ncol=2)

    for name, tr in dn_traces.items():
        mean_tr = np.asarray(tr).mean(axis=0)
        ax_dn.plot(mean_tr[:, 0], label=f"{name} (DNp01_R)", alpha=0.8)
        if mean_tr.shape[1] > 1:
            ax_dn.plot(mean_tr[:, 1], label=f"{name} (DNp01_L)", alpha=0.5, linestyle="--")
    ax_dn.set_title("DNp01 traces (MaleCNS-grounded premotor)")
    ax_dn.set_xlabel("frame")
    ax_dn.set_ylabel("rate (a.u.)")
    ax_dn.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(prop_dir / "premotor_traces.png", dpi=110)
    plt.close(fig)

    logger.info("MaleCNS premotor propagation complete -> %s", prop_dir)
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