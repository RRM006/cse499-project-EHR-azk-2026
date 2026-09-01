# CSE499 Final Report — Complete Information Matrix
**Second-pass evidence sweep completed 1 September 2026.** Every row states exactly what is missing, not "some information is missing".

Legend for the last column: **A** = derived from the project, no question needed · **B** = writable as methodology/design/limitation without any new fact · **C** = genuinely needs your answer.

---

## FRONT MATTER

| Section | Needs | Available + evidence | Missing | Safe to write | Cat |
|---|---|---|---|---|---|
| Cover | Logo, dept, university, title, 3 students + IDs, advisor, semester | All confirmed. Logo `CSE499_poster_kit_2/assets/nsu_logo.png`; students from `README.md` + 499A cover; advisor Dr. Mohammad Ashrafuzzaman Khan [AzK], Associate Professor; "Summer, 2026" (your answer) | — | Yes, in full | A |
| Letter of Transmittal | Date, Chairman, subject, body, 3 signature blocks | Dated September 2026; Dr. Mohammad Abdul Matin [mtn], Professor & Chair (your confirmation); body content from both semesters' verified work | — | Yes | A |
| Approval | Names + IDs + title + supervisor sentence; two signature blocks | Confirmed, incl. Ph.D. (Newcastle University, UK) for the Chairman and "Bachelor of Science in Computer Science and Engineering" | — | Yes | A |
| Declaration | Institutional wording + signature lines | Template wording kept verbatim (institutional text) | — | Yes | A |
| Acknowledgements | Who is thanked | 499A version: supervisor + ECE Department. No other names appear anywhere in the project | Nobody else named | Yes — mirror 499A, invent no names | A |
| Abstract | ~1 page, no citations/abbreviations/symbols | All facts verified (corpus, benchmark, built system, honest scope) | — | Yes | A |
| TOC / LoF / LoT | Auto | LaTeX | — | Yes | A |

---

## CHAPTER 1 — INTRODUCTION

| Section | Needs | Available + evidence | Missing | Safe to write | Cat |
|---|---|---|---|---|---|
| 1.1 Background and Motivation | Healthcare context, dialect problem, low-resource Bangla | 499A Ch.1; **verified externally:** World Bank/WHO series SH.MED.PHYS.ZS gives 0.637 physicians per 1,000 people for Bangladesh (2019) — I will phrase it as "fewer than one physician per 1,000 people", which every source supports | An exact 2026 figure | Yes | A |
| 1.2 Purpose and Goal | Objective, requirements, contributions | Objective verbatim from `Conext_for_CSE499_capston_Project.md`; requirements R1–R4 same file; contributions verified against code and `evaluation/` | — | Yes | A |
| 1.3 Organization | Chapter map | — | — | Yes | A |

---

## CHAPTER 2 — LITERATURE REVIEW

| Section | Needs | Available + evidence | Missing | Safe to write | Cat |
|---|---|---|---|---|---|
| 2.1 Existing Research | Recent related work | 30 verified `\bibitem`s in `docs/submissions/latex/02_related_works.tex`; 19 in the 499A reference list; 16 paper-review documents in `docs/literature_reviews/ehr_papers/` | — | Yes; I will use only the subset that supports a claim actually made | A |
| 2.2 Limitations of Existing Work / Research Gap | Gap statement | Derived from the reviewed literature + this project's own benchmark result | — | Yes | A/B |

---

## CHAPTER 3 — METHODOLOGY

