"""Tests for connectome mapping (pure logic, no network)."""
import pandas as pd

from hawking_fly.connectome.mapping import (
    FLYVIS_RECEPTOR_PROXY,
    ReceptorDrivePlan,
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
    plan = build_receptor_drive_plan(df, available_cell_types={"T4a", "T4b", "T5a"})
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
    assert prov["summary"]["n_proxy_unverified"] == 1
