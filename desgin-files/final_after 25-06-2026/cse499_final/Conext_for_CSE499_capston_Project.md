**Project Title   :** AI-Powered Voice-Based Medical Pre-Screening System with Intelligent symptom capture and clinical documentation for Bangladesh

**Overview:** Before a patient meets the doctor, they speak naturally in Bangla, Banglish, or regional dialects to describe their symptoms and medical history. An AI pipeline transcribes the speech, extracts clinically relevant information, asks targeted follow-up questions (spoken aloud and shown on screen) to fill any gaps, and generates a structured pre-screening report — all before the consultation begins.

The doctor receives a ready-to-review report including the patient's symptom profile, risk level with an explainable-AI summary, prominent red-flag indicators, and suggested next steps — reducing documentation burden, cutting consultation time, and ensuring no critical information is missed. All data is securely stored in an EHR-integrated database, and doctor feedback continuously improves the system over time.

> **2026-06-25 design update (ADR-0024):** The standalone Emergency Detection module (old Module 5) and its automatic staff-escalation alert were removed from the flow. The safety responsibility is preserved as a **rule-based red-flag check inside Module 10 (Risk Assessment)**, which routes clearly life-threatening symptoms to the **Critical** tier and shows them prominently to the doctor. The system does **not** perform autonomous emergency triage/escalation. Module numbering keeps a gap at M5.

**How it works**

A patient sits with a voice-enabled tablet or kiosk in the waiting area and speaks naturally — describing symptoms, medical history, current medications, and allergies in Bangla or Banglish. **Interaction is voice-only**: the patient speaks, the system listens (speech-to-text), and any follow-up questions are read aloud (text-to-speech) while also shown on screen; the patient answers by voice. A manual text box exists only as a fallback when the microphone fails. From that conversation, the system builds a complete clinical picture before the doctor walks in: transcribing the speech, extracting medically relevant entities, structuring them into a standardized EHR, surfacing a short list of conditions worth considering, and delivering everything to the doctor's dashboard the moment the patient enters the room.

**Beyond transcription**

This is not a dictation tool. By linking extracted symptoms to a lightweight medical knowledge layer, the system gives the doctor a focused differential before the examination begins — for example, flagging possible tuberculosis and prompting a rule-out of lung cancer when a patient reports persistent cough, weight loss, and night sweats. The model never diagnoses. The AI narrows the search space; the doctor decides.

**The product**

Once the core models are trained/built, the system becomes a deployable clinic product: a Bangla voice interface for patients, a clean web dashboard for doctors, a secure backend API, and a built-in consent and encryption layer. A small clinic should be able to install and use it — not just read about it in a paper. And the Bangla speech and NLP resources built along the way will support future healthcare AI work well beyond this system.

## Project Objective

The goal of this project is to develop a real-time Speech-to-Text (STT) system specifically designed for Bangladeshi patients. The system will accurately capture and transcribe spoken Bangla, regional Bangla dialects, and Bangla-English mixed speech (Banglish) into text without modifying the patient's original words.

The transcribed text will serve as the foundation for an intelligent clinical pre-screening platform that assists healthcare professionals by automatically extracting medical information, assessing risk levels, surfacing red flags, and generating structured clinical reports.

## Core Speech-to-Text Requirements

### R1. Real-Time Processing
* The system must transcribe speech as the patient speaks.
* Minimal latency between speech input and text output.
* Continuous streaming transcription capability.

### R2. High Accuracy
* The displayed text should match the patient's spoken words as closely as possible.
* No unnecessary word replacement or modification.
* Preserve the patient's original expressions whenever possible.

### R3. Bangladesh-Focused Speech Recognition
The ASR (Automatic Speech Recognition) system should support:
* Standard Bangla
* Regional Bangladeshi dialects
* Bangla-English code-switching (Banglish)
* Different accents, speaking speeds, age groups, and educational backgrounds

### R4. Open-Source and Low-Cost Deployment
* Preference for open-source models and tools.
* Capable of running on low-resource devices (CPU-only, no NVIDIA GPU).
* Free APIs may be used where necessary (e.g., Gemini / Groq / OpenRouter free tiers), always behind a swappable interface.

### Technical Notes
* Converting spoken Banglish directly into Bangla script may reduce fidelity. The system should first preserve the exact utterance and perform normalization only in later processing stages.
* Current STT path: **browser Web Speech API** (`bn-BD`, Chrome/Edge) for the quick-start demo; robust local path planned with **faster-whisper** (CPU int8) in Phase 1.
* Potential technologies: OpenAI Whisper / faster-whisper, Wav2Vec2 Bangla models, and free OpenAI-compatible LLMs (Gemini Flash, Groq Llama, OpenRouter) for downstream NLP.

---

## System Architecture and Roadmap

### Module 1: Speech-to-Text
**Goal:** Convert patient voice input into raw text.
Accepts voice input in Bangla, Banglish, or regional dialects. Must tolerate noise, accents, and code-switching. **Patient input is voice-only; a manual text box is a fallback for poor speech quality / mic failure.**
**Key requirements:** dialect-aware recognition, real-time/near-real-time transcription, manual text-input fallback.

### Module 2: Text Processing and Normalization
**Goal:** Clean, standardize, and prepare raw transcribed text for downstream analysis — in a **separate field** (raw is never modified).
Handles spelling correction, Banglish normalization, filler removal, punctuation restoration, and sentence-boundary detection.
**Key requirements:** NLP preprocessing, Bangla-English bilingual handling, medical spelling correction.

### Module 3: Information Extraction
**Goal:** Extract structured clinical data from the normalized text.
Identifies and tags symptoms, affected body parts, duration, severity, frequency, patient age, and pre-existing conditions or medications. This forms the patient profile.
**Key requirements:** medical NER, temporal expression extraction (e.g., "for three days").

