# current_task.md — What We Are Doing RIGHT NOW

> This is a small, throwaway snapshot. It gets **overwritten** every session.
> It is NOT a history log (that is `changelog.md`). It answers only:
> "If I open a brand-new Claude Code session, what do I need to know to continue?"

---

**Date:** 2026-08-14 (end of Session 38)
**Phase:** **The S38 staff-portal UX + clinical-workflow brief is COMPLETE.** All nineteen requested
items (A1–A7, B1–B7, C1–C4) are implemented, tested and exercised in a browser.
Test suite: **931 passed, 2 skipped, 0 failures** (was 767).
Alembic head: **0013 — `0013_height_and_clinical_notes`** (was 0012). **18 tables** (was 17).
No new Python dependency. New ADRs: **0060, 0061, 0062, 0063**.
**No module changed status.** The work lands inside M14 + the medic staff layer (both ✅) and M16.
**M15 stays 🟨.**

**⚠ Step S5 is STILL NOT implemented and must not be assumed. See the bottom of this file.**

---

## 🚦 THE NEXT STEP — **a HUMAN pass over the two staff portals**

Everything S38 built is test-pinned and was driven in a real browser. Three things no test and no
automated run can settle, because they are judgement calls about this clinic:

1. **Does the glucose panel read as a REFERENCE, or as guidance?** The human asked for "a diabetic
   limit". There is no such number, so the medic portal shows the published chart instead — fasting
   / 2-h OGTT / random / HbA1c, each with the sample conditions that make its numbers mean anything,
   both mmol/L and mg/dL, and the WHO-vs-ADA disagreement stated out loud. If a medic reads it and
   comes away thinking the system told them something about a patient, that is a defect and the
   panel should be narrowed.
2. **Is the FHIR export the right shape for whatever this clinic would actually hand it to?** It is
   a structurally valid, semantically conservative HL7 FHIR R4 document Bundle — **not** certified
   and **not** profiled against a national implementation guide. If there is a real receiving system
   in mind, its expectations should drive the next iteration.
3. **Is the doctor→medic note a channel this clinic wants?** It is deliberately tiny (a note to a
   ROLE, no thread, no reply, no notifications). It could equally turn out to be noise on a busy
   desk, in which case it should be removed rather than grown.

### Setup
- Run: `.venv\\Scripts\\python.exe -m uvicorn backend.app.main:app --reload --port 8001`
- Open **http://127.0.0.1:8001/medic/** and **http://127.0.0.1:8001/doctor/** in Chrome.
- No microphone is involved in any of this — S38 touched no voice code.
- ⚠ The dev DB has every visit in `reviewed`, so both queues will look empty. That is the correct
  B7 empty state, not a bug. To see the queue features, either run a kiosk session or seed a
  throwaway DB (S38 used `DATABASE_URL=sqlite:///<scratch>/demo.db` — the real dev DB was **not**
  modified this session).

### The exact flow to walk
1. **Medic:** log in. Check the header clock (real date, 12-hour, ticking) and the "Live · every
   15s · updated …" line under the queue title. Press **ⓘ** beside "Triage Queue" and read the
   explanation.
2. **Medic:** search a phone number, then wait 20 seconds. **The result must NOT be replaced by the
   full queue** — the line should say "Search result — auto-refresh held".
3. **Medic:** click the **10/10 meter** on a queue row. It must open a list of which fields are
   empty, and must NOT open the case.
4. **Medic:** open a case → **Intake & Vitals** → *Record/Edit*. Enter a height and a weight and
   watch the **BMI** appear with both WHO ladders. Save; confirm it persists and the "Still to
   record" line shrinks. Then open **🩸 Sugar reference** and read it with question 1 above in mind.
5. **Medic:** on a field card the AI extracted, press **✔ Looks right**. The badge must become
   "✔ Checked", the **value must not change**, and the queue's verified count must go up.
6. **Medic:** forward a case, then switch to **My referrals** — it must be there, attributed to you.
7. **Doctor:** open a case → **📝 Write Prescription**. The case must STAY on screen and the form
   appears below it. Check the Date field is pinned to today and the follow-up will not accept a
   past date.
8. **Doctor:** in **Required Tests**, type "cbc" (pick a suggestion), then type a test that is not
   on the list and press Enter, then remove one.
9. **Doctor:** **Accept & Write to EHR** → a `.json` file downloads. Open it: it should be a FHIR
   `Bundle` with `type: "document"` and a `Composition` first. Judge it against question 2.
10. **Doctor:** **Follow-up & handover** → schedule a recall and send a note to the medic. Then in
    the **medic** portal open **Inbox** and mark it done. Judge it against question 3.
11. **Both:** toggle বাংলা throughout and confirm nothing overflows or falls back to English.

