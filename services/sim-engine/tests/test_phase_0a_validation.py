"""Phase 0A validation tests — pure artifact math, no flyvis inference."""

from __future__ import annotations

import json

import numpy as np
import pytest

from hawking_fly.sensory.validation import (
    _cell_type_norms,
    _load_readout_plan,
    _sanity_metrics,
    phase_0a_validation,
)

LABELS = ["T2", "TmY3", "Tm4", "Tm2", "T5", "T2", "Mi1", "Tm5Y"]


def _responses_like(run_dir, n_samples=2, frames=40):
    """Write synthetic but shape-realistic *responses.npz per stimulus."""
    rng = np.random.default_rng(0)
    for name in ("flash", "moving_edge", "loom"):
        arr = rng.normal(0, 1, size=(1, n_samples, frames, len(LABELS)))
        np.savez(run_dir / f"{name}_responses.npz", responses=arr)
    # loom intentionally driven harder to make it maximal
    arr = np.load(run_dir / "loom_responses.npz")["responses"]
    arr = arr + 2.0
    np.savez(run_dir / "loom_responses.npz", responses=arr)


def _mapping(run_dir):
    rows = [
        {
            "receptor_type": "LC4",
            "body_id": 100 + i,
            "flyvis_cell_types": ["T2", "TmY3", "Tm4"],
            "flyvis_cell_type_weights": [100.0, 80.0, 60.0],
            "correspondence": "connectome_grounded",
            "verified": True,
        }
        for i in range(3)
    ]
    (run_dir / "connectome").mkdir(parents=True, exist_ok=True)
    (run_dir / "connectome" / "mapping.json").write_text(
        json.dumps(
            {
                "receptor_drive_mapping": rows,
                "summary": {"n_receptors": 3, "avg_coverage": 0.6},
            }
        )
    )


@pytest.fixture()
def run_dir(tmp_path):
    _responses_like(tmp_path)
    _mapping(tmp_path)
    return tmp_path


def test_sanity_metrics_finite_and_distinct(run_dir):
    resp = {
        name: np.load(run_dir / f"{name}_responses.npz")["responses"]
        for name in ("flash", "moving_edge", "loom")
    }
    metrics = _sanity_metrics(resp)
    for name in resp:
        assert metrics[name]["finite"] is True
        assert metrics[name]["mean_abs_response"] > 0
    pair = metrics["pairwise_trace_mse"]
    assert all(v > 0 for v in pair.values())


def test_cell_type_norms_aligns_columns(run_dir):
    resp = {
        name: np.load(run_dir / f"{name}_responses.npz")["responses"]
        for name in ("flash", "moving_edge", "loom")
    }
    per = _cell_type_norms(resp, LABELS)
    assert per["loom"]["T2"] > per["flash"]["T2"]
    assert "__all_columns__" in per["loom"]


def test_cell_type_norms_rejects_mismatched_columns(run_dir):
    resp = {
        name: np.load(run_dir / f"{name}_responses.npz")["responses"]
        for name in ("flash", "moving_edge", "loom")
    }
    resp = {k: v[..., :3] for k, v in resp.items()}  # 3 columns vs 8 labels
    with pytest.raises(ValueError):
        _cell_type_norms(resp, LABELS)


def test_readout_plan_reads_grounded_weights(run_dir):
    plan = _load_readout_plan(run_dir / "connectome" / "mapping.json")
    assert plan["n_receptors"] == 3
    assert plan["class_weight"]["T2"] > plan["class_weight"]["Tm4"]
    assert "note" in plan["summary_note"] or plan["summary_note"] == ""


def test_phase_0a_validation_writes_honest_report(run_dir, tmp_path):
    out = phase_0a_validation(run_dir, tmp_path / "out", labels=LABELS)
    report = json.loads((out / "validation.json").read_text())
    assert report["stage"].startswith("Phase 0A")
    assert report["no_decoder_claims"]
    # loom maximal under the synthetic fixture (loom + 2.0)
    assert report["readout"]["loom_maximal"] is True
    assert report["readout"]["drive_ordering"][0] == "loom"
    assert report["limitations"]  # honesty invariants present
    # nothing claims dynamics validated
    assert "dynamics_validated=false" in report["no_decoder_claims"]
    labels_out = json.loads((out / "cell_type_labels.json").read_text())
    assert labels_out["cell_types"] == LABELS


def test_phase_0a_validation_reports_when_loom_not_maximal(run_dir, tmp_path):
    # make flash dominate instead — validation must report, not fabricate
    arr = np.load(run_dir / "flash_responses.npz")["responses"]
    np.savez(run_dir / "flash_responses.npz", responses=arr + 5.0)
    out = phase_0a_validation(run_dir, tmp_path / "out2", labels=LABELS)
    report = json.loads((out / "validation.json").read_text())
    assert report["readout"]["loom_maximal"] is False
    assert report["readout"]["drive_ordering"][0] == "flash"