**Context & Task**

**Project Topic & Details**

**Project Title:** EHR-Based Pre-Consultation Medical Documentation System

**Overview:** Before a patient meets the doctor, they describe their medical history and symptoms to a voice-based interface. An AI pipeline then transcribes the speech, extracts the clinically relevant information, and generates a structured Electronic Health Record (EHR) that the doctor reviews at the start of the consultation — saving consultation time and reducing the doctor's documentation burden.

**Pipeline:** `Voice input → ASR (Bangla / code-mixed) → Medical NER → Structured EHR → Differential-diagnosis hints`

**How It Works:** A patient sits with a voice-enabled device (tablet or kiosk) in the waiting area and speaks naturally about their symptoms, medical history, current medications, and allergies. The system then:

1. Transcribes the speech into text using a Bangla-tuned speech recognition model.  
2. Extracts the medically relevant information — symptoms, diseases, medications, duration, and allergies — using a medical NER model.  
3. Structures the extracted information into a standardized Electronic Health Record (EHR).  
4. Suggests likely conditions for the doctor to consider or rule out, based on the symptom pattern.  
5. Delivers the complete record to the doctor's screen the moment the patient walks in.

The goal is simple: the doctor walks in already knowing the patient's story, so the consultation can focus on examination and decision-making instead of paperwork.

**The Core Technical Challenge: Real Bangladeshi Speech** Patients in Bangladesh do not speak in textbook Bangla. The system must understand how people actually talk in a clinic:

* **Regional dialects** — Sylheti, Chittagonian, Barishali, Dhakaiya, and others, which differ significantly in pronunciation, vocabulary, and even grammar.  
* **Bangla–English code-mixing** — patients freely mix English medical and everyday terms into Bangla sentences (e.g., "gas-er problem, sathe pressure low hoye jay").  
* **Informal, unscripted speech** — hesitations, repetitions, colloquial expressions, and incomplete sentences.

Most existing Bangla speech models are trained on clean, formal speech (news, audiobooks). They break down on real patient speech. Solving this is the hardest and most important part of the project.

**Beyond Transcription: A Pre-Screening Assistant** The system is not just a fancy dictation tool. By linking the extracted symptoms to a lightweight medical knowledge layer, it gives the doctor a short list of conditions worth considering before the examination begins.

Example: persistent cough \+ loss of appetite \+ weight loss \+ night sweats → flag possible tuberculosis, suggest ruling out lung cancer.

The model never makes a diagnosis. It narrows the search space and reminds the doctor of possibilities they might want to investigate. The AI assists; the doctor decides.

**From Models to a Real Product** Once the speech recognition and medical NER models are trained and evaluated, the project moves into a software development phase to turn them into a usable system for real clinics:

* **Patient-facing app** — a simple voice-recording interface (mobile or kiosk) in Bangla, designed for users who may not be tech-literate.  
* **Doctor-facing dashboard** — a clean web interface where the doctor sees the structured EHR, the original transcript (for verification), and the suggested differential diagnoses.  
* **Backend service** — an API that runs the trained ASR and NER models on incoming audio, stores records securely, and serves them to the dashboard.  
* **Privacy and consent layer** — patient data handled with proper consent, encryption, and access control, since this involves sensitive health information.

The end result is a deployable product that a small clinic could realistically install, not just a research prototype.

**Why This Matters** For Bangladesh specifically, this project addresses three real gaps at once:

1. The lack of digital health records in most clinics.  
2. The shortage of consultation time per patient.  
3. The absence of usable Bangla medical AI tools.

Solving the dialect and code-mixing problem also creates speech and NLP resources that can support future Bangla healthcare AI work — far beyond this single product.

**Project Progress (What We Have Done So Far)**

Our instructor guided us through the project in the following phases:

**Phase 1:** The instructor first told us to look at existing ASR models and test them on Bangla dialect speech. We collected a minimum of 1 hour of audio for this. *(Reference: `01_data_download.ipynb` and `02_audio_preprocessing.ipynb`)*

**Phase 2:** We studied how existing ASR models perform on Bangla dialect — voice to transcript. *(Reference: `03_model_comparison_FIXED_3.ipynb`)*

**Phase 3:** After showing our results, the instructor told us to repeat the same process but with bigger ASR models ranging from 2B to up to 7B parameters. We did that as well. *(Reference: `03_bigger_model_comparison_fixed_2.ipynb`)*

**Phase 4:** After showing the results from bigger models, the instructor told us to work on `Qwen/Qwen3-ASR-1.7B` and fine-tune this model for Bangla.

**Phase 5 (Pending — will be done after the presentation):** The instructor told us to talk with existing AI chatbots (examples: ChatGPT, DeepSeek, Qwen, Perplexity, etc.) as if we are a patient using our system, and ask each chatbot to produce output in the format our project would generate. We then need to compare the output formats across different AI chatbots and present the comparison results at the next demo. This phase is not yet done.

