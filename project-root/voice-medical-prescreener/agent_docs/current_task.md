# current_task.md — What We Are Doing RIGHT NOW

> This is a small, throwaway snapshot. It gets **overwritten** every session.
> It is NOT a history log (that is `changelog.md`). It answers only:
> "If I open a brand-new Claude Code session, what do I need to know to continue?"

---

**Date:** 2026-07-07 (Session 17 end)
**Phase:** ✅ Build complete (20/20) + Arch TTS verified + **quota-aware free-provider switching
landed (ADR-0041, 156 tests pass)**. Next work = collect the human's **bug list +
faculty-requirement features**, turn them into a numbered spec, and plan step 1.
The full HUMAN live run also still remains.

## Where we are right now
- **All 20 build steps DONE** (`context_fixed_problem.md` all ✅). Alembic head **0010**.
  Three portals + landing + `/legacy/`. **156 tests pass** (`pytest backend/tests/`).
- **Session 17 (ADR-0041):** fixed "voice transcribes but formatting fails". `llm_client.py`
  now logs EVERY provider attempt to `module_events` and puts a provider on cooldown after a
  429/quota error (60s RPM / 15min daily; fail-open); fallback chain is now
  assigned → **Groq → Cerebras → Mistral → OpenRouter** (blank keys auto-skipped).
  Optional free buckets: `CEREBRAS_API_KEY` (recommended, ~1M tok/day),
  `MISTRAL_API_KEY` (⚠ trains on inputs — rule #4, leave blank for patient use).
  **Server restart needed** for the change to load.
- **Arch TTS = DONE** (S16, ADR-0040). The 15-module table stays 🟨 on purpose — gates on the
  human live-voice run with real numbers.

## The one thing we are doing next
**Collect and plan the next work items — DO NOT start coding until the list is written & agreed.**
👉 STEP 1 (next session): ask the human to enumerate (a) the **bugs** they hit and (b) the **new
   features from faculty requirements**. Capture them as a numbered spec in the
   `context_fixed_problem.md` style (one checkable item each), get the human's sign-off, then plan
   the first item — small, reviewable, one step per "go" (CLAUDE.md working rules).

## Human's own to-do list (given step-by-step at end of S17)
1. **Restart the server** (loads the ADR-0041 switching).
2. Optional: sign up at cloud.cerebras.ai → add `CEREBRAS_API_KEY=` to `backend/.env` → restart.
3. **Live real-mic run** on Chrome/Chromium per `agent_docs/human_live_run_guide.md`:
   TC-V1 (WER+latency), TC-V3 (voice-only loop), TC-F2 (resume), TC-R1 (red flag → Critical),
   TC-A1 (provider fallback — the new per-attempt logging will now show the real errors).
4. **Windows Bangla voice**: Settings → Time & Language → Speech → Add voices → Bengali.
5. **Rotate the three API keys** in `backend/.env` before any public demo.
6. Write the **bug list + faculty-requirement features** for next session.

## Locked decisions from the build (do NOT re-open) — see `decisions.md`
- **C1 (ADR-0036):** AI suggested condition is staff-facing, always disclaimered; the doctor's
  prescription **Diagnosis is NEVER AI-filled** (ADR-0038/0039).
- **C2:** risk "score" = display-only tier→band map (`shared.js` `TIER_BANDS`); tier codes on the
  wire stay `low|medium|high|critical`; labels ONLY in `TIER_LABELS`.
- **Storage:** prescriptions/reports DB-backed (Alembic **0010**, ADR-0039).
- **Bilingual values** `{value, value_en, value_bn}` (ADR-0033).
- **ADR-0041:** quota-aware cooldown + extended free fallback chain; Gemini buckets are NOT
  cross-fallbacks (they hold the quality-task quota); OpenRouter stays LAST (only ~50 free/day).

## Important environment notes
- All three API keys in `backend/.env` (Gemini/Groq/OpenRouter) — **rotate before public demo**.
  Never auto-run live LLM calls (quota + rule #4 synthetic-only).
- Free-tier reality (researched S17): Gemini Flash ≈10 RPM/1,500 RPD (resets midnight PT);
  Flash-Lite higher RPM; Groq ≈1,000 RPD (midnight UTC); OpenRouter `:free` ≈50 RPD.
- Server: port 8001. Entry points: `/` · `/kiosk.html` · `/medic/` · `/doctor/` · `/legacy/`.
  `.env` changes need a restart. **DEV_OTP=000000**. Alembic head `0010`; NEVER delete the DB.
- Windows console gotcha: Bangla prints need `PYTHONIOENCODING=utf-8`.
- Browser-cache gotcha: `fetch(url, {cache:'reload'})` + reload the page BEFORE asserting in preview.

## Reminders (the four non-negotiables held throughout the build)
- **Rule #1:** raw words are never edited — export writers reproduce raw byte-exact.
- **Rule #2:** the system never diagnoses — prescription Diagnosis is doctor-authored.
- **Rule #3:** red flags are ADD-only; staff can't hide a red-flag Critical.
- **Rule #4:** no auto-run of live LLM calls; synthetic/offline data only in dev — this is also
  why `MISTRAL_API_KEY` stays blank (its free tier trains on inputs).
- Run (Windows): `.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --port 8001`
- Run (Arch):    `.venv/bin/python -m uvicorn backend.app.main:app --reload --port 8001`
- Tests: `pytest backend/tests/` (**156 passing**).
