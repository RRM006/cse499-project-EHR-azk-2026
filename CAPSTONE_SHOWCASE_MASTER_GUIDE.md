# CAPSTONE SHOWCASE — MASTER GUIDE
### AI-Powered Voice-Based Medical Pre-Screening System for Bangladesh
**Course:** CSE499 (NSU) · **Prepared:** for the project showcase (the day before)

> **How to use this document.** Read Sections 1–3 first (they are what you *say*). Skim Sections 4–18 to understand the machine. Study Section 24 (Live Demo) and Section 26 (One-Page Speaking Guide) the night before. Section 27 (Judge Q&A) and Section 29 (Mock Viva) are your defense prep. Section 30 is your final "I must know these" checklist.
>
> **Ground rules this guide follows:** nothing here is invented. Every feature, number, and file name was cross-checked against the actual code in your repo. Where something is *planned but not built*, or *not measured*, it says so plainly — because a judge will find exactly those gaps, and it is far better that **you** raise them first.

---

## TABLE OF CONTENTS

1. What is this project?
2. 30-second / 1-minute / 3-minute explanations
3. The four non-negotiable rules
4. Complete system architecture
5. Complete end-to-end workflow (one patient's journey)
6. Every major module explained (M1–M16)
7. Patient Portal (kiosk)
8. Medic / Triage Portal
9. Doctor Portal
10. How data moves between the three portals
11. Speech Recognition (STT) — the hard part
12. AI / LLM — where it is used and where it is *not*
13. Backend & Database
14. FHIR / EHR / PDF
15. Security / Privacy / Safety
16. Testing
17. Technology stack (table)
18. What we actually achieved (Completed / Partial / Future)
19. Limitations (honest)
20. Impact (expected vs measured)
21. Live Demo Script (step by step)
22. Demo Backup Plan
23. One-Page Speaking Guide
24. Judge Q&A (grouped)
25. Hard Judge / Trick Questions
26. Mock Viva (build up from easy to hard)
27. Final "What I Must Know" Checklist
28. Items Requiring Your Confirmation

*(Sections are numbered for study order; they cover everything in your original brief.)*

---

## 1. WHAT IS THIS PROJECT?

**In one sentence:** Before a patient meets the doctor, they *speak* their problem in Bangla (or Banglish, or a regional dialect) into a kiosk; the system turns that speech into a clean, structured, risk-scored pre-screening report so the doctor walks in already knowing the story.

**The problem we solve.** In busy Bangladeshi clinics, consultations are short and rushed. Patients — often elderly, low-literacy, or more comfortable speaking than typing — struggle to describe symptoms fully. Important details get missed, doctors spend precious minutes on documentation instead of examination, and most digital health tools are English-first and typing-first, which excludes exactly the people who need them most.

**Who the users are:**
- **Patients** — speak naturally, in their own language, at a waiting-room kiosk/tablet. No typing skills needed.
- **Medic / triage staff** — see a queue ordered by urgency, verify what the AI understood, record vitals, and forward the case to a doctor.
- **Doctors** — receive a ready-to-read report: the patient's own words, a structured summary, a risk level with a plain-language reason, prominent red flags, and one-click prescription + EHR export.

**Why this matters in Bangladesh specifically:** Bangla is spoken by ~230 million people but is badly under-served by speech technology. Add regional dialects (Sylheti, Chittagonian, Barishal, Puran Dhaka), Banglish code-switching ("amar fever hoyeche 3 days"), and medical vocabulary, and off-the-shelf tools fall apart. Our own benchmark (Section 11) confirms this: even the best open-source Bangla ASR model we tested got **nearly half the words wrong**. So the design is built around that reality instead of pretending it away.

**What is novel about our approach** (say this — it's your differentiation):
1. **Voice-first, not typing-first** — the patient *speaks*; typing is only a fallback. This is the whole point, not a feature.
2. **We never rewrite the patient's words.** The raw transcript is stored permanently and untouched; all cleaning/structuring happens in *separate* later steps. This is a hard architectural rule, not a preference.
3. **The system assists, it never diagnoses.** It narrows the search space for the doctor and surfaces red flags; the doctor decides. Every risk score comes with an explanation.
4. **Three coordinated portals + interoperable output** — the encounter ends as an HL7 **FHIR** record and a human-readable PDF, so it can plug into a real EHR rather than dying in our database.

**The final goal:** a deployable clinic product — a Bangla voice interface for patients, a triage desk, a doctor dashboard, a secure backend, and standards-based clinical documentation — that a small clinic could actually install, not just read about in a paper.

---

## 2. THE THREE EXPLANATIONS (MEMORIZE THESE)

### 🕐 30-second version (the elevator pitch)
> "Our project is a voice-based medical pre-screening system for Bangladesh. Before a patient sees the doctor, they simply *speak* their symptoms in Bangla or Banglish at a kiosk. The system transcribes their speech, keeps their exact words, cleans and structures the information with AI, asks a few spoken follow-up questions, checks for danger signs, scores the urgency, and hands the doctor a ready-made, explainable report. It saves consultation time and makes sure nothing important is missed — and it never diagnoses; the doctor always decides."

### 🕐 1-minute version
> "In Bangladesh, clinic visits are short and patients — especially elderly or low-literacy ones — find it hard to describe symptoms, so consultations are rushed and details get missed. Our system fixes the *front* of that visit. The patient sits at a kiosk and speaks naturally in Bangla, Banglish, or a dialect. We capture their exact words — and we never change them, that's a strict rule. Then, in separate AI steps, we clean the text, pull out the symptoms, duration and severity, and ask targeted follow-up questions that are both shown on screen and read aloud. A rule-based safety check flags danger signs like chest pain or breathing trouble and forces a 'critical' rating. The system scores the case Low to Critical, writes a plain-language reason for the score, and assembles a structured report — no diagnosis. Triage staff verify it and record vitals; the doctor gets the whole picture the moment the patient walks in, and can export it as a standard FHIR health record and a PDF. It's built to run cheaply, on ordinary hardware, using free tools."

### 🕐 3-minute version
> "Let me give you the whole picture.
>
> **The problem.** Bangladeshi clinics are high-volume and time-pressured. A doctor might get a few minutes per patient, and a lot of that goes into asking the same basic questions and writing notes. Patients who are elderly, anxious, or not comfortable with English or typing often can't tell their story fully, so critical information is lost. Existing digital health tools are typing-first and English-first, which excludes the very people who struggle most.
>
> **Our solution.** We move symptom-collection to *before* the consultation, and we make it voice-first. The patient identifies themselves with a phone number and a one-time code, then just talks — in Bangla, Banglish, or a regional dialect. Behind that simple experience is a 15-module pipeline. Module 1 captures speech to text. We store the patient's exact words permanently and never edit them — cleaning happens in a *separate* field, because trusting a machine to rewrite what a patient said is dangerous. Then AI modules extract the clinical details, summarize the chief complaint, find what's missing, and generate follow-up questions that are spoken aloud and shown on screen. A local, deterministic rule scans for red-flag phrases — chest pain, stroke signs, trouble breathing — and forces the case to 'Critical' no matter what the AI thinks. A risk module rates the case Low, Medium, High, or Critical, and an explainable-AI step writes a plain-language reason a doctor can verify.
>
> **The people side.** There are three portals. The patient kiosk is voice-first and elderly-friendly. The medic/triage desk sees a queue sorted by urgency, checks the AI's reading against the patient's own words, records vitals, and forwards the case. The doctor sees the safety story first, the patient's history, the structured report, and can write a prescription and export the encounter as a standard **FHIR** health record plus a PDF — so it's interoperable, not locked in our database.
>
> **The honesty.** The system never diagnoses; it narrows the options and the doctor decides. Every risk score is explained. And we're realistic about Bangla speech recognition — we benchmarked eighteen open-source models and the best still got about half the words wrong on dialect medical speech, which is exactly why we preserve the raw words and design for imperfect transcription. It runs on ordinary CPUs with free tools, so a small clinic could actually deploy it."

*(Practice the 3-minute version out loud twice. The judges' first impression is set in the first 30 seconds — nail the short one cold.)*

---

## 3. THE FOUR NON-NEGOTIABLE RULES (the soul of the project)

These four rules appear throughout the codebase and are enforced by tests. If you remember nothing else technical, remember these — they answer half of the "did you think about safety/ethics?" questions.

| # | Rule | What it means in practice | Where it lives in code |
|---|------|---------------------------|------------------------|
| **1** | **Never change the patient's exact words.** | The raw transcript is stored *once* and never edited. Cleaning/correction is a *separate* step saved in a *separate* column. "Raw is forever." | `utterances.raw_text` is write-once; `corrected_text` is a different column. Guarded by tests like `test_raw_immutable.py`. |
| **2** | **The system never diagnoses.** | It narrows the search space and surfaces information. The doctor decides. The AI "suggested condition" is always labelled "not a diagnosis" and is *excluded* from the exported health record. | Every AI prompt says "NEVER diagnose"; the prescription's Diagnosis field is doctor-typed only, never AI-filled. |
| **3** | **Surface red flags; never reassure falsely.** | A local rule flags clearly life-threatening symptoms and forces "Critical". A failed AI call defaults to *Medium*, never *Low*. Staff cannot downgrade a red-flag Critical. | `red_flags.py` + `risk.py`. The rule runs *regardless* of the AI outcome. |
| **4** | **Patient data is sensitive.** | Development uses synthetic/consented data only. We never send real patient data to a free AI tier that may train on it. (Note: the browser STT sends audio to Google's cloud — flagged openly.) | Documented in `constitution.md`; Mistral (which trains on inputs) is left disabled by default. |

> **Say to a judge:** "These four rules constrain every module. They exist because the honest failure mode of a system like this is a machine confidently rewriting or over-interpreting what a sick person said. We designed so that can't happen silently."

## 4. COMPLETE SYSTEM ARCHITECTURE

This is the **actual** flow built in the repo (not a generic template). Read it top to bottom.

```
                       ┌─────────────────────────────────────────┐
                       │   PATIENT at kiosk (tablet in waiting    │
                       │   area) — speaks Bangla/Banglish/dialect │
                       └───────────────────┬─────────────────────┘
                                           │ phone number + OTP (one-time code)
                                           ▼
   ┌──────────────────────────────────────────────────────────────────────┐
   │  FRONTEND (plain HTML/JS)  —  frontend/kiosk.html + kiosk.js           │
   │  • Browser Web Speech API captures speech (lang = bn-BD)               │
   │  • Text shown on screen AND questions read aloud (TTS)                 │
   └───────────────────┬──────────────────────────────────────────────────┘
                        │  HTTP/JSON (REST)  → each turn = one "utterance"
                        ▼
   ┌──────────────────────────────────────────────────────────────────────┐
   │  BACKEND — FastAPI (backend/app)                                       │
   │                                                                        │
   │  M1  Speech-to-Text ........ raw_text stored UNCHANGED (rule #1)       │
   │  M2  Correction ............ separate corrected_text column (LLM)      │
   │  M3  Info Extraction ....... 10 structured fields, bilingual (LLM)     │
   │  M4  Clinical Summary ...... 2–4 sentence chief complaint (LLM)        │
   │  M6  Missing-Info Analysis . present vs missing checklist (LLM)        │
   │  ┌── M7 Follow-up Question (LLM) ── shown on screen + spoken (TTS) ──┐  │
   │  │   M8 Process Answer & update profile (LLM)                        │  │
   │  │   M9 Completion check (LOCAL) — enough info? ── loop back to M7 ──┘  │
   │  M10 Risk Assessment ....... LLM base tier + LOCAL red-flag rule       │
   │  M11 Explainable AI ........ plain-language reason for the tier (LLM)  │
   │  M12 Structured Report ..... assembled locally, NO diagnosis          │
   │  M13 EHR Database .......... SQLite (18 tables), everything stored     │
   └───────────────────┬──────────────────────────────────────────────────┘
                        │ visit.status = 'awaiting_review'
                        ▼
   ┌──────────────────────────────────┐     ┌──────────────────────────────┐
   │  MEDIC / TRIAGE PORTAL  /medic/   │     │  DOCTOR PORTAL  /doctor/     │
   │  • queue sorted by URGENCY        │ ──▶ │  M14 Doctor Dashboard        │
   │  • verify AI fields vs raw words  │forward │  • risk + red flags + XAI  │
   │  • record vitals (wt/BP/sugar)    │     │  • patient history/timeline  │
   │  • forward to a named doctor      │     │  • prescription (.docx)      │
   └──────────────────────────────────┘     │  • EHR export: FHIR + PDF    │
                                            │  M16 drug/test info assistant │
                                            │  M15 feedback (partial)       │
                                            └──────────────────────────────┘
```

**Reading the diagram as "what enters / what happens / what comes out":**

| Stage | What enters | What happens | Which file | What comes out |
|---|---|---|---|---|
| Kiosk capture | Patient's voice | Browser converts speech→text live | `frontend/kiosk.js` | Raw text per turn |
| M1 store | Raw text | Saved once, never edited | `db/models.py` (`Utterance`) | An immutable `raw_text` row |
| M2 correct | Raw text | LLM fixes spelling/normalizes | `services/correction/` | `corrected_text` (separate) |
| M3 extract | Conversation | LLM pulls 10 fields (bilingual) | `services/intake.py` | `summary_fields` JSON |
| M4 summary | Conversation | LLM writes chief complaint | `services/intake.py` | 2–4 sentence summary |
| M6 gaps | Fields + convo | LLM lists present vs missing | `services/intake.py` | `{present, missing}` |
| M7 question | Gaps + history | LLM writes next question | `services/followup.py` | One bilingual question |
| M8 update | Patient's answer | Re-extract, merge into profile | `services/profile_update.py` | Updated profile |
| M9 check | Profile | Count filled fields (LOCAL) | `services/completion.py` | complete? loop or stop |
| M10 risk | Whole case | LLM tier + LOCAL red-flag rule | `services/risk.py` + `red_flags.py` | Low/Med/High/Critical + flags |
| M11 XAI | Tier + drivers | LLM writes the reason | `services/risk.py` | Plain-language explanation |
| M12 report | Everything | Assemble sections (LOCAL) | `services/report.py` | Structured report (no dx) |
| M13 store | All of it | Persist to SQLite | `db/` | The permanent record |
| M14 review | The visit | Doctor reads/overrides | `frontend_doctor/` + `routes_dashboard.py` | Decision + prescription |
| Export | The visit | Build FHIR bundle + PDF | `services/ehr_export.py`, `ehr_pdf.py` | `.fhir+json` + `.pdf` |

**Why the pipeline is shaped this way (principles actually in the code):**
- **The `visit` is the aggregate root.** One pre-screening = one `visit`; every output (utterances, profile, risk, report, review) hangs off it. Adding a new output later = a new child table, nothing existing breaks.
- **Raw is immutable; everything else is derived.** The database is the source of truth; the `.docx`/`.pdf`/FHIR files are *regenerable exports*.
- **LLM provider is config, not code.** Which AI serves which module is a data map (`MODULE_PROVIDERS`), so swapping providers is a `.env` change.
- **Everything runs on one `uvicorn` command, SQLite, and free APIs** — no GPU, no paid infrastructure.

---

## 5. COMPLETE END-TO-END WORKFLOW (one patient's journey)

Here's a concrete, realistic example you can narrate. **Patient: Rafiq, 68, with a 3-day fever and cough.**

1. **Rafiq sits at the kiosk.** He enters his phone number. The system texts (or, in dev mode, logs) a 6-digit **OTP**; he enters it. This is his login — no password, no typing his history.
   - *Backend:* `POST /api/patients/lookup` issues a real OTP (hashed, 5-min expiry); `verify-otp` checks it. A `visit` row is created with status `in_progress`.

2. **The assistant greets him and asks him to describe his problem.** The question is **read aloud** (TTS) and **shown on screen**. The mic opens itself; Rafiq says: *"তিন দিন ধরে জ্বর আর কাশি, শরীর দুর্বল লাগছে।"* ("Fever and cough for three days, feeling weak.")
   - *Backend:* the raw text is stored **unchanged** as an `utterance` (`source='mic'`, `stt_provider='browser_webspeech'`).

3. **The system reads his answer back to him** ("You said: …") and waits for a yes/tap so a misheard sentence never slips through silently. Then it processes the turn.
   - *M2* cleans the text into a separate field. *M3* extracts fields: main problem = fever + cough, duration = 3 days, etc. *M4* writes a summary. *M6* notices what's missing (temperature? breathing difficulty? medications?).

4. **The system asks follow-up questions**, one at a time, spoken + on screen: *"জ্বর কি থার্মোমিটার দিয়ে মেপেছেন?"* ("Did you measure the fever with a thermometer?"). Rafiq answers by voice. *M8* merges each answer; *M9* checks whether enough is collected; if not, *M7* asks again — up to a configured limit so he doesn't get fatigued.

5. **Risk + safety.** *M10* runs: the **local red-flag rule** scans everything for danger phrases (none here → no forced Critical), and the LLM rates the case (say, **Medium** — fever >3 days in an elderly patient warrants examination). *M11* writes: *"Medium risk: fever lasting more than 3 days, cough, and patient age over 65."*

6. **Review & submit.** Rafiq sees a summary of what the system understood, can correct anything by voice, and confirms. The visit flips to **`awaiting_review`** and lands on the medic queue.

7. **Medic desk.** A triage staff member opens `/medic/`. Rafiq's case is near the top because of his age/tier. They compare the 10 AI-extracted fields against his **verbatim words**, fix anything wrong (their edit is marked `human`, and the AI can never overwrite it), record his **vitals** (weight, BP, blood sugar), then **forward** to Dr. Rahman. Status → **`awaiting_doctor`**.

8. **Doctor.** Dr. Rahman opens `/doctor/`. She sees the **safety story first** (tier, red flags, XAI reason), then Rafiq's **history/timeline** (has he come before with this?), his own words, and the structured summary. She writes a prescription (she types the diagnosis herself — the AI never fills it), and clicks **"Accept & Write to EHR"**, producing a **FHIR** health record and a **PDF**. Status → **`reviewed`**.

**The data trail, end to end:**
```
Rafiq speaks → utterances.raw_text (immutable)
            → utterances.corrected_text (M2)
            → case_profiles.entities.summary_fields (M3/M8, bilingual)
            → case_profiles.summary (M4), .gaps (M6)
            → followup_questions (M7/M8)
            → risk_assessments (M10, append-only) + xai_explanations (M11)
            → reports (M12)
            → medic edits summary_fields (source='human') + patients vitals
            → doctor_reviews + prescriptions + documents (.docx/.pdf/FHIR)
            → audit_log rows the whole way (who did what)
```

## 6. EVERY MAJOR MODULE EXPLAINED (M1–M16)

There are 15 numbered modules (with a deliberate gap at M5) plus M16. **Modules 1–14 are built and working; M5 is retired; M15 is partial; M16 is built.** For each module: what it does, why, where it lives, how it works, and one line to say to a judge.

> **Quick reference — which modules use AI vs run locally:**
> **LLM (cloud API):** M2, M3, M4, M6, M7, M8, M10 (base tier only), M11, M12 (wording), M16.
> **Local / no API:** M1 (browser STT is client-side), M9, M10's red-flag rule, M12 assembly, M13, M14, M15.

---

### Module 1 — Speech-to-Text (STT)
- **What it does:** Turns the patient's spoken Bangla/Banglish/dialect into text, live.
- **Why we need it:** It's the front door. The patient speaks; everything downstream needs text.
- **Where:** `frontend/kiosk.js` (the browser's **Web Speech API**, `lang='bn-BD'`, `continuous`, `interimResults`). The backend just stores what comes back.
- **How it works:** The browser streams microphone audio to Google's speech service and returns text as the person talks. Each finished turn is POSTed to the backend and stored.
- **Input:** Microphone audio. **Processing:** browser speech recognition. **Output:** raw text (stored unchanged, `stt_provider='browser_webspeech'`).
- **Example:** Rafiq says *"তিন দিন ধরে জ্বর"* → text "তিন দিন ধরে জ্বর".
- **⚠ Key honesty:** This uses the **browser's** recognizer (Google cloud), *not* a model we trained. A local, private recognizer (`faster-whisper`) is the planned Phase-1 upgrade — see Section 11.
- **Say to a judge:** "Module 1 uses the browser's Web Speech API for the live demo — it's the fastest, most accurate path for standard Bangla today. We benchmarked local open-source models as the offline replacement; that's future work, and I can tell you why."

### Module 2 — Text Processing & Normalization (Correction)
- **What it does:** Cleans the raw text — spelling, filler removal, Banglish normalization — in a **separate field**.
- **Why:** ASR output is messy; downstream extraction works better on clean text. But we must *not* touch the original.
- **Where:** `services/correction/openai_compatible.py` (LLM, Gemini Flash bucket).
- **Input:** `raw_text`. **Processing:** one LLM call. **Output:** `corrected_text` (a *different* column — rule #1).
- **Example:** "amar fever 3 din" → "আমার তিন দিন ধরে জ্বর".
- **Say to a judge:** "Correction never overwrites the raw words — it writes a parallel corrected field, so we can always show exactly what the patient said."

### Module 3 — Information Extraction
- **What it does:** Pulls structured clinical data into a fixed 10-field summary, each field **bilingual** (English + Bangla).
- **Why:** A doctor needs structured facts (symptom, duration, severity, meds, allergies…), not a wall of text.
- **Where:** `services/intake.py` (LLM, Gemini Flash-Lite bucket — cheap structured task).
- **Input:** the conversation. **Processing:** one LLM extraction call returning strict JSON. **Output:** `summary_fields` (10 keys), plus `problem_area` and patient demographics (name/age/sex — *only if the patient stated them*, never guessed).
- **Example:** `{main_problem: "fever & cough", onset: "3 days", ...}`.
- **Say to a judge:** "Extraction fills a fixed 10-field shape so the doctor always sees the same structure, and it's stored bilingually because the clinic reads both."

### Module 4 — Initial Clinical Summary
- **What it does:** Writes a 2–4 sentence chief-complaint summary for the doctor.
- **Where:** `services/intake.py` (LLM, Gemini Flash).
- **Output:** e.g. *"Patient reports fever and dry cough for 3 days with mild fatigue. No breathing difficulty or chest pain mentioned."* — **no diagnosis**.
- **Say to a judge:** "It summarizes only what the patient actually said — no interpretation, no disease names."

### Module 5 — Emergency Detection — **RETIRED**
- **Status:** Removed as a standalone module (decision ADR-0024). The module numbering keeps a gap at 5 on purpose (so all the M6–M15 references in our docs and tests stay valid).
- **Why retired:** A standalone auto-escalation module implied the system could triage emergencies autonomously — which we explicitly don't do. The *safety responsibility* moved **into Module 10** as a rule-based red-flag check.
- **Say to a judge:** "We deliberately don't do autonomous emergency triage. The red-flag safety check lives inside risk assessment instead, and it flags danger to the doctor rather than acting on its own."

### Module 6 — Missing Information Analysis
- **What it does:** Lists what's known vs still missing for a complete picture.
- **Where:** `services/intake.py` (LLM, Groq bucket).
- **Output:** `{present: [...], missing: [...]}` — e.g. ✓ fever ✗ temperature ✗ breathing assessed. This drives the follow-up loop.
- **Say to a judge:** "This is what makes the follow-up intelligent — it asks about gaps, not random questions."

### Module 7 — Dynamic Follow-up Question Generation
- **What it does:** Generates the next targeted question, **shown as text AND read aloud (TTS)**; the patient answers by voice.
- **Where:** `services/followup.py` (LLM, Groq — a fast live-loop task). It also has an **output guard** that blocks a generated question that strays into dosing/prescribing, and a deterministic fallback question so a rejected question never costs the patient their turn.
- **Input:** gaps + conversation + patient age/sex/area. **Output:** one bilingual question, stored (so it's never repeated).
- **Example:** *"জ্বর কি গতকাল থেকে? থার্মোমিটার দিয়ে মেপেছেন?"* / "When did the fever start? Did you measure it?"
- **Say to a judge:** "Questions are age-appropriate, never repeat what's answered, and every question is both spoken and shown — for elderly and low-literacy patients."

### Module 8 — Response Processing & Profile Update
- **What it does:** Runs each answer back through extraction and **merges** it into the profile, protecting human-edited fields.
- **Where:** `services/profile_update.py` (LLM). **Output:** updated `summary_fields` (a merge, not a replace — so a staff correction or a found body-area is never wiped).
- **Say to a judge:** "Answers flow through the *same* pipeline as the first turn — one path, not a special case."

### Module 9 — Case Completion Check
- **What it does:** Decides if enough is collected. **Local, no AI.**
- **Where:** `services/completion.py`. Completeness = fraction of the 10 fields filled; the loop stops on a threshold or a max-question cap (avoids patient fatigue).
- **Say to a judge:** "Completion is deterministic and local — we don't spend an API call to count filled fields, and the loop has a hard cap so patients aren't interrogated."

### Module 10 — Risk Assessment Engine (with the red-flag rule)
- **What it does:** Classifies the case **Low / Medium / High / Critical**, and runs the **local red-flag rule** that forces Critical for clearly life-threatening symptoms.
- **Where:** `services/risk.py` (LLM base tier) + `services/red_flags.py` (local rule).
- **How it works (this is important — memorize the ordering):**
  1. The **local red-flag rule runs first** and its result survives any AI failure.
  2. The **LLM** proposes a base tier (best-effort).
  3. **Combine:** if a red flag matched → **Critical**, period. If the AI call failed/unparseable → default **Medium** (never silently Low). Assessments are append-only.
- **Red-flag categories (5):** chest pain, severe breathing difficulty, stroke signs, loss of consciousness, severe uncontrolled bleeding — each with Bangla, Banglish, and English trigger phrases, matched as substrings, tuned for **recall over precision** ("a false Critical costs attention; a miss costs a life").
- **Say to a judge:** "The safety net is a deterministic local rule, not the AI. The AI can only ever *raise* concern — it can never suppress a red flag or talk the system out of Critical."

### Module 11 — Explainable AI (XAI)
- **What it does:** Writes a 1–3 sentence plain-language reason for the risk tier. Every risk row gets one.
- **Where:** `services/risk.py` (LLM, with a **deterministic fallback** if the call fails — a risk score is never stored without a reason).
- **Example:** *"Medium risk was assigned due to: fever lasting more than 3 days and patient age over 65."*
- **Say to a judge:** "No opaque scores — the doctor can read *why* and disagree. If the AI can't produce a reason, we generate one from the rule trace, so a reason always exists."

### Module 12 — Structured Clinical Report
- **What it does:** Assembles the doctor-facing report: profile, chief complaint, symptoms, **red flags**, Q&A, risk + explanation, possible condition *categories* (not a diagnosis), next steps.
- **Where:** `services/report.py` (assembled **locally**), with a disclaimer. **Contains no diagnosis.**
- **Say to a judge:** "The report is assembled from stored data — it's regenerable and it never contains a diagnosis."

### Module 13 — EHR Database
- **What it does:** Securely stores everything — transcripts, profiles, questions, risk, reports, audit log — linked to patient + timestamps.
- **Where:** SQLite via SQLAlchemy + Alembic (**18 tables, migration head 0014**). The `visit` is the aggregate root; append-only tables for anything clinical/accountability.
- **Say to a judge:** "One encounter is one `visit`, and every output hangs off it. It's SQLite now, but the URL is config-driven, so moving to Postgres is a one-line change — no schema rewrite."

### Module 14 — Doctor Dashboard
- **What it does:** The doctor's review UI — risk/red-flags/XAI first, patient timeline, verbatim words, editable fields, review/override, prescription, EHR export.
- **Where:** `frontend_doctor/index.html` + `routes_dashboard.py`, `routes_history.py`, `routes_prescription.py`.
- **Say to a judge:** "The doctor sees the safety story first, then the history, then the words. They can override the AI's fields and tier, and nothing is decided until a human acts."

### Module 15 — Feedback & Continuous Learning — **PARTIAL**
- **What it does (built):** The doctor can rate/override; feedback is captured in the `feedback` and `doctor_reviews` tables for later use.
- **What is NOT built (be honest):** The offline **retraining/fine-tuning pipeline** with regression testing. The data capture exists; the learning loop is future work (it depends on having our *own* trainable models, which ties back to the STT roadmap).
- **Say to a judge:** "We capture the feedback signal today — ratings, overrides, corrections. The retraining pipeline is future work; it's marked as such and it's honest that we don't retrain yet."

### Module 16 — Doctor Drug/Test Information Assistant
- **What it does:** The doctor can ask about a medicine or a diagnostic test (and, on explicit opt-in, "what test might suit this patient?"). It does a **free web search** + one LLM call, and attaches a mandatory disclaimer **server-side**.
- **Where:** `services/assistant.py` (DuckDuckGo via `ddgs` + LLM). **Guardrails:** the web search only ever gets the doctor's typed question (never patient data); patient context, when used, is **de-identified** and carries **no raw transcript**; the answer is informational, never a prescription/order.
- **Say to a judge:** "It's an information helper, not a prescriber. The disclaimer is attached by the server, not the model, so the AI can't talk its way out of it, and patient data never reaches the search engine."

## 7. PATIENT PORTAL (the kiosk)

**URL:** `/kiosk.html` · **Files:** `frontend/kiosk.html` + `frontend/kiosk.js` (the biggest single frontend file). **Persona:** an often elderly or non-technical patient, alone with a screen. **The one question it answers:** *"Tell us what is wrong, in your own words."*

**What the patient does, step by step:**
1. **Identify:** enters phone number → receives an **OTP** → enters it (digits can be spoken too, and are read back before use so a wrong digit can't send the code to a stranger).
2. **Speak:** the assistant asks a question (spoken + on screen); the **mic opens itself** after the voice finishes (with a short "echo guard" so the system never transcribes its own question); a visible **3-2-1 countdown** confirms the turn ended — but any resumed speech cancels it, so an answer is never clipped.
3. **Confirm:** each spoken answer is **read back** ("You said: …") and the patient accepts or repeats it — the one moment they can catch a mishearing.
4. **Follow-ups:** answers more spoken questions until the system has enough.
5. **Review:** sees a plain summary of what was understood, can correct by voice, and taps **Confirm & Submit**. The kiosk auto-logs-out for the next patient.

**Key patient-portal facts for a judge:**
- **Voice-first, typing always available.** The design actively guides the patient to speak, but a text box is always there for a failed mic, a noisy room, or preference. Both modes use the *same* backend path (they differ only by `source='mic'|'manual'`).
- **Language handling:** UI is bilingual (English/বাংলা toggle); questions are generated and spoken in Bangla; the raw transcript keeps whatever the patient actually said.
- **Elderly-friendly UX:** large touch targets, spoken questions, read-backs, no time pressure, minimal clicks.
- **Raw transcript:** the patient can download their own verbatim transcript; it's never shown as editable.
- **After submission:** the visit becomes `awaiting_review` and appears on the medic queue. The patient's job is done.

> **Say to a judge:** "The kiosk is voice-first for a reason — our target user is elderly or low-literacy. Everything is spoken and shown, answers are read back before they count, and typing is always there as a fallback."

---

## 8. MEDIC / TRIAGE PORTAL

**URL:** `/medic/` · **File:** `frontend_medic/index.html` (+ shared `frontend_shared/staff.js`, backend `services/triage.py`, `routes_dashboard.py`). **Persona:** clinic triage staff at a desk working a queue. **The one question it answers:** *"Who do I handle next, and is this case fit to hand to a doctor?"*

**What the medic sees and does:**
- **A queue ordered by URGENCY, not arrival** — worst tier first, then longest wait. (An unassessed case sorts *between* High and Medium so it can't hide.) Each row shows a **wait-time chip**, a **red-flag chip**, and an **intake completeness meter**.
- **A floor-load strip** — how many are waiting / critical / high / not assessed / the longest wait — the "how bad is the floor right now" answer a triage desk is accountable for.
- **The verbatim panel** — the patient's exact words, **read-only** (rule #1). They compare it against the 10 AI-extracted fields and **correct** anything wrong; the corrected field is marked `source='human'` and the AI can never overwrite it.
- **Risk panel with a staff override** (audit-logged) — but a **red-flag Critical cannot be downgraded** by a medic; only the doctor decides at review.
- **Intake & Vitals — recorded BEFORE forwarding:** weight, height (→ live BMI, shown against WHO + WHO-Asian bands but never stored), blood pressure, and blood sugar (value + measurement context together — a fasting 6.5 and a random 6.5 are different facts). No interpretation is stored — the published reference chart is shown beside the reading.
- **A handover check** (advisory) — says what the doctor is about to be missing, while the medic can still fix it. **It can never block a forward** — a Critical patient must reach a doctor even with incomplete paperwork.
- **Forward to a named doctor** — status → `awaiting_doctor`, and the forwarding medic is recorded in the audit log. A post-referral summary `.docx` can be downloaded.

> **Say to a judge:** "The medic's job is triage and verification. They decide who's seen next, they check the AI against the patient's actual words before a doctor ever trusts it, and they capture vitals up front. The safety rules are enforced here too — they can escalate a case but can't hide a red flag."

---

## 9. DOCTOR PORTAL

**URL:** `/doctor/` · **File:** `frontend_doctor/index.html` (+ backend `routes_history.py`, `routes_prescription.py`, `routes_report.py`, `services/history.py`, `ehr_export.py`, `ehr_pdf.py`). **Persona:** the physician, one patient at a time, deciding. **The one question it answers:** *"What is going on with this person, and what do I do about it?"*

**What the doctor sees and does:**
- **Safety story first** — the risk tier, red flags, and the XAI reason are shown before anything else.
- **Patient timeline / history** — prior visits (date, complaint, tier, red flags, treating doctor) and **prior prescriptions** from any doctor, with `.docx` links. (This answers "third time this month with the same complaint?" — but it *interprets nothing*; two visits with the same complaint are just two dated rows. And it carries **no transcript** — the doctor opens the prior visit to read the one immutable copy.)
- **The verbatim words + the structured summary**, and the same editable 10 fields (a doctor edit is also `human`).
- **The AI "suggested condition" card** — always labelled "AI Suggestion – Not a Diagnosis", and it **never** flows into the prescription's Diagnosis field.
- **M16 drug/test assistant** — look up a medicine/test without leaving the case; the reply always carries its disclaimer.
- **Decide** — Accept & Write to EHR, or Override to Low-Risk, with notes.
- **Prescribe** — the doctor **types the diagnosis themselves** (never AI-filled), generates a prescription `.docx` on a reusable letterhead, and can find it later under a "Completed" scope.
- **Export the encounter** — **"Accept & Write to EHR"** produces an actual **HL7 FHIR R4 document Bundle** (`application/fhir+json`) and a human-readable **PDF** (properly shaped Bangla).

> **Say to a judge:** "The doctor is always in control. The AI suggestion is walled off from the diagnosis, the diagnosis is typed by a human, and the output is a standards-based FHIR record plus a PDF — so the encounter is interoperable, not trapped in our app."

---

## 10. HOW DATA MOVES BETWEEN THE THREE PORTALS

This is a favourite judge question ("how do the parts talk to each other?"). The answer is clean: **a one-directional status flow on a single `visit`, and everyone reads the same rows — there is no copying and no messaging.**

```
  in_progress ──patient submits──▶ awaiting_review ──medic forwards──▶ awaiting_doctor ──doctor reviews──▶ reviewed/closed
   (KIOSK)                            (MEDIC queue)                        (DOCTOR queue)
```

- **Kiosk → Medic:** the patient produces `utterances` (raw words) and the pipeline fills `case_profiles`. On submit, `visit.status = awaiting_review` and it appears on the medic queue. The medic never talks to the kiosk; they read what the patient produced.
- **Medic → Doctor:** one hand-off — `POST /visits/{uuid}/assign` sets `assigned_doctor_id` and status `awaiting_doctor`, and records the forwarding medic in `audit_log`. **Everything the medic edited is visible to the doctor because both read the same `case_profiles` row** — no second copy, no message passed.
- **Doctor → back:** the doctor writes `doctor_reviews` and `prescriptions`; the prescription `.docx`/PDF is the artifact that crosses back to the patient.
- **Deliberately NOT shared:** the kiosk never sees a queue, tier, red flag, or suggested condition. The medic never sees prescriptions or the drug assistant. The doctor never sees the triage load strip.

**Data-ownership in one line:** the patient owns the raw words (write-once); the medic/doctor own vitals and the *derived* fields (marked `human`); risk is append-only; who-did-what is in `audit_log`. Derived things (wait time, completeness, history, queue load) are **computed per request, never stored** — so renaming a patient updates the queue instantly, because nothing cached an identity it doesn't own.

> **Say to a judge:** "There's one workflow state machine and one shared record. Portals coordinate by moving the visit's status forward and reading the same rows — not by copying data around or sending messages, which is how these things usually drift out of sync."

## 11. SPEECH RECOGNITION (STT) — THE HARD PART

This is the heart of the project's *research* story. Frame it as **supporting background** that justifies the design (per your decision), and be ready to go deep if asked.

### Why Bangla speech recognition is genuinely difficult
- **Bangla is low-resource for speech tech.** ~230M speakers, but far less labelled audio data than English, so models are weaker.
- **Dialects.** Sylheti, Chittagonian, Barishal, and Puran Dhaka differ enough that a model trained on "standard" Bangla mishears them badly.
- **Banglish / code-switching.** Real patients mix languages: *"amar 3 days ধরে fever, cough ও আছে."* A recognizer trained on pure Bangla or pure English chokes on the switches.
- **Medical terminology & drug names** are rare words the models haven't seen.
- **Clinic noise** — a waiting room is not a quiet recording booth.

### Why a raw transcript alone is not enough — and why we never rewrite it
Because recognition is imperfect, two design choices follow directly:
1. We **keep the raw transcript exactly as recognized** (rule #1) — so a human can always see what was actually captured and catch errors.
2. We do **cleaning and structuring as separate later steps** (M2/M3) — improving the *derived* text without ever destroying the *original*. Converting spoken Banglish straight into "clean" Bangla script can silently lose meaning, so we normalize downstream, not at capture.

### What STT the system actually uses (be precise here)
- **Deployed now:** the **browser's Web Speech API** (`bn-BD`), which is Google's cloud recognizer. It's the most accurate quick-start path for standard Bangla, needs no server and no key, and gives ~real-time results. **This is what runs in the demo.**
- **Investigated as the future local/private replacement:** open-source models we benchmarked (Whisper family, wav2vec2/XLSR, MMS, SeamlessM4T, and larger ones like Qwen2-Audio, Voxtral). **Planned Phase-1 path:** `faster-whisper` (CPU, int8) for an offline, private recognizer.
- **⚠ Fallback vs primary:** the *typed text box* is the fallback when the mic fails. There is not currently a second live STT engine running as automatic fallback — that's the local-model roadmap.

### Our ASR benchmark (this is your measured research result)
We evaluated open-source ASR models on **Bangla multi-dialect medical speech** and computed **WER (Word Error Rate)** and **CER (Character Error Rate)**. Results (lower is better):

**Baseline models — best performers:**

| Model | WER | CER |
|---|---|---|
| **bengaliai_regional (best)** | **0.469** | **0.243** |
| bengaliai_whisper | 0.505 | 0.308 |
| mms | 0.557 | 0.269 |
| vakyansh_bn | 0.614 | 0.295 |
| wav2vec2_xlsr_cv_bn | 0.681 | 0.437 |
| whisper_large_v3 | 0.910 | 0.583 |
| whisper_medium | 1.168 | 1.230 |
| whisper_small | 1.958 | 1.706 |

**"Bigger" models (>1B params) — all *worse*, WER > 1.0:** qwen2_audio (via English) 1.004, qwen2_audio (direct) 1.084, qwen3_asr 1.134, voxtral_mini 1.363.

**The two headline takeaways for judges:**
1. **Even the best open-source model got ~47% of words wrong** on our dialect medical speech (WER 0.469). Larger, newer models were *not* better — several were dramatically worse. Bigger ≠ better for low-resource Bangla.
2. **On the dialects specifically** (Sylheti, Puran Dhaka, Barishal), exact-sentence accuracy was essentially **zero** across models — direct evidence that dialect Bangla is an open problem.

*(These numbers live in `evaluation/` as CSVs and charts. They are for the **candidate open-source models**, which justify our architecture and roadmap — they are **not** the accuracy of the browser STT the demo uses.)*

### WER explained simply (and why it can exceed 100%)
**WER = (Substitutions + Deletions + Insertions) ÷ (number of words in the reference).**

*Example.* Reference (what was said): "আমার তিন দিন ধরে জ্বর" (5 words). Recognized: "আমার তিন দিন জ্বর ছিল" — one word deleted ("ধরে"), one word inserted ("ছিল"), one substituted. That's 3 errors ÷ 5 words = **0.60 = 60% WER**.

**Why WER can be > 100%:** the denominator is the *reference* length, but **insertions** are counted in the numerator with no upper limit. If a model **hallucinates** and outputs far more words than were spoken (common with Whisper on noisy/short clips — it repeats or invents text), the error count can exceed the number of reference words. So a WER of 1.958 (195.8%, whisper_small) means the model produced roughly twice as many errors as there were words to get right — usually runaway hallucinated output. **This is itself a finding:** high-capacity models fail *unsafely* on Bangla by inventing text, which is exactly why rule #1 (never trust/rewrite the transcript) matters.

> **Say to a judge:** "We didn't assume Bangla ASR was good enough — we measured it. The best open model still missed about half the words on dialect medical speech, and the biggest models were worse, sometimes hallucinating past 100% WER. That result shaped the whole architecture: preserve the raw words, structure them in separate steps, keep a human in the loop, and never let the machine silently rewrite a patient."

---

## 12. AI / LLM — WHERE IT IS USED (AND WHERE IT IS NOT)

Be crisp about this — judges will test whether you know the difference between "speech recognition", "an LLM", and "diagnosis".

### The four distinct layers (say them clearly)
1. **Speech Recognition (STT)** — audio → text. This is the **browser Web Speech API**. *Not* an LLM.
2. **AI Processing (LLM)** — text → structure. Cleaning, extraction, summary, gap-finding, follow-up questions, risk wording, XAI explanation. This is where **large language models** are used.
3. **Clinical Decision Support** — surfacing risk tiers, red flags, and possible condition *categories* to help the doctor. Assistive, explainable.
4. **Diagnosis** — deciding the disease. **We do NOT do this. Ever.** The doctor diagnoses.

### Which model/provider serves which module
The LLM is a **swappable OpenAI-compatible client**. Which provider serves which module is a config map (`MODULE_PROVIDERS`), not hard-coded logic:

| Provider (free tier) | Role | Modules |
|---|---|---|
| **Gemini Flash** | Quality tasks | M2 correction, M4 summary, M10 risk wording, M11 XAI, M12, M16 |
| **Gemini Flash-Lite** | Cheap structured extraction | M3, M8 |
| **Groq (Llama-class, very fast)** | Live-loop tasks | M6, M7 |
| **Cerebras / Mistral / OpenRouter** | Fallbacks | universal fallback chain |

*(Current model ids in config: `gemini-flash-latest`, `gemini-flash-lite-latest`, Groq `openai/gpt-oss-120b`, and an OpenRouter list of `:free` models. These rotate — that's why there's a key-checker script.)*

### The API flow (one module call)
```
module (e.g. M3) → call_module() → pick assigned provider bucket
   → try each configured KEY (up to 3), each MODEL, in order
   → on 429/quota, cool down THAT (bucket,key,model) briefly and move on
   → success → parse JSON/text, log a module_events row (provider, latency)
   → total failure → safe error (no provider details leak to the patient)
```
**Redundancy has three multiplying dimensions:** BUCKETS (provider list) × KEYS (up to 3–4 per provider) × MODELS (comma-separated lists). Order: every model of key 1, then key 2, then key 3, then the next provider. A rate-limit only cools down that one combination, temporarily — no key is ever permanently disabled.

### What the AI is explicitly NOT allowed to do
- **Not diagnose / not name a disease** — every prompt says so; the prescription Diagnosis is human-typed only.
- **Not rewrite the raw transcript** — correction writes a separate field.
- **Not suppress a red flag** — the safety rule is local and overrides the AI.
- **Not prescribe/order** — M16 is information-only with a server-attached disclaimer.
- **Not receive un-needed patient data** — M16's web search only ever gets the doctor's question; its patient context is de-identified and carries no raw transcript.

### Error / fallback behavior
- Any single provider failing → the chain tries the next; a 429 cools that combo down.
- M10 risk: if the AI fails entirely, the case defaults to **Medium** (never Low) and the **red-flag rule still runs**.
- M11 XAI: if the AI fails, a **deterministic reason** is generated so no risk is stored without an explanation.
- Patient-facing errors are a fixed safe sentence + retry — **no provider name, model id, or upstream body ever reaches the patient's screen**.

### Privacy / security considerations (rule #4)
- Free tiers may train on inputs → **synthetic/consented data only** in development; Mistral (which trains on inputs) is disabled by default.
- The browser STT sends audio to Google's cloud — **flagged openly** as a reason real deployment needs local STT.
- Real deployment would need a no-training (paid or local) AI provider and encryption — stated as future work, not claimed as done.

> **Say to a judge:** "Speech recognition, the LLM, decision support, and diagnosis are four different things. We use LLMs to *structure* language — extract, summarize, ask, explain — behind a swappable client with a multi-key fallback so a free-tier outage doesn't take the demo down. The LLM never diagnoses, never rewrites the raw words, and never overrides the safety rule."

## 13. BACKEND & DATABASE

**In beginner terms:**
- **FastAPI** is the web framework — it receives requests from the browser (like "store this utterance" or "give me the risk") and returns JSON. It's fast, modern Python, and auto-generates API docs at `/docs`.
- **The API** is a set of URLs (routes) like `POST /api/visits/{uuid}/utterances`. The frontend calls these; the backend does the work and answers.
- **SQLAlchemy** is the tool that lets Python talk to the database using objects instead of raw SQL — each table is a Python class (`Visit`, `Patient`, `Utterance`…).
- **SQLite** is the database — a single file (`prescreener.db`). Simple, zero-setup, perfect for a demo. The connection URL is config-driven, so switching to **Postgres** later is a one-line change, no code rewrite.
- **Alembic** manages **migrations** — versioned, reviewable schema changes (0001 → 0014). You never edit an old migration or delete the database; each change is a new numbered file. The app auto-migrates on startup.

**The important tables (18 total). The `visit` is the hub everything hangs off:**

| Table | Holds | Notes |
|---|---|---|
| `clinics`, `users` | clinic + staff accounts | roles: doctor/medic/desk/admin (auth stubbed) |
| `patients` | one person (keyed by phone) | name/sex/birth_year + vitals (weight, height, BP, blood sugar) |
| `visits` | ONE pre-screening encounter | **aggregate root**; the status state machine |
| `utterances` | each turn's `raw_text` (immutable) + `corrected_text` | **rule #1 lives here** |
| `case_profiles` | the 10 `summary_fields` (JSON), summary, gaps | derived working state |
| `followup_questions` | each M7 question + the answer utterance | prevents repeats |
| `risk_assessments` | tier + red_flags + rule_overrode | **append-only** |
| `xai_explanations` | the reason for each risk row | 1:1 with risk |
| `reports` | assembled report sections (JSON) | no diagnosis |
| `documents` | generated `.docx`/`.pdf`/FHIR files | derived, regenerable |
| `doctor_reviews`, `feedback` | doctor decisions + M15 signal | append-only |
| `prescriptions` | doctor prescription payload (JSON) | Diagnosis human-typed only |
| `clinical_notes` | recalls + doctor→medic notes | not a chat table |
| `otp_codes` | hashed OTP codes | salted SHA-256, expiring |
| `audit_log` | who did what | append-only accountability |
| `module_events` | per-module run (provider, latency, status) | observability + extensibility keystone |

**How records connect (say this simply):** "A patient has many visits. A visit has many utterances, one profile, many risk assessments, one report, and many documents. Everything points back to the visit. To add a new kind of output later, we add a new child table pointing at `visit` — nothing existing changes."

**How the frontend talks to the backend:** plain `fetch()` calls to `/api/...` returning JSON. Writes that trigger a pipeline stage return the updated slice, so the voice-first frontend doesn't need a second round-trip. Every state-changing call writes an `audit_log` row and (for AI steps) a `module_events` row.

**Where data goes after a patient submits (the one example to memorize):**
```
Patient speaks → POST /api/visits/{uuid}/utterances → utterances.raw_text (immutable)
   → POST /api/visits/{uuid}/intake → M2/M3/M4/M6 → case_profiles
   → follow-up loop → more utterances + followup_questions
   → POST /api/visits/{uuid}/assess → risk_assessments + xai_explanations
   → submit → visit.status='awaiting_review' → shows on MEDIC queue (GET /api/dashboard)
   → medic edits case_profiles + patients vitals → assign → status='awaiting_doctor'
   → DOCTOR reads GET /api/visits/{uuid} → doctor_reviews + prescriptions
   → EHR export → documents (.fhir+json / .pdf)
```

---

## 14. FHIR / EHR / PDF

**What EHR means:** Electronic Health Record — the digital record of a patient's clinical information.

**What FHIR means:** *Fast Healthcare Interoperability Resources* — the HL7 standard that essentially every modern health system speaks. It defines standard "resources" (Patient, Observation, Condition, RiskAssessment…) as JSON objects, and a **document Bundle**: a self-contained file describing one clinical encounter, indexed by a `Composition`.

**Why we use FHIR (this is a classic judge question):**
> "The brief asked for a 'universal EHR download', and the honest answer is: there is no universal EHR *file* — but there **is** HL7 FHIR, the interoperability standard real systems use. So instead of inventing our own format that no one else could read, we export a **FHIR R4 document Bundle**. R4 (not R5) because R4 is the version with real-world deployment behind it."

**What our system converts into FHIR** (built in `services/ehr_export.py`):
- **Patient** (demographics), **Composition** (the index), a **verbatim-transcript section** (the patient's own words, reproduced exactly — rule #1 in the export), **chief complaint / HPI / medications / allergies** narratives, **vitals** as Observations (weight, height, BMI, BP, blood glucose — with real LOINC codes only where we're certain), the **risk tier as a FHIR `RiskAssessment`** (carrying the no-diagnosis disclaimer as a note), and the **doctor's own diagnosis as a `Condition`**.
- **Deliberately excluded:** the AI "suggested condition" — because once ingested by another EHR, the "not a diagnosis" disclaimer wouldn't travel with it, and a model's guess wearing a `Condition` shape is dangerous. The tier is *never* turned into a `Condition`.

**Honest framing (say this exactly):** "It's a **structurally valid, semantically conservative** FHIR R4 document — **not certified, not profiled** against a national implementation guide. Where we weren't certain of a code, we ship the concept as text rather than guess a code, because a wrong code is silently believed."

**How PDF generation works** (`services/ehr_pdf.py`): the PDF is a **second rendering of the same FHIR bundle** — a *pure function of the bundle*, it never reads the database, so the PDF and the FHIR file can't disagree. It uses **fpdf2 + HarfBuzz** specifically because **Bangla needs complex-script shaping** (conjuncts, vowel-sign reordering) — ReportLab can't shape Bengali, and a PDF that mangles the patient's own words would break rule #1. The renderer **refuses rather than emit broken Bangla**, and a font ships in the repo so it renders identically on any machine.

**Machine-readable vs human-readable — the key distinction:**
- **FHIR (`.fhir+json`)** = for *machines* — another EHR system ingests it.
- **PDF** = for *humans* — a doctor or patient reads/prints it.
- Both come from the same source of truth, so they always describe the same encounter.

> **"Why didn't you just store everything in your own database?"** — "We do store it in our database; that's the source of truth. But a record trapped in our SQLite file is useless to the rest of the health system. FHIR is the standard other systems already speak, so exporting FHIR is what makes the record *portable* — a real clinic's EHR could actually receive it. Inventing our own 'universal' format would just be another silo."

---

## 15. SECURITY / PRIVACY / SAFETY

Be scrupulously honest here — separate **implemented** from **future/recommended**. Claiming security you don't have is the fastest way to lose a judge's trust.

### ✅ IMPLEMENTED (in the code today)
- **OTP identity verification** — a real one-time-code flow keyed on the phone number: 6 random digits, **salted SHA-256 hash stored** (never the plaintext), **5-minute expiry**, **single-use**, **constant-time comparison**, **max-attempt lockout**, and **resend throttling**. Two channels behind one seam: `dev` (code to server log) and `textbee` (real SMS). The universal `000000` bypass works **only** in the dev channel (structurally impossible under a production channel).
- **Rule #1 raw-transcript protection** — the raw words are write-once, never editable in any portal, never re-rendered; correction is a separate column. Guarded by tests.
- **Audit / provenance** — an append-only `audit_log` records who did what; even the AI auto-filling a patient's name writes an audit row (`actor_id=NULL`) so it's traceable and never mistaken for human-entered.
- **Secrets hygiene** — API keys live only in `.env` (gitignored); `.env.example` lists names only; keys are **never logged or printed** (even the key-checker reports only presence/length/verdict).
- **No provider leakage** — patient-facing errors are a fixed safe sentence; provider names, model ids, and upstream error bodies never reach the screen.
- **Diagnosis limitation** — the system never diagnoses; the AI suggestion is walled off from the doctor's diagnosis and excluded from the FHIR export.
- **Failure handling** — safe defaults everywhere (risk defaults to Medium not Low; XAI always has a stored reason; red-flag rule survives any AI outage).

### 🔶 FUTURE / RECOMMENDED (be upfront — NOT built)
- **Real authentication/authorization** — staff login is **stubbed** (you pick a seeded user). Real role-based auth is a later phase; the `users` table and roles exist as the seam.
- **Encryption at rest and in transit** — not implemented; required for real deployment (HTTPS, encrypted DB/volume).
- **Local/private STT and a no-training AI provider** — today the browser STT uses Google's cloud and free LLM tiers may train on inputs, which is why **development uses synthetic/consented data only**. Real deployment needs on-device STT and a paid/local model.
- **De-identification at rest, retention policies, consent management UI** — designed for (consent flag exists) but not fully built.

> **Say to a judge:** "I'll be precise: OTP, raw-word protection, audit logging, and secret hygiene are implemented. Real staff authentication and encryption are stubbed or future — the seams exist but they're not done, which is exactly why we only use synthetic data. I'd rather tell you what's real than oversell it."

---

## 16. TESTING

- **What exists:** a large automated **pytest** suite — **~1,196 tests passing, 2 skipped** — across ~100 test files in `backend/tests/`.
- **What's tested (the important areas):**
  - **Rule enforcement:** raw immutability, "answer never edits raw text", the follow-up loop never repeats/loops forever.
  - **Safety:** the red-flag rule forces Critical with **zero misses on the fixed phrase list** (test `TC-R1`), risk defaults to Medium on AI failure, staff can't downgrade a red-flag Critical.
  - **The pipeline:** intake extraction, the 10 bilingual fields, follow-up targeting, completion scoring.
  - **Provider resilience:** the multi-key/multi-model fallback chain, cooldown behavior, and that **no key is ever logged**, all **mocked** (no real network/quota spent).
  - **Portals:** medic queue ordering, doctor history, kiosk voice flow, OTP entry, TTS fallback, the FHIR export structure (every `urn:uuid` resolves), the PDF reads back correctly through its own font map.
  - **Migrations:** each schema change tested fresh + in-place upgrade + downgrade, including DB-level CHECK constraints.
- **How we know it works:** every rule and safety behavior is pinned by a test, so a future change that breaks a rule fails the suite. Manual real-microphone runs were also done (the S25 live run passed: STT judged "very accurate", ~2s latency — subjective, not a WER number).
- **Known testing limitations (say these):** the provider failover is **mock-tested only** (real keys weren't in the suite); there's been **no fresh real-microphone run recently**; and there are **no automated UI screenshot/visual tests** — appearance is verified by measurement, not by rendered image.

> **Say to a judge:** "We treat the four rules as invariants and pin each with a test, so ~1,200 tests act as a safety net against regressions. I'm careful not to sell test *count* as quality — what matters is that the safety behaviors specifically are covered. The gaps are honest: failover is mock-tested and we don't have automated visual tests."

*(Note: test count is a real number from the repo, but don't lead with it as a marketing point — lead with *what* is protected.)*

---

## 17. TECHNOLOGY STACK

Only technologies actually used in the current system.

| Technology | Where used | Why (one line) |
|---|---|---|
| **Python 3** | Backend language | Rich ecosystem for web + AI, runs on Windows & Linux from one venv. |
| **FastAPI** | Web framework / REST API | Fast, modern, auto-generates API docs; async-ready for future streaming. |
| **Uvicorn** | ASGI server | Runs the FastAPI app with one command. |
| **SQLite** | Database | Zero-setup single file; perfect for a demo; config-swappable to Postgres. |
| **SQLAlchemy** | ORM (DB access) | Tables as Python objects; portable across SQLite/Postgres. |
| **Alembic** | DB migrations | Versioned, reviewable schema changes; app auto-migrates at startup. |
| **pydantic-settings** | Config from `.env` | Keys/URLs from environment, nothing hardcoded. |
| **Browser Web Speech API** | Module 1 STT | Live Bangla (`bn-BD`) speech→text, no server, no key (client-side). |
| **OpenAI-compatible client (`openai` lib)** | All LLM calls | One client for Gemini/Groq/Cerebras/OpenRouter — swap by config. |
| **Gemini / Groq / Cerebras / OpenRouter (free tiers)** | The LLM providers | Free, capable, spread across quotas so no single limit is a bottleneck. |
| **edge-tts** | Module 7 audio (TTS) | Natural Microsoft neural Bangla voice (`bn-BD`), free, no key. |
| **espeak-ng** | TTS offline fallback | Fully local/offline Bangla voice when there's no internet. |
| **python-docx** | `.docx` exports | Transcript, summary report, prescription documents. |
| **fpdf2 + uharfbuzz (HarfBuzz)** | EHR PDF | Correct **Bangla shaping** (conjuncts, reordering) that ReportLab can't do. |
| **ddgs (DuckDuckGo)** | M16 assistant search | Free, no-key web search for drug/test info. |
| **httpx** | TextBee OTP SMS calls | HTTP client for the real SMS channel. |
| **pytest** | Testing | ~1,196 tests guarding the rules and pipeline. |
| **Plain HTML/JS + shared CSS** | All three portals | No framework needed; "Teal Medical" design system; fast, simple, portable. |

**Hardware reality (say it):** "No NVIDIA GPU, CPU-only, runs on a 6-core AMD with 12–24 GB RAM, identical on Windows and Arch Linux from one `requirements.txt`. Everything is free or open-source. That's a deliberate constraint — a real Bangladeshi clinic won't have a GPU server."

---

## 18. WHAT WE ACTUALLY ACHIEVED

### ✅ COMPLETED (built and working)
- The **three-portal system** (patient kiosk, medic/triage, doctor) end to end.
- **Voice-first patient intake** — phone/OTP login, spoken questions (TTS) + on-screen text, spoken answers with read-back, review & submit.
- **Modules 1–14** of the pipeline: STT capture, correction, extraction, summary, gap analysis, follow-up loop, completion check, risk assessment, XAI, structured report, EHR database, doctor dashboard.
- **Safety:** the local red-flag rule forcing Critical; append-only risk history; XAI always present.
- **Clinical documentation:** `.docx` transcript/summary/prescription, **HL7 FHIR R4** export, and a **Bangla-shaped PDF**.
- **Real OTP** identity flow; **audit logging**; **multi-provider/multi-key LLM failover**.
- **~1,196 automated tests**; **18-table schema** managed by Alembic.
- **The ASR benchmark study** (18 models, WER/CER, dialect breakdown) — your measured research result.

### 🔶 PARTIALLY COMPLETE
- **Module 15 (feedback/continuous learning):** feedback *capture* is built (ratings/overrides/corrections stored); the **offline retraining pipeline is not**.
- **Voice loop hardening:** the hands-free flow works, but one step (S5 — no-speech re-prompt + permission/visibility recovery) is **not built**, and there's been **no fresh real-microphone run recently**.
- **Provider failover:** implemented and **mock-tested**, but not yet exercised with real keys under real quota pressure.

### 🔮 FUTURE WORK
- **Local/private STT** (`faster-whisper` on CPU) to replace the cloud browser STT.
- **Faculty research track:** quantized on-device STT/TTS and a quantized summary model; a fully voice-driven follow-up conversation.
- **Real authentication + encryption** at rest and in transit.
- **The M15 retraining loop** with regression testing.
- **Postgres + containerized deployment** for a real clinic pilot.

> **⚠ Do not say "production-ready."** The repo itself doesn't claim it. Say **"a working, end-to-end prototype with a clear path to deployment."** That's both accurate and stronger, because it's defensible.

## 19. LIMITATIONS (be honest — it builds credibility)

For each: why it exists, and how we'd improve it.

| Limitation | Why it exists | How we'd improve it |
|---|---|---|
| **Bangla ASR accuracy** — best open model ~47% WER; dialects near-zero | Bangla is low-resource; dialects, Banglish, medical terms, and noise are hard | Fine-tune a local model on clinic dialect/medical data; keep raw words + human verification so errors are caught, not trusted |
| **Cloud dependency for STT** | The browser Web Speech API sends audio to Google | Move to local `faster-whisper` (CPU) — private, offline, deployable |
| **Internet dependency for AI** | LLM steps call cloud APIs (Gemini/Groq/…) | Multi-provider/multi-key failover already softens outages; a local quantized model is the offline path |
| **Free-tier / API limits** | We use free quotas (rule #4, cost) | Redundant keys and buckets today; a paid no-training provider for production |
| **No real authentication/encryption** | Auth is stubbed; encryption not built | Add role-based login + HTTPS + encrypted storage before any real patient data |
| **Synthetic data only** | Free tiers may train on inputs; no ethics clearance for real data | Consent + no-training/local models + de-identification for a real pilot |
| **Model can misextract** | LLM extraction isn't perfect | The medic verifies every field against the raw words; edits are marked `human` and protected |
| **Scalability** | SQLite + single server | Config-swap to Postgres; the API is stateless-ish and containerizable |
| **M15 retraining not built** | Depends on having our own trainable models | Build the offline pipeline once local models exist; the feedback data is already captured |
| **No recent real-mic test / no WER on deployed STT** | Time; the browser STT wasn't formally benchmarked | Run a formal WER/precision-recall study on the deployed pipeline as thesis evidence |

> **Say to a judge:** "The biggest real limitation is Bangla speech recognition itself — and we measured exactly how bad it is rather than hand-waving. Every other limitation has a designed-in mitigation: raw words are preserved, a human verifies, the safety rule is local, and providers fail over. The architecture assumes the transcription is imperfect."

---

## 20. IMPACT

Separate **expected/potential** impact from **measured** results — do not blur them.

### Expected / potential impact (design-level, not yet measured)
- **Elderly and low-literacy patients** can describe symptoms by *speaking*, not typing — the group most excluded by typing-first tools.
- **Bangla / dialect / Banglish speakers** get a tool in their own language, not an English-first one.
- **Faster, richer intake** — symptom collection happens *before* the consultation, so the doctor starts already informed.
- **Less repetitive data entry** and **reduced documentation burden** for the doctor.
- **Better clinical documentation** — structured, explainable, with the patient's own words preserved.
- **Improved doctor preparation** — risk, red flags, and history are visible the moment the patient walks in.
- **Interoperability** — the encounter exports as standard FHIR, so it can feed a real EHR rather than dying in one app.
- **Safety** — danger signs are surfaced, never falsely reassured away.

### Measured results (what we can actually claim)
- **The ASR benchmark** (WER/CER across 18 models, with a dialect breakdown) — a concrete, reproducible measurement and arguably the project's clearest research contribution.
- **The S25 live run** — real-microphone use judged the STT "very accurate" with ~2s latency (**subjective**, not a WER figure).
- **~1,196 passing automated tests** — evidence the built behaviors (especially the safety rules) hold.

> **⚠ Critical framing:** "We have **not** run a clinical trial or measured time-saved with real patients — that would need ethics clearance and a deployment. The impact claims are the *designed-for* benefits; the measured results are the ASR benchmark and the test suite. I'm keeping those two categories separate on purpose."

> **Say to a judge:** "The measured contribution is the benchmark: we quantified how hard Bangla dialect medical ASR is. The clinical impact — faster intake, better documentation for underserved patients — is what the system is *designed* to deliver; proving it needs a real-world pilot, which is future work."

## 21. LIVE DEMO SCRIPT (step by step)

> **Decision confirmed:** the **full AI pipeline will be live** (API keys pasted, uvicorn restarted). Demo all three portals. Use **Chrome** (not Edge — Edge lacks the Bangla voices and had STT quirks). Keep a phone/tablet-friendly quiet spot; clinic noise hurts the mic.

### ⏱ PRE-DEMO CHECKLIST (do this 30–60 min before, calmly)
1. **Paste the API keys** into `backend/.env` (the 9 slots) and save.
2. **Verify keys without spending much quota:**
   `.venv\Scripts\python.exe -m backend.scripts.check_api_keys` — expect "key configured" + PASS per provider. *(It never prints a key.)*
3. **Start the server:**
   `.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --port 8001`
   *(Windows: set `PYTHONIOENCODING=utf-8` first if you see encoding errors.)*
4. **Open Chrome** at `http://localhost:8001` and **hard-reload every portal** (`Ctrl-F5` on `/kiosk.html`, `/medic/`, `/doctor/`) — browsers cache the CSS/JS aggressively and a stale copy can break the medic Edit button.
5. **Allow microphone access** for the site (do this once, in advance).
6. **Seed the queues so the portals aren't empty.** There should be pre-seeded synthetic patients/visits. Make sure at least one case is `awaiting_review` (medic queue) and one is `awaiting_doctor` (doctor queue). *(If the medic queue is empty because a case was forwarded, restore one to `awaiting_review` — you have a note/SQL for this in `current_task.md`.)*
7. **Grant mic + test one sentence** in the kiosk to confirm Bangla STT is working *before* the judges arrive.
8. **Have the backup materials ready** (Section 22): screenshots of each portal, a short screen-recording of a full run, and a pre-completed visit you can open.

### 🎬 THE WALKTHROUGH (aim for 5–7 minutes)

**STEP 0 — One-line intro (say the 30-second pitch).**
- *You explain:* what it is and the problem, in 2 sentences. Then: "Let me show you the patient's experience first."

**STEP 1 — Patient kiosk: identify.**
- *You open:* `/kiosk.html`.
- *You click/do:* enter a phone number → get the OTP (in dev it appears in the server log, or use the demo code) → enter it.
- *Audience sees:* a clean, large, bilingual login. No password.
- *You explain:* "The patient logs in with just a phone number and a one-time code — no typing their history."

**STEP 2 — Patient kiosk: speak.**
- *You do:* let the assistant ask the first question (it's spoken aloud + shown). When the mic opens, **speak a realistic Bangla/Banglish complaint**, e.g. *"তিন দিন ধরে জ্বর আর কাশি, শরীর দুর্বল লাগছে।"*
- *Audience sees:* your words appear live on screen; the system reads your answer back; a follow-up question is spoken.
- *You explain:* "It captured my exact words — and it will never change them. Notice it read my answer back so I can catch a mishearing, then asked a targeted follow-up about what's missing."

**STEP 3 — Patient kiosk: follow-ups + review + submit.**
- *You do:* answer one or two follow-ups by voice, reach the review screen, glance at the structured summary, tap **Confirm & Submit**.
- *Audience sees:* the 10-field structured summary built from free speech; the kiosk resets for the next patient.
- *You explain:* "In the background, AI cleaned the text, extracted the structured fields, checked for danger signs, and scored the urgency — all before the patient ever meets a doctor."

**STEP 4 — Medic portal: triage.**
- *You open:* `/medic/`, log in as the medic.
- *Audience sees:* the queue **ordered by urgency**, with wait-time, red-flag, and completeness chips, plus the floor-load strip.
- *You do:* open the case you just submitted; show the **verbatim panel** next to the **10 AI fields**; correct one field to show the `human` edit; record **vitals** (weight/BP/sugar) → point out the **live BMI**; then **forward to a doctor**.
- *You explain:* "The medic verifies the AI against the patient's real words, adds vitals, and hands the case forward. They can escalate the risk, but they can't hide a red flag — the safety rule wins."

**STEP 5 — Doctor portal: review, prescribe, export.**
- *You open:* `/doctor/`, log in as the doctor; open the forwarded case.
- *Audience sees:* the **safety story first** (tier, red flags, XAI reason), the **patient timeline**, the verbatim words, the structured report.
- *You do:* show the **"AI Suggestion – Not a Diagnosis"** card (and that it's separate from the prescription). Write a short prescription (type the diagnosis yourself). Click **"Accept & Write to EHR"** → download the **FHIR** file and the **PDF**.
- *You explain:* "The doctor sees the explanation and decides — the AI never diagnoses. The output is a standard FHIR record plus a Bangla PDF, so it's interoperable, not locked in our app."

**STEP 6 — Land the close (say the last line of your one-pager).**
- *You explain:* "So: a patient spoke Bangla into a kiosk, and a doctor got an explainable, structured, standards-based record — with the patient's exact words preserved and no diagnosis made by a machine. That's the system."

### The "what to have on screen" cheat
Keep these five tabs open in order: **kiosk → medic → doctor**, plus a tab with the **`/docs` API page** (if a judge asks "is there a real backend?") and a tab with the **ASR benchmark chart** (if a judge asks about accuracy).

---

## 22. DEMO BACKUP PLAN

Assume something *will* glitch. Have these ready and you'll look prepared instead of panicked.

**If the microphone / STT fails (most likely risk):**
- **Switch to Type mode** — it's built in and uses the *same* pipeline. Say: "Voice is primary, but typing is always available as a fallback — same backend path." This turns a failure into a *feature demonstration*.
- Or open a **pre-recorded screen capture** of a successful voice run.

**If the AI/LLM calls fail (quota/network/429):**
- The system fails safe: risk defaults to Medium, the red-flag rule still runs, and a retry appears. Say: "This is the multi-provider failover in action — notice it degrades safely and lets me retry, rather than crashing or showing an error to the patient."
- Fall back to a **pre-completed visit** already in the database — open it in the medic/doctor portal and narrate from there. The pipeline output is already stored, so you can demo the medic/doctor experience without any live AI call.

**If a portal looks broken (usually a stale cache):**
- **`Ctrl-F5`** to hard-reload. This is the #1 fix. Do it calmly.

**If the whole live demo won't cooperate:**
- Switch to **screenshots / the screen-recording** and narrate the flow. You still get full credit for explaining the system clearly.

**What to prepare in advance (make these tonight):**
- [ ] Screenshots of each portal (kiosk speaking, medic queue, doctor case + FHIR/PDF).
- [ ] A 60–90s screen recording of a full successful run.
- [ ] One **pre-completed visit** in each queue so the portals are never empty.
- [ ] The ASR benchmark chart image open in a tab.
- [ ] A downloaded **sample FHIR file + PDF** to show even if export fails live.

**What to skip if you're short on time:** the follow-up loop can be one question instead of several; the M16 drug assistant is optional; the patient history/timeline can be mentioned rather than clicked.

**⚠ What NOT to reveal / dwell on to judges (unless directly asked — then answer honestly):**
- Don't *volunteer* "the API keys were empty until an hour ago" or "failover is only mock-tested." If asked, answer straight (see Section 27). Don't over-explain the internal session notes.
- Don't claim "production-ready", "certified FHIR", "trained our own ASR model", or any WER number for the *deployed* STT. Those aren't true and a sharp judge will catch them.
- Don't show the raw `.env`, and don't paste keys on the projector.

## 23. ONE-PAGE SPEAKING GUIDE (print this)

# 🎤 CAPSTONE SHOWCASE — 1-PAGE SPEAKING GUIDE

**1. Opening:** "Hi, we built a **voice-based medical pre-screening system for Bangladesh**. Before a patient sees the doctor, they *speak* their symptoms in Bangla — and the doctor gets a ready, explainable report."

**2. Problem:** "Clinic visits here are short and rushed. Elderly and low-literacy patients can't easily describe symptoms, especially with typing-first, English-first tools. Details get missed."

**3. Motivation:** "Bangla speech tech is weak — we benchmarked 18 models and the best still got about **half the words wrong** on dialect medical speech. So instead of pretending transcription is perfect, we built around that reality."

**4. Our solution:** "The patient speaks; we keep their exact words untouched; AI cleans and structures them; it asks spoken follow-ups; a safety rule flags danger signs; it scores urgency with a plain-language reason; and it hands the doctor a structured report. It **never diagnoses** — the doctor decides."

**5. How the system works:** "Fifteen modules in a pipeline: speech-to-text → correction → extraction → summary → gap analysis → spoken follow-up loop → risk + red-flag safety → explainable AI → structured report → EHR. Three portals sit on top."

**6. Patient Portal:** "Voice-first kiosk. Phone + OTP login, spoken questions shown on screen, answers read back so a mishearing is caught, then review and submit. Typing is always available as a fallback."

**7. Medic Portal:** "A triage desk. Queue by urgency, verify the AI's fields against the patient's real words, record vitals, forward to a doctor. They can escalate but can't hide a red flag."

**8. Doctor Portal:** "Safety story first — risk, red flags, the explanation. Then history, the patient's words, the report. The doctor writes the diagnosis themselves and exports a standard FHIR record and a PDF."

**9. AI / STT:** "Speech recognition uses the browser's Bangla recognizer today; local private models are our roadmap. LLMs do the language *structuring* — extract, summarize, ask, explain — behind a swappable client with multi-key failover. The LLM never diagnoses and never rewrites the raw words."

**10. Clinical documentation / EHR:** "One encounter is one record in our database, exported as **HL7 FHIR R4** for interoperability plus a Bangla-shaped PDF for humans. Same source of truth, two renderings."

**11. Key features:** "Voice-first Bangla intake · raw words preserved forever · rule-based red-flag safety · explainable risk · three coordinated portals · real OTP · audit logging · FHIR + PDF export · runs on CPU with free tools."

**12. Impact:** "Designed to include elderly/low-literacy/dialect patients, speed up intake, cut documentation, and improve doctor prep — with interoperable output. The *measured* result so far is our ASR benchmark and a 1,200-test safety net."

**13. Limitations:** "Bangla ASR accuracy is the real limit — we measured it. Auth and encryption are stubbed/future; data is synthetic. Every limitation has a designed-in mitigation: raw words preserved, human verification, local safety rule, provider failover."

**14. Future work:** "Local on-device STT (faster-whisper), real auth + encryption, the feedback-driven retraining loop, and a real clinic pilot with Postgres."

**15. Conclusion:** "A patient spoke Bangla into a kiosk, and a doctor got an explainable, structured, standards-based record — exact words preserved, no machine diagnosis. That's a working prototype with a clear path to a real clinic."

> **Golden rules while speaking:** slow down · say "it assists, never diagnoses" often · when unsure, say "that's future work" rather than bluffing · separate *measured* from *designed-for*.

---

## 24. JUDGE Q&A (grouped, with short + detailed answers)

For each: a **Short Answer** (say this fast) and a **Detailed Answer** (for follow-ups), plus **⚠ warnings** where you must not overclaim.

### 🟢 Basic Questions

**Q: What does your project do?**
- **Short:** "A patient speaks their symptoms in Bangla before seeing the doctor; the system transcribes, structures, and risk-scores that, and hands the doctor an explainable pre-screening report."
- **Detailed:** Walk the pipeline briefly (STT → structure → follow-up → risk → report → EHR) and the three portals.

**Q: Who is it for?**
- **Short:** "Patients — especially elderly, low-literacy, dialect speakers — and the medic and doctor who serve them."
- **Detailed:** Patient kiosk, medic triage desk, doctor dashboard; each answers one question (what's wrong / who's next / what do I do).

**Q: What problem does it solve?**
- **Short:** "Rushed consultations and missed information, plus digital tools that exclude non-typists and non-English speakers."
- **Detailed:** Intake moves before the consult; voice-first inclusion; structured, explainable documentation.

### 🔧 Technical Questions

**Q: What's your tech stack?**
- **Short:** "FastAPI backend, SQLite via SQLAlchemy + Alembic, plain HTML/JS portals, browser STT, edge-tts, and a swappable LLM client — all free, CPU-only, Windows + Linux."
- **Detailed:** See Section 17. Emphasize config-driven providers and DB URL.

**Q: Why FastAPI / SQLite / plain HTML instead of React + Postgres?**
- **Short:** "Right-sized for a capstone and a clinic demo: fast to build, zero-setup, runs anywhere. Both are config-swappable to Postgres/React later without a rewrite."
- **Detailed:** SQLite→Postgres is one URL; the API is clean so a React or mobile client can reuse it; plain HTML keeps it dependency-light and portable.

**Q: How is the system extensible?**
- **Short:** "The `visit` is an aggregate root — new outputs are new child tables; new modules are new `module_code` values; providers and DB are config. Adding features rarely touches existing code."
- **Detailed:** `module_events` keyed by module code is the keystone; JSON columns hold evolving shapes so many changes need no migration.

### 🧠 AI Questions

**Q: Where exactly is the AI?**
- **Short:** "LLMs do the *language structuring* — correction, extraction, summary, gap analysis, follow-up questions, risk wording, and the explanation. STT is separate (browser), and the red-flag safety rule is local, not AI."
- **Detailed:** Give the `MODULE_PROVIDERS` map; stress the four layers (STT / LLM / decision support / diagnosis) and that diagnosis is out of scope.

**Q: How is this different from just using ChatGPT?**
- **Short:** "ChatGPT is one chat box. This is a structured clinical *system*: a fixed pipeline with a preserved raw transcript, a local safety rule the AI can't override, explainable risk, three role-based portals, an audited database, and FHIR export — with hard rules the AI must obey."
- **Detailed:** An LLM is *one component* behind a swappable client with failover; the value is the workflow, the safety guarantees, the data model, and interoperability — not the chat.

**Q: Which model do you use and why?**
- **Short:** "Free OpenAI-compatible tiers — Gemini Flash for quality tasks, Flash-Lite for cheap extraction, Groq for the fast live loop — with Cerebras/OpenRouter as fallback. Chosen for being free, capable, and swappable."
- **Detailed:** Load spread across independent quotas; multi-key/multi-model failover; rule #4 means no training-on-inputs providers by default.
- **⚠ Warning:** don't claim you *trained* or *fine-tuned* these models — you use them via API.

### 🗣 Speech Recognition Questions

**Q: What STT do you use?**
- **Short:** "The browser's Web Speech API for Bangla today — fast, accurate for standard Bangla, no server. Local `faster-whisper` is the planned private replacement."
- **Detailed:** Explain the cloud-vs-local trade-off and why raw words are preserved because recognition is imperfect.
- **⚠ Warning:** don't imply you built the recognizer — you use the browser's.

**Q: How accurate is it?**
- **Short:** "For the *deployed* browser STT we don't have a formal WER number — in live use it was judged very accurate for standard Bangla. For *candidate open models* we benchmarked, the best was ~47% WER on dialect medical speech."
- **Detailed:** Give the benchmark; explain WER and why bigger models did worse.
- **⚠ Warning:** never state a made-up WER for the deployed STT.

### 🌐 Bangla / Dialect Questions

**Q: How do you handle dialects and Banglish?**
- **Short:** "We preserve the raw utterance exactly, then normalize in a later AI step — never at capture, because forcing Banglish into clean Bangla loses meaning. The red-flag rule includes Bangla, Banglish, and English phrases."
- **Detailed:** Benchmark showed dialects are near-unsolved; our mitigation is raw preservation + human verification + downstream normalization, and a local fine-tuned model as future work.

**Q: What about medical terms and noise?**
- **Short:** "Both are known weak spots for ASR; that's why the medic verifies fields against the raw words, and why we keep the original audio-derived text untouched."

### 🗄 Backend / Database Questions

**Q: How does data flow after a patient submits?**
- **Short:** Recite the Section 13 flow: utterances → case_profiles → risk/xai → report → medic edits → doctor review → documents, with audit_log throughout.

**Q: Is your data model normalized / does it scale?**
- **Short:** "The `visit` aggregate root with append-only clinical tables and JSON for evolving shapes. SQLite now; the URL is config so Postgres is a one-line switch."

### 🔐 Security Questions

**Q: How do you protect patient data?**
- **Short:** "Implemented: real hashed OTP, raw-word protection, audit logging, secret hygiene, no provider leakage. Future: real auth and encryption — which is why we use synthetic data only for now."
- **Detailed:** Section 15. Be explicit about implemented vs future.
- **⚠ Warning:** don't claim encryption or real auth — they're stubbed/future.

**Q: You send audio to Google — isn't that a privacy problem?**
- **Short:** "Yes, and we flag it openly. That's exactly why development uses only synthetic/consented data and why local STT is the roadmap for real deployment."

### 🏥 EHR / FHIR Questions

**Q: Why FHIR, and why not your own format?**
- **Short:** "There's no universal EHR *file*, but FHIR is the standard real systems speak. Our own format would be another silo; FHIR makes the record portable."
- **Detailed:** R4 document Bundle; structurally valid but not certified/profiled; uncoded text where we're unsure; AI suggestion excluded.
- **⚠ Warning:** say "structurally valid, not certified" — never "certified FHIR".

**Q: Why both FHIR and PDF?**
- **Short:** "FHIR for machines, PDF for humans — same source of truth, two renderings. The PDF is a pure function of the bundle, so they can't disagree."

### 📊 Research / Methodology / Evaluation Questions

**Q: What's your research contribution?**
- **Short:** "An empirical benchmark of Bangla multi-dialect medical ASR — 18 models by WER/CER — showing even the best misses ~47% of words and that bigger models can be worse. That evidence shaped the architecture."
- **Detailed:** Methodology: dialect-labelled medical utterances, WER + CER + dialect breakdown, confusion analysis; the design conclusions that follow.

**Q: How did you evaluate the *system* (not just ASR)?**
- **Short:** "~1,200 automated tests pin the pipeline and the four safety rules; a real-mic live run validated the voice flow. A formal end-to-end WER/precision-recall study is future thesis work."
- **⚠ Warning:** don't present the ASR benchmark as the deployed system's accuracy.

### 🤔 "Why did you choose this?" Questions

**Q: Why voice-only / voice-first?** — "Our target users are elderly and low-literacy — typing excludes them. Speaking is the natural interface; typing stays as a fallback."

**Q: Why not train your own ASR model?** — "We benchmarked the open ones first to know the ceiling. Training a good Bangla dialect medical model needs large labelled datasets and compute we don't have for a capstone — it's the clear future track. For now we use a working recognizer and design for its errors."

**Q: Why free LLM APIs instead of a local model?** — "Cost and capability for a prototype, behind a swappable client so we're never locked in. A local/paid no-training model is the production path — the seam is already there."

**Q: Why keep the raw transcript at all?** — "Because ASR is imperfect and the machine must never be the only record of what a sick person said. It's a safety and accountability decision."

**Q: Why three separate portals instead of one app?** — "Three different jobs with different data needs and safety boundaries. The kiosk must never show a queue or a risk tier; the medic must never prescribe. Separating them enforces least-privilege by design."

### 🔴 Difficult / Trick Questions (rehearse these)

**Q: "So it's basically a ChatGPT wrapper?"**
- "No. An LLM is one component. The contribution is the *system*: a fixed clinical pipeline, a preserved immutable transcript, a *local* safety rule the AI cannot override, explainable risk, three role-based portals, an audited data model, and FHIR interoperability — plus four hard rules the AI is forced to obey. Remove the LLM and swap another in by config; the architecture stands."

**Q: "Can your system diagnose?"**
- "No, by design. It surfaces information and possible condition *categories*, always labelled 'not a diagnosis', and the doctor's diagnosis is human-typed and even excluded from the exported record. Rule #2 is enforced in code, not just policy."

**Q: "What happens with no internet?"**
- "STT and the LLM steps need connectivity today — that's an honest limitation. TTS has an offline espeak fallback, and typing works offline. Local STT and a local model are the roadmap for a fully offline clinic."

**Q: "Your best ASR model gets half the words wrong — how is this usable?"**
- "That's exactly why the architecture doesn't trust the transcript. We preserve raw words, a human medic verifies every field against them, the safety rule is deterministic, and the doctor sees the patient's actual words. The system is designed to be useful *despite* imperfect ASR, not to pretend ASR is solved. And the demo uses the browser recognizer, which handles standard Bangla well."

**Q: "How do I know the AI didn't invent a symptom?"**
- "Because the raw words are stored and shown, the medic verifies each extracted field against them (edits marked 'human'), extraction prompts forbid inventing details, and the demographics auto-fill is audited. If the AI misreads, a human catches it before the doctor trusts it."

**Q: "Why should anyone use this over a paper form or a normal EHR?"**
- "A paper form needs literacy and a person to fill it; a normal EHR is a typing tool for staff. This lets the *patient* contribute by speaking in their own language before the consult, produces structured explainable output, surfaces danger signs, and still exports to a standard EHR via FHIR. It's the front-door that existing EHRs don't have."

**Q: "Is this production-ready?"**
- "No — it's a working end-to-end prototype with a clear deployment path. Auth and encryption are stubbed, data is synthetic, and STT is cloud-based. I'd rather be precise about that than overclaim."

**Q: "What's the single biggest weakness?"**
- "Bangla dialect ASR accuracy — and we measured it rather than guessing. It's a field-wide open problem; our answer is to design so the system stays safe and useful despite it, and to fine-tune a local model as future work."

**Q: "What did *your team* actually build vs. what's off-the-shelf?"**
- "Off-the-shelf: the browser recognizer, the LLM APIs, FastAPI/SQLite. **We built** the entire pipeline and its safety rules, the three coordinated portals and their role boundaries, the data model and migrations, the FHIR/PDF export with correct Bangla shaping, the OTP flow, the provider-failover client, the ~1,200-test suite, and the ASR benchmark study. The intelligence *orchestration and safety* is ours; the raw models are tools."

**Q: "If the LLM is down during grading, does your project fail?"**
- "No — it fails *safe* and I can show it. Risk defaults to Medium, the red-flag rule still runs locally, a retry appears, and I can open a pre-completed visit to demo the medic/doctor experience. The multi-provider failover exists precisely for this."

---

## 25. MOCK VIVA (practice out loud — build from easy to hard)

Have someone read these to you; answer without notes. They escalate.

1. In one sentence, what is your project?
2. Who speaks to the kiosk, and in what language?
3. What are the three portals, and what does each one do?
4. Walk me through what happens from the moment a patient speaks to the moment a doctor reads the report.
5. Where exactly is the AI used? Where is it *not*?
6. What's the difference between the raw transcript and the corrected text — and why keep both?
7. **Why?** Why does it matter that you never edit the raw words?
8. What is a red flag in your system, and what happens when one is detected?
9. **How do you know** the red-flag rule works? What if the AI disagrees?
10. What happens to the risk score if the AI call fails completely?
11. Which STT do you use? Is it a model you trained?
12. **How accurate is your speech recognition?** Give me a number.
13. Explain WER. How can it be over 100%?
14. Why did bigger ASR models do *worse* in your benchmark?
15. What happens with a Sylheti or Barishal dialect speaker?
16. **What happens with no internet?**
17. How is this different from ChatGPT? From a normal EHR?
18. **Can your system diagnose a patient?** Prove it can't.
19. How do you protect patient data? What's implemented vs. future?
20. You send audio to Google — defend that.
21. Why FHIR? Why not just your own database format?
22. Why both a FHIR file and a PDF?
23. How does the medic portal stop the AI from putting words in the patient's mouth?
24. Show me where the data goes after submission — table by table.
25. How would you deploy this in a real hospital tomorrow? What's missing?
26. **What is your actual research contribution?**
27. **What's the biggest weakness of your project?**
28. Which part did your team build versus use off the shelf?
29. If I unplug your internet right now, what still works?
30. Why should a clinic trust a machine with a sick person's words?

> **Scoring yourself:** if you can answer 1–15 smoothly and 16–30 honestly (including saying "that's future work" where true), you're ready. The bolded ones are the ones judges love — over-prepare those.

---

## 26. FINAL "WHAT I MUST KNOW" CHECKLIST

Tick each before you present. If you can't explain it in one breath, review its section.

**The story**
- [ ] Project purpose (voice pre-screening for Bangladesh) — §1
- [ ] The problem it solves — §1
- [ ] What's novel (voice-first · raw preserved · never diagnoses · FHIR) — §1
- [ ] 30-second, 1-minute, 3-minute pitches — §2
- [ ] The four non-negotiable rules — §3

**The machine**
- [ ] The complete workflow, patient → doctor — §5
- [ ] What each module does (esp. M1, M2, M7, M10, M11, M12) — §6
- [ ] Which modules are AI vs local — §6/§12
- [ ] Patient / Medic / Doctor portals — §7–9
- [ ] How data moves between portals (status flow, shared rows) — §10

**The hard parts**
- [ ] Why Bangla ASR is hard; the benchmark (best ~47% WER) — §11
- [ ] WER explained + why it exceeds 100% — §11
- [ ] What STT the demo actually uses (browser) vs future (faster-whisper) — §11
- [ ] The four AI layers; where the AI is/ isn't; failover — §12
- [ ] Database: FastAPI/SQLite/SQLAlchemy/Alembic, `visit` root, 18 tables — §13
- [ ] FHIR (R4 doc bundle, not certified) + PDF + why both — §14

**The honesty**
- [ ] Security: implemented vs future (OTP real; auth/encryption future) — §15
- [ ] Testing: ~1,196 tests, what's covered, what's mock-tested — §16
- [ ] Completed / Partial / Future — §18
- [ ] Limitations + mitigations — §19
- [ ] Measured results vs expected impact — §20

**The performance**
- [ ] The live demo flow, all three portals — §21
- [ ] The backup plan (mic fail → type; AI fail → pre-seeded visit; cache → Ctrl-F5) — §22
- [ ] The one-page speaking guide, rehearsed — §23
- [ ] Judge Q&A + trick questions — §24/§25
- [ ] Mock viva done out loud at least once — §26

**Pre-demo mechanics**
- [ ] Keys pasted + `check_api_keys` PASS
- [ ] Server running on :8001, Chrome, mic allowed
- [ ] All portals hard-reloaded (Ctrl-F5)
- [ ] Each queue has at least one case
- [ ] Backup screenshots / recording / sample FHIR+PDF ready

## 27. ITEMS REQUIRING YOUR CONFIRMATION (fill these in before tomorrow)

These are things the repo can't tell me — verify or fill them so the guide is 100% yours:

1. **The ASR benchmark is your own work** — I've presented it as your measured research contribution (supporting background). Confirm the numbers in `evaluation/` are yours to claim. *(If you have a target/goal WER or a "with fine-tuning we expect X" figure, add it — but only if it's real.)*
2. **Team framing** — I wrote a neutral "we built the orchestration + safety; the models/frameworks are tools" line (Section 24, "what did your team build"). If a judge asks for individual contributions, be ready with names/roles — I deliberately didn't invent any.
3. **Live-demo machine/browser/mic** — confirm you're on **Chrome** (not Edge), mic tested, quiet spot. Fill in the exact phone number + OTP you'll use for the demo login.
4. **Queue seeding** — confirm there's at least one `awaiting_review` case (medic) and one `awaiting_doctor` case (doctor) before you start; restore the accidentally-forwarded case if needed (see `current_task.md`).
5. **Any numbers I should NOT say** — I've avoided stating a WER for the deployed browser STT and avoided "production-ready"/"certified". If your faculty expect a specific accuracy figure, get a real one; don't let anyone push you into inventing it.
6. **Scope of what you'll claim about M15/feedback** — I've marked the retraining loop as *not built*. Confirm you're comfortable saying "feedback is captured; retraining is future work."

---

## 28. QUICK-REFERENCE FACT SHEET (last-minute glance)

| Thing | The answer |
|---|---|
| **What it is** | Voice-based medical pre-screening for Bangladesh; patient speaks → doctor gets an explainable structured report |
| **Modules** | 15 (M5 retired, gap kept) + M16; M1–M14 built, M15 partial, M16 built |
| **STT (now)** | Browser Web Speech API, `bn-BD` (Google cloud) — *not our own model* |
| **STT (future)** | `faster-whisper`, local, CPU, private |
| **AI/LLM** | Gemini Flash / Flash-Lite, Groq, Cerebras/OpenRouter — swappable, multi-key failover |
| **TTS** | edge-tts (Microsoft neural `bn-BD`); espeak offline fallback |
| **Backend** | FastAPI + Uvicorn |
| **DB** | SQLite + SQLAlchemy + Alembic; 18 tables; head 0014; `visit` = aggregate root |
| **Frontends** | Plain HTML/JS; 3 portals: `/kiosk.html`, `/medic/`, `/doctor/` |
| **Safety** | Local red-flag rule forces Critical; AI failure → Medium not Low; staff can't hide a red flag |
| **EHR export** | HL7 FHIR R4 document Bundle (structurally valid, *not certified*) + Bangla PDF (fpdf2 + HarfBuzz) |
| **Identity** | Real OTP (salted SHA-256, expiry, single-use, lockout); dev `000000` bypass |
| **Auth** | Stubbed (future work) |
| **Tests** | ~1,196 passing, 2 skipped |
| **ASR benchmark** | Best open model `bengaliai_regional` = 0.469 WER / 0.243 CER; bigger models worse (WER > 1.0); dialects near-zero |
| **The 4 rules** | 1) never edit raw words · 2) never diagnose · 3) surface red flags · 4) synthetic/consented data only |
| **Run command** | `.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --port 8001` → Chrome `http://localhost:8001` |
| **The one-liner** | "The patient speaks Bangla; the doctor gets an explainable, standards-based record — exact words preserved, no machine diagnosis." |

---

### 🌟 Final word before you walk in
You built a genuinely thoughtful system, and its best quality is **honesty** — it's designed around what Bangla ASR can't do, it never pretends to diagnose, and it keeps the human in charge. Judges reward candidates who know exactly where their system is strong *and* where it isn't. Lead with the working demo, tell the truth about the limits, and let the design speak. You've got this. 🎓










