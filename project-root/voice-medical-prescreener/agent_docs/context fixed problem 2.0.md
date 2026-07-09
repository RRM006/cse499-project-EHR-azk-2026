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
- **Cross-cutting (STRUCT):** ✅ STRUCT-1 · 👉⬜ STRUCT-2 · ⬜ STRUCT-3
- **P1 Patient Portal (highest):** ⬜ P1-1 · ⬜ P1-2 · ⬜ P1-3 · ⬜ P1-4 · ⬜ P1-5 · ⬜ P1-6
- **P2 Medic Portal:** ⬜ P2-1 · ⬜ P2-2 · ⬜ P2-3
- **P3 Doctor Portal:** ⬜ P3-1 · ⬜ P3-2 · ⬜ P3-3 · ⬜ P3-4
- **P4 OTP (last):** ⬜ P4-1
- **Out of scope (future research):** the "Faculty Requirement – Future Features" below
  (quantized Moshi summary model; quantized on-device STT/TTS) — NOT part of this cycle.

## Checklist (maps to the requirements below)

### Cross-cutting first (STRUCT — low risk)
- [x] **STRUCT-1 — Rename "Patient Kiosk" → "Patient Portal"** (visible strings only; EN + "রোগী পোর্টাল").
  ✅ done S18 — `frontend/index.html:41`, `frontend/kiosk.html:6,81,200`. URLs/filenames kept.
- [ ] **STRUCT-2 — Logout on every page → Portal Directory (`/`).** 👉 NEXT. Add a Logout button to the
  medic + doctor `.portal-header`; optional shared `logout()` in `frontend_shared/shared.js`. Kiosk
  already auto-logs-out. *(Requirement: "General UI/UX" → Logout on every page.)*
- [ ] **STRUCT-3 — Theme evolution (shared).** Evolve `:root` tokens in `frontend_shared/shared.css`
  toward the teal/modern reference look; KEEP layouts. *(Requirement: "General UI/UX" → redesign.)*

### P1 — Patient Portal `/kiosk.html` (highest priority)
- [ ] **P1-1 — "Summary" auto-stops recording + processes immediately.** `kiosk.js finishConversation`
  (:287): if `listening`, stop + flush `finalBuffer` as a turn before intake/profile. *(→ "Voice Recording".)*
- [ ] **P1-2 — Language toggle translates ALL UI both ways.** Assistant/opening bubbles carry
  `data-en/bn`, re-applied in `onLanguageChange`; **patient raw words NEVER translated (rule #1)**.
  *(→ "Language Toggle".)*
- [ ] **P1-3 — Always ask 4–5 history-based follow-ups.** `followup_min_questions=4` in `config.py`;
  don't report `complete` before min in `routes_followup.py`; broaden `_QUESTION_SYSTEM` in
  `services/followup.py`. Add a test. *(→ "Follow-up Questions".)*
- [ ] **P1-4 — Highlight MISSING required fields on the summary.** `renderSummary` + `.summary-item.missing`
  CSS in `frontend/kiosk.html`. *(→ "Missing Medical Information".)*
- [ ] **P1-5 — Confirm & Submit fast = background assessment.** Move M10/M11/M10C in
  `routes_dashboard.submit_visit` (:92) into FastAPI `BackgroundTasks`; keep status+audit sync. *(→ "Confirm and Submit".)*
- [ ] **P1-6 — Patient Portal UI polish** on top of STRUCT-3. *(→ "UI/UX".)*

### P2 — Medic Portal `/medic/`
- [ ] **P2-1 — Correct Dhaka date/time in the queue.** Shared `dhakaDateTime()` in `shared.js`
  (`toLocaleString(..., {timeZone:'Asia/Dhaka'})`, browser-side); fix `staff.js:51`. *(→ "Queue Time".)*
- [ ] **P2-2 — Patient details: add Gender + auto-fill Name/Age/Gender + editable.** Write
  `Patient.sex`/`birth_year` (exist, never written) via extended M3/M8 extraction; make name/age/gender
  editable (extend vitals PATCH or add a patient PATCH); add Gender row to `frontend_medic/index.html`
  `renderPostReferral`. *(→ "Patient Details".)*
- [ ] **P2-3 — Medic Portal UI polish.** *(→ "UI/UX".)*

### P3 — Doctor Portal `/doctor/`
- [ ] **P3-1 — Correct patient submission Dhaka date/time.** Add `Visit.submitted_at` (**Alembic 0011**),
  set in submit, expose in dashboard/detail, render with `dhakaDateTime()`. *(→ "Patient Time".)*
- [ ] **P3-2 — Show latest patient details incl. medic edits** (mostly verification). *(→ "Patient Details".)*
- [ ] **P3-3 — AI Medical Assistant (drug info): web search + LLM, side panel.** New `routes_assistant.py`
  → free web search (add `ddgs`/DuckDuckGo + `httpx`) → `call_module()` (new code e.g. M16) → structured
  answer + MANDATORY disclaimer "AI-generated information. Please verify before prescribing." (rule #2).
  *(→ "AI Medical Assistant".)*
- [ ] **P3-4 — Doctor Portal UI polish.** *(→ "UI/UX".)*

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

  