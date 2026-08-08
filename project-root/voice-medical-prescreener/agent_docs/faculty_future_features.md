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
> **Requirement 3 EXPANDED 2026-08-08 (S28)** — the human broadened it from "remove the mic clicks"
> to **"every patient interaction after login must support BOTH voice and typing, switchable at
> will"** (§3b below). The original §3 text is kept byte-identical above it; §3b is the human's own
> written expansion. **ADR-0048** scopes the expansion and records the governing-rule conflict it
> creates with ADR-0027 (see below) — that conflict is **not yet resolved**; it needs the human's GO.
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

### **3b. EXPANSION (human, 2026-08-08 / S28): dual input — Voice AND Typing, the patient's choice**

> Scope grew here. Requirement 3 is no longer only "remove the mic clicks"; it now governs **the
> whole Patient Portal interaction after phone login**. Recorded as **ADR-0048**.

**GOAL.** After the patient logs in with their phone number and enters the Patient Portal, ALL
patient questions/interactions must support **both** VOICE MODE and TYPING MODE. The patient must
**not** be forced into one or the other, and must be able to switch between them naturally.

**VOICE MODE**
- The microphone becomes ready **automatically after TTS finishes** — never while TTS is speaking.
- The patient answers naturally; ~**3 seconds of continuous silence** is taken as "probably finished".
- At that point a **visible countdown** is shown ("Submitting in 3… 2… 1…"), large and legible enough
  for elderly / non-technical patients.
- **If the patient starts speaking again during the countdown, the countdown is CANCELLED and
  listening continues.** A short pause must never cut the answer off.
- TTS/audio echo must never enter the patient's transcript.
- RAW transcript preserved exactly as captured; the corrected transcript stays a separate field.

**TYPING MODE**
- A text input is **always visible** — typing is a first-class choice, not only a failure fallback.
- Voice → typing (when STT fails or the patient prefers it) and typing → voice must both work
  mid-conversation.
- Typed answers follow the **same** question/follow-up flow; **no separate pipeline**. The backend
  receives one common format regardless of origin.

**PATIENT CONTROL / SAFETY**
- Hands-free must never mean loss of control: keep a clear **Stop/Cancel**, keep the existing
  **Done / See Summary**, allow interrupt + retry of a question.
- Silence must not wait forever: after a reasonable timeout, repeat the question **once**; if still
  no answer, surface the typing option.
- **Never silently submit an empty answer.**

**SAFETY/UX RULE (explicit).** Do **not** assume 3 seconds of silence always means the patient has
finished. The 3-second window is a **CONFIRMATION WINDOW, not an aggressive hard cutoff.**

**Desired shape**

```
AI: "আপনার কী সমস্যা হচ্ছে?"   → AI finishes speaking
    → microphone becomes active
    → patient: "আমার মাথা ব্যথা করছে..."   → patient stops
    → silence detected:  "Submitting in 3... 2... 1..."
        · still silent      → submit answer
        · speaks again      → cancel countdown, keep listening

    [🎤 Speak]  [⌨ Type]        ← the active method is always obvious
```

