# CSE499B Capstone Final Report — Phase 1–3 Audit
**Prepared:** 1 September 2026
**Sources inspected:** `Capstone Final Report Template_BAETE_v1-1.docx` (unpacked + rendered to PDF and read page by page) and the full `C:\Workspace\NSU\cse499-project-EHR-azk-2026` project folder.

> **Nothing in this document is assumed.** Every claim carries the file it came from. Where evidence is missing or conflicting, it is marked as such and turned into a question at the end.

---

## PROGRESS TRACKER

| Step | Status |
|---|---|
| BAETE template inspected | **DONE** (unzipped OOXML + rendered to PDF, 22 pages, read visually) |
| Template requirements extracted | **DONE** |
| Template checklist completed | **DONE** (§2 below) |
| Complete project folder inspected | **DONE** (backend, 3 frontends, DB, migrations, ~100 test files, agent_docs, evaluation CSVs, notebooks, prior submissions, poster kit) |
| Project architecture understood | **DONE** |
| Project features verified | **DONE** (verified against source code, not only docs) |
| Technical details verified | **DONE** |
| Implemented / future status verified | **DONE** (§4) |
| Missing information identified | **DONE** (§6) |
| Uncertain information identified | **DONE** (§6) |
| Issues found reported | **DONE** (§5) |
| Questions asked | **DONE** (§7) |
| **User answers received** | **BLOCKED — waiting on you** |
| Report outline | NOT STARTED (blocked) |
| Chapters 1–8, figures, tables, references | NOT STARTED (blocked) |
| LaTeX project / compile / PDF inspection | NOT STARTED (blocked) |

---

## 1. WHAT THE BAETE TEMPLATE ACTUALLY REQUIRES (verified from the file, not assumed)

### 1.1 Page and typography rules (read from `word/styles.xml` `docDefaults` and `sectPr`)

| Setting | Value in the template | Evidence |
|---|---|---|
| Page size | **US Letter, 8.5 in × 11 in** (not A4) | `sectPr` w:pgSz 12240×15840 twips |
| Margins | **1 in** all four sides | `w:pgMar` 1440 twips each |
| Header / footer distance | 0.5 in | `w:header`/`w:footer` 720 twips |
| Body font | **Times New Roman 12 pt** | `docDefaults/rPrDefault` `sz=24` half-points |
| Body paragraph | **Justified**, **1.5 line spacing**, 10 pt space after | `pPrDefault`: `jc=both`, `line=360 auto`, `after=200` |
| Heading 1 (chapter + front-matter titles) | 18 pt bold, **centred**, **forced page break before**, keep-with-next | `Heading1` style: `sz=36`, `b`, `jc=center`, `pageBreakBefore` |
| Heading 2 | 16 pt | `Heading2` `sz=32` |
| Heading 3 | 14 pt | `Heading3` `sz=28` |
| Page numbers | **Centred in the footer, plain Arabic, starting at 1 on the cover page** — the template has **no roman-numeral front matter** | `footer1.xml` contains a centred `PAGE` field; the rendered PDF shows "1" on the cover and "8" on the Table of Contents |
| Table of Contents | Word field `TOC \h \u \z \t "Heading 1,1,Heading 2,2,Heading 3,3,"` — **includes Heading 1/2/3 and lists the front matter too** | `document.xml` `instrText` |
| Figure captions | **Below** the figure, centred, single-spaced, Times 12 pt, format `Figure N. Caption.` — **numbered straight through the document, not per chapter** | Rendered p.17: "Figure 1. A sample Gantt chart." |
| Table captions | **Above** the table, centred, **ALL CAPS**, **Roman numerals**: `TABLE I. A SAMPLE …` | Rendered pp.14, 18, 19 |
| Citation style | **IEEE numeric** `[1]`, `[2]` | Ch. 1 instruction text: "The references can be cited in IEEE format"; the reference list is unnumbered plain paragraphs in the template but IEEE-formatted |
| Cover page | NSU logo image, department + university, "Senior Design Project", project title, up to 4 student names + IDs, faculty advisor block, semester + year | Rendered p.1 |

### 1.2 Required document structure (exact order in the template)