### Module 4: Initial Clinical Summary Generation
**Goal:** Generate a concise, human-readable summary of the patient's chief complaint.
**Example output:** *"Patient reports fever and dry cough for 3 days, with mild fatigue. No mention of breathing difficulty or chest pain."*
**Key requirements:** medical text summarization; templated + generative options.

### Module 5: Emergency Detection — RETIRED (ADR-0024)
This standalone module and its automatic staff-escalation alert were **removed** from the system flow on 2026-06-25. The red-flag responsibility now lives inside **Module 10 (Risk Assessment)** as a rule-based check that maps clearly life-threatening symptoms (chest pain, stroke signs, severe breathing difficulty, loss of consciousness) to the **Critical** tier and shows them prominently to the doctor. The system does **not** perform autonomous emergency triage or escalation in this version. Module numbering keeps a gap at M5.

### Module 6: Missing Information Analysis
**Goal:** Identify clinical information gaps needed for a complete profile.
Produces a checklist of confirmed vs. missing data points.
**Example output:** ✓ Fever detected · ✗ Temperature not provided · ✗ Fever duration not specified · ✗ Breathing difficulty not assessed.
**Key requirements:** symptom-completeness logic, clinical checklists, gap-report generation.

### Module 7: Dynamic Follow-up Question Generation
**Goal:** Generate targeted, conversational questions to fill identified gaps.
Questions are generated in Bangla or English, prioritized by clinical importance, and avoid repeating answered items. **Each question is displayed as text AND read aloud via text-to-speech simultaneously; the patient answers by voice only (no keyboard).**
**Example output:** *"Apnar jwor ki gotokal theke? Thermometer diye measure korechen?"* / *"When did your fever start? Have you measured your temperature?"*
**Key requirements:** medical-context question generation, Bangla/English bilingual output, priority ranking, TTS playback + on-screen text, voice-only reply capture.

### Module 8: Response Processing and Profile Update
**Goal:** Analyze patient answers to follow-up questions and update the profile.
Answers go through the same extraction/normalization pipeline (Modules 2–3) and are merged into the profile with conflict resolution.
**Key requirements:** incremental NLP pipeline, profile state management, conflict resolution.

### Module 9: Case Completion Check
**Goal:** Decide whether enough information has been collected.
Scores profile completeness against a threshold; loops back to Module 7 if critical gaps remain; stops after a configurable maximum number of cycles (to avoid patient fatigue).
**Key requirements:** completeness scoring, per-condition thresholds, loop/turn limits.

### Module 10: Risk Assessment Engine
**Goal:** Classify the patient into a risk tier from the complete profile, and run the rule-based red-flag check (absorbed from old Module 5).
Assigns **Low / Medium / High / Critical** using clinical decision rules plus a trained risk model, weighting age, comorbidities, symptom severity, and duration. **Clearly life-threatening red-flag symptoms force a Critical classification and are surfaced prominently.**
**Risk tiers:** Low (likely minor) · Medium (warrants examination, not urgent) · High (needs prompt attention) · Critical (requires immediate intervention / red flag present).
**Key requirements:** risk classification model, clinical rule engine, age/comorbidity weighting, integrated red-flag rule check.

### Module 11: Explainable AI (XAI)
**Goal:** Make the reasoning transparent and auditable.
For every risk assessment, generates a plain-language explanation of contributing symptoms, durations, and risk factors (including any red flag that drove a Critical tier).
**Example output:** *"High risk was assigned due to: fever lasting more than 5 days, reported difficulty breathing, and patient age over 65."*
**Key requirements:** feature attribution (rule-trace / LIME / SHAP), human-readable explanation, dashboard display.

### Module 12: Structured Clinical Report Generation
**Goal:** Compile everything into a formatted pre-screening report for the doctor. **Contains no diagnosis.**
**Report sections:** Patient Profile (age, gender, known conditions) · Chief Complaint · Symptoms with Duration & Severity · **Red Flags (from Module 10, if any)** · Follow-up Questions & Answers · Risk Level & Explanation · Possible Condition Categories (not a diagnosis) · Recommended Next Steps.
**Key requirements:** structured + human-readable output, PDF and dashboard export (python-docx now; PDF behind the format seam).

### Module 13: EHR Database
**Goal:** Securely store all patient data, reports, and interaction history.
Every session (transcripts, extracted data, follow-up exchanges, risk assessments, reports) is stored, linked to patient identifiers and timestamps, supporting retrieval, audits, and longitudinal tracking.
**Key requirements:** secure/compliant design, encryption at rest and in transit, patient identity management, retrieval by ID/date, audit logging.

### Module 14: Doctor Dashboard
**Goal:** A clear, fast interface for doctors to review the pre-screening report.
Displays the structured report, risk level, red flags, and the XAI explanation; shows conversation history; lets doctors validate/override extractions and add annotations; notifies on high/critical cases.
**Key requirements:** web dashboard, role-based access, real-time high/critical notifications, annotation/override tools, mobile-responsive design.

### Module 15: Feedback and Continuous Learning
**Goal:** Use doctor feedback to improve accuracy over time.
Doctors rate report quality, correct extractions, flag missed symptoms, and annotate risk disagreements. Feedback is collected and periodically used to retrain/fine-tune the extraction, risk, and question-generation models (offline, with regression testing before deploying updates).
**Key requirements:** feedback collection UI, dataset management, retraining pipeline, performance monitoring + regression testing.

---

**Expected Outcome**

The final product will be an AI-powered clinical pre-screening assistant capable of understanding Bangladeshi speech, generating accurate medical summaries, surfacing red flags, assessing patient risk, and supporting doctors with structured, explainable, and actionable clinical insights before consultation — while never diagnosing and never replacing the doctor.
