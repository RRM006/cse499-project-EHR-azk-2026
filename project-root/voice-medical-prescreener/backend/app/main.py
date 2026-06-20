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

from backend.app.api.routes_transcripts import router as transcripts_router
from backend.app.db.database import init_db

# backend/app/main.py -> parents[2] == project root, then /frontend
FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()  # create SQLite tables if missing
    yield


app = FastAPI(title="Voice Medical Pre-Screener", version="0.0.1", lifespan=lifespan)

# API routes are registered BEFORE the catch-all static mount so /api and /health win.
app.include_router(transcripts_router)


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok"}


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