| Section | Needs | Available + evidence | Missing | Safe to write | Cat |
|---|---|---|---|---|---|
| 3.1 System Design | Architecture, module flow, DB, roles | **Verified in code:** `backend/app/main.py` (5 mount points, 15 routers); 18 tables in `db/models.py`; 15 route modules; 41 service files; 14 Alembic migrations (0001–0014); role model in `agent_docs/portal_roles.md`; module board in `milestone_log.md`; TikZ flow in `agent_docs/update_system_flowchart.md` | Nothing | Yes, in full | A |
| 3.2 Software Components | Template's 4-column tools table | `requirements.txt` (verified deps), `CAPSTONE_SHOWCASE_MASTER_GUIDE.md` §17, **69 ADRs** in `decisions.md` giving the "why selected" and the rejected alternatives | Nothing | Yes | A |
| 3.3 Implementation | Backend, speech, AI layer, follow-up loop, safety, OTP, portals, exports | **All verified in code:** full API surface enumerated (44 endpoints across 15 routers); provider map `M2,M4,M10,M10C,M11,M12,M16→Gemini Flash · M3,M8→Flash-Lite · M6,M7→Groq`, `FALLBACK_ORDER = [Groq, Cerebras, Mistral, OpenRouter]`; follow-up loop constants `followup_min_questions=4`, `followup_max_questions=5`, `completeness_threshold=0.7`, `followup_resume_max_questions=8`; voice knobs `countdown 3000 ms`, `tts_guard 400 ms`, `no_speech 10000 ms`, `max_answer 120000 ms`, `review_timeout 60000 ms`, `phone_confirm 10000 ms`; 5 red-flag categories in `red_flags.py`; OTP properties in `otp/service.py`; 4 export kinds `("transcript","summary_report","ehr_bundle","ehr_pdf")`; 11 FHIR R4 resource types and 10 bilingual Composition sections in `ehr_export.py` | Nothing | Yes, in full | A |

---

## CHAPTER 4 — EXPERIMENT, RESULT, ANALYSIS AND DISCUSSION

**This is the chapter the honesty rules bite hardest on. Four distinct evidence classes, never merged.**

| Section | Needs | Available + evidence | Missing | Safe to write | Cat |
|---|---|---|---|---|---|
| 4.1 Corpus | Composition, provenance, preprocessing | **Fully documented in the 499A report Table 4.1:** 10 source recordings, 284.1 min ≈ **4.7 h**, per-dialect split (pd 1 file / 35.7 min · br 2 / 33.8 · sy 2 / 31.7 · nb 3 / 87.0 · ib 2 / 95.9), 8 male / 2 female, ages 20s–50s, public sources via `yt-dlp`, 16 kHz mono, RMS-normalised, WhisperX VAD into 10–15 s clips, ≈1,100 segments; evaluation subset 50 clips × 5 dialects = **250** | Nothing further needed | Yes | A |
| 4.2 Baseline ASR benchmark | Method + results, 12 models | Recomputed by me from `evaluation/baseline_models/evaluation_scores.csv` (3,000 rows) and matches `baseline_vs_bigger_comparison.csv` exactly. Best: BengaliAI Regional WER 0.4694 / CER 0.2429 / BLEU 0.2730 | Nothing | Yes | A |
| 4.3 Larger multimodal models | Method + results, 6 models | 4 scored (qwen2_audio_via_english 1.0039 · qwen2_audio_direct 1.0837 · qwen3_asr 1.1339 · voxtral_mini 1.3627); **phi4_multimodal and qwen25_omni have empty metric cells in every results file** | Nothing | Yes — reported as **failures to produce usable output**, never as scores | A |
| 4.4 Dialect analysis | Per-dialect breakdown | Measured: WER exists for **147 of 250** clips — barishal 47, normal_bangla 50, indian_bangla 50. **puran_dhaka 0/50 and sylheti 0/50.** Notebook cell 46 shows 244 reference `.txt` files do exist on Drive (pd 44, sy 50) but cell 8 matched only 147 → filename mismatch | Valid WER for Puran Dhaka and Sylheti | Yes — report the three measured varieties and state the matching failure explicitly as a limitation. **No value will be invented for pd/sy** | A + optional C (only if you re-run the matching) |
| 4.5 Verification of the built system | What was tested and by what method | Last recorded full-suite run **1196 passed, 2 skipped, 0 failed** (Session 45, 19 Aug 2026, `current_task.md` + `milestone_log.md`); **89 test files** counted directly in `backend/tests/`; per-file coverage tables in `test_log.md`; Session-25 human real-mic run TC-V1/V2/V3/F2/R1 all passed, recorded as **qualitative** ("very accurate", ≈2 s latency, explicitly no WER) | A re-run I could execute myself (the suite runs on your machine, not here) | Yes — framed as **software verification, not clinical evaluation**, with the suite figure attributed to its recorded run | A |
| 4.6 What was not measured | Honest gap statement | `test_log.md` names it: no formal WER on the deployed STT, no extraction precision/recall, no risk accuracy on a labelled set, no latency distribution, no real-key failover test, no user study, no microphone run since Session 41, FHIR never tested against a real receiving system | — | Yes, in full | B |
| 4.7 Discussion | Why the results shaped the architecture | Traceable to ADR-0024 and the whole design | — | Yes | A/B |

