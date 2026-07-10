# 🗂️ BUILD TRACKER — "Context Fixed Problem 2.0"

> **This is now the single living checklist for this feature/fix cycle.** The human's original
> requirements are kept verbatim BELOW this tracker (the source of truth for *what* each item means);
> this tracker adds the plan IDs, status, and the files each item touches so any new session knows
> exactly what is done and what is left. Plan approved Session 18 (**ADR-0042** in `decisions.md`).
> Rules that constrain the build: **one item per human "go"**, functional fixes before UI polish,
> cross-platform (Windows + Arch), and the four non-negotiables (raw words never translated — rule #1;
> never diagnose — rule #2; red flags add-only — rule #3; synthetic data / no auto live-LLM — rule #4).
>
> **Legend:** ✅ done · ⏳ in progress · ⬜ not started · 👉 the next step

## Progress at a glance
- **Cross-cutting (STRUCT):** ✅ STRUCT-1 · ✅ STRUCT-2 · ✅ STRUCT-3
- **P1 Patient Portal (highest):** ✅ P1-1 · ✅ P1-2 · ✅ P1-3 · ✅ P1-4 · ✅ P1-5 · ✅ P1-6 — **P1 CLOSED**
- **P2 Medic Portal:** ✅ P2-1 · ✅ P2-2 · ✅ P2-3 — **P2 CLOSED**
- **P3 Doctor Portal:** ✅ P3-1 · ✅ P3-2 · ✅ P3-3 · ✅ P3-4 — **P3 CLOSED**
- **P4 OTP (last):** 👉⬜ P4-1 — ⚠ blocked on the HUMAN's sender-channel choice (ask first)
- **Out of scope (future research):** the "Faculty Requirement – Future Features" below
  (quantized Moshi summary model; quantized on-device STT/TTS) — NOT part of this cycle.

## Checklist (maps to the requirements below)

### Cross-cutting first (STRUCT — low risk)
- [x] **STRUCT-1 — Rename "Patient Kiosk" → "Patient Portal"** (visible strings only; EN + "রোগী পোর্টাল").
  ✅ done S18 — `frontend/index.html:41`, `frontend/kiosk.html:6,81,200`. URLs/filenames kept.
- [x] **STRUCT-2 — Logout on every page → Portal Directory (`/`).** ✅ done S19 — shared `logout()`
  in `frontend_shared/shared.js` + a bilingual Logout button in ALL THREE portal headers (medic +
  doctor + kiosk — the kiosk's post-submit auto-logout stays; this is the manual exit). Verified in
  preview: button renders, "লগআউট" in Bangla, click lands on `/`, no console errors.
  *(Requirement: "General UI/UX" → Logout on every page.)*
- [x] **STRUCT-3 — Theme evolution (shared).** ✅ done S19 (**ADR-0043**) — human chose "Teal Medical"
  (Option A) from live previews: primary `#0F766E`, secondary `#0D9488`, bg `#F0FBF8`, radius 10px
  + the hardcoded blue tints in `shared.css` retinted; semantic risk colors untouched; CLAUDE.md
  FRONTEND section updated. Verified teal on `/`, kiosk, medic, doctor — no console errors.
  *(Requirement: "General UI/UX" → redesign; per-portal polish still lands in P1-6/P2-3/P3-4.)*

### P1 — Patient Portal `/kiosk.html` (highest priority)
- [x] **P1-1 — "Summary" auto-stops recording + processes immediately.** ✅ done S19 — new
  `submitFinalTurn()` + reworked `finishConversation()` in `kiosk.js`: stops the mic, flushes the
  captured words as the final turn (answer path = followup/answer with next-question IGNORED;
  opening path = utterance + intake re-run so the words are extracted), then summary. Reentry
  guard `state.finishing`. Verified in preview with a stubbed `api` (no LLM calls): both paths +
  empty-buffer + double-click all correct. *(→ "Voice Recording".)*
- [x] **P1-2 — Language toggle translates ALL UI both ways.** ✅ done S19 — bubbles carry
  `data-en/bn` on labels (+ bilingual bodies like the opening prompt), so shared `applyLanguage()`
  re-translates them; new `setBilingualText()` keeps JS-written text (OTP subtitle, mic hints)
  toggle-safe; live transcript mirrored into both slots so a toggle can't wipe it; 🔊 tooltips
  refresh in `onLanguageChange()`; bilingual `data-en/bn-placeholder` support added to shared
  `applyLanguage()` + the 2 fallback inputs. **Patient bubbles have NO dataset — verbatim forever
  (rule #1)**; server questions (EN+BN in one string) left as captured. Preview-verified both
  directions incl. round-trip. *(→ "Language Toggle".)*
- [x] **P1-3 — Always ask 4–5 history-based follow-ups.** ✅ done S20 — `followup_min_questions=4`
  in `config.py`; `_loop_state()` in `routes_followup.py` now requires threshold AND ≥4 asked; M7
  (`services/followup.py`) switches to history-grounded DEEPENING questions when the gap list runs
  out (main loop only — the `scope=fields` resume loop still stops as before; cap 5 always wins;
  empty-list salvage fixed). Human approved the new `_QUESTION_SYSTEM` wording. New
  `test_followup_min_questions.py` (floor via deepening / cap terminates / fields scope unaffected)
  + 2 existing tests updated to the new spec. **159 tests pass.** *(→ "Follow-up Questions".)*
- [x] **P1-4 — Highlight MISSING required fields on the summary.** ✅ done S20 — empty REQUIRED
  fields (the `HIGHLIGHT_FIELDS` clinical set) get `.summary-item.missing` (amber warning border +
  tinted card + bold amber "Not mentioned") + a bilingual "Needs info / তথ্য প্রয়োজন" chip that
  follows the language toggle; optional empties stay muted. Preview-verified (classes, chip,
  EN↔BN, screenshot). *(→ "Missing Medical Information".)*
- [x] **P1-5 — Confirm & Submit fast = background assessment.** ✅ done S21 (ADR-0042b) — new
  `_post_submit_assessment()` in `routes_dashboard.py` runs M10/M11/M10C in a FastAPI
  `BackgroundTasks` job on its OWN session bound via `db.get_bind()` (same engine in prod AND
  tests); submit keeps only guards + status→`awaiting_review` + audit synchronous, so the endpoint
  returns instantly and the tier fills in on the staff queues' 15s refresh. Job is fire-and-forget
  (try/except + log). New `test_submit_background.py`: assessment+C1 land after submit · a
  background crash never blocks/undoes submission · red flag STILL forces Critical from the
  background with the model down (rule #3). **162 tests pass.** *(→ "Confirm and Submit".)*
- [x] **P1-6 — Patient Portal UI polish** on top of STRUCT-3. ✅ done S22 — retinted the 6 leftover
  clinical-blue tints in `kiosk.html` inline CSS to Teal Medical (dock transcript `#F4FAF8`,
  summary icons `#ECF5F3`, highlight icon/pill + progress chip `#E6F7F3`/`#B8E5DC`, card shadow
  `rgba(13,63,60,.07)`); P1-4 amber warning treatment + green complete-chip kept (semantic).
  Layouts/hooks untouched. Preview-verified via computed styles + screenshot; no console errors.
  **P1 (Patient Portal) is fully CLOSED.** *(→ "UI/UX".)*

### P2 — Medic Portal `/medic/`
- [x] **P2-1 — Correct Dhaka date/time in the queue.** ✅ done S22 — ROOT CAUSE found: SQLite rows
  serialize **offset-less** UTC (`2026-07-05T14:03:42.884654`), which `new Date()` reads as LOCAL
  time → "random" queue times. New shared helpers in `shared.js`: `parseUtc()` (pins offset-less
  strings to UTC) + `dhakaTime()`/`dhakaDateTime()` (always render `Asia/Dhaka`, bn-BD/en-GB by
  current language); `staff.js` `renderQueue` now uses `dhakaTime(item.started_at)` — BOTH staff
  portals inherit. Verified with known instants: offset-less 06:30 UTC → **12:30**, 18:00Z → 00:00,
  +00:00 → 06:00, Bangla "১২:৩০ PM", invalid → "—". Browser-side `Intl` = cross-platform (no
  backend tzdata). *(→ "Queue Time"; P3-1 reuses `dhakaDateTime()` for submitted-at.)*
- [x] **P2-2 — Patient details: add Gender + auto-fill Name/Age/Gender + editable.** ✅ done S22 —
  (a) M3/M8 extraction (human-approved wording) now also returns `patient_demographics`
  {name-exactly-as-stated, age_years, sex male|female|other}; new `apply_demographics()` in
  `services/intake.py` (called from intake + M8 answer-merge) writes `Patient.display_name/sex/
  birth_year` **fill-only-when-empty** → staff values are final, NO migration needed. (b) Vitals
  PATCH extended (`display_name`/`sex` pattern-validated/`age_years`→birth_year; audits only sent
  fields). (c) Medic post-referral card: Gender row + "Edit Details" identity editor (name/age/
  gender, prefilled, weight-editor pattern); doctor portal displays the same Patient row. New
  `test_patient_demographics.py` (4 tests: autofill · never-overwrite · malformed-ignored ·
  staff-PATCH-final + validation). **166 tests pass.** UI preview-verified incl. Bangla labels.
  *(→ "Patient Details".)*
- [x] **P2-3 — Medic Portal UI polish.** ✅ done S23 — the portal was already token-clean (its one
  hex is an approved teal tint; `staff.js` hex-free). Real fixes in `shared.css`: `.card` radius
  `12px` → `var(--radius)` (the ADR-0043 10px lock — all portals inherit) + `.verbatim-speaker`
  `display:block; margin-bottom:4px` (speaker labels no longer run into the raw text). Full medic
  flow preview-verified with a stubbed `api` (login → queue → case → forward → post-referral →
  EN↔BN); computed styles + screenshots; no console errors. **P2 CLOSED.** *(→ "UI/UX".)*

### P3 — Doctor Portal `/doctor/`
- [x] **P3-1 — Correct patient submission Dhaka date/time.** ✅ done S23 — nullable
  `Visit.submitted_at` (**Alembic 0011**, applied; head 0010→0011), stamped in
  `repository_visits.set_visit_status()` on `in_progress → awaiting_review` (mirrors the
  `completed_at` pattern; synchronous with submit, unaffected by the P1-5 background job).
  Exposed in `VisitOut` (detail + submit response) and `DashboardItemOut`; queues render
  `dhakaTime(submitted_at || started_at)` (fallback for pre-0011 rows); doctor patient-details
  card gains a "Submitted / জমার সময়" row via `dhakaDateTime()`. New `test_submitted_at.py` (3) +
  `test_migration_0011.py` (2). **171 tests pass.** Preview: 14:00Z renders 20:00 / "১০ জুল, ২০২৬".
  *(→ "Patient Time".)*
- [x] **P3-2 — Show latest patient details incl. medic edits.** ✅ done S23 — verification
  confirmed NO product change needed: every doctor-side read is fresh (`GET /visits/{uuid}` embeds
  the live Patient row; /profile + /risk re-query on each case open), so medic edits — including
  POST-forward identity/weight edits from the post-referral card — always show. Locked in with
  `test_doctor_sees_medic_edits.py` (1 end-to-end: field edit + C1 replacement + risk override +
  post-assign vitals/identity PATCH all visible; `source=human`; C1 disclaimer survives).
  **172 tests pass.** Render side preview-verified (মানব-সম্পাদিত badges). *(→ "Patient Details".)*
- [x] **P3-3 — AI Medical Assistant (drug info): web search + LLM, side panel.** ✅ done S23
  (**ADR-0044**) — new module **M16** on the Flash bucket: `services/assistant.py` (ddgs search,
  top-5 snippets capped 400 chars → one `call_module`), `routes_assistant.py`
  (`POST /api/visits/{uuid}/assistant/drug-info` — visit-scoped: module_events audit linkage),
  `schemas/assistant.py` (disclaimer fields REQUIRED). Disclaimer attached SERVER-side on every
  answer (rule #2); search gets only the doctor's typed question (rule #4); search fail →
  sourceless answer; non-JSON reply salvaged; dead chain → 502. Doctor UI: 💊 top-nav button +
  teal slide-in panel (disclaimer bar always visible, textContent-only rendering, source links,
  EN↔BN, hidden in print). Dep: `ddgs==9.14.4` only (its `primp` has Win+Linux wheels; no
  separate httpx needed). New `test_assistant.py` (5). **177 tests pass.**
  *(→ "AI Medical Assistant".)*
- [x] **P3-4 — Doctor Portal UI polish.** ✅ done S23 — already token-clean (semantic amber/red
  kept; the JS-rendered prescription form has ZERO hex hardcodes — verified in the live DOM). One
  fix: `.safety-panel` radius `12px` → `var(--radius)` in `shared.css` (deferred from P2-3) — the
  LAST radius hardcode. Preview-verified incl. prescription form (Diagnosis empty — rule #2).
  **P3 CLOSED.** *(→ "UI/UX".)*

### P4 — OTP verification (LAST)
- [ ] **P4-1 — Real OTP + `000000` universal bypass.** Persisted, expiring code (new `OtpCode` table +
  migration) + a **pluggable sender seam**. ⚠ Free reliable OTP-to-any-phone is NOT feasible (WhatsApp/SMS
  cost money/approval; a Telegram bot can't cold-message a phone). **Confirm the channel with the human
  before building the sender.** *(→ "Patient Login (OTP)".)*

---

## **Task: UI/UX Improvements and Functional Fixes**

**After starting the backend, it shows:**

**Uvicorn running on: `http://127.0.0.1:8001`**

**The Niramoy Pre-Screening Portal Directory is available at:**

**`http://127.0.0.1:8001`**

**The server is running correctly.**

---

## **Requirements**

### **General UI/UX**

* **Update the UI/UX based on the reference screenshots I shared.**  
* **Do not change any backend logic unless it is absolutely necessary.**  
* **Add a Logout option on every page that returns the user to the Niramoy Pre-Screening Portal Directory.**  
* **Rename "Patient Kiosk" to "Patient Portal" throughout the project.**

  ---

  ## **Patient Login (OTP)**

**Implement real OTP verification.**

* **OTP should be delivered to the user's phone through WhatsApp, Telegram, or SMS.**  
* **The implementation must use a free verification method if possible.**  
* **Keep `000000` as a universal OTP so any phone number can log in for development/demo purposes.**

  ---

  ## **Patient Portal**

**URL: `http://127.0.0.1:8001/kiosk.html`**

### **Language Toggle**

**After logging in, the page displays:**

**সহকারী 🔊**  
**আপনার সমস্যাটি নিজের ভাষায় খুলে বলুন তো।**

**When the language is switched to English, this text does not change. The language toggle should translate all UI text correctly in both directions (Bangla ↔ English).**

---

### **Voice Recording**

**Currently, after clicking "সম্পন্ন — সারাংশ দেখুন", nothing happens immediately.**

**The user must click the microphone button again to stop recording before processing starts.**

**This should be fixed so that clicking "সম্পন্ন — সারাংশ দেখুন" automatically stops recording (if still recording) and immediately starts processing.**

---

### **Follow-up Questions**

**Currently, follow-up questions are skipped when most answers are already found.**

**Instead, I want the system to ask 4–5 follow-up questions based on the patient's conversation/history to collect additional useful medical information.**

---

### **Missing Medical Information**

**If required information for the medical summary is missing, the unanswered fields/questions should be highlighted clearly.**

---

### **Confirm and Submit**

**After clicking "নিশ্চিত ও জমা দিন / Confirm and Submit", the system takes too long to complete.**

**Please optimize this so the submission finishes as quickly as possible.**

---

### **UI/UX**

**Improve the Patient Portal UI/UX using the reference screenshots I shared.**

---

# **Medic Portal**

**URL: `http://127.0.0.1:8001/medic/`**

### **Queue Time**

**In "তালিকা (3 সক্রিয়) / Queue (3 active)", the displayed time is not accurate and appears random.**

**Make sure it always displays the correct Dhaka date and time.**

---

### **Patient Details**

**Current fields:**

* **Name**  
* **Phone**  
* **Gender (add this field)**  
* **Age**  
* **Weight (Editable)**  
* **Blood Pressure**

**Requirements:**

* **The medic should be able to edit these details if needed.**  
* **If the patient already mentioned their name, age, or gender during the conversation, these fields should be filled automatically.**

  ---

  ### **UI/UX**

**Improve the Medic Portal design based on the reference screenshots I shared.**

---

# **Doctor Portal**

**URL: `http://127.0.0.1:8001/doctor/`**

### **Patient Time**

**The submitted patient time currently appears random.**

**Display the exact Dhaka date and time when the patient submitted the pre-screening.**

---

### **Patient Details**

**The Patient Details section should display the latest information, including any edits made by the medic.**

---

### **AI Medical Assistant**

**Add an AI chatbot panel on the left side of the Doctor Portal.**

**The chatbot should allow the doctor to search for medicine-related information. For example, if the doctor enters a medicine name, the chatbot should provide:**

* **Uses of the medicine**  
* **Benefits**  
* **Side effects**  
* **Who should avoid taking it**  
* **Recommended age groups**  
* **Dosage information**  
* **Warnings and precautions**  
* **Drug interactions (if available)**

**The chatbot should retrieve up-to-date information from the web using AI and display the results in a popup or side panel.**

**If you have a better design or workflow for this feature, you may suggest and implement it.**

---

### **UI/UX**

**Improve the Doctor Portal UI/UX based on the reference screenshots I shared.**

- 


## **Faculty Requirement – Future Features**

### **1\. Integrate a Quantized AI Model for Medical Summary Generation**

Currently, the system uses an external AI model API to generate structured medical summaries. The workflow is as follows:

* The patient speaks through the microphone.  
* The speech is converted into text.  
* The transcript is sent to an AI model API.  
* The AI model returns the information in the required structured medical format.

As a future faculty requirement, this API-based approach will be replaced with a **locally deployed quantized AI model** developed by our team. The team is training the **Moshi** model using Bangla medical conversations and speech data. After training is completed, a **quantized version** of the model will be integrated into the system to generate structured medical summaries locally. This will reduce dependency on external APIs while improving privacy, response speed, and scalability.

---

### **2\. Replace Browser-Based Speech Processing with a Quantized Speech Model**

Currently, the system relies on browser APIs for speech processing:

* **Live Speech-to-Text (STT):** Uses the Browser Web Speech API (`SpeechRecognition`) optimized for Bangla (`bn-BD`) in Google Chrome and Microsoft Edge for real-time transcription.  
* **Text-to-Speech (TTS):** Uses the Browser Web Speech API (`SpeechSynthesis`) to read questions and follow-up prompts aloud to patients.

As a future faculty requirement, these browser-based components will be replaced with a **locally deployed quantized speech AI model**. Instead of depending on browser APIs, the integrated model will perform both speech recognition and speech generation within the system. The model will:

* Convert the patient's spoken Bangla into **Banglish (Romanized Bangla)** text in real time.  
* Generate natural voice responses to ask medical questions and follow-up prompts.  
* Provide a single, integrated speech processing pipeline that supports offline deployment, improves privacy, and reduces dependence on browser-based STT and TTS services.

  