**Real-life cases the design must answer** (the human's list, kept in full): elderly patients who
pause; slow speakers; coughing / throat-clearing; background noise; family talking nearby;
Bengali/Banglish speech; browser mic-permission problems; mic disconnected; TTS voice unavailable;
speech recognition ending unexpectedly; changing their mind during the countdown; accidental screen
touches; wanting to type after starting voice; wanting to speak after starting typing; very long
answers; completely silent patients; repeated "I don't know" / unclear answers; accidental empty
submissions; network/API delays; the browser tab losing microphone permission.

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

#### Suggested implementation order (Requirement 3, internal — S27 original, superseded by the S28 plan below)
1. **Auto-listen on `speak()`'s `onend`** — mic opens itself after the question; the patient still
   taps once to finish. Removes half the taps with no endpointing risk.
2. **Silence-based auto-endpointing** behind the `voice_loop` switch; tap-to-finish stays available.
3. **Echo / barge-in handling + the bounded no-speech re-prompt** (the correctness work).
4. **Apply to the KIOSK-7 resume dock** and re-verify the `scope=fields` loop.
5. **Revisit as true full-duplex** once Requirement 2's streaming STT gives real VAD.

---

## S28 inspection + plan for Requirement 3 + 3b (2026-08-08 — PLAN ONLY, awaiting the human's GO)

> Written after a full re-read of `kiosk.js`, `kiosk.html`, `tts.js`, `shared.js`,
> `routes_followup.py`, `schemas/followup.py`, `core/config.py` and `backend/tests/`.
> **No code was changed.** Every step below is GO-gated individually.

### A. What ALREADY works (do not rebuild)
- **The server loop is already autonomous** — `POST /followup/answer` returns `next_question` in the
  same response; `submitPatientTurn()` chains it into `assistantSays()`. Faculty steps 4–8 work today.
- **Voice and typing ALREADY share one pipeline.** `AnswerRequest.source: Literal["mic","manual"]`;
  `sendTypedFallback()` → `submitPatientTurn(text,'manual')` and `sendResumeTyped()` →
  `submitResumeAnswer(text,'manual')` hit the **same endpoint**. 3b's "do not duplicate the
  question/answer logic" is **already satisfied** — there is no duplicate flow to remove.
- `speak(text,{onend})` exists (ignored at all 3 call sites); `interimResults=true` already supplies
  the silence ticks; `activeDock()` means the KIOSK-7 resume dock inherits any change for free;
  `stopListening()` already refuses to submit empty text; the loop is bounded server-side (cap 5).

### B. What must change
1. **Typing is second-class** — hidden behind the *"Microphone issue? Type instead"* link. 3b makes
   it co-equal and always visible.
2. Mic never opens itself (the three `speak()` call sites drop the callback).
3. `kiosk.js` `r.onend = () => { if (listening) r.start(); }` **deliberately never ends a turn** —
   this is the line the endpointer replaces.
4. No countdown UI exists in `kiosk.html` (neither dock).
5. No echo guard — nothing stops `recognition.start()` while TTS is audible.
6. No no-speech timeout / re-prompt — an auto-opened mic with a silent patient hangs forever.
7. `AnswerRequest.raw_text: str` has **no minimum length** — an empty answer is storable today.

### C. ⚠ GOVERNING-RULE CONFLICT — unresolved, needs the human's explicit GO
`CLAUDE.md` ("VOICE INTERACTION RULES") and **ADR-0027** state: *"Patient input is VOICE ONLY (no
keyboard for the patient). The manual text box remains ONLY as a developer/accessibility fallback."*
**ADR-0030** narrowed it further (typing allowed for phone/OTP identification, never clinical input).
**Requirement 3b directly supersedes this.** It must be an explicit, recorded decision — see
**ADR-0048** — and `CLAUDE.md`'s rule text must be edited as part of the build, not silently
reinterpreted.

### D. Recommended UX
- **Persistent segmented control in BOTH docks — `[🎤 Voice] [⌨ Type]`** — always visible, the active
  mode filled teal + `aria-pressed`, so the patient always knows which input is live.
- **Voice:** question shown + spoken → TTS `onend` → **400 ms guard** → mic opens itself, hint
  "শুনছি… / Listening…" → speech stops → **visible 3-2-1 confirmation window** (ring + large digit +
  "৩ সেকেন্ডে জমা হচ্ছে…") → **any** new interim result cancels it and listening continues → 0 submits.
- **⚠ OPEN QUESTION for the human — the 3 seconds.** 3b says both "detect ~3 s of continuous silence"
  *and* "then show a 3-2-1 countdown", which read literally is 3 + 3 = **6 s** before submit.
  **Recommendation: the 3 s silence window IS the visible countdown** (one window, ≈3 s + engine lag)
  — it satisfies both sentences and avoids 6 s of dead air reading as "broken".
  Alternative for noisy rooms: 1.2 s quiet-detect **then** a 3 s countdown (≈4.2 s). **Not yet chosen.**
- **Typing:** mic fully **off** (not merely ignored — no bystander capture), input focused, Enter or
  Send submits. TTS still speaks the questions (output channel, unchanged).
- **Mode switch mid-answer:** Voice→Type **clears** the un-submitted voice buffer rather than
  pre-filling it. Reason: a typed edit on top of STT text would be stored as ONE utterance whose
  `source`/`stt_provider` provenance is false. (Option B — pre-fill and store `source='manual'` —
  available if the human prefers; **not chosen**.)
- **Always reachable:** `⏸ Stop` (drop out of auto-listening back to manual), `🔊 Repeat question`,
  and the existing `Done — see summary`.

