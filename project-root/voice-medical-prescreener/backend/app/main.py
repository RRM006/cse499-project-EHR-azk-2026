"""FastAPI application entry point.

Run from the project root:
    uvicorn backend.app.main:app --reload --port 8000

Serves the JSON API under /api and (once it exists) the static frontend at /.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from backend.app.api.routes_assistant import router as assistant_router
from backend.app.api.routes_documents import router as documents_router
from backend.app.api.routes_dashboard import router as dashboard_router
from backend.app.api.routes_followup import router as followup_router
from backend.app.api.routes_prescription import router as prescription_router
from backend.app.api.routes_report import router as report_router
from backend.app.api.routes_risk import router as risk_router
from backend.app.api.routes_transcripts import router as transcripts_router
from backend.app.api.routes_visit_documents import router as visit_documents_router
from backend.app.api.routes_visits import router as visits_router
from backend.app.db.database import SessionLocal, init_db
from backend.app.db.seed import seed_demo_letterhead

# backend/app/main.py -> parents[2] == project root, then the static portal dirs
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = _PROJECT_ROOT / "frontend"            # landing page + patient kiosk
FRONTEND_SHARED_DIR = _PROJECT_ROOT / "frontend_shared"
FRONTEND_MEDIC_DIR = _PROJECT_ROOT / "frontend_medic"
FRONTEND_DOCTOR_DIR = _PROJECT_ROOT / "frontend_doctor"
FRONTEND_LEGACY_DIR = _PROJECT_ROOT / "frontend_legacy"  # Phase-0 transcript demo, isolated

logger = logging.getLogger("uvicorn.error")

# The app entry points this backend serves (STRUCT-2: surfaced at startup).
ENTRY_POINTS = [
    ("Landing page", "/"),
    ("Patient kiosk", "/kiosk.html"),
    ("Medic portal", "/medic/"),
    ("Doctor portal", "/doctor/"),
    ("Legacy Phase-0 demo", "/legacy/"),
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()  # create SQLite tables if missing
    with SessionLocal() as db:  # idempotent demo letterhead (fills NULLs only)
        seed_demo_letterhead(db)
    logger.info("App entry points (relative to the server root, e.g. http://localhost:8001):")
    for name, path in ENTRY_POINTS:
        logger.info("  %-22s %s", name, path)
    yield


app = FastAPI(title="Voice Medical Pre-Screener", version="0.0.1", lifespan=lifespan)

# API routes are registered BEFORE the catch-all static mount so /api and /health win.
app.include_router(transcripts_router)
app.include_router(documents_router)
app.include_router(visits_router)
app.include_router(visit_documents_router)
app.include_router(followup_router)
app.include_router(risk_router)
app.include_router(dashboard_router)
app.include_router(report_router)
app.include_router(prescription_router)
app.include_router(assistant_router)


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

# Legacy Phase-0 transcript demo — isolated at /legacy/ (STRUCT-1). Kept fully
# working (its /api routes are unchanged); only its home moved off the root.
if FRONTEND_LEGACY_DIR.is_dir():
    app.mount("/legacy", StaticFiles(directory=FRONTEND_LEGACY_DIR, html=True), name="legacy")

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
