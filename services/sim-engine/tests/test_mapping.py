"""Tests for connectome mapping (pure logic, no network)."""
import numpy as np
import pandas as pd

from hawking_fly.connectome.mapping import (
    FLYVIS_RECEPTOR_PROXY,
    ReceptorDrivePlan,
    aggregate_drive,
    build_connectome_grounded_drive_plan,
    build_receptor_drive_plan,
    mapping_provenance,
)


def test_proxy_table_covers_lc4_lplc2():
    assert "LC4" in FLYVIS_RECEPTOR_PROXY
    assert "LPLC2" in FLYVIS_RECEPTOR_PROXY
    for rtype, entry in FLYVIS_RECEPTOR_PROXY.items():
        assert entry["correspondence"] == "proxy"
        assert entry["verified"] is False


def test_build_plan_flags_proxy():
    df = pd.DataFrame(
        [
            {"bodyId": 12032, "type": "LC4", "instance": "LC4_L"},
            {"bodyId": 11498, "type": "LPLC2", "instance": "LPLC2_L"},
        ]
    )
    plan = build_receptor_drive_plan(
        df, available_cell_types={"T4a", "T4b", "T5a", "T5b", "Tm9"}
    )
    types = {p.receptor_type for p in plan}
    assert "LC4" in types
    assert "LPLC2" in types
    for p in plan:
        if p.receptor_type in ("LC4", "LPLC2"):
            assert p.correspondence == "proxy"
            assert p.verified is False
            assert len(p.flyvis_cell_types) > 0


def test_unknown_type_unplanned():
    df = pd.DataFrame([{"bodyId": 99999, "type": "UNKNOWN", "instance": "X"}])
    plan = build_receptor_drive_plan(df, available_cell_types=set())
    assert len(plan) == 1
    assert plan[0].correspondence == "none"
    assert plan[0].flyvis_cell_types == ()


def test_side_inference():
    df = pd.DataFrame(
        [
            {"bodyId": 10001, "type": "DNp01", "instance": "DNp01(GF)_R"},
            {"bodyId": 10010, "type": "DNp01", "instance": "DNp01(GF)_L"},
        ]
    )
    plan = build_receptor_drive_plan(df, available_cell_types=set())
    sides = {p.body_id: p.side for p in plan}
    assert sides[10001] == "R"
    assert sides[10010] == "L"


def test_provenance_has_summary():
    plan = [
        ReceptorDrivePlan(
            receptor_type="LC4",
            body_id=1,
            flyvis_cell_types=("T4a",),
            correspondence="proxy",
            verified=False,
        )
    ]
    prov = mapping_provenance(plan)
    assert prov["summary"]["n_receptors"] == 1
    assert prov["summary"]["n_legacy_proxy"] == 1
    assert prov["summary"]["n_connectome_grounded"] == 0


# ---------------------------------------------------------------------------
# Connectome-grounded plan builder
# ---------------------------------------------------------------------------

class TestConnectomeGroundedPlan:
    """The grounded builder must use MaleCNS synapse evidence, not guess."""

    EVIDENCE = {
        "LC4": pd.DataFrame([
            {"pre_type": "T2",    "total_syn": 46000, "is_self": False},
            {"pre_type": "Tm4",   "total_syn": 31000, "is_self": False},
            {"pre_type": "Tm3",   "total_syn": 17000, "is_self": False},
            {"pre_type": "LC4",   "total_syn": 18000, "is_self": True},
            {"pre_type": "Am1",   "total_syn": 100,   "is_self": False},
        ]),
        "LPLC2": pd.DataFrame([
            {"pre_type": "T5c",   "total_syn": 17000, "is_self": False},
            {"pre_type": "T4a",   "total_syn": 10000, "is_self": False},
            {"pre_type": "LPLC2", "total_syn": 46000, "is_self": True},
            {"pre_type": "PVLP011", "total_syn": 9000, "is_self": False},
        ]),
    }

    RECEPTORS = pd.DataFrame(
        [
            {"bodyId": 10, "type": "LC4",   "instance": "LC4_R"},
            {"bodyId": 20, "type": "LPLC2", "instance": "LPLC2_R"},
        ]
    )

    FLYVIS = {"T2", "Tm4", "Tm3", "T5c", "T4a"}

    def test_grounded_plan_uses_evidence(self):
        plan = build_connectome_grounded_drive_plan(
            self.RECEPTORS, self.EVIDENCE, available_cell_types=self.FLYVIS
        )
        by_type = {p.receptor_type: p for p in plan}
        lc4 = by_type["LC4"]
        lplc2 = by_type["LPLC2"]
        assert lc4.correspondence == "connectome_grounded"
        assert lc4.verified is True
        assert "T2" in lc4.flyvis_cell_types
        assert "Tm3" in lc4.flyvis_cell_types
        assert "Am1" not in lc4.flyvis_cell_types  # too low, below min_synapses
        assert lplc2.verified is True
        assert "T5c" in lplc2.flyvis_cell_types
        # self-feedback and non-flyvis classes excluded
        assert "LC4" not in lc4.flyvis_cell_types
        assert "PVLP011" not in lplc2.flyvis_cell_types

    def test_grounded_plan_weights_are_synapse_counts(self):
        plan = build_connectome_grounded_drive_plan(
            self.RECEPTORS, self.EVIDENCE, available_cell_types=self.FLYVIS,
            min_synapses=0,
        )
        for p in plan:
            if p.flyvis_cell_type_weights:
                # raw synapse counts (normalized to weight proportions at
                # aggregation time in `_weighted_proxy`)
                assert all(w > 0 for w in p.flyvis_cell_type_weights)
                assert len(p.flyvis_cell_type_weights) == len(p.flyvis_cell_types)

    def test_grounded_coverage_positive(self):
        plan = build_connectome_grounded_drive_plan(
            self.RECEPTORS, self.EVIDENCE, available_cell_types=self.FLYVIS
        )
        for p in plan:
            if p.correspondence == "connectome_grounded":
                assert 0.0 < p.coverage <= 1.0

    def test_provenance_grounded(self):
        plan = build_connectome_grounded_drive_plan(
            self.RECEPTORS, self.EVIDENCE, available_cell_types=self.FLYVIS
        )
        prov = mapping_provenance(plan)
        assert prov["summary"]["n_connectome_grounded"] == 2
        assert prov["summary"]["n_legacy_proxy"] == 0
        assert prov["summary"]["avg_coverage"] > 0

    def test_weighted_aggregate_drive(self):
        plan = build_connectome_grounded_drive_plan(
            self.RECEPTORS, self.EVIDENCE, available_cell_types=self.FLYVIS,
            min_synapses=0,
        )
        # fake responses: 1 network, 2 samples, 10 frames, 3 neurons (T2, Tm4, T5c)
        import xarray as xr
        responses = xr.DataArray(
            np.ones((1, 2, 10, 3)),
            dims=("network_id", "sample", "frame", "neuron"),
            coords={"cell_type": ("neuron", ["T2", "Tm4", "T5c"])},
        )
        drive = aggregate_drive(responses, plan)
        assert drive.shape == (2, 10, 2)  # (samples, frames, receptors)
        assert np.all(drive > 0)  # all driven
