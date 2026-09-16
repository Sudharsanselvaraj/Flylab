"""Feature extraction for the proxy motor-signal decoding study.

Features are computed per trajectory (whole trajectory = one decoding unit), so
a train/test split at the trajectory level can never share frames. Each feature
vector is a coarse temporal profile of the upstream drive magnitude plus a
global activity norm.

NOTE: frame counts differ across stimuli (flash 600, moving_edge 465, loom 700);
bins cover each trajectory's own duration. This is recorded in the study output
and is a known experimental simplification.
"""

from __future__ import annotations

import numpy as np


def _bin_profile(visible: np.ndarray, n_bins: int) -> np.ndarray:
    """Mean summed-magnitude activity in ``n_bins`` equal-width time windows."""
    frames = visible.shape[0]
    edges = np.linspace(0, frames, n_bins + 1, dtype=int)
    profile = np.empty(n_bins, dtype=np.float64)
    magnitude = np.sum(np.abs(visible), axis=1)  # (frame,)
    for i in range(n_bins):
        lo, hi = edges[i], edges[i + 1]
        profile[i] = float(magnitude[lo:hi].mean()) if hi > lo else 0.0
    return profile


def to_feature_vector(visible: np.ndarray, n_bins: int = 8) -> np.ndarray:
    """Build the feature vector of one trajectory from its visible trace.

    This is the channel-*agnostic* magnitude profile: bins are sums of |visible|
    across channels. It erases channel identity on purpose, so a connectivity
    null can never separate signal from this representation (see study.py/docs).
    """
    visible = np.asarray(visible, dtype=np.float64)
    if visible.ndim != 2:
        raise ValueError(f"visible must be (frame, channels), got {visible.shape}")
    norm = float(np.linalg.norm(visible))
    profile = _bin_profile(visible, n_bins)
    return np.concatenate([profile, [norm]])


def to_channel_profile(visible: np.ndarray) -> np.ndarray:
    """Per-channel mean magnitude profile — preserves channel identity.

    Shape (n_channels,). Keeps which upstream channel drives how much activity
    on average, so a channel-identity null (baselines.shuffled_channel_identity)
    can actually destroy channel-specific signal.
    """
    visible = np.asarray(visible, dtype=np.float64)
    if visible.ndim != 2:
        raise ValueError(f"visible must be (frame, channels), got {visible.shape}")
    return np.mean(np.abs(visible), axis=0)