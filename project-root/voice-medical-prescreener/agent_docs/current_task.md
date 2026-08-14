# current_task.md — What We Are Doing RIGHT NOW

> This is a small, throwaway snapshot. It gets **overwritten** every session.
> It is NOT a history log (that is `changelog.md`). It answers only:
> "If I open a brand-new Claude Code session, what do I need to know to continue?"

---

**Date:** 2026-08-14 (end of Session 39)
**Phase:** **The S39 brief is COMPLETE.** One reported bug (the patient name) root-caused and fixed,
two requested features built (medic-recordable blood sugar; a human-readable EHR PDF beside the FHIR
JSON), one duplicate form removed, and one shared-code move made.
Test suite: **1005 passed, 2 skipped, 0 failures** (was 931).
Alembic head: **0014 — `0014_blood_glucose`** (was 0013). Still **18 tables** — two columns, no table.
New ADR: **0064**. **Two new dependencies (fpdf2, uharfbuzz) + one binary asset (an OFL font).**
**No module changed status.** The work lands inside M13/M14 and the staff layer. **M15 stays 🟨.**

**⚠ Step S5 is STILL NOT implemented and must not be assumed. See the bottom of this file.**

---

## 🚦 THE NEXT STEP — **a HUMAN pass over the two staff portals**

This is the same next step S38 ended on, and it is now larger rather than smaller: S39 changed the
portals again, and **the browser-pane pass did not happen this session**. The Browser pane restricts
localhost to the port in `.claude/launch.json` (8001), and that port was occupied by a uvicorn this
session did not start and would not stop. Everything is covered by static-source tests and by a
34-check HTTP walkthrough against a real server, but **no browser has rendered the new portal DOM.**

### Setup
- Stop any server already on 8001, then run:
  `.venv\\Scripts\\python.exe -m uvicorn backend.app.main:app --reload --port 8001`
- Open **http://127.0.0.1:8001/medic/** and **http://127.0.0.1:8001/doctor/** in Chrome.
- No microphone is involved — S39 touched **no voice code** and no kiosk file.
- ⚠ The dev DB has every visit in `reviewed`, so both queues look empty (correct B7 empty state).
  Use the medic's phone search, or seed a throwaway DB. S39 used
  `DATABASE_URL=sqlite:///<scratch>/demo.db`; **the dev DB was read once, read-only, and never
  modified.**

### What is NEW in S39 and needs eyes (in addition to the S38 walkthrough below)
1. **MEDIC → open a case → Intake & Vitals.** Under the patient's name there is now an **origin
   line**: "ⓘ Name entered by <staff> on <date>", or "Name taken by the AI from what the patient
   said", or a ⚠ line saying the name came from an **earlier visit**, or "Origin of this name is not
   recorded". Judge whether it reads as *reassuring context* or as *alarm* — it appears on every
   case, so if it reads as an alarm it should be quieter.
2. **MEDIC → Intake & Vitals → Record/Edit.** There is a **Blood sugar** pair: a mmol/L number and a
   "Measured as" dropdown (fasting / 2 h after 75 g OGTT / random). Try saving a number **without**
   picking a context — it must refuse, and the server refuses independently. Save both; the read-back
   line shows mmol/L **and** mg/dL with the context spelled out. Then open **🩸 Sugar reference** and
   check the number and the chart sit sensibly together.
3. **MEDIC → forward a case.** The post-referral summary is now **read-only** — its Edit Details and
   Edit weight buttons are gone (they duplicated the intake form and covered fewer fields). Confirm
   the line explaining where editing happens is enough, and that nothing you need is now unreachable.
4. **DOCTOR → open a case.** The details card has the same name-origin line and a **read-only** Blood
   sugar row, with a 🩸 Sugar reference button that appears **only when a reading exists**.
5. **DOCTOR → ⬇ EHR record (PDF)**, beside the existing ⬇ EHR record (FHIR). Open the PDF and judge
   it against the one question only a person can answer: **is this the right shape for whatever this
   clinic would actually file, hand to a patient, or post to a specialist?** If a receiving system or
   a real form is in mind, its expectations should drive the next iteration.
6. **Both portals, বাংলা toggle**, on every screen above.

### The S38 walkthrough still stands
The glucose reference chart, the segmented completeness meter, per-field verification, the referral
history, the recall/handover inbox and the FHIR bundle were all built in S38 and have not been
re-inspected by a human. See the S38 entry in `changelog.md` for its 11-step list.

