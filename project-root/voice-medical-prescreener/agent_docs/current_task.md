# current_task.md — What We Are Doing RIGHT NOW

> This is a small, throwaway snapshot. It gets **overwritten** every session.
> It is NOT a history log (that is `changelog.md`). It answers only:
> "If I open a brand-new Claude Code session, what do I need to know to continue?"

---

**Date:** 2026-06-21
**Phase:** Phase 0 — Quick working demo (browser-only STT)
**Module:** Module 1 — Speech-to-Text (+ correction step) · plus two-file document export

## Where we are right now
Pipeline: **mic → Chrome Web Speech API → RAW (immutable, stored) → raw .docx on Stop →
Gemini correct → corrected .docx**. Two SEPARATE, independently downloadable Word files now.
The DB schema is managed by **Alembic** (migrations run automatically at startup).

- DB bug FIXED: `utterances` was missing `stt_provider` (the old create_all never altered
  existing tables). Alembic now owns the schema: `0001_baseline` + `0002` (adds
  `stt_provider` + `documents.kind`). Migrations auto-run on startup; legacy DBs are
  baseline-stamped then upgraded; data is preserved (the real DB's 2 rows survived).
  Pre-migration backup: `backend/data/prescreener.db.pre-alembic.bak`.
- Backend (fastapi 0.115.6, alembic 1.14.0): `POST /api/transcripts` (store raw),
  `GET /api/transcripts` (list), `GET /api/transcripts/{id}` (raw+corrected + both doc links),
  `POST /api/transcripts/{id}/documents/raw`, `…/documents/corrected`, `POST /api/correct`
  (corrects by id + best-effort makes the corrected .docx), `GET /api/documents` (+ /download),
  `/health`. Serves the frontend.
- Documents: DB is the source of truth; each .docx is a DERIVED, regenerable artifact.
  `documents.kind` = "raw" | "corrected". `DocxWriter.render(utterance, *, kind)` renders ONE
  side. Files under configurable `documents_dir` (env `DOCUMENT_OUTPUT_PATH`, legacy
  `DOCUMENTS_DIR`; default `backend/data/documents/`), named by UUID.
- Frontend (Mintlify): raw saved + raw .docx generated when recording STOPS; per-panel
  "Download Raw/Corrected .docx" buttons; loading states + spec error strings.
- Tests: `pytest backend/tests/` = **19 passed** (raw_immutable 3, corrector 4, docx_writer 5,
  documents_repo 4, migration 2, routes_documents 2). Manual-text → raw .docx download
  verified end-to-end in the browser (real 36 KB Word file).

## Important environment notes
- **Server runs on port 8001.** `.claude/launch.json` now has TWO configs: Windows
  (`backend (FastAPI + uvicorn)`, `.venv/Scripts/python.exe`) and Linux
  (`backend-linux (FastAPI + uvicorn)`, `.venv/bin/python`). Pick the one for your OS.
  - ⚠ **Preview gotcha (Arch):** `preview_start` / the preview panel DEFAULTS to the first
    (Windows) config and fails with `spawn .venv/Scripts/python.exe ENOENT`. On Linux, start
    the **`backend-linux`** config by name, or just run uvicorn directly (Arch command below).
- New dep this session: `alembic==1.14.0` — run `pip install -r requirements.txt`.
- `.env` changes need a server RESTART (uvicorn --reload only watches .py).
- Schema changes are applied by Alembic automatically at startup — **never delete the DB.**
  Manual equivalents: existing DB `alembic -c backend/alembic.ini stamp 0001_baseline &&
  alembic -c backend/alembic.ini upgrade head`; fresh DB `alembic -c backend/alembic.ini upgrade head`.
- Generated docs + DB are gitignored (`data/`, `*.db`). A synthetic session #3 raw doc was
  created during this session's verification — harmless.

## The one thing we are doing next
**Human-driven live test (mic + two-file export + correction), and sample collection.**
1. `pip install -r requirements.txt` (gets alembic), run server on port 8001, open
   http://localhost:8001 in Chrome. GEMINI_API_KEY must be set in backend/.env.
2. Click Start, speak Bangla/Banglish; confirm transcript appends live & verbatim; pause
   briefly (keeps going); go silent ~10s OR click Stop → confirm a **Raw .docx** is saved and
   the "Download Raw .docx" button enables; download + open it (title "Transcript", Bangla
   renders correctly).
3. Click "Correct with Gemini" → corrected text appears; RAW unchanged; a **Corrected .docx**
   is generated and its download button enables; open it (title "Corrected Transcript").
   Confirm both files download independently and both show in "Saved documents" with kind.
4. Collect ~50 sample utterances; record rough latency + did correction preserve meaning +
   did both docs render correctly (esp. Bangla), in test_log.md.

## Exact next step for Claude Code
Wait for the human's live-test results, then help debug or log numbers. Optional follow-ups:
make the preview launch OS-robust (e.g. make `backend-linux` the first config on this
machine so the preview panel's default works); PDF or Markdown writer behind the existing
`format` seam; a "regenerate document" / version list in the UI; auth on the document routes.

## Reminders
- Raw words are never edited (rule #1). Correction AND both .docx files are derived/separate.
- The .docx is a derived artifact — DB is the source of truth (ADR-0021/0023).
- Schema = Alembic; do not delete the DB; add new columns via a new migration (ADR-0022).
- Synthetic/consented data only — Gemini may log input (rule #4).
- Plan first, one small step at a time. Do not assume. (CLAUDE.md)
- Frontend follows DESIGN-mintlify.md; the 3 transcript panels share the
  fixed-height + scroll + stick-to-bottom behavior (see CLAUDE.md).
- Run (Windows): `.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --port 8001`
- Run (Arch):    `.venv/bin/python -m uvicorn backend.app.main:app --reload --port 8001`
- Tests: `pytest backend/tests/`  ·  Python 3.14 needs SQLAlchemy>=2.0.51.
