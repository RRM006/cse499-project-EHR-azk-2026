# current_task.md — What We Are Doing RIGHT NOW

> This is a small, throwaway snapshot. It gets **overwritten** every session.
> It is NOT a history log (that is `changelog.md`). It answers only:
> "If I open a brand-new Claude Code session, what do I need to know to continue?"

---

**Date:** 2026-07-06 (Session 11 end)
**Phase:** Fix/feature build from the human's Part-2 live test — spec = `agent_docs/context_fixed_problem.md`
**Module:** whole system; working through the 20-step approved plan, ONE step per "go"

## Where we are right now
- **Steps 1–13 are DONE.** S9: legacy `/legacy/` + landing (ADR-0031) · Alembic **0010**
  (ADR-0032) · visit-grain docx seam · `fieldValue()` + `TIER_BANDS` · bilingual values
  (ADR-0033). S10: kiosk OTP UX (KIOSK-1) · per-message 🔊 + no-bn-voice hint (KIOSK-2/3).
  S11: raw-transcript download button (KIOSK-4) · summary card redesign (KIOSK-5) ·
  language-consistent summary (KIOSK-6) · **resume loop** (KIOSK-7, ADR-0034:
  `?scope=fields`, shared cap, asked-once-counts-as-answered, fail-open UI) · medic
  bilingual + polish + Refresh-Queue (MEDIC-1/2/5, staff.js is now fully bilingual and
  shared) · **risk override** (MEDIC-3, ADR-0035: appended `model_provider='human'` row,
  audit-logged, red-flag-Critical downgrade blocked 409; medic risk panel with C2 bands).
- **129 tests pass** (`pytest backend/tests/`). New suites: `test_resume_loop.py` (5),
  `test_risk_override.py` (3).
- ⚠ Screenshot tool was broken in S11 (page fine; verified via eval + a11y snapshot) —
  human should eyeball `/kiosk.html` summary + `/medic/` risk panel once (Ctrl+F5 first).
- ⚠ Still open from S10: install a Bangla TTS voice on the Windows box (Settings → Time &
  Language → Speech → Add voices → Bengali) so kiosk TTS actually plays audio.

## Locked decisions for this build (human-approved, do NOT re-open)
- **C1:** "Possible Condition (AI Suggestion – Not a Diagnosis)" IS allowed — clearly
  labeled, disclaimer, editable by medic/doctor; the doctor's prescription Diagnosis field
  is NEVER AI-filled (rule #2 boundary; needs its ADR when implemented — that is step 14).
- **C2:** Risk "score" = display-only tier→band mapping in `shared.js` (`TIER_BANDS`).
  NO numeric score generated or stored. (Held in S11: the override endpoint accepts tier
  codes only.)
- **Storage:** prescriptions/reports DB-backed (documents.visit_id, kinds, `prescriptions`
  table — Alembic **0010**). Letterhead in DB columns (clinic + doctor).
- **Bilingual values:** `{value, value_en, value_bn}`; `value` mirrors value_en; staff
  edits fill all slots untranslated; readers fall back across slots (ADR-0033).
- **KIOSK-7 mechanics (ADR-0034):** resume scope shares the ONE per-visit
  `followup_max_questions` cap; a field asked once counts as answered ("নেই/জানি না");
  UI is fail-open — the patient can always submit when the loop can't continue.
- **MEDIC-3 (ADR-0035):** staff cannot downgrade a red-flag Critical (409); only the
  doctor's review can. Overrides append rows — AI assessments are never edited.

## The one thing we are doing next
**Step 14 — MEDIC-4 / C1: AI Suggested Condition section**, backend + medic UI:
1. Plan first (this step needs its own ADR — the C1 wording/boundary): where the
   suggestion is generated (likely M10/M11 bucket or a small M-call on the flash bucket),
   where it is stored (suggest: `case_profiles` JSON or a column — decide via plan),
   the exact label "Possible Condition (AI Suggestion – Not a Diagnosis)" + disclaimer,
   and the edit path (medic can edit/replace; store with `source` provenance like the
   10 fields).
2. Hard boundary (rule #2): this NEVER flows into the doctor's prescription Diagnosis
   field (step 18 must default that field to EMPTY).
3. Tests: generation offline-faked, edit path, provenance, and the disclaimer string
   present in every API payload that carries the suggestion.
⚠ Present the plan + options and WAIT for "go" before coding (session protocol).

**Remaining steps (15–20, one per "go"):** post-referral summary + docx download
(15, MEDIC-6/7) · doctor: toggle+polish+remove-↻Queue (16, DOCTOR-1/2/7) ·
patient-details card (17, DOCTOR-3) · prescription form (18, DOCTOR-4/5) ·
prescription docx + save (19, DOCTOR-6) · final test sweep + doc sweep +
context_fixed_problem status flips (20).

## Important environment notes
- All three API keys in `backend/.env` (Gemini/Groq/OpenRouter) — rotate before public
  demo. Never auto-run live LLM calls (quota + rule #4 synthetic-only); S11 verified all
  frontend flows with stubbed fetch.
- Server: port 8001. Entry points: `/` (landing) · `/kiosk.html` · `/medic/` · `/doctor/`
  · `/legacy/`. `.env` changes need a restart.
- **DEV_OTP=000000**. Alembic head `0010` (no new migration in S11); NEVER delete the DB.
- Windows console gotcha: Bangla prints need `PYTHONIOENCODING=utf-8`.
- Browser-cache gotcha (bit us in S10): `fetch(url, {cache:'reload'})` + reload the page
  BEFORE asserting anything in the preview.

## Reminders
- Raw words are never edited (rule #1) — S11 held this: transcript export byte-exact,
  verbatim panel re-renders but never translates, patient 🔊 reads captured words.
- The system never diagnoses (rule #2) — C1 wording is a *suggestion with disclaimer*;
  the doctor's Diagnosis field stays human-only (enforce again in steps 14 and 18).
- Red flags: ADD only, each with a TC-R1 test (rule #3); staff can't hide them (ADR-0035).
- Tier codes on the wire stay `low|medium|high|critical`; labels ONLY in `TIER_LABELS`;
  bands ONLY in `TIER_BANDS` (display-only).
- One small step per "go": plan (if backend/design) → diff → `pytest backend/tests/` →
  browser check with stubbed network → doc updates → wait.
- Run (Windows): `.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --port 8001`
- Run (Arch):    `.venv/bin/python -m uvicorn backend.app.main:app --reload --port 8001`
- Tests: `pytest backend/tests/` (**129 passing**).