### ⚠ The rule for next session
**Only change code if the walkthrough reveals a REAL issue.** The brief is complete and test-pinned.

---

## Also open (the human's choice, not a queue)

1. **Rotate the 3 API keys** — HUMAN-only, pending since S25, recommended before any public demo.
2. **Formal WER / precision-recall** on a labelled set — the thesis-evidence gap.
3. **The mid-turn word-loss rule #1 decision** — what happens to a half-captured answer in
   `finalBuffer` when the tab is backgrounded or mic permission is revoked mid-answer. **Yours to
   decide, and it is what BLOCKS the second half of Step S5.**
4. **The Edge run** — every live run so far has been Chrome only.
5. **Faculty future requirements** (`faculty_future_features.md`): quantized summary model,
   quantized STT/TTS, the fully voice-driven follow-up loop (S6–S7 each need their own "go").

---

## ✅ What Session 39 shipped (settled — do not redo or re-derive)

**The patient-name bug — root cause and fix**
- Root cause: `patients` is keyed by **phone**, so `display_name` is patient-scoped and permanent and
  is inherited by every later visit on that number. Nothing was invented; it was **unlabelled**.
- `services/identity.py` (NEW) — `name_provenance()`, **derived from `audit_log`**, no new column.
- `services/intake.apply_demographics` now writes a `patient.identity_ai_fill` audit row
  (`actor_id=None`). It previously wrote **nothing**, so an AI-written name was untraceable.
- `display_name` **removed** from `POST /api/patients/lookup` (the one unaudited writer; unused).
- `name_provenance` rides on `GET /api/visits/{uuid}`; both portals render it under the name.
- `patientNameLabel()` in `shared.js` — ONE "Name not provided" wording, replacing four placeholders.

**Blood sugar**
- `migrations/versions/0014_blood_glucose.py` — `patients.blood_glucose_mmol_l` +
  `blood_glucose_context`, with a DB **CHECK constraint** on the context.
- `clinical_reference.RECORDABLE_GLUCOSE_CONTEXTS` — fasting / ogtt_2h / random. **HbA1c excluded**
  (a percentage and a lab result, not a bedside mmol/L reading); it stays on the chart.
- The vitals PATCH takes both and **refuses either without the other**, server-side, before the write.
- Shown in: the medic intake card, the post-referral summary, the doctor's card, the .docx meta, and
  the FHIR bundle as a **`laboratory`** Observation (LOINC 15074-8 + our context coding), with **no
  `interpretation` and no `referenceRange`**.

**The EHR PDF**
- `services/ehr_pdf.py` (NEW) — a **pure function of the bundle** `ehr_export.build_fhir_bundle()`
  returns. It never touches the DB, and a test forbids `db.query`/`db.get` in the module.
- Kind `ehr_pdf` → `.pdf` → `application/pdf`, through the existing documents table and route.
- Deps: **fpdf2 2.8.8 + uharfbuzz 0.56.0**; asset: **`assets/fonts/NotoSansBengali-Regular.ttf`**
  (OFL-1.1, licence beside it). The renderer **refuses** rather than shipping mis-shaped Bangla.

**Shared / removed**
- The glucose reference panel **moved** from `frontend_medic/index.html` into
  `frontend_shared/staff.js`; both portals mount the same one.
- The post-referral **identity and weight editors are gone** (they duplicated the intake form with
  fewer fields), along with `saveIdentity()` and `saveWeight()`.

## ⚠ Open gaps / honest caveats (carry these forward)

- **No browser has rendered the new portal DOM** (see the next step above). The PDF itself *was*
  inspected visually in Chrome and its Bengali shaping is correct.
- **Real-mic status is UNCHANGED by S39** — it touched no voice code, no kiosk file. The S37 wording
  stands exactly: the S33–S36 run was carried out, **no per-claim results were supplied**, and no
  defects came back. Do not upgrade the three S36 claims. S25's itemised evidence stands.
- **The FHIR bundle is still not certified and not profiled**, and the PDF inherits that honestly —
  it says on its face that it is a rendering of the same record, nothing more.
- **The PDF depends on one shipped font.** Any replacement via `PDF_FONT_PATH` must cover Bengali AND
  Latin with real OpenType shaping tables, or the renderer will refuse.
