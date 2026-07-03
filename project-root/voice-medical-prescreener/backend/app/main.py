"""FastAPI application entry point.

Run from the project root:
    uvicorn backend.app.main:app --reload --port 8000

Serves the JSON API under /api and (once it exists) the static frontend at /.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from backend.app.api.routes_documents import router as documents_router
from backend.app.api.routes_dashboard import router as dashboard_router
from backend.app.api.routes_followup import router as followup_router
from backend.app.api.routes_report import router as report_router
from backend.app.api.routes_risk import router as risk_router
from backend.app.api.routes_transcripts import router as transcripts_router
from backend.app.api.routes_visits import router as visits_router
from backend.app.db.database import init_db

# backend/app/main.py -> parents[2] == project root, then the static portal dirs
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = _PROJECT_ROOT / "frontend"            # patient kiosk (+ legacy transcript app)
FRONTEND_SHARED_DIR = _PROJECT_ROOT / "frontend_shared"
FRONTEND_MEDIC_DIR = _PROJECT_ROOT / "frontend_medic"
FRONTEND_DOCTOR_DIR = _PROJECT_ROOT / "frontend_doctor"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()  # create SQLite tables if missing
    yield


app = FastAPI(title="Voice Medical Pre-Screener", version="0.0.1", lifespan=lifespan)

# API routes are registered BEFORE the catch-all static mount so /api and /health win.
app.include_router(transcripts_router)
app.include_router(documents_router)
app.include_router(visits_router)
app.include_router(followup_router)
app.include_router(risk_router)
app.include_router(dashboard_router)
app.include_router(report_router)


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok"}


# Staff portals + shared assets are mounted BEFORE the catch-all patient mount.
if FRONTEND_SHARED_DIR.is_dir():
    app.mount("/shared", StaticFiles(directory=FRONTEND_SHARED_DIR), name="shared")
if FRONTEND_MEDIC_DIR.is_dir():
    app.mount("/medic", StaticFiles(directory=FRONTEND_MEDIC_DIR, html=True), name="medic")
if FRONTEND_DOCTOR_DIR.is_dir():
    app.mount("/doctor", StaticFiles(directory=FRONTEND_DOCTOR_DIR, html=True), name="doctor")

# Serve the frontend if it has been built (Step 5); otherwise a friendly placeholder.
if FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
else:

    @app.get("/", response_class=HTMLResponse, tags=["meta"])
    def placeholder() -> str:
        return (
            "<h1>Voice Medical Pre-Screener</h1>"
            "<p>Backend is running. The frontend is not built yet (Step 5).</p>"
            "<p>API docs: <a href='/docs'>/docs</a></p>"
        )
