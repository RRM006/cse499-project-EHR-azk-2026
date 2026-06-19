**Project Title   :** AI-Powered Voice-Based Medical Pre-Screening System  with Intelligent symptom capture and clinical documentation for Bangladesh

**Overview:** Before a patient meets the doctor, they speak naturally in Bangla, Banglish, or regional dialects to describe their symptoms and medical history. An AI pipeline transcribes the speech, extracts clinically relevant information, asks targeted follow-up questions to fill any gaps, and generates a structured pre-screening report — all before the consultation begins.

The doctor receives a ready-to-review report including the patient's symptom profile, risk level with an explainable AI summary, emergency flags, and suggested next steps — reducing documentation burden, cutting consultation time, and ensuring no critical information is missed. All data is securely stored in an EHR-integrated database, and doctor feedback continuously improves the system over time.

**How it works**

A patient sits with a voice-enabled tablet or kiosk in the waiting area and speaks naturally — describing symptoms, medical history, current medications, and allergies in Bangla or Banglish. From that single recording, the system builds a complete clinical picture before the doctor walks in: transcribing the speech, extracting medically relevant entities, structuring them into a standardized EHR, surfacing a short list of conditions worth considering, and delivering everything to the doctor's dashboard the moment the patient enters the room.

**Beyond transcription**

This is not a dictation tool. By linking extracted symptoms to a lightweight medical knowledge layer, the system gives the doctor a focused differential before the examination begins — for example, flagging possible tuberculosis and prompting a rule-out of lung cancer when a patient reports persistent cough, weight loss, and night sweats. The model never diagnoses. The AI narrows the search space; the doctor decides.

**The product**

Once the core models are trained/build, the system becomes a deployable clinic product: a Bangla voice interface for patients, a clean web dashboard for doctors, a secure backend API, and a built-in consent and encryption layer. A small clinic should be able to install and use it — not just read about it in a paper. And the Bangla speech and NLP resources built along the way will support future healthcare AI work well beyond this system.

## **Project Objective**

The goal of this project is to develop a real-time Speech-to-Text (STT) system specifically designed for Bangladeshi patients. The system will accurately capture and transcribe spoken Bangla, regional Bangla dialects, and Bangla-English mixed speech (Banglish) into text without modifying the patient's original words.

The transcribed text will serve as the foundation for an intelligent clinical pre-screening platform that assists healthcare professionals by automatically extracting medical information, assessing risk levels, and generating structured clinical reports.

## **Core Speech-to-Text Requirements**

### **R1. Real-Time Processing**

* The system must transcribe speech as the patient speaks.  
* Minimal latency between speech input and text output.  
* Continuous streaming transcription capability.

### **R2. High Accuracy**

* The displayed text should match the patient's spoken words as closely as possible.  
* No unnecessary word replacement or modification.  
* Preserve the patient's original expressions whenever possible.

### **R3. Bangladesh-Focused Speech Recognition**

The ASR (Automatic Speech Recognition) system should support:

* Standard Bangla  
* Regional Bangladeshi dialects  
* Bangla-English code-switching (Banglish)  
* Different accents, speaking speeds, age groups, and educational backgrounds

### **R4. Open-Source and Low-Cost Deployment**

* Preference for open-source models and tools.  
* Capable of running on low-resource devices.  
* Free APIs may be used where necessary (e.g., OpenRouter-supported models).

### 

### **Technical Notes**

* Converting spoken Banglish directly into Bangla script may reduce fidelity. The system should first preserve the exact utterance and perform normalization only in later processing stages.

Real-time speech recognition with minimal latency.

Support for:

* Standard Bangla  
* Regional Bangladeshi dialects  
* Bangla-English code-switching (Banglish)

Preserve the patient's exact spoken words.

Avoid modifying, paraphrasing, or rewriting speech during transcription.

Work on low-capability devices.

Prefer open-source models and free APIs when required.

Potential technologies:

