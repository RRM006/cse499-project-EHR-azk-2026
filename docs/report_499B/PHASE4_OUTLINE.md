# CSE499 Capstone Final Report — Phase 4: Report Outline
**Status:** for your confirmation before any chapter text is written.

## Decisions locked from your answers

| Item | Decision |
|---|---|
| Title | **A Voice-Based AI Framework for Medical Pre-Screening of Bangla and Regional Bangladeshi Speech** |
| Scope | **Combined CSE499A + CSE499B** capstone final report |
| Cover semester | Summer, 2026 |
| Letter of Transmittal date | September, 2026 |
| Supervisor | Dr. Mohammad Ashrafuzzaman Khan [AzK], Associate Professor, ECE, NSU |
| Chairman | Dr. Mohammad Abdul Matin [mtn], Professor & Chair, Ph.D. (Newcastle University, UK) |
| Degree wording | Bachelor of Science in Computer Science and Engineering |
| Page setup | **BAETE template literally** — US Letter 8.5×11 in, 1 in margins, Times New Roman 12 pt, justified, 1.5 line spacing, **Arabic page numbers on every page starting at 1 on the cover**, centred footer |
| Headings | H1 18 pt bold centred with a page break before · H2 16 pt · H3 14 pt |
| Captions | Figures: *below*, centred, `Figure N. Caption.`, numbered straight through · Tables: *above*, centred, ALL CAPS, Roman numerals `TABLE I.` |
| Citations | IEEE numeric `[1]` |
| Chapter 4 | Report **only measured evidence**; the deployed pipeline's lack of formal evaluation stated plainly |
| Gantt | Reconstructed from dated project logs, labelled as such, for your review |

---

## Report structure

### FRONT MATTER

| Page | Content | Source |
|---|---|---|
| Cover | NSU logo, "Department of Electrical and Computer Engineering / North South University", "Senior Design Project", the title, 3 students + IDs, advisor block, "Summer, 2026" | `assets/nsu_logo.png`, README, 499A cover |
| Letter of Transmittal | Dated September 2026, to Dr. Mohammad Abdul Matin, subject naming the project, body summarising both semesters' work, 3 signature blocks | 499A transmittal as the model; content updated for 499B |
| Approval | 3 students + IDs + title + supervisor sentence; Supervisor's and Chairman's signature blocks | Template wording + 499A |
| Declaration | Template institutional wording, kept intact; 3 numbered name/signature lines | Template p.5 |
| Acknowledgements | Supervisor, ECE Department; honest, no invented names | 499A acknowledgements as base |
| Abstract | ~250–300 words. Problem → what was built → what was measured → what it means. **No citations, abbreviations spelled out, no symbols** (template rule). Keywords line. | New text from verified facts |
| Table of Contents / List of Figures / List of Tables | Auto-generated | LaTeX |

---

### CHAPTER 1 — INTRODUCTION

**1.1 Background and Motivation** *(~2 pages)*
Bangladesh's physician-to-population ratio and short consultation times; how much of a consultation goes on history-taking; why patients who speak regional dialects or Banglish are poorly served by English-first digital tools; why Bangla is a low-resource language for speech technology.
*Evidence:* 499A Ch.1 · WHO physician-density data [ref 1] · `Conext_for_CSE499_capston_Project.md`.
*Figure:* none. *External references:* 3–5.

**1.2 Purpose and Goal of the Project** *(~1.5 pages)*
The objective in the project's own terms (real-time Bangla/dialect/Banglish STT that never alters the patient's words, feeding a pre-screening platform). Requirements R1–R4. Stated contributions:
(i) a five-dialect Bangla speech benchmark of 12 baseline ASR models and 6 large multimodal audio models;
(ii) a working three-portal pre-screening system built on the finding that transcription is unreliable;
(iii) four safety invariants enforced in code and pinned by tests;
(iv) standards-based clinical output (HL7 FHIR R4 + a Bangla-shaped PDF).
*Evidence:* `Conext_for_CSE499_capston_Project.md` "Project Objective" and R1–R4 · `CLAUDE.md` rules · `evaluation/` · `services/ehr_export.py`.

**1.3 Organization of the Report** *(~0.5 page)* — chapter map.

---

### CHAPTER 2 — RESEARCH LITERATURE REVIEW

