"""Tests for the Phase 0B paired-dataset builder (no decoder, spec §8 labels)."""
import json
from pathlib import Path

import numpy as np

from hawking_fly.motor_gate.dataset import (
    PAIRED_MANIFEST,
    PAIRED_NPZ,
    PAIRED_VERIFIED_NPZ,
    PAIRED_VERIFIED_TYPE_AGG_NPZ,
    build_paired_dataset,
    build_verified_premotor_dataset,
)


def _fake_run(run_dir: Path) -> None:
    conn = run_dir / "connectome"
    conn.mkdir(parents=True)
    rng = np.random.default_rng(0)
    for stim, frames in (("flash", 60), ("loom", 70)):
        np.savez(conn / f"receptor_drive_{stim}.npz", drive=rng.random((2, frames, 4)))
        np.savez(conn / f"dnp01_{stim}.npz", trace=rng.random((2, frames, 2)))
    (conn / "mapping.json").write_text(
        json.dumps(
            {
                "created": "2026-09-16T00:00:00+00:00",
                "summary": {"n_receptors": 311, "verified": False},
            }
        )
    )
    (run_dir / "metrics.json").write_text(
        json.dumps(
            {
                "connectome_provenance": {
                    "model_choice": {"nonlinearity": "relu"},
                    "mapping_summary": {"n_receptors": 311},
                }
            }
        )
    )


def test_build_paired_dataset(tmp_path):
    run_dir = tmp_path / "run128"
    run_dir.mkdir()
    _fake_run(run_dir)
    out = build_paired_dataset(run_dir, out_dir=run_dir / "motor_gate")
    assert out.name == PAIRED_NPZ
    assert (run_dir / "motor_gate" / PAIRED_MANIFEST).is_file()

    data = np.load(out)
    assert "visible_flash" in data and "truth_flash" in data
    assert "visible_loom" in data and "truth_loom" in data
    assert data["visible_flash"].shape == (2, 60, 4)
    assert data["truth_flash"].shape == (2, 60, 2)
    assert data["visible_flash"].dtype == np.float32

    manifest = json.loads((run_dir / "motor_gate" / PAIRED_MANIFEST).read_text())
    assert manifest["perc"]["verified"] is False
    assert manifest["model_choice"]["nonlinearity"] == "relu"
    assert manifest["stimuli"]["loom"]["n_samples"] == 2


def test_build_paired_dataset_missing_connectome_raises(tmp_path):
    run_dir = tmp_path / "run_bare"
    run_dir.mkdir()
    try:
        build_paired_dataset(run_dir)
        assert False, "expected FileNotFoundError"
    except FileNotFoundError:
        pass


# ---------------------------------------------------------------------------
# MaleCNS-grounded premotor pairing (relay neurons -> DNp01)
# ---------------------------------------------------------------------------


def _fake_verified_run(run_dir: Path) -> None:
    """A synthetic full-graph leg: 5 relay neurons, 3 driven + 2 silent."""
    conn = run_dir / "connectome"
    conn.mkdir(parents=True)
    rng = np.random.default_rng(1)
    relay_meta = [
        {"bodyId": 10001, "type": "PVLP010", "instance": "a", "has_receptor_input": True},
        {"bodyId": 10002, "type": "PVLP010", "instance": "b", "has_receptor_input": True},
        {"bodyId": 10003, "type": "SAD064", "instance": "a", "has_receptor_input": True},
        {"bodyId": 10004, "type": "JO-B1_a", "instance": "a", "has_receptor_input": False},
        {"bodyId": 10005, "type": "AN12B001", "instance": "a", "has_receptor_input": False},
    ]
    (conn / "relay_neurons.json").write_text(json.dumps(relay_meta))
    for stim, frames in (("flash", 60), ("loom", 70)):
        np.savez(conn / f"relay_{stim}.npz", trace=rng.random((2, frames, 5)))
        np.savez(conn / f"dnp01_{stim}.npz", trace=rng.random((2, frames, 2)))
    (conn / "mapping.json").write_text(
        json.dumps(
            {
                "created": "2026-09-16T00:00:00+00:00",
                "summary": {
                    "n_receptors": 311,
                    "n_connectome_grounded": 311,
                    "avg_coverage": 0.56,
                },
            }
        )
    )


def test_build_verified_premotor_dataset(tmp_path):
    run_dir = tmp_path / "run_verified"
    run_dir.mkdir()
    _fake_verified_run(run_dir)
    out = build_verified_premotor_dataset(run_dir)
    assert out.name == PAIRED_VERIFIED_NPZ

    data = np.load(out)
    # only the 3 driven relay cells are emitted as visible channels
    assert data["visible_loom"].shape == (2, 70, 3)
    assert data["truth_loom"].shape == (2, 70, 2)
    assert data["visible_loom"].dtype == np.float32

    manifest = json.loads((run_dir / PAIRED_MANIFEST).read_text())
    perc = manifest["perc"]
    assert perc["dynamics_validated"] is False
    assert perc["flyvis_to_malecns_mapping_verified"] is True  # grounded summary
    assert perc["n_relay_channels"] == 3
    assert perc["n_silent_excluded"] == 2
    assert perc["channels"] == ["PVLP010", "PVLP010", "SAD064"]


def test_build_verified_premotor_dataset_type_agg(tmp_path):
    run_dir = tmp_path / "run_typeagg"
    run_dir.mkdir()
    _fake_verified_run(run_dir)
    out = build_verified_premotor_dataset(run_dir, type_aggregated=True)
    assert out.name == PAIRED_VERIFIED_TYPE_AGG_NPZ

    data = np.load(out)
    assert data["visible_loom"].shape == (2, 70, 2)  # PVLP010 + SAD064

    manifest = json.loads((run_dir / "manifest_type_agg.json").read_text())
    perc = manifest["perc"]
    assert perc["n_type_channels"] == 2
    assert perc["channels"] == ["PVLP010", "SAD064"]
    assert perc["dynamics_validated"] is False


def test_build_verified_premotor_dataset_missing_relay_meta_raises(tmp_path):
    run_dir = tmp_path / "run_no_meta"
    run_dir.mkdir()
    conn = run_dir / "connectome"
    conn.mkdir()
    np.savez(conn / "relay_loom.npz", trace=np.zeros((2, 10, 5)))
    np.savez(conn / "dnp01_loom.npz", trace=np.zeros((2, 10, 2)))
    try:
        build_verified_premotor_dataset(run_dir)
        assert False, "expected FileNotFoundError"
    except FileNotFoundError:
        pass