* OpenAI Whisper / Faster-Whisper  
* BanglaSpeech2  
* Wav2Vec2 Bangla models  
* OpenRouter-supported free models (for downstream NLP tasks)

**System Architecture and Roadmap**

\#\# Module 1: Speech-to-Text

\*\*Goal:\*\* Convert patient voice input into raw text.

The system accepts voice input in Bangla, Banglish, or regional dialects. A speech recognition model trained or fine-tuned on Bangladeshi speech patterns handles transcription. The module must tolerate noise, accents, and code-switching between Bangla and English.

\*\*Key requirements:\*\* Dialect-aware acoustic model, real-time or near-real-time transcription, fallback to manual text input if speech quality is poor.

Bangla-focused ASR system with:

* Dialect recognition  
* Banglish support  
* Real-time transcription  
* Manual text input fallback

\#\# Module 2: Text Processing and Normalization

\*\*Goal:\*\* Clean, standardize, and prepare raw transcribed text for downstream analysis.

This module handles spelling correction, normalization of Banglish text, removal of filler words, punctuation restoration, and sentence boundary detection. Where necessary, it translates Bangla or Banglish content into a standardized form the rest of the pipeline can process consistently.

\*\*Key requirements:\*\* NLP preprocessing pipeline, Bangla-English bilingual handling, medical spelling correction, noise and artifact removal.

Processes raw transcripts by:

* Correcting spelling errors  
* Normalizing Banglish expressions  
* Removing fillers and noise words  
* Detecting sentence boundaries

\#\# Module 3: Information Extraction  
\*\*Goal:\*\* Extract structured clinical data from the normalized text.

The system identifies and tags key clinical entities including symptoms, affected body parts, duration, severity, frequency, patient age, and any pre-existing conditions or medications mentioned. This forms the foundation of the patient profile.

\*\*Key requirements:\*\* Medical NLP, named entity recognition for clinical entities, temporal expression extraction (e.g., "for three days", "since last week").

Automatically identifies and extracts:

* Symptoms  
* Body parts  
* Duration of symptoms  
* Severity levels  
* Medications  
* Existing diseases and comorbidities

\#\# Module 4: Initial Clinical Summary Generation

\*\*Goal:\*\* Generate a concise, human-readable summary of the patient's chief complaint.

From the extracted entities, the system produces a short clinical summary that captures the core of what the patient reported. This is used in subsequent modules and displayed on the doctor dashboard.

\*\*Example output:\*\* \*"Patient reports fever and dry cough for 3 days, with mild fatigue. No mention of breathing difficulty or chest pain."\*

\*\*Key requirements:\*\* Medical text summarization model, templated and generative output options.

Generates a concise and human-readable summary of the patient's chief complaint for doctors.

\#\# Module 5: Emergency Detection

\*\*Goal:\*\* Immediately flag life-threatening or urgent conditions before the full pipeline runs.

This module runs in parallel with or immediately after extraction. It checks for red-flag symptoms — such as chest pain, stroke indicators, severe breathing difficulty, loss of consciousness, or acute trauma — and triggers an emergency alert if any are detected. This step takes priority over everything else.

\*\*Key requirements:\*\* Rule-based critical symptom checker, AI classifier for ambiguous emergency presentations, escalation pathway to alert medical staff immediately.

Runs in parallel with other modules and immediately identifies critical conditions such as:

* Chest pain  
* Stroke symptoms  
* Loss of consciousness  
* Severe breathing difficulties

Automatically alerts healthcare staff when emergency symptoms are detected.

\#\# Module 6: Missing Information Analysis

\*\*Goal:\*\* Identify clinical information gaps that are necessary for a complete pre-screening profile.

Using clinical reasoning rules and medical knowledge, the system checks what information is present versus what is expected. It produces a checklist of confirmed and missing data points.