**2.1 Existing Research and Limitations** *(~4 pages)*
Thematic review, each theme closing with what it does not solve:
- Multilingual and self-supervised ASR — Whisper, wav2vec 2.0, XLSR, MMS, SeamlessM4T
- Bangla-specific speech resources — Bengali.AI, Common Voice, OOD-Speech, IndicWav2Vec, Vakyansh
- Large multimodal audio language models — Qwen2-Audio, Qwen3-ASR, Voxtral, Phi-4 Multimodal
- Clinical NLP and speech in medicine — BioBERT, ClinicalBERT, BanglaBERT; ASR for medical dictation and EHR
*Evidence:* `docs/submissions/latex/02_related_works.tex` (30 verified `\bibitem`s) · 16 paper reviews in `docs/literature_reviews/ehr_papers/` · 499A Ch.2.

**2.2 Research Gap** *(~1 page)*
Four gaps: no dialect-aware Bangla benchmark on clinical-style speech; systems assume transcription is good enough; no conversational gap-closing loop for Bangla; no low-resource, CPU-only Bangladeshi deployment path.
> ⚠ **Structural note:** the template shows only "2.1". Your accepted CSE499A report used 2.1 + 2.2. I am proposing 2.1 + 2.2 for the same reason. Say the word if you want it collapsed into 2.1 only.

---

### CHAPTER 3 — METHODOLOGY

**3.1 System Design** *(~5 pages)*
- 3.1.1 Design constraints and the four non-negotiable rules
- 3.1.2 Overall architecture — three portals (`/kiosk.html`, `/medic/`, `/doctor/`) over one FastAPI backend, one database, a swappable LLM provider layer
- 3.1.3 The module pipeline M1–M16 and the patient journey, including the retired M5 and why the gap in numbering was kept
- 3.1.4 Role and data-ownership model — the one-directional handover `in_progress → awaiting_review → awaiting_doctor → reviewed`
- 3.1.5 Database design — visit as aggregate root, append-only clinical tables, JSON payload columns, `module_events` for extensibility
*Figures:* **Fig 1** system architecture (new, TikZ) · **Fig 2** patient-journey module flowchart (from `agent_docs/update_system_flowchart.md`, corrected against the built system) · **Fig 3** database schema diagram (new, from `models.py`)
*Tables:* **Table II** the 15+1 modules with implementation status · **Table III** database tables and what each owns
*Evidence:* `backend/app/main.py`, `db/models.py`, `agent_docs/architecture.md`, `agent_docs/portal_roles.md`, `agent_docs/milestone_log.md`.

**3.2 Software Components** *(~3 pages)*
The template's four-column tools table plus prose on why each was chosen, including the hardware constraint (no NVIDIA GPU, CPU-only, Windows + Arch Linux from one `requirements.txt`).
*Table:* **Table I** — Tool | Function | Other similar tools | Why selected (FastAPI, Uvicorn, SQLite, SQLAlchemy, Alembic, pydantic-settings, browser Web Speech API, `openai` client, Gemini/Groq/Cerebras/OpenRouter, edge-tts, espeak-ng, python-docx, fpdf2 + uharfbuzz, ddgs, httpx, pytest, plain HTML/CSS/JS)
*Evidence:* `requirements.txt`, `CAPSTONE_SHOWCASE_MASTER_GUIDE.md` §17, `agent_docs/decisions.md` (69 ADRs), `CLAUDE.md` tech constraints.
> ⚠ The README's stack table (PostgreSQL, React/Next.js, Flutter, BanglaBERT, spaCy, SHAP/LIME) is **not** what was built. Those appear in this chapter only as *alternatives considered*, clearly labelled.

**3.3 Software Implementation** *(~7 pages)*
- 3.3.1 Backend, API surface and configuration
- 3.3.2 Speech input and output — browser Web Speech API (`bn-BD`), the voice-first loop, the `[🎤 Speak] [⌨ Type]` fallback, the TTS seam (browser → edge-tts → espeak-ng)
- 3.3.3 The AI module layer — per-module provider assignment, the fallback chain, per-(bucket, key, model) cooldown
- 3.3.4 The conversational gap-closing loop — M6 gaps → M7 question with an output guard → M8 merge protecting human edits → M9 completeness over the fixed 10 fields
- 3.3.5 Risk assessment and the safety layer — the 5-category local red-flag rule, forced Critical, medium-not-low default on model failure, XAI with a deterministic fallback
- 3.3.6 Identity and privacy — the OTP flow (salted SHA-256, expiry, single-use, constant-time, lockout, throttle, pluggable sender), the append-only audit log, secret hygiene
- 3.3.7 The three portals
- 3.3.8 Clinical documentation and EHR export — `.docx`, HL7 FHIR R4 Bundle, Bangla-shaped PDF via HarfBuzz
*Figures:* **Fig 4** the follow-up loop as a flow · **Fig 5** the LLM provider fallback chain
*Table:* **Table IV** risk tiers and the five red-flag categories
*Evidence:* read directly from `services/*.py`, `api/routes_*.py`, `core/llm_providers.py`, `schemas/profile.py`.