---

## CHAPTER 5 — IMPACTS

| Section | Needs | Available + evidence | Missing | Safe to write | Cat |
|---|---|---|---|---|---|
| 5.1 Societal / health / safety / legal / cultural | Impact discussion | 499A Ch.5, `Ethical_and_professional_responsibility_499A.pdf`, the four project rules, the safety design in code | No measured impact — none claimed | Yes; expected impact kept strictly separate from measured results | A/B |
| 5.2 Environment and sustainability | Impact discussion | `Sustainability_and_Environmental_Effects_CSE499B.tex`, inference-only evaluation, CPU-only target, free-tier compute, SDG 3 and SDG 10 | — | Yes | A/B |

---

## CHAPTER 6 — PLANNING AND BUDGET

| Section | Needs | Available + evidence | Missing | Safe to write | Cat |
|---|---|---|---|---|---|
| 6.1 Planning (Gantt) | Timeline | **499A:** existing chart, Mar–Apr 2026 with four demo dates. **499B:** exact dated session history recovered from `changelog.md` — S0 18 Jun · S1–S6 19–21 Jun · S7 architecture lock 25 Jun · S8–S17 3–7 Jul · S18–S24 9–11 Jul · **S25 live real-mic run 12 Jul** · S28–S36 8–13 Aug · S37–S41 13–15 Aug · S42–S45 19 Aug | Nothing | Yes — chart labelled as reconstructed from the development log | A |
| 6.2 Budget | Itemised cost | **Evidence found:** OpenRouter key checked via `GET /api/v1/key` → free tier, **$0 usage** (`test_log.md` S17, `changelog.md`); the optional $10 OpenRouter top-up is recorded as **deferred, not purchased**; paid tiers **explicitly rejected** ("project rule: free-first", ADR); TextBee = open-source gateway on the team's **own BD SIM**; Colab / Drive / GitHub / Hugging Face all free tier; **no hosting, no domain, no cloud deploy anywhere in the repo** — the app runs on one local `uvicorn`; dev machines are the team's own pre-existing hardware | Whether any money left your pockets outside the repo (SIM recharge for the TextBee SMS demo, mobile data, printing) | Table is writable; **the total is not asserted until you confirm** | **C** |

---

## CHAPTER 7 — CEP / CEA

**What CEP/CEA are here:** BAETE (Board of Accreditation for Engineering and Technical Education) accreditation requires a capstone to demonstrate *Complex Engineering Problem* attributes **P1–P7** (depth of knowledge K3–K8, conflicting requirements, depth of analysis, familiarity of issues, extent of applicable codes, stakeholder involvement, interdependence) and *Complex Engineering Activity* attributes **A1–A5** (range of resources, level of interactions, innovation, consequences to society/environment, familiarity). The template supplies a sample table for each and instructs the student to **discuss the table with the supervisor**.