### ⚠ The rule for next session
**Only change code if the walkthrough reveals a REAL issue.** The brief is complete and test-pinned.

---

## Also open (the human's choice, not a queue)

1. **Rotate the 3 API keys** — HUMAN-only, still pending since S25, recommended before any public demo.
2. **Formal WER / precision-recall** on a labelled set — the thesis-evidence gap. S25's live run was
   qualitative.
3. **The mid-turn word-loss rule #1 decision** — what happens to a half-captured answer in
   `finalBuffer` when the tab is backgrounded or mic permission is revoked mid-answer. **This is
   yours to decide, and it is what BLOCKS the second half of Step S5.**
4. **The Edge run** — every live run so far has been Chrome only.
5. **Faculty future requirements** (`faculty_future_features.md`): quantized summary model,
   quantized STT/TTS, the fully voice-driven follow-up loop.

---

## ✅ What Session 38 shipped (settled — do not redo or re-derive)

**Backend, new files**
- `services/clinical_dates.py` — the Dhaka clock (**fixed UTC+06:00**, not `ZoneInfo`) + the
  three-category date policy (system / authored-now / scheduled-forward).
- `services/clinical_reference.py` — BMI bands (WHO + WHO Asian), the glucose reference chart, and
  the ~50-entry bilingual diagnostic-test vocabulary. **Constants, not a table.**
- `services/ehr_export.py` — the HL7 FHIR R4 document Bundle builder.
- `services/notes.py` — recalls + the doctor→medic back-channel on one table.
- `api/routes_reference.py`, `api/routes_notes.py`, `schemas/reference.py`, `schemas/notes.py`.
- `migrations/versions/0013_height_and_clinical_notes.py`.

**Backend, changed**
- `db/models.py` — `patients.height_cm` + the `ClinicalNote` model. **No BMI column, deliberately.**
- `services/triage.py` — `field_is_verified()`, `verified_field_keys()`, `completed_referrals()`.
- `services/assistant.py` — M16 widened (tests + opt-in de-identified case context + a NEW output
  guard + `suggested_tests`).
- `routes_dashboard.py` — `POST .../fields/{key}/verify`, `height_cm` on the vitals PATCH,
  `fields_empty` on the queue row.
- `routes_prescription.py` — server-side date policy before the write.
- `services/documents/` + `routes_documents.py` — the `ehr_bundle` kind and `application/fhir+json`.

**Frontend**
- `shared.js` — `dhakaNowParts()`, `dhakaTodayIso()`, `localeNum()`, all formatters 12-hour.
- `staff.js` — the shared auto-refresh timer, `buildCompletenessMeter()`, `renderWorkspaceState()`,
  `showBmi()`, the per-field verify control.
- `frontend_medic/index.html` — clock, triage explainer, refresh line, rebuilt Intake & Vitals,
  glucose panel, Queue/My referrals/Inbox tabs.
- `frontend_doctor/index.html` — clock, inline prescription at the bottom, two-column advice/tests,
  the test token editor, the EHR button, the Follow-up & handover card, the widened assistant panel.
- `motion.css` / `shared.css` — segmented meter, chips, suggestion list, `.rx-two-col`,
  `.source-verified`, the ≤700px header-wrap fix.

## ⚠ Open gaps / honest caveats (carry these forward)

- **🟡 Real-mic status is UNCHANGED by S38** (it touched no voice code). The human confirmed at S37
  that the real-microphone run of the **S33–S36** changes was carried out; **no per-claim results
  were supplied and none are documented**, and no defects came back. Do NOT say "no microphone has
  exercised S33–S36" (false) and do NOT upgrade the three specific S36 claims to "verified" (no
  evidence). S25's itemised evidence stands unchanged.
- **The FHIR bundle is not certified and not profiled.** Structurally valid and semantically
  conservative is exactly the claim; a receiving system will still need to map it. Where a concept
  had no code we were confident of, it ships as TEXT on purpose.
- **The glucose chart and the BMI bands are published reference values, transcribed by hand.** They
  are sourced in the code and in the payload, but a clinician should read them once before any
  demo.
- **The test vocabulary is a typing aid, not a formulary.** Bangladesh-outpatient-shaped, ~50
  entries, and deliberately not exhaustive — anything can be typed.
- **S38's frontend tests are static-source assertions** (the S28 decision: no JS test runner). They
  prove wiring and containment, not appearance. Everything visual in the list above was checked in
  a browser by hand this session and is described in `test_log.md`; none of it is machine-verified.
- **⚠ Three existing tests were modified** — two fixture date literals made relative, and one
  assertion on M16's prompt phrasing updated because the module legitimately widened. No test was
  weakened, deleted, or changed to make a failure disappear. See the S38 changelog entry.