---

### CHAPTER 4 — INVESTIGATION/EXPERIMENT, RESULT, ANALYSIS AND DISCUSSION

**4.1 The multi-dialect Bangla speech corpus** *(~1.5 pages)*
Five varieties (Puran Dhaka, Barishal, Sylheti, Standard Bangla, Indian Bangla); collection via `yt-dlp` from public recordings plus manual uploads; naming convention; 16 kHz mono normalisation and VAD segmentation; the evaluation subset of 50 clips per dialect (250 total); manual reference transcription.
**Stated honestly:** reference transcripts could be matched for **147 of 250 clips**, covering Barishal, Standard Bangla and Indian Bangla only.
*Table:* **Table V** corpus composition
*Evidence:* `notebooks/01_data_download.ipynb`, `notebooks/03_model_comparison.ipynb` cells 8 and 46, 499A Ch.4.

**4.2 Experiment 1 — Baseline ASR benchmark (12 models)** *(~3 pages)*
Setup (Google Colab T4/A100, Hugging Face checkpoints), metrics (WER, CER, BLEU via `jiwer`), full results, the WER > 100 % explanation.
*Table:* **Table VI** WER/CER/BLEU for all 12 models · *Figure:* **Fig 6** WER comparison bar chart

**4.3 Experiment 2 — Larger multimodal audio LLMs (6 models)** *(~2 pages)*
Qwen2-Audio (direct and via-English), Qwen3-ASR-1.7B, Voxtral-Mini scored; **Phi-4 Multimodal and Qwen2.5-Omni produced no usable output and are reported as failures, not as scores**.
*Table:* **Table VII** larger-model results against the best baseline

**4.4 Dialect-level analysis** *(~1.5 pages)*
Per-dialect WER for the three scored categories; Barishal degradation against Standard Bangla; the near-zero exact-sentence accuracy at the WER < 0.3 threshold; the explicit statement that Puran Dhaka and Sylheti carry **no** error rate.
*Table:* **Table VIII** per-dialect WER · *Figure:* **Fig 7** per-dialect WER chart (new, from raw CSV)

**4.5 Verification of the implemented system** *(~2.5 pages)*
Clearly framed as **software verification, not clinical evaluation**:
- the automated suite (1196 passed, 2 skipped, ~100 files) and specifically what the safety tests pin
- the Session-25 human real-microphone run — TC-V1/V2/V3/F2/R1 all passed, **qualitative only** ("very accurate", ≈2 s latency, no WER recorded)
- what is explicitly *not* measured: WER of the deployed browser STT, extraction precision/recall, risk-tier accuracy, latency distribution, real-key provider failover, any user study
*Table:* **Table IX** verification summary — what was tested, by what method, and what it does and does not prove
*Evidence:* `agent_docs/test_log.md`, `current_task.md`, `milestone_log.md`.

**4.6 Discussion** *(~2 pages)*
Why "bigger is not better" for low-resource Bangla; how a ~47 % WER ceiling forced the architecture (preserve raw words, structure in separate steps, close gaps by conversation, keep a human in the loop, keep the safety rule local and deterministic); what the verification evidence supports and what it cannot.
*Figures:* **Fig 8–11** the four portal screenshots (kiosk conversation, patient summary, medic triage queue, doctor case view with the FHIR/PDF actions)

---

### CHAPTER 5 — IMPACTS OF THE PROJECT

