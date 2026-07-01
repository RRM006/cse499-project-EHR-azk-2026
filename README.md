# CSE499: EHR-Based Pre-Consultation Medical Documentation System
## (AI Medical Pre-Screening Assistant)

**North South University | Department of Electrical & Computer Engineering**

---

## Project Overview

This capstone project (CSE499A/B) develops an interactive **AI Medical Pre-Screening Assistant** to streamline the patient intake process. The system enables patients in Bangladesh to verbally describe their symptoms in Bangla, Banglish, or regional dialects, and converts this information into a structured, physician-ready Electronic Health Record (EHR) pre-screening report.

### The Architectural Evolution

Originally proposed as a passive, linear **5-Stage ASR Pipeline**, empirical results during Phases 1–3 demonstrated that even the strongest open-source Bangla ASR model (BengaliAI Regional) yields a **46.94% Word Error Rate (WER)** on real dialect speech. In a single-pass system, this level of noise leads to critical, silent clinical omissions.

To ensure safety and reliability, the architecture has been upgraded to a **15-Module Conversational Clinical Intelligence System**. This design uses an active conversational loop to detect missing information, ask target follow-up questions to fill gaps, perform emergency triage, assign clinical risk tiers, and generate explainable medical summaries.

---

## Academic Information

| Detail | Information |
|--------|-------------|
| **Course** | CSE499A/B Capstone Project |
| **Supervisor** | Dr. Mohammad Ashrafuzzaman Khan (AzK) |
| **Department** | Department of Electrical & Computer Engineering |
| **University** | North South University (NSU), Dhaka, Bangladesh |

---

## Research Team

| Name | Student ID | Role | Email |
|------|-----------|------|-------|
| Rafiur Rahman Mashrafi | 2221971042 | Team Member | rafiurmashrafi@northsouth.edu |
| M.G. Rabbi Hossen | 2222516042 | Team Member | rabbi.hossen@northsouth.edu |
| Israt Zaman Srity | 2211084042 | Team Member | israt.srity@northsouth.edu |

---

## System Architecture (15-Module Pipeline)

The system coordinates fifteen modules to transform noisy verbal inputs into high-quality clinical reports. Rather than a linear progression, it uses a parallel triage path and a stateful conversational feedback loop.

```text
               Patient Speaks (Bangla / Banglish / Dialect)
                                    |
                                    v
                     [Module 1: Speech-to-Text (ASR)]
                                    |
                                    v
              [Module 2: Text Processing & Normalisation]
                                    |
                                    v
                  [Module 3: Information Extraction]
                                    |
                                    v
                [Module 4: Initial Clinical Summary]
                                    |
                                    v
                  [Module 6: Missing Info Analysis]
                                    |
                                    v
                 [Module 7: Follow-up Question Gen]
              (Audio + Text display | Voice reply only)
                                    |
                                    v
                               Patient Answers
                                                     |
                                                     v
                                       [Module 8: Response Processing]
                                                     |
                                                     v
                                       [Module 9: Case Completion Check]
                                           +---------+---------+
                                           |                   |
                                      [Incomplete]         [Complete]
                                       Loop to M7          Continue
                                                               |
                                                               v
                                                 [Module 10: Risk Assessment]
                                                               |
                                                               v
                                                 [Module 11: Explainable AI]
                                                               |
                                                               v
                                                 [Module 12: Report Generation]
                                                               |
                                                               v
                                                 [Module 13: EHR Database (Store)]
                                                               |
                                                               v
                                                 [Module 14: Doctor Dashboard]
                                                               |
                                                               v
                                                 [Module 15: Feedback Loop]
```

### Module Breakdown

1. **M1: Speech-to-Text (ASR)**: Transcribes patient speech in Bangla/Banglish/dialects. Incorporates noise-tolerant voice activity detection and falls back to manual text entry if input quality is too low.
2. **M2: Text Processing & Normalisation**: Performs spelling correction, Banglish normalization, punctuation restoration, and sentence boundary detection.
3. **M3: Information Extraction (Medical NER)**: Extracts clinical entities (symptoms, body parts, duration, severity, medications, allergies, age, etc.).
4. **M4: Initial Clinical Summary**: Generates a concise human-readable summary of the initial chief complaint.
6. **M6: Missing Information Analysis**: Checks extracted clinical data against expected symptoms per disease template to generate a structured gap report.
7. **M7: Dynamic Follow-up Question Generation**: Generates contextual questions in Bangla or English to systematically collect missing information (Audio + Text display | Voice reply only).
8. **M8: Response Processing & Profile Update**: Processes the patient's answers to update the overall clinical profile and resolve contradictions.
9. **M9: Case Completion Check**: Evaluates if the collected profile is complete enough for clinical assessment; loops back to M7 up to a configured turn limit.
10. **M10: Risk Assessment**: Assigns a risk level (**Low / Medium / High / Critical**) using clinical decision rules and a weighted scoring engine.
11. **M11: Explainable AI (XAI)**: Provides clear, plain-language text explanations showing which specific symptoms and factors led to the assigned risk level.
12. **M12: Structured Clinical Report Generation**: Packages details into a standardized pre-screening template (comprising chief complaints, symptoms, emergency status, follow-up log, and risk analysis).
13. **M13: EHR Database**: Stores session records securely (HIPAA/PDPA-compliant relational storage with row-level encryption).
14. **M14: Doctor Dashboard**: A real-time interface for physicians to review intake reports, review raw transcript audio, and override or annotate system findings.
15. **M15: Feedback & Continuous Learning**: Collects physician adjustments to system outputs, driving model retraining and long-term optimization.

---

## Design Comparison: Old vs. New

