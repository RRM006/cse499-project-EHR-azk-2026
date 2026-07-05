# current_task.md — What We Are Doing RIGHT NOW

> This is a small, throwaway snapshot. It gets **overwritten** every session.
> It is NOT a history log (that is `changelog.md`). It answers only:
> "If I open a brand-new Claude Code session, what do I need to know to continue?"

---

**Date:** 2026-07-05 (Session 9)
**Phase:** Fix/feature build from the human's Part-2 live test — spec = `agent_docs/context_fixed_problem.md`
**Module:** whole system; working through a 20-step approved plan, ONE step per "go"

## Where we are right now
- The human ran the Part-2 real-mic test and wrote up the bugs/features as
  `context_fixed_problem.md` (IDs: STRUCT-1/2, KIOSK-1..7, DOCTOR-1..7, MEDIC-1..7).
- A 20-step sequenced plan was approved. **Steps 1–5 are DONE:** legacy demo isolated at
  `/legacy/` + landing page at `/` (ADR-0031); Alembic rev **0010** applied (ADR-0032:
  nullable `documents.utterance_id`, vitals, letterhead, `prescriptions` table);
  visit-grain docx seam (`visit_docx.py`, `POST /api/visits/{uuid}/documents/{kind}`);
  `shared.js` `fieldValue()` + C2 `TIER_BANDS` (browser-verified); M3/M8 bilingual
  values (ADR-0033: one call fills `value_en`+`value_bn`, `value` mirrors value_en,
  staff edits fill all slots untranslated, M9 counts any slot). **121 tests pass.**
- ⚠ Rows extracted BEFORE step 5 stay English-only until re-extracted (fine — readers
  fall back across slots).

## Locked decisions for this build (human-approved, do NOT re-open)
- **C1:** "Possible Condition (AI Suggestion – Not a Diagnosis)" IS allowed — clearly
  labeled, disclaimer, editable by medic/doctor; the doctor's prescription Diagnosis field
  is NEVER AI-filled (rule #2 boundary; needs its ADR when implemented).
- **C2:** Risk "score" = display-only tier→band mapping in `shared.js` (e.g. low = 0–25%).
  NO numeric score generated or stored.
- **Storage:** prescriptions/reports are DB-backed: `documents.visit_id` (nullable FK),
  new `documents.kind` values (`transcript`, `summary_report`, `prescription`), plus a
  `prescriptions` table (visit_id, doctor_id, payload JSON, document_id) — Alembic **0010**.
- **Bilingual values:** M3/M8 generate BOTH `value_bn` and `value_en` once, stored in the
  `summary_fields` JSON; must stay back-compatible with existing `{value}` rows.
- **Letterhead:** clinic (name/address/logo) + doctor (qualification/registration/
  specialization/signature) live in DB columns (0010), reusable and editable.
- **KIOSK-7:** resume loop on the summary screen asks ONLY still-missing fields, one at a
  time, respects `followup_max_questions`; "নেই" / "No" / "জানি না" count as answered.

## The one thing we are doing next
**Step 6 — kiosk OTP auto-advance (KIOSK-1)**, frontend-only:
1. `frontend/kiosk.js` + `kiosk.html`: typing a digit auto-focuses the next `.otp-input`;
   Backspace on an empty box moves to the previous one; pasting a full 6-digit code
   fills all boxes; repeated digits like `000000` enter smoothly. DEV_OTP stays 000000.
2. Verify in the browser preview (focus flow + paste), no backend change.

**Remaining steps (7–20, one per "go"):** repeat-btn diagnosis + per-message 🔊 (7) ·
raw transcript download button → step-3 endpoint (8) · summary card redesign (9) ·
toggle renders value_bn/value_en (10) · resume loop (11) · medic: toggle+polish+
Queue-btn (12) · risk override endpoint (13) · suggested condition C1 (14) ·
post-referral summary + docx download (15) · doctor: toggle+polish (16) · patient-details
card (17) · prescription form (18) · prescription docx + save (19) · final test sweep +
doc sweep + context_fixed_problem statuses (20).

## Important environment notes
- All three API keys in `backend/.env` (Gemini/Groq/OpenRouter) — rotate before public demo.
  Never auto-run live LLM calls (quota + rule #4 synthetic-only).
- Server: port 8001. Entry points: `/` (landing) · `/kiosk.html` · `/medic/` · `/doctor/` ·
  `/legacy/` (old Phase-0 demo — ADR-0031). `.env` changes need a restart.
- **DEV_OTP=000000**. Alembic head `0010` (applied; backup `.pre-0010.bak`); NEVER delete the DB.
- Windows console gotcha: Bangla prints need `PYTHONIOENCODING=utf-8`.

## Reminders
- Raw words are never edited (rule #1); the system never diagnoses (rule #2) — C1 wording
  is a *suggestion with disclaimer*, never a diagnosis. Red-flag phrases: ADD only, each
  with a TC-R1 test (rule #3).
- Tier codes on the wire stay `low|medium|high|critical`; labels ONLY in `TIER_LABELS`.
- One small step per "go": diff → `pytest backend/tests/` → doc updates → wait.
- Run (Windows): `.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --port 8001`
- Run (Arch):    `.venv/bin/python -m uvicorn backend.app.main:app --reload --port 8001`
- Tests: `pytest backend/tests/` (**121 passing**).
