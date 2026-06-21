# current_task.md — What We Are Doing RIGHT NOW

> This is a small, throwaway snapshot. It gets **overwritten** every session.
> It is NOT a history log (that is `changelog.md`). It answers only:
> "If I open a brand-new Claude Code session, what do I need to know to continue?"

---

**Date:** 2026-06-21
**Phase:** Phase 0 — Quick working demo (browser-only STT)
**Module:** Module 1 — Speech-to-Text (+ correction step) · plus document export

## Where we are right now
Pipeline: **mic → Chrome Web Speech API → RAW (immutable, stored) → Gemini →
corrected → auto-saved .docx**. Document export was added this session.

- Backend (fastapi 0.115.6): endpoints `POST /api/transcripts` (store raw),
  `POST /api/correct` (by utterance_id; now ALSO best-effort generates a .docx),
  `GET /api/transcripts`, `GET /api/documents` (list), `GET /api/documents/{id}/download`,
  `/health`. Serves the frontend.
- Documents: DB is the source of truth; a .docx is a DERIVED, regenerable artifact.
  New `Document` model (UUID PK, FK → Utterance). `services/documents/` = DocxWriter
  (python-docx, Bangla font) + filesystem storage abstraction + `build_writer()` seam.
  Files saved under a configurable `documents_dir` (default `backend/data/documents/`,
  env-overridable), named by the document UUID.
- Frontend (Mintlify): RAW/Corrected/Manual panels + a "Saved documents (.docx)"
  panel listing docs with download links, auto-refreshed after a correction.
- Tests: `pytest backend/tests/` = **13 passed** (raw_immutable, corrector,
  docx_writer, documents_repo). End-to-end download verified via HTTP this session.

## Important environment notes
- **Server runs on port 8001** (`.claude/launch.json`). Port 8000 has an orphaned
  LISTENING socket from a dead process — clears on reboot, then you can switch back.
- `.env` changes need a server RESTART (uvicorn --reload only watches .py).
- New dep this session: `python-docx==1.1.2` — run `pip install -r requirements.txt`.
- Generated docs + DB are gitignored (`data/`, `*.db`). A synthetic demo doc
  (session #5) was created during verification — harmless.

## The one thing we are doing next
**Human-driven live test (mic + correction + document), and sample collection.**
1. `pip install -r requirements.txt` (gets python-docx), run server on port 8001,
   open http://localhost:8001 in Chrome. GEMINI_API_KEY must be set in backend/.env.
2. Click Start, speak Bangla/Banglish; confirm transcript appends live & verbatim;
   pause briefly (keeps going); go silent ~10s (auto-stops).
3. Click Correct → corrected appears; RAW unchanged; a .docx appears in the
   "Saved documents" panel. Click Download → open in Word/LibreOffice; confirm
   Raw + Corrected + metadata render and **Bangla displays correctly**.
4. Collect ~50 sample utterances; record rough latency + did correction preserve
   meaning + did the doc render correctly, in test_log.md.

## Exact next step for Claude Code
Wait for the human's live-test results, then help debug or log numbers. Optional
follow-ups (any of): add mocked offline tests for the `/api/documents` routes via
TestClient; add a "regenerate document" path; start the PDF writer behind the same
`format` seam.

## Reminders
- Raw words are never edited (rule #1). Correction AND the .docx are derived/separate.
- The .docx is a derived artifact — DB is the source of truth (ADR-0021).
- Synthetic/consented data only — Gemini may log input (rule #4).
- Plan first, one small step at a time. Do not assume. (CLAUDE.md)
- Frontend follows DESIGN-mintlify.md; the 3 transcript panels share the
  fixed-height + scroll + stick-to-bottom behavior (see CLAUDE.md).
- Run (Windows): `.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --port 8001`
- Run (Arch):    `.venv/bin/python -m uvicorn backend.app.main:app --reload --port 8001`
- Tests: `pytest backend/tests/`  ·  Python 3.14 needs SQLAlchemy>=2.0.51.