1. **Cover page** (logo, department, university, "Senior Design Project", title, students + IDs, advisor, semester/year)
2. **LETTER OF TRANSMITTAL** — dated; addressed to the ECE Department Chairman; subject line naming the project; body; signature blocks for every student
3. **APPROVAL** — sentence naming every student + ID + project title + supervisor; **Supervisor's Signature** block; **Chairman's Signature** block
4. **DECLARATION** — fixed institutional wording + numbered student name/signature lines
5. **ACKNOWLEDGEMENTS**
6. **ABSTRACT** — project title repeated, then the abstract. Template explicitly forbids: references, abbreviations, symbols, special characters, footnotes, maths in the abstract
7. **TABLE OF CONTENTS**
8. **LIST OF FIGURES**
9. **LIST OF TABLES**
10. **Chapter 1 Introduction** — 1.1 Background and Motivation · 1.2 Purpose and Goal of the Project · 1.3 Organization of the Report
11. **Chapter 2 Research Literature Review** — 2.1 Existing Research and Limitations
12. **Chapter 3 Methodology** — 3.1 System Design · 3.2 Hardware and/or Software Components (with the software/hardware tools table: *Tool | Functions | Other similar Tools | Why selected this tool*) · 3.3 Hardware and/or Software Implementation
13. **Chapter 4 Investigation/Experiment, Result, Analysis and Discussion**
14. **Chapter 5 Impacts of the Project** — 5.1 societal, health, safety, legal and cultural · 5.2 environment and sustainability
15. **Chapter 6 Project Planning and Budget** — Gantt and/or RACI chart + itemised budget
16. **Chapter 7 Complex Engineering Problems and Activities** — 7.1 CEP table (P1–P7) · 7.2 CEA table (A1–A5)
17. **Chapter 8 Conclusions** — 8.1 Summary · 8.2 Limitations · 8.3 Future Improvement
18. **References**

**No appendix section exists in the template.** Adding one is optional and would be a deviation to agree with you first.

---

## 2. REPORT TEMPLATE CHECKLIST

Legend — **P** = can be filled from project evidence · **U** = you must supply · **P+U** = partly available, needs your confirmation.

| # | Requirement | Where in template | Information needed | Source |
|---|---|---|---|---|
| 1 | NSU logo on cover | p.1 | Logo image | **P** — `CSE499_poster_kit_2/assets/nsu_logo.png` |
| 2 | Project title | cover, transmittal, approval, abstract | The final agreed title | **U** — four different titles exist in the project (see §5, Issue 1) |
| 3 | Student names + IDs | cover, transmittal, approval, declaration | 3 students | **P** — README + 499A report: Rafiur Rahman Mashrafi (2221971042), M. G. Rabbi Hossen (2222516042), Israt Zaman Srity (2211084042) |
| 4 | Faculty advisor block | cover, approval, acknowledgements | Name, designation, dept | **P** — Dr. Mohammad Ashrafuzzaman Khan [AzK], Associate Professor, ECE (499A report cover + approval page) |
| 5 | Semester and year | cover | e.g. "Summer, 2026" | **U** — 499A was Spring 2026; 499B semester not recorded anywhere |
| 6 | Letter of Transmittal date | p.2 | Month, Year | **U** |
| 7 | Chairman name/designation | transmittal + approval | Current ECE Chairman | **P+U** — 499A used Dr. Mohammad Abdul Matin [mtn], Professor & Chair, Ph.D. (Newcastle University, UK). Needs confirmation it is unchanged |
| 8 | Declaration wording | p.5 | Institutional text | **P** — template wording used verbatim (institutional text, per your rules) |
| 9 | Acknowledgements | p.6 | Who to thank | **P+U** — 499A version exists; ask whether to add anyone for 499B |
| 10 | Abstract | p.7 | 1 page, no citations/abbreviations | **P** — `docs/submissions/Abstract.docx` exists but describes the **proposal**, not the built system; must be rewritten for 499B |
| 11 | Table of Contents | p.8 | auto | **P** — LaTeX generates |
| 12 | List of Figures | p.10 | auto | **P** |
| 13 | List of Tables | p.11 | auto | **P** |
| 14 | Ch.1 Background & Motivation | p.12 | Bangladesh healthcare context with references | **P** — 499A Ch.1 + WHO physician-density reference [1] |
| 15 | Ch.1 Purpose and Goal | p.12 | Objectives + contributions | **P** — `Conext_for_CSE499_capston_Project.md` "Project Objective" + R1–R4 |
| 16 | Ch.1 Organization of Report | p.12 | Chapter map | **P** |
| 17 | Ch.2 Existing Research + Limitations | p.13 | Literature review + gap statement | **P** — 16 paper reviews in `docs/literature_reviews/ehr_papers/` + 30-entry bibliography in `docs/submissions/latex/02_related_works.tex` |
| 18 | Ch.3 System Design (diagrams) | p.14 | Architecture, flow, DB, UML | **P** — TikZ flowchart source in `agent_docs/update_system_flowchart.md`; DB schema from `backend/app/db/models.py` (18 tables); 3-portal architecture from `agent_docs/portal_roles.md` |
| 19 | Ch.3 tools table | p.14 | Tool / Function / Alternatives / Why | **P** — `CAPSTONE_SHOWCASE_MASTER_GUIDE.md` §17 + `requirements.txt` + `agent_docs/decisions.md` (69 ADRs) |
| 20 | Ch.3 Implementation | p.14 | Modules, code, DB, portals | **P** — verified in the source tree |
| 21 | Ch.4 Experiments and Results | p.15 | Measured results + figures/tables | **P (partly)** — the ASR benchmark is real and reproducible; **there is NO measured result for the built system** (see §5, Issue 3) |
| 22 | Ch.5 Societal/health/safety/legal/cultural | p.16 | Impact discussion | **P** — 499A Ch.5 + `docs/submissions/Ethical_and_professional_responsibility_499A.pdf` |
| 23 | Ch.5 Environment & sustainability | p.16 | Impact discussion | **P** — `docs/submissions/latex/Sustainability_and_Environmental_Effects_CSE499B.tex` |
| 24 | Ch.6 Gantt / RACI | p.17 | 499B timeline | **P+U** — a 499A Gantt exists (Mar–Apr 2026); the **499B timeline is not recorded anywhere** |
| 25 | Ch.6 Budget | p.17 | Itemised cost | **P+U** — 499A budget was BDT 0; 499B added paid/free API keys, TextBee SMS — actual spend unknown |
| 26 | Ch.7 CEP table P1–P7 | p.18 | Attribute mapping | **P+U** — a full 499A CEP table exists; template says to **discuss the table with the supervisor** |
| 27 | Ch.7 CEA table A1–A5 | p.19 | Attribute mapping | **P+U** — same as above |
| 28 | Ch.8 Summary | p.20 | | **P** |
| 29 | Ch.8 Limitations | p.20 | | **P** — `CAPSTONE_SHOWCASE_MASTER_GUIDE.md` §19 is an honest limitations table |
| 30 | Ch.8 Future Improvement | p.20 | | **P** — §18 "Future work" + `agent_docs/faculty_future_features.md` |
| 31 | References (IEEE) | p.21 | Real, verifiable | **P** — 19 verified entries in the 499A report + 30 in `02_related_works.tex`; new ones needed for FHIR/FastAPI/etc. |