**5.1 Societal, health, safety, legal and cultural** *(~2.5 pages)* — access for elderly, low-literacy and dialect-speaking patients; documentation burden; safety posture (never diagnoses, never falsely reassures); legal position under the emerging Bangladesh data-protection framework; cultural fit of a Bangla-first bilingual interface. Expected impact kept strictly separate from measured results.
**5.2 Environment and sustainability** *(~1.5 pages)* — inference-only evaluation, no training runs, CPU-only deployment target, free-tier compute, paperless records, UN SDG 3 and SDG 10.
*Evidence:* 499A Ch.5 · `Sustainability_and_Environmental_Effects_CSE499B.tex` · `Ethical_and_professional_responsibility_499A.pdf`.

---

### CHAPTER 6 — PROJECT PLANNING AND BUDGET

**6.1 Project Planning** *(~1.5 pages)* — a Gantt chart covering **March 2026 – September 2026**, both semesters:
CSE499A (Mar–Apr): project selection, Phase 1 corpus, Phase 2 baseline benchmark, Phase 3 large-model benchmark, Phase 4 fine-tuning methodology study, Phase 5 chatbot study, report.
CSE499B (Jun–Aug, dates from the project logs): 18–25 Jun architecture and Phase-0 demo · 3–7 Jul the twenty-step system build · 9–12 Jul redesign, bilingual portals, OTP, **live real-mic run 12 Jul** · 8–13 Aug voice-first loop and TTS hardening · 13–15 Aug staff-portal roles, FHIR/PDF export, schema 0013–0014 · 19 Aug final demo hardening · Sept report.
*Figure:* **Fig 12** Gantt chart (new, TikZ), captioned as reconstructed from the project development log
*Evidence:* `agent_docs/changelog.md` session dates, `test_log.md` dated entries.

**6.2 Project Budget** *(~1 page)* — itemised, expected total **BDT 0**: Colab free tier, Hugging Face open checkpoints, public audio, Google Drive free tier, GitHub free tier, free LLM API tiers, open-source software, the students' own hardware.
*Table:* **Table X** budget
> ⚠ **Needs your confirmation** — was anything paid for (API credits, TextBee SMS, domain, hosting)?

---

### CHAPTER 7 — COMPLEX ENGINEERING PROBLEMS AND ACTIVITIES

**7.1 CEP** — P1–P7 table, updated from the 499A version to cover the implemented system (K3–K8 mapping; conflicting requirements now including accuracy vs. latency, privacy vs. cloud AI, safety recall vs. false alarms; depth of analysis across 18 benchmarked models and 69 recorded design decisions; stakeholders; interdependence of the 15-module chain).
**7.2 CEA** — A1–A5 table, similarly updated.
*Tables:* **Table XI**, **Table XII**
> ⚠ The template says these tables must be **discussed with the supervisor**. Tell me if Dr. Khan has given specific wording.

---

### CHAPTER 8 — CONCLUSIONS

**8.1 Summary** *(~1 page)*
**8.2 Limitations** *(~1.5 pages)* — Bangla ASR ceiling; incomplete dialect coverage in the benchmark; cloud dependency for both STT and the AI layer; no formal evaluation of the deployed pipeline; authentication stubbed and no encryption; synthetic data only; provider failover mock-tested only; no microphone run since Session 41; voice-loop step S5 not built; M15 retraining not built; SQLite single-server scale.
**8.3 Future Improvement** *(~1.5 pages)* — local `faster-whisper` STT; the faculty research track (quantized on-device STT/TTS, quantized summary model, fully voice-driven follow-up); LoRA fine-tuning of a mid-size Bangla ASR model; real authentication and encryption; the M15 retraining and regression loop; PostgreSQL and containerised deployment; a formal WER and precision/recall study; a supervised clinic pilot.

---

### REFERENCES
IEEE numeric. Base: the 19 entries already used and verified in the CSE499A report plus relevant entries from `02_related_works.tex`. New entries needed and to be verified before use: HL7 FHIR R4, W3C Web Speech API, FastAPI, SQLite, SQLAlchemy/Alembic, `jiwer`, BLEU (Papineni et al.), HarfBuzz, Groq/Gemini model documentation, WHO Bangladesh health-workforce data.
**No reference will be added without checking it resolves to a real, correct source.**

---

## FIGURE PLAN

