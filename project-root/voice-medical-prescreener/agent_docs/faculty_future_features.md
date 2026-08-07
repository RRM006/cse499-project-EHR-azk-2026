# 🔮 faculty_future_features.md — Faculty Requirement: Future Features (research track)

> **Why this file exists (S24):** the faculty gave two FUTURE requirements during the 2.0 cycle
> (S16/S18). ADR-0042 explicitly ruled them **out of scope** for the 2.0 build so they wouldn't
> derail the fix cycle — but they must not be lost. This file is the permanent reference for when
> that work starts. The faculty's original wording is kept **verbatim** below (source of truth);
> the implementation notes after it map each requirement onto the seams that already exist in the
> codebase, so a future session can start planning without re-exploring.
>
> **Requirement 3 added 2026-08-08** — a later faculty clarification about the follow-up
> conversation. Requirements 1 and 2 below are untouched. ⚠ Provenance note: 1 and 2 are the
> faculty's own pasted text; **3 was relayed by the human as a spoken clarification** and is written
> here in the same formal register — treat its wording as faithful, not literally verbatim.
>
> **Status: ⬜ NOT STARTED — research track.** Do not begin any of the three items without the
> human's "go" and a session-planned approach (CLAUDE.md workflow). When work starts, turn this into
> a numbered tracker like `context fixed problem 2.0.md` and log decisions as ADRs in `decisions.md`.

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

### **3. Fully Voice-Driven Interactive Follow-up Conversation**

Currently, the follow-up stage of the conversation still requires user interaction. The workflow is as follows:

* The AI asks a follow-up question, which is displayed on screen and spoken aloud.
* The patient taps the microphone button to start answering.
* The patient speaks the answer.
* The patient taps the microphone button a second time to signal that the answer is finished.
* The answer is submitted, and the next question is asked.

As a future faculty requirement, the entire follow-up conversation must become **completely voice-driven**. The desired workflow is:

1. The AI asks the follow-up question using voice.
2. The microphone automatically starts listening.
3. The patient answers naturally.
4. The answer is captured automatically.
5. The AI analyzes the answer.
6. If information is still missing, the AI automatically asks the next follow-up question.
7. The cycle repeats until all required information has been collected.
8. The structured medical summary is then generated.

During the follow-up conversation the patient should **not** need to click buttons, press "Next", select questions, or touch the screen. Only **starting** or **ending** the session may require interaction. The goal is a natural spoken conversation between the AI and the patient.

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

### Requirement 3 — fully voice-driven follow-up loop (removes the two mic taps)

- **Why this is future work, not a bug:** nothing here is broken. The tap-to-talk rhythm was a
  deliberate 2.0-era choice (explicit turn boundaries = a clean verbatim record, no echo risk), and
  the S25 live run passed with it. Making the loop hands-free changes the *interaction contract* on
  the kiosk and introduces real speech-engineering problems (endpointing, echo, noise) — so it needs
  its own planned cycle and its own ADR, exactly like the other two requirements.
- **Most of this ALREADY exists — the gap is turn-taking, not pipeline.** The server loop is
  already autonomous: `POST /api/visits/{uuid}/followup/answer` (`api/routes_followup.py`) runs
  M8 merge → M9 completeness → M7 next question and returns `next_question` **in the same
  response** (`AnswerOut`); `kiosk.js submitPatientTurn()` feeds that straight back into
  `assistantSays()`. **Faculty steps 4–8 therefore already work today.** Only steps 2–3 are manual:
  `toggleListening()` needs one tap to open the mic and a second tap to close it
  (`stopListening(true)` is what actually submits the turn). Requirement 3 = automate those two
  taps in the browser; **the basic loop needs no backend change.**
- **Seam for "the mic starts automatically": `speak()` already accepts an `onend` callback** —
  `frontend_shared/tts.js` `speak(text, { lang, onend })`. kiosk.js currently calls `speak(text)`
  and ignores it at all three sites (`assistantSays()`, the KIOSK-7 resume question,
  `repeatQuestion()`). Handing it a "start listening" callback is the whole of step 2, and ADR-0028
  survives untouched (the question is still displayed as text, always).
- **Seam for "the answer is captured automatically": interim results are already on.**
  `initRecognition()` sets `continuous = true` + `interimResults = true`, so every partial chunk is
  a "still talking" tick — a silence timer over those ticks is enough to endpoint a turn without any
  new browser API. The line that must change is `r.onend = () => { if (listening) r.start(); }`
  (today: "brief pauses keep going", i.e. deliberately never ends the turn). The endpointer then
  calls the EXISTING `stopListening(true)`, which already submits the turn.
- **Both loops get it in one change:** `activeDock()` routes the ONE recognition engine to either
  the conversation screen or the KIOSK-7 summary resume dock, so the resume loop inherits the same
  behaviour.
- **The loop is already bounded server-side — hands-free cannot run forever.** `core/config.py`:
  `followup_min_questions = 4`, `followup_max_questions = 5`, `completeness_threshold = 0.7`, plus
  M7's no-repeat memory (`followup_questions.target_gap`). This is the safety property that makes
  removing the taps acceptable: the **cap** ends the conversation, not the patient's finger.
