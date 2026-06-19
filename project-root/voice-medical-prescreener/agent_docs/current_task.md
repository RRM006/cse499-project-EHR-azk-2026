# current_task.md — What We Are Doing RIGHT NOW

> This is a small, throwaway snapshot. It gets **overwritten** every session.
> It is NOT a history log (that is `changelog.md`). It answers only:
> "If I open a brand-new Claude Code session, what do I need to know to continue?"

---

**Date:** 2026-06-19
**Phase:** Phase 0 — Quick working demo
**Module:** Module 1 — Speech-to-Text (+ the correction step)

## Where we are right now
The full Phase 0 stack is BUILT and the server runs end to end:
- Steps 1–5 of the 6-step build are done (scaffolding → backend skeleton →
  correction service → API + static serving → frontend).
- Backend: FastAPI `main.py` serves the frontend + JSON API. Endpoints:
  `POST /api/correct`, `GET /api/transcripts`, `/health`, `/docs`.
- Frontend: `frontend/index.html` + `app.js` (Web Speech API `bn-BD`, interim grey
  / final committed verbatim, RAW box, manual fallback) + `styles.css`.
- Correction: `build_corrector()` → Gemini via OpenAI-compatible client (swappable).
- Storage: SQLite; raw stored verbatim, corrected in a separate column.
- Tests: `pytest backend/tests/` = **7 passed**. Server verified rendering via the
  preview tool (no console errors, all assets 200). Live Gemini call NOT yet run.

How the mic works (important): live transcription is 100% browser↔Google (Web
Speech API). Our backend is hit ONLY when the user clicks "Correct" (one Gemini
request per click; free tier ≈ 15/min, ~1,500/day).

## The one thing we are doing next
**Step 6 — end-to-end live test + collect samples (human-driven).**
1. Run the server and open http://localhost:8000 in Chrome/Edge (see run commands
   in Reminders). Needs a valid `GEMINI_API_KEY` in `backend/.env`.
2. Speak Bangla / Banglish / Roman Bangla → confirm RAW appears verbatim, click
   Correct → corrected appears separately, RAW unchanged; check the recent list.
3. Try the manual fallback box too.
4. Start collecting ~50 real sample utterances (the Phase 0 "move on" gate).
5. Record findings (rough latency, does correction preserve meaning?) in test_log.

## Exact next step for Claude Code
Wait for the human to report their live-test results. If they hit issues (mic,
Gemini errors, latency), help debug. If they want automated coverage of
`/api/correct`, propose mocking the corrector (no real network) — plan first.

## Open / optional improvements (discuss, don't assume)
- Add a mocked test for `POST /api/correct` so CI covers the route offline.
- Add run commands to `CLAUDE.md` COMMANDS section (still says TBD).
- `.claude/launch.json` uses the Windows venv path; Arch needs `.venv/bin/python`.

## Reminders
- Raw words are never edited (rule #1). Correction is a separate field/column.
- Plan first, code second, one small step at a time. Do not assume. (CLAUDE.md)
- Synthetic/consented data only — free LLM tiers may train on input (rule #4).
- Run app (Windows): `.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --port 8000`
- Run app (Arch):    `.venv/bin/python -m uvicorn backend.app.main:app --reload --port 8000`
- Run tests:         `pytest backend/tests/`   ·   Python 3.14 needs SQLAlchemy >= 2.0.51.