\*\*Example output:\*\*  
\- ✓ Symptom detected: Fever  
\- ✗ Temperature reading not provided  
\- ✗ Duration of fever not specified  
\- ✗ Breathing difficulty not assessed

\*\*Key requirements:\*\* Symptom completeness logic, clinical checklists per condition category, structured gap report generation.

Evaluates collected clinical information and identifies missing data required for proper assessment.

Produces a structured gap analysis report.

\#\# Module 7: Dynamic Follow-up Question Generation

\*\*Goal:\*\* Generate targeted, conversational questions to fill identified information gaps.

Based on the missing information report, the system generates follow-up questions in natural language — in Bangla or English as appropriate. Questions are prioritized by clinical importance and adapt based on what has already been answered. The system avoids redundant or already-answered questions.

\*\*Example output:\*\* \*"Apnar jwor ki matro kal theke? Thermometer diye measure korechen?"\* / \*"When did your fever start? Have you measured your temperature?"\*

\*\*Key requirements:\*\* Question generation model with medical context, Bangla/English bilingual output, priority ranking of questions.

Generates intelligent follow-up questions in voice mode :

* Bangla  
* English

Questions are prioritized according to clinical importance to collect missing information.

\#\# Module 8: Response Processing and Profile Update

\*\*Goal:\*\* Analyze patient answers to follow-up questions and update the patient profile.

New answers go through the same extraction and normalization pipeline as the original input (Modules 2–3). Extracted information is merged into the existing patient profile, resolving any contradictions and marking newly filled gaps.

\*\*Key requirements:\*\* Incremental NLP pipeline, patient profile state management, conflict resolution logic.

Patient responses are reprocessed through:

* Text normalization  
* Medical entity extraction

New information is merged into the patient profile with conflict resolution mechanisms.

\#\# Module 9: Case Completion Check

\*\*Goal:\*\* Determine whether sufficient information has been collected to proceed to assessment.

The system scores the completeness of the patient profile against a minimum threshold for reliable pre-screening. If critical gaps remain, it loops back to Module 7 for another round of questions. The loop continues until the profile is sufficiently complete or a configurable maximum number of turns is reached.

\*\*Key requirements:\*\* Completeness scoring model, configurable thresholds per condition type, loop management and turn limits to avoid patient fatigue.

Evaluates overall profile completeness.

* Assigns a completeness score.  
* Returns to the follow-up questioning stage if critical information is still missing.  
* Stops after a configurable maximum number of interaction cycles.

\#\# Module 10: Risk Assessment   Engine

\*\*Goal:\*\* Classify the patient into a risk tier based on their complete profile.

The system assigns one of four risk levels — Low, Medium, High, or Critical — using a combination of clinical decision rules and a trained risk prediction model. Risk factors such as age, comorbidities, symptom severity, and duration are all weighted. Critical risk cases are re-flagged for immediate attention.

\*\*Risk tiers:\*\*  
\- \*\*Low\*\* — Likely minor, self-limiting condition  
\- \*\*Medium\*\* — Warrants examination but not urgent  
\- \*\*High\*\* — Needs prompt medical attention  
\- \*\*Critical\*\* — Requires immediate intervention

\*\*Key requirements:\*\* Risk classification model, clinical rule engine, age/comorbidity weighting, integration with emergency detection output from Module 5\.

Classifies patients into:

* Low Risk  
* Medium Risk  
* High Risk  
* Critical Risk

Assessment is based on:

* Symptoms  
* Severity  
* Age  
* Medical history  
* Comorbidities

Uses a combination of clinical rules and machine learning models.

\#\# Module 11: Explainable AI (XAI)

\*\*Goal:\*\* Make the system's reasoning transparent and auditable for doctors and regulators.

For every risk assessment, the system generates a plain-language explanation of which symptoms, durations, and risk factors contributed to the classification. This builds doctor trust, enables correction, and satisfies medical accountability requirements.

\*\*Example output:\*\* \*"High risk was assigned due to: fever lasting more than 5 days, reported difficulty breathing, and patient age over 65."\*