- **Ship it behind a config switch (ADR-0045 pattern:** channel in `.env`, old path never deleted**)**
  — e.g. a `voice_loop = manual | auto` setting, so today's tap-to-talk stays selectable for noisy
  rooms and gives a like-for-like comparison baseline during evaluation.
- **Rules that still bind:** the auto-captured answer is stored verbatim, write-once, as a `patient`
  utterance (rule #1) — **an endpointer that clips a sentence is a rule #1 defect, not a UX nit**;
  the typed fallback and the `onerror` `not-allowed` / `audio-capture` recovery path must survive
  untouched (ADR-0027: keyboard = developer/accessibility fallback only); and "only starting or
  ending may require interaction" still requires a visible, always-reachable **stop / "Done"**
  control — hands-free must never mean uninterruptible.

#### Research challenges (Requirement 3)
- **Echo / self-capture is the big one.** If the mic opens while TTS is still audible, browser STT
  will transcribe **the AI's own question into the patient's verbatim record** — direct rule #1
  contamination. Today that is structurally impossible (`toggleListening()` calls
  `speechSynthesis.cancel()` first, and a human separates the turns). To research: strict `onend`
  gating plus a short guard delay, `getUserMedia` echo-cancellation constraints, or refusing
  mic/TTS overlap entirely until Requirement 2's server-side pipeline can do real VAD.
- **Endpointing in Bangla, for unwell patients.** How much silence means "finished"? Elderly, ill,
  or hesitant patients pause a lot: too short truncates the answer (rule #1 harm), too long feels
  broken. The Web Speech API exposes no energy/VAD signal — only interim-result timing — so this
  stays a heuristic until Requirement 2 lands.
- **Chrome's own auto-stop fights a JS silence timer.** The current `onend`-restart line exists
  precisely because Chrome ends recognition on its own; an auto-endpointer has to arbitrate between
  "the engine stopped" and "the patient stopped".
- **Waiting-room noise and bystanders.** A continuously open mic will pick up attendants and
  neighbours — whose words then end up inside a verbatim medical record?
- **Dead-end states.** Silence because the patient did not understand ≠ silence because they
  finished. Needs a bounded re-prompt (repeat once, then surface the fallback), never an infinite
  wait.
- **Mic permission needs a user gesture.** The session-start tap covers the session, but recovering
  from a mid-session permission or hardware error cannot be automated away.
- **Convergence with Requirements 1 & 2:** true full-duplex speech dialogue (the shape Moshi is
  actually built for) is the real end-state here. Keep Requirement 3 achievable on the CURRENT
  browser stack so it is not blocked on the model work, then revisit it once Req 2's streaming STT
  provides genuine VAD.

#### Evaluation ideas (Requirement 3)
Log in `test_log.md` next to the other metrics — this makes a clean thesis table:
- **Zero-touch completion rate** — % of sessions finished with no screen contact between "start" and
  "end". The headline number for this requirement.
- **Echo-contamination rate** — AI words appearing inside `patient` utterances. Target: **zero**
  (rule #1).
- **False-endpoint rate** (answer cut off mid-sentence) vs. **missed-endpoint rate** (loop hangs).
- **Turn-taking latency** — question audio ends → mic live → answer submitted; compare against the
  ≈2 s STT latency recorded in the S25 live run.
- **WER and extraction precision/recall unchanged** vs. the tap-to-talk path on the same synthetic
  set — auto-capture must not cost accuracy.
- **Patient-perceived naturalness** and total session time vs. today's manual loop.

#### Benefits (Requirement 3)
- Genuine hands-free operation for exactly the users this project targets: low-literacy, elderly,
  low-vision, or simply unwell patients who struggle with a tap-to-talk rhythm.
- Delivers CLAUDE.md's opening premise ("a patient speaks naturally") across the WHOLE conversation,
  not just the opening turn.
- Less staff coaching per patient, faster kiosk throughput, and no repeated screen contact on a
  shared device.
- The natural stepping stone toward the faculty's full-duplex end-state under Requirements 1 & 2.

#### Suggested implementation order (Requirement 3, internal)
1. **Auto-listen on `speak()`'s `onend`** — mic opens itself after the question; the patient still
   taps once to finish. Removes half the taps with no endpointing risk.
2. **Silence-based auto-endpointing** behind the `voice_loop` switch; tap-to-finish stays available.
3. **Echo / barge-in handling + the bounded no-speech re-prompt** (the correctness work).
4. **Apply to the KIOSK-7 resume dock** and re-verify the `scope=fields` loop.
5. **Revisit as true full-duplex** once Requirement 2's streaming STT gives real VAD.

### Suggested build order (when this starts)
1. Requirement 1 first (pure config-level provider swap, lowest risk, no UX change).
2. Then STT (server-side, WebSocket streaming — the pre-planned Phase 1 shape).
3. TTS last (browser TTS already works and has a clean fallback story).
4. **Requirement 3 is independent of 1 and 2** — it is frontend turn-taking on the existing stack
   and touches no model, so it can be scheduled at any point, including FIRST as the most visible
   demo win. Its step-5 (full-duplex) refinement is the only part that waits for Requirement 2.
