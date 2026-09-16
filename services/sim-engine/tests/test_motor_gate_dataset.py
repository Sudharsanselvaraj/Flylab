"""Tests for the Phase 0B paired-dataset builder (no decoder, spec §8 labels)."""
import json
from pathlib import Path

import numpy as np

from hawking_fly.motor_gate.dataset import (
    PAIRED_MANIFEST,
    PAIRED_NPZ,
    build_paired_dataset,
)


def _fake_run(run_dir: Path) -> None:
    import pandas as pd

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