"""Null-model baselines for the proxy motor-signal decoding study.

Two independent chance comparisons:

* **shuffled labels** — permute the ground-truth target across trajectories.
  Breaks any real visible->truth coupling while keeping feature statistics.
* **shuffled connectivity** — permute the feature-column mapping (simulated
  random wiring between upstream channels and the truth readout) while keeping
  labels intact.

The study reports where the true decoder result sits within each baseline
distribution rather than comparing against a single magic threshold.
"""

from __future__ import annotations

import numpy as np

Shuffler = np.random.Generator  # type alias for readability


def shuffled_labels(y: np.ndarray, rng: Shuffler) -> np.ndarray:
    return rng.permutation(y)


def shuffled_connectivity(X: np.ndarray, rng: Shuffler) -> np.ndarray:
    """Column-permuted features.

    NOTE: for a linear (ridge) estimator this is a no-op up to feature-column
    relabeling, so it is NOT a valid connectivity null by itself — it exists
    only for transparency. The informative null is `shuffled_channel_identity`.
    """
    perm = rng.permutation(X.shape[1])
    return X[:, perm]


def shuffled_channel_identity(visible: np.ndarray, rng: Shuffler) -> np.ndarray:
    """Permute the upstream-channel axis of ONE trajectory.

    Breaks the address identity of each upstream channel while preserving the
    per-trajectory magnitude statistics. Applied inside feature extraction, this
    is the informative connectivity null (it is not linear-estimator invariant).
    """
    visible = np.asarray(visible, dtype=np.float64)
    if visible.ndim != 2:
        raise ValueError(f"visible must be (frame, channels), got {visible.shape}")
    return visible[:, rng.permutation(visible.shape[1])]