| Section | Needs | Available + evidence | Missing | Safe to write | Cat |
|---|---|---|---|---|---|
| 7.1 CEP (P1–P7) | Attribute → project mapping | 499A Table 7.1 is complete and usable as a base; the 499B system provides much stronger material for P2 (accuracy vs latency, privacy vs cloud AI, recall vs false alarms), P3 (18 benchmarked models + 69 recorded design decisions), P5 (no governing standard; HL7 FHIR R4 adopted voluntarily), P6 (patient / medic / doctor / clinic / regulator), P7 (15-module chain) | Nothing factual | Yes — full mapping, written as analysis | A/B |
| 7.2 CEA (A1–A5) | Attribute → project mapping | 499A Table 7.2 as base, updated for the implemented system | Nothing factual | Yes | A/B |
| Supervisor discussion statement | Whether the tables were discussed with Dr. Khan | 499A says "have been discussed with the faculty advisor" **for CSE499A**. Nothing in the project records a 499B discussion | The fact itself | The tables yes; **the sentence claiming supervisor discussion will not be written unless you confirm it** | **C** |

---

## CHAPTER 8 — CONCLUSIONS

| Section | Available + evidence | Cat |
|---|---|---|
| 8.1 Summary | All verified | A |
| 8.2 Limitations | 10 named limitations, every one evidenced: ASR ceiling · 147/250 matching · no deployed-system evaluation · cloud STT · cloud AI · stubbed auth, no encryption · synthetic data only · failover mock-tested only · no mic run since S41 · voice step S5 not built · M15 retraining not built · SQLite single-server · FHIR never tested against a real receiving system | A |
| 8.3 Future Improvement | `faculty_future_features.md` (3 faculty requirements), `milestone_log.md` roadmap phases, the standing evaluation gap | A |

---

## REFERENCES — verification status

| Reference | Status |
|---|---|
| The 19 entries used in the 499A report (Whisper, MMS, wav2vec 2.0, SeamlessM4T, Qwen2-Audio, Bengali.AI, Common Voice, IndicWav2Vec, Vakyansh, OOD-Speech, BanglaBERT, BioBERT, ClinicalBERT, Transformers, LoRA, WhisperX, Attention Is All You Need, BERT, WHO) | Reused **only where the claim needs them**; each re-checked before inclusion |
| **BLEU — Papineni, Roukos, Ward, Zhu** | **Verified this session:** ACL 2002, pp. 311–318, ACL Anthology P02-1040 |
| **HL7 FHIR R4** | **Verified this session:** FHIR Release 4, v4.0.1, published 1 Nov 2019 |
| **Web Speech API** | **Verified this session:** Draft Community Group Report, W3C WebAudio Community Group, dated 10 Aug 2026 |
| **jiwer** | **Verified this session:** `github.com/jitsi/jiwer` |
| **Physician density** | **Verified this session:** World Bank indicator SH.MED.PHYS.ZS, Bangladesh 0.637 per 1,000 (2019). Report will say "fewer than one physician per 1,000 people" |
| FastAPI, SQLAlchemy, Alembic, SQLite, python-docx, fpdf2, HarfBuzz, edge-tts | To be cited as software with their canonical project URLs; each URL checked before it goes in |
| Anything I cannot verify | **Will not be cited.** No reference will be invented |

---

## FIGURE PLAN

| Fig | Title | Ch | Section | Source | Status |
|---|---|---|---|---|---|
| 1 | System architecture of the pre-screening platform | 3 | 3.1.2 | New TikZ from `main.py`, `portal_roles.md` | to build |
| 2 | Patient journey through the module pipeline | 3 | 3.1.3 | Adapted from `agent_docs/update_system_flowchart.md`, corrected against code | to build |
| 3 | Database schema (18 tables) | 3 | 3.1.5 | New TikZ from `db/models.py` | to build |
| 4 | Conversational gap-closing loop (M6–M9) | 3 | 3.3.4 | New TikZ from `followup.py`, `completion.py`, `config.py` | to build |
| 5 | LLM provider fallback chain | 3 | 3.3.3 | New TikZ from `llm_providers.py` | to build |
| 6 | Word Error Rate of the evaluated ASR models | 4 | 4.2 | `CSE499_poster_kit_2/assets/stt_wer_poster.png` — values cross-checked against the CSVs | exists |
| 7 | WER by dialect for the leading models | 4 | 4.4 | New chart computed from `evaluation_scores.csv` | to build |
| 8 | Patient kiosk during the follow-up conversation | 4 | 4.6 | `assets/patient_conversation.png` | exists, viewed |
| 9 | Bilingual pre-submission summary | 4 | 4.6 | `assets/patient_summary_en.png` | exists |
| 10 | Medic triage queue and case verification | 4 | 4.6 | `assets/medic_triage_queue.png` | exists, viewed |
| 11 | Doctor case view with EHR export actions | 4 | 4.6 | `assets/doctor_safety_xai.png` | exists, viewed |
| 12 | FHIR R4 document bundle produced for a visit | 3 | 3.3.8 | `assets/ehr_fhir_output.png` | exists |
| 13 | Gantt chart, CSE499A and CSE499B | 6 | 6.1 | New TikZ from `changelog.md` dates | to build |

