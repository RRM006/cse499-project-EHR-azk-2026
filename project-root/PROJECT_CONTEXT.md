# PROJECT CONTEXT — Read this first, every session

> **Purpose of this file:** This is the stable reference. It rarely changes.
> If you (Claude, in a new session) are reading this, read it fully before
> touching any code. Then read `CURRENT_TASK.md` for what to do right now,
> and the latest 1-2 entries of `CHATLOG.md` for recent history.

---

## 1. Project Identity

**Title:** AI-Powered Voice-Based Medical Pre-Screening System with Intelligent
Symptom Capture and Clinical Documentation for Bangladesh

**One-line pitch:** A patient speaks naturally in Bangla/Banglish/regional
dialect before seeing a doctor; the system transcribes, extracts clinical
info, asks follow-up questions to fill gaps, assesses risk, and generates a
structured pre-screening report for the doctor's dashboard.

**Course context:** CSE499 capstone project.

---

## 2. Non-Negotiable Rules (do not violate these in any module)

1. **Never modify the patient's exact spoken words during transcription.**
   Normalization/correction happens in *later* pipeline stages, never at the
   STT step itself.
2. **The system never diagnoses.** It narrows the differential and flags
   risk; the doctor decides. Any output implying a diagnosis is a bug.
3. **Emergency detection (Module 5) takes priority over everything else.**
   It must be checked in parallel with / immediately after extraction,
   regardless of what else is running.
4. **Prefer open-source, low-cost, low-resource-device-friendly tools.**
   Free APIs (e.g. OpenRouter) are acceptable for downstream NLP, not as a
   default crutch.
5. **All patient data must be treated as sensitive medical data** —
   encryption at rest/in transit, audit logging, even in early prototypes.
   Don't bolt this on at the end.

---

## 3. System Architecture — 15 Modules

| # | Module | Goal (one line) |
|---|---|---|
| 1 | Speech-to-Text | Convert Bangla/Banglish/dialect voice → raw text, real-time, exact words preserved |
| 2 | Text Processing & Normalization | Clean/standardize raw transcript (spelling, filler removal, sentence boundaries) |
| 3 | Information Extraction | NER for symptoms, body parts, duration, severity, meds, comorbidities |
| 4 | Initial Clinical Summary | Short human-readable chief-complaint summary |
| 5 | Emergency Detection | Real-time red-flag check, runs in parallel, top priority |
| 6 | Missing Information Analysis | Gap checklist vs. expected clinical data points |
| 7 | Follow-up Question Generation | Targeted Bangla/English questions to fill gaps, priority-ranked |
| 8 | Response Processing & Profile Update | Re-run Modules 2-3 on answers, merge into profile, resolve conflicts |
| 9 | Case Completion Check | Completeness score vs. threshold; loop to Module 7 or proceed; max-turn limit |
| 10 | Risk Assessment Engine | Classify Low/Medium/High/Critical via rules + model |
| 11 | Explainable AI (XAI) | Plain-language reasoning trace for every risk classification |
| 12 | Structured Clinical Report | Compile everything into doctor-facing report (PDF + dashboard) |
| 13 | EHR Database | Secure storage: audio, transcripts, profiles, reports, audit logs |
| 14 | Doctor Dashboard | Web UI: report, risk, XAI, alerts, annotations/overrides |
| 15 | Feedback & Continuous Learning | Doctor feedback → retraining pipeline → regression testing |

**Dependency shape (rough):** 1 → 2 → 3 → {4, 5, 6}. 6 → 7 → 8 → 9, looping
9→7 until complete or max turns. Completed profile → 10 → 11 → 12 → 13/14.
15 feeds back into 3/7/10 over time. Modules 13/14 (storage, dashboard) are
infrastructure that most other modules read/write to, so they often need to
exist in skeleton form early, not last.

*(Full per-module detail — example outputs, key requirements — lives in
`docs/full_spec.md`, copied verbatim from the original project brief. This
table is the quick-reference version.)*

---

## 4. Tech Constraints & Candidate Stack

- **STT candidates:** OpenAI Whisper / Faster-Whisper, BanglaSpeech2,
  Wav2Vec2 Bangla fine-tunes.
- **Downstream NLP:** OpenRouter-supported free models acceptable.
- **Must tolerate:** noise, code-switching, regional accents, varying
  speech speed, varying education levels.
- **Must run on:** low-resource devices (clinic kiosk/tablet class hardware)
  — keep this in mind before reaching for a huge model by default.
- **Compliance target:** HIPAA/PDPA-style handling for Module 13 (EHR DB),
  even in prototype form — don't store plaintext patient data "for now."

Final concrete stack choices (frameworks, DB, hosting) belong in
`DECISIONS.md`, not here — this file only states constraints, not choices,
since choices will evolve.

---

## 5. How This Project's Documentation System Works

This repo uses a small set of tracking files so that any Claude Code session
— today or in a month — can pick up exactly where the last one left off.

| File | Updated | Purpose |
|---|---|---|
| `PROJECT_CONTEXT.md` | rarely | This file. Stable architecture/rules reference. |
| `MILESTONE_LOG.md` | per module milestone | Big-picture status of all 15 modules. |
| `CURRENT_TASK.md` | every session | What we're doing *right now*, exact next step. |
| `CHATLOG.md` | end of every session | Running session-by-session decision/build log. |
| `TEST_LOG.md` | whenever tests are run | What was tested, how, results, pass/fail. |
| `DECISIONS.md` | whenever a real choice is made | Architecture Decision Records (ADRs). |
| `CODEBASE_MAP.md` | when structure changes | Folder/file map with one-line descriptions. |

**Session protocol (see `SESSION_PROTOCOL.md` for the full checklist):**
start of session → read context + current task + last chatlog entry →
do the work → end of session → update chatlog + current task + (if
applicable) milestone log / test log / decisions.