\*\*Key requirements:\*\* Feature attribution methods (e.g., LIME, SHAP, or rule-based reasoning traces), human-readable explanation generation, display on doctor dashboard alongside the report.

Provides transparent explanations of risk predictions.

Doctors can see:

* Which symptoms influenced the prediction  
* Why a patient was assigned a specific risk category  
* Confidence indicators and reasoning

\#\# Module 12: Structured Clinical Report Generation

\*\*Goal:\*\* Compile all collected information into a formatted pre-screening report ready for the doctor.

The report presents a standardized summary that the doctor can review before or during the consultation. It does not contain a diagnosis but provides a clear, organized picture of the patient's situation.

\*\*Report sections:\*\*  
\- Patient Profile (age, gender, known conditions)  
\- Chief Complaint  
\- Symptoms with Duration and Severity  
\- Emergency Flags (if any)  
\- Follow-up Questions and Answers  
\- Risk Level and Explanation  
\- Possible Condition Categories (not a diagnosis)  
\- Recommended Next Steps

\*\*Key requirements:\*\* Medical report generation system, structured and human-readable output, PDF and digital dashboard export options.

Generates a structured pre-screening report containing:

* Chief complaint  
* Extracted symptoms  
* Risk assessment  
* Emergency alerts  
* Possible differential conditions  
* Recommended next steps

Reports can be exported as:

* PDF  
* Dashboard view

\#\# Module 13: EHR Database

\*\*Goal:\*\* Securely store all patient data, reports, and interaction history.

Every session — including transcripts, extracted data, follow-up exchanges, risk assessments, and final reports — is stored in a structured medical database. Records are linked to patient identifiers and consultation timestamps. The database supports future retrieval, audits, and longitudinal patient tracking.

\*\*Key requirements:\*\* Secure, HIPAA/PDPA-compliant database design, encryption at rest and in transit, patient identity management, efficient retrieval by patient ID or date, audit logging.

Secure storage for:

* Audio recordings  
* Transcripts  
* Patient profiles  
* Clinical reports  
* Audit logs

Data should be encrypted and compliant with healthcare privacy regulations.

\#\# Module 14: Doctor Dashboard

\*\*Goal:\*\* Give doctors a clear, fast interface to review the pre-screening report before or during consultation.

The dashboard displays the structured clinical report, risk level, emergency flags, and the XAI explanation. Doctors can see the patient's conversation history, validate or override any extracted information, and add their own annotations. A notification system alerts doctors to high or critical risk cases immediately.

\*\*Key requirements:\*\* Web-based dashboard, role-based access control, real-time notifications for high/critical cases, annotation and override tools, mobile-responsive design.

Web-based interface providing:

* Full patient transcript  
* Clinical summary  
* Risk score  
* Explainable AI insights  
* Real-time emergency alerts  
* Doctor annotations and overrides

\#\# Module 15: Feedback and Continuous Learning

\*\*Goal:\*\* Use doctor feedback to improve system accuracy and clinical relevance over time.

After each consultation, doctors can rate the quality of the pre-screening report, correct inaccurate extractions, flag missed symptoms, and annotate risk level disagreements. This feedback is collected, reviewed, and periodically used to retrain or fine-tune the extraction, risk, and question-generation models.

\*\*Key requirements:\*\* Structured feedback collection interface on the dashboard, feedback dataset management, model retraining pipeline, performance monitoring and regression testing before deploying updated models.

Healthcare professionals can:

* Rate system outputs  
* Correct extracted information  
* Add annotations

Collected feedback is used for:

* Model retraining  
* Performance improvement  
* Regression testing before deployment

Expected Outcome

The final product will be an AI-powered clinical pre-screening assistant capable of understanding Bangladeshi speech, generating accurate medical summaries, detecting emergencies, assessing patient risk, and supporting doctors with structured, explainable, and actionable clinical insights before consultation.