Screenshots are limited to six, each showing a distinct capability (voice conversation · patient summary · triage queue · doctor decision surface · FHIR output · WER result). No screenshot is included for decoration.

## TABLE PLAN

| Tbl | Title | Ch | Source |
|---|---|---|---|
| I | Software tools and components used | 3.2 | `requirements.txt`, 69 ADRs |
| II | Modules of the system and their implementation status | 3.1 | `milestone_log.md` verified against source |
| III | Database tables and the data each owns | 3.1 | `db/models.py` |
| IV | Risk tiers and rule-based red-flag categories | 3.3 | `red_flags.py`, `risk.py` |
| V | Multi-dialect Bangla speech corpus | 4.1 | 499A Table 4.1 |
| VI | Baseline ASR results (12 models) | 4.2 | `baseline_vs_bigger_comparison.csv` |
| VII | Larger multimodal audio model results (6 models) | 4.3 | same |
| VIII | WER by dialect, leading models | 4.4 | recomputed from `evaluation_scores.csv` |
| IX | Verification activities and what each establishes | 4.5 | `test_log.md` |
| X | Project budget | 6.2 | evidence above + your confirmation |
| XI | Complex Engineering Problem (CEP) attributes | 7.1 | 499A + current system |
| XII | Complex Engineering Activity (CEA) attributes | 7.2 | 499A + current system |

---

## PROJECT CONTRIBUTIONS (separated as instructed)

**Implemented contributions** — a three-portal pre-screening system (patient kiosk, medic triage desk, doctor workspace) over one FastAPI backend with an 18-table Alembic-managed schema; a voice-first bilingual patient intake with typing always available; a conversational gap-closing loop over ten fixed clinical fields; a deterministic, locally-evaluated red-flag rule that overrides the model; explainable risk output that can never be stored without a reason; an append-only audit trail covering AI-written values; a real hashed OTP identity flow behind a pluggable sender; a multi-provider, multi-key LLM failover chain; and clinical output as `.docx`, an HL7 FHIR R4 document bundle, and a correctly-shaped Bangla PDF.

**Evaluated contributions** — the multi-dialect Bangla ASR benchmark: 12 baseline models and 6 larger multimodal audio models scored with WER, CER and BLEU on a self-assembled five-variety corpus, with the finding that scaling did not help and two large models failed outright. This is the only part of the project with measured quantitative results.

**Proposed / future contributions** — LoRA fine-tuning of a mid-sized Bangla ASR model (methodology only, no training performed); local `faster-whisper` STT; the M15 retraining and regression loop; real authentication and encryption; and a formal evaluation of the deployed pipeline.

---

## WHAT I STILL NEED FROM YOU — 4 items only

1. **Cost.** All evidence points to zero monetary cost, but I will not assert it. Did CSE499B cost you anything at all (SIM recharge for the TextBee SMS demo, printing, anything)?
2. **CEP/CEA.** Have you discussed the CEP and CEA tables with Dr. Khan for CSE499B? I will not write that you did unless you confirm it.
3. **Puran Dhaka / Sylheti WER.** Do you want to try re-running the notebook's reference matching before I finalise Chapter 4, or should I write the limitation as it stands?
4. **Appendices.** The BAETE template has no appendix section. Do you want one anyway?
