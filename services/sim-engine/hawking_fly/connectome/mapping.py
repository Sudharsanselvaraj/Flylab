"""Explicit flyvis -> MaleCNS receptor drive mapping (HONESTY-CRITICAL).

The looming-escape receptors in MaleCNS are the lobula columnar cells LC4 and
LPLC2. In contrast, the pretrained flyvis optic-lobe model simulates 65
cell types that do NOT include LC4 or LPLC2 (it covers photoreceptors,
medulla columnar cells, Tm/TmY, T4/T5 direction-selective cells, C2/C3, CT1,
etc.). Therefore there is **no one-to-one correspondence** between flyvis
output columns and the MaleCNS receptor bodyIds.

Per spec §8, we must not silently assume equivalence. Everything here is
recorded as an explicit, auditable proxy: each MaleCNS receptor type is paired
with a set of flyvis cell types that plausibly feed that channel, flagged
`correspondence="proxy"`, `verified=False`, with a human-readable note. Every
integration run writes its mapping table into metrics/provenance so the claim
("DNp01 driven by proxy flyvis activity") is fully transparent.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
import xarray as xr

#: Proxy flyvis cell types per MaleCNS receptor type. Documented in
#: `docs/circuit/*.md`; REVISIT before treating any of these as biological fact.
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
            "LC4 is a medulla-recipient lobula columnar neuron. flyvis does not "
            "simulate LC4; medulla->lobula Tm/TmY columnar cells are used as a "
            "proxied feed. Modeling approximation, NOT a verified correspondence."
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
            "LPLC2 is a lobula-plate tangential/columnar loom cell. flyvis does "
            "not simulate LPLC2; direction-selective T4/T5 columns are used as a "
            "proxied LP feed. Modeling approximation, NOT a verified correspondence."
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
        correspondence: 'exact' (never currently) or 'proxy'.
        verified:       False for every proxy row — see spec §8.
        side:           'L' / 'R' best-effort from MaleCNS instance metadata.
        note:           why this pairing was chosen.
    """

    receptor_type: str
    body_id: int
    flyvis_cell_types: tuple[str, ...]
    correspondence: str = "proxy"
    verified: bool = False
    side: str = "unknown"
    note: str = ""

    def to_row(self) -> dict[str, Any]:
        return {
            "receptor_type": self.receptor_type,
            "body_id": self.body_id,
            "flyvis_cell_types": list(self.flyvis_cell_types),
            "correspondence": self.correspondence,
            "verified": self.verified,
            "side": self.side,
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
        else:
            per_receptor.append(_summed_proxy(by_type, p.flyvis_cell_types))
    return np.stack(per_receptor, axis=-1)  # (sample, frame, n_receptors)


def _summed_proxy(by_type: dict[str, np.ndarray], cells: tuple[str, ...]) -> np.ndarray:
    present = [by_type[c] for c in cells if c in by_type]
    if not present:
        return np.zeros(next(iter(by_type.values())).shape[:-1])
    stacked = np.stack(present, axis=-1)  # (sample, frame, n_cells)
    return stacked.mean(axis=-1)


def mapping_provenance(plan: list[ReceptorDrivePlan]) -> dict[str, Any]:
    """The auditable record written into every integration run's metrics."""
    frame = receptor_drive_plan_frame(plan)
    return {
        "receptor_drive_mapping": frame.to_dict(orient="records"),
        "summary": {
            "n_receptors": len(frame),
            "n_driven": int((frame["correspondence"] != "none").sum()),
            "n_proxy_unverified": int((frame["verified"] == False).sum()),  # noqa: E712
            "note": (
                "flyvis (65 optic-lobe cell types) contains NO LC4/LPLC2; the "
                "drive above is a documented proxy and is NOT a verified "
                "cell-type correspondence (spec §8)."
            ),
        },
    }