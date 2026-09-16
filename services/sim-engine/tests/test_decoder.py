"""Tests for the Phase 0C proxy motor-signal decoding study (no validated claims)."""
import json
from pathlib import Path

import numpy as np
import pytest

from hawking_fly.decoder.baselines import (
    shuffled_channel_identity,
    shuffled_connectivity,
    shuffled_labels,
)
from hawking_fly.decoder.data import load_paired_dataset
from hawking_fly.decoder.features import to_channel_profile, to_feature_vector
from hawking_fly.decoder.study import run_study


def _fake_run(run_dir: Path, verified: bool = False) -> None:
    rng = np.random.default_rng(0)
    arrays: dict[str, np.ndarray] = {}
    for stim, frames, n_samples in (("flash", 60, 3), ("loom", 70, 2)):
        arrays[f"visible_{stim}"] = rng.random((n_samples, frames, 4)).astype(np.float32)
        arrays[f"truth_{stim}"] = rng.random((n_samples, frames, 2)).astype(np.float32)
    np.savez(run_dir / "motor_gate_paired_v0.npz", **arrays)
    (run_dir / "manifest.json").write_text(
        json.dumps(
            {
                "perc": {"label": "documented proxy", "verified": verified},
                "model_choice": {"nonlinearity": "relu"},
                "definition": {"visible": "proxy", "ground_truth": "DNp01"},
            }
        )
    )


def test_load_paired_dataset_shape_and_metadata(tmp_path):
    _fake_run(tmp_path)
    ds = load_paired_dataset(tmp_path)
    assert len(ds.trajectories) == 5
    assert ds.trajectories[0].visible.shape == (60, 4)
    assert ds.trajectories[0].truth.shape == (60, 2)
    assert set(t.stimulus for t in ds.trajectories) == {"flash", "loom"}
    assert ds.mapping_verified is False


def test_feature_vector_shape():
    fv = to_feature_vector(np.random.rand(50, 4), n_bins=8)
    assert fv.shape == (9,)
    assert np.all(fv[:-1] >= 0)
    assert fv[-1] > 0


def test_channel_profile_shape():
    cp = to_channel_profile(np.random.rand(50, 11))
    assert cp.shape == (11,)
    assert np.all(cp >= 0)


def test_baselines_actually_shuffle():
    rng = np.random.default_rng(1)
    y = np.arange(5, dtype=float)
    assert not np.array_equal(shuffled_labels(y, rng), y)
    X = np.arange(20, dtype=float).reshape(5, 4)
    Xs = shuffled_connectivity(X, np.random.default_rng(3))
    assert sorted(X[0].tolist()) == sorted(Xs[0].tolist())
    assert not np.array_equal(X, Xs)
    vis = rng.random((30, 4))
    vis_swap = shuffled_channel_identity(vis, np.random.default_rng(3))
    assert vis_swap.shape == vis.shape
    assert not np.array_equal(vis, vis_swap)
    # same values overall (columns permuted, no channel lost or duplicated)
    assert np.allclose(np.sort(vis.flatten()), np.sort(vis_swap.flatten()))


def test_run_study_emits_artifacts_and_flags_proxy(tmp_path):
    _fake_run(tmp_path)
    out = tmp_path / "out"
    results = run_study(
        tmp_path, out_dir=out, n_shuffles=10, also_leave_out_flash=True
    )
    assert results["mapping_verified"] is False
    assert results["study"] == "proxy_motor_decoding"
    assert "profile" in results["regression"]
    assert "channel" in results["regression"]
    assert results["baselines"]["channel"]["channel_swap"]["note"].startswith(
        "per-trajectory upstream-channel permutation"
    )
    assert results["leakage"]["result"].startswith("trajectory-level")
    assert (out / "proxy_motor_decoding.json").is_file()
    assert (out / "proxy_motor_decoding.png").is_file()


def test_run_study_refuses_verified_true(tmp_path):
    _fake_run(tmp_path, verified=True)
    with pytest.raises(ValueError, match="reviewer acknowledgment"):
        run_study(tmp_path, n_shuffles=5)


def test_run_study_allows_grounded_with_opt_in(tmp_path):
    _fake_run(tmp_path, verified=True)
    results = run_study(
        tmp_path, n_shuffles=5, allow_grounded_mapping=True
    )
    assert results["mapping_verified"] is True
    # caveat switched to the grounded note, not the legacy "unverified" one
    assert any("synapse" in c for c in results["caveats"])


def test_generalization_includes_flash_and_loom(tmp_path):
    _fake_run(tmp_path)
    results = run_study(tmp_path, n_shuffles=2, also_leave_out_flash=True)
    assert "flash" in results["generalization_leave_stimulus_out"]
    assert "loom" in results["generalization_leave_stimulus_out"]