- **Still not done from earlier cycles:** the 3 API keys, formal WER, the Edge run, Step S5.

## Locked decisions — do NOT re-open

- **ADR-0060 (S38):** BMI is **derived, never stored**; one `clinical_notes` table serves both the
  recall and the back-channel; per-field verification lives in the existing `summary_fields` JSON
  and **does not touch the value or `source`**; an empty field cannot be verified; the referral
  history is derived from `audit_log` and **reports what it cannot attribute** rather than inventing
  an owner; a note is addressed to a **role**, never a person; the clinical reference data is a
  module, not a table; **there is no single "diabetic limit"** and `glucose_reference()` takes no
  argument.
- **ADR-0061 (S38):** dates are policed **by category** — system/historical are never touched, the
  prescription date must be today, a follow-up/recall must not be in the past; enforced
  **server-side and before the write**; "today" is the **Dhaka** date from a **fixed UTC+06:00
  offset** (Windows has no tz database — do not switch to `ZoneInfo` without adding `tzdata`); all
  staff clocks are 12-hour.
- **ADR-0062 (S38):** the export is a **FHIR R4 document Bundle**; the **AI suggested condition is
  excluded from it entirely** (its disclaimer does not survive ingestion elsewhere); the risk tier
  is a `RiskAssessment`, never a `Condition`; `critical` is never silently downgraded; free-text
  clinical content ships **uncoded** rather than with a guessed code; Bangla travels via the
  standard `_title` translation extension.
- **ADR-0063 (S38):** M16 stays **one service**; case context is **opt-in and off by default**; the
  **web search receives the question and nothing else, by signature**; the case context is
  de-identified and carries **no raw transcript**; suggested tests are **clicked** in, never
  auto-inserted; the M16 output guard must **NOT** reuse M7's dosage rule (a dosage range is the
  correct answer here); a flagged answer is delivered with a stronger disclaimer, not deleted.
- **ADR-0058 / 0059 (S37)** and **0057 / 0056 / 0055 / 0054 / 0053 / 0052 / 0051 / 0050 / 0049 /
  0048 / 0045 / 0040** — see `decisions.md`.
- **S31's terminal/transient STT split:** `no-speech`, `aborted`, `bad-grammar` must stay OUT of
  `TERMINAL_STT_ERRORS` or Chrome's continuous listening regresses. `r.onend` stays untouched.
- **⚠ No apostrophes in comments inside the `CONFIRM_*` literals** in `kiosk.js` — the vocabulary
  tests parse quoted tokens straight out of the served file. This actually happened in S36.

## ⛔ Step S5 is NOT implemented — do not assume it is

S5 (`faculty_future_features.md` §J) is: **no-speech re-prompt, empty-submit guard, 120 s answer
cap, and permission/visibility recovery.** S34 built only the narrow empty-capture re-ask its
Phase 2 required; S35, S36, S37 and **S38 built nothing from S5 at all** (S38 touched no voice
code). Pinned by `test_step_s5_is_still_not_implemented`: `no_speech_ms` and `max_answer_ms` are
still marked `S5 (not used yet)` and read by nothing, and there is no `visibilitychange` handler
and no permission-recovery path anywhere in the kiosk.
⚠ **The permission/visibility half is BLOCKED, not merely pending** — see open item 3 above.
⚠ S38 DID add a `visibilitychange` listener to **`frontend_shared/staff.js`** (the queue
auto-refresh). That is the STAFF portals and has nothing to do with S5, which is about the kiosk.

## Reminders (the four non-negotiables)

- **Rule #1:** raw words are never edited, and never RE-RENDERED elsewhere. S38's FHIR export
  includes the transcript **verbatim** (escaped for XHTML, never replaced by its correction) and a
  test reconstructs the text and compares it to the stored string. M16's case context deliberately
  carries **no** transcript at all.
- **Rule #2:** never diagnoses. The glucose reference takes no patient value; BMI reports a band and
  no advice; the AI suggested condition has no FHIR representation; the risk tier exports as a
  `RiskAssessment`; a clinical note is workflow text nothing reads back; M16's new output guard
  catches patient-directed assertions.
- **Rule #3:** red flags ADD-only. Untouched by S38 — the queue chip, the handoff `info` row and the
  local rule forcing Critical with every LLM down all still stand.
- **Rule #4:** synthetic/consented data only. S38 used a **throwaway** seeded DB for every browser
  check and did not modify the dev DB. M16's web search receives the doctor's question and nothing
  else, by signature.
- Run (Windows): `.venv\\Scripts\\python.exe -m uvicorn backend.app.main:app --reload --port 8001`
- Tests: `pytest backend/tests/` (**931 passing, 2 skipped**). Windows: `PYTHONIOENCODING=utf-8`.
