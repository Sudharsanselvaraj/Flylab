"""Explicit flyvis -> MaleCNS receptor drive mapping (HONESTY-CRITICAL).

The looming-escape receptors in MaleCNS are the lobula columnar cells LC4 and
LPLC2. In contrast, the pretrained flyvis optic-lobe model simulates 65
cell types that do NOT include LC4 or LPLC2 (it covers photoreceptors,
medulla columnar cells, Tm/TmY, T4/T5 direction-selective cells, C2/C3, CT1,
etc.). Therefore there is **no one-to-one correspondence** between flyvis
output columns and the MaleCNS receptor bodyIds.

Two mapping modes are supported, both auditable:

* ``connectome_grounded`` (default): the flyvis -> receptor drive is built
  from the *actual* MaleCNS v1.0 synaptic input to each receptor type. For
  every LC4/LPLC2 neuron we look at what MaleCNS types are presynaptic to it
  (live adjacency, cached by ``routes.discover_receptor_upstream_evidence``),
  keep the subset that flyvis models, and weight each flyvis class by its
  measured synapse count onto that receptor type. This replaces a guess with
  connectome evidence: "these flyvis classes genuinely synapse onto LC4/LPLC2
  in MaleCNS v1.0, with these weights." The residual gap (flyvis classes cover
  ~60% of non-self synapse weight for these receptors in v1.0) is recorded
  per row.

* ``legacy_proxy``: the old hand-picked Tm/TmY / T4/T5 proxy, retained only
  for comparison runs. Marked ``verified=False``.

Whatever mode runs, the plan is recorded in metrics/provenance so the claim
("DNp01 driven by proxy flyvis activity") is fully transparent. `verified`
means *synapse-grounded at the connectome level* (the class indeed feeds the
receptor in MaleCNS v1.0), NOT that flyvis responses equal MaleCNS recordings.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
import xarray as xr

from hawking_fly.connectome.circuits import FLYVIS_CELL_TYPES

#: Legacy proxy flyvis cell types per MaleCNS receptor type. KEPT AS FALLBACK
#: ONLY (comparison / sensitivity runs). Documented in `docs/circuit/*.md`;
#: DO NOT treat as biological fact — MaleCNS evidence disagrees with LC4.
FLYVIS_RECEPTOR_PROXY: dict[str, dict[str, Any]] = {
    "LC4": {
        "proxy_cell_types": [
            "Tm5a",
            "Tm5b",
            "Tm5c",
            "Tm9",
            "Tm16",
            "TmY10",
        ],
        "correspondence": "proxy",
        "verified": False,
        "note": (
            "LEGACY PROXY. MaleCNS v1.0 connectome evidence shows LC4 input is "
            "dominated by T2/TmY3/Tm4/Tm2/Tm3/T5 (flyvis classes) — see the "
            "connectome_grounded mode. Retained only for comparison runs."
        ),
    },
    "LPLC2": {
        "proxy_cell_types": [
            "T4a",
            "T4b",
            "T4c",
            "T4d",
            "T5a",
            "T5b",
            "T5c",
            "T5d",
        ],
        "correspondence": "proxy",
        "verified": False,
        "note": (
            "LEGACY PROXY. MaleCNS v1.0 confirms T4/T5 feed LPLC2 but Tm5Y/"
            "Tm20/TmY5A/Tm4 contribute more total synapses than the T4/T5 block "
            "alone — see the connectome_grounded mode."
        ),
    },
}

#: MaleCNS side inference is best-effort (from `instance` strings like
#: 'DNp01(GF)_R' / 'DNp01(GF)_L'); a missing side defaults to 'unknown' and the
#: same single-eye flyvis drive is applied bilaterally (recorded assumption).
UNILATERAL_SIDE = "R"


@dataclass
class ReceptorDrivePlan:
    """Auditable plan linking MaleCNS receptor bodyIds to flyvis cell types.

    Attributes:
        receptor_type:  MaleCNS cell type (e.g. 'LC4').
        body_id:        MaleCNS neuron bodyId (one row per receptor neuron).
        flyvis_cell_types: flyvis columns supplying the drive for this receptor.
        flyvis_cell_type_weights: per-class synapse weight (MaleCNS v1.0) used
            for weighted aggregation; empty tuple for legacy equal-mean proxy.
        correspondence: 'connectome_grounded' or 'proxy'.
        verified:       False for every legacy proxy row — see spec §8. For
            connectome-grounded rows True means *synapse-grounded in MaleCNS
            v1.0*, not that flyvis responses are MaleCNS recordings.
        side:           'L' / 'R' best-effort from MaleCNS instance metadata.
        coverage:       fraction of this receptor's non-self synapse input that
            the selected flyvis classes account for (0..1).
        note:           why this pairing was chosen.
    """

    receptor_type: str
    body_id: int
    flyvis_cell_types: tuple[str, ...]
    correspondence: str = "proxy"
    verified: bool = False
    side: str = "unknown"
    coverage: float = 0.0
    flyvis_cell_type_weights: tuple[float, ...] = field(default_factory=tuple)
    note: str = ""

    def to_row(self) -> dict[str, Any]:
        return {
            "receptor_type": self.receptor_type,
            "body_id": self.body_id,
            "flyvis_cell_types": list(self.flyvis_cell_types),
            "flyvis_cell_type_weights": list(self.flyvis_cell_type_weights),
            "correspondence": self.correspondence,
            "verified": self.verified,
            "side": self.side,
            "coverage": round(self.coverage, 4),
            "note": self.note,
        }


def build_receptor_drive_plan(
    receptor_neurons: pd.DataFrame,
    *,
    available_cell_types: set[str] | None = None,
) -> list[ReceptorDrivePlan]:
    """Build the proxy drive plan for the MaleCNS receptor set.

    One row per receptor bodyId. `available_cell_types`, if given, filters each
    proxy list to cell types actually present in the flyvis response dataset
    (recorded in the note when filtering occurs).
    """
    plan: list[ReceptorDrivePlan] = []
    for row in receptor_neurons.itertuples(index=False):
        rtype = str(row.type)
        rtype = "LPLC2" if rtype == "LPLC2" else rtype
        entry = FLYVIS_RECEPTOR_PROXY.get(rtype)
        if entry is None:
            # Receptors outside the proxy table are intentionally un-driven.
            plan.append(
                ReceptorDrivePlan(
                    receptor_type=rtype,
                    body_id=int(row.bodyId),
                    flyvis_cell_types=(),
                    correspondence="none",
                    verified=False,
                    side=_infer_side(row),
                    note="no flyvis proxy defined for this receptor type; "
                    "left un-driven (documented omission).",
                )
            )
            continue

        proxy = list(entry["proxy_cell_types"])
        note = entry["note"]
        if available_cell_types is not None:
            missing = [c for c in proxy if c not in available_cell_types]
            proxy = [c for c in proxy if c in available_cell_types]
            if missing:
                note = f"{note} [filtered to flyvis-available cells; absent: {sorted(missing)!r}]"

        plan.append(
            ReceptorDrivePlan(
                receptor_type=rtype,
                body_id=int(row.bodyId),
                flyvis_cell_types=tuple(proxy),
                correspondence=str(entry["correspondence"]),
                verified=bool(entry["verified"]),
                side=_infer_side(row),
                note=note,
            )
        )
    return plan


def _infer_side(row: Any) -> str:
    inst = str(getattr(row, "instance", "") or "")
    for marker, side in (("(R)", "R"), ("(L)", "L"), ("_R", "R"), ("_L", "L")):
        if marker in inst:
            return side
    return "unknown"


DEFAULT_MIN_SYNAPSES = 50
DEFAULT_COVERAGE_FRACTION = 0.9


def build_connectome_grounded_drive_plan(
    receptor_neurons: pd.DataFrame,
    upstream_evidence: dict[str, pd.DataFrame],
    *,
    available_cell_types: set[str] | None = None,
    min_synapses: int = DEFAULT_MIN_SYNAPSES,
    coverage_fraction: float = DEFAULT_COVERAGE_FRACTION,
) -> list[ReceptorDrivePlan]:
    """Build the drive plan from actual MaleCNS synaptic input.

    For each receptor type, take its MaleCNS-typed upstream partners
    (``upstream_evidence[type]`` with columns pre_type / total_syn / is_self),
    keep rows that flyvis models *and* that are present in
    ``available_cell_types``, drop self-feedback, order classes by descending
    synapse weight, and keep the smallest prefix that accounts for at least
    ``coverage_fraction`` of the flyvis-representable non-self input. Every
    receptor bodyId of that type is then driven by those classes weighted by
    their measured MaleCNS synapse counts.

    Returns one :class:`ReceptorDrivePlan` per receptor neuron, with
    ``correspondence='connectome_grounded'`` and ``verified=True``
    (synapse-grounded in MaleCNS v1.0 — see module docstring for the boundary
    of 'verified').
    """
    covered_types: set[str] = set(available_cell_types or FLYVIS_CELL_TYPES)
    plan: list[ReceptorDrivePlan] = []
    for row in receptor_neurons.itertuples(index=False):
        rtype = str(row.type)
        table = upstream_evidence.get(rtype)
        if table is None:
            plan.append(
                ReceptorDrivePlan(
                    receptor_type=rtype,
                    body_id=int(row.bodyId),
                    flyvis_cell_types=(),
                    correspondence="none",
                    verified=False,
                    side=_infer_side(row),
                    coverage=0.0,
                    note="no MaleCNS upstream evidence for this receptor type; "
                    "left un-driven (documented omission).",
                )
            )
            continue

        cand = table[~table["is_self"]].copy()
        flyvis_rows = cand[cand["pre_type"].isin(FLYVIS_CELL_TYPES)].copy()
        if available_cell_types is not None:
            flyvis_rows = flyvis_rows[flyvis_rows["pre_type"].isin(covered_types)]
        flyvis_rows = flyvis_rows.sort_values("total_syn", ascending=False)

        total_non_self = float(cand["total_syn"].sum())
        representable = float(flyvis_rows["total_syn"].sum())
        selected: list[str] = []
        weights: list[float] = []
        covered = 0.0
        for _, r in flyvis_rows.iterrows():
            if float(r["total_syn"]) < min_synapses:
                continue
            selected.append(str(r["pre_type"]))
            weights.append(float(r["total_syn"]))
            covered = sum(weights)
            if representable > 0 and covered / representable >= coverage_fraction:
                break
        coverage = (covered / total_non_self) if total_non_self > 0 else 0.0

        if not selected:
            plan.append(
                ReceptorDrivePlan(
                    receptor_type=rtype,
                    body_id=int(row.bodyId),
                    flyvis_cell_types=(),
                    correspondence="none",
                    verified=False,
                    side=_infer_side(row),
                    coverage=0.0,
                    note=(
                        "no MaleCNS-typed flyvis-class input above the synapse "
                        "floor for this receptor; left un-driven."
                    ),
                )
            )
            continue

        plan.append(
            ReceptorDrivePlan(
                receptor_type=rtype,
                body_id=int(row.bodyId),
                flyvis_cell_types=tuple(selected),
                correspondence="connectome_grounded",
                verified=True,
                side=_infer_side(row),
                coverage=coverage,
                flyvis_cell_type_weights=tuple(weights),
                note=(
                    "drive classes = MaleCNS v1.0 presynaptic partners of this "
                    "receptor that flyvis models, weighted by synapse count; "
                    f"flyvis-representable coverage {coverage:.1%} of non-self input."
                ),
            )
        )
    return plan


def receptor_drive_plan_frame(plan: list[ReceptorDrivePlan]) -> pd.DataFrame:
    return pd.DataFrame([p.to_row() for p in plan])


def aggregate_drive(
    flyvis_responses: Any,
    plan: list[ReceptorDrivePlan],
) -> np.ndarray:
    """Aggregate flyvis activity into per-receptor drive over time.

    `flyvis_responses` is a flyvis response xarray Dataset (or response
    DataArray) with dims (network_id, sample, frame, neuron) and a `cell_type`
    (neuron) coordinate. Returns drive array of shape
    (n_samples, frame, n_receptors); samples are averaged over network only,
    NEVER over samples — flash alternation (ON/OFF) cancels under a sample mean,
    destroying the stimulus signal for the downstream gate.

    Weighted aggregation: when a plan row carries MaleCNS synapse weights they
    are used (weighted mean over the driving classes); legacy proxy rows fall
    back to an equal-mean over the listed classes.

    Bilateral assumption (recorded, spec §8): flyvis simulates a single optic
    lobe; the same drive signal is applied to both MaleCNS left/right receptor
    bodyIds because every row in the plan references the same single-eye signal.
    """
    cell_types = list(np.asarray(flyvis_responses.cell_type.values))
    if isinstance(flyvis_responses, xr.Dataset):
        responses = np.asarray(flyvis_responses["responses"].values)  # (net, sample, frame, neuron)
    else:
        responses = np.asarray(flyvis_responses.values)
    if responses.ndim != 4:
        raise ValueError(f"expected 4D responses, got shape {responses.shape}")
    per_net = responses.mean(axis=0)  # (sample, frame, neuron)

    by_type: dict[str, np.ndarray] = {}
    for i, ct in enumerate(cell_types):
        by_type[ct] = per_net[..., i]

    per_receptor: list[np.ndarray] = []
    for p in plan:
        if not p.flyvis_cell_types:
            per_receptor.append(np.zeros(per_net.shape[:-1], dtype=np.float64))
        elif p.flyvis_cell_type_weights:
            per_receptor.append(
                _weighted_proxy(
                    by_type, p.flyvis_cell_types, p.flyvis_cell_type_weights
                )
            )
        else:
            per_receptor.append(_summed_proxy(by_type, p.flyvis_cell_types))
    return np.stack(per_receptor, axis=-1)  # (sample, frame, n_receptors)


def _weighted_proxy(
    by_type: dict[str, np.ndarray],
    cells: tuple[str, ...],
    weights: tuple[float, ...],
) -> np.ndarray:
    present = [(c, w) for c, w in zip(cells, weights) if c in by_type]
    present = [(c, w) for c, w in present if np.isfinite(float(w)) and float(w) > 0]
    if not present:
        return np.zeros(next(iter(by_type.values())).shape[:-1])
    names = [c for c, _ in present]
    wts = np.asarray([w for _, w in present], dtype=np.float64)
    wts = wts / wts.sum()
    stacked = np.stack([by_type[c] for c in names], axis=-1)  # (sample, frame, n_cells)
    return (stacked * wts).sum(axis=-1)


def _summed_proxy(by_type: dict[str, np.ndarray], cells: tuple[str, ...]) -> np.ndarray:
    present = [by_type[c] for c in cells if c in by_type]
    if not present:
        return np.zeros(next(iter(by_type.values())).shape[:-1])
    stacked = np.stack(present, axis=-1)  # (sample, frame, n_cells)
    return stacked.mean(axis=-1)


def mapping_provenance(plan: list[ReceptorDrivePlan]) -> dict[str, Any]:
    """The auditable record written into every integration run's metrics."""
    frame = receptor_drive_plan_frame(plan)
    n_grounded = int((frame["correspondence"] == "connectome_grounded").sum())
    return {
        "receptor_drive_mapping": frame.to_dict(orient="records"),
        "summary": {
            "n_receptors": len(frame),
            "n_driven": int((frame["correspondence"] != "none").sum()),
            "n_connectome_grounded": n_grounded,
            "n_legacy_proxy": int((frame["correspondence"] == "proxy").sum()),
            "avg_coverage": round(float(frame["coverage"].mean()), 4),
            "note": (
                "flyvis (65 optic-lobe cell types) contains NO LC4/LPLC2; the "
                "drive is either grounded in MaleCNS v1.0 synaptic input "
                "(correspondence='connectome_grounded', verified=True) or the "
                "documented legacy proxy. Grounded verified=True means the "
                "classes synapse onto the receptor in MaleCNS v1.0 — NOT that "
                "flyvis responses equal MaleCNS recordings."
            ),
        },
    }