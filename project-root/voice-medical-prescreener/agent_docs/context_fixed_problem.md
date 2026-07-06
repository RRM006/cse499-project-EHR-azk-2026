# context_fixed_problem.md — Full-Stack Bug & Feature Spec

> This answers one question: **"What is broken or missing in the new full-stack app,
> and exactly what should it do instead?"**
> It is the work spec for the current build. Each item has a stable ID so the plan,
> the changelog, and the tests can all point back to it. Preserve Bangla strings verbatim.

**Status keys:** ⬜ Not started · 🟨 In progress · 🟦 Blocked (needs a decision) · ✅ Done

> ✅ **BUILD COMPLETE (Session 14, 2026-07-07):** every numbered item below is Done. The
> 20-step plan is fully implemented (Sessions 9–13); 150 tests pass. What remains is NOT
> build work — it is the **human live real-mic run** (TC-V2/V3/F2/R1/A1 with the real keys
> in `.env`) and installing a Bangla TTS voice on Windows (the ⚠ HUMAN notes below).

**Last updated:** 2026-07-07
**Related docs:** `constitution.md` (rules #1–#4), `architecture.md`, `codebase_map.md`,
`decisions.md` (ADR-0024–0029 + ADR-0031–0039), `milestone_log.md`, `current_task.md`.

---

## 0. The big picture

Backend runs at port **8001**:
`python -m uvicorn backend.app.main:app --reload --port 8001`.

Right now `http://127.0.0.1:8001/` still opens the **old Phase-0 demo**
("Voice Medical Pre-Screener — Phase 0 demo"). That demo has these features:
RAW transcript · Corrected transcript · Corrected `.docx` · Manual text fallback ·
"Recently saved (raw → corrected)" · "Saved documents (.docx)".

The four core artifacts the old demo produces, for reference:

| Artifact | What it is |
|---|---|
| **Raw transcript** | What the patient says into the mic in real time (Bangla / Banglish), transcribed unchanged. |
| **Raw `.docx`** | The same raw words, written out as a Word document. |
| **Corrected transcript** | If the raw transcript came out badly, an AI API corrects it **without changing what the patient said** (rule #1). |
| **Corrected `.docx`** | The corrected words, written out as a Word document. |

We are now building the **final full-stack version** (patient kiosk + medic + doctor). The bugs
and features below are what has to be fixed/built. **The old demo must not be deleted** — it must
be kept and made to work — but it needs to be cleanly separated in the codebase so it is easy to
understand and **cannot affect the new full-stack version**.

### 0.1 — Structural isolation of the legacy demo · ✅ (Session 9, step 1 — ADR-0031)
- **STRUCT-1 ✅:** Phase-0 demo moved to `frontend_legacy/` (git mv; asset refs made relative),
  served at **`/legacy/`**, behavior unchanged; its `/api/*` routes untouched. Not deleted.
- **STRUCT-2 ✅:** `/` is now a clinical-blue landing page linking all four entry points
  (kiosk / medic / doctor / legacy); `main.py` logs the `ENTRY_POINTS` list at startup.
  Guarded by `backend/tests/test_routes_static.py` (5 tests).
- ✅ **DECISION RESOLVED (human):** "4 links" = the **four app entry points**; route = `/legacy/`.

---

## 1. Patient Kiosk — `http://localhost:8001/kiosk.html`

### KIOSK-1 · OTP verification · ✅ (Session 10, step 6)
Typing a digit auto-advances focus (repeated digits like **000000** flow smoothly);
non-digits are stripped; Backspace on an empty box clears + focuses the previous box;
pasting fills all boxes from box 1 (junk stripped, short pastes focus the next empty box).
`initOtpInputs()` in `kiosk.js`; boxes carry `inputmode="numeric"` +
`autocomplete="one-time-code"`. Browser-verified (scripted events + screenshot).
DEV_OTP stays `000000`.

### Voice Consultation Screen

### KIOSK-2 · "Repeat Question" button not working · ✅ (Session 10, step 7)
ROOT CAUSE confirmed: the button always fired — **the Windows dev box has no Bangla TTS
voice**, so speech was silently absent (TC-V2, test_log 2026-07-06). Fix: a bilingual
`#voice-hint` banner now shows on the voice screen whenever `banglaVoiceAvailable()` is
false; on-screen text stays the fallback (ADR-0028). Button kept and verified (speaks the
last question). ⚠ HUMAN: install a Bengali voice (Windows Settings → Speech → Add voices)
for actual audio; re-check TC-V2 then.

### KIOSK-3 · Speaker icon on every message · ✅ (Session 10, step 7)
Every chat bubble now carries a **🔊 icon** (in `addBubble()`): assistant icon replays that
question via TTS; patient icon reads back EXACTLY the words captured at bubble creation
(raw, unchanged — rule #1). The Repeat-Question button was kept alongside (separate spec
item + big accessible target). Browser-verified via a `speak()` spy.

### KIOSK-4 · Download raw transcript (`.docx`) · ✅ (Session 11, step 8)
Add a **Download (.docx)** option so the patient can download the raw voice transcript exactly as
transcribed, **before** any AI summarization. Example —
**আপনার কথা:** `"আমি মোহাম্মদ কামাল হোসেন... বর্তমানে আমি গ্যাস্ট্রিকের ওষুধ, নাপা এবং নাপা এক্সটেন্ড খাচ্ছি।"`
- **Expected:** the downloaded document preserves the original transcript with no modifications.
**Done:** bilingual "Download Raw Transcript (.docx)" button on the kiosk summary screen (before
Confirm & Submit), wired to the existing visit-grain `transcript` export via a temporary anchor;
the .docx reproduces every raw turn byte-exact (rule #1). No backend change.

### Pre-Screening Summary

### KIOSK-5 · Improve summary card UI · ✅ (Session 11, step 9)
After voice input, the **"Please Review Your Pre-Screening Summary"** section shows the extracted
info, but the current layout looks plain and unprofessional.
- **Expected improvements:**
  - Modern card with subtle blur and soft shadow.
  - Rounded corners (16–20px) with proper spacing and padding.
  - **Bold** field titles and a clear visual hierarchy.
  - Each of the 10 pre-screening items in its own clean section/card, not plain text.
  - A relevant icon per section (Chief Complaint, Duration, Symptoms, Medications, Allergies, etc.).
  - Highlight important values (symptoms, duration, medications) with accent colors or badges.
  - Better typography, spacing, alignment.
  - Should feel like a professional medical report while staying easy to review before submitting.
  - **Must stay inside the locked clinical-blue design system** (ADR-0029 / `shared.css`) — extend
    it, don't fork it. Never show module codes in patient-facing UI.
**Done:** each of the 10 fields is its own card (18px radius, backdrop blur, soft shadow, an icon
chip per section, bold primary-blue titles); the clinically key fields get a left accent border +
value badge; empty fields show muted-italic "Not mentioned / উল্লেখ করা হয়নি"; clinical-blue
tokens only (extends `shared.css`, no fork).

### KIOSK-6 · Language toggle bug · ✅ (Session 11, step 10)
Switching **English ↔ বাংলা** changes the labels correctly, but the extracted patient responses
stay in **English**.
- **Expected:**
  - **English** selected → both labels **and** extracted responses shown in English.
  - **বাংলা** selected → both labels **and** extracted responses shown in Bangla.
  - The entire summary follows the selected language consistently.
  - (Translation applies to the extracted/normalized summary fields only — the raw verbatim
    transcript is never altered.)
**Done:** the summary follows the toggle end-to-end — `renderSummary()` reads values via
`fieldValue()`, the profile is kept as `state.lastProfile`, and `onLanguageChange()` re-renders;
legacy `{value}` rows display as-is. Labels + extracted values both switch; raw is never altered.

### KIOSK-7 · Automatic follow-up questions for missing information · ✅ (Session 11, step 11 — ADR-0034)
After the summary is generated, the system should detect missing/incomplete fields **before**
allowing submit.
- **Current issue:** if fields like **Medical History, Current Medications, Allergies, Recent
  Changes** are missing or marked **"উল্লেখ করা হয়নি"**, the user only sees **Speak Again** and
  **Confirm & Submit** — so incomplete info can be sent to the doctor.
- **Expected workflow:** ask follow-up questions **one at a time, in Bangla, via voice (TTS + text)**;
  the patient answers by voice; the AI fills that field, then asks the next missing field. Ask
  **only** the missing fields until all 10 items are complete. Example sequence:
  - চিকিৎসা ইতিহাস → **সহকারী:** `"আপনার কি আগে থেকে কোনো রোগ বা চিকিৎসার ইতিহাস আছে?"`
  - চলমান ওষুধসমূহ → **সহকারী:** `"আপনি বর্তমানে কোনো ওষুধ খাচ্ছেন? খেলে ওষুধগুলোর নাম বলুন।"`
  - অ্যালার্জি → **সহকারী:** `"আপনার কোনো ওষুধ বা খাবারে অ্যালার্জি আছে কি?"`
  - সাম্প্রতিক পরিবর্তন → **সহকারী:** `"সম্প্রতি আপনার অবস্থার কোনো পরিবর্তন হয়েছে কি?"`
- **UI behavior:**
  - Hide **Confirm & Submit** while required information is missing.
  - Show a progress indicator (e.g. **8/10 তথ্য সম্পন্ন**).
  - After all missing fields are completed, regenerate the summary automatically.
  - Only then show **Confirm & Submit**; the patient reviews the completed summary and submits.
- **Reuse the existing M7 → M8 → M9 loop** (`followup.py` / `profile_update.py` / `completion.py`),
  voice-only per ADR-0027/0028. Do not rebuild it.
**Done (ADR-0034):** a resume loop on the summary screen — `?scope=fields` on
`followup/next` + `followup/answer` asks only still-empty summary-field keys, one per turn
(no 0.7-threshold gate; `target_gap` forced to a real field so "নেই / জানি না" is never
re-asked); progress chip ("৮/১০ তথ্য সম্পন্ন"), Confirm & Submit hidden while a question is
open, summary regenerated after every answer, shared per-visit question cap, **fail-open**
(cap/API-error → submit returns). New `test_resume_loop.py` (5).

---

## 2. Doctor Dashboard — `http://localhost:8001/doctor/`

### DOCTOR-1 · Remove `↻ Queue` · ✅ (Session 12, step 16)
The **↻ Queue** button has no clear purpose. If it is not used, remove it.
**Done:** removed — the queue auto-refreshes every 15s and reloads after every review, so the
button had no distinct job (unlike the medic's, which clears the phone filter — MEDIC-5).

### DOCTOR-2 · Bangla / English toggle · ✅ (Session 12, step 16)
Add a language toggle for the **entire** dashboard. All UI text, patient details, AI summary, and
the **10 pre-screening questions & answers** switch between Bangla and English; patient responses
translate with the selected language.
**Done:** EN/বাংলা toggle in the header; every static string carries data-en/bn; the safety panel
renders from state (`renderSafety()`) so risk/red-flags/XAI strings switch too; queue, verbatim
chrome, and the 10 field cards switch via the shared `staffLanguageRefresh()` (values via
`fieldValue()`); placeholders switch via `updatePlaceholders()`. Raw verbatim text is re-rendered
but never translated (rule #1).

### DOCTOR-3 · Patient details · ✅ (Session 13, step 17)
Display a clean patient summary: Name · Phone Number · Age · Gender · Weight · BP ·
AI Risk Score (0–100%) · AI Suggested Condition · AI Reasoning · complete 10-question pre-screening
summary.
**Done:** a Patient Details card after the safety panel (Name · Phone · Age-from-`birth_year` ·
Gender · Weight · BP, from the patient embedded in `GET /visits/{uuid}`), with inline weight + BP
edit reusing `PATCH /patients/{id}/vitals`; a mounted `#condition-card` so the shared
`renderConditionCard()` surfaces the AI suggested condition + reasoning + disclaimer; the risk
"score" is the C2 display band (`tierBand()`) beside the tier badge; the 10-question summary + XAI
were already present. Bilingual; raw + patient name never translated (rule #1).

### DOCTOR-4 · Prescription module · ✅ (Session 13, step 18 — ADR-0038)
Add a **Prescription** button that opens a professional prescription form with:
Clinic/Hospital Name & Logo · Doctor Name · Qualification · Specialization · Registration Number ·
Date · Patient Information · Symptoms / Chief Complaints · Diagnosis · Medicines (Name, Strength,
Dosage, Timing, Duration) · Advice / Lifestyle · Required Tests · Follow-up Date ·
Doctor Signature & Stamp.
**Done:** "📝 Write Prescription" in the review bar opens a full-screen bilingual form with every
listed field; letterhead prefilled from a read-only `GET .../prescription/context` (clinic +
doctor, seeded via `seed_demo_letterhead()`); **Diagnosis defaults EMPTY and is doctor-authored,
never AI-filled (rule #2)**. New `test_prescription_context.py` (6).

### DOCTOR-5 · Smart features · ✅ (Session 13, step 18)
- Add/remove medicine rows.
- Auto-fill patient details from the referral.
- Auto-fill symptoms from the pre-screening summary.
- Support Bangla and English prescription formats.
**Done:** medicine rows add/remove (`rxDraft` state survives the EN↔বাংলা toggle); patient details
auto-fill from the loaded case; symptoms auto-fill from the 10 `summary_fields` via `fieldValue()`;
the whole form is bilingual.

### DOCTOR-6 · Download & save · ✅ (Session 13, step 19 — ADR-0039)
After clicking **Submit**:
- Automatically generate a professionally formatted **`.docx`** prescription.
- Automatically download it.
- Save it in the system so both the doctor and the patient can access it later.
**Done:** `POST /api/visits/{uuid}/prescription` (`{doctor_id, payload}`) renders the LOCAL .docx
(`render_prescription`), stores it, and persists a `prescriptions` row linked to a `documents` row
(kind `prescription`); the form Submit POSTs → auto-downloads → "✅ Saved & Downloaded" with a
re-download link; retrievable later via `GET /documents/{id}/download`. A new prescription per
Submit (append). The writer reads only the payload, so Diagnosis can't be AI-filled (rule #2,
regression-tested). New `test_prescription_docx.py` (5).

### DOCTOR-7 · UI/UX · ✅ (Session 13, steps 17–19)
Modern medical dashboard: clean cards, icons, spacing, typography. Make Risk, AI Suggestion,
Diagnosis, and Prescription Status easy to identify. Layout responsive and print-friendly.
**Done:** base polish landed in S12 step 16 (nav icon, responsive flex-wrap, `@media print` block,
glanceable safety panel); S13 completed the four "easy to identify" targets — **Risk** (safety
panel + C2 band), **AI Suggestion** (mounted condition card), **Diagnosis** (the prescription
form's own field), and **Prescription Status** (the Write-Prescription action + the Saved &
Downloaded confirmation). Bilingual throughout.

---

## 3. Medic Dashboard — `http://localhost:8001/medic/`

### MEDIC-1 · Bangla / English toggle · ✅ (Session 11, step 12)
The Medic Dashboard is English-only. Add a Bangla/English toggle. All UI elements, labels, buttons,
tables, forms, and AI-generated content switch with the selection; the Bangla version follows the
same professional UI/UX as the English one.
**Done:** `staff.js` fully bilingual (labels + icons, badges, verbatim chrome via `t()`; extracted
values via `fieldValue()`; `staffLanguageRefresh()` on toggle); the medic portal gained the
EN/বাংলা header toggle + data-en/bn on all static text. Raw verbatim never translated (rule #1).

### MEDIC-2 · Improve UI/UX · ✅ (Session 11, step 12)
Redesign with a cleaner, modern medical interface: better spacing, typography, icons, cards, status
badges, color hierarchy. Highlight important patient info (risk, chief complaint, referral status).
Make it professional and easy to scan.
**Done:** field-card icon chips + queue hover states in `shared.css`, status/risk badges via the
shared `tierBadge()`, clinical-blue hierarchy throughout (extends `shared.css`, no fork).

### MEDIC-3 · Editable AI risk assessment · ✅ (Session 11, step 13 — ADR-0035)
AI auto-generates a **Risk Score (0–100%)**, displayed as **Low / Medium / High** with color
coding. The medic can edit/override the AI-assigned risk level before referral. (Wire codes stay
`low/medium/high/critical`; labels come from `shared.js` `TIER_LABELS`; log overrides to `audit_log`.)
**Done:** a risk panel shows the tier + C2 band (display-only score) + red flags + XAI; the medic
overrides via `POST /visits/{uuid}/risk/override`, which **appends** a `model_provider='human'`
assessment row (the AI row is untouched) and audit-logs from→to. Staff **cannot downgrade a
red-flag Critical** (409). New `test_risk_override.py` (3).

### MEDIC-4 · AI suggested condition · ✅ (Session 12, step 14 — ADR-0036)
Add a section showing **Possible Condition(s)** suggested by AI plus **Reasoning** explaining why,
based on the patient's symptoms. Example — **Possible Condition:** GERD (Acid Reflux);
**Reason:** chest burning after meals, nighttime symptoms, and sour burps are consistent with GERD.
The medic can edit/replace the suggested condition.
**Done:** new module **M10C** (Flash bucket, separate call from M10) generates a bilingual
condition + reasoning at kiosk submit (best-effort — never blocks); stored at
`entities["suggested_condition"]` with provenance + the embedded "not a diagnosis" disclaimer;
`PATCH /profile/condition` staff edit (403 for non-staff, audit-logged); shared
`renderConditionCard()` card in the medic portal (doctor mount arrives at step 17); the kiosk
never shows it and the doctor's Diagnosis field is never pre-filled (step 18 enforces EMPTY).
Tests: `test_suggested_condition.py` (5).

### MEDIC-5 · `↻ Queue` button · ✅ (Session 11, step 12)
The purpose of the **↻ Queue** button/menu is unclear. If it has a functional purpose, make it clear
in the UI; if not, remove it to reduce clutter.
**Done:** kept with its purpose made explicit — relabelled "↻ Refresh Queue / তালিকা রিফ্রেশ" with a
tooltip; its one clear job is to reload the full queue and clear the phone-search filter
(`refreshQueue()`). (The doctor's identical-looking button had no distinct job and was removed —
DOCTOR-1.)

### MEDIC-6 · Patient summary after referral · ✅ (Session 12, step 15)
After referring a patient to a doctor, generate a structured summary: Patient Name · Phone Number ·
Age · **Weight** (editable by the medic) · AI Risk Score · AI Suggested Condition · AI Reasoning ·
all 10 pre-screening questions and answers in a clean, formatted layout.
**Done:** "Submit & Forward" now lands on a post-referral summary screen (bilingual): patient card
(name/phone/age-from-birth-year/**weight inline-edit**/BP), risk tier + C2 band + red flags + XAI,
the C1 suggested condition with its disclaimer, and all 10 Q&A rows. Weight edits go through the
new `PATCH /api/patients/{id}/vitals` (staff-only, audit-logged `patient.vitals_edit`);
`GET /visits/{uuid}` now embeds the patient with vitals (`VisitDetailWithPatientOut`).

### MEDIC-7 · Download report (`.docx`) · ✅ (Session 12, step 15)
Add a **Download (.docx)** option to export the patient summary as a professionally formatted
document suitable for sharing or printing. **Download must actually work.**
**Done:** "⬇ Download Report (.docx)" on the post-referral screen (temp-anchor, KIOSK-4 pattern).
The `summary_report` docx now renders the C1 possible-condition section (with its embedded
disclaimer) + patient vitals, and is assembled from a **fresh** M12 report at download time so
staff edits/overrides always show (staleness regression covered by `test_medic_summary.py`, 5 tests).

---

## 4. Rules this work must not break (from `constitution.md`)

- **#1 Raw words are never edited.** Raw transcript stays immutable and visibly separate from
  corrected/normalized/summary fields. Patient-message TTS (KIOSK-3) reads raw text verbatim.
- **#2 The system never diagnoses.** "AI Suggested Condition" (MEDIC-4, DOCTOR-3) is a
  **non-diagnostic** suggestion + reasoning and keeps the no-diagnosis disclaimer. The prescription
  **Diagnosis** field (DOCTOR-4) is authored by the human doctor and must not be pre-filled by AI.
- **#3 Red-flag rule** in `red_flags.py` must always be able to force `Critical` even with every LLM
  down (ADR-0024); add phrases only, each with a matching TC-R1 test.
- **#4 Never auto-run live LLM calls** to burn quota; test on synthetic/offline data; route LLM use
  through `llm_client.py` (per-module bucket + fallback, ADR-0026).
- **Design system locked** to clinical-blue (ADR-0029 / `shared.css`, Noto Sans Bengali, bilingual);
  reconcile the "glassmorphism" ask (KIOSK-5) within it, don't fork it. No module codes in
  patient-facing UI. Tier labels only in `shared.js` `TIER_LABELS`.
- **Schema change = a new Alembic revision** (0010+); never edit an applied revision, never delete
  the DB.
- **Keep the 104 passing tests green**; add tests for every new behavior.
- **Cross-platform** (Windows + Arch Linux, no NVIDIA GPU); no new heavy deps — TTS/STT/`.docx`
  stay browser-native / python-docx.

---

## 5. Open decisions — ALL RESOLVED by the human (Session 9; do not re-open)

1. ✅ **STRUCT / §0.1:** the 4 **app entry points**; legacy route = **`/legacy/`** (ADR-0031).
2. ✅ **DOCTOR-6 / MEDIC-7:** DB-backed — `documents.visit_id` (nullable FK) + new
   `documents.kind` values (`transcript`, `summary_report`, `prescription`) + a
   **`prescriptions` table** (visit_id, doctor_id, payload JSON, document_id). Alembic 0010.
   File-only storage rejected.
3. ✅ **Bilingual values:** generate **both `value_bn` and `value_en` once** at extraction/merge
   (M3/M8) and store them in the `summary_fields` JSON; back-compatible with old `{value}` rows.
   On-the-fly client translation rejected (quota).
4. ✅ **DOCTOR-4 letterhead:** clinic (name/address/logo) + doctor (qualification/registration/
   specialization/signature) stored in **DB columns** (0010) — reusable and editable.
5. ✅ **C1 (constitution rule #2 boundary):** "Possible Condition (AI Suggestion – Not a
   Diagnosis)" allowed with a clear disclaimer, editable by medic/doctor; the doctor's
   prescription **Diagnosis field is never AI-filled**.
6. ✅ **C2 (risk score):** display-only tier→band mapping in `shared.js` (e.g. Low = 0–25%);
   no numeric score generated or stored.
7. ✅ **KIOSK-7 loop depth:** resume loop asks only missing fields, one per turn, respects
   `followup_max_questions`; "নেই" / "No" / "জানি না" count as completing a field.
