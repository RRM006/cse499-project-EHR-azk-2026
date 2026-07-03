# current_task.md — What We Are Doing RIGHT NOW

> This is a small, throwaway snapshot. It gets **overwritten** every session.
> It is NOT a history log (that is `changelog.md`). It answers only:
> "If I open a brand-new Claude Code session, what do I need to know to continue?"

---

**Date:** 2026-07-03 (Session 8c)
**Phase:** Full-stack build — backend + all three portals BUILT; **live pipeline VERIFIED (Part 1)**
**Module:** whole M1–M15 system; next gate = the human real-mic run (Part 2)

## Where we are right now
- The whole reconciled system is built (Session 8) and **the full pipeline now runs LIVE with
  real API keys (Session 8c)**. All three keys are in `backend/.env`: Gemini + **Groq +
  OpenRouter** (key gap closed).
- **Live-run Part 1 PASSED** with synthetic typed Banglish: lookup → OTP `000000` → visit →
  utterances → intake → follow-up loop (real Bangla Groq questions, exit at 0.7) → assess
  (medium, no red flags) → report. `module_events`: 13 rows, all ok, zero fallbacks, providers
  exactly per ADR-0026 (M3/M8 flash-lite, M4/M10/M11 flash, M6/M7 groq, M12 local).
  Details + numbers: test_log.md 2026-07-03 Session 8c.
- **Tests: 104 passing** (`pytest backend/tests/`).

## The one thing we are doing next
**Part 2 — the HUMAN real-microphone kiosk run in Chrome** (I cannot do this; it needs a voice):
1. Start the server (port 8001), open `http://localhost:8001/kiosk.html`.
2. Phone → any BD mobile → OTP `000000` → speak a Bangla complaint → answer the follow-up
   questions by voice → check the 10-field summary → Confirm & Submit → watch the auto-logout.
3. Open `/medic/` → login → case in queue WITH risk badge → edit a field → Assign Doctor →
   Submit & Forward.
4. Open `/doctor/` → login as that doctor → check risk/red-flags/XAI panel → Accept & Write to
   EHR (or Override to Low-Risk).
5. Record in `test_log.md`: TC-V2 (bn-BD TTS voice available per OS?), TC-V3 (voice-only loop),
   TC-F2 (loop exits, no repeats), TC-R1 (say "বুকে ব্যথা" → tier must be Critical),
   TC-A1 (pull a key → fallback provider logged in `module_events`).

**After that:** per-visit report `.docx` export (M12 → the existing DocxWriter/documents seam),
then optional PDF, then Phase-1 faster-whisper.

## Important environment notes
- **All three API keys are now set** in `backend/.env` (Gemini, Groq, OpenRouter). ⚠ The keys
  were pasted in chat this session — rotate them before any public demo. `.env` is gitignored.
- Free tiers: Gemini ~1,500/day, Groq ~1,000/day, OpenRouter `:free` ~50/day (a $10 top-up
  raises it to 1,000/day). Never auto-run live LLM calls (quota + rule #4 synthetic-only).
- Server: port 8001. Windows launch config `backend (FastAPI + uvicorn)`; Arch `backend-linux`.
  `.env` changes need a restart.
- Windows console gotcha: printing Bangla from a script needs `PYTHONIOENCODING=utf-8`.
- **DEV_OTP=000000** (stub — no SMS). Patient phone lives in `patients.external_ref`.
- Alembic migrates at startup (head `0009`); NEVER delete the DB. Pre-migration backups:
  `backend/prescreener.db.pre-000{3,4,5,6,7}.bak` (gitignored).
- Tier codes on the wire are always low/medium/high/critical; labels (incl. "Moderate", Bangla)
  live ONLY in `frontend_shared/shared.js` TIER_LABELS.

## Reminders
- Raw words are never edited (rule #1) — staff edits touch only `summary_fields` (source
  becomes 'human'; M8 never overwrites human fields). The system never diagnoses (rule #2).
- Red flags: rule list in `backend/app/services/red_flags.py` — ADD phrases only, each with a
  matching TC-R1 test case; the rule must always be able to force Critical (rule #3).
- Plan first, one small step at a time (CLAUDE.md).
- Run (Windows): `.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --port 8001`
- Run (Arch):    `.venv/bin/python -m uvicorn backend.app.main:app --reload --port 8001`
- Tests: `pytest backend/tests/` (**104 passing**).
