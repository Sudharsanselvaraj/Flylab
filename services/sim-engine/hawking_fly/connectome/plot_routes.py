"""Subgraph route summary plot (no live queries — reads cached snapshots only)."""
from __future__ import annotations
from pathlib import Path
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from hawking_fly.connectome.cache import load_cached_circuit

REPO = Path(__file__).resolve().parents[4]
PLOT_DIR = REPO / "experiments/loom_escape/plots"
PLOT_DIR.mkdir(parents=True, exist_ok=True)


def make_summary_plot() -> Path:
    direct, _ = load_cached_circuit("loom_escape_direct_lc4_lplc2_to_dnp01")
    upstream, _ = load_cached_circuit("loom_escape_upstream_partners")
    if direct is None or upstream is None:
        raise RuntimeError("cached circuits missing")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5), gridspec_kw={"width_ratios": [2, 1]})

    # (a) Top upstream types by total synapses
    top = upstream.groupby("type")["total_syn"].sum().nlargest(8).reset_index()
    colors = ["#2b6a99" if t in ("LC4", "LPLC2") else "#999" for t in top["type"]]
    ax1.barh(top["type"][::-1], top["total_syn"][::-1], color=colors[::-1], edgecolor="white")
    ax1.set_xlabel("total synapses")
    ax1.set_title("DNp01 top upstream partners (MaleCNS v1.0)")
    ax1.invert_yaxis()

    # (b) Pie: direct LC4/LPLC2 vs other upstream (above threshold)
    direct_total = int(direct["syn_count"].sum())
    other_total = int(upstream.loc[~upstream["type"].isin(("LC4", "LPLC2")), "total_syn"].sum())
    ax2.pie(
        [direct_total, other_total],
        labels=[f"LC4/LPLC2 direct\n{direct_total:,}", f"other upstream\n{other_total:,}"],
        colors=["#2b6a99", "#ccc"],
        startangle=90,
        autopct=lambda p: f"{p:.0f}%",
    )
    ax2.set_title(f"DNp01 input composition\n(direct = {direct_total / (direct_total + other_total):.0%})")

    fig.suptitle("LC4/LPLC2 → DNp01 loom-escape subgraph (bounded, MaleCNS v1.0)", y=1.02, fontsize=11)
    fig.tight_layout()
    out = PLOT_DIR / "connectome_routes_summary.png"
    fig.savefig(out, dpi=110, bbox_inches="tight")
    plt.close(fig)
    return out


if __name__ == "__main__":
    p = make_summary_plot()
    print("saved:", p)