- **⚠ A missing glyph does not raise — it VANISHES.** That is how `kg/m²` shipped as `kg/m` before it
  was caught by looking at the output. A test now walks every character the renderer will draw
  against the font's cmap; keep it.
- **S39's frontend tests are static-source assertions** (the S28 decision: no JS test runner). They
  prove wiring and containment, not appearance.
- **⚠ Three existing S38 tests were MOVED** (`MEDIC` → `STAFF_JS`) because the glucose panel moved to
  shared code. Every assertion is byte-identical. Nothing was weakened or deleted.
- **Still not done from earlier cycles:** the 3 API keys, formal WER, the Edge run, Step S5.

## Locked decisions — do NOT re-open

- **ADR-0064 (S39):** name provenance is **derived from `audit_log`**, never a column; an origin that
  cannot be established is reported as `unknown`, never guessed; a staff edit **timestamped before
  the visit began** is reported as not-from-this-visit, and one made during it stays `None`; the AI
  identity fill is **audited**; glucose is **value + context or neither**, constrained in the DB;
  **no band, class or interpretation is ever stored or computed** and `glucose_reference()` still
  takes no argument; **HbA1c is not recordable**; there is **no `measured_at` column** (audit_log
  answers it); the PDF **renders the bundle and never reads the DB**; the renderer **refuses** rather
  than mis-shaping Bangla; the font ships **in the repo**; the doctor's glucose row is **read-only**
  because intake is the medic's to own.
- **ADR-0060/0061/0062/0063 (S38)** — BMI derived not stored; dates policed by category with a fixed
  **UTC+06:00** offset (do NOT switch to `ZoneInfo`; Windows has no tz database); the FHIR export
  excludes the AI suggested condition entirely; M16's web search receives the question and nothing
  else, by signature. See `decisions.md`.
- **ADR-0058 / 0059 (S37)** and **0057 / 0056 / 0055 / 0054 / 0053 / 0052 / 0051 / 0050 / 0049 /
  0048 / 0045 / 0040** — see `decisions.md`.
- **S31's terminal/transient STT split:** `no-speech`, `aborted`, `bad-grammar` must stay OUT of
  `TERMINAL_STT_ERRORS` or Chrome's continuous listening regresses. `r.onend` stays untouched.
- **⚠ No apostrophes in comments inside the `CONFIRM_*` literals** in `kiosk.js` — the vocabulary
  tests parse quoted tokens straight out of the served file. This actually happened in S36.

## ⛔ Step S5 is NOT implemented — do not assume it is

S5 (`faculty_future_features.md` §J) is: **no-speech re-prompt, empty-submit guard, 120 s answer
cap, and permission/visibility recovery.** S34 built only the narrow empty-capture re-ask its
Phase 2 required; S35–S38 built nothing from S5, and **S39 touched no voice code at all**. Pinned by
`test_step_s5_is_still_not_implemented`: `no_speech_ms` and `max_answer_ms` are still marked
`S5 (not used yet)` and read by nothing, and there is no `visibilitychange` handler and no
permission-recovery path anywhere in the kiosk.
⚠ **The permission/visibility half is BLOCKED, not merely pending** — see open item 3 above.
⚠ The `visibilitychange` listener in **`frontend_shared/staff.js`** is the STAFF queue auto-refresh
(S38) and has nothing to do with S5, which is about the kiosk.

## Reminders (the four non-negotiables)

- **Rule #1:** raw words are never edited, and never RE-RENDERED elsewhere. The new PDF reproduces
  the transcript **verbatim**, and a test reads the text back out of the PDF's own ToUnicode map and
  compares it to the stored string. Correct Bengali **shaping** is part of this: a mis-shaped word is
  not the patient's word.
- **Rule #2:** never diagnoses. The glucose value is stored and reported with **no band and no
  interpretation**, in the portals and in FHIR alike; the chart still takes no patient value.
- **Rule #3:** red flags ADD-only. Untouched by S39 — and the PDF now renders them as separate
  bullets instead of one run-on paragraph, which is a legibility fix, not a behaviour change.
- **Rule #4:** synthetic/consented data only. S39 used a **throwaway** seeded DB for every server
  check; the dev DB was read once, read-only, and its mtime is unchanged.
- Run (Windows): `.venv\\Scripts\\python.exe -m uvicorn backend.app.main:app --reload --port 8001`
- Tests: `pytest backend/tests/` (**1005 passing, 2 skipped**). Windows: `PYTHONIOENCODING=utf-8`.
