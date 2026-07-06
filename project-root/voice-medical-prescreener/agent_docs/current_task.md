# current_task.md — What We Are Doing RIGHT NOW

> This is a small, throwaway snapshot. It gets **overwritten** every session.
> It is NOT a history log (that is `changelog.md`). It answers only:
> "If I open a brand-new Claude Code session, what do I need to know to continue?"

---

**Date:** 2026-07-06 (Session 12 end)
**Phase:** Fix/feature build from the human's Part-2 live test — spec = `agent_docs/context_fixed_problem.md`
**Module:** doctor portal (M14); working through the 20-step approved plan, ONE step per "go"

## Where we are right now
- **Steps 1–16 are DONE.** S12 added: **C1 suggested condition** (step 14, ADR-0036: module
  `M10C` on the Flash bucket, separate from M10; stored in `entities["suggested_condition"]`
  with embedded "not a diagnosis" disclaimers; `PATCH /profile/condition` staff edit; shared
  `renderConditionCard()` — medic mounts it, kiosk never does) · **post-referral summary +
  .docx** (step 15, ADR-0037: snapshot screen after Submit & Forward with weight inline-edit
  via new `PATCH /patients/{id}/vitals`; `GET /visits/{uuid}` embeds the patient
  (`VisitDetailWithPatientOut`); summary_report docx renders the C1 block and is assembled
  from a **fresh report at download time**) · **doctor toggle/polish/↻-removal** (step 16:
  fully bilingual via data-en/bn + `renderSafety()` from state; ↻ Queue deleted; print CSS).
- **139 tests pass** (`pytest backend/tests/`). New suites: `test_suggested_condition.py` (5),
  `test_medic_summary.py` (5).
- ⚠ `preview_screenshot` flaky again late-session — human should eyeball `/medic/` post-referral
  screen (forward a case) and `/doctor/` in বাংলা once (Ctrl+F5 first).
- ⚠ Still open from S10: install a Bangla TTS voice on the Windows box (Settings → Time &
  Language → Speech → Add voices → Bengali) so kiosk TTS actually plays audio.

## Locked decisions for this build (human-approved, do NOT re-open)
- **C1 (ADR-0036):** the suggestion is staff-facing ONLY, always disclaimered (constants live
  in `services/suggestion.py` and travel inside the stored object); the doctor's prescription
  **Diagnosis field is NEVER AI-filled** — step 18 must default it to EMPTY.
- **C2:** risk "score" = display-only tier→band map in `shared.js` (`TIER_BANDS`). No numeric
  scores generated, stored, or on the wire; the docx prints the tier code only.
- **Storage:** prescriptions/reports DB-backed (Alembic **0010**: `prescriptions` table,
  `documents.visit_id`, letterhead columns on clinics/users, patient vitals).
- **Bilingual values:** `{value, value_en, value_bn}` (ADR-0033); staff edits fill all slots
  untranslated — same rule now applies to the condition edit and vitals are language-neutral.
- **KIOSK-7 (ADR-0034)** and **MEDIC-3 (ADR-0035)** mechanics unchanged from S11.
- **MEDIC-7 freshness (ADR-0037):** summary_report docx always regenerates the M12 report so
  staff edits/overrides show; report rows are append-only.

## The one thing we are doing next
**Step 17 — DOCTOR-3: patient-details card** in the doctor portal:
1. Everything it needs is already on the wire: `GET /visits/{uuid}` embeds the patient
   (name/phone/sex/birth_year/weight_kg/bp), risk comes from `GET /risk`, and the C1
   suggestion sits in the profile entities.
2. Build: a patient-details card (Name · Phone · Age from birth_year · Gender · Weight · BP —
   reuse `PATCH /patients/{id}/vitals` if the doctor should edit too) + mount
   `#condition-card` so the shared `renderConditionCard()` shows the AI suggestion + reasoning
   (this also closes part of DOCTOR-7's "AI Suggestion easy to identify").
3. Risk "score" display = `tierBand()` (C2). Bilingual throughout; browser-verify with stubbed
   network; add/extend tests only if backend changes (aim: none needed).
⚠ Frontend-heavy step — a short plan message is enough; wait for "go" before coding
   (session protocol).

**Remaining steps (18–20, one per "go"):** prescription form (18, DOCTOR-4/5 — Diagnosis
EMPTY by default, letterhead from DB, medicine rows add/remove, autofill patient+symptoms) ·
prescription docx + save (19, DOCTOR-6 — `prescriptions` table + documents kind
`prescription`) · final test sweep + doc sweep + context_fixed_problem status flips (20).

## Important environment notes
- All three API keys in `backend/.env` (Gemini/Groq/OpenRouter) — rotate before public demo.
  Never auto-run live LLM calls (quota + rule #4 synthetic-only); S12 verified all frontend
  flows with stubbed fetch and all backend suites with monkeypatched `_attempt`.
- Server: port 8001. Entry points: `/` (landing) · `/kiosk.html` · `/medic/` · `/doctor/`
  · `/legacy/`. `.env` changes need a restart.
- **DEV_OTP=000000**. Alembic head `0010` (no new migration in S11/S12); NEVER delete the DB.
- Windows console gotcha: Bangla prints need `PYTHONIOENCODING=utf-8`.
- Browser-cache gotcha: `fetch(url, {cache:'reload'})` + reload the page BEFORE asserting
  anything in the preview.

## Reminders
- Raw words are never edited (rule #1) — S12 held this: the condition/vitals paths never touch
  utterances; the docx transcript writer is untouched.
- The system never diagnoses (rule #2) — C1 is a labeled, disclaimered suggestion; enforce the
  EMPTY Diagnosis default again in step 18 (it needs its own ADR note when built).
- Red flags: ADD only, each with a TC-R1 test (rule #3); staff can't hide them (ADR-0035).
- Tier codes on the wire stay `low|medium|high|critical`; labels ONLY in `TIER_LABELS`;
  bands ONLY in `TIER_BANDS` (display-only).
- One small step per "go": plan (if backend/design) → diff → `pytest backend/tests/` →
  browser check with stubbed network → doc updates → wait.
- Run (Windows): `.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --port 8001`
- Run (Arch):    `.venv/bin/python -m uvicorn backend.app.main:app --reload --port 8001`
- Tests: `pytest backend/tests/` (**139 passing**).