---

## 3. PROJECT UNDERSTANDING REPORT

### 3.1 Identity

| Item | Value | Evidence |
|---|---|---|
| System name (in the running product) | **Niramoy Pre-Screening** | UI header in `CSE499_poster_kit_2/assets/*.png`; `presentations/Niramoy_CSE499_Final_Presentation.pptx` |
| Repository | `project-root/voice-medical-prescreener` | folder |
| Course | CSE499A (Spring 2026) → CSE499B | 499A report cover |
| Supervisor | Dr. Mohammad Ashrafuzzaman Khan [AzK], Associate Professor, ECE | 499A cover + approval page |
| Team | Rafiur Rahman Mashrafi 2221971042 · M. G. Rabbi Hossen 2222516042 · Israt Zaman Srity 2211084042 | README.md + 499A report |

### 3.2 Problem, motivation, objective

- **Problem:** Bangladeshi outpatient consultations are very short; a large share of that time goes on manual history-taking. Patients often describe symptoms in regional dialects or Banglish, so information is lost or incomplete. (`docs/.../Final_report_submission_499A.pdf` Ch.1; WHO physician-density figure cited there.)
- **Objective (verbatim source):** build a real-time STT system for Bangladeshi patients that captures Bangla, regional dialects and Banglish **without modifying the patient's original words**, and use that text as the base for a clinical pre-screening platform that extracts medical information, assesses risk, surfaces red flags and generates structured reports. (`Conext_for_CSE499_capston_Project.md`, "Project Objective".)
- **Stated requirements R1–R4:** real-time processing · high fidelity to the spoken words · Bangladesh-focused recognition (standard Bangla, dialects, Banglish) · open-source and low-cost, CPU-only, free APIs behind a swappable interface. (same file.)

### 3.3 The four non-negotiable project rules (these are the design spine and should appear in the report)

1. The raw transcript is **never** changed; correction is a separate stored field.
2. The system **never diagnoses**; it narrows the search space for the doctor.
3. Red flags are surfaced; the system never falsely reassures.
4. Patient data is sensitive → **synthetic or consented data only** during development.

