# context_fixed_problem.md — Full-Stack Bug & Feature Spec

> This answers one question: **"What is broken or missing in the new full-stack app,
> and exactly what should it do instead?"**
> It is the work spec for the current build. Each item has a stable ID so the plan,
> the changelog, and the tests can all point back to it. Preserve Bangla strings verbatim.

**Status keys:** ⬜ Not started · 🟨 In progress · 🟦 Blocked (needs a decision) · ✅ Done

**Last updated:** 2026-07-05
**Related docs:** `constitution.md` (rules #1–#4), `architecture.md`, `codebase_map.md`,
`decisions.md` (ADR-0024/0025/0026/0027/0028/0029), `milestone_log.md`, `current_task.md`.

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

### KIOSK-1 · OTP verification · ⬜
When the patient enters a phone number and the OTP page opens, typing a digit does **not**
auto-move the cursor to the next input box. Users must switch boxes manually, which makes codes
like **000000** hard to enter.
- **Expected:** typing a digit auto-advances focus to the next box; Backspace moves back a box;
  pasting a full 6-digit code fills all boxes. (DEV_OTP stays `000000`.)

### Voice Consultation Screen

### KIOSK-2 · "Repeat Question" button not working · ⬜
The **🔊 প্রশ্নটি আবার শুনুন / 🔊 Repeat Question** button does nothing.
- **Expected:** tapping it replays the assistant's current question via TTS. Example —
  **সহকারী:** `"আপনার সমস্যাটি নিজের ভাষায় খুলে বলুন তো।"`

### KIOSK-3 · Speaker icon on every message · ⬜
Instead of a single "Repeat Question" button, add a **🔊 speaker icon** beside every chat message.
- **Expected:**
  - Tapping the icon on an **assistant** message plays the TTS for that question.
  - Tapping the icon on a **patient** message reads back **exactly** what the patient said
    (raw words, unchanged — rule #1).
  - Gives a consistent, intuitive chat experience.

### KIOSK-4 · Download raw transcript (`.docx`) · ⬜
Add a **Download (.docx)** option so the patient can download the raw voice transcript exactly as
transcribed, **before** any AI summarization. Example —
**আপনার কথা:** `"আমি মোহাম্মদ কামাল হোসেন... বর্তমানে আমি গ্যাস্ট্রিকের ওষুধ, নাপা এবং নাপা এক্সটেন্ড খাচ্ছি।"`
- **Expected:** the downloaded document preserves the original transcript with no modifications.

### Pre-Screening Summary

### KIOSK-5 · Improve summary card UI · ⬜
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

### KIOSK-6 · Language toggle bug · ⬜
Switching **English ↔ বাংলা** changes the labels correctly, but the extracted patient responses
stay in **English**.
- **Expected:**
  - **English** selected → both labels **and** extracted responses shown in English.
  - **বাংলা** selected → both labels **and** extracted responses shown in Bangla.
  - The entire summary follows the selected language consistently.
  - (Translation applies to the extracted/normalized summary fields only — the raw verbatim
    transcript is never altered.)

### KIOSK-7 · Automatic follow-up questions for missing information · ⬜
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

---

## 2. Doctor Dashboard — `http://localhost:8001/doctor/`

### DOCTOR-1 · Remove `↻ Queue` · ⬜
The **↻ Queue** button has no clear purpose. If it is not used, remove it.

### DOCTOR-2 · Bangla / English toggle · ⬜
Add a language toggle for the **entire** dashboard. All UI text, patient details, AI summary, and
the **10 pre-screening questions & answers** switch between Bangla and English; patient responses
translate with the selected language.

### DOCTOR-3 · Patient details · ⬜
Display a clean patient summary: Name · Phone Number · Age · Gender · Weight · BP ·
AI Risk Score (0–100%) · AI Suggested Condition · AI Reasoning · complete 10-question pre-screening
summary.

### DOCTOR-4 · Prescription module · ⬜
Add a **Prescription** button that opens a professional prescription form with:
Clinic/Hospital Name & Logo · Doctor Name · Qualification · Specialization · Registration Number ·
Date · Patient Information · Symptoms / Chief Complaints · Diagnosis · Medicines (Name, Strength,
Dosage, Timing, Duration) · Advice / Lifestyle · Required Tests · Follow-up Date ·
Doctor Signature & Stamp.

### DOCTOR-5 · Smart features · ⬜
- Add/remove medicine rows.
- Auto-fill patient details from the referral.
- Auto-fill symptoms from the pre-screening summary.
- Support Bangla and English prescription formats.

### DOCTOR-6 · Download & save · ⬜
After clicking **Submit**:
- Automatically generate a professionally formatted **`.docx`** prescription.
- Automatically download it.
- Save it in the system so both the doctor and the patient can access it later.

### DOCTOR-7 · UI/UX · ⬜
Modern medical dashboard: clean cards, icons, spacing, typography. Make Risk, AI Suggestion,
Diagnosis, and Prescription Status easy to identify. Layout responsive and print-friendly.

---

## 3. Medic Dashboard — `http://localhost:8001/medic/`

### MEDIC-1 · Bangla / English toggle · ⬜
The Medic Dashboard is English-only. Add a Bangla/English toggle. All UI elements, labels, buttons,
tables, forms, and AI-generated content switch with the selection; the Bangla version follows the
same professional UI/UX as the English one.

### MEDIC-2 · Improve UI/UX · ⬜
Redesign with a cleaner, modern medical interface: better spacing, typography, icons, cards, status
badges, color hierarchy. Highlight important patient info (risk, chief complaint, referral status).
Make it professional and easy to scan.

### MEDIC-3 · Editable AI risk assessment · ⬜
AI auto-generates a **Risk Score (0–100%)**, displayed as **Low / Medium / High** with color
coding. The medic can edit/override the AI-assigned risk level before referral. (Wire codes stay
`low/medium/high/critical`; labels come from `shared.js` `TIER_LABELS`; log overrides to `audit_log`.)

### MEDIC-4 · AI suggested condition · ⬜
Add a section showing **Possible Condition(s)** suggested by AI plus **Reasoning** explaining why,
based on the patient's symptoms. Example — **Possible Condition:** GERD (Acid Reflux);
**Reason:** chest burning after meals, nighttime symptoms, and sour burps are consistent with GERD.
The medic can edit/replace the suggested condition.

### MEDIC-5 · `↻ Queue` button · ⬜
The purpose of the **↻ Queue** button/menu is unclear. If it has a functional purpose, make it clear
in the UI; if not, remove it to reduce clutter.

### MEDIC-6 · Patient summary after referral · ⬜
After referring a patient to a doctor, generate a structured summary: Patient Name · Phone Number ·
Age · **Weight** (editable by the medic) · AI Risk Score · AI Suggested Condition · AI Reasoning ·
all 10 pre-screening questions and answers in a clean, formatted layout.

### MEDIC-7 · Download report (`.docx`) · ⬜
Add a **Download (.docx)** option to export the patient summary as a professionally formatted
document suitable for sharing or printing. **Download must actually work.**

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
