"""FlyLab API: physical coding, real anatomy, training and saved evidence.

The hawking_fly import namespace is retained for existing scripts and checkpoints.
"""
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from hawking_fly.api.anatomy import router as anatomy_router
from hawking_fly.api.coding import router as coding_router
from hawking_fly.api.coding_training import router as training_router
from hawking_fly.api.physical_coding import router as physical_coding_router

app = FastAPI(
    title="FlyLab API",
    version="0.1.0",
    description="Contact-driven coding sessions, MaleCNS activity, training and recorded evidence.",
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(anatomy_router)
# FlyLab uses the physical controller; retain the shared recording artifact API.
recording_router = APIRouter()
recording_router.routes.extend(route for route in coding_router.routes if route.path.startswith('/api/coding/record'))
app.include_router(recording_router)
app.include_router(physical_coding_router)
app.include_router(training_router)

@app.get("/api/health")
def health():
    return {"status": "ok", "application": "FlyLab", "mode": "physical-coding",
            "dataset_version": "MaleCNS v1.0"}

def main() -> int:
    import uvicorn
    uvicorn.run("hawking_fly.api.app:app", host="127.0.0.1", port=8050, reload=False)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
