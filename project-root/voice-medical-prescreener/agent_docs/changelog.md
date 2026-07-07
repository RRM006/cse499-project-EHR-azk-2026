# changelog.md — Session-by-Session History

> The running memory of the project. **Newest entry at the top.**
> One short entry per session. This is what a new session reads to remember
> "what happened recently and why", so we never re-explain or re-litigate.
>
> Template for each entry:
> ```
> ## Session N — YYYY-MM-DD — <short title>
> - Did: <what we actually built or changed>
> - Decided: <any decision; also add it to decisions.md>
> - Broke / problem: <anything that failed or is fragile>
> - Deferred: <what we chose NOT to do yet, and why>
> - Next: <the one thing to do next — also update current_task.md>
> ```

---

## Session 15 — 2026-07-07 — Arch Linux TTS fix: diagnosed + documented (PART 1B)
- Did: chased down why the kiosk 🔊 button is **silent on the Arch laptop**. Read-only
  diagnostics confirmed it is **system-level, not a code bug**: `speech-dispatcher` and
  `espeak-ng` are **not installed** and the speechd service is inactive, so Linux Chromium's
  `speechSynthesis.getVoices()` is empty and `frontend_shared/tts.js` correctly degrades to
  text-only (ADR-0028). The existing `human_live_run_guide.md` only covered the **Windows**
  Bangla-voice install. Added a new **"🐧 PART 1B — Enable a Bangla voice on Arch Linux"**
  section right after the Windows PART 1: `sudo pacman -S speech-dispatcher espeak-ng`,
  `espeak-ng --voices | grep bn` + `spd-say` verification, "fully restart Chromium", the same
  `getVoices().filter(bn)` console check + "hint banner gone = ✅" success test, and a note that
  the espeak-ng Bengali voice is robotic (expected; text stays primary) and STT is unaffected.
  **No application code changed** — `_pickBanglaVoice()`/`banglaVoiceAvailable()` already match
  any `bn*` voice, so they start working once the packages exist.
- Decided: nothing at ADR level — this is a docs/system-setup step, not an architecture choice.
  Confirmed scope with the human: **TTS only** (their mic/STT works), and **stay on Chromium**
  (do NOT switch to Google Chrome).
- Broke / problem: the `pacman` install needs `sudo` and could not be run from the non-interactive
  agent shell, so the fix is **documented but NOT yet installed/verified** on the Arch box.
- Deferred: the human runs the one `pacman` line, then verify (espeak-ng bn voice + `spd-say`
  audible → Chromium `getVoices` non-empty → kiosk `#voice-hint` gone + 🔊 speaks = TC-V2 on Arch).
  Everything from S14 still pending too (the full live real-mic run + Windows Bangla voice + key rotation).
- Next: human installs `speech-dispatcher`+`espeak-ng`, then I verify the three checks above.

## Session 14 — 2026-07-07 — Step 20 of 20 (FINAL): test gate + status flips + doc sweep — BUILD COMPLETE
- Did: closed the 20-step fix/feature build. Re-ran the gate — `pytest backend/tests/` = **150
  passed**. Flipped all stale markers in `context_fixed_problem.md` to ✅ (its "Last updated" was
  2026-07-05, predating S11/S13): **KIOSK-4/5/6/7** (S11 steps 8–11; KIOSK-7 = ADR-0034),
  **MEDIC-1/2/5** (S11 step 12) + **MEDIC-3** (S11 step 13, ADR-0035), **DOCTOR-3** (S13 step 17),
  **DOCTOR-4/5** (S13 step 18, ADR-0038), **DOCTOR-6** (S13 step 19, ADR-0039), and **DOCTOR-7**
  🟨→✅ (S13 steps 17–19) — each with a one-line "Done" note; added a "BUILD COMPLETE" banner +
  refreshed the header date/ADR list. Every numbered spec item is now ✅ (no ⬜/🟨 left except the
  legend). Marked the 20-step build complete in `milestone_log.md` while **deliberately keeping the
  15-module status table 🟨** (those gate on the human live-voice run, not build completion).
  `test_log.md` got a one-line S14 gate entry. Also (same session): wrote a plain-language
  **`agent_docs/human_live_run_guide.md`** for the human — start-the-app, install a Bangla TTS
  voice on Windows, the live-test walkthrough (each step mapped to TC-V1/V2/V3/F2/R1), and
  key rotation (which key → which `.env` line → where to get a fresh one). Refreshed the stale
  **`CLAUDE.md`** status line (was "Session 8 / Alembic 0009 / 104 tests" → now Session 14 /
  Alembic 0010 / 150 tests / build complete, pointing at the new guide).
- Decided: nothing new — step 20 is a sweep, no ADR (ADR-0031–0039 already cover the build).
- Broke / problem: none. Docs-only; no application code, DB, or patient data touched.
- Deferred: NOT build work — the **human live real-mic run** (TC-V2/V3/F2/R1/A1, real keys already
  in `.env`) and installing a Bangla TTS voice on the Windows box (kiosk audio). Any polish the
  live run surfaces.
- Next: hand off to the human live run; there is no further coded step in the 20-step plan.

