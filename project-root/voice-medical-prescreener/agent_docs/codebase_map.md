# codebase_map.md — Where Everything Lives

> A living map of the repo so Claude (and you) can find things without
> re-exploring the whole project each session. Update it whenever you add or move
> a folder/file. Keep each note to one line.

**Last updated:** 2026-08-14 (**Session 39 — TWO new production files, FIVE new test files, one
Alembic revision (0013 → 0014, TWO columns, no new table, still 18 tables), TWO new Python
dependencies and ONE new binary asset. One file was DELETED from the medic portal by moving it into
shared code, and two duplicate editors were removed.**)

**NEW in S39 — name provenance, blood glucose, the EHR PDF (ADR-0064):**

| File | What it is |
|---|---|
| `backend/app/services/identity.py` | **NEW.** Answers "where did this patient's name come from, when, from which visit, and by whom" — **DERIVED from `audit_log`, no column, no table**. Owns the two audit action constants. ⚠ Honest by construction: a name written before S39 has no audit row and reports `unknown`, never a guess; `from_this_visit` is deduced from the clock only when a staff edit **predates the visit's start**, and is left `None` when it genuinely cannot be answered. |
| `backend/app/services/ehr_pdf.py` | **NEW.** The EHR record as a human-readable PDF. ⚠ **It never reads the database** — `bundle_to_pdf()` is a pure function of the dict `ehr_export.build_fhir_bundle()` returns, so the PDF and the FHIR file cannot describe the visit differently. Typesets the bundle's own section narratives (a FHIR document Bundle *is* a Composition carrying XHTML per section). Contains a small `<p>/<b>/<br>/<li>/<table>` narrative parser and `renderable_text()`, which exists for one test: **a missing glyph does not raise, it VANISHES**. Raises `PdfFontUnavailable` rather than emitting mis-shaped Bangla. |
| `backend/migrations/versions/0014_blood_glucose.py` | **NEW.** `patients.blood_glucose_mmol_l` + `blood_glucose_context`, with a DB **CHECK constraint** on the context. ⚠ **No band/class/interpretation column** (rule #2) and **no `measured_at`** — `audit_log` answers when and by whom, exactly as it does for weight and BP. |
| `assets/fonts/NotoSansBengali-Regular.ttf` + `OFL.txt` | **NEW asset (463 KB, OFL-1.1).** The font the EHR PDF embeds. Ships in the repo rather than being resolved from the OS: Windows' `Nirmala.ttf` is not redistributable and not on Arch, and a clean Arch box may have no Bengali font at all — a medical document must render identically on both dev machines. Covers Bengali **and** Latin, so one file serves the whole document. Override with `PDF_FONT_PATH`. |
| `backend/tests/test_patient_name_provenance.py` | **NEW (10).** The reported bug, pinned: a name inherited from an earlier visit must say so. |
| `backend/tests/test_intake_vitals_glucose.py` | **NEW (16).** Medic edits pre-referral; value and context refused apart; nothing classifies the reading. |
| `backend/tests/test_migration_0014.py` | **NEW (5).** Fresh + in-place upgrade, the CHECK constraint biting **by name**, no interpretation column under any spelling, downgrade. |
| `backend/tests/test_ehr_pdf.py` | **NEW (26).** Reads text back out of the PDF through its own **ToUnicode CMap** (helpers `pdf_text` / `pdf_flat`), so assertions are about the artifact, not the input. |
| `backend/tests/test_staff_portal_s39.py` | **NEW (17).** Static-source assertions over the shipped portals (the S28 no-JS-runner method). |

**CHANGED in S39:**

| File | Change |
|---|---|
| `backend/app/services/intake.py` | `apply_demographics` now writes a `patient.identity_ai_fill` audit row (`actor_id=None`). It previously wrote **nothing**, so an AI-written name was untraceable forever after. |
| `backend/app/api/routes_visits.py` | `GET /visits/{uuid}` carries `name_provenance` beside the patient. ⚠ `display_name` **removed** from `POST /patients/lookup` — the third writer of the field and the only unaudited one; no client ever sent it. |
| `backend/app/db/repository_visits.py` | `get_or_create_patient_by_phone` no longer takes a `display_name`. |
| `backend/app/api/routes_dashboard.py` | The vitals PATCH takes the glucose pair and **refuses either without the other**, server-side, before the write. |
| `backend/app/services/clinical_reference.py` | `RECORDABLE_GLUCOSE_CONTEXTS` (fasting / ogtt_2h / random). ⚠ **HbA1c is excluded** — a percentage and a lab result, not a bedside mmol/L reading; it stays a reference row with no input beside it. |
| `backend/app/services/ehr_export.py` | A **`laboratory`** glucose Observation (LOINC 15074-8 + a context coding in our own namespace), with **no `interpretation` and no `referenceRange`**. ⚠ The BMI narrative now says `kg/m2` (the UCUM unit it already codes) — `kg/m²` was being silently truncated to `kg/m` by the PDF renderer, a different unit. |
| `backend/app/services/documents/` | New visit-document kind **`ehr_pdf`** → `.pdf` → `application/pdf`, beside `ehr_bundle`. ⚠ The `_WRITERS` registry is untouched: it is the UTTERANCE-grain seam, and the EHR PDF is visit-grain. |
| `backend/app/core/config.py` | `DEFAULT_PDF_FONT` + `pdf_font_path` / `resolved_pdf_font`. |
| `frontend_shared/shared.js` | `patientNameLabel()` — ONE "Name not provided" wording, replacing four different placeholders. |
| `frontend_shared/staff.js` | `renderNameProvenance()`, the glucose label map + `glucoseText()`, and **the glucose reference chart moved here from the medic portal** so the doctor sees the same one. ⚠ `MMOL_TO_MGDL` must equal `clinical_reference.MMOL_TO_MGDL`; a test asserts it. |
| `frontend_medic/index.html` | Name-origin line, the blood-sugar pair in the intake form (value + context, validated together), the sugar read-back line. ⚠ **The post-referral identity and weight editors are GONE**, with `saveIdentity()` and `saveWeight()` — they wrote the same `patients` row through the same PATCH as the intake form but covered fewer fields. The screen is now a read-only snapshot. |
| `frontend_doctor/index.html` | Name-origin line, a **read-only** blood-sugar row (intake is the medic's to own), the shared sugar chart mounted only when a reading exists, and **⬇ EHR record (PDF)** beside the FHIR button — both through ONE `downloadEhrExport(btn, kind)`. |
| `requirements.txt` | **+fpdf2 2.8.8, +uharfbuzz 0.56.0.** ⚠ Chosen by BANGLA, not by PDF features: Bengali needs conjunct formation and vowel-sign reordering, ReportLab cannot shape it, and a PDF that mangles the patient's own words is a rule #1 defect in the one export a human reads. |
| `backend/tests/test_staff_portal_s38.py` | ⚠ Three tests **MOVED** from reading `MEDIC` to reading `STAFF_JS` because the glucose panel moved. **Every assertion is byte-identical** — nothing weakened or deleted. |

**Last updated:** 2026-08-14 (**Session 38 — EIGHT new production files, SIX new test files, and
the first schema change since S25: Alembic 0012 → 0013, ONE column + ONE table, 18 tables.
No new Python dependency.**)

**NEW in S38 — staff-portal UX + clinical workflow (ADR-0060 derived/stored + the four workflow
features, ADR-0061 the date policy, ADR-0062 the FHIR export, ADR-0063 the M16 widening):**

| File | What it is |
|---|---|
| `backend/app/services/clinical_dates.py` | **NEW.** The ONE definition of "what date is it" and "which dates may a human type". Dhaka via a **fixed UTC+06:00 offset** (Windows ships no IANA tz database and `zoneinfo` raises here; Bangladesh has had no DST since 2010, so the offset is exact). Three policy categories — **system/historical (never touched)**, **authored-now (must be today)**, **scheduled-forward (never in the past)** — and validators returning machine CODES, never sentences. |
| `backend/app/services/clinical_reference.py` | **NEW.** Static clinical constants: BMI bands (WHO international **and** WHO Asian action points), the glucose reference chart, and the ~50-entry bilingual diagnostic-test vocabulary. ⚠ `glucose_reference()` takes **no argument** — there is no function anywhere that maps a reading to a conclusion (rule #2). A module, deliberately not a table. |
| `backend/app/services/ehr_export.py` | **NEW.** Builds the **HL7 FHIR R4 document Bundle** (`build_fhir_bundle` / `render_fhir_bundle`). Read-only; no dependency (a FHIR resource is a JSON object). ⚠ The AI suggested condition has **no representation** in it; the tier is a `RiskAssessment`, never a `Condition`; free-text clinical content ships **uncoded** rather than with a guessed code. |
| `backend/app/services/notes.py` | **NEW.** Recalls (C3) + the doctor→medic back-channel (C4) on ONE table. Addressed to a **role**, never a person; no thread, no reply, no read receipts — it must not become a chat. |
| `backend/app/schemas/reference.py` | **NEW.** `BmiOut` / `GlucoseReferenceOut` / `TestSuggestionOut`. No field anywhere accepts a patient reading. |
| `backend/app/schemas/notes.py` | **NEW.** `NoteCreateRequest` / `NoteOut` / `ReferralOut` / `ReferralHistoryOut` (the last carries `unattributed_total` — honesty about pre-S37 referrals with no recorded medic). |
| `backend/app/api/routes_reference.py` | **NEW.** `GET /api/reference/bmi`, `/glucose`, `/tests`. No patient id in any of them (rule #4 — cacheable, nothing personal in a query string). |
| `backend/app/api/routes_notes.py` | **NEW.** `POST|GET /api/visits/{uuid}/notes`, `GET /api/notes`, `PATCH /api/notes/{id}`, `GET /api/medics/{id}/referrals`. |
| `backend/migrations/versions/0013_height_and_clinical_notes.py` | **NEW.** `patients.height_cm` + the `clinical_notes` table with CHECK constraints on `kind`/`status`/`recipient_role`. ⚠ **No BMI column** — it is derived from two columns that are both present, and a stored copy would go stale the moment a weight was corrected. |
| `backend/tests/test_clinical_reference.py` | **NEW (30).** The 18:00-UTC Dhaka rollover, the date categories, BMI arithmetic + its refusal on implausible input, the published WHO thresholds, and that `glucose_reference` has no parameter (asserted on the signature). |
| `backend/tests/test_migration_0013.py` | **NEW (6).** Fresh + in-place upgrade, **no BMI column under any spelling**, the CHECK constraints biting at DB level, downgrade. |
| `backend/tests/test_staff_portal_s38.py` | **NEW (39).** Static-source assertions over the shipped portals (the S28 no-JS-runner method). Carries a brace-matching `_fn_body()` helper — two earlier drafts sliced on `"\n}"` and on the parameter list and broke on correct code. |
| `backend/tests/test_date_policy.py` | **NEW (11).** Through the REAL prescription route, including that a historical visit's timestamps survive a prescription written today. |
| `backend/tests/test_ehr_export.py` | **NEW (28).** Structural FHIR correctness (every `urn:uuid` resolves) plus the safety boundaries. |
| `backend/tests/test_workflow_notes.py` | **NEW (31).** C1-C4, including that verification leaves the value and `source` untouched. |

**CHANGED in S38:**

| File | What changed |
|---|---|
| `backend/app/db/models.py` | `patients.height_cm` (rev 0013) + the `ClinicalNote` model. |
| `backend/app/services/triage.py` | `field_is_verified()` (source=human **or** `verified_by`), `verified_field_keys()`, `completed_referrals()` — the last derived from `audit_log.actor_id`, reporting `unattributed_total` rather than guessing an owner. |
| `backend/app/services/assistant.py` | M16 widened to medicines + diagnostic tests + opt-in de-identified case context; `build_case_context()` reuses `question_tools.get_patient_context` (no second context builder); a **new** `unsafe_answer_reason()` that deliberately does **not** reuse M7's dosage rule; `suggested_tests` cleaned and bounded. ⚠ `_search()` still takes the question and nothing else, **by signature**. |
| `backend/app/api/routes_dashboard.py` | `POST /visits/{uuid}/profile/fields/{key}/verify` (C2 — writes provenance only), `height_cm` on the vitals PATCH, `fields_empty` on the queue row. |
| `backend/app/api/routes_prescription.py` | `_enforce_prescription_dates()` runs BEFORE the write, so a rejected date reaches neither the stored payload nor the .docx. |
| `backend/app/services/documents/` + `routes_documents.py` | the `ehr_bundle` kind, `VISIT_DOCUMENT_FORMATS`, and `application/fhir+json`. |
| `frontend_shared/shared.js` | `dhakaNowParts()`, `dhakaTodayIso()` (**never `toISOString`**), `localeNum()`; all formatters 12-hour with AM/PM. |
| `frontend_shared/staff.js` | the shared auto-refresh timer (holds on a search result / a hidden tab / another list), `buildCompletenessMeter()`, `renderWorkspaceState()`, `showBmi()` (fetches from the server — the cut-offs live in ONE place), the per-field verify control. |
| `frontend_medic/index.html` | live clock, triage explainer, refresh line, the rebuilt Intake & Vitals form, the glucose panel, and Queue / My referrals / Inbox tabs. |
| `frontend_doctor/index.html` | live clock, the prescription inline at the bottom of the case, two-column Advice/Required Tests, the test token editor, the EHR (FHIR) button, the Follow-up & handover card, the widened assistant panel with its case-context opt-in. |
| `frontend_shared/motion.css`, `shared.css` | the segmented meter, chips, the suggestion list, `.rx-two-col`, `.source-verified`, and the ≤700px header-wrap fix. |

**NEW in S37 — the two STAFF portals audited as ROLES (ADR-0058 features/ownership, ADR-0059 UI):**

| File | What it is |
|---|---|
| `backend/app/services/triage.py` | **NEW.** The MEDIC's operational view, entirely DERIVED: `waiting_minutes()` (pins offset-less SQLite UTC first — subtracting naive from aware is a TypeError), `TIER_ORDER` (unassessed sorts BETWEEN high and medium), `triage_sort_key()`, `empty_field_keys()` / `human_verified_count()` (share M9's `field_has_text`), `handoff_checks()` (**advisory — can never block a forward**) and `queue_stats()`. Writes nothing. |
| `backend/app/services/history.py` | **NEW.** The DOCTOR's longitudinal view: `patient_history()` assembles prior visits + prior prescriptions from existing rows. Carries **no transcript** (rule #1) and interprets nothing (rule #2). `_medicine_names()` survives any payload shape. Writes nothing. |
| `backend/app/schemas/triage.py` | **NEW.** `HandoffOut` / `HandoffCheckOut` / `QueueStatsOut`. Codes on the wire, labels in the frontend (ADR-0030 f). |
| `backend/app/schemas/history.py` | **NEW.** `PatientHistoryOut` / `HistoryVisitOut` / `HistoryPrescriptionOut`. |
| `backend/app/api/routes_history.py` | **NEW.** `GET /api/patients/{id}/history` (read-only). Registered in `main.py`. |
| `frontend_shared/motion.css` | **NEW.** Depth + motion for `/medic/` and `/doctor/` ONLY (the kiosk must not load it). Every `animation`/`@keyframes` sits inside `@media (prefers-reduced-motion: no-preference)`; role identity (`body.portal-medic` amber TRIAGE vs `body.portal-doctor` indigo CLINICAL); staff-only responsive breakpoints; pins the staff portals to the viewport so the two panes scroll independently. |
| `agent_docs/portal_roles.md` | **NEW doc.** What each portal is for, per-role feature tables (existing vs S37), use cases, how the roles connect, the **data-ownership matrix**, and everything considered and deliberately NOT built with the reason. |

**CHANGED in S37:** `api/routes_dashboard.py` (`scope` + `sort` params, `_queue_visits()` as the ONE
queue definition, `GET /api/dashboard/stats`, `GET /api/visits/{uuid}/handoff`, assign records the
forwarding medic) · `schemas/dashboard.py` (`DashboardItemOut` gains `waiting_minutes`,
`fields_filled/total/verified`, `assigned_doctor_name`; `AssignRequest` gains optional `editor_id`) ·
`main.py` (registers the history router) · `frontend_shared/staff.js` (skeleton/empty/error/search-miss
states, `waitLabel()`, queue chips + tier rails, `setQueueScope()`) · `frontend_medic/index.html`
(load strip, Intake & Vitals card BEFORE the referral, handover check, attributed forward) ·
`frontend_doctor/index.html` (patient timeline + prescription history, Queue/Completed scope,
review-state bar, `STATUS_LABELS`). **NEW tests:** `test_medic_triage.py` (18),
`test_doctor_history.py` (10), `test_staff_portal_ui.py` (16).

Prior: 2026-08-13 (**Session 36 — ONE new production file, SEVEN new test files, no
schema change (Alembic stays 0012), no dependency change.**

**NEW production file — `backend/app/services/question_tools.py`** (Finding 3). The session-scoped
context tools behind an M7 question, and the record of why they are NOT MCP tools (ADR-0057 b —
no tool-calling loop exists, the round-trips are the scarce free-tier resource, a second context
path rebuilds a disagreement S35 removed, and session scoping here is structural because every
function takes `visit`). Four exports: `get_patient_context()` (age/sex/area ONLY — never the name,
phone, weight or BP that sit on the same row), `get_question_context()` (collected · missing ·
already_asked · the recent conversation **bounded to `MAX_CONTEXT_TURNS = 24`**, which never
truncates a normal ~18-turn visit), `unsafe_question_reason()` (the output guard on M7's generated
question — dosage amounts and explicit prescribing/diagnosing phrases; ⚠ HIGH-PRECISION,
LOW-RECALL, deliberately does NOT ban "ওষুধ"/"medicine"/"diagnosis", and is NOT a medical-safety
classifier), and `safe_fallback_question()` (the deterministic bilingual replacement, so a rejected
question never costs the patient their turn).

**NEW test files** (all under `backend/tests/`):
- **`test_kiosk_resume_layout.py`** (8) — Finding 1. The grid track that outlived its occupant, the
  pairing that must not drift, the specificity argument against both responsive overrides, and the
  `min-width: 0` on the question text column.
- **`test_kiosk_session_isolation.py`** (16) — Finding 2. The epoch, the ordering (`sessionEpoch += 1`
  FIRST), the engine teardown (handlers detached BEFORE `abort()`, and `abort()` not `stop()`), the
  four timers, the re-entry guards, "removed not merely hidden", and the stale-response guard on
  each of the eight async patient paths.
- **`test_question_tools.py`** (27) — Finding 3. The MCP rejection, the minimum context, the
  isolation proofs (patient A's context/asked-questions/conversation can never reach patient B), the
  bound, and the output guard in both directions — legitimate questions PASS, prescriptions fail.
- **`test_kiosk_phone_early_stop.py`** (13) — Finding 4. Where the decision is made (inside
  `onresult`, before `restartSilenceWindow()`), when it must not fire, that it exits through the
  ordinary turn path without bypassing the read-back, and the one-verification-only guard.
- **`test_kiosk_review_completion.py`** (12) — Finding 5. The vocabulary additions, why `all`/`সব`
  are YES words rather than filler, the routing ahead of the read-back gate, and that a real
  correction still reaches the existing pipeline untouched.
- **`test_auto_raw_transcript.py`** (12) — Finding 6. Real backend renders (the filename, its lack
  of patient identity, the raw bytes, an empty visit) plus the kiosk wiring (once-only, unawaited,
  silent on the auto path, dropped when stale).
- **`test_kiosk_patient_feedback.py`** (13) — Finding 7, **including the test that pins S5 as NOT
  implemented** so a later session cannot assume it landed here.

**Changed production files:**
- **`frontend/kiosk.js`** — NEW `sessionEpoch` / `sessionToken()` / `endSession()` /
  `startNewSession()`; `maybeCompletePhone()`; `otpSending`; `reviewCorrectionOpen()` /
  `maybeFinishReview()`; `autoTranscriptDownloaded` + `downloadRawTranscript({auto})`;
  `SUBMITTED_ALOUD`; `renderConvoProgress()` / `hideConvoProgress()`; `CONFIRM_YES` gains
  `alright`/`all`/`সব`/`সবকিছু` and `CONFIRM_FILLER` gains `s`; `updateSubmitVisibility()` also
  respects `submitting`; `confirmSubmit()`'s hand-written teardown replaced by one call.
- **`frontend/kiosk.html`** — `.summary-body.no-float`, `.resume-q-body`, `.doctor-stage
  .progress-chip`, `#convo-progress`; the resume row's inline `flex:1` became a class.
- **`backend/app/services/followup.py`** — `patient_context()` now RENDERS what
  `get_patient_context()` returns; the conversation comes from the bounded tool; M7's output passes
  `unsafe_question_reason()` before it is stored or spoken. `datetime`/`timezone`/`Patient` imports
  dropped (they moved to the tool).
- **`backend/app/services/documents/__init__.py`** — the transcript kind's human-facing download
  name is now `raw-transcript-visit-<8>-<date>.docx`. ⚠ The stored `kind` is UNCHANGED — it is the
  API contract and both staff portals read it.

**Five existing tests updated, none weakened** — four pinned the hand-written teardown inside
`confirmSubmit()` line by line (that list is exactly what S36 replaced with one seam, and they are
now stricter: the timer test checks all FOUR cancels rather than the three somebody remembered), and
one widened `updateSubmitVisibility`'s condition by the `submitting` term.

⚠ **A trap worth knowing before editing `frontend/kiosk.js`:** the vocabulary tests parse
`CONFIRM_YES` / `CONFIRM_NO` / `CONFIRM_FILLER` straight out of the SERVED file by matching quoted
tokens, so **an apostrophe in a comment inside those literals is read as vocabulary**. This happened
in S36 and was caught by the pre-existing `test_the_two_vocabularies_do_not_overlap`.

---

### Session 35 (previous)

**Last updated:** 2026-08-12 (**Session 35 — ONE new production file, FOUR new test files, no schema
change (Alembic stays 0012), no dependency change. One element MOVED (see below).**

**NEW production file — `backend/app/services/tts/prosody.py`** (Finding 6). `speech_text(text, lang)`
punctuates a line for SPEECH: a sentence-final `।` (bn) / `.` (en) so the engine applies a closing
contour instead of stopping mid-breath, and a real comma where this project's own strings already
imply a pause (em dash, ellipsis). Applied ONCE, in `tts/service.synthesize()`, so the primary
provider and the espeak fallback read the identical line. ⚠ **It may never change a WORD** — the
S34/S35 read-back sends the PATIENT's own captured words down this path, and a rewrite there would
read back something they did not say. Also exports `SENTENCE_ENDINGS`.

**NEW test files** (all under `backend/tests/`):
- **`test_question_context.py`** (12) — Finding 4. `collected_context()` is the exact complement of
  `missing_summary_fields()` over the same 10 keys; a blank field counts as missing; a Bangla-only
  answer counts as collected; the block reaches the model AHEAD of the conversation; and it contains
  **no evaluative language at all** (the "this is not a decision system" guard).
- **`test_tts_prosody.py`** (29) — Finding 6. The two prosodic cues, the empty/dangling-comma edge
  cases, that every provider gets the SAME paced line, the neutral pitch/volume defaults reaching
  edge-tts, and — the safety property — that **no word is changed, added, removed or reordered**.
  Its docstring states plainly that acoustic quality is neither tested nor claimed.
- **`test_kiosk_voice_confirmation.py`** (17) — Findings 2 + 7 (ADR-0056). The shipped vocabularies
  parsed OUT of kiosk.js, the two safety rules (unknown word → ambiguous; NO beats YES), the routing
  that keeps a verdict from being stored as an answer, and the REMOVAL of S34's retraction-on-listen.
- **`test_kiosk_phone_timer.py`** (17) — Findings 1 + 3 + 8. The 10-second window on the shared
  ticker, its single-send guard, the ONE header clock (and that `#review-timer` is gone rather than
  duplicated), the `order: 1` narrow-screen fix, and the derived `body[data-kiosk-state]` cues.

**Edited production files:**
- **`frontend/kiosk.js`** — `speechTokens()` **extracted** as the ONE tokenizer (⚠ `digitsFromSpeech`
  now calls it; the NFC fold and the `\p{M}` split class moved WITH it, and two tests were retargeted
  accordingly). NEW `CONFIRM_YES`/`CONFIRM_NO`/`CONFIRM_FILLER` + `parseConfirmation()`;
  `applySpokenConfirmation()` / `askConfirmationAloud()` / `CONFIRM_NOT_UNDERSTOOD`;
  `state.reviewConfirm` + `startReviewConfirmation()` / `stopReviewConfirmation()` /
  `applyReviewConfirmation()` / `rejectReview()` + `REVIEW_CONFIRM_PROMPT` / `REVIEW_CORRECTION`;
  `renderClock()` / `hideClock()` / `CLOCK_LABELS` replacing the review-scoped renderer;
  `startPhoneTimer()` / `cancelPhoneTimer()` / `phoneConfirmMs()`; `body.dataset.kioskState` in
  `applyAvatarState()`.
  ⚠ **`setResumeMode()` now calls `updateSubmitVisibility()` LAST**, not before its branch — the
  `cancelPendingMic()` on the else path was cancelling the microphone the review approval had just
  armed. ⚠ **`toggleListening()` must NOT clear the read-back** (see the comment left in place).
- **`frontend/kiosk.html`** — `#kiosk-clock` **moved into `.portal-header`** (the element outside the
  scrolling `.screen`); `#review-timer` removed; `.confirm-say` lines on all three confirmations;
  `#phone-confirm-hint`; the mic-pulse + loud-hint CSS keyed on `body[data-kiosk-state]`; `order: 1`
  on the clock in the narrow query. ⚠ There must stay exactly ONE
  `@media (prefers-reduced-motion: reduce)` block — a second one would hide the first from any reader.
- **`backend/app/services/followup.py`** — NEW `collected_context()` + `_COLLECTED_VALUE_CHARS`; two
  new clauses in `_QUESTION_SYSTEM`; the block inserted between `patient_context()` and
  `CONVERSATION:` (⚠ that position is load-bearing — everything after `CONVERSATION:` is pinned
  identical across two patients differing only in age).
- **`backend/app/services/tts/service.py`** — `speech_text()` applied once; `_make_edge()` passes
  pitch/volume. **`tts/edge.py`** — `pitch`/`volume` constructor args reaching `Communicate`.
- **`backend/app/core/config.py`** — `voice_phone_confirm_ms: int = 10000`, `tts_edge_pitch`,
  `tts_edge_volume`. **`schemas/kiosk_config.py`** + **`api/routes_config.py`** — `phone_confirm_ms`
  (clamped at 0). **`backend/.env.example`** — all three documented.
→ suite **547 → 622 passing, 2 skipped**.

Prior: 2026-08-12 (**Session 34 — THREE new test files, NO new production file, no
schema change (Alembic stays 0012), no dependency change, nothing moved or renamed.**

**NEW test files** (all under `backend/tests/`):
- **`test_kiosk_answer_confirm.py`** (23) — ADR-0055 c/d/e. That the spoken-answer read-back gate
  sits at ONE routing point (`stopListening()`'s spoken branch, AFTER identification and BEFORE the
  two clinical submits); that `acceptAnswer()` re-enters the SAME `submitPatientTurn(text,'mic')` /
  `submitResumeAnswer(text,'mic')` so there is still one pipeline; that nothing reaches the server
  or the transcript before ✔; that the read-back is verbatim, `bn-BD`, and can never open the mic;
  that an unclear capture re-asks instead of storing; and (P5) that new turns scroll the THREAD,
  never the page.
- **`test_kiosk_review_timer.py`** (17) — ADR-0055 g/h. The shared `startTicker()`, its at-most-once
  `onEnd`, the auto-logout countdown moved onto it, the clock/submit shared verdict, idempotent
  start, the `submitting` re-entry guard, and an explicit test that the **S4 endpointer is NOT**
  folded into the shared ticker.
- **`test_kiosk_review_screen.py`** (19) — ADR-0055 f/i. Per-card 🔊 and the read-through, the third
  `AVATAR_IDS` mount and the `AVATAR_SUBSTATUS_IDS` generalisation, "exactly one assistant on
  screen", the float animation being on the CARD not `.doctor-avatar`, the `minmax(0, 1fr)` tracks
  and the narrow-screen `span 1 !important`, plus a duplicate-selector guard for the new CSS.

**Edited production files (no new modules, no new routes):**
- **`frontend/kiosk.js`** — the bulk. Phase 1: ten Bangla transliterations in `SPOKEN_DIGITS`,
  `spacedDigits()`, `renderDigitPreview()` / `clearDigitPreview()`, `digitPreview` on `DOCKS.phone`
  and `DOCKS.otp`. Phase 2: `holdForConfirmation()` (the ONE gate) + `isUnclearAnswer()` +
  `currentQuestionText()` + `reAskUnclearAnswer()` + `offerSpokenAnswer()` + `showAnswerConfirm()` /
  `hideAnswerConfirm()` + `speakAnswerBack()` + `acceptAnswer()` / `rejectAnswer()`,
  `state.pendingAnswer`, `applyCountdownCaption()`. Phases 3-4: per-card 🔊 in `renderSummary()`,
  `speakSummaryField()`, `toggleSummaryReadAloud()` + `readAloudQueue` + `setReadAloudLabel()`,
  `AVATAR_IDS` += `summary-avatar`, new `AVATAR_STATUS_IDS` / `AVATAR_SUBSTATUS_IDS`. Phase 5:
  `scrollThreadToEnd()`. Phases 6-7: `startTicker()` (also used by the auto-logout),
  `startReviewTimer()` / `cancelReviewTimer()` / `renderReviewClock()` / `hideReviewClock()` /
  `reviewTimeoutMs()` / `reviewSpeakAgain()`, and `let submitting` guarding `confirmSubmit()`.
  ⚠ `resetState()` still must NOT touch `DOCKS` or any DOCKS-walking helper — it runs at module
  load, inside the temporal dead zone (the trap that killed the kiosk in S33). The new panels and
  the clock are hidden there **by element id** for exactly that reason.
- **`frontend/kiosk.html`** — `#phone-digit-preview` / `#otp-digit-preview`; the two
  `#dock-answer-confirm` / `#resume-answer-confirm` read-back panels; `.summary-head` +
  `.summary-body` two-column review with `#summary-float` / `#summary-avatar` / `#summary-status` /
  `#summary-substatus` / `#read-summary-btn`; `#review-timer` + `#review-timer-value`; the
  `.digit-preview` / `.answer-confirm` / `.doctor-float` / `.review-timer` CSS and their
  reduced-motion entries; **`html, body { height: 100% }` + `.screen { min-height: 0; overflow-y:
  auto }`** (the page-growth fix — see ADR-0055 i); and `span 1 !important` in the narrow query.
- **`backend/app/core/config.py`** — `voice_answer_confirm: bool = True`,
  `voice_review_timeout_ms: int = 60000`.
- **`backend/app/schemas/kiosk_config.py`** + **`backend/app/api/routes_config.py`** — the same two
  as `answer_confirm` / `review_timeout_ms` (the latter clamped at 0 in the route).
- **`backend/.env.example`** — `VOICE_ANSWER_CONFIRM` / `VOICE_REVIEW_TIMEOUT_MS` documented.
- **Three existing test files edited, none weakened:** `test_kiosk_config.py` (+2 tests, key set),
  `test_tts_provider.py` (key set), `test_kiosk_avatar.py` (the `AVATAR_IDS` assertion rewritten to
  parse the list and cross-check the markup), `test_voice_digits.py` (+6).
→ suite **480 → 547 passing, 2 skipped**.

Prior: 2026-08-11 (**Session 33 — FOUR new test files, NO new production file, no
schema change (Alembic stays 0012), no dependency change.**

**NEW test files** (all under `backend/tests/`):
- **`test_voice_digits.py`** (20) — F5a. The cross-language digit contract: `normalize_phone` /
  `to_ascii_digits` accepting Bangla digits, and the shipped `SPOKEN_DIGITS` map parsed OUT of the
  served `kiosk.js` rather than restated. Also pins the two Unicode traps — `\p{M}` in the
  tokeniser and the NFC fold for `ছয়`/`নয়`.
- **`test_kiosk_voice_identification.py`** (26) — F5b. That identification is two more `DOCKS`
  entries and two branches, NOT a second recognizer (`new SR()` appears exactly once); that a
  spoken phone number is never auto-sent; that a spoken OTP reuses `maybeAutoVerify()`.
- **`test_kiosk_avatar.py`** (25) — P1/P2. Avatar state derived-not-pushed and its precedence,
  the poll, the error expiry, the TDZ guard, the custom-property lamp, plus the elderly-UI
  assertions (touch targets, focus rings, both responsive axes) and a regression test for
  equal-specificity duplicate CSS.
- **`test_age_appropriate_questions.py`** (17 + 1 opt-in skip) — P3, tiered: deterministic code
  validation and prompt validation, with the live `M7_LIVE=1` probe skipped by default.

**Edited production files (no new modules):**
- **`backend/app/db/repository_visits.py`** — NEW `to_ascii_digits()`; `normalize_phone` now folds
  any Unicode decimal digit instead of `re.sub(r"\D", ...)`. `import re` -> `import unicodedata`.
- **`frontend/kiosk.js`** — F5a pure digit functions (`unicodeDigit`, `asciiDigits`,
  `SPOKEN_DIGITS`, `digitsFromSpeech`, `phoneFromSpeech`); F5b `DOCKS.phone`/`DOCKS.otp`,
  `state.identifyStep`/`pendingPhone`, `applySpokenPhone`/`applySpokenOtp`, the read-back
  (`showPhoneConfirm`/`confirmPhone`/`rejectPhone`), `reAskPhone`/`reAskOtp`, `IDENTIFY_HINTS` +
  a dock-aware `modeHint(dock)`; P1 `AVATAR_STATES`/`currentAvatarState`/`refreshAvatar`/
  `applyAvatarState`/`setAvatarOverride` + the 200 ms poll.
  ⚠ `IDENTIFY_HINTS` MUST stay declared ABOVE `const DOCKS` (temporal dead zone).
- **`frontend/kiosk.html`** — the two identification docks + the phone read-back panel; the
  robotic-doctor markup in both docks and its CSS-only 3D; the P2 elderly sizing block and the two
  responsive media queries.
- **`backend/tests/test_kiosk_otp_entry.py`** — one assertion updated (not weakened) for F5b's
  extended `if (!res) { reAskOtp(); return; }`.

Prior: 2026-08-11 (**Session 32 — faculty-demo cycle F1–F4 + F6: ONE new production file,
five new test files, no schema change (Alembic stays 0012), no dependency change.**

**NEW production file — `backend/app/services/requirements.py`** (F3). The ONE definition of what a
pre-screening must have collected before the patient reaches the final review. Exports
`MUST_HAVE_VALUE` (`main_problem` — must carry text), `MUST_HAVE_BEEN_ASKED` (onset, symptom details,
medicines, allergies — must have been PUT to the patient but may legitimately end empty),
`IDENTITY_REQUIREMENTS` (`patient_name`, `patient_age`, `problem_area` — F4, living OUTSIDE
`summary_fields`), and `missing_requirements(db, visit)`. The kiosk gate, the readiness route and the
submit guard all read it from here — do NOT fork a second definition.

**Edited production files:**
- **`frontend/kiosk.js`** — the bulk. F1: `OTP_LENGTH` / `otpBoxes()` / `otpDigits()` /
  `clearOtpInputs()` / `maybeAutoVerify()`, an Enter branch inside `initOtpInputs()`'s keydown
  (⚠ the Backspace branch keeps its early `return` — a test pins that), `wire('phone-input', sendOtp)`
  in `initTypedInputs()`, and a rewritten `verifyOtp()` with `otpVerifying`. F3:
  `updateSubmitVisibility()` / `renderRequiredNotice()` / `loadReadiness()`, `state.readiness`, and
  `confirmSubmit()` now posts `?require_complete=true`. F4: `INTAKE_SCRIPT` + `scriptEntry()` +
  `askScriptedQuestion()` + `inScriptedOpening()`, `state.scriptIndex` / `state.resumeScripted`,
  `pendingScriptedRequirement()`, and **`setResumeMode(question, scripted)` now takes two kinds of
  question** — this is what invalidated the old `askAloud(question.question_text)` assertion.
- **`frontend/kiosk.html`** — `#required-notice` div + its `.required-notice` warning style.
- **`backend/app/services/followup.py`** — `FIELD_PROMPTS` (one description per canonical key),
  `patient_context()` (age/sex/area → M7), the AGE-APPROPRIATE clause in `_QUESTION_SYSTEM`, the
  server-named `target_key` replacing the old `target_gap = remaining[0]` repair, and the resume cap
  = `followup_max_questions + followup_resume_max_questions`.
- **`backend/app/services/intake.py`** — `problem_area()` helper + the `problem_area` key in
  `_EXTRACT_SYSTEM`; `run_intake` now **merges** into `entities` instead of replacing it.
- **`backend/app/services/profile_update.py`** — same merge fix, so a found area and the C1
  `suggested_condition` survive every follow-up answer.
- **`backend/app/api/routes_visits.py`** — NEW `GET /api/visits/{uuid}/readiness`.
- **`backend/app/api/routes_dashboard.py`** — `submit_visit()` gains `require_complete: bool = False`
  (⚠ **opt-in on purpose** — staff/walk-in paths legitimately submit partial cases; the kiosk always
  sends true; ADR-0052 d).
- **`backend/app/schemas/visit.py`** — `ReadinessOut`.
- **`backend/app/core/config.py`** — `followup_resume_max_questions: int = 8`.

**NEW test files:** `test_kiosk_otp_entry.py` (12) · `test_followup_target_gap.py` (13) ·
`test_required_info.py` (21) · `test_intake_context.py` (16) · `test_conversation_preserved.py` (6)
→ suite **324 → 392, 1 skipped**. Two existing test files edited, neither weakened:
`test_resume_loop.py` (its fake Settings gained the new field) and `test_kiosk_auto_listen.py` (the
`setResumeMode` assertion retargeted and strengthened).

**Pointer for next session (F5, NOT built):** `backend/app/db/repository_visits.py:17`
`normalize_phone` — `re.sub(r"\D", "", ...)` **keeps** Bangla digits (they are Unicode digits) and then
fails the ASCII `startswith("1")` check → `ValueError` → 400. **Verified, not assumed.** JS `/\D/g` in
`kiosk.js` is ASCII-only and silently **deletes** them instead. The two languages disagree; F5's
normalizer must resolve that explicitly.
Prior: 2026-08-09 (**Session 31 — the Edge terminal-error fix: ONE production file changed,
ONE test file added.** `frontend/kiosk.js` — three bilingual message constants (`MIC_UNAVAILABLE` /
`STT_SERVICE_UNAVAILABLE` / `STT_LANGUAGE_UNSUPPORTED`) + the **`TERMINAL_STT_ERRORS`** map, declared
immediately **above `initRecognition()`**; `r.onerror` became a 5-line map lookup. ⚠ **`r.onend` and
`FLUSH_GRACE_MS` were NOT touched** — this therefore **supersedes the three S30 pointers below**:
the `onerror` pointer is now DONE, the `onend` pointer is unchanged-by-design (the loop stops because
`stopListening(false)` flips `listening`, not because the restart learned about errors), and
`FLUSH_GRACE_MS` remains **UNVERIFIED on Edge**. New test file
**`backend/tests/test_kiosk_stt_errors.py`** (6) → suite **318 → 324, 1 skipped**; it extracts the
shipped `TERMINAL_STT_ERRORS` literal out of the served `kiosk.js` and compares the key set, the same
"run the shipped literal" pattern S30 introduced. **No backend, schema, dependency or Alembic change;
head stays 0012. No existing test file was edited.** One NEW pointer for future sessions:
**`frontend/kiosk.js:576`** — `stopListening()`'s `if (sendTurn && text)`, i.e. where a **mid-turn**
terminal error **discards the patient's captured `finalBuffer`**. Pre-existing, widened in reach by S31,
and **an open rule #1 decision awaiting the human** — do not change it unilaterally.
Prior: 2026-08-08 (**Session 29 — ADR-0049 Bangla TTS: new package
`backend/app/services/tts/`** — `base.py` (`TtsProvider` ABC + `TtsUnavailable`), `espeak.py`
(`EspeakNgProvider`: local espeak-ng via stdlib `subprocess`, text through **stdin** so Bangla never
hits Windows argv encoding, `shell=False`, 600-char cap), `service.py` (`get_provider()` selector +
`server_tts_available()` + `synthesize()`), `__init__.py` — deliberately mirroring the `services/otp/`
seam. New route `api/routes_tts.py`; `schemas/kiosk_config.py` + `server_tts: bool`; `core/config.py`
+ `TTS_PROVIDERS`, four `tts_*` settings and `resolved_tts_provider`; `main.py` registers the router
and now serves ALL static mounts through **`RevalidatedStaticFiles`** (`no-cache, must-revalidate`) —
a stale cached `shared.js` had silently broken TTS language selection. Frontend: `frontend_shared/tts.js`
rewritten around a provider chain (browser voice → `/api/tts` → `false`) + `ttsSpeaking()` / `ttsCancel()`
/ `configureTts()` / `banglaAudioAvailable()`; `frontend/kiosk.js` swaps ONE echo-guard predicate to
`ttsSpeaking()`. New tests: `test_tts_provider.py` · `test_kiosk_tts_fallback.py` · (S4)
`test_kiosk_countdown.py` → suite **274 (+3 skipped)**. **No new Python dependency; Alembic stays 0012.**
**S29 end — no files added or moved by the live run; the only map-relevant note is a POINTER:**
`backend/app/services/followup.py:45` is where the M7 prompt forces
`"question": "<Bangla question> (<English question>)"` — i.e. **every question is ONE bilingual string**.
That single line is the root cause of the TTS-1 "two questions, no gap" defect, and
`followup.py:145` is where that same string is stored verbatim as a `system` utterance (so a TTS-only
fix must not touch either). Also: `agent_docs/context fixed problem 3.0.md` is now 🟢 OPEN with TTS-1/TTS-2.
**2026-08-08, Session 30 (part 3) — Edge compatibility verification: NO FILES ADDED, MOVED OR CHANGED.**
Inspection only. The map-relevant output is three **POINTERS** for the next session:
- **`frontend/kiosk.js:499`** — `r.onerror`, which handles only `not-allowed` / `audio-capture`. This is
  **the single place the proposed Edge terminal-error fix touches** (`language-not-supported`,
  `network`, `service-not-allowed`). **NOT IMPLEMENTED.**
- **`frontend/kiosk.js:491`** — `r.onend`'s `if (listening) r.start()`, the other half of the infinite
  `start → error → end → start` loop. Nothing here changes; it stops looping once `onerror` calls
  `stopListening(false)`.
- **`frontend/kiosk.js:372`** — `FLUSH_GRACE_MS = 600`, Chrome-calibrated by its own comment.
  **UNVERIFIED on Edge — a suspicion, not a bug.** Do not change it blindly.
Also noted, deliberately NOT edited: **`agent_docs/human_live_run_guide.md:19`** ("use Chrome, not
Edge") and **`:72`** (the now-disproven "Edge may expose `bn-BD` voices") are both stale.
Prior: **2026-08-08, Session 30 (part 2) — TTS-2 shipped (ADR-0050 Accepted): the natural neural Bangla voice.**
**NEW FILE `backend/app/services/tts/edge.py`** — `EdgeTtsProvider` (Microsoft neural `bn-BD` via
edge-tts; `media_type = "audio/mpeg"`, i.e. MP3 not WAV). `service.py` rewritten around a
**`PROVIDER_FACTORIES`** registry (`espeak` | `edge`) + **`get_fallback_provider()`** and a fallback
chain in `synthesize()` (primary → espeak-ng → raise). `base.py` gained **`MAX_TEXT_CHARS`** (moved out
of `espeak.py`, which now re-exports it) and **`TtsProvider.available()`** (default True; espeak
overrides it via `resolve_binary`); `routes_tts.py` now imports the cap from `base`. `core/config.py`:
`TTS_PROVIDERS += "edge"`, **`tts_provider` default flipped `espeak` → `edge`**, plus
`tts_edge_voice_bn` / `tts_edge_voice_en` / `tts_edge_rate` / `tts_edge_timeout_s` /
`tts_local_fallback`. `requirements.txt` += **`edge-tts==7.2.8`** (LGPL-3.0; pulls aiohttp).
`.env.example` documents all three providers + the privacy warning. New test file
`backend/tests/test_tts_edge_provider.py` (21, offline by default; `TTS_LIVE=1` opts into the network)
→ suite **318, 1 skipped**. **No route, frontend, schema or Alembic change — the ADR-0049 seam held.**
Prior: **2026-08-08, Session 30 (part 1) — TTS-1 fixed (ADR-0051), no files added or moved except one test.**
`frontend_shared/tts.js` gains the `BILINGUAL_QUESTION` regex constant + **`spokenHalf(text, short)`**,
applied ONCE inside `speak()` (`const speech = verbatim ? text : spokenHalf(text, short);`) so BOTH
providers — `new SpeechSynthesisUtterance(speech)` and `encodeURIComponent(speech)` — receive the same
split half; `speak()` gains a **`verbatim`** option. `frontend/kiosk.js` changes ONE call site: the
per-bubble 🔊 passes `verbatim: role === 'patient'`. **Neither `followup.py` line above was touched** —
the stored `system` utterance and the on-screen bubble keep the full bilingual string. New test file
`backend/tests/test_tts_bilingual_split.py` (20) → suite **297**. Two pre-existing static assertions in
`test_kiosk_auto_listen.py` / `test_kiosk_tts_fallback.py` updated to the new strings.
Prior: 2026-07-11, Session 24 — **P4-1 real OTP (ADR-0045): new package
`backend/app/services/otp/`** — `base.py` (`OtpSender` ABC + `OtpSendError`), `dev_log.py`
(`DevLogSender`: code → server log via `uvicorn.error`), `textbee.py` (`TextBeeSender`: real SMS
via httpx), `service.py` (issue/verify core: hash, expiry, single-use, lockout, throttle,
`get_sender()` factory), `__init__.py` (re-exports) — plus migration
`backend/migrations/versions/0012_otp_codes.py` (**Alembic head is now 0012**) and the `OtpCode`
model. New test files: `test_otp.py` (13) · `test_migration_0012.py` (2) → suite **192**. New
direct dep: `httpx==0.28.1` (was transitive; Arch laptop: re-run `pip install -r requirements.txt`).
Edits: `config.py` (OTP_CHANNEL/OTP_DEV_BYPASS/TTL/attempts/cooldown/TextBee creds),
`routes_visits.py` (lookup ISSUES a real OTP + audits `otp_issued`; verify-otp = DB check,
401/429; bypass only on the dev channel), `schemas/patient.py` (+`retry_after_seconds`),
`.env.example` (OTP block), and `migrations/env.py`
(`fileConfig(..., disable_existing_loggers=False)` — pre-existing bug: startup migrations silenced
all uvicorn logs). No frontend changes (kiosk UX identical). **The 2.0 tracker is COMPLETE.**
S24b docs addendum: CLAUDE.md status refreshed; NEW agent_docs files `context fixed problem
3.0.md` (next-cycle scaffold, empty inbox) + `faculty_future_features.md` (quantized-model
research track) — see the agent_docs listing below.)

---

## Current structure (real, today)

> Session 8 built the whole reconciled system. Session 9 moved the old Module-1 transcript app
> into `frontend_legacy/` (served at `/legacy/`, behavior unchanged — ADR-0031) and put a
> portal landing page at `/`.

```
voice-medical-prescreener/
├── CLAUDE.md · DESIGN-mintlify.md · INSTALL.md · README.md
│     # CLAUDE.md frontend section points at the clinical-blue system (ADR-0029, done S8b);
│     # DESIGN-mintlify.md carries a SUPERSEDED banner — design source of truth is frontend_shared/shared.css.
├── requirements.txt              # CORE deps (FastAPI, uvicorn, pydantic-settings, SQLAlchemy, alembic, openai, python-docx, pytest)
│                                  #   + ddgs (S23, M16 web search — ADR-0044) + httpx (S24, TextBee OTP sender)
│                                  #   + edge-tts (S30) + fpdf2 & uharfbuzz (S39, the EHR PDF — ADR-0064)
├── .gitignore                    # ignores .env, .venv/, *.db, *.db.*.bak, *.bak, data/, audio/, models/
├── .claude/launch.json           # preview dev-server configs (uvicorn; PORT 8001): Windows + backend-linux
├── agent_docs/                   # the project's shared brain (living docs) — now incl. architecture.md,
│   │                              #   reconciliation.md, mockups-redesign.html, update_system_flowchart.md,
│   │                              #   context_fixed_problem.md (20-step spec, all ✅), human_live_run_guide.md (S14: human handoff),
│   │                              #   context fixed problem 2.0.md (S18–S24 cycle tracker — ALL items ✅, historical),
│   │                              #   context fixed problem 3.0.md (S24: NEXT cycle scaffold — human pastes raw manual-testing
│   │                              #     findings → numbered tracker; currently EMPTY/waiting),
│   │                              #   faculty_future_features.md (S24: quantized Moshi summary + quantized STT/TTS;
│   │                              #     +2026-08-08: Req 3 fully voice-driven follow-up loop — faculty text +
│   │                              #     seam-mapping notes; research track, NOT current work)
│   └── ... (constitution, milestone_log, current_task, changelog, test_log, decisions, codebase_map, session_protocol)
├── backend/
│   ├── .env / .env.example       # + OTP block (S24: OTP_CHANNEL=dev|textbee, OTP_DEV_BYPASS, DEV_OTP,
│   │                              #   TTL/attempts/cooldown, TEXTBEE_* creds), per-bucket model names (ADR-0026)
│   ├── alembic.ini · migrations/env.py (render_as_batch; S24: disable_existing_loggers=False so
│   │                              #   startup migrations no longer silence uvicorn logs)
│   ├── migrations/versions/      # 0001_baseline · 0002_add_stt_provider_and_doc_kind ·
│   │                              #   0003_aggregate_root (clinics/users/patients/visits + deltas + backfill + seeds) ·
│   │                              #   0004_intake_profile (case_profiles, module_events) · 0005_followup_questions ·
│   │                              #   0006_risk_xai · 0007_reports · 0008_doctor_reviews_feedback · 0009_audit_log ·
│   │                              #   0010_prescriptions_letterhead (visit-grain docs, vitals, letterhead, prescriptions — ADR-0032) ·
│   │                              #   0011_visit_submitted_at (P3-1, S23) · 0012_otp_codes (P4-1, S24 — ADR-0045) ·
    │                              #   0013_height_and_clinical_notes (S38) · 0014_blood_glucose (S39 — ADR-0064)
│   ├── prescreener.db            # SQLite (gitignored); 18 tables + alembic_version (head 0014)
│   ├── prescreener.db.pre-000{3,4,5,6,7}.bak · .pre-0010.bak  # per-migration backups (gitignored)
│   ├── data/documents/           # generated .docx (gitignored)
│   ├── app/
│   │   ├── main.py               # lifespan init_db + ENTRY_POINTS startup log; registers transcripts, documents,
│   │   │                          #   visits, followup, risk, dashboard, report, prescription, assistant (S23)
│   │   │                          #   routers; mounts /shared /medic
│   │   │                          #   /doctor /legacy + landing/kiosk at / (ADR-0031)
│   │   ├── core/
│   │   │   ├── config.py         # + OTP settings (S24: otp_channel/otp_dev_bypass/dev_otp/ttl/attempts/
│   │   │   │                      #   cooldown/textbee_*), followup floors/caps, per-bucket models
│   │   │   └── llm_providers.py  # provider registry + MODULE_PROVIDERS map (ADR-0026); S17: FALLBACK_ORDER
│   │   │                          #   assigned→Groq→Cerebras→Mistral→OpenRouter + optional Cerebras/Mistral buckets (ADR-0041)
│   │   ├── api/
│   │   │   ├── routes_transcripts.py · routes_documents.py   # (existing, untouched)
│   │   │   ├── routes_visits.py  # patients/lookup (S24: ISSUES a real OTP, audits otp_issued, resend-throttle
│   │   │   │                      #   fields) + verify-otp (S24: DB check, 401/429, dev-only 000000 bypass);
│   │   │   │                      #   visits CRUD + utterances; intake; profile
│   │   │   ├── routes_visit_documents.py # S9: POST /api/visits/{uuid}/documents/{transcript|summary_report}
│   │   │   ├── routes_followup.py# NEW: followup/next (M7) · followup/answer (M8+M9); S11: ?scope=fields
│   │   │   │                      #   = KIOSK-7 resume loop (no threshold gate; ADR-0034)
│   │   │   ├── routes_risk.py    # NEW: assess (M10 + rule) · risk (latest + XAI); S11: risk/override
│   │   │   │                      #   (MEDIC-3 human row, audit-logged, red-flag guard — ADR-0035)
│   │   │   ├── routes_dashboard.py # NEW: users list · submit (→auto-assess; S12: +M10C suggestion, best-effort) ·
│   │   │   │                      #   dashboard queues · field-edit PATCH · assign; S12: PATCH profile/condition
│   │   │   │                      #   (C1 staff edit, ADR-0036) + PATCH patients/{id}/vitals (ADR-0037)
│   │   │   ├── routes_report.py  # NEW: report (M12) · review (M14) · feedback (M15)
│   │   │   ├── routes_prescription.py # S13: GET .../prescription/context (letterhead prefill, DOCTOR-4/5, ADR-0038) +
│   │   │   │                      #   POST .../prescription (DOCTOR-6 save row + render .docx, ADR-0039)
│   │   │   ├── routes_assistant.py # S23 (P3-3, ADR-0044): POST /api/visits/{uuid}/assistant/drug-info — M16,
│   │   │   │                      #   visit-scoped, 404 guard before any LLM call, LLMCallError → 502
│   │   │   ├── routes_config.py   # NEW S28 (Req 3 step S1, ADR-0048): GET /api/config — PUBLIC, no DB/auth.
│   │   │   │                      #   Kiosk voice-loop mode + timings so a clinic tunes them from .env,
│   │   │   │                      #   not JS. Built field-by-field so a Settings secret can never leak.
│   │   │   │                      #   S29: + server_tts (a CAPABILITY bool, never the provider name/path)
│   │   │   └── routes_tts.py      # NEW S29 (ADR-0049): GET /api/tts?text=&lang= -> audio/wav. PUBLIC (the
│   │   │                          #   kiosk needs it pre-login) but renders ONLY the assistant's own
│   │   │                          #   question — no raw_text/utterance/transcript ever passes through, so
│   │   │                          #   rule #1 is untouched. Missing engine => 503, NEVER a silent 200.
│   │   ├── schemas/              # transcript, document (existing) + visit (S23: +submitted_at), patient, profile,
│   │   │                          #   followup, risk, dashboard (S23: +submitted_at), prescription (S13: no diagnosis
│   │   │                          #   field, rule #2), assistant (S23: disclaimer fields REQUIRED in the contract);
│   │   │                          #   S28: kiosk_config.py (NEW, behavioural knobs only) + followup.py AnswerRequest
│   │   │                          #   gains a non-blank raw_text guard that returns the value UNCHANGED (rule #1)
│   │   │  ── frontend/kiosk.{html,js}: S28 step S2 (ADR-0048) adds the [🎤 Speak][⌨ Type] mode switch
│   │   │     to BOTH docks — state.inputMode + DOCKS map + MODE_HINTS + setInputMode() (updates both
│   │   │     docks at once, hides the mic in Type mode, Enter-to-send, mic error -> typing). The old
│   │   │     "Microphone issue? Type instead" reveal link is REMOVED.
│   │   │  ── S28 step S3 (auto-listen): kiosk.js gains VOICE_DEFAULTS + loadKioskConfig() (first
│   │   │     consumer of GET /api/config), askAloud() at the 3 question sites (assistantSays,
│   │   │     setResumeMode, repeatQuestion — the per-bubble 🔊 stays plain speak()), openMicWhenQuiet()
│   │   │     = the ECHO GUARD, and cancelPendingMic() on every deliberate action. frontend_shared/
│   │   │     tts.js speak() gains a GENERATION TOKEN + onerror->onend bridge so a cancelled
│   │   │     utterance's callback can never open the mic during the next question (rule #1).
│   │   │     Patient still taps once to finish — the countdown is S4.
│   │   ├── services/
│   │   │   ├── correction/       # (existing) reused as M2
│   │   │   ├── documents/        # (existing) DocxWriter + storage; S9 + visit_docx.py (visit-grain
│   │   │   │                      #   transcript/summary_report writers) + generate_visit_document();
│   │   │   │                      #   S12: summary_report renders the C1 block + regenerates FRESH (ADR-0037);
│   │   │   │                      #   S13: render_prescription() + generate_prescription_document() (DOCTOR-6, ADR-0039)
│   │   │   ├── llm_client.py     # call_module() — assigned bucket → fallback; S17 (ADR-0041): logs EVERY
│   │   │   │                      #   attempt, 429/quota cooldown (60s/15min, fail-open), reset_cooldowns()
│   │   │   ├── intake.py         # NEW: M3 extract (10-field summary_fields; bilingual value_en/value_bn since S9,
│   │   │   │                      #   ADR-0033) → M4 summary → M6 gaps
│   │   │   ├── followup.py       # NEW: M7 question gen (Groq; no repeats; stored + spoken); S11:
│   │   │   │                      #   missing_summary_fields() + missing-override param (resume scope)
│   │   │   ├── profile_update.py # NEW: M8 re-extract + merge (human fields protected)
│   │   │   ├── completion.py     # NEW: M9 completeness (LOCAL)
│   │   │   ├── risk.py           # NEW: M10 classify + M11 XAI (rule forces critical; deterministic fallback);
│   │   │   │                      #   S11: override_assessment() + RiskOverrideBlocked (ADR-0035)
│   │   │   ├── suggestion.py     # S12: M10C — C1 "Possible Condition (AI Suggestion – Not a Diagnosis)"
│   │   │   │                      #   (ADR-0036: separate call from M10; disclaimer CONSTANTS embedded in the
│   │   │   │                      #   stored entities["suggested_condition"]; best-effort, never blocks submit)
│   │   │   ├── assistant.py      # S23 (P3-3, ADR-0044): M16 — ddgs/DuckDuckGo search (top-5, capped snippets,
│   │   │   │                      #   best-effort → []) + one Flash-bucket call_module; disclaimer attached
│   │   │   │                      #   SERVER-side always (rule #2); search gets only the doctor's question (rule #4)
│   │   │   ├── otp/              # S24 (P4-1, ADR-0045): base.py (OtpSender ABC + OtpSendError) ·
│   │   │   │                      #   dev_log.py (DevLogSender — code → server log, the ONE sanctioned
│   │   │   │                      #   plaintext spot) · textbee.py (TextBeeSender — real SMS via httpx) ·
│   │   │   │                      #   service.py (issue/verify: salted-SHA-256 hash, 5-min expiry, single-use,
│   │   │   │                      #   constant-time, 5-attempt lockout, 60s resend throttle, get_sender())
│   │   │   ├── red_flags.py      # NEW: RED_FLAG_RULES (5 categories, bn/banglish/en) — LOCAL, no API
│   │   │   ├── report.py         # NEW: M12 local report assembly (Red Flags + disclaimer); S12: sections gain
│   │   │   │                      #   patient vitals + suggested_condition (ADR-0037)
│   │   │   └── audit.py          # NEW: audit() one-line append writer
│   │   └── db/
│   │       ├── database.py       # engine/session; run_migrations() + _legacy_stamp_revision() (mixed-state fix)
│   │       ├── models.py         # Utterance/Document (+visit_id/role/seq; utterance_id nullable since 0010) + Clinic/User/
│   │       │                      #   Patient/Visit + CaseProfile/ModuleEvent/FollowupQuestion/RiskAssessment/XaiExplanation/
│   │       │                      #   Report/DoctorReview/Feedback/AuditLog + Prescription (0010, ADR-0032)
│   │       ├── repository.py     # (existing) utterance/document session-grain writers (NO raw mutator)
│   │       ├── repository_visits.py # NEW: normalize_phone, get/create patient+visit, add_utterance, set_visit_status
│   │       │                      #   (S23: stamps submitted_at on awaiting_review — P3-1)
│   │       └── seed.py           # S13: seed_demo_letterhead() — idempotent, fills NULL letterhead columns at startup
│   └── tests/                    # 6 existing suites + test_migration_0003 · test_routes_visits · test_intake ·
│                                  #   test_followup_loop · test_risk · test_staff_routes · test_report_review ·
│                                  #   test_routes_static (entry points + legacy isolation) ·
│                                  #   test_migration_0010 (visit-grain docs + prescriptions) ·
│                                  #   test_visit_documents (transcript verbatim + summary report) ·
│                                  #   test_bilingual_fields (value_en/value_bn + legacy back-compat) ·
│                                  #   test_resume_loop (KIOSK-7 scope=fields, S11) ·
│                                  #   test_risk_override (MEDIC-3 human row + red-flag guard, S11) ·
│                                  #   test_suggested_condition (C1 M10C + edit path + disclaimer, S12) ·
│                                  #   test_medic_summary (vitals PATCH + docx freshness, S12) ·
│                                  #   test_prescription_context (DOCTOR-4/5 letterhead prefill + seed, S13) ·
│                                  #   test_prescription_docx (DOCTOR-6 save row + .docx + Diagnosis-never-AI, S13) ·
│                                  #   conftest.py (S17: autouse LLM-cooldown reset) ·
│                                  #   test_llm_client (S17: per-attempt logging + cooldown switching, ADR-0041) ·
│                                  #   test_followup_min_questions (S20) · test_submit_background (S21) ·
│                                  #   test_patient_demographics (S22) · test_submitted_at (S23, P3-1) ·
│                                  #   test_migration_0011 (S23) · test_doctor_sees_medic_edits (S23, P3-2) ·
│                                  #   test_assistant (S23, M16) · test_otp (S24, 13: hash-only + expiry +
│                                  #   single-use + bypass matrix + lockout + throttle + sender seam) ·
│                                  #   test_migration_0012 (S24) ·
│                                  #   test_kiosk_config / test_kiosk_input_modes / test_kiosk_auto_listen /
│                                  #   test_kiosk_countdown / test_answer_raw_text_guard (S28-S29, Req 3 S1-S4) ·
│                                  #   test_tts_provider + test_kiosk_tts_fallback (S29, ADR-0049 seam) ·
│                                  #   test_kiosk_stt_errors (S31: the Web Speech terminal/transient
│                                  #     split — extracts TERMINAL_STT_ERRORS from the served JS;
│                                  #     2 of its 6 tests exist to keep no-speech/aborted TRANSIENT
│                                  #     so Chrome's continuous listening never regresses) ·
│                                  #   test_tts_bilingual_split (S30, ADR-0051: runs the shipped
│                                  #   BILINGUAL_QUESTION regex extracted from the served tts.js)  (297 total)
├── frontend/                     # patient side (served at /)
│   ├── index.html                # NEW (S9): landing page linking the 4 entry points (ADR-0031)
│   ├── kiosk.html · kiosk.js     # patient kiosk (at /kiosk.html): phone→OTP (auto-advance/Backspace/paste, S10
│   │                              #   KIOSK-1)→voice chat (per-bubble 🔊 icons + no-bn-voice hint banner, S10
│   │                              #   KIOSK-2/3)→summary (S11: per-field cards KIOSK-5, bilingual values KIOSK-6,
│   │                              #   raw .docx download KIOSK-4, resume voice dock + progress chip KIOSK-7)
│   │                              #   →submit→auto-logout
├── frontend_legacy/              # OLD Module-1 transcript app, isolated (served at /legacy/ — ADR-0031)
│   ├── index.html · app.js · styles.css   # unchanged behavior; asset refs made relative
├── frontend_shared/              # NEW: shared portal assets (mounted at /shared)
│   ├── shared.css                # "Teal Medical" design tokens (ADR-0043; structure per ADR-0029) + Noto Sans
│   │                              #   Bengali; S23: last 12px radii → var(--radius), verbatim speaker display:block
│   ├── shared.js                 # TIER_LABELS (only place codes→labels), TIER_BANDS/tierBand (C2, display-only),
│   │                              #   fieldValue() (bilingual value_bn/value_en + {value} legacy), EN/BN helper, api()/showError()
│   ├── staff.js                  # queue render, phone lookup, verbatim panel, 10 editable field cards; S11:
│   │                              #   fully bilingual (labels+icons via t(), values via fieldValue(),
│   │                              #   staffLanguageRefresh() hook) — raw text re-rendered, never translated;
│   │                              #   S12: renderConditionCard() (C1 — portals opt in via #condition-card mount;
│   │                              #   the kiosk never has one)
│   ├── tts.js                    # speak() via speechSynthesis bn-BD (Step A1); text stays the fallback
│   └── motion.css                # NEW S37 (ADR-0059): depth/motion for the STAFF portals only (kiosk never
│                                  #   loads it). Elevation ladder, .fx-card 3D lift, queue tier rails + wait/
│                                  #   flag/meter chips, stat tiles, handover check rows, doctor timeline spine,
│                                  #   skeletons, role identity (portal-medic amber TRIAGE / portal-doctor indigo
│                                  #   CLINICAL), staff-only breakpoints, body pinned to 100vh (released in print).
│                                  #   EVERY animation + @keyframes is inside prefers-reduced-motion:no-preference.
├── frontend_medic/index.html     # NEW medic portal (at /medic/): login→queue→verbatim+fields→Assign & Forward;
│                                  #   S11: EN/বাংলা toggle (MEDIC-1), ↻ Refresh Queue (MEDIC-5), risk panel
│                                  #   with C2 bands + override control (MEDIC-3); S12: #condition-card mount
│                                  #   (MEDIC-4) + post-referral summary screen with weight inline-edit +
│                                  #   summary_report .docx download (MEDIC-6/7)
└── frontend_doctor/index.html    # NEW doctor portal (at /doctor/): login→queue→risk/red-flag/XAI panel→Override/Accept;
                                   #   S12: fully bilingual (renderSafety() from state), ↻ Queue removed (DOCTOR-1/2),
                                   #   print CSS + responsive nav (DOCTOR-7 base); S13: patient-details card +
                                   #   prescription form/.docx (DOCTOR-3..6); S23: "Submitted" Dhaka-time row (P3-1) +
                                   #   💊 M16 drug-info slide-in panel (P3-3 — textContent-only, disclaimer bar,
                                   #   hidden in print)
```

REMOVED in Session 4 (browser-only): `services/stt/**`, `api/routes_stt.py`, the per-provider
requirements files, the STT config/.env block. (Still gone.)

Run from the project root. App: `python -m uvicorn backend.app.main:app --reload --port 8001`
(use the venv's Python). Tests: `pytest backend/tests/` (**192 passing**). Schema is Alembic-managed
and migrates at startup — never delete the DB. Entry points: `/` (landing), `/kiosk.html`,
`/medic/`, `/doctor/`, `/legacy/`.

---

## Planned structure (final locked stack — built incrementally via the build plan)

> This is the target layout the Phase A–I build plan grows the repo into. It EXTENDS the
> current structure (same FastAPI + SQLite + plain-HTML stack — ADR-0025); it is not a rewrite.
> Each module gets its own small service file; the patient pipeline is orchestrated in one
> place; the doctor dashboard is a second static page. Build it folder-by-folder, with the
> human's "go" each step. Treat anything not yet on disk as TBD.

```
voice-medical-prescreener/
├── backend/
│   ├── app/
│   │   ├── main.py                     # adds the patient-flow + report + dashboard routers
│   │   ├── core/
│   │   │   ├── config.py               # + per-module model/provider settings (ADR-0026), TTS lang
│   │   │   └── llm_providers.py        # provider registry: Gemini Flash / Flash-Lite / Groq / OpenRouter (base_url+model+key, fallback order)
│   │   ├── api/
│   │   │   ├── routes_transcripts.py   # (existing) raw + correct + docs
│   │   │   ├── routes_documents.py     # (existing) list + download
│   │   │   ├── routes_intake.py        # NEW: POST /api/intake/text → runs M2→M3→M4→M6, returns summary + gaps
│   │   │   ├── routes_followup.py      # NEW: POST /api/followup/next (M7 question) · POST /api/followup/answer (M8 + M9 loop check)
│   │   │   ├── routes_report.py        # NEW: GET /api/report/{case_id} (M10 risk + red-flags, M11 XAI, M12 report; PDF later)
│   │   │   └── routes_dashboard.py     # NEW: doctor-facing list/detail/override (M14)
│   │   ├── services/
│   │   │   ├── correction/             # (existing) Corrector ABC + OpenAICompatibleCorrector  → reused as M2
│   │   │   ├── llm_client.py           # NEW: thin call(provider_key, prompt) wrapper w/ automatic fallback (uses llm_providers)
│   │   │   ├── extraction.py           # NEW M3: normalized text → structured entities (Gemini Flash-Lite)
│   │   │   ├── summary.py              # NEW M4: entities → 2–4 sentence chief-complaint summary (Gemini Flash)
│   │   │   ├── missing_info.py         # NEW M6: present-vs-missing checklist (fed directly by M4 — no emergency branch)
│   │   │   ├── followup.py             # NEW M7: gaps → prioritized questions (Groq); served as text + spoken via browser TTS
│   │   │   ├── profile_update.py       # NEW M8: re-run answers through M2/M3, merge into the case profile
│   │   │   ├── completion.py           # NEW M9: completeness score + loop-back decision (LOCAL / NO-API)
│   │   │   ├── risk.py                 # NEW M10: Low/Med/High/Critical + RULE-BASED RED-FLAG CHECK → forces Critical (ADR-0024)
│   │   │   ├── red_flags.py            # NEW: the red-flag phrase/rule list used by risk.py (chest pain, stroke signs, etc.)
│   │   │   ├── xai.py                  # NEW M11: plain-language reason for the risk level (Gemini Flash)
│   │   │   ├── report.py               # NEW M12: assemble full report incl. a Red Flags section (no diagnosis); PDF writer later
│   │   │   └── documents/              # (existing) DocxWriter + storage; PDF writer slots in behind the format seam
│   │   ├── pipeline/
│   │   │   └── orchestrator.py         # NEW: runs the patient journey M1→M2→M3→M4→M6→(M7→M8→M9 loop)→M10→M11→M12 (M13 store)
│   │   ├── schemas/
│   │   │   ├── transcript.py / document.py   # (existing)
│   │   │   ├── case.py                 # NEW: CaseProfile, Entities, Gaps, Question, Answer
│   │   │   └── report.py               # NEW: RiskResult (incl. red_flags[]), XAIReason, ClinicalReport
│   │   └── db/
│   │       ├── models.py               # + Case/Profile/Report/AuditLog tables (M13) via NEW Alembic revisions (never edit old ones)
│   │       └── migrations/versions/    # 0003+ add the new tables (ADR-0022 rule: new revision per schema change)
│   └── tests/                          # + test_extraction / test_risk_red_flags (TC-R1) / test_followup_loop / test_api_fallback / test_flow_m4_m6
├── frontend/                           # patient UI (Mintlify), plain HTML/JS — ADR-0025
│   ├── index.html                      # + TTS test button (Phase A), later the live follow-up Q&A view
│   ├── app.js                          # + speak(text) via window.speechSynthesis (bn-BD); voice-only answer capture
│   ├── tts.js                          # NEW (optional split): SpeechSynthesis helper + Bangla-voice selection
│   └── styles.css                      # (existing tokens)
├── frontend_doctor/                    # NEW: doctor dashboard (second static page; M14)
│   ├── index.html                      # report view: summary, risk + red flags, XAI, override/annotate
│   └── dashboard.js                    # fetches /api/dashboard + /api/report/{id}
├── requirements.txt                    # single cross-platform list (no new heavy deps for TTS — browser-native)
├── .env.example                        # + per-provider key names (GEMINI_API_KEY, GROQ_API_KEY, OPENROUTER_API_KEY) — names only
└── docker/                             # OPTIONAL Phase I: single Dockerfile + one compose file (one service — NOT microservices)
```

---

## Important file rules
- **Never commit secrets.** API keys live in a `.env` file that is gitignored.
  `.env.example` (committed) just lists the key *names*.
- **Raw vs corrected** must be obvious in both the code and the data layout
  (separate fields/files), per constitution rule #1.
- **One service file per module**, called through `pipeline/orchestrator.py`; keep each file
  small and reviewable (CLAUDE.md). LLM calls go through `llm_client.py` so the per-module
  provider + fallback (ADR-0026) is configured in ONE place, not scattered.
- **Schema changes = a NEW Alembic revision** (0003, 0004, …). Never edit an applied revision
  and never delete the DB (ADR-0022).
- **The red-flag check lives in `risk.py`/`red_flags.py` (Module 10)** — there is no separate
  emergency module/route/node anymore (ADR-0024).
