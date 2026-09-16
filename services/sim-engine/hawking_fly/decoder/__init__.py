"""Decoder module (Phase 0C) — experimental proxy motor-signal decoding.

This is an *experimental* study: it decodes the DNp01 ground-truth trace from
the upstream **proxy** receptor drive. The proxy mapping is explicitly
unverified (`mapping.verified=False`, spec §8); the results here must never be
described as validated motor-signal decoding. See
`docs/decoder/proxy_motor_decoding.md`.
"""

from hawking_fly.decoder.data import PairedDataset, PairedTrajectory, load_paired_dataset
from hawking_fly.decoder.features import to_feature_vector
from hawking_fly.decoder.study import run_study

__all__ = [
    "PairedDataset",
    "PairedTrajectory",
    "load_paired_dataset",
    "to_feature_vector",
    "run_study",
]