Evidence: `CLAUDE.md` "NON-NEGOTIABLE RULES"; enforced in code (`services/red_flags.py`, `schemas/followup.py` raw-text guard) and pinned by tests (`tests/test_raw_immutable.py`, `tests/test_answer_raw_text_guard.py`).

### 3.4 System architecture as actually built

**Three web portals over one FastAPI backend** (`backend/app/main.py`, verified):

| Entry point | Served from | Role |
|---|---|---|
| `/kiosk.html` | `frontend/kiosk.html` + `kiosk.js` (149 KB) | Patient kiosk — phone + OTP login, voice conversation, review, submit |
| `/medic/` | `frontend_medic/index.html` | Triage desk — urgency-ordered queue, vitals, field verification, referral |
| `/doctor/` | `frontend_doctor/index.html` | Clinician workspace — risk/red flags/XAI, history, prescription, EHR export |
| `/legacy/` | `frontend_legacy/` | The Phase-0 transcript demo, kept isolated |
| `/shared` | `frontend_shared/` | `shared.css`, `shared.js`, `staff.js`, `tts.js`, `motion.css` |

**Module pipeline (15 modules, M5 retired, M16 added):** M1 STT → M2 correction → M3 extraction → M4 summary → M6 gap analysis → (M7 question → M8 profile update → M9 completeness) loop → M10 risk + local red-flag rule → M11 XAI → M12 report → M13 EHR DB → M14 doctor dashboard → M15 feedback capture. M16 is a doctor-side drug/test information assistant.
Evidence: `agent_docs/milestone_log.md` module table; each module maps to a real file in `backend/app/services/`.

**Backend stack (verified from code, not from README):**
Python + **FastAPI** + Uvicorn · **SQLite** via **SQLAlchemy** + **Alembic** (head `0014`, **18 tables**) · pydantic-settings · `openai` client pointed at OpenAI-compatible providers · python-docx · fpdf2 + uharfbuzz · edge-tts / espeak-ng · ddgs · httpx · pytest.

**18 tables** (counted in `backend/app/db/models.py`): clinics, users, patients, visits, case_profiles, followup_questions, risk_assessments, xai_explanations, reports, doctor_reviews, feedback, audit_log, otp_codes, clinical_notes, module_events, utterances, documents, prescriptions.

