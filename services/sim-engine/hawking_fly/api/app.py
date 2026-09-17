"""FastAPI application for Phase 0D (replay-based experiment frontend).

Run:
    uvicorn hawking_fly.api.app:app --port 8050
    (or `python -m hawking_fly.api`)

All data is **recorded** (replay mode): responses are served from experiment
run directories without re-running any model. The websocket stream re-emits the
recorded per-frame values at the run's real timestep (dt from config); it is a
genuine temporal stream of recorded frames, not a fake live sim. The UI must
label it "Replay of recorded simulation run".
"""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from hawking_fly.api.replay import (
    RunNotFoundError,
    assemble_provenance,
    communication_decode,
    decoder_results,
    latest_premotor_run,
    list_runs,
    log_test_action,
    overview_channels,
    resolve_run,
    run_metadata,
    session_correlation,
    symbol_set,
    wheelchair_state,
)

app = FastAPI(
    title="The Hawking Fly API",
    version="0.1.0",
    description="Replay API for the MaleCNS-grounded premotor experiment.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

EXPERIMENT = "loom_escape"


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class RunRequest(BaseModel):
    stimulus: str = Field("loom", description="flash | moving_edge | loom")
    sample: int = Field(0, ge=0)
    run_id: str | None = Field(
        None, description="recorded run to replay (default: latest premotor run)"
    )


class StreamConfig(BaseModel):
    stimulus: str = "loom"
    sample: int = 0
    run_id: str | None = None


class TestActionRequest(BaseModel):
    stimulus: str = "loom"
    chosen_symbol: str = "\u00b7"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_or_default(run_id: str | None) -> Any:
    if run_id:
        try:
            return resolve_run(run_id, experiment=EXPERIMENT)
        except RunNotFoundError:
            raise HTTPException(status_code=404, detail=f"run {run_id!r} not found")
    run = latest_premotor_run(EXPERIMENT)
    if run is None:
        raise HTTPException(
            status_code=404,
            detail="no recorded premotor experiment run found under "
            f"{EXPERIMENT!r} — run the propagation pipeline first.",
        )
    return run


def _stimulus_dt_ms(run: Any, stimulus: str) -> float:
    cfg = run_metadata(run).get("config", {})
    for s in cfg.get("stimuli", []):
        if s.get("name") == stimulus:
            return float(s.get("cfg", {}).get("dt", 0.005)) * 1000.0
    return 5.0


# ---------------------------------------------------------------------------
# Health & catalog
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health() -> dict[str, Any]:
    runs = list_runs(EXPERIMENT)
    return {
        "status": "ok",
        "mode": "replay",
        "message": "Replay of recorded simulation runs (no live sim in Phase 0D).",
        "experiment": EXPERIMENT,
        "recorded_runs": len(runs),
        "dataset_version": "MaleCNS v1.0",
    }


@app.get("/api/experiments")
def experiments() -> dict[str, Any]:
    runs = list_runs(EXPERIMENT)
    return {
        "experiment": EXPERIMENT,
        "mode": "replay",
        "runs": [
            {
                "run_id": r.run_id,
                "stimuli": list(r.stimuli),
                "has_premotor": r.has_premotor,
                "has_decoder": r.has_decoder,
            }
            for r in runs
        ],
    }


# ---------------------------------------------------------------------------
# Run metadata
# ---------------------------------------------------------------------------

@app.get("/api/experiments/{run_id}")
def get_run(run_id: str) -> dict[str, Any]:
    run = _resolve_or_default(run_id)
    return run_metadata(run)


@app.get("/api/experiments/{run_id}/provenance")
def get_provenance(run_id: str) -> dict[str, Any]:
    run = _resolve_or_default(run_id)
    return assemble_provenance(run)


@app.get("/api/experiments/{run_id}/decoder")
def get_decoder(run_id: str) -> dict[str, Any]:
    run = _resolve_or_default(run_id)
    results = decoder_results(run)
    if results is None:
        raise HTTPException(
            status_code=404,
            detail="decoder results unavailable for this run.",
        )
    return results


@app.get("/api/experiments/{run_id}/neural")
def get_neural(run_id: str, stimulus: str = "loom", sample: int = 0) -> dict[str, Any]:
    run = _resolve_or_default(run_id)
    if stimulus not in run.stimuli:
        raise HTTPException(
            status_code=404,
            detail=f"stimulus {stimulus!r} not in recorded run {run.run_id}; "
            f"available: {list(run.stimuli)}.",
        )
    dt_ms = _stimulus_dt_ms(run, stimulus)
    channels = overview_channels(run, stimulus, sample=sample)
    return {
        "run_id": run.run_id,
        "stimulus": stimulus,
        "sample": sample,
        "mode": "replay",
        "frame_dt_ms": dt_ms,
        "channels": channels,
    }


# ---------------------------------------------------------------------------
# Phase 0E — designed-UX symbol layer, decoded communication, avatar state,
# and in-session discovery log
# ---------------------------------------------------------------------------

@app.get("/api/experiments/{run_id}/symbols")
def get_symbols(run_id: str) -> dict[str, Any]:
    run = _resolve_or_default(run_id)
    return symbol_set(run)


@app.get("/api/experiments/{run_id}/wheelchair")
def get_wheelchair(run_id: str) -> dict[str, Any]:
    run = _resolve_or_default(run_id)
    return wheelchair_state(run)


@app.get("/api/experiments/{run_id}/communication")
def get_communication(run_id: str, stimulus: str = "loom") -> dict[str, Any]:
    run = _resolve_or_default(run_id)
    if stimulus not in run.stimuli:
        raise HTTPException(
            status_code=404,
            detail=f"stimulus {stimulus!r} not in recorded run {run.run_id}; "
            f"available: {list(run.stimuli)}.",
        )
    return communication_decode(run, stimulus)


@app.post("/api/experiments/{run_id}/test-action")
def post_test_action(run_id: str, req: TestActionRequest) -> dict[str, Any]:
    run = _resolve_or_default(run_id)
    if req.stimulus not in run.stimuli:
        raise HTTPException(
            status_code=404,
            detail=f"stimulus {req.stimulus!r} not in recorded run {run.run_id}; "
            f"available: {list(run.stimuli)}.",
        )
    decoded = communication_decode(run, req.stimulus)
    return log_test_action(
        run_id=run.run_id,
        stimulus=req.stimulus,
        chosen_symbol=req.chosen_symbol,
        chosen_class=decoded["decoded_class"],
        observed={
            "decoded_label": decoded["decoded_label"],
            "symbol": decoded["symbol"],
            "confidence": decoded["confidence"],
        },
    )


@app.get("/api/experiments/{run_id}/test-actions")
def get_test_actions(run_id: str) -> dict[str, Any]:
    run = _resolve_or_default(run_id)
    return session_correlation(run.run_id)


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

@app.post("/api/experiments/run")
def run_experiment(req: RunRequest) -> dict[str, Any]:
    run = _resolve_or_default(req.run_id)
    if req.stimulus not in run.stimuli:
        raise HTTPException(
            status_code=404,
            detail=f"stimulus {req.stimulus!r} not available in {run.run_id}: "
            f"{list(run.stimuli)}.",
        )
    # Replay semantics: we return the recorded run that already contains this
    # stimulus. No model is re-run.
    return {
        "run_id": run.run_id,
        "stimulus": req.stimulus,
        "mode": "replay",
        "sample": req.sample,
        "frame_dt_ms": _stimulus_dt_ms(run, req.stimulus),
        "message": "Replay: loaded recorded run (no live simulation in Phase 0D).",
    }


# ---------------------------------------------------------------------------
# WebSocket — replay stream of recorded frames
# ---------------------------------------------------------------------------

@app.websocket("/api/experiments/{run_id}/stream")
async def stream_run(websocket: WebSocket, run_id: str) -> None:
    await websocket.accept()
    run = _resolve_or_default(run_id)
    cfg: dict[str, Any] = {}
    try:
        req = await websocket.receive_json()
        cfg.update(req)
    except Exception:
        cfg = {}

    stimulus = str(cfg.get("stimulus", "loom"))
    sample = int(cfg.get("sample", 0))
    if stimulus not in run.stimuli:
        await websocket.send_json(
            {"event": "error", "detail": f"stimulus {stimulus!r} not in run"}
        )
        await websocket.close()
        return

    channels = overview_channels(run, stimulus, sample=sample)
    length = min((len(c["values"]) for c in channels), default=0)
    dt_ms = _stimulus_dt_ms(run, stimulus)
    t0 = time.time()

    await websocket.send_json(
        {
            "event": "meta",
            "run_id": run.run_id,
            "stimulus": stimulus,
            "mode": "replay",
            "frame_dt_ms": dt_ms,
            "n_frames": length,
            "channels": [c["key"] for c in channels],
        }
    )

    try:
        for t in range(length):
            frame = {
                "event": "frame",
                "t": t,
                "ms": round(t * dt_ms, 3),
                "values": {
                    c["key"]: c["values"][t] for c in channels if t < len(c["values"])
                },
            }
            await websocket.send_json(frame)
            # honor the recorded timestep (replay pacing)
            await asyncio.sleep(dt_ms / 1000.0)
            # if the client is far behind, don't buffer unboundedly
            if time.time() - t0 > (t * dt_ms / 1000.0 + 2.0):
                t0 = time.time()
    except WebSocketDisconnect:
        return
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    import uvicorn

    uvicorn.run("hawking_fly.api.app:app", host="127.0.0.1", port=8050, reload=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())