## Session 13 — 2026-07-06 — Steps 17–19 of 20: DOCTOR-3 patient-details · DOCTOR-4/5 prescription form · DOCTOR-6 prescription .docx + save
- Did (step 19, DOCTOR-6, ADR-0039): the prescription **Submit** now saves + downloads.
  New `render_prescription(payload)` in `services/documents/visit_docx.py` (LOCAL .docx:
  letterhead · patient · symptoms · **Diagnosis verbatim from payload** · medicines table ·
  advice/tests/follow-up · signature) and `generate_prescription_document()` in
  `services/documents/__init__.py` (render → store → `create_document(kind="prescription")` →
  persist a `prescriptions` row linked by `document_id`). New endpoint
  `POST /api/visits/{uuid}/prescription` (body `{doctor_id, payload}`; 404 visit/doctor, 400
  non-doctor; audit `prescription.created`; returns `{prescription_id, document}`). A **new**
  prescription + docx per Submit (append). Frontend: `submitPrescription()` POSTs, auto-downloads
  the .docx (anchor-click, like the medic), and shows a "✅ Saved & Downloaded" confirmation with a
  re-download link (the step-18 preview fn removed). The .docx writer reads ONLY the payload, so
  the Diagnosis is structurally un-AI-fillable (rule #2) — regression-tested. New
  `test_prescription_docx.py` (5). **150 tests pass** (145 + 5). Verified live: real POST created a
  prescription row + linked document, downloaded the .docx and confirmed it contains the diagnosis,
  medicine, clinic, patient; frontend Submit wiring checked with a stubbed POST (body/auto-download/
  confirmation), no console errors.
- Did (step 18, DOCTOR-4/5, ADR-0038): a **Prescription form** in the doctor portal.
  Backend (small, read-only): `GET /api/visits/{uuid}/prescription/context?doctor_id=`
  (new `routes_prescription.py` + `schemas/prescription.py`) returns **letterhead only**
  (clinic + doctor); 404 unknown visit/doctor, 400 non-doctor. Patient + the 10 symptoms
  are assembled client-side from the already-loaded case (no re-send). An idempotent
  `seed_demo_letterhead()` (new `backend/app/db/seed.py`, run in `lifespan`) fills the NULL
  letterhead columns on the demo clinic + doctors with sample values (never clobbers a real
  value). New `test_prescription_context.py` (6). **No prescription is persisted in step 18**
  — the DB row + .docx are created together at Submit in step 19 (DOCTOR-6). Frontend
  (`frontend_doctor/index.html`): "📝 Write Prescription" in the review bar opens a full-screen
  `#prescription-screen` form — letterhead (editable, prefilled) · Date · Patient
  (auto-filled) · Symptoms (auto-filled from `summary_fields`) · **Diagnosis EMPTY, doctor-
  authored, never AI-filled (rule #2)** · Medicines table with **add/remove rows** · Advice ·
  Tests · Follow-up · signature line. `rxDraft` state survives the EN↔বাংলা toggle;
  `collectPrescriptionPayload()` assembles the payload (empty medicine rows filtered);
  Submit shows an inline preview (the .docx/download replaces it in step 19). **145 tests
  pass** (139 + 6). Browser-verified (stubbed context): full autofill, empty Diagnosis,
  add/remove + language-toggle persistence, ≥1-row guard, payload correct, no console errors,
  screenshot of the rendered form.
- Did (step 17, DOCTOR-3, frontend-only, `frontend_doctor/index.html`): the doctor case
  view now shows — right after the safety panel — a **Patient Details card** (Name · Phone ·
  Age-from-`birth_year` · Gender · Weight · Blood Pressure) reading the patient embedded in
  `GET /visits/{uuid}` (`VisitDetailWithPatientOut`), with **inline weight + BP editing** that
  reuses `PATCH /patients/{id}/vitals` (already permits role=doctor — **zero backend change**);
  a mounted **`#condition-card`** so the shared `renderConditionCard()` surfaces the C1 AI
  suggestion + reasoning + "not a diagnosis" disclaimer (identical to the medic — closes part of
  DOCTOR-7); and the **C2 display band** (`tierBand()`) beside the risk tier badge in
  `renderSafety()`. New page functions: `onDoctorCaseLoaded()` (renders patient details then
  loads risk — replaces `loadRisk` as the `PORTAL.onCaseLoaded` hook), `renderPatientDetails()`,
  `saveVitals()` (weight range + ≥1-field validation), `genderLabel()`; `onLanguageChange()`
  re-renders the patient card. Bilingual throughout; raw verbatim + patient name are never
  translated (rule #1). **139 tests still pass** (no backend touched). Browser-verified with
  stubbed network: all 6 fields correct, band renders "HIGH 51–75%", condition card + disclaimer,
  EN↔বাংলা toggle, edit fires `PATCH /api/patients/42/vitals` body `{editor_id, weight_kg, bp}`
  and updates the card, empty/invalid-weight guards block the call, no console errors, screenshot
  confirms the layout order (safety → patient → condition).
- Decided: **ADR-0038** (step 18, form + read-only letterhead prefill; save deferred) +
  **ADR-0039** (step 19, dedicated `POST …/prescription` saves row + renders .docx; new
  prescription per Submit; Diagnosis structurally un-AI-fillable). Step 17 needed no ADR
  (reuses C1/ADR-0036, C2 band, ADR-0037).
- Broke / problem: none. The preview server stopped between edits twice (restarted cleanly);
  `preview_screenshot` worked this session. Note: the startup letterhead seed only runs on
  server (re)start.
- Deferred: Step 20 (final): full `pytest` sweep + doc sweep + flip the `context_fixed_problem`
  DOCTOR-3/4/5/6/7 (+ any still-open KIOSK/MEDIC/STRUCT) statuses to done; sanity-eyeball all
  three portals. The whole 20-step build then closes.
- Next: Step 20 — final test + doc sweep + `context_fixed_problem` status flips. See `current_task.md`.

## Session 12 — 2026-07-06 — Steps 14–16 of 20: C1 suggested condition (MEDIC-4) + post-referral summary & docx (MEDIC-6/7) + doctor toggle/polish (DOCTOR-1/2/7)
- Did: **Step 14 (MEDIC-4/C1, ADR-0036):** new module **M10C** (Flash bucket, deliberately a
  SEPARATE call from M10 so the risk prompt's no-disease-names rule is never contaminated)
  generates a bilingual "Possible Condition (AI Suggestion – Not a Diagnosis)" + reasoning at
  kiosk submit, best-effort (LLM down → no suggestion, submit never blocked). Stored at
  `case_profiles.entities["suggested_condition"]` (no migration) with 10-field-style provenance
  AND the "not a diagnosis" disclaimers embedded IN the object — every payload carrying the
  suggestion carries them. `PATCH /visits/{uuid}/profile/condition` staff edit (403 non-staff,
  all language slots untranslated, disclaimer re-attached server-side, audit `profile.condition_edit`).
  Shared `renderConditionCard()` in staff.js; medic mounts `#condition-card`; kiosk has no mount.
  New `test_suggested_condition.py` (5). **Step 15 (MEDIC-6/7):** "Submit & Forward" now lands on
  a bilingual post-referral summary (snapshot-as-referred): patient card (name/phone/age-from-
  birth-year/**weight inline-edit**/BP), risk tier + C2 band + flags + XAI, the disclaimered
  condition, all 10 Q&A rows, ⬇ Download Report (.docx) + Back to Queue. New
  `PATCH /patients/{id}/vitals` (staff-only, 0–500 kg validated, audit `patient.vitals_edit`);
  `GET /visits/{uuid}` now embeds the patient with vitals (`VisitDetailWithPatientOut`, defined in
  patient.py to avoid a schema import cycle). M12 report sections gain vitals +
  `suggested_condition`; the summary_report docx renders the C1 block with both disclaimers; and
  the docx is assembled from a **FRESH report at download time** — staleness after staff
  edits/overrides was the hidden "download doesn't really work" failure. New
  `test_medic_summary.py` (5, incl. the staleness regression). **Step 16 (DOCTOR-1/2/7):** doctor
  portal fully bilingual (EN/বাংলা toggle, data-en/bn on all chrome, safety panel re-renders from
  state via `renderSafety()`, placeholders switch); **↻ Queue removed** (auto-refresh + post-review
  reload already cover it; the medic's Refresh-Queue stays — it clears the phone filter);
  `@media print` block (case content prints, chrome doesn't); responsive flex-wrap.
  **139 tests pass** (129 + 5 + 5). All frontend steps browser-verified with stubbed network.
- Decided: ADR-0036 (C1 = separate M10C call; embedded disclaimer; staff-only; never the doctor's
  Diagnosis field); ADR-0037 (post-referral summary = snapshot + fresh-report-on-download +
  patient embedded in visit detail + patient-scoped vitals PATCH).
- Broke / problem: `preview_screenshot` worked early in the session then timed out again
  (S11 flakiness) — post-referral screen + doctor toggle proven via eval + a11y snapshot;
  worth a human eyeball of `/medic/` after a forward and `/doctor/` in বাংলা (Ctrl+F5 first).
- Deferred: Steps 17–20 (one per "go"): DOCTOR-3 patient-details card (17, mounts the shared
  condition card + vitals from the now-embedded patient) · prescription form (18, Diagnosis
  defaults EMPTY — rule #2, per ADR-0036) · prescription docx + save (19) · final sweep (20).
  DOCTOR-7 stays 🟨 until 17–19 land its remaining identification targets.
- Next: Step 17 — DOCTOR-3: patient-details card in the doctor portal. See `current_task.md`.

## Session 11 — 2026-07-06 — Steps 8–13 of 20: kiosk summary complete (KIOSK-4/5/6/7) + medic bilingual/polish/refresh (MEDIC-1/2/5) + risk override (MEDIC-3)
- Did: **Step 8 (KIOSK-4):** bilingual "Download Raw Transcript (.docx)" button on the kiosk
  summary screen (before Confirm & Submit), wired to the existing step-3 endpoint via a
  temporary-anchor click (kiosk page never navigates away); no backend change.
  **Step 9 (KIOSK-5):** summary redesigned — each of the 10 fields is its own card (18px
  radius, backdrop blur, soft shadow, icon chip 🩺⏱️📋🤒📖💊⚠️🔄🩹💬, bold primary-blue
  titles); clinically key fields (main problem, duration, symptom details, medicines,
  allergies) get a left accent border + value badge; empty = muted-italic "Not mentioned /
  উল্লেখ করা হয়নি"; clinical-blue tokens only. **Step 10 (KIOSK-6):** summary follows the
  language toggle end-to-end — `renderSummary()` reads via `fieldValue()`, profile kept as
  `state.lastProfile`, `onLanguageChange()` re-renders; legacy `{value}` rows display as-is.
  **Step 11 (KIOSK-7, ADR-0034):** resume loop live — `?scope=fields` on `followup/next`
  + `followup/answer` (no 0.7-threshold gate; missing = empty summary-field keys via new
  `missing_summary_fields()`; `target_gap` forced to a real field key so "নেই/জানি না"
  is never re-asked; SHARED per-visit question cap). Kiosk: progress chip ("৮/১০ তথ্য
  সম্পন্ন"), resume voice dock on the summary screen (one recognition engine serves both
  docks via `activeDock()`), Confirm & Submit hidden while a question is open, summary
  regenerates after every answer, FAIL-OPEN (cap/API-error → submit returns; never trap
  the patient). New `test_resume_loop.py` (5 tests). **Step 12 (MEDIC-1/2/5):** staff.js
  fully bilingual (labels+icons, badges, verbatim chrome via t(); values via fieldValue();
  new `staffLanguageRefresh()`), medic portal gets the EN/বাংলা toggle + data-en/bn on all
  static text; "↻ Queue" → "↻ Refresh Queue / তালিকা রিফ্রেশ" (clears the phone filter +
  reloads — its one clear job); field-card icon chips + queue hover in shared.css; doctor
  portal (shares staff.js) regression-checked. **Step 13 (MEDIC-3, ADR-0035):**
  `POST /api/visits/{uuid}/risk/override` — appends a `model_provider='human'`
  risk_assessments row (AI rows never edited), carries red_flags + rule_overrode forward,
  stores a reason (constitution), audit_logs from/to/reason; **red-flag Critical cannot be
  downgraded by staff (409)** — only the doctor decides at review. Medic risk panel: tier
  badge + C2 display band + AI/Human badge + red flags + XAI + override select (labels
  from TIER_LABELS, band per tier) + reason box. New `test_risk_override.py` (3 tests).
  **129 tests pass** (121 + 5 + 3). All frontend steps browser-verified with stubbed
  network (no live LLM spend).
- Decided: ADR-0034 (resume loop = `?scope=fields` on the existing endpoints; shared
  question cap; asked-once = answered); ADR-0035 (risk override = appended human row, no
  migration; red-flag-Critical downgrade blocked for staff).
- Broke / problem: `preview_screenshot` tool times out this session (page itself healthy —
  all assertions via eval/a11y snapshot); the step-9 visual is worth a human eyeball at
  /kiosk.html (Ctrl+F5 first).
- Deferred: Steps 14–20 (one per "go"): C1 suggested condition (14) · post-referral
  summary + docx (15) · doctor toggle+polish (16) · patient-details card (17) ·
  prescription form (18) · prescription docx + save (19) · final sweep (20). Real-M7
  resume-loop questions over Groq untested by design — covered by the next live-mic run.
- Next: Step 14 — MEDIC-4 / C1: "Possible Condition (AI Suggestion – Not a Diagnosis)"
  section (clearly labeled, disclaimer, editable; doctor's Diagnosis never AI-filled —
  needs its own ADR per the locked C1 note). See `current_task.md`.

## Session 10 — 2026-07-06 — Fix/feature build continues: steps 6–7 (KIOSK-1 OTP + KIOSK-2/3 TTS UX)
- Did: **Step 6 DONE (KIOSK-1):** `frontend/kiosk.js` gains `initOtpInputs()` — typing a
  digit auto-focuses the next `.otp-input` (repeated digits like 000000 flow smoothly),
  non-digits are stripped, Backspace on an empty box clears + focuses the previous one,
  and pasting fills the boxes from box 1 (junk stripped, e.g. "code: 04-73-92" → 047392;
  short pastes focus the next empty box). `kiosk.html` boxes gain `inputmode="numeric"`
  + `autocomplete="one-time-code"`. All 5 behaviors asserted live in Chrome + screenshot.
  **Step 7 DONE (KIOSK-2/3):** (a) ROOT CAUSE of "Repeat Question does nothing" found and
  CONFIRMED live: the button always fired — **this Windows machine has NO Bangla TTS voice**
  (`banglaVoiceAvailable() === false`), so speech was silently absent (TC-V2, recorded in
  test_log.md). Fix = make the state visible: a bilingual `#voice-hint` banner shows on the
  voice screen whenever no bn voice exists (chained onto tts.js's `onvoiceschanged`, not
  replacing it); on-screen text stays the fallback (ADR-0028). (b) `addBubble()` now puts a
  🔊 icon on EVERY chat bubble — assistant icon replays that question; patient icon reads
  back EXACTLY the words captured at bubble creation (rule #1, never re-fetched/rewritten).
  The Repeat-Question button is KEPT alongside the icons (KIOSK-2 and KIOSK-3 are separate
  spec items; the button is also the accessibility-friendly big target). Browser-verified
  via a `speak()` spy: both icons + the repeat button speak the exact right text; hint
  toggles correctly both ways. **121 tests pass** (frontend-only; no backend change).
- Decided: nothing new (no ADR — bug fix + spec'd UI; the keep-the-repeat-button call is
  recorded here).
- Broke / problem: Browser CACHE bit twice — a stale kiosk.js made the first verification
  round of step 6 report false failures. Rule for preview checks: `fetch(url,
  {cache:'reload'})` + reload BEFORE asserting. The human should Ctrl+F5 the kiosk once.
- Deferred: Steps 8–20 (one per "go"). Installing a Bangla TTS voice on the Windows box
  (Settings → Time & Language → Speech → Add voices → Bengali) so TC-V2 can PASS with
  audio — human action, worth doing before the re-run.
- Next: Step 8 — kiosk "Download Raw Transcript (.docx)" button wired to the step-3
  endpoint `POST /api/visits/{uuid}/documents/transcript` (KIOSK-4). See `current_task.md`.

## Session 9 — 2026-07-05 — Fix/feature build from the human's Part-2 test: steps 1–5 of 20
- Did: The human's real-mic Part-2 run surfaced bugs + feature gaps, written up as
  `agent_docs/context_fixed_problem.md` (stable IDs: STRUCT/KIOSK/MEDIC/DOCTOR). A 20-step
  sequenced plan was approved with all open decisions resolved: C1 = "Possible Condition
  (AI Suggestion – Not a Diagnosis)" allowed with disclaimer + editable, doctor's Diagnosis
  never AI-filled; C2 = display-only tier→band mapping, NO stored numeric risk scores;
  legacy → `/legacy/` + `/` landing page; prescriptions/reports DB-backed (documents.visit_id
  + kinds + prescriptions table, Alembic 0010); bilingual summary values generated once and
  stored (`value_bn`/`value_en`, back-compat with `{value}`); clinic/doctor letterhead in DB;
  KIOSK-7 = resume loop asking only missing fields, cap respected, "নেই/জানি না" accepted.
  **Step 1 DONE (STRUCT-1/2, ADR-0031):** legacy demo `git mv`-ed to `frontend_legacy/`
  (asset refs made relative), mounted at `/legacy/`; new clinical-blue landing page at `/`
  linking all four entry points; `ENTRY_POINTS` list logged at startup; new
  `test_routes_static.py` (5 tests). **Step 2 DONE (ADR-0032):** Alembic rev
  `0010_prescriptions_letterhead` written AND applied to the real DB (backup
  `prescreener.db.pre-0010.bak`): `documents.utterance_id` now nullable (visit-grain
  exports), `patients.weight_kg`+`bp`, users/clinics letterhead columns, new
  `prescriptions` table (payload JSON, document_id link). Discovery that shrank the step:
  `documents.visit_id` already existed since 0003 and `patients` already had
  `birth_year`/`sex` — no duplicates added. Models updated (+`Prescription`); new
  `test_migration_0010.py` (4 tests incl. rule-#1 raw-preservation across the rebuild).
  architecture.md gained §8 (rev-0010 deltas). **Step 3 DONE:** visit-grain docx seam —
  new `services/documents/visit_docx.py` (full-visit RAW transcript writer, verbatim
  role-labeled turns; staff summary-report writer rendering the stored M12 sections with
  bilingual field labels + red flags + disclaimer), `generate_visit_document()` orchestrator
  (documents row: `visit_id` set, `utterance_id` NULL), `create_document` repo + DocumentOut
  schema extended (both grains), new route `POST /api/visits/{uuid}/documents/{kind}`
  (`routes_visit_documents.py`; download reuses `/api/documents/{id}/download`). New
  `test_visit_documents.py` (3 tests: byte-exact raw turns, field labels/values/disclaimer,
  route guards). **Step 4 DONE:** `shared.js` gains `fieldValue(field)` (bilingual summary
  values: picks `value_bn`/`value_en` by the active language, falls back cross-language,
  then to the legacy `{value}` shape, then ''; display-only, never writes back) and the C2
  `TIER_BANDS` map + `tierBand(tier)` (fixed display-only percentage band per tier — no
  numeric score generated/stored/wired). Verified live in the browser preview (all shapes +
  fallbacks + bands correct, zero console errors). **Step 5 DONE (ADR-0033):** M3/M8 now
  emit BOTH `value_en` + `value_bn` per field in ONE extraction call ({"en","bn"} reply
  shape; plain-string replies salvaged as English); stored shape `{value, value_en,
  value_bn, source, ...}` with `value` mirroring `value_en` so every legacy consumer/row
  works; M9 `field_has_text()` counts any slot; staff PATCH edits write the typed text to
  ALL slots untranslated (authoritative, no quota); `visit_docx._field_value()` falls back
  across slots. Test fakes updated + new `test_bilingual_fields.py` (5 back-compat tests)
  + a staff-PATCH slot assertion. **121 tests pass** (104 + 5 + 4 + 3 + 5).
- Decided: ADR-0031 (legacy isolation + landing page + startup URL log); ADR-0032 (rev 0010:
  one documents table with two grains, DB letterhead, prescriptions payload as JSON,
  human-only Diagnosis per C1, no stored risk scores per C2); ADR-0033 (bilingual values:
  one extraction call fills en+bn, `value` mirrors value_en, staff edits fill all slots
  untranslated).
- Broke / problem: Nothing. Note: legacy `index.html` used absolute `/styles.css`+`/app.js` —
  would have 404'd under `/legacy/`; caught before shipping, made relative.
- Deferred: Steps 6–20 (kiosk fixes KIOSK-1..7, medic MEDIC-1..7, doctor DOCTOR-1..7,
  final doc sweep) — one approved step at a time. Note: values stored by OLD intake runs
  stay English-only until re-extracted; new runs are bilingual.
- Next: Step 6 — kiosk OTP auto-advance + Backspace + paste (KIOSK-1). See
  `current_task.md`.

## Session 8c — 2026-07-03 — Live-run Part 1 PASSED: full pipeline live with real keys, all three buckets verified
- Did: (A) Added the human-provided **GROQ_API_KEY + OPENROUTER_API_KEY** to `backend/.env`
  (Gemini untouched) — the Session-8b key gap is CLOSED. (B) Ran **live-run Part 1** end-to-end
  with SYNTHETIC typed Banglish (no mic): phone lookup → stub OTP → visit → 2 utterances →
  `/intake` → follow-up loop (2 real Bangla questions from Groq, loop exited at completeness
  0.7) → `/assess` (tier=medium, no red flags — correct for headache+mild fever) → `/report`.
  (C) Verified `module_events`: **13 rows, all status=ok, ZERO fallbacks** — M3/M8=
  gemini_flash_lite, M4/M10/M11=gemini_flash, M6/M7=groq, M12=local — exactly the ADR-0026
  bucket map, live. Latencies 484–8577 ms. (D) `pytest backend/tests/` still **104 passing**.
  Numbers in test_log.md.
- Decided: nothing new (this executes the existing plan; no ADR).
- Broke / problem: Only a cosmetic Windows console issue: printing Bangla from a driver script
  needs `PYTHONIOENCODING=utf-8` (cp1252 UnicodeEncodeError) — not a code bug, backend unaffected.
  Note: the keys were pasted in chat; `.env` is gitignored so the repo is safe, but rotate the
  keys before any public demo.
- Deferred: **Part 2 — the human real-mic kiosk run** (TC-V1/V2/V3/F2/R1 + a live TC-A1
  pull-a-key test) — inherently the human's job. Then `.docx` per-visit report export, optional
  PDF, Phase-1 faster-whisper. Still: ~50 samples + WER, real SMS OTP/auth, encryption at rest.
- Next: Human does Part 2 in Chrome (`/kiosk.html` → speak → follow-ups → submit → `/medic/` →
  forward → `/doctor/` → review) and records TC-V2/V3/F2/R1/A1 in test_log.md. See
  `current_task.md`.

## Session 8b — 2026-07-03 — ADR-0029 doc rewrite executed + FIRST live Gemini verification
- Did: (A) Executed the deferred **ADR-0029 design-system switch in the docs**: CLAUDE.md's
  frontend section now points at the clinical-blue system (`frontend_shared/shared.css`) as the
  source of truth (with the TIER_LABELS rule + Noto Sans Bengali + the read-only-raw rule) and its
  status/stack lines updated; `DESIGN-mintlify.md` got a **SUPERSEDED banner** at the top (ADR-0029)
  with a compact clinical-blue token summary, keeping the old Mintlify analysis only as historical
  reference. (B) Ran the **first-ever LIVE LLM call** in the project: one real Gemini correction on
  synthetic Banglish — see test_log.md.
- Decided: nothing new (ADR-0029/0030 already stand; this executes them).
- Broke / problem: **Live-run gap surfaced, not a code bug:** only `GEMINI_API_KEY` is set;
  `GROQ_API_KEY` and `OPENROUTER_API_KEY` are EMPTY. Since M6 (gaps) + M7 (follow-up) are assigned
  to the Groq bucket with OpenRouter as the only fallback, a FULL live intake/loop cannot complete
  until a Groq OR OpenRouter key is added. All of it passes offline (LLM faked) — purely a missing
  key, not a code issue.
- Deferred: The full live pipeline (blocked on a Groq/OpenRouter key) and the human mic test
  (I cannot operate a real microphone — the voice portion is inherently the human's part).
- Next: Add a Groq (or OpenRouter) key to `backend/.env`, then run a full live pipeline with
  synthetic typed text; separately, the human does the real-voice kiosk run in Chrome. Record
  TC-V2/V3/F2/R1/A1. See `current_task.md`.

## Session 8 — 2026-07-03 — Mockup reconciliation + FULL-STACK BUILD: DB 0003–0009, backend M3–M12 pipeline, three portals
- Did: The biggest build session so far. (A) **Reconciliation:** reconciled `mockups-redesign.html`
  against architecture.md → new `agent_docs/reconciliation.md` + architecture.md §7. Human decided:
  'medic' is a real role; OTP is a stub; the mockup's clinical-blue design system replaces Mintlify
  (ADR-0029). (B) **Database:** Alembic revs **0003–0009 all written AND applied** to the real DB
  (backup .bak per rev): clinics/users/patients/visits (+'medic' role, 'awaiting_doctor' status,
  `assigned_doctor_id` — ADR-0030), case_profiles, module_events, followup_questions,
  risk_assessments, xai_explanations, reports, doctor_reviews, feedback, audit_log. Legacy
  utterances backfilled onto synthetic closed visits; seeds: 1 clinic, 1 medic, 2 doctors, 1 admin.
  (C) **Backend:** visits API + phone lookup + stub OTP (`DEV_OTP`); LLM provider registry +
  fallback + module_events logging (ADR-0026 as data); intake M3→M4→M6 writing the enforced
  10-field `summary_fields` JSON; follow-up loop M7 (Groq, no repeats, question stored + spoken)
  → M8 (merge; human edits never overwritten) → M9 (LOCAL completeness, threshold/max-turn exit);
  **M10 risk with the LOCAL red-flag rule list (5 categories, Bangla/Banglish/English) that forces
  Critical and survives total LLM outage** + M11 XAI (deterministic fallback reason); local M12
  report (Red Flags section + no-diagnosis disclaimer); staff endpoints (submit→auto-assess,
  dashboard queues, field-edit PATCH, assign); doctor review (accept/override→'reviewed') +
  feedback; audit rows on every state change. (D) **Frontend:** `frontend_shared/` (clinical-blue
  CSS, TIER_LABELS, EN/BN helper, tts.js `speak()` — Step A1 shipped), patient kiosk at
  `/kiosk.html` (phone→OTP→voice chat with STT bn-BD + TTS→10-field summary→submit→auto-logout),
  medic portal `/medic/`, doctor portal `/doctor/`. Old Module-1 app at `/` untouched.
- Decided: ADR-0029 (mockup clinical-blue design system supersedes Mintlify) and ADR-0030
  (medic role, `assigned_doctor_id`, 'awaiting_doctor', stub OTP, 10-field JSON shape, tier
  display labels, OTP-typing clarification) — both written to decisions.md mid-session.
  Implementation choices: M12 report assembly is LOCAL (no quota); model failure in M10 degrades
  to 'medium', never 'low' (rule #3); each legacy utterance = its own closed visit.
- Broke / problem: (1) Found + FIXED a pre-existing crash: this Windows machine's DB was a
  MIXED-state legacy DB (had `stt_provider`, lacked `documents.kind`) — the old blind
  stamp-at-0001 died with 'duplicate column'; `database.py` now picks the stamp revision from the
  ACTUAL columns (regression-tested). (2) alembic wasn't installed in the Windows venv (S6 ran on
  Arch) — installed from requirements.txt. (3) Batch-mode FKs need explicit names (0003 fixed).
- Deferred: Real SMS OTP, real auth (still stubbed), PDF export, per-visit report .docx export,
  Postgres (G7 = config), Phase 1 faster-whisper. CLAUDE.md + DESIGN doc rewrite per ADR-0029
  (awaiting explicit go). LIVE end-to-end run with real Gemini/Groq calls — the human's manual
  check (quota). Still from S4–S6: live mic test + ~50 samples + WER/latency.
- Next: Human live test in Chrome (`/kiosk.html` → speak → follow-ups → submit → `/medic/` →
  forward → `/doctor/` → review), with real keys in backend/.env; record TC-V2/V3/F2/R1/A1
  results + Bangla-voice availability per OS in test_log.md. Then the ADR-0029 doc rewrite.
  See `current_task.md`.

## Session 7 — 2026-06-25 — Architect planning lock: flowchart + final stack + per-module API strategy + voice model
- Did: A planning-only session (NO code). Locked the FINAL project plan ahead of vibe-coding.
  (A) **Flowchart:** removed the standalone Emergency module from the Patient Journey diagram —
  deleted node `D1` ("Emergency Detected?"), node `AX` (escalation alert), the `M4→D1`, `D1→No→M6`,
  `D1→Yes→AX` and the dashed `AX→` continuation arrows; added a direct `M4→M6` arrow; dropped the
  now-unused `DECA`, `ALTB`, `RA` styles and the "Emergency" legend entry. Reconstructed the whole
  TikZ source into `update_system_flowchart.md` (the original file was NOT in the uploaded set —
  marked as a reconstruction to diff against the real one). (B) **Safety preserved:** folded a
  lightweight **rule-based red-flag check into Module 10 (Risk Assessment)** that forces the
  **Critical** tier for clearly life-threatening symptoms, with a **Red Flags** section in the M12
  report; revised constitution rule #3 from "emergency detection runs first" to "surface red flags;
  never reassure falsely". (C) **Stack:** CONFIRMED the existing stack (no rewrite) and **added
  browser TTS** for M7 + a deploy path. (D) **API strategy:** assigned each LLM module across three
  independent free quota buckets (Gemini Flash / Gemini Flash-Lite / Groq) with OpenRouter `:free`
  as universal fallback. (E) **Voice:** patient input is **voice-only**; M7 questions show as **text
  AND play as audio (TTS) simultaneously**; manual text box demoted to a mic-failure fallback.
  (F) Rewrote the tracking docs (CLAUDE.md, constitution.md, Context, decisions.md, changelog.md,
  current_task.md, milestone_log.md, test_log.md, codebase_map.md; session_protocol.md unchanged).
- Decided: ADR-0024 (retire Emergency module, fold red-flag check into M10, keep numbering with an
  M5 gap), ADR-0025 (confirm stack + add browser TTS + deploy path), ADR-0026 (per-module free-API
  assignment, refines ADR-0003), ADR-0027 (voice model: STT `bn-BD` + `SpeechSynthesis` TTS,
  voice-only patient replies, manual text = fallback), ADR-0028 (follow-up = on-screen text AND
  spoken audio simultaneously).
- Broke / problem: Nothing built, so nothing broke. **Open conflict flagged, not silently resolved:**
  removing the Emergency module contradicts the *original* non-negotiable rule #3 and the Module
  10/12 dependency columns — this is a SAFETY-relevant change for a medical tool, so it is recorded
  as Open Flag 1 (recommended default: keep the rule-based red-flag check in M10, which is how the
  files are now written). `update_system_flowchart.md` is a reconstruction — node positions / exact
  fill colours are best-effort and must be diffed against the real file before committing.
- Deferred: Building any of the new modules (M2–M15) — still Phase 0. The actual M7 TTS code, the
  per-module provider config wiring, and the OpenRouter $10 top-up decision. Still deferred from
  S4/S5/S6: the human live mic test + ~50 samples + WER/latency on real speech.
- Next: First coding task = **Phase A / Step A1** of the build plan — add browser **TTS** to the
  existing frontend (speak a test Bangla string via `speechSynthesis`, on-screen text stays as
  fallback), planned-then-approved per CLAUDE.md before any code. See `current_task.md`.

## Session 6 — 2026-06-21 — Two separate raw/corrected .docx + Alembic migration (fix stt_provider bug)
- Did: (A) FIXED the live `sqlite3.OperationalError: table utterances has no column named
  stt_provider` by adopting **Alembic**. New `backend/alembic.ini` + `backend/migrations/`
  (env.py reads the URL from app settings, `render_as_batch=True` for SQLite) with two
  revisions: `0001_baseline` (original schema) and `0002` (adds `utterances.stt_provider` +
  `documents.kind`). `init_db()` now runs `run_migrations()` — stamps the baseline on a
  legacy DB, then `upgrade head`; fresh DBs build from scratch; re-runs no-op. Verified on
  the REAL db (2 rows preserved) + a fresh db; backed up the pre-migration db to
  `backend/data/prescreener.db.pre-alembic.bak`. (B) Split document export into TWO separate,
  independently downloadable files: added `documents.kind` ("raw"|"corrected"; legacy
  "combined"); `DocumentWriter.render(utterance, *, kind)` → DocxWriter renders raw-only
  ("Transcript") or corrected-only ("Corrected Transcript"); `generate_session_document(kind=…)`;
  repo `create_document(kind=…)` + `get_latest_document`. New routes (kept `/api/*`):
  `GET /api/transcripts/{id}` (TranscriptDetailOut: raw+corrected text + both doc links),
  `POST /api/transcripts/{id}/documents/raw`, `…/documents/corrected`; `/api/correct` now
  best-effort generates the CORRECTED doc and returns the detail. (C) Frontend: raw is now
  saved + a raw .docx generated when recording STOPS (not only on Correct); added per-panel
  "Download Raw/Corrected .docx" buttons (enabled when each file exists), loading states
  (Saving…/Generating document…/Correcting text…), and the exact spec error strings.
  (D) Config: added `STT_PROVIDER` + `DOCUMENT_OUTPUT_PATH` (alias of DOCUMENTS_DIR) +
  documented `DATABASE_URL`; updated `.env.example` and `.env`. Added a `backend-linux`
  launch.json config (the existing one is Windows-only `.venv/Scripts/python.exe`).
- Decided: Alembic + auto-migrate-at-startup with legacy baseline-stamp (ADR-0022); raw and
  corrected exported as SEPARATE docs via a `documents.kind` column, dedicated documents
  table kept over flat path columns, `/api/*` prefix kept (ADR-0023, decided with the human).
- Broke / problem: One real issue surfaced at END of session — `preview_start` failed with
  `spawn .venv/Scripts/python.exe ENOENT`: the DEFAULT `.claude/launch.json` config uses the
  WINDOWS venv path, which doesn't exist on Arch. Workaround: launch the new `backend-linux`
  config (`.venv/bin/python`) explicitly — that starts cleanly (earlier this session the
  server ran fine that way). NOT yet OS-robust (no single launch.json default works on both
  machines; the preview panel picks the first config). Test gotchas fixed during dev:
  TestClient runs sync endpoints in a threadpool, so the route test needed `StaticPool` to
  share the in-memory SQLite across threads; the preview screenshot tool timed out (renderer),
  but functional verification via preview_eval was conclusive. A synthetic session #3 raw doc
  was created in the dev DB during verification (harmless; gitignored, like S5's session #5).
- Deferred: LIVE Gemini correction in-browser + opening both .docx in Word/LibreOffice to
  confirm Bangla renders (human's manual check — not auto-run to save free quota). PDF /
  Markdown writers (format seam ready), version-history UI, auth, cloud storage, Patient/Visit
  tables. Still deferred from S4/S5: the human live mic test + ~50 samples + WER/latency.
- Next: Human live test in Chrome — record → Stop (raw .docx auto-saves + downloads) →
  Correct (corrected .docx) → open both, confirm Bangla renders + RAW unchanged; collect
  samples. See `current_task.md`.

## Session 5 — 2026-06-21 — Auto-generate & store .docx per session + Saved Documents UI
- Did: Added automatic Word-document export for completed sessions (additive, nothing
  existing broken). New `Document` SQLAlchemy model (UUID PK, FK → Utterance, format,
  filename, rel_path, created_at) + repo `create_document`/`get_document`/
  `list_documents`. New `services/documents/` layer: `DocumentWriter` ABC, `DocxWriter`
  (python-docx; renders Raw verbatim + Corrected + metadata; Bengali font set on Latin
  AND complex-script slots), `storage.py` filesystem abstraction (S3-swappable), and a
  `build_writer()` seam + `generate_session_document()` orchestrator. New routes
  `GET /api/documents` (list) and `GET /api/documents/{id}/download` (FileResponse, Word
  media type). `/api/correct` now best-effort generates the .docx after a successful
  correction (a docx failure logs but never fails the correction). Added `documents_dir`
  config (env-overridable, default `backend/data/documents`, no hardcoded paths) and
  `python-docx==1.1.2` to requirements.txt. Frontend: "Saved documents (.docx)" panel
  (Mintlify-styled) listing docs with download links, auto-refreshed after correction.
- Decided: A `.docx` is a DERIVED export artifact; the DB stays the source of truth
  (regenerable, preserves rule #1, avoids Bangla round-trip loss). python-docx (pure
  Python, cross-platform). Filesystem storage now, behind a swappable interface.
  Document grain = one Utterance/session; NO Patient/Visit tables yet. DOCX now, PDF
  later (clean `format` seam). (ADR-0021.)
- Broke / problem: Nothing broke. Note: passing a multi-line python `-c` with Bangla
  string literals through PowerShell mangled the quotes — used a temp script file
  instead (deleted after). Port-8000 orphaned-socket workaround (port 8001) still stands.
- Deferred: PDF generation + in-browser preview; Patient/Visit data model; auth on the
  document routes; cloud (S3/MinIO) storage. All have seams left in place. Still
  deferred from S4: the human live mic test + ~50 samples + WER/latency.
- Next: Human live test — record/correct in Chrome, confirm a .docx auto-saves and
  downloads + opens correctly (Bangla renders), alongside the mic/sample collection.

## Session 4 — 2026-06-20 — Simplify to browser-only STT + Mintlify UI + scrollable panels
- Did: (A) REMOVED the multi-provider STT architecture per the human's new plan —
  deleted `backend/app/services/stt/`, `api/routes_stt.py`, `test_stt_registry.py`,
  the three `requirements-*.txt`, all STT config + the `.env` STT block,
  `python-multipart`, and the startup health log. Recreated the venv from
  requirements.txt (clean core: fastapi 0.115.6, starlette 0.41.3; torch/
  transformers/qwen gone). Module 1 STT is now ONLY the browser Web Speech API.
  Rewrote the frontend for continuous recording: no cap, append-only verbatim
  transcript, brief pauses keep going (restart on `onend`), auto-stop after ~10s
  of silence. (B) Restyled the whole frontend to `DESIGN-mintlify.md` (Inter font,
  black pill buttons, mint-green accent for Start + active, 12px cards, hairline
  borders) and made the 3 transcript panels (Raw/Corrected/Manual) fixed-height,
  scrollable, with stick-to-bottom auto-scroll. Added the Frontend/Transcript-UI
  rules to CLAUDE.md.
- Decided: Browser Web Speech API is the only Module 1 STT (others return later);
  keep a clean seam (the `stt_provider` column stays). Drop the banglaspeech2text
  package permanently. Frontend follows DESIGN-mintlify.md. (ADR-0019, ADR-0020.)
- Broke / problem: A previous session left an ORPHANED socket holding port 8000
  (process dead, leaked handle keeps it LISTENING; clears on reboot). Worked around
  by switching `.claude/launch.json` to **port 8001**.
- Deferred: Live mic test of the continuous-recording + 10s-silence behavior (the
  human's manual check in Chrome). Collecting ~50 samples + WER/latency. Switching
  launch.json back to 8000 after a reboot. Regenerating the (now-removed) Groq key
  is moot since Groq STT was removed.
- Next: Human does the live mic test (speak, pause briefly, then go silent ~10s to
  confirm auto-stop) and collects samples. See `current_task.md`.

## Session 3 — 2026-06-19 — Multi-provider STT (5 providers) + provider health + installs
- Did: Re-planned Phase 0 to support 5 swappable STT providers with frontend
  switching. Built `backend/app/services/stt/` (STTProvider ABC + ProviderInfo
  health + registry + audio.py decode + 5 providers: browser_webspeech,
  groq_whisper, local_whisper, banglaspeech2text, qwen_asr). Added endpoints
  `GET /api/stt/providers`, `POST /api/transcribe`, `POST /api/transcripts`;
  refactored `/api/correct` to correct by utterance_id; added `Utterance.stt_provider`.
  Rewrote the frontend (provider dropdown + status badges, Start/Stop, MM:SS timer
  with 5-min auto-stop, raw/corrected copy+clear, manual fallback, error banner).
  Added a startup STT health log. Then FIXED 5 issues the human reported: documented
  QWEN_ASR_MODEL_DIR (optional, auto-download); rich provider health
  (available/missing_api_key/missing_package/missing_model/unsupported_platform/error)
  shown in the UI; resolved the huggingface-hub dependency conflict; split installs
  into per-provider requirements files; wrote INSTALL.md. INSTALLED all engines and
  verified the local transcribe paths.
- Decided: Drop the unmaintained `banglaspeech2text` pip package (pins
  huggingface-hub==0.11.1) and run shhossain/whisper-*-bn via `transformers`
  instead. Per-provider optional requirements files. Server STT = record→upload→
  transcribe; browser stays live. (ADR-0015 to ADR-0018.)
- Broke / problem: `requirements-local.txt` had a real conflict (fixed by the split).
  `torch==2.5.1` pin had no Python-3.14 wheel → unpinned (got torch 2.12.1).
  `qwen-asr` is INVASIVE: it bumped fastapi 0.115→0.137, starlette→1.3, transformers
  5→4.57, huggingface_hub→0.36 and pulled gradio/flask. App still works (13 tests
  pass, server boots) but Qwen may warrant its own venv.
- Deferred: Live Groq STT test (would spend the human's free quota). Qwen live run
  (3.4 GB download + very slow on CPU) — installed/ready but unverified. WER/latency
  on real Bangla speech. Regenerating the exposed Groq key (human action).
- Next: Human runs the live mic test for each provider in Chrome, collects ~50
  samples, and records real latency/WER. See `current_task.md`.

## Session 2 — 2026-06-19 — Phase 0 Steps 3–5: correction service + API + frontend
- Did: Built the correction service (Step 3): `services/correction/base.py`
  (`Corrector` ABC) + `openai_compatible.py` (`OpenAICompatibleCorrector` +
  `build_corrector()` + strict prompt + manual `__main__` live check) and
  `test_corrector.py` (4 offline guards). Built the API (Step 4):
  `schemas/transcript.py`, `api/routes_transcripts.py` (`POST /api/correct`,
  `GET /api/transcripts`), and `main.py` (lifespan `init_db`, `/health`, serves
  frontend or a placeholder). Built the frontend (Step 5): `frontend/index.html`,
  `app.js` (Web Speech API bn-BD, interim grey / final verbatim), `styles.css`.
  Fixed `.claude/launch.json` to use the venv Python. Ran the server via the
  preview tool and verified the page renders with no console errors.
- Decided: `POST /api/correct` persists RAW *before* calling the LLM, so raw
  survives a correction failure (502 with raw kept); misconfig fails fast (500).
  Recorded as ADR-0013.
- Broke / problem: `launch.json` first used system `python` (no uvicorn) → fixed to
  `.venv/Scripts/python.exe` (Windows-specific; Arch needs `.venv/bin/python`).
- Deferred: Live Gemini call NOT auto-run (spends free-tier quota) — left as a
  manual check for the human. No automated test for `/api/correct` (would hit the
  network). Groq/OpenRouter still interface-only. Frontend = plain HTML/JS (React later).
- Next: Step 6 — human runs the end-to-end live mic test in Chrome on both
  machines and collects ~50 sample utterances. See `current_task.md`.

## Session 1 — 2026-06-19 — Phase 0 scaffolding + backend skeleton (Steps 1–2)
- Did: Approved the Phase 0 plan, then built the foundation (not a throwaway
  demo folder): `requirements.txt`, `.gitignore`, `backend/.env` + `.env.example`,
  and the backend skeleton — `backend/app/core/config.py` (pydantic-settings),
  `backend/app/db/` (database.py, models.py `Utterance`, repository.py), and
  `backend/tests/test_raw_immutable.py`. Installed deps in `.venv` and ran tests.
- Decided: Build the real `backend/` + `frontend/` structure now (foundation for
  the full app); SQLite via a repository layer; one FastAPI server serving the
  frontend; mic + manual-text fallback; correction via the OpenAI-compatible
  client pointed at Gemini (swappable). Recorded as ADR-0009 to ADR-0011.
- Broke / problem: Pinned `SQLAlchemy==2.0.36` crashed on Python 3.14.4
  (typing-union `__getitem__` bug). Fixed by upgrading to `2.0.51` and re-pinning.
- Deferred: Gemini code + the actual network call, API routes, frontend
  (Steps 3–5). Groq/OpenRouter fallback (interface only). The human still needs to
  REGENERATE the pasted Gemini key and put it in `backend/.env`.
- Next: Step 3 — correction service (`Corrector` ABC + `OpenAICompatibleCorrector`
  with the strict correct-only prompt). See `current_task.md`.

## Session 0 — 2026-06-18 — Project setup & memory system
- Did: Created the project memory system: `CLAUDE.md` plus `agent_docs/`
  (constitution, milestone_log, current_task, changelog, test_log, decisions,
  codebase_map, session_protocol). No code yet.
- Decided: Locked in the starting stack and key choices — recorded as
  ADR-0001 to ADR-0008 in `decisions.md`.
- Broke / problem: None (nothing built yet).
- Deferred: All actual coding. AMD-GPU acceleration deferred (CPU-only first).
  Real Bangla-fine-tuned model deferred to Phase 2.
- Next: Build the Phase 0 demo (browser Web Speech API live Bangla transcription
  + free-LLM correction). Plan it with the human before coding.
  See `current_task.md`.