| Fig | Caption (draft) | Chapter | Source | Status |
|---|---|---|---|---|
| 1 | System architecture of the pre-screening platform. | 3.1.2 | New TikZ from `main.py` + `portal_roles.md` | to build |
| 2 | Patient journey through the module pipeline. | 3.1.3 | `agent_docs/update_system_flowchart.md` TikZ, corrected | to adapt |
| 3 | Database schema of the pre-screening system. | 3.1.5 | New TikZ from `db/models.py` | to build |
| 4 | The conversational gap-closing loop (M6–M9). | 3.3.4 | New TikZ | to build |
| 5 | LLM provider fallback chain. | 3.3.3 | New TikZ from `llm_providers.py` | to build |
| 6 | Word Error Rate of the evaluated ASR models. | 4.2 | `CSE499_poster_kit_2/assets/stt_wer_poster.png` (verified against CSVs) | exists |
| 7 | Word Error Rate by dialect for the best models. | 4.4 | New chart from `evaluation_scores.csv` | to build |
| 8 | Patient kiosk during the follow-up conversation. | 4.6 | `assets/patient_conversation.png` | exists, viewed |
| 9 | Bilingual patient summary before submission. | 4.6 | `assets/patient_summary_bn.png` / `_en.png` | exists |
| 10 | Medic triage queue and case verification screen. | 4.6 | `assets/medic_triage_queue.png` | exists, viewed |
| 11 | Doctor portal case view with EHR export actions. | 4.6 | `assets/doctor_safety_xai.png` | exists, viewed |
| 12 | Gantt chart of CSE499A and CSE499B execution. | 6.1 | New TikZ from the project logs | to build |

*(A FHIR-output figure from `assets/ehr_fhir_output.png` is available if Chapter 3.3.8 needs it — I will include it only if it earns the space.)*

## TABLE PLAN

| Table | Caption (draft) | Chapter | Source |
|---|---|---|---|
| I | Software tools and components used in the project. | 3.2 | `requirements.txt`, ADRs |
| II | Modules of the system and their implementation status. | 3.1.3 | `milestone_log.md` verified against source |
| III | Database tables and the data each one owns. | 3.1.5 | `db/models.py` |
| IV | Risk tiers and the rule-based red-flag categories. | 3.3.5 | `services/red_flags.py`, `risk.py` |
| V | Composition of the multi-dialect Bangla speech corpus. | 4.1 | notebooks + 499A |
| VI | Baseline ASR results on the multi-dialect corpus. | 4.2 | `baseline_vs_bigger_comparison.csv` |
| VII | Larger multimodal audio model results. | 4.3 | same |
| VIII | Word Error Rate by dialect for the leading models. | 4.4 | recomputed from `evaluation_scores.csv` |
| IX | Verification activities and what each does and does not establish. | 4.5 | `test_log.md` |
| X | Project budget. | 6.2 | 499A budget, updated |
| XI | Complex Engineering Problem (CEP) attributes. | 7.1 | 499A CEP, updated |
| XII | Complex Engineering Activity (CEA) attributes. | 7.2 | 499A CEA, updated |

## LaTeX PROJECT LAYOUT

```
report/
├── main.tex                 % class, BAETE page setup, fonts, caption/numbering rules
├── preamble.tex             % packages + template-exact styling
├── frontmatter/
│   ├── cover.tex  transmittal.tex  approval.tex  declaration.tex
│   └── acknowledgements.tex  abstract.tex
├── chapters/
│   └── ch1_introduction.tex … ch8_conclusions.tex
├── figures/                 % PNGs + generated PDFs
├── tikz/                    % architecture.tex, flowchart.tex, schema.tex, gantt.tex, …
├── tables/                  % the long CEP/CEA tables
└── references.bib           % IEEE, verified entries only
```

---

## ⚠ STILL OPEN (defaults I will use unless you say otherwise)

| # | Item | My default |
|---|---|---|
| 1 | CSE499B budget | BDT 0, itemised as in 499A |
| 2 | CEP/CEA supervisor wording | Update the 499A tables; note in the report that they were prepared in consultation with the advisor **only if you confirm that is true** |
| 3 | Puran Dhaka / Sylheti WER | Report the honest limitation. If you can re-run the notebook matching, tell me and I will rewrite §4.4 |
| 4 | Corpus size | Cite "approximately 4.7 hours across five regional varieties" as stated in the CSE499A report; the underlying `dataset_log.csv` is on Google Drive, not in this folder |
| 5 | Chapter 2 sub-structure | 2.1 + 2.2, as in your accepted 499A report |
| 6 | Appendix | **None** — the template has no appendix section |
| 7 | Acknowledgements | Supervisor + ECE Department only, unless you name others |
