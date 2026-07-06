# current_task.md — What We Are Doing RIGHT NOW

> This is a small, throwaway snapshot. It gets **overwritten** every session.
> It is NOT a history log (that is `changelog.md`). It answers only:
> "If I open a brand-new Claude Code session, what do I need to know to continue?"

---

**Date:** 2026-07-06 (Session 13 end)
**Phase:** Fix/feature build from the human's Part-2 live test — spec = `agent_docs/context_fixed_problem.md`
**Module:** doctor portal (M14); working through the 20-step approved plan, ONE step per "go"

## Where we are right now
- **Steps 1–19 are DONE.** S13 landed step 17 (DOCTOR-3 patient-details), step 18 (DOCTOR-4/5
  prescription form, ADR-0038), and **Step 19 (DOCTOR-6, ADR-0039):** prescription **Submit
  saves + downloads**. `render_prescription(payload)` (LOCAL .docx) + `generate_prescription_
  document()` persist a `prescriptions` row + a linked `documents` row (kind `prescription`);
  `POST /api/visits/{uuid}/prescription` (`{doctor_id, payload}`) audits `prescription.created`
  and returns `{prescription_id, document}`; the form's Submit POSTs, auto-downloads the .docx,
  and shows a "✅ Saved & Downloaded" confirmation. A **new** prescription per Submit (append).
  The .docx writer reads ONLY the payload → Diagnosis structurally un-AI-fillable (rule #2).
- **150 tests pass** (`pytest backend/tests/`; +6 context, +5 docx).
- ⚠ Human eyeball still worth doing on `/doctor/` (Ctrl+F5 first): patient-details card + the
  full **Prescription** flow (open → fill → Generate → the .docx downloads) in EN + বাংলা.
  S13 verified via stubbed-network eval + a11y + screenshots + one real end-to-end POST/curl,
  but not through the real UI against an assigned case.
- ⚠ The letterhead seed runs at server startup only (fills NULLs). On the other machine it
  seeds on first launch.
- ⚠ Still open from S10: install a Bangla TTS voice on the Windows box (Settings → Time &
  Language → Speech → Add voices → Bengali) so kiosk TTS actually plays audio.

## Locked decisions for this build (human-approved, do NOT re-open)
- **C1 (ADR-0036):** the suggestion is staff-facing ONLY, always disclaimered; the doctor's
  prescription **Diagnosis field is NEVER AI-filled** — step 18 must default it to EMPTY.
- **C2:** risk "score" = display-only tier→band map in `shared.js` (`TIER_BANDS`). No numeric
  scores generated, stored, or on the wire; the docx prints the tier code only.
- **Storage:** prescriptions/reports DB-backed (Alembic **0010**: `prescriptions` table,
  `documents.visit_id`, letterhead columns on clinics/users, patient vitals).
- **Bilingual values:** `{value, value_en, value_bn}` (ADR-0033); staff edits fill all slots
  untranslated. Vitals (weight/BP) are language-neutral.
- **Vitals edit endpoint:** `PATCH /patients/{id}/vitals` accepts weight and/or BP, allows
  roles medic/doctor/admin (403 otherwise), 422 on out-of-range weight — reuse it, don't fork it.
- **KIOSK-7 (ADR-0034)**, **MEDIC-3 (ADR-0035)**, **MEDIC-4/6/7 (ADR-0036/0037)** unchanged.

## The one thing we are doing next
**Step 20 (FINAL) — test sweep + doc sweep + status flips**, closing the 20-step build:
1. Run the full `pytest backend/tests/` (expect **150 pass**) as the final gate.
2. In `context_fixed_problem.md`, flip the now-complete items to done: **DOCTOR-3** (patient-
   details, S13), **DOCTOR-4/5** (prescription form, S13), **DOCTOR-6** (prescription .docx +
   save, S13), and **DOCTOR-7** (its four "easy to identify" targets — Risk, AI Suggestion,
   Diagnosis, Prescription — are all now present). Re-check any still-open KIOSK/MEDIC/STRUCT
   items and flip the ones the build satisfied; leave anything gated on the human live-voice
   run marked as such.
3. Doc sweep: confirm `changelog.md` / `milestone_log.md` / `decisions.md` / `codebase_map.md`
   all agree (test count 150, ADR-0038/0039, new files). Note the remaining human tasks:
   the live real-mic run + a Bangla TTS voice on Windows.
⚠ Mostly a docs/status step + one test run — a short confirmation, then "go".

**After step 20** the reconciled fix/feature build from the Part-2 spec is fully implemented;
what's left for the project overall is the HUMAN live run (real keys already in `.env`, real
mic) and any polish it surfaces.

## Important environment notes
- All three API keys in `backend/.env` (Gemini/Groq/OpenRouter) — rotate before public demo.
  Never auto-run live LLM calls (quota + rule #4 synthetic-only); verify frontend flows with
  stubbed fetch and backend suites with monkeypatched `_attempt`.
- Server: port 8001. Entry points: `/` (landing) · `/kiosk.html` · `/medic/` · `/doctor/`
  · `/legacy/`. `.env` changes need a restart.
- **DEV_OTP=000000**. Alembic head `0010` (no new migration since S9); NEVER delete the DB.
- Windows console gotcha: Bangla prints need `PYTHONIOENCODING=utf-8`.
- Browser-cache gotcha: `fetch(url, {cache:'reload'})` + reload the page BEFORE asserting
  anything in the preview.

## Reminders
- Raw words are never edited (rule #1) — S13 held this: the patient-details/vitals paths never
  touch utterances; verbatim + patient name are re-rendered but never translated.
- The system never diagnoses (rule #2) — C1 is a labeled, disclaimered suggestion; enforce the
  EMPTY Diagnosis default in step 18 (it needs its own ADR note when built).
- Red flags: ADD only, each with a TC-R1 test (rule #3); staff can't hide them (ADR-0035).
- Tier codes on the wire stay `low|medium|high|critical`; labels ONLY in `TIER_LABELS`;
  bands ONLY in `TIER_BANDS` (display-only).
- One small step per "go": plan (if backend/design) → diff → `pytest backend/tests/` →
  browser check with stubbed network → doc updates → wait.
- Run (Windows): `.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --port 8001`
- Run (Arch):    `.venv/bin/python -m uvicorn backend.app.main:app --reload --port 8001`
- Tests: `pytest backend/tests/` (**150 passing**).
