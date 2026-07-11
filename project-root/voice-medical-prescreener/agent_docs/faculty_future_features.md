# 🔮 faculty_future_features.md — Faculty Requirement: Future Features (research track)

> **Why this file exists (S24):** the faculty gave two FUTURE requirements during the 2.0 cycle
> (S16/S18). ADR-0042 explicitly ruled them **out of scope** for the 2.0 build so they wouldn't
> derail the fix cycle — but they must not be lost. This file is the permanent reference for when
> that work starts. The faculty's original wording is kept **verbatim** below (source of truth);
> the implementation notes after it map each requirement onto the seams that already exist in the
> codebase, so a future session can start planning without re-exploring.
>
> **Status: ⬜ NOT STARTED — research track.** Do not begin either item without the human's "go"
> and a session-planned approach (CLAUDE.md workflow). When work starts, turn this into a numbered
> tracker like `context fixed problem 2.0.md` and log decisions as ADRs in `decisions.md`.

---

## The faculty's requirement (verbatim)

## **Faculty Requirement – Future Features**

### **1. Integrate a Quantized AI Model for Medical Summary Generation**

Currently, the system uses an external AI model API to generate structured medical summaries. The workflow is as follows:

* The patient speaks through the microphone.
* The speech is converted into text.
* The transcript is sent to an AI model API.
* The AI model returns the information in the required structured medical format.

As a future faculty requirement, this API-based approach will be replaced with a **locally deployed quantized AI model** developed by our team. The team is training the **Moshi** model using Bangla medical conversations and speech data. After training is completed, a **quantized version** of the model will be integrated into the system to generate structured medical summaries locally. This will reduce dependency on external APIs while improving privacy, response speed, and scalability.

---

### **2. Replace Browser-Based Speech Processing with a Quantized Speech Model**

Currently, the system relies on browser APIs for speech processing:

* **Live Speech-to-Text (STT):** Uses the Browser Web Speech API (`SpeechRecognition`) optimized for Bangla (`bn-BD`) in Google Chrome and Microsoft Edge for real-time transcription.
* **Text-to-Speech (TTS):** Uses the Browser Web Speech API (`SpeechSynthesis`) to read questions and follow-up prompts aloud to patients.

As a future faculty requirement, these browser-based components will be replaced with a **locally deployed quantized speech AI model**. Instead of depending on browser APIs, the integrated model will perform both speech recognition and speech generation within the system. The model will:

* Convert the patient's spoken Bangla into **Banglish (Romanized Bangla)** text in real time.
* Generate natural voice responses to ask medical questions and follow-up prompts.
* Provide a single, integrated speech processing pipeline that supports offline deployment, improves privacy, and reduces dependence on browser-based STT and TTS services.

---

## Implementation notes — where each requirement plugs into TODAY's code

> Written S24 so the future session doesn't re-derive this. Verify against `codebase_map.md`
> before acting — the code may have moved.

### Requirement 1 — quantized summary model (replaces the LLM API for M3/M4/M8… tasks)

- **The seam already exists:** every AI task goes through `backend/app/services/llm_client.py`
  `call_module(module_code, …)`, which picks a provider from
  `backend/app/core/llm_providers.py` (`MODULE_PROVIDERS` + `FALLBACK_ORDER`, ADR-0026/0041).
  All providers are **OpenAI-compatible** (one client, `base_url` + model + key from `.env`).
- **Cleanest integration:** serve the quantized Moshi-derived model behind ANY local
  OpenAI-compatible server (e.g. llama.cpp `llama-server`, vLLM, LM Studio — pick at build time)
  → add it as a provider (`base_url=http://localhost:PORT/v1`, blank key) → point the summary
  modules (M3/M4 first) at it in `MODULE_PROVIDERS`. **Zero pipeline-code change**; the cloud
  chain can even stay as fallback during evaluation.
- **Hardware reality (CLAUDE.md constraint):** CPU-only, 24 GB / 12 GB RAM, no NVIDIA — the
  quantization (int8/int4 GGUF-style) is not optional, it is what makes this feasible at all.
- **Rules that still bind:** raw transcript untouched (rule #1); structured output must keep the
  10-field `summary_fields` contract (`value_en`/`value_bn`, ADR-0033); the local red-flag rule
  in M10 stays independent of ANY model (rule #3); local inference actually *improves* rule #4
  (no patient data leaves the machine — a headline thesis point).
- **Evaluate before switching:** extraction precision/recall + summary quality vs. the current
  Gemini pipeline on the same synthetic set — record in `test_log.md` (a ready-made thesis table).

### Requirement 2 — quantized speech model (replaces browser STT + TTS)

- **STT seam:** the swap was designed-in from day one — `stt_provider` setting in `config.py`
  (`browser_webspeech` today, label stored per-utterance in `utterances.stt_provider`), and the
  "robust path" placeholder in CLAUDE.md is server-side **faster-whisper (CTranslate2, int8,
  CPU)** streamed over the **native WebSocket reserved for Phase 1** (ADR-0025). The faculty
  model would slot into that same server-side position (Bangla speech → **Banglish/Romanized**
  text per the requirement — note: output script changes downstream prompts; M2/M3 prompts must
  be re-checked against Banglish input, which they already partially handle).
- **TTS seam:** `frontend_shared/tts.js` `speak()` is the ONLY TTS entry point (ADR-0027/0028).
  A server-side TTS would become an endpoint returning audio that the kiosk plays — keep the
  **on-screen text as the mandatory fallback** (ADR-0028 survives the swap untouched).
- **Latency gate:** the kiosk loop is live conversation; browser STT is ~instant today. A local
  model on these CPUs must be measured (TC-V1-style: seconds from speech → text) before it
  replaces the browser path — keep `browser_webspeech` as a config-selectable fallback, exactly
  like the OTP sender seam (ADR-0045 pattern: channel switch in `.env`, old path never deleted).
- **Win worth stating in the thesis:** removes the rule-#4 caveat that Web Speech API sends
  audio to Google's cloud → fully offline, private, deployable in rural clinics.

### Suggested build order (when this starts)
1. Requirement 1 first (pure config-level provider swap, lowest risk, no UX change).
2. Then STT (server-side, WebSocket streaming — the pre-planned Phase 1 shape).
3. TTS last (browser TTS already works and has a clean fallback story).