### E. Real-life safeguards (answers 3b's list)
| Situation | Behavior |
|---|---|
| Elderly / slow / pausing | 3 s window; **any** interim result cancels the countdown. Never a hard cutoff |
| Cough / throat-clear / "উম্…" | Non-final chunks never enter `finalBuffer` but **do** cancel the countdown — errs toward not cutting the patient off |
| Background noise, family nearby | Mic open **only** during an active turn — never during API calls, never on the summary screen unless a resume question is open. Visible red listening state |
| Bengali / Banglish | Unchanged (`lang='bn-BD'`); the timing logic is language-agnostic |
| Mic permission denied / disconnected | Existing `onerror` `not-allowed`/`audio-capture` path survives untouched → auto-switch to Type mode + explain why |
| **TTS voice unavailable** | 🚨 `onend` may **never fire** → frozen kiosk. `max(3 s, len×80 ms)` fallback timer opens the mic anyway. KIOSK-2 hint banner already covers the no-voice case |
| Chrome ends recognition on its own | Keep the restart, gated: only while `listening && !countingDown && !submitting` |
| Mind changed during countdown | Speaking cancels it; `⏸ Stop` cancels it; a screen touch cancels it |
| Accidental screen touch | Only the mode toggle / Stop / Done are hit targets in the dock — a stray tap cannot submit |
| Very long answers | 120 s hard cap → auto-submit what was captured (prevents runaway + memory growth) |
| Completely silent patient | 10 s → repeat the question **once** → another 10 s → auto-switch to Type mode, input focused. Never an infinite wait, never an empty submit |
| Repeated "জানি না" / unclear | Already handled server-side — `scope=fields` counts it answered and will not re-ask; the cap ends the loop |
| Network / API delay | `state.busy` already blocks re-entry; add a visible "thinking" state; mic stays shut until the next question finishes speaking |
| Tab hidden / loses permission | `visibilitychange` → pause the auto-loop, show "Tap to resume". A user gesture is genuinely required to re-acquire the mic — this cannot be automated away |

### F. Backend changes (minimal — **no schema change, stays at Alembic head 0012**)
1. **`GET /api/config`** (public, no auth) → `{voice_loop, silence_ms, countdown_ms, no_speech_ms,
   tts_guard_ms, max_answer_ms}`. **There is no config endpoint today** (verified). This is what lets
   a clinic tune the 3 s for elderly patients without editing JS.
2. `voice_loop: str = "auto"` + those timings in `core/config.py`, `.env`-overridable
   (**ADR-0045 pattern: switch in `.env`, the old manual path is never deleted**).
3. `AnswerRequest.raw_text` gains `min_length=1` + a non-blank validator — server-side enforcement of
   "never silently submit an empty answer".
- **Unchanged:** `/followup/answer`, `/followup/next`, the `source: mic|manual` contract, the
  profile/merge pipeline.

### G. Frontend changes
- `frontend_shared/tts.js` — `speak()` gains an `onerror`→`onend` bridge and returns a handle so a
  **cancelled** utterance cannot fire a stale "open the mic" callback.
- `frontend/kiosk.html` — mode toggle (both docks), countdown element (both docks), `⏸ Stop`; the
  typed row becomes permanent instead of `display:none`.
- `frontend/kiosk.js` — the bulk: `inputMode` state, auto-listen chaining, silence timer + countdown +
  barge-in cancel, no-speech re-prompt, visibility handling, `activeDock()` extended with the new ids.
- All new strings bilingual via `data-en`/`data-bn` (P1-2 rule).

### H. Tests — and an honest limit
**There is no JavaScript test infrastructure in this repo** (no `package.json`, no Node; all 192 tests
are pytest/backend). **The countdown, the barge-in cancel and the echo guard cannot be unit-tested as
things stand.**
- **Existing tests over this area:** `test_followup_loop.py`, `test_followup_min_questions.py`,
  `test_resume_loop.py`, `test_raw_immutable.py`, `test_routes_visits.py`, `test_routes_static.py`.
- **New backend tests (~8, real coverage):** config endpoint shape + `.env` override; `source='manual'`
  stores verbatim with `stt_provider=null`; empty/whitespace `raw_text` → 422; typed and spoken answers
  produce an identical profile merge; raw-immutability re-asserted on the manual path.