**AI providers:** Gemini Flash / Flash-Lite, Groq, Cerebras, Mistral (disabled by rule #4), OpenRouter — one OpenAI-compatible client, a per-module assignment map and a fallback chain `Gemini k1→k2→k3 → Groq k1→k2→k3 → Cerebras → OpenRouter k1→k2→k3`, with per-(bucket, key, model) cooldown. Verified in `backend/app/core/llm_providers.py` and `services/llm_client.py`.

**Speech:** M1 STT is the **browser Web Speech API** (`bn-BD`) — not a local model. TTS is browser `speechSynthesis` with a **server-side edge-tts / espeak-ng fallback** behind `GET /api/tts`. Verified in `CLAUDE.md` "CURRENT STACK", `backend/app/api/routes_tts.py`, `backend/app/services/tts/`.

**Safety mechanism (the strongest engineering story in the project):** `services/red_flags.py` holds 5 rule-based categories (chest pain, severe breathing difficulty, stroke signs, loss of consciousness, severe uncontrolled bleeding), each with Bangla, Banglish/Roman and English trigger phrases, matched case-insensitively as substrings over both raw and corrected patient text. A hit **forces the Critical tier regardless of what the LLM says**, and a failed LLM call defaults to **medium**, never low. Read directly from the source.

**Clinical output:** `.docx` transcript / summary / prescription (python-docx), an **HL7 FHIR R4 document Bundle** (`services/ehr_export.py`, 36 KB), and a **Bangla-shaped PDF** rendered from that same bundle via fpdf2 + HarfBuzz (`services/ehr_pdf.py`) because ReportLab cannot shape Bengali.

**Security actually implemented:** real OTP (6 digits, salted SHA-256 stored, 5-minute expiry, single-use, constant-time compare, attempt lockout, resend throttle, pluggable `dev` / `textbee` sender) · append-only `audit_log` including AI auto-fills · secrets only in gitignored `.env`, never logged · fixed safe error text so no provider/model name leaks to a patient.
**Not implemented:** real staff authentication (stubbed — you pick a seeded user), encryption at rest or in transit, de-identification, retention policy, consent-management UI.

### 3.5 Measured results that genuinely exist

**ASR benchmark (CSE499A, reproducible from `evaluation/`):**

| Model | WER | CER | BLEU |
|---|---|---|---|
| **bengaliai_regional (best)** | **0.4694** | 0.2429 | 0.2730 |
| bengaliai_whisper | 0.5055 | 0.3075 | 0.2527 |
| mms | 0.5568 | 0.2687 | 0.2003 |
| vakyansh_bn | 0.6142 | 0.2950 | 0.1810 |
| wav2vec2_xlsr_cv_bn | 0.6808 | 0.4365 | 0.1668 |
| wav2vec2_xlsr_300m_bn | 0.7023 | 0.3894 | 0.1191 |
| seamlessm4t | 0.7679 | 0.5210 | 0.1233 |
| whisper_large_v3 | 0.9097 | 0.5827 | 0.0646 |
| wav2vec2_xlsr53_bn | 1.0023 | 0.8245 | 0.0002 |
| whisper_v3_turbo | 1.0264 | 0.7850 | 0.0117 |
| whisper_medium | 1.1680 | 1.2299 | 0.0002 |
| whisper_small | 1.9580 | 1.7060 | 0.0000 |

Larger multimodal models (1.7B–7B): qwen2_audio_via_english 1.0039 · qwen2_audio_direct 1.0837 · qwen3_asr 1.1339 · voxtral_mini 1.3627. **phi4_multimodal and qwen25_omni produced no usable output at all** (their rows in `baseline_vs_bigger_comparison.csv` are empty).

I recomputed these means from the raw per-clip file `evaluation/baseline_models/evaluation_scores.csv` and they match the published CSV exactly.

**Test suite:** 1196 passed, 2 skipped, 0 failed, ~100 test files (`agent_docs/current_task.md`, `milestone_log.md`).
**Live run:** the Session-25 human real-microphone run passed TC-V1/V2/V3/F2/R1 on Windows 11 — but it is explicitly recorded as **qualitative** ("very accurate", ≈2 s latency), with no WER number (`agent_docs/test_log.md`, 2026-07-12 entry).

### 3.6 Figures and screenshots that already exist and are usable

| File | Shows | Verified by me |
|---|---|---|
| `CSE499_poster_kit_2/assets/patient_conversation.png` | Kiosk voice conversation, bilingual questions, countdown, Speak/Type switch | Yes — opened and viewed |
| `CSE499_poster_kit_2/assets/medic_triage_queue.png` | Medic queue with urgency chips, Intake & Vitals, risk, AI-suggestion card with disclaimer, handover check, 10 verification fields | Yes |
| `CSE499_poster_kit_2/assets/doctor_safety_xai.png` | Doctor case view, 10 fields, follow-up & handover, EHR (FHIR) / EHR (PDF) / prescription buttons | Yes |
| `CSE499_poster_kit_2/assets/patient_summary_bn.png`, `patient_summary_en.png` | Bilingual patient summary | staged |
| `CSE499_poster_kit_2/assets/ehr_fhir_output.png` | FHIR export | staged |
| `CSE499_poster_kit_2/assets/stt_wer_poster.png` | Publication-quality WER bar chart for all 16 scored models | Yes — numbers match the CSVs |
| `evaluation/baseline_models/evaluation_charts.png`, `evaluation/bigger_models/evaluation_charts_bigger.png` | WER/CER charts | staged |
| `evaluation/*/confusion_matrices/*.png` | 16 per-model dialect heatmaps | listed |
| `agent_docs/update_system_flowchart.md` | TikZ source of the patient-journey flowchart — compiles standalone | read |
| `assets/nsu_logo.png` | Cover-page logo | staged |

---

## 4. IMPLEMENTATION STATUS (strictly separated)

### IMPLEMENTED + TESTED (automated tests exist)
M1 STT capture (browser Web Speech API, `bn-BD`) · M2 correction · M3 10-field bilingual extraction · M4 summary · M6 gap analysis · M7 follow-up question generation with an output guard · M8 profile update with human-edit protection · M9 completeness scoring (local) · M10 risk tiers + the local red-flag rule · M11 XAI with deterministic fallback · M12 structured report · M13 EHR database (18 tables, Alembic 0014, audit log) · M14 doctor dashboard · M16 drug/test assistant · OTP identity flow · `.docx` exports · HL7 FHIR R4 export · Bangla-shaped EHR PDF · multi-provider/multi-key LLM failover · three portals, bilingual EN/BN.

### TESTED BUT ONLY WITH MOCKS
Provider failover and the multi-key chain — all 31 S44 tests use mocked providers; **no real API key has ever been exercised through the chain** (`agent_docs/current_task.md`).

### EVALUATED (real measurement exists)
Only the **CSE499A ASR benchmark**. Nothing else in the project has a measured accuracy, precision, recall, latency or WER number.

### PARTIALLY IMPLEMENTED
- **M15 Feedback & Continuous Learning** — feedback *capture* is built and stored; the retraining/regression pipeline is **not**. Status 🟨 in `milestone_log.md`.
- **Voice loop** — works end to end, but **Step S5** (no-speech re-prompt, empty-submit guard, 120 s answer cap, permission/visibility recovery) is verified **absent** and pinned by a test.
- **Phase 4 (LoRA fine-tuning of Qwen3-ASR-1.7B)** — README calls it "In Progress"; it is a **methodology study only**. No fine-tuning was executed, no fine-tuned checkpoint exists in the repo.

### PLANNED / FUTURE WORK (must never be written as done)
Local `faster-whisper` STT · real authentication + RBAC · encryption at rest and in transit · PostgreSQL + containerised deployment · the M15 retraining loop · the three faculty research requirements (quantized on-device STT/TTS, quantized summary model, fully voice-driven follow-up) · JWT/PDPA consent flow · MLflow tracking.

### NOT IMPLEMENTED (despite appearing in the README)
**PostgreSQL, React/Next.js, Flutter/PWA, BanglaBERT, spaCy, WhisperX in the running system, SHAP/LIME, HF PEFT/LoRA, row-level encryption.** See §5 Issue 2.

---

## 5. ISSUES FOUND

### Issue 1 — Four different project titles exist
- README.md: *"CSE499: EHR-Based Pre-Consultation Medical Documentation System (AI Medical Pre-Screening Assistant)"*
- CSE499A report cover: *"EHR-Based Pre-Consultation Medical Documentation System"* + subtitle *"A Bangla, dialect-aware voice-to-EHR pipeline for pre-consultation patient triage"*
- `docs/submissions/Abstract.docx`: *"A Voice-Based AI Framework for Medical Pre-Screening of Bangla and Regional Bangladeshi Speech with Intelligent Symptom Capture, Risk Assessment, Clinical Documentation, and EHR Integration"*
- `Conext_for_CSE499_capston_Project.md`: *"AI-Powered Voice-Based Medical Pre-Screening System with Intelligent symptom capture and clinical documentation for Bangladesh"*
- Product brand in the UI and the final presentation: **Niramoy**

**Why it matters:** the title appears on the cover, in the Letter of Transmittal, in the Approval page and above the Abstract. It must be one string. **This is a question for you.**

### Issue 2 — The README's technology table does not describe the built system
`README.md` lists PostgreSQL, React/Next.js, Flutter/PWA, BanglaBERT, spaCy, WhisperX, SHAP/LIME and HF PEFT/LoRA as the stack. The code uses **SQLite, plain HTML/JS, browser Web Speech API and hosted LLM APIs**; there is no BanglaBERT, no spaCy, no SHAP/LIME and no PEFT anywhere in `requirements.txt` or the source tree. `agent_docs/` and `CAPSTONE_SHOWCASE_MASTER_GUIDE.md` §17 describe the real stack correctly.
**How I will handle it:** the report will describe **the implemented stack** and, where useful, name the originally-proposed components as *design alternatives considered / future path*. The README is out of date; I am not treating it as the source of truth. Flagging so you can fix the README separately if you want.

### Issue 3 — The headline WER excludes the two hardest dialects, and the project's own text overstates the dialect finding
Measured directly from `evaluation/baseline_models/evaluation_scores.csv`:

| Dialect | Clips evaluated | Clips with a WER value |
|---|---|---|
| barishal | 50 | **47** |
| normal_bangla | 50 | **50** (49 for three models) |
| indian_bangla | 50 | **50** |
| **puran_dhaka** | 50 | **0** |
| **sylheti** | 50 | **0** |

So **WER = 46.94% is a mean over 147 clips from three categories only**. Notebook `03_model_comparison.ipynb` cell 46 reports that 244 reference `.txt` files *do exist* on Drive (puran_dhaka 44, sylheti 50), yet cell 8 matched only 147 — the reference filenames evidently do not line up with the cleaned `.wav` filenames for those two dialects.

Consequently the claim in `CAPSTONE_SHOWCASE_MASTER_GUIDE.md` — *"On the dialects specifically (Sylheti, Puran Dhaka, Barishal), exact-sentence accuracy was essentially zero"* — is only supported for **Barishal**. For Puran Dhaka and Sylheti, **nothing was computed at all**; `dialect_accuracy.csv` shows `total = 0` for both.

**Honest way to write it:** "WER and CER were computed on the 147 clips for which reference transcripts could be matched, covering Barishal, Standard Bangla and Indian Bangla. Reference transcripts for Puran Dhaka and Sylheti were prepared but could not be matched to the processed audio files, so no error rate is reported for those two varieties — a limitation of this evaluation." Then Barishal alone carries the dialect-degradation claim (best model: 0.594 WER on Barishal vs 0.468 on Standard Bangla).
**Option:** if you can re-run the matching, this is fixable and would materially strengthen Chapter 4.

### Issue 4 — Two of the six large models produced nothing, and this is silently absent
`phi4_multimodal` and `qwen25_omni` have empty WER/CER/BLEU in every results file. The 499A abstract states "two failed to produce usable output at all", which is correct — the report must say the same and not present six scored models.

### Issue 5 — README Phase 4 says "In Progress"; no fine-tuning was ever run
There is no fine-tuned checkpoint, no training run and no training log in the repo. Phase 4 must be written as **planned methodology / future work**.

### Issue 6 — No measured evaluation of the built system
There is no WER on the deployed browser STT, no extraction precision/recall, no risk-tier accuracy on a labelled set, no latency measurement, and no user study. The project's own `test_log.md` names this as the standing gap ("formal WER / precision-recall on a labeled set is still to be logged as thesis evidence"). Chapter 4 will therefore report: the ASR benchmark (measured), the test suite (measured behaviour), and the S25 live run (qualitative, explicitly labelled as such). **See question Q6.**

### Issue 7 — Provider failover has never run with a real key
Nine credential slots in `backend/.env` are empty; all failover tests are mocked. Must be stated in Limitations.

### Issue 8 — No recent real-microphone run
No microphone run since Session 41; Sessions 42–45 touched no speech code. Stated honestly in Limitations.

### Issue 9 — Template page numbering differs from what you did in 499A
The BAETE template numbers **every** page in Arabic starting at 1 (the cover is page 1). Your CSE499A report used **roman numerals for front matter** and Arabic from Chapter 1. Both are defensible; the template is literal. **See question Q4.**

### Issue 10 — The template is US Letter, but your 499A report was A4
The template's `sectPr` is 8.5 × 11 in. Your prior LaTeX submissions use `a4paper`. **See question Q4.**

---

## 6. GAP ANALYSIS

### A. INFORMATION AVAILABLE (no action needed from you)
- Student names, IDs, emails; supervisor name and designation; department; university
- Full system architecture, module list, database schema, API routes, service files
- The four project rules and their code-level enforcement
- Complete implemented/partial/planned status per module (`milestone_log.md`, verified against source)
- ASR benchmark results, per-model and per-dialect, reproducible from raw CSVs
- Test-suite size and what it covers
- 6 real UI screenshots + WER charts + 16 confusion matrices + NSU logo
- TikZ flowchart source for the patient journey
- An honest limitations list and future-work list
- ~49 verified IEEE references across the 499A report and `02_related_works.tex`
- 499A Chapter 5 (impacts), Chapter 6 (Gantt + budget), Chapter 7 (CEP + CEA) as a base to update
- Prior institutional wording for Transmittal / Approval / Declaration / Acknowledgements

### B. INFORMATION MISSING (cannot be derived from the files)
1. The **final project title** for the 499B cover
2. The **semester and year** for the cover ("Summer, 2026"? "Fall, 2026"?)
3. The **Letter of Transmittal date**
4. The **CSE499B project timeline** for the Chapter 6 Gantt chart (499A's chart covers Mar–Apr 2026 only; the build sessions run to 19 Aug 2026 but no phase/milestone dates are recorded)
5. The **CSE499B budget** — were the Gemini/Groq/OpenRouter/Cerebras keys all free tier? Did TextBee SMS cost anything? Any other spend?
6. Whether the **CEP/CEA tables were discussed with and approved by the supervisor** (the template explicitly instructs this)
7. Whether **Puran Dhaka and Sylheti WER can be recovered** by fixing the filename matching
8. Whether **any measurement of the built system** was made that is not in `test_log.md`
9. Whether a **demo video / additional screenshots** exist that should be figures

### C. INFORMATION UNCERTAIN (needs your confirmation)
1. **Chairman** — is Dr. Mohammad Abdul Matin still Professor & Chair of ECE? The BAETE template still names Dr. Rajesh Palit
2. **Degree wording** — 499A used "Bachelor of Science in Computer Science and Engineering"; the template says "Bachelors of Science in Engineering". Which does your department require?
3. **Dataset size** — "approximately 4.7 hours, five regional varieties" appears in the 499A report and README, but I could **not** find the underlying `dataset_log.csv` in this folder (it lives in Google Drive). I can cite the 499A report for it, or you can supply the log
4. **Corpus provenance** — `01_data_download.ipynb` uses `yt-dlp` plus manual Drive uploads. The report needs one honest sentence about where the audio came from and the copyright/ethics position on it
5. **Page size and numbering** — see Issues 9 and 10
6. Whether the report should be written for **CSE499B alone** or as a **combined 499A+499B final report** (the template is "Capstone Final Report", and much of Chapters 2/4 comes from 499A)

### D. INFORMATION YOU MUST PROVIDE
Everything in B, plus the confirmations in C. These are asked as numbered questions in §7.

---

## 7. QUESTIONS

### PROJECT INFORMATION NEEDED
1. **What is the exact final project title?** (See Issue 1 for the four candidates. If you want, I recommend the 499A title for continuity: *"EHR-Based Pre-Consultation Medical Documentation System"*, optionally with the Niramoy product name mentioned in Chapter 1.)
2. **Is this report for CSE499B only, or the combined 499A + 499B capstone?** This decides whether Chapter 4 is "the built system" or "the ASR benchmark **and** the built system".
3. **CSE499B timeline for the Gantt chart** — rough start/end dates for the main phases and any demo dates to the supervisor. Even month-level is enough.
4. **CSE499B budget** — any money spent at all (API credits, SMS, hosting, hardware)? If everything stayed free-tier, I will write BDT 0 with an itemised justification like 499A.
5. **Have the CEP and CEA tables been discussed with Dr. Khan?** The template requires this. If yes, any changes he asked for?

### TECHNICAL INFORMATION NEEDED
6. **Chapter 4 is the weak point.** The built system has no measured result. Which do you want?
   - (a) Report only what exists — ASR benchmark + test-suite evidence + the qualitative S25 live run, and state plainly that no formal evaluation of the deployed pipeline was performed. **Safest and fully honest.**
   - (b) You run a small measurement before I write (e.g. 20–30 recorded utterances → WER of the browser STT, and/or extraction precision/recall on those cases), and I write it up as a real experiment. **Strongest report, needs your time.**
   - (c) Something else you have in mind.
7. **Can the Puran Dhaka / Sylheti reference transcripts be re-matched?** The `.txt` files exist on Drive (44 + 50) but did not match the `.wav` names. If you can fix and re-run cell 38, Chapter 4 gains a proper five-dialect breakdown. If not, I write the honest limitation.
8. **Dataset details** — can you give me the `dataset_log.csv` (or the numbers): total clips, total duration, per-dialect counts, and where the audio came from (YouTube channels? recorded by the team? both)? Needed for the Chapter 4 dataset table and for the ethics paragraph.
9. **Any extra screenshots or a demo recording** you want included as figures?

### PERSONAL / UNIVERSITY INFORMATION NEEDED
10. **Semester and year for the cover page** (e.g. "Summer, 2026").
11. **Letter of Transmittal date** (month + year).
12. **Chairman's name, designation and qualification** as of this submission — confirm Dr. Mohammad Abdul Matin [mtn], Professor & Chair, Ph.D. (Newcastle University, UK), or give me the current one.
13. **Degree wording** — "Bachelor of Science in Computer Science and Engineering" (your 499A) or "Bachelors of Science in Engineering" (the template)?
14. **Acknowledgements** — anyone besides Dr. Khan and the ECE Department you want thanked?

### REPORT / FORMATTING INFORMATION NEEDED
15. **Page size:** follow the template literally (**US Letter**) or use **A4** as in your 499A submission?
16. **Page numbering:** follow the template literally (**Arabic from the cover page**) or use your 499A style (**roman front matter, Arabic from Chapter 1**)?
17. **Appendix:** the template has none. Do you want one (e.g. API route list, database schema, sample FHIR bundle, test summary), or keep strictly to the template?

---

## 8. WHAT I HAVE **NOT** DONE YET
No report text has been written. No LaTeX project has been created. No compilation has been attempted. No figure has been generated. Nothing is marked done that is not done.