| Feature / Dimension | Original 5-Stage Design | Updated 15-Module Design |
|:---|:---|:---|
| **Interaction Model** | Single-pass, stateless transcription pipeline. | Stateful, interactive conversational loop. |
| **Handling Gaps** | None (incomplete data passed to doctor). | Active gap analysis (M6) and follow-up (M7–M9). |
| **Risk Stratification** | Differential diagnostic hints only. | 4-tier risk classification (Low, Medium, High, Critical). |
| **Reasoning Audit** | Not supported. | Dedicated Explainable AI module (M11) using SHAP/LIME. |
| **Language Support** | Standard Bangla and Bangla-English code-mixed. | Bangla, Banglish, and regional dialects (Dhaka, Sylhet, Barishal). |
| **Quality Control** | No post-deployment learning path. | Dr. Feedback loop (M15) to drive continuous training. |
| **Data Traceability** | Audio linked directly to static transcripts. | Complete session logs (transcripts, gap QA, overrides). |

---

## Technical Stack & Software Components

The architecture relies entirely on software-based elements, leveraging open-source ML/DL frameworks and modern web tools.

| Tool | Function | Why Selected |
|------|----------|--------------|
| **Python 3.10 / PyTorch 2.x** | Core ML/NLP backend and execution runtime | Industry standard for machine learning; vast NLP library ecosystem. |
| **HF Transformers** | Model execution and tokenization | Standardized API for Whisper, Wav2Vec2, and Qwen-Audio variants. |
| **HF PEFT / LoRA** | Parameter-efficient fine-tuning | Enables Speech Encoder fine-tuning of Qwen3-ASR-1.7B on limited GPU budgets. |
| **BanglaBERT** | Token classification for Medical NER (M3) | High performance on Bangla-specific text with low adaptation cost. |
| **spaCy + Custom Rules** | Entity tracking & clinical checklists (M6/M9) | Fast, production-ready parsing; allows deterministic medical checklist checks. |
| **WhisperX** | Audio segmentation and alignment (M1) | Segments long-form audio beyond Whisper's 30-second window limitations. |
| **FastAPI** | REST & WebSocket Backend server | High-performance, asynchronous endpoints suitable for live conversational loops. |
| **PostgreSQL** | Relational database storage (M13) | Supports structured clinical schema design, indices, and row-level encryption. |
| **React / Next.js** | Doctor Dashboard application (M14) | Robust dashboard UI ecosystem; server-side rendering support for low-bandwidth clinics. |
| **Flutter / PWA** | Patient Kiosk interface (M1) | Single-button audio recording UX; unified mobile/tablet/PWA distribution. |
| **SHAP / LIME** | XAI feature attribution (M11) | Model-agnostic calculations for plain-text explanation of risk scores. |
| **Google Colab** | Primary GPU compute (T4 / A100) | Adequate for academic prototyping, benchmarking, and low-cost LoRA adapter training. |

---

## Project Status & Phases

The academic roadmap spans 5 core phases across CSE499A and CSE499B:

| Phase | Focus Area | Status | Key Deliverables & Milestones |
|:---:|:---|:---:|:---|
| **Phase 1** | **Audio Collection & Preprocessing** | **Completed** | Collected 4.7 hours of multi-dialect audio; normalized to 16kHz mono; WhisperX VAD segmentation. |
| **Phase 2** | **Baseline ASR Benchmarking** | **Completed** | Evaluated 12 models on dialects. Best model: `BengaliAI Regional` at 46.94% WER (showed need for conversational gaps loop). |
| **Phase 3** | **Multimodal Audio LLM Benchmark** | **Completed** | Benchmarked 6 LLMs (1.7B-7B). Verified that general large models do not outperform specialized models on Bangla dialect. |
| **Phase 4** | **ASR Fine-Tuning Research** | **In Progress** | Formulated LoRA fine-tuning methodology for `Qwen3-ASR-1.7B` on dialect datasets (planned execution in CSE499B). |
| **Phase 5** | **Comparative Chatbot & EHR Study** | **Selected** | Evaluated public LLMs (ChatGPT, DeepSeek, Perplexity, Qwen) on medical extraction, prompting the 15-module redesign. |

### Upcoming for Deployed System (CSE499B)
- **JWT Auth & RBAC**: Dedicated authentication levels for patients, triage nurses, clinicians, and system admins.
- **PDPA-compliant Consent**: Patient intake flow requiring explicit verbal/digital consent prior to audio processing.
- **MLflow Tracking**: Experiment tracking and automated model deployments as Module 15 collects doctor correction data.
- **PDF Report Exporter**: Direct PDF creation from structured reports for physical printing or inclusion in legacy hospital databases.

---

## Getting Started

### 1. Clone the Repository
```bash
git clone https://github.com/RRM006/cse499-project-temp-azk-2026.git
cd cse499-project-temp-azk-2026
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Notebook Execution
To review model comparisons and research benchmarks, run the notebooks in the `notebooks/` directory sequentially:
1. `00_project_setup.ipynb` - Colab environment validation
2. `01_data_download.ipynb` - Data ingestion pipeline
3. `02_audio_preprocessing.ipynb` - Audio cleaning and WhisperX chunking
4. `03_model_comparison.ipynb` - 12 baseline ASR models comparison
5. `04_bigger_model_comparison.ipynb` - 1.7B–7B multimodal models evaluation
6. `05_chatbot_comparison.ipynb` - Chatbot pre-screening outputs audit

---

## License & Acknowledgments

This project is conducted for academic purposes at North South University.
- Special thanks to our Faculty Advisor, **Dr. Mohammad Ashrafuzzaman Khan (AzK)**, for guidance and architecture feedback.
- Thanks to the open-source community for providing Whisper, Wav2Vec2, BanglaBERT, and Qwen audio weights.

*Last Updated: June 2026*
*CSE499 Capstone Project - North South University*

---
