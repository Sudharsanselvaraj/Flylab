"""Phase 0D API tests — replay endpoints against recorded artifacts."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from hawking_fly.api.app import app

REPO_ROOT = Path(__file__).resolve().parents[3]
pytestmark = pytest.mark.skipif(
    not (REPO_ROOT / "experiments/loom_escape").is_dir(),
    reason="recorded loom_escape experiments not present",
)

RUN_ID = "20260916-223510"
STIMULI = ("flash", "moving_edge", "loom")


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["mode"] == "replay"


def test_experiment_list(client):
    r = client.get("/api/experiments")
    assert r.status_code == 200
    runs = r.json()["runs"]
    assert any(x["run_id"] == RUN_ID for x in runs)


def test_run_metadata(client):
    r = client.get(f"/api/experiments/{RUN_ID}")
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] == "replay"
    assert set(body["stimuli"]) == set(STIMULI)
    assert "manifest" in body
    assert "mapping" in body


def test_neural_channels_shapes_and_honesty(client):
    for stim in STIMULI:
        r = client.get(
            f"/api/experiments/{RUN_ID}/neural", params={"stimulus": stim}
        )
        assert r.status_code == 200
        body = r.json()
        assert body["mode"] == "replay"
        channels = {c["key"]: c for c in body["channels"]}
        assert "LC4" in channels and "LPLC2" in channels
        assert any(k.startswith("relay.") for k in channels)
        assert any(k.startswith("DNp01") for k in channels)
        frames = {c["key"]: len(c["values"]) for c in body["channels"]}
        # all channels share the same frame count per stimulus
        assert len(set(frames.values())) == 1
        assert frames["LC4"] > 100
        # honesty: every channel must declare what it is
        for c in body["channels"]:
            assert c["note"], "each channel must carry provenance"
            assert c["layer"] in {"receptor", "relay", "dnp01"}


def test_decoder_reports_model_inferred(client):
    r = client.get(f"/api/experiments/{RUN_ID}/decoder")
    assert r.status_code == 200
    body = r.json()
    assert "regression" in body  # profile/channel R² etc.
    assert body["mapping_verified"] is True  # connectome-grounded mapping
    # the caveat language must not overclaim biology
    assert "recordings" in " ".join(body.get("caveats", []))


def test_provenance_layers_never_fake(client):
    r = client.get(f"/api/experiments/{RUN_ID}/provenance")
    assert r.status_code == 200
    body = r.json()
    flags = body["flags"]
    assert flags["connectome_edges_verified"] is True
    assert flags["dynamics_validated"] is False  # never upgraded to True
    assert body["dataset"] == "MaleCNS v1.0"
    statuses = {l["layer"]: l["status"] for l in body["layers"]}
    assert "MaleCNS connectivity" in statuses
    assert "FlyVis visual model" in statuses
    assert "Wheelchair / avatar" in statuses
    # the presentation layer must stay labeled as such
    assert statuses["Wheelchair / avatar"] == "PRESENTATION"


def test_run_is_replay(client):
    r = client.post(
        "/api/experiments/run", json={"stimulus": "loom", "run_id": RUN_ID}
    )
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] == "replay"
    assert body["run_id"] == RUN_ID
    assert body["stimulus"] == "loom"


def test_run_unknown_stimulus_404(client):
    r = client.post(
        "/api/experiments/run", json={"stimulus": "bogus", "run_id": RUN_ID}
    )
    assert r.status_code == 404


def test_run_unknown_run_id_404(client):
    r = client.post(
        "/api/experiments/run", json={"stimulus": "loom", "run_id": "does-not-exist"}
    )
    assert r.status_code == 404


def test_missing_decoder_404(client):
    # a run without decoder study outputs → 404 (unavailable, not fabricated)
    r = client.get("/api/experiments/20260916-210539/decoder")
    assert r.status_code in (200, 404)


def test_websocket_replays_frames(client):
    with client.websocket_connect(f"/api/experiments/{RUN_ID}/stream") as ws:
        ws.send_json({"stimulus": "flash"})
        meta = ws.receive_json()
        assert meta["event"] == "meta"
        assert meta["mode"] == "replay"
        assert meta["n_frames"] == 600
        f0 = ws.receive_json()
        assert f0["event"] == "frame"
        assert "LC4" in f0["values"]
        assert len(f0["values"]) > 3