- **Frontend, three options — (a) RECOMMENDED:** static-source assertions via `TestClient`, the
  pattern `test_routes_static.py` already uses; catches deletion of the toggle / countdown element /
  guard constants but **does not prove behavior**. **(b)** add vitest + jsdom (real state-machine
  tests, but breaks "one requirements.txt + a venv" and adds a Node toolchain to both machines).
  **(c)** no frontend tests, rely on the live run. **Not yet chosen.**

### I. Risks
| # | Risk | Severity |
|---|---|---|
| R1 | **Endpointer clips an answer** → truncated verbatim = **rule #1 defect, not a UX nit** | 🔴 highest |
| R2 | **TTS echo inside a `patient` utterance.** Note: the Web Speech API opens its **own** audio stream, so `echoCancellation` constraints **cannot** be passed — mitigation is structural gating only (never start while `speechSynthesis.speaking`, + guard delay) | 🔴 high |
| R3 | ADR-0027 "voice-only" conflict (§C) — needs an explicit supersede | 🟠 governance |
| R4 | Core behavior unprovable by unit tests → the human live run is the only real gate | 🟠 |
| R5 | Chrome's own auto-stop racing the JS silence timer | 🟠 |
| R6 | A continuously-open mic on a shared kiosk captures **bystanders** into a medical record | 🟠 privacy |
| R7 | TTS `onend` never fires (no voice installed) → frozen kiosk | 🟡 mitigated (§E) |

### J. Step-by-step plan — each step is its own GO
| Step | What | Risk |
|---|---|---|
| **S1** | `voice_loop` + timing config, `GET /api/config`, `raw_text` min-length, + tests. **Backend only, zero UX change** | none |
| **S2** | `[🎤 Voice][⌨ Type]` toggle in both docks; typing promoted to first-class. **No auto behavior yet** | none to rule #1 |
| **S3** | Auto-listen after TTS (`onend` + speaking-guard + fallback timer). Patient still taps to finish | low |
| **S4** | **Silence detection + visible 3-2-1 countdown + barge-in cancel** ← the heart | 🔴 R1/R2 live here |
| **S5** | No-speech re-prompt, empty-submit guard, 120 s cap, permission/visibility recovery | medium |
| **S6** | KIOSK-7 resume dock + re-verify the `scope=fields` loop | low |
| **S7** | Docs + the human's live Chrome run (§K) | — |

### K. LIVE TEST CHECKLIST (real Chrome + real mic — the only true proof)
**Steps S3–S6 cannot be verified from this side: no mic, no TTS, no browser session.** As in S25, the
human's live run is the gate. Record results in `test_log.md`.
1. **Voice-only completion** — login → finish the whole conversation → summary, **zero screen touches**
2. **Typing-only completion** — never touch the mic; same 10-field summary results
3. **Voice → typing** mid-conversation (switch, answer, loop continues correctly)
4. **Typing → voice** mid-conversation
5. **3-second countdown** appears, is legible, and counts down visibly
6. **Countdown cancellation** — speak again during it; it must cancel and keep listening
7. **No TTS echo in RAW** — inspect the stored `patient` utterances: **zero** AI words. Target: 0
8. **Slow / elderly-style speech** with long mid-sentence pauses — answer must NOT be clipped
9. **Background noise** / a second person talking nearby
10. **Microphone / browser failure** — deny permission, unplug the mic: clean fall back to typing
11. **No-answer fallback** — stay silent: question repeats once, then the typing option appears
12. **Final Done / Summary flow** still works, including the KIOSK-7 resume dock

**Metrics worth logging** (thesis table): zero-touch completion rate · echo-contamination rate
(target 0) · false-endpoint vs missed-endpoint rate · turn-taking latency vs the ≈2 s of S25 · WER and
extraction precision/recall **unchanged** vs tap-to-talk on the same synthetic set.

### Suggested build order (when this starts)
1. Requirement 1 first (pure config-level provider swap, lowest risk, no UX change).
2. Then STT (server-side, WebSocket streaming — the pre-planned Phase 1 shape).
3. TTS last (browser TTS already works and has a clean fallback story).
4. **Requirement 3 is independent of 1 and 2** — it is frontend turn-taking on the existing stack
   and touches no model, so it can be scheduled at any point, including FIRST as the most visible
   demo win. Its step-5 (full-duplex) refinement is the only part that waits for Requirement 2.
