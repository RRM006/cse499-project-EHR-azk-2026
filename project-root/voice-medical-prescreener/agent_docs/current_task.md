# current_task.md — What We Are Doing RIGHT NOW

> This is a small, throwaway snapshot. It gets **overwritten** every session.
> It is NOT a history log (that is `changelog.md`). It answers only:
> "If I open a brand-new Claude Code session, what do I need to know to continue?"

---

**Date:** 2026-06-20
**Phase:** Phase 0 — Quick working demo (browser-only STT)
**Module:** Module 1 — Speech-to-Text (+ the correction step)

## Where we are right now
Module 1 is now **simplified to ONE STT path: the browser Web Speech API**
(Chrome/Edge, `bn-BD`). The multi-provider architecture was removed. Pipeline:
**mic → Chrome Web Speech API → RAW (immutable, stored) → Gemini → corrected.**

- Backend (clean core, fastapi 0.115.6): endpoints `POST /api/transcripts` (store
  raw), `POST /api/correct` (by utterance_id), `GET /api/transcripts`, `/health`.
  Serves the frontend. `services/correction/` (Gemini) unchanged. The
  `Utterance.stt_provider` column stays as a clean seam for future providers.
- Frontend (Mintlify-styled per DESIGN-mintlify.md): continuous recording — Start/
  Stop, ● Recording, count-up MM:SS (no cap), append-only verbatim transcript,
  brief pauses keep going (restart on `onend`), auto-stop after ~10s of silence.
  Raw/Corrected/Manual panels are fixed-height, scrollable, with stick-to-bottom
  auto-scroll. Manual fallback kept.
- Tests: `pytest backend/tests/` = **7 passed** (test_raw_immutable + test_corrector;
  registry test removed). UI verified live (fonts, pill buttons, scroll behavior,
  mobile no-overflow); one store→correct round-trip worked end to end.

## Important environment notes
- **Server now runs on port 8001** (`.claude/launch.json`). Port 8000 has an
  orphaned LISTENING socket from a dead process — it clears on reboot, after which
  you can switch launch.json back to 8000 if you want.
- `.env` changes need a server RESTART (uvicorn --reload only watches .py).
- Fonts load from Google Fonts CDN (Inter + Noto Sans Bengali) with system
  fallbacks — fine offline, just falls back to system fonts.

## The one thing we are doing next
**Human-driven live mic test + sample collection.**
1. Run server (port 8001), open http://localhost:8001 in Chrome. GEMINI_API_KEY
   must be set in backend/.env.
2. Click Start, speak Bangla/Banglish/Roman Bangla; confirm the transcript appends
   live and verbatim; PAUSE briefly and keep talking (should NOT stop); then go
   SILENT ~10s and confirm it auto-stops.
3. Click Correct → corrected appears in its panel; RAW unchanged.
4. Collect ~50 sample utterances; record rough latency + did correction preserve
   meaning, in test_log.md.

## Exact next step for Claude Code
Wait for the human's live-test results, then help debug or log numbers. Optional:
add mocked offline tests for `POST /api/transcripts` and `/api/correct` so CI
covers the routes without the network.

## Reminders
- Raw words are never edited (rule #1). Correction is a separate field/column.
- Synthetic/consented data only — Gemini may log input (rule #4).
- Plan first, one small step at a time. Do not assume. (CLAUDE.md)
- Frontend follows DESIGN-mintlify.md; the 3 transcript panels share the
  fixed-height + scroll + stick-to-bottom behavior (see CLAUDE.md).
- Run (Windows): `.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --port 8001`
- Run (Arch):    `.venv/bin/python -m uvicorn backend.app.main:app --reload --port 8001`
- Tests: `pytest backend/tests/`  ·  Python 3.14 needs SQLAlchemy>=2.0.51.
