# current_task.md — What We Are Doing RIGHT NOW

> This is a small, throwaway snapshot. It gets **overwritten** every session.
> It is NOT a history log (that is `changelog.md`). It answers only:
> "If I open a brand-new Claude Code session, what do I need to know to continue?"

---

**Date:** 2026-07-07 (Session 14 end)
**Phase:** ✅ **The 20-step fix/feature build is COMPLETE.** There is no next *coded* step in
this plan. The remaining work is the HUMAN live run + any polish it surfaces.

## Where we are right now
- **All 20 steps DONE.** Every numbered item in `context_fixed_problem.md`
  (STRUCT / KIOSK-1..7 / MEDIC-1..7 / DOCTOR-1..7) is ✅. **150 tests pass**
  (`pytest backend/tests/`). Alembic head **0010**. Three portals + landing + `/legacy/`.
- Session 14 (step 20) was a docs-only sweep: re-ran the 150-test gate, flipped the stale
  `context_fixed_problem.md` markers to ✅ (KIOSK-4/5/6/7 + MEDIC-1/2/3/5 from S11,
  DOCTOR-3/4/5/6/7 from S13), and marked the build complete in `milestone_log.md`.
- The **15-module status table** in `milestone_log.md` stays 🟨 on purpose — those modules
  gate on the HUMAN live-voice run recording real numbers, not on build completion.

## The one thing we are doing next
**Hand off to the HUMAN live run — no coded step remains in the 20-step plan.**
👉 The human has a click-by-click checklist in **`agent_docs/human_live_run_guide.md`**
(start the app · install a Bangla TTS voice · the live-test walkthrough · rotate keys).
The human's tasks (unchanged, all still pending):
1. **Live real-mic run** on Chrome: TC-V1 (STT verbatim + WER/latency), **TC-V2** (Bangla TTS
   audio actually plays), **TC-V3** (voice-only reply loop), **TC-F2** (resume loop on real
   speech), **TC-R1** (a red-flag phrase spoken → forced Critical), **TC-A1** (forced provider
   fallback). Real keys are already in `backend/.env` — this run spends quota, so it is the
   human's to trigger (rule #4: no auto-run of live LLM/mic).
2. **Install a Bangla TTS voice on Windows** (Settings → Time & Language → Speech → Add voices →
   Bengali) so kiosk `SpeechSynthesis` has a `bn-BD` voice; then re-check that the KIOSK-2
   `#voice-hint` banner disappears and audio plays.
3. **Rotate the three API keys** in `backend/.env` before any public demo (they were pasted in
   chat during earlier sessions).
When the live run surfaces bugs/polish, that becomes the next build spec (a new
`context_fixed_problem`-style item list) — plan it with the human first, one step per "go".

## Locked decisions from the build (do NOT re-open) — see `decisions.md`
- **C1 (ADR-0036):** AI suggested condition is staff-facing, always disclaimered; the doctor's
  prescription **Diagnosis is NEVER AI-filled** (ADR-0038/0039: the .docx writer reads only the
  submitted payload, so it's structurally un-AI-fillable).
- **C2:** risk "score" = display-only tier→band map (`shared.js` `TIER_BANDS`); no numeric score
  generated/stored/on the wire; docx prints the tier code only.
- **Storage:** prescriptions/reports DB-backed (Alembic **0010**). Prescription = a new
  `prescriptions` row + a linked `documents` row per Submit (ADR-0039).
- **Bilingual values** `{value, value_en, value_bn}` (ADR-0033); tier codes on the wire stay
  `low|medium|high|critical`, labels ONLY in `TIER_LABELS`, bands ONLY in `TIER_BANDS`.
- **Vitals:** `PATCH /patients/{id}/vitals` (weight and/or BP; roles medic/doctor/admin) — reuse.

## Important environment notes
- All three API keys in `backend/.env` (Gemini/Groq/OpenRouter) — **rotate before public demo**.
  Never auto-run live LLM calls (quota + rule #4 synthetic-only).
- Server: port 8001. Entry points: `/` (landing) · `/kiosk.html` · `/medic/` · `/doctor/`
  · `/legacy/`. `.env` changes need a restart. The letterhead seed runs at startup (fills NULLs).
- **DEV_OTP=000000**. Alembic head `0010`; NEVER delete the DB.
- Windows console gotcha: Bangla prints need `PYTHONIOENCODING=utf-8`.
- Browser-cache gotcha: `fetch(url, {cache:'reload'})` + reload the page BEFORE asserting in preview.

## Reminders (the four non-negotiables held throughout the build)
- **Rule #1:** raw words are never edited — verbatim + patient name are re-rendered but never
  translated; export writers reproduce raw byte-exact.
- **Rule #2:** the system never diagnoses — C1 is a labeled, disclaimered suggestion; the
  prescription Diagnosis is doctor-authored and un-AI-fillable.
- **Rule #3:** red flags are ADD-only, each with a TC-R1 test; staff can't hide a red-flag Critical.
- **Rule #4:** no auto-run of live LLM calls; synthetic/offline data only in dev.
- Run (Windows): `.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --port 8001`
- Run (Arch):    `.venv/bin/python -m uvicorn backend.app.main:app --reload --port 8001`
- Tests: `pytest backend/tests/` (**150 passing**).
