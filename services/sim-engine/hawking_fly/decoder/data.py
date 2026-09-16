"""Dataset interface for the decoder study.

Proxy-agnostic by design: the study consumes arbitrary ``visible`` and ``truth``
trajectories, so the verified MaleCNS premotor representation can later replace
the proxy source without touching the decoder API. Metadata (spec §8:
``mapping.verified=False``) always travels with the data.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

PAIRED_FILENAME = "motor_gate_paired_v0.npz"
MANIFEST_FILENAME = "manifest.json"
TYPE_AGG_FILENAME = "motor_gate_verified_v0_type_agg.npz"


@dataclass
class PairedTrajectory:
    stimulus: str
    sample: int
    visible: np.ndarray  # (frame, n_visible_channels)
    truth: np.ndarray  # (frame, n_truth_channels)

    @property
    def id(self) -> str:
        return f"{self.stimulus}/{self.sample}"


@dataclass
class PairedDataset:
    trajectories: list[PairedTrajectory]
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def mapping_verified(self) -> bool:
        perc = self.metadata.get("perc", {})
        # connectome-grounded mode records flyvis_to_malecns_mapping_verified;
        # the legacy paired dataset keeps the plain `verified` key.
        if "flyvis_to_malecns_mapping_verified" in perc:
            return bool(perc["flyvis_to_malecns_mapping_verified"])
        return bool(perc.get("verified", False))


def load_paired_dataset(
    run_dir: str | Path, filename: str = PAIRED_FILENAME
) -> PairedDataset:
    """Load the paired motor-gate dataset from an integration run directory."""
    run_dir = Path(run_dir)
    npz_path = run_dir / filename
    if not npz_path.is_file():
        raise FileNotFoundError(f"paired dataset not found: {npz_path}")
    manifest_path = run_dir / MANIFEST_FILENAME
    if filename == TYPE_AGG_FILENAME:
        manifest_path = run_dir / "manifest_type_agg.json"
    metadata: dict[str, Any] = {}
    if manifest_path.is_file():
        metadata = json.loads(manifest_path.read_text())

    data = np.load(npz_path)
    trajectories: list[PairedTrajectory] = []
    for key in sorted(data.files):
        if key.startswith("visible_"):
            stimulus = key.removeprefix("visible_")
            truth_key = f"truth_{stimulus}"
            if truth_key not in data:
                raise ValueError(f"missing {truth_key} paired to {key}")
            visible = np.asarray(data[key], dtype=np.float64)  # (sample, frame, ch)
            truth = np.asarray(data[truth_key], dtype=np.float64)
            if visible.shape[0] != truth.shape[0]:
                raise ValueError(f"sample mismatch for {stimulus}")
            for s in range(visible.shape[0]):
                trajectories.append(
                    PairedTrajectory(
                        stimulus=stimulus,
                        sample=int(s),
                        visible=visible[s],
                        truth=truth[s],
                    )
                )
    if not trajectories:
        raise ValueError(f"no visible/truth trajectories in {npz_path}")
    return PairedDataset(trajectories=trajectories, metadata=metadata)