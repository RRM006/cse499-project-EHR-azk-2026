# changelog.md — Session-by-Session History

> The running memory of the project. **Newest entry at the top.**
> One short entry per session. This is what a new session reads to remember
> "what happened recently and why", so we never re-explain or re-litigate.
>
> Template for each entry:
> ```
> ## Session N — YYYY-MM-DD — <short title>
> - Did: <what we actually built or changed>
> - Decided: <any decision; also add it to decisions.md>
> - Broke / problem: <anything that failed or is fragile>
> - Deferred: <what we chose NOT to do yet, and why>
> - Next: <the one thing to do next — also update current_task.md>
> ```

---

## Session 29 — 2026-08-08 — **Step S4 SHIPPED + live-tested PASS**, then **Bangla TTS solved architecturally (ADR-0049)** — 234 → 274 tests
- Did (two separate pieces of work, each after its own "go"):
  - **Step S4 — silence detection + the visible 3-2-1 countdown + barge-in cancel.** `kiosk.html`
    gained a `.countdown` block in **both** docks (2.2rem digit + bilingual caption); `kiosk.js` gained
    the endpointer: `restartSilenceWindow()` / `renderCountdown()` / `endTurnOnSilence()` /
    `finishFlushedTurn()`, a deadline-driven window so a tuned `countdown_ms` displays honestly, and
    `r.onend` rewritten from the old "always restart" line into an arbiter. **Every `onresult` tick —
    interim OR final — restarts the window**, so a pause or a cough cannot clip an answer; the window
    **arms only after real words are captured**, leaving the silent-patient case to S5. **The human's
    live run PASSED.** → 234 → **247 tests**.
  - **The flush (the human's call).** `stopListening()` reads `finalBuffer` immediately, so at zero we
    now `recognition.stop()` FIRST and submit from `onend` (or a 600 ms grace, whichever wins, exactly
    once). Proven in-browser: the submitted buffer was `"আমার জ্বর — এবং গলা ব্যথাও আছে"`, i.e. it
    **included the tail the engine only released on stop()** — without this that tail was silently lost.
  - **Then: Bangla TTS.** Audited first, as instructed. **Verified root cause, not guessed:** Bengali is
    **absent from Microsoft's entire Windows TTS voice list** (no `bn-BD`, no `bn-IN`), and the dev box
    confirms it — only `David/Zira (en-US)`, no `bn` token in the classic OR `Speech_OneCore` hive, no
    Bengali language pack. **So `human_live_run_guide.md` PART 1 was instructing the human to do
    something impossible**, and ADR-0040's "Windows path is unchanged" rested on that false premise.
  - **Built the seam (ADR-0049):** `backend/app/services/tts/` (`base.py` ABC + `espeak.py` +
    `service.py` selector — deliberately mirroring the ADR-0045 OTP seam) and public
    **`GET /api/tts?text=&lang=`** → `audio/wav`. `tts.js` keeps its exact signature but now walks a
    chain: **browser voice → server → `false`**. Text goes to espeak-ng via **stdin** (never argv, so
    Bangla dodges Windows argv encoding), `shell=False`, length-capped because the endpoint is
    unauthenticated. **Zero new Python dependencies** — stdlib `subprocess`.
  - **Honest failure, which was the actual ask:** the old `speak()` returned `true` whenever
    `speechSynthesis` merely existed, so Bangla read by an en-US voice *looked* like success. Now Bangla
    demands a matching voice, a missing engine is a **503** (never a silent 200), `speak()` returns
    **false**, and `/api/config` gained **`server_tts: bool`** — a capability, never the provider name
    or path (the schema's own no-disclosure rule, re-asserted by a test).
- Decided: **ADR-0049 — Accepted.** espeak-ng over the alternatives on verified grounds: **Piper has no
  Bengali voice at all** (checked `VOICES.md`); **`facebook/mms-tts-ben`** is a real bn model but needs
  torch+transformers and is **CC-BY-NC-4.0**, so it is parked as the natural fit for **Requirement 2**
  and drops into this seam as one subclass; **edge-tts** has genuine bn-BD neural voices
  (`NabanitaNeural`/`PradeepNeural`) but pulls binary `aiohttp` and ships question text to Microsoft —
  kept as a documented future provider. espeak-ng wins because it is **already this project's accepted
  Bangla voice** (ADR-0040, Arch), keeps question text **on the machine** (M7 questions are derived from
  patient speech — rule #4), and adds no dependency.
- Broke / problem — **three real bugs found and fixed, two of them mine:**
  1. **A rule #1 trap I created.** Server audio plays through `<audio>`, and `speechSynthesis.speaking`
     is **false** the whole time — so S3's echo guard would have opened the mic while the AI was
     audible. Fixed with **`ttsSpeaking()`** (true for either provider **and while the request is still
     in flight**) swapped into `openMicWhenQuiet()`, plus `ttsCancel()` in `toggleListening()`. Measured:
     `ttsSpeaking()` is already true the instant the request is created.
  2. **I broke English TTS** by making the browser path conditional on finding a matching voice —
     `getVoices()` is empty during Chrome's async load, so English returned `false`. Caught in the
     browser, not by tests. Only **Bangla** now demands a matching voice.
  3. **Stale `shared.js` served from cache** silently sent every question down the wrong language path —
     this is what made bug 2 invisible for two rounds. Starlette's `StaticFiles` sends no
     `Cache-Control`, so Chrome applied heuristic freshness. Fixed with `RevalidatedStaticFiles`
     (`no-cache, must-revalidate`; the existing ETag keeps it a cheap 304), and `tts.js` now reads the
     language from the **`lang` localStorage key shared.js already owns** instead of a shared.js helper,
     removing the cross-file version skew entirely. On a clinic kiosk that staleness would have silently
     disabled Bangla audio after an update.
- **Then espeak-ng was installed (winget, with the human approving the UAC prompt) and the pipeline was
  verified end to end → 274 → 277 tests, 0 skipped:**
  - Engine has a **Bengali voice** (`bn`, `inc\bn`); a Bangla question renders **exit 0, 158,098 bytes,
    RIFF/WAVE, 22,050 Hz, 3.58 s**. Endpoint: **200, `audio/wav`, 157,438 bytes, 3.57 s**.
    `/api/config` → **`"server_tts": true"`**; the KIOSK-2 banner is now **hidden** while
    `banglaVoiceAvailable()` is still false — proving the fallback, not a browser voice, is speaking.
  - **Playback genuinely completes:** `onend` at **3877 ms** vs the measured **22 ms** error path.
  - **Rule #1 integration proof:** with `toggleListening` spied, the mic opened **exactly once at
    4110 ms**; `ttsSpeaking()` was true at 509/1525/2553/3583 ms and the mic stayed shut throughout.
    Without the predicate swap it would have opened at ~400 ms, mid-question.
  - Hardened en route: `resolve_binary()` now also checks the installers' well-known paths, because the
    Windows MSI updates the **machine** PATH and processes started earlier cannot see it — a clinic
    would otherwise see "not installed" forever.
- Deferred: **S5–S7 are still NOT built.** ⚠ And the honest remaining gap: **nobody has HEARD the
  Bangla.** Bytes, duration and completed playback are proven; espeak-ng Bangla is known to be robotic
  (ADR-0040), and whether it is *intelligible* to a Bangladeshi patient is the human's judgement.
  Voice quality must not be described as validated. Also noted, not acted on: **CLAUDE.md says Python
  3.14 but the venv is 3.13.3.**

### 🔊 LIVE RUN VERDICT — end of Session 29 (the human's real listen, in Chrome)
> Recorded as part of Session 29, not a new session: this was one continuous session, and inventing a
> "Session 30" would corrupt the numbering the whole memory system relies on.
- Did: the human ran the kiosk in Chrome with real audio and reported: **Bangla voice: Too robotic ·
  Mic timing: Pass · Countdown: Pass · Transcript clean: Yes · English: Pass**, plus *"there are no gap
  when tts Bangla and English hear . some time 2 question hear at a same time this is confusing"* and
  *"i want make it like human not too robotic"*. Verbatim wording preserved in
  `context fixed problem 3.0.md`. **I then root-caused the audio defect** to
  `services/followup.py:45`.
- Decided: **ADR-0050 (Proposed).** The ADR-0049 **seam is validated and stays**; only its **first
  provider is rejected**. espeak-ng is a formant synthesizer, so "too robotic" is **inherent, not
  tunable** — no `.env` value fixes it. Replacing the voice is **one subclass**, which is exactly what
  the seam was built for. espeak-ng is **demoted, not deleted** (offline, zero-dep, no-network fallback +
  the Arch path). **The replacement provider is deliberately NOT chosen** — edge-tts (natural `bn-BD`
  neural, but a binary dep + sends question text to Microsoft), `facebook/mms-tts-ben` (local, but torch
  + CC-BY-NC), or fold into faculty Requirement 2. That choice carries a **rule #4 privacy trade-off**
  that is the human's to make explicitly, not mine to assume.
- Broke / problem: **TTS-1 — one question is spoken as Bangla then English with no gap**, which sounds
  like two questions. **Root cause found, not guessed:** `services/followup.py:45` forces the M7 prompt
  to emit `"question": "<Bangla question> (<English question>)"` — every question is a SINGLE bilingual
  string, so TTS reads both halves in one breath. **It is not an overlap bug and not caused by
  ADR-0049**; it has existed since S25 and was merely exposed, because espeak `-v bn` also applies
  Bengali phonetics to the English half. The fix must be **TTS-only**: the stored `system` utterance and
  the on-screen text keep the full bilingual string (rule #1 + ADR-0028).
- Deferred: **everything.** The human explicitly asked to fix nothing this session — "i want fixed some
  bug and add some features in upcoming session for now i want you will remember". So **no code was
  written after the verdict**; TTS-1 and TTS-2 are filed as the first two items of the **3.0 cycle**
  (`context fixed problem 3.0.md`, now 🟢 OPEN after being empty since S24). Also still open: **Steps
  S5–S7** of Requirement 3, rotating the 3 API keys, formal WER, the TextBee demo, **CLAUDE.md claiming
  Python 3.14 when the venv is 3.13.3**, and a **stray second uvicorn on port 8000**.
- Next: **TTS-1 first** (functional before polish) — but it needs one human decision before any code:
  should the patient hear **only their UI language** (recommended: faster, less confusing) or **both
  halves with a real pause**? Then TTS-2's provider choice, then Step S5.

## Session 28 — 2026-08-08 — Requirement 3 EXPANDED to voice-first + typing-fallback; inspection, 7-step plan, and **Steps S1 + S2 + S3 SHIPPED** — 234 tests pass
- Did (inspection + docs FIRST as instructed, then Steps S1 → S2 → S3, each after its own separate
  "go" from the human — no code was written before the plan was approved):
  - **The human expanded faculty Requirement 3** from "remove the mic clicks" to **"every patient
    interaction after phone login must support BOTH voice and typing, switchable at will"**. Filed as
    **§3b** in `faculty_future_features.md`, with the original §3 text kept **byte-identical** above it
    (provenance: §3 was relayed S27; §3b is the human's own written expansion).
  - **Full code inspection first, as instructed** — `kiosk.js`, `kiosk.html`, `tts.js`, `shared.js`,
    `routes_followup.py`, `schemas/followup.py`, `core/config.py`, `backend/tests/`.
  - **Key finding #1: voice and typing ALREADY share one pipeline.** `AnswerRequest.source` is
    `Literal["mic","manual"]` and `sendTypedFallback()`/`sendResumeTyped()` already hit the **same**
    `/followup/answer` endpoint. 3b's "do not duplicate the question/answer logic" is already
    satisfied — what is actually wrong is the *framing*: typing hides behind a "Microphone issue?"
    link. Nothing needs un-duplicating.
  - **Key finding #2 — a GOVERNING-RULE CONFLICT, surfaced not silently resolved.** `CLAUDE.md`'s
    VOICE INTERACTION RULES and **ADR-0027** say *"Patient input is VOICE ONLY … the manual text box
    remains ONLY as a developer/accessibility fallback"* (narrowed by ADR-0030 to phone/OTP only).
    Requirement 3b supersedes that. Recorded as **ADR-0048**; the `CLAUDE.md` rule edit is left
    **pending the human's explicit GO**.
  - **Key finding #3: no JavaScript test infrastructure exists** (no `package.json`, no Node — all
    192 tests are pytest/backend). **The countdown, barge-in cancel and echo guard cannot be
    unit-tested as things stand.** Three options filed (static-source assertions per
    `test_routes_static.py` / vitest+jsdom / none); recommended (a); **not yet chosen**.
  - **Key finding #4: two traps the spec does not mention** — (i) if no Bangla voice is installed,
    `speak()` degrades silently and **`onend` may never fire**, freezing an auto-listen kiosk → needs a
    `max(3 s, len×80 ms)` fallback timer; (ii) the Web Speech API opens its **own** audio stream, so
    `echoCancellation` constraints **cannot** be passed — echo protection is structural gating only.
  - **Key finding #5:** `AnswerRequest.raw_text` has **no minimum length** — an empty answer is
    storable today, so "never silently submit an empty answer" needs a server-side guard too.
  - **Filed the full plan** in `faculty_future_features.md` §A–K: what already works, what must
    change, recommended UX (persistent `[🎤 Voice][⌨ Type]` control, countdown as a **confirmation
    window**), a 20-row real-life safeguards table, backend changes (**no schema change — Alembic stays
    at 0012**), frontend changes, tests, 7 risks, a **7-step GO-gated build order**, and the **12-point
    live Chrome checklist**.
- Decided: **ADR-0048 — Accepted** (proposed mid-session, accepted once the human answered its three
  open questions). Voice is the **primary/default** patient interaction and typing is the
  **always-available fallback**; this **supersedes ADR-0027's clinical-input voice-only rule**
  (ADR-0028's "text AND audio" is untouched), and `CLAUDE.md` was amended to match. The 3-second
  countdown **is** the silence window and is a **confirmation window, never a hard cutoff**. ONE
  answer pipeline (`source: mic|manual` unchanged). Timings served from `.env` via a new public
  `GET /api/config`. `raw_text` gains a non-blank minimum, enforced server-side. Frontend tests =
  static-source assertions only (no vitest/jsdom). ADR-0047 marked "scope EXTENDED by ADR-0048".
- Broke / problem: nothing broke — **zero regressions across all three steps** (192 → 211 → 222 →
  234, every existing test still green). Two real hazards were found and closed rather than
  discovered later: (i) **Chrome fires `onend` for an utterance that `cancel()` killed**, so a
  cancelled question's callback would have opened the mic *during the next question* — the AI's own
  voice into a `patient` utterance (rule #1). Closed with a generation token in `tts.js` and
  **disproven by measurement** (two questions 200 ms apart → exactly one mic-open, after the second).
  (ii) With no installed voice `onend` may never fire at all — closed with the
  `max(3 s, len×80 ms)` safety net, verified by deleting `speechSynthesis` (mic still opened at
  416 ms). ⚠ Standing honesty caveat: **no microphone was ever opened this session** — `toggleListening`
  was a spy — so echo is disproven only at the *scheduling* level, and the dev machine has **no
  Bangla voice installed**, leaving the Bangla TTS path unexercised.
- **Then the human answered all three and said GO for S1 only — so S28 also SHIPPED Step S1:**
  - **Answers:** (1) **the 3 s visible countdown IS the silence window** (speech stops → 3→2→1 →
    submit; any resumed speech cancels it instantly); (2) frontend tests = **(a) static-source
    assertions** via the existing `TestClient` pattern, **no vitest/jsdom** — real mic/TTS/countdown/
    barge-in behaviour is proven only by the live Chrome run; (3) **`CLAUDE.md`: YES, update it.**
  - **Priority recorded:** *voice is the main goal and primary UX, not an optional feature* — the
    portal guides patients toward speaking, automating voice wherever possible; typing exists so no
    patient is ever blocked. UX priority = minimize clicks, waiting and complexity for
    elderly/non-technical patients.
  - **Built (S1 — backend only, zero UX change, fully reversible):**
    `core/config.py` — `voice_loop` (`auto`|`manual`, default **auto**) + `voice_countdown_ms=3000`,
    `voice_tts_guard_ms=400`, `voice_no_speech_ms=10000`, `voice_max_answer_ms=120000`, plus a
    `resolved_voice_loop` property (case/space-insensitive; a `.env` typo falls back to `auto`
    instead of breaking startup — same spirit as `resolved_database_url`). **NEW public
    `GET /api/config`** (`api/routes_config.py` + `schemas/kiosk_config.py`) — no DB, no auth,
    built field-by-field so a future secret in `Settings` can never leak through it.
    `schemas/followup.py` — `raw_text` gains `min_length=1` + a non-blank validator that **returns
    the value COMPLETELY UNCHANGED** (`.strip()` tests emptiness only — rule #1); its docstring now
    states the one-pipeline contract for `mic`|`manual`. `backend/.env.example` documents all five
    knobs and the restart requirement. `main.py` registers the router.
  - **`CLAUDE.md` amended (approved):** the "VOICE INTERACTION RULES" block now reads **voice-first,
    typing always available**, with an explicit ⚠ that this **supersedes** the old "patient input is
    VOICE ONLY / keyboard is a mic-failure fallback only" rule (ADR-0027 as narrowed by ADR-0030) and
    a "do not re-apply the old rule" warning; plus the one-pipeline rule and the countdown-is-a-
    confirmation-window rule. Status paragraph notes S28/S1.
  - **Tests: 192 → 211 (+19), all passing** — `test_kiosk_config.py` (defaults, `.env` override,
    `manual` selectable, 4 normalization cases, and an **exact-key-set + no-secret-substring** guard)
    and `test_answer_raw_text_guard.py` (6 blank forms rejected, padding preserved byte-for-byte,
    1-char "না" accepted, voice/typing share one contract, unknown `source` rejected, `mic` is the
    default). **No schema change — Alembic stays at head 0012.**
- **Then the human said "go" again → S28 also SHIPPED Step S2 (kiosk UI, no turn-taking change):**
  - **`kiosk.html`** — a `.mode-switch` segmented control **`[🎤 Speak] [⌨ Type]`** in **both** docks
    (conversation + KIOSK-7 resume), active mode filled teal with `aria-pressed`, bilingual
    `data-en`/`data-bn`. **The old "Microphone issue? Type instead" reveal link is GONE** — typing is
    now a first-class choice, not failure recovery.
  - **`kiosk.js`** — `state.inputMode` ('voice' default), a `DOCKS` map replacing the inline
    `activeDock()` literals, `MODE_HINTS`, and `setInputMode()` which updates **both** docks at once
    (the patient picks once; the resume dock inherits it), hides the mic in Type mode so it cannot be
    tapped by accident, and **focuses the input**. `stopListening()` now restores a **mode-aware**
    hint. Mic `onerror` (`not-allowed`/`audio-capture`) and the unsupported-browser branch now
    **switch the patient to typing** instead of merely revealing a row. **Enter sends** a typed answer
    (UX priority: fewer taps). Post-logout reset returns to voice — every patient starts voice-first.
  - **Rule #1 / ADR-0048 honored:** switching Voice→Type calls `stopListening(false)`, which
    **discards** the un-submitted STT buffer rather than pre-filling the box — a typed edit on top of
    STT text would be stored as one utterance whose `source`/`stt_provider` provenance is false.
  - **Turn-taking is UNCHANGED** — the patient still taps the mic to start and to finish, exactly as
    in the passed S25 run. Auto-listen is S3; the countdown is S4.
  - **Tests: 211 → 222 (+11)** — `test_kiosk_input_modes.py`, static-source assertions per the human's
    decision (2), with a docstring stating plainly that they prove the controls EXIST and cannot prove
    browser behaviour.
  - **Browser-verified** (in-app Chrome preview, no mic needed): voice default → Speak filled, mic
    shown, typed row hidden; Type → mic hidden, input auto-focused, hint changes, **resume dock
    inherits the mode**; switch back restores voice; the EN/BN toggle re-renders both labels and the
    hint in Bangla. **Zero console errors, zero server errors.**
- Deferred: **Steps S3–S7 are NOT built** (auto-listen, countdown, safeguards, resume-dock re-verify,
  live run) — each needs its own "go". `/api/config` is built but **not yet read by the kiosk** (S3 is
  the first consumer). Still open from before: rotating the 3 API keys, formal WER, the TextBee demo,
  the empty 3.0 inbox.
- **Then the human said "go" again → S28 also SHIPPED Step S3 (auto-listen):**
  - **`tts.js`** — `speak()` now carries a **generation token**. Chrome fires `onend` for an utterance
    that `speechSynthesis.cancel()` killed, so without this a **cancelled** question's callback would
    open the mic while the **next** question is still being spoken — the AI's own voice straight into
    a `patient` utterance. Guarded at the single TTS entry point; `onerror` is bridged to the same
    handler (a failed utterance can never strand the caller) and the callback fires **at most once**.
  - **`kiosk.js`** — `VOICE_DEFAULTS` + `loadKioskConfig()` (the **first consumer of `/api/config`**;
    a failed fetch keeps the safe defaults — configuration must never be what stops a patient being
    screened). New `askAloud()` replaces `speak()` at the **three** question sites (`assistantSays`,
    `setResumeMode`, `repeatQuestion`); the per-bubble 🔊 replay stays plain `speak()` because
    reviewing an old turn must not open the mic. `openMicWhenQuiet()` is the **echo guard**: it polls
    until `speechSynthesis.speaking` is false, then waits `tts_guard_ms`, then calls the SAME
    `toggleListening()` a tap calls — one code path, so auto and manual can't diverge. A
    `max(3 s, len×80 ms)` **safety net** covers the case where `onend` never fires (no installed
    voice). `cancelPendingMic()` is wired into every deliberate action — a tap, a mode switch, Done,
    and the logout reset all beat a pending arm. Bilingual arming hint ("the microphone will start by
    itself").
  - **The patient still taps ONCE to finish** — auto-endpointing and the countdown are S4.
    `voice_loop=manual` reproduces the S25 behaviour exactly.
  - **Tests: 222 → 234 (+12)** — `test_kiosk_auto_listen.py`, static-source assertions.
  - **Browser-verified with an instrumented spy on `toggleListening` (no mic touched):** `/api/config`
    really is consumed; a normal question opens the mic **once at 926 ms** with TTS already silent
    (the 3680 ms safety net correctly did not double-fire); **two questions 200 ms apart produce
    exactly ONE open, at 1057 ms — after the second question** (the cancelled utterance's `onend` did
    not fire the mic: the rule #1 echo case, disproven at the scheduling level); a mode switch mid-
    question yields **zero** opens; `manual` yields **zero** opens with the original hint; and with
    `speechSynthesis` deleted entirely the mic still opens at **416 ms** (no freeze).
    **Zero console/server errors.**
  - **Known gap, deliberately deferred to S5 and documented in the code:** tapping "Repeat question"
    while the mic is already open plays TTS into a live recognizer. Closing it means deciding what
    happens to the half-spoken answer already in the buffer — discarding a patient's words is a
    rule #1 decision, not something to slip into this step. Pre-existing since S25.
- Next: **Step S4 on the human's "go"** — silence detection + the **visible 3-2-1 confirmation
  countdown** + barge-in cancel. This is the step where rule #1 is genuinely at risk (a clipped
  answer), and the first one whose core behaviour a spy **cannot** verify — it needs real speech.

## Session 27 — 2026-08-08 — Faculty Requirement 3 filed (fully voice-driven follow-up conversation) + doc cross-references synced (docs-only, no code)
- Did (no code, no tests — 6 markdown files):
  - **`faculty_future_features.md`: added Requirement 3 — "Fully Voice-Driven Interactive Follow-up
    Conversation"** (a later faculty clarification relayed by the human). Written in the same formal
    register as Reqs 1–2 (`Currently… / As a future faculty requirement…`), plus a full
    implementation-notes block: why it is future work, current vs. future workflow, reusable seams,
    research challenges, evaluation ideas, benefits, and an internal build order.
    **Reqs 1 & 2 left byte-identical** (the only deletion was the header's status block).
  - **Key finding — read from the code, not assumed: the server-side loop is ALREADY autonomous.**
    `POST /api/visits/{uuid}/followup/answer` runs M8 merge → M9 check → M7 next question and returns
    `next_question` in the SAME response (`AnswerOut`), and `kiosk.js submitPatientTurn()` already
    chains it into `assistantSays()`. **Faculty steps 4–8 work today**; only steps 2–3 are manual
    (the two taps in `toggleListening()`). So Req 3 = frontend turn-taking, **no backend change**
    needed for the basic loop.
  - **Seams recorded for the future build:** `tts.js speak(text, {onend})` — the callback already
    exists and is ignored at all 3 kiosk call sites (= "mic starts automatically");
    `interimResults = true` already supplies the silence-timer ticks for auto-endpointing, replacing
    `r.onend = () => { if (listening) r.start(); }`; `stopListening(true)` already submits the turn;
    `activeDock()` means the KIOSK-7 resume dock inherits the change; and the loop is already bounded
    server-side (`followup_max_questions = 5`, `min = 4`, `threshold = 0.7`) — so hands-free cannot
    run forever. That bound is the safety property that makes removing the taps acceptable.
  - **Provenance kept honest:** Reqs 1–2 are the faculty's own pasted text; Req 3 was **relayed as a
    spoken clarification**, so the header marks it "faithful, not literally verbatim".
  - **Cross-references synced (5 spots)** so nothing still reads "two faculty requirements":
    `CLAUDE.md` (status pointer + memory-file item 11), `current_task.md` (menu option 3),
    `session_protocol.md` (the standing start-of-session menu), `codebase_map.md` (tree entry), and
    `context fixed problem 3.0.md` — the last one also gained a **misfiling guard**: "the mic needs
    two taps" is a **Req 3 research item, NOT a 3.0 bug**.
  - **Deliberately NOT touched (history stays honest):** this changelog's S24b entry, **ADR-0042**,
    `context fixed problem 2.0.md`, and `codebase_map.md`'s S24b note all correctly said "two" when
    written. `milestone_log.md` line 42 was checked and left alone (its wording carries no count).
- Decided: **ADR-0047** — Requirement 3 is filed to the **research track** (explicitly NOT the 3.0 bug
  cycle) and scoped as a **client-side turn-taking change, independent of Reqs 1 & 2**, to ship behind
  a `voice_loop = manual | auto` config switch (ADR-0045 pattern: switch in `.env`, old path never
  deleted). Rule #1 framing recorded: an endpointer that clips an answer, or TTS echo captured into a
  `patient` utterance, is a **rule #1 defect — not a UX nit**.
- Broke / problem: none. **No code was touched**, so the 192-test suite is unchanged and was
  deliberately **NOT re-run** this session (there was nothing for it to prove) — the number is carried
  over from S24/S25, not re-verified today.
- Deferred: building any of it. Reqs 1–3 all stay ⬜ NOT STARTED (research track). Still open from
  before: rotating the 3 API keys (pre-demo), formal WER/precision-recall, the TextBee real-SMS demo,
  and the empty 3.0 inbox.
- Next: **HUMAN's choice from the menu** — now with 4 real candidates: (1) rotate the 3 API keys
  (recommended before any public demo), (2) paste manual-testing findings into the 3.0 inbox,
  (3) faculty Reqs 1–3 — **Req 3 step 1 (auto-listen via `speak()`'s existing `onend`) is the
  smallest and most visible starting point**, (4) formal WER / TextBee demo.

## Session 26 — 2026-07-12 — Standing start-of-session "options menu"; confirmed 3.0 tracker intentionally empty (docs-only, no code)
- Did (no code, no tests):
  - **Confirmed the 3.0 tracker is EMPTY by design, not by oversight.** Re-read
    `context fixed problem 3.0.md` — 📥 inbox still "(nothing yet)". In S25 the human reported 0 bugs
    and explicitly said "leave 3.0 empty for now", so there is correctly nothing to file.
  - **Established a standing start-of-session behavior (human's request):** the 5-line orientation
    summary must ALSO surface the open **menu of options** and stress that picking among them is the
    **human's choice** — never assume one. Menu = (1) rotate the 3 API keys (recommended pre-demo),
    (2) paste manual-testing bugs/UX findings → `context fixed problem 3.0.md`, (3) faculty future
    features (`faculty_future_features.md`), (4) formal WER / TextBee demo, (5) anything else.
  - Wired it in three places so it survives: **`current_task.md`** next-step is now that menu with
    the choice framing; **`session_protocol.md`** gained a standing note in its START section; a
    **feedback memory** (`session-start-options-menu`) captures the preference.
- Decided: no new ADR — this is a **session-workflow preference**, not an architecture/design choice
  (ADRs stay reserved for real technical decisions). Captured in session_protocol.md + current_task.md
  + memory instead.
- Broke / problem: none. **192 tests still pass** (no code touched; carried over, unverified this
  session).
- Deferred: the whole menu itself — key rotation, the 3.0 fix cycle, faculty future features, formal
  WER, TextBee demo — all remain the human's to pick from.
- Next: **HUMAN's choice from the menu** (recommended pre-demo default = rotate the 3 API keys,
  `human_live_run_guide.md` PART 3).

## Session 25 — 2026-07-12 — HUMAN LIVE REAL-MIC RUN PASSED (Windows 11); Modules 1–14 → ✅ (docs-only, no code)
- Did (no code, no new tests — recording the human's live-run result):
  - **The human ran the live real-mic test** (`human_live_run_guide.md` PART 2) on **Windows 11 +
    Chrome + real mic**, synthetic data, OTP via the `000000` dev bypass. **TC-V1/V2/V3/F2/R1 all
    PASS.** Observations: STT **very accurate**, latency **≈ 2 s**, TTS **spoke correctly**,
    follow-up questions **good**. **No bugs / UX issues found.**
  - **`test_log.md`**: added the S25 live-run entry (all 5 cases PASS + the qualitative numbers +
    the explicit caveat that this run was qualitative & Windows-only — formal WER/precision-recall
    still to be logged).
  - **`milestone_log.md`**: the human live-voice gate is CLEARED → **Modules 1–14 flipped 🟨 → ✅**
    (M5 stays ⛔ retired; **M15 stays 🟨** = future retrain/regression pipeline). Status board,
    "Last updated", and Phase-0 step-6 marker updated; added the S25 note.
  - **`CLAUDE.md`**: status paragraph → Session 25, live run PASSED, Modules 1–14 ✅.
  - **`current_task.md`**: overwritten — the live run is DONE; next real work = **rotate the 3 API
    keys** (still pending) + optional formal WER/precision-recall as thesis evidence; future issues
    → the 3.0 inbox.
- Decided: **ADR-0046** — on the passed live-voice gate, move the happy-path module board (1–14) to
  ✅ (M5 ⛔, M15 🟨), with a standing caveat that the run was qualitative + Windows-only so formal
  WER/precision-recall is still owed as evidence. The human chose this over the more conservative
  "flip M1 & M7 only" and "change nothing" options.
- Broke / problem: none. **192 tests still pass** (no code touched). Caveat recorded, not a bug: the
  live run was qualitative (no by-hand WER / precision-recall / labeled set) and Windows-only.
- Deferred: rotating the 3 API keys (human, before any public demo); formal WER/precision-recall on
  ~50 samples; the optional TextBee real-SMS demo; everything in `faculty_future_features.md`.
- Next: **rotate the 3 API keys** (`human_live_run_guide.md` PART 3) before showing anyone; then the
  project is demo-ready. Any manual-testing issues found later → `context fixed problem 3.0.md` inbox.

## Session 24b — 2026-07-11 — Docs-only addendum: CLAUDE.md refreshed, 2.0 tracker closed, 3.0 scaffold + faculty future-features file created
- Did (no code, no tests — documentation structure for what comes next):
  - **CLAUDE.md**: stale status paragraph (S14/156 tests/head 0010) → current (S24, both cycles
    complete, real OTP ADR-0045, M16, head 0012, **192 tests**); memory-file list gained items
    10–11 (the two new files below).
  - **`context fixed problem 2.0.md`**: P4-1 flipped to ✅ with the S24 summary; header now says
    the WHOLE 2.0 tracker is complete and points to 3.0 — the file is historical.
  - **NEW `agent_docs/faculty_future_features.md`**: the faculty's two future requirements
    (quantized Moshi medical-summary model; quantized on-device STT/TTS replacing the browser
    APIs) kept VERBATIM + implementation notes mapping each onto existing seams (Req 1 = local
    OpenAI-compatible server as one more provider in `llm_providers.py`, zero pipeline change;
    Req 2 = `stt_provider` setting + Phase-1 WebSocket slot for STT, `tts.js speak()` for TTS,
    latency gates, Banglish-output caveat) + a suggested order (summary → STT → TTS). Research
    track, ⬜ not started, needs the human's "go" + its own plan.
  - **NEW `agent_docs/context fixed problem 3.0.md`**: the next-cycle scaffold, 🕐 EMPTY/waiting —
    encodes the 2.0 workflow: human pastes RAW manual-testing findings into its 📥 inbox → Claude
    triages into a numbered checkable tracker (original words kept verbatim) → human approves the
    plan → ONE item per "go", functional before polish. Carries over the locked rules + the
    baseline (192 tests, head 0012).
  - Consistency touches: `codebase_map.md` agent_docs listing + `current_task.md` next-step now
    name both new files.
- Decided: nothing new — documentation organization only (no ADR; ADR-0045 from S24 stands).
- Broke / problem: none.
- Deferred: everything in `faculty_future_features.md` (explicitly future).
- Next: unchanged — the human live real-mic run; findings → the 3.0 inbox.

## Session 24 — 2026-07-11 — P4-1 real OTP (Alembic 0012, pluggable sender seam, TextBee) — **2.0 TRACKER COMPLETE**; 192 tests
- Did:
  - **OTP channel research (human asked for deep 2026 research first):** a truly FREE SMS-OTP to
    arbitrary BD numbers does not exist — Twilio BD $0.5962/SMS (trial = verified numbers only);
    WhatsApp auth templates ~$0.0113/msg + Meta Business verification; Firebase phone auth is
    Blaze-plan-only (billing card, per-SMS); local BTRC aggregators (sms.bd / Alpha / MiM) are the
    real production route at ~৳0.30–0.40/OTP; Telegram Gateway is $0.01/code but recipients must
    have Telegram; email (Brevo 300/day, Gmail SMTP) is free but verifies the wrong thing. The
    free-AND-real option: **TextBee.dev** (open-source Android-phone SMS gateway, own BD SIM) —
    demo-grade, chosen as the second sender.
  - **Built P4-1 (ADR-0045):** `otp_codes` table (**Alembic 0012**, applied — head 0011→0012) +
    `OtpCode` model; new package `backend/app/services/otp/` (base ABC + `DevLogSender` default +
    `TextBeeSender` via httpx + channel-independent `service.py`); config `OTP_CHANNEL=dev|textbee`,
    `OTP_DEV_BYPASS`, TTL/attempts/cooldown knobs + TextBee creds. Security: salted-SHA-256 hash
    only (plaintext never persisted/audited), 5-min expiry, single-use, constant-time compares,
    5-attempt lockout (429 even for the CORRECT code), 60 s resend throttle (`otp_sent=false` +
    `retry_after_seconds`), undelivered codes voided, random codes can't collide with `000000`.
    The `000000` bypass lives ONLY inside the `otp_channel=="dev"` branch — a test proves it is
    rejected under `textbee` even with `OTP_DEV_BYPASS=true`. `lookup` now really issues+audits
    (`otp_issued`); kiosk UX unchanged (zero frontend edits). `httpx==0.28.1` pinned (now direct).
  - **Fixed a PRE-EXISTING logging bug** found while verifying: `migrations/env.py` ran
    `fileConfig(alembic.ini)` at every startup with default `disable_existing_loggers=True`,
    silencing ALL `uvicorn.*` logs after migrations (entry-point banner, access logs — and the new
    dev-OTP line). Fix: `disable_existing_loggers=False`; DevLogSender logs via `uvicorn.error`
    (same channel as main.py's banner).
  - **Live-verified end to end** on the dev server: 0012 applied at startup → lookup printed
    `[OTP] verification code for +8801766666666: 130303` → wrong code 401 → real code 200 with an
    `in_progress` visit → `000000` still accepted on the dev channel.
- Decided: **ADR-0045** (OTP design: hashed single-use codes behind a pluggable sender seam;
  dev-log default; TextBee = free real-SMS demo channel; BTRC aggregator = future prod sender).
- Broke / problem: nothing in the suite (**192 pass**, was 177; +test_otp.py 13 + 
  test_migration_0012.py 2). The env.py logging bug above was pre-existing, now fixed.
- Deferred: activating `textbee` (human must install the TextBee app on an Android+BD-SIM phone
  and put API key + device id in `.env`); a BTRC-approved aggregator sender for real deployment
  (paid ~৳0.35/OTP — same seam, new subclass).
- Next: **the 2.0 tracker is COMPLETE (STRUCT+P1+P2+P3+P4 all ✅).** Next real work = the human
  live real-mic run (`human_live_run_guide.md`) + key rotation; optional: TextBee real-SMS demo.

## Session 23 — 2026-07-10 — 2.0 build: P2-3 + P3-1..P3-4 (P2 AND P3 CLOSED — Alembic 0011, M16 drug-info assistant); 177 tests
- Did: five tracker items, one per "go":
  - **P2-3 (closes P2):** the medic portal needed NO retint — `frontend_medic/index.html` is fully
    token-based (its one hex `#F4FAF8` is an approved teal tint) and `staff.js` has zero hexes.
    Two real polish fixes, both in `shared.css`: `.card` radius `12px` → `var(--radius)` (10px, the
    ADR-0043 lock — all three portals inherit) and `.verbatim-speaker` made `display:block` + 4px
    gap ("ASSISTANT ASKED" no longer runs into the Bangla question text). Full medic flow
    preview-verified with a stubbed `api` (login → queue → case → Submit & Forward → post-referral
    → EN↔BN), computed styles + screenshots, no console errors.
  - **P3-1 (Alembic 0011):** new nullable `Visit.submitted_at` — stamped in
    `repository_visits.set_visit_status()` on `in_progress → awaiting_review` (mirrors the
    `completed_at` pattern, so `submit_visit` needed no change and the stamp stays synchronous —
    unaffected by the P1-5 background job). Exposed via `VisitOut` (detail + submit response
    inherit) and `DashboardItemOut`/`_to_item`. Frontend: queue rows render
    `dhakaTime(submitted_at || started_at)` (fallback covers pre-0011 rows); the doctor
    patient-details card gains a "Submitted / জমার সময়" row via `dhakaDateTime()`. Migration
    0011 applied to the dev DB (head confirmed; data untouched). New `test_submitted_at.py` (3:
    stamped once + a 2nd submit can't move it · queue+detail expose it · assign/review never
    clobber) + `test_migration_0011.py` (2 DB gates, house style).
  - **P3-2 (verification, NO product-code change):** traced that every doctor-side read is fresh
    (`GET /visits/{uuid}` embeds the live Patient row; /profile + /risk re-query per open) →
    doctor always sees medic edits, including post-referral identity/weight edits. Locked it in
    with `test_doctor_sees_medic_edits.py` (1 end-to-end: field edit + C1 replacement + risk
    override + post-forward vitals/identity PATCH → all visible in the doctor's queue row, visit
    detail, profile [source=human, disclaimer survives], /risk [human tier]). Render side
    preview-verified (মানব-সম্পাদিত badges etc.).
  - **P3-3 (M16 drug-info assistant, ADR-0044):** new `services/assistant.py` (ddgs/DuckDuckGo
    search, top-5 snippets capped at 400 chars → ONE `call_module("M16")` on the Flash bucket),
    `routes_assistant.py` (`POST /api/visits/{uuid}/assistant/drug-info` — visit-scoped because
    `module_events.visit_id` is NOT NULL + audit linkage), `schemas/assistant.py` (disclaimer
    fields REQUIRED in the contract). Disclaimer "AI-generated information. Please verify before
    prescribing." (+Bangla) attached SERVER-side on every answer — never left to the model (rule
    #2); search gets only the doctor's typed question (rule #4). Search fail → sourceless answer;
    non-JSON reply → salvaged; chain dead → 502. Doctor UI: "💊 AI Drug Info" top-nav button +
    teal slide-in panel (always-visible disclaimer bar, Q/A bubbles via textContent ONLY, source
    links, per-answer disclaimer, EN↔BN, hidden in print CSS). Dep: `ddgs==9.14.4` (its `primp`
    ships Windows x64 + manylinux wheels; no separate httpx needed). New `test_assistant.py` (5).
  - **P3-4 (closes P3):** doctor portal was already token-clean (semantic amber/red kept; the
    JS-rendered prescription form has ZERO hex hardcodes — verified in the live DOM). One fix:
    `.safety-panel` radius `12px` → `var(--radius)` in `shared.css` (deferred from P2-3) — the
    LAST radius hardcode; every panel now derives from the ADR-0043 token. Preview-verified incl.
    prescription form (Diagnosis still empty on open — rule #2).
- Decided: **ADR-0044** (M16 assistant design: visit-scoped endpoint, Flash bucket, server-attached
  disclaimer, ddgs-only dep, best-effort search). Everything else implements already-locked ADRs.
- Broke / problem: none. Two preview quirks (not app bugs): the stub must match the prescription
  context path WITH its `?doctor_id=` query; `preview_eval` can mis-read a just-toggled class.
- Deferred: **P4-1 (real OTP) — the ONLY item left**, and it needs the human's CHANNEL decision
  before the sender is built (recommend: dev/log sender + `000000` bypass behind a pluggable seam,
  optionally ONE free reference channel: email-OTP or Telegram-for-opted-in).
- Next: **P4-1** — get the human's OTP channel choice, then build: `OtpCode` table (Alembic 0012),
  expiring code, `000000` universal bypass, pluggable sender seam.

## Session 22 — 2026-07-10 — 2.0 build: P1-6 (kiosk polish, P1 CLOSED) + P2-1 (Dhaka time fixed) + P2-2 (patient demographics); 166 tests
- Did: three tracker items, one per "go":
  - **P1-6 (frontend, closes P1):** retinted the 6 leftover clinical-blue hardcodes in
    `frontend/kiosk.html` inline CSS to Teal Medical (dock transcript, summary icons, highlight
    icon/pill, progress chip, card shadow); the P1-4 amber "needs info" + green complete-chip
    (semantic colors) kept untouched. Verified via computed styles + screenshot — **Priority 1
    (Patient Portal) is now fully CLOSED** (P1-1 through P1-6 all ✅).
  - **P2-1 (frontend, opens P2):** found the ROOT CAUSE of the "random" medic/doctor queue times —
    SQLite serializes timestamps **offset-less** (`2026-07-05T14:03:42.884654`, no `Z`), so the
    browser's bare `new Date()` read them as LOCAL time instead of UTC. New shared helpers in
    `frontend_shared/shared.js`: `parseUtc()` (pins offset-less strings to UTC) + `dhakaTime()` /
    `dhakaDateTime()` (always render `Asia/Dhaka`, bn-BD/en-GB by language) — pure browser `Intl`,
    no backend/tzdata dependency. `frontend_shared/staff.js` `renderQueue` now uses `dhakaTime()` —
    both medic AND doctor queues fixed at once (shared file). Verified with known UTC instants
    (offset-less 06:30→12:30, `18:00Z`→00:00, `+00:00`→06:00, Bangla digits, invalid→"—").
  - **P2-2 (backend + frontend, MEDIC-details spec item):** `Patient.sex`/`birth_year` existed in
    the model but were never written; `display_name` only came from phone-lookup. (a) Extended the
    M3/M8 extraction prompt (human-approved wording) with a `patient_demographics` key — same LLM
    call, zero extra quota. (b) New `apply_demographics()` in `services/intake.py` (called from
    intake AND the M8 answer-merge in `services/profile_update.py`) writes
    `display_name`/`sex`/`birth_year` **FILL-ONLY-WHEN-EMPTY** — a staff-entered value is never
    overwritten by the AI, no schema migration needed. (c) Extended `PATCH /patients/{id}/vitals`
    (`schemas/dashboard.py` + `routes_dashboard.py`) to accept `display_name`/`sex` (pattern-
    validated)/`age_years`; audit now logs only the fields actually sent (fixed a pre-existing test
    that asserted strict-equality on the audit detail dict). (d) Medic post-referral card gets a
    **Gender** row + an "Edit Details" identity editor (name/age/gender, prefilled, same pattern as
    the weight editor); the doctor portal reads the same `Patient` row so it benefits automatically.
    New `test_patient_demographics.py` (4 tests: autofill · never-overwrite-existing ·
    malformed/absent-ignored · staff-PATCH-is-final + 422/400 validation). **166 pass** (was 162).
- Decided: no new ADR — P1-6/P2-1 implement the already-locked ADR-0042/0043; P2-2's
  fill-only-when-empty pattern mirrors the existing `source=human` M8-merge guard, not a new rule.
- Broke / problem: one pre-existing test (`test_medic_summary.py::test_vitals_patch_updates_and_audits`)
  broke on the extended PATCH because the audit detail dict grew 3 always-present `None` keys —
  fixed by auditing only sent fields (better behavior, not a workaround). One dev-server hiccup
  mid-session: `preview_start` tried the Linux launch config (`.venv/bin/python ENOENT` on
  Windows) — resolved by explicitly starting `"backend (FastAPI + uvicorn)"`.
- Deferred: P2-3 (medic UI polish, closes P2), then P3 (doctor: submitted-at, patient-details
  verification, AI chatbot) → P4 (OTP, channel choice still needs the human).
- Next: **P2-3** — Medic Portal UI polish (closes P2): sweep `frontend_medic/index.html` for
  leftover blue hardcodes → teal equivalents; layouts/hooks untouched.

## Session 21 — 2026-07-10 — 2.0 build: P1-5 (Confirm & Submit = instant, assessment in background); 162 tests
- Did: **P1-5** (ADR-0042b, one "go"). `backend/app/api/routes_dashboard.py`:
  `submit_visit()` now keeps only the guards + `status→awaiting_review` + audit **synchronous**
  (the case is in the medic queue the moment the response returns); the up-to-3 LLM round-trips
  (M10 risk + M11 XAI + M10C suggestion) moved into a new **`_post_submit_assessment(engine,
  visit_id)`** FastAPI `BackgroundTasks` job with its OWN session. Seam detail that kept every
  existing test green: the job binds to **`db.get_bind()`** (the request's engine), so prod uses
  the real DB and the tests' overridden in-memory engine exercises the same path — zero fixture
  churn. Job is fire-and-forget (try/except + `logger.exception`); `assess_visit` /
  `suggest_condition` were already idempotent + best-effort. No frontend change needed (the tier
  fills into the staff queues on their 15s refresh; null tier renders "—").
  Tests: new `test_submit_background.py` (3): assessment+XAI+C1 land after submit · a background
  crash never blocks/undoes the submission · **red flag still forces Critical from the background
  with the model down (rule #3)**. **162 pass** (was 159), 6.1 s.
- Decided: no new ADR — this is the implementation of the already-locked ADR-0042(b).
- Broke / problem: none; all submit-dependent suites (staff routes, risk, report/review,
  suggested condition, risk override) passed unchanged thanks to the engine-binding seam.
- Deferred: P1-6 (kiosk polish — the leftover blue tints in kiosk.html inline CSS), then P2→P4.
  Live-run caveat: TestClient runs background tasks synchronously, so the "instant return" is
  proven by design/tests offline — the human live run will see the real wall-clock win.
- Next: **P1-6** — Patient Portal UI polish (closes P1): retint `#EFF6FF`/`#BFDBFE`/`#F1F5F9` in
  `frontend/kiosk.html` to teal equivalents + visual polish; layouts/hooks untouched.

## Session 20 — 2026-07-10 — 2.0 build: P1-3 (4–5 follow-up floor + deepening) + P1-4 (missing-field highlight); 159 tests
- Did: two tracker items, one per "go":
  - **P1-3 (backend — first of the cycle):** the main follow-up loop now always asks **4–5**
    history-grounded questions. (1) `config.py`: `followup_min_questions=4` (cap stays 5).
    (2) `routes_followup.py` `_loop_state()`: "complete" needs the 0.7 threshold **AND** ≥4
    questions asked; cap exit unchanged; `scope=fields` resume loop untouched. (3) M7
    (`services/followup.py`): human-approved broadened `_QUESTION_SYSTEM` — gap-filling first,
    then **DEEPENING** questions grounded in the conversation (severity 1–10, location/spread,
    triggers/relievers, progression, impact, past episodes, family history) when the gap list is
    exhausted (main loop only; fields scope still stops); fixed the `remaining[0]` salvage
    fallbacks that would crash on an empty list. Tests: new `test_followup_min_questions.py`
    (floor-via-deepening incl. non-JSON salvage · cap terminates when floor>cap · fields scope
    unaffected) + 2 existing tests updated to the new spec (`test_followup_loop.py` drives to the
    floor and asserts exactly 4; `test_resume_loop.py` asserts the main loop stays open at 0 asked,
    re-serving the open question). **159 pass** (was 156).
  - **P1-4 (frontend):** kiosk summary — empty REQUIRED fields (the `HIGHLIGHT_FIELDS` set) now get
    `.summary-item.missing` (amber warning border/tint) + a bilingual **"Needs info / তথ্য প্রয়োজন"**
    chip that follows the P1-2 language toggle; optional empties stay muted "Not mentioned".
    Preview-verified (classes, chip EN↔BN, screenshot; no console errors).
- Decided: no new ADR — the 4–5-question floor was already locked in ADR-0042(3); the human
  approved the exact M7 prompt wording in-session before it was coded.
- Broke / problem: none. Note for the live run: every visit now spends ~3 more Groq M7 calls +
  M8 merges than before (still tiny vs the ~1,000/day free tier).
- Deferred: P1-5 (background-assessed submit), P1-6 (kiosk polish — incl. retinting the leftover
  blue tints in kiosk.html inline CSS: #EFF6FF/#BFDBFE/#F1F5F9), then P2→P4.
- Next: **P1-5** — move the 3 blocking LLM calls in `submit_visit` (M10/M11/M10C) into FastAPI
  `BackgroundTasks` so Confirm & Submit returns instantly (status+audit stay synchronous).

## Session 19 — 2026-07-10 — 2.0 build: STRUCT-2/3 + P1-1/P1-2 (logout, teal theme, auto-stop, full i18n)
- Did: executed four tracker items, one per "go", each preview-verified with a stubbed `api`
  (no backend/LLM calls — rule #4):
  - **STRUCT-2 (logout):** shared `logout()` in `frontend_shared/shared.js` + a bilingual Logout
    button in ALL THREE portal headers (medic + doctor + kiosk) → returns to the Portal Directory
    `/`. Verified: button renders, "লগআউট" in Bangla, click lands on `/`, no console errors.
  - **STRUCT-3 (theme):** shared palette evolved to **"Teal Medical"** (ADR-0043) — `:root` tokens
    (primary `#0F766E`, secondary `#0D9488`, bg `#F0FBF8`, radius 10px, teal shadows) + retinted
    the ~10 hardcoded blue tints in `shared.css`; semantic risk-badge colors untouched; CLAUDE.md
    FRONTEND section updated. Human chose Option A (teal) over Option B (ocean blue) from LIVE
    in-browser previews of both on the real medic portal. Verified teal on `/`, kiosk, medic, doctor.
  - **P1-1 (Summary auto-stops mic):** `kiosk.js` — new `submitFinalTurn()` + reworked
    `finishConversation()`: clicking "Done — see summary" now stops the mic, flushes the captured
    words as the final turn (answer path posts `followup/answer` and IGNORES the next question;
    opening path posts the utterance + re-runs intake so the words are extracted), then summarizes.
    `state.finishing` reentry guard. Verified: both flush paths + empty-buffer + triple-click.
  - **P1-2 (full language toggle):** `kiosk.js`/`shared.js`/`kiosk.html` — bubble labels + bilingual
    bodies carry `data-en/bn` so shared `applyLanguage()` re-translates them; new `setBilingualText()`
    keeps JS-written text (OTP subtitle, mic hints) toggle-safe; live transcript mirrored into both
    language slots so a mid-recording toggle can't wipe it; 🔊 tooltips refresh in `onLanguageChange`;
    shared `applyLanguage()` gained `data-en/bn-placeholder` support (+ the 2 fallback inputs).
    **Patient bubbles carry NO dataset — verbatim forever (rule #1)**; server questions (EN+BN in one
    string) left as captured. Verified the exact spec bug ("সহকারী / আপনার সমস্যাটি…" → EN and back)
    plus OTP subtitle, hints, transcript, placeholders — full EN↔BN round-trip.
- Decided: **ADR-0043** — shared palette = "Teal Medical" (Option A, chosen from live previews;
  ADR-0029 structure + semantic risk colors kept).
- Broke / problem: none functional. The preview **screenshot** capturer wedged during P1-2 (tooling
  hiccup; page JS confirmed alive via eval) — used the accessibility snapshot as proof instead.
  **No pytest run this session** (changes were frontend HTML/CSS/JS only); P1-3 will add tests.
- Deferred: P1-3 → P4 (unchanged queue). Per-portal UI polish (P1-6/P2-3/P3-4) still pending on top
  of the shared teal base.
- Next: **P1-3** — force 4–5 intelligent, history-based follow-ups (backend: `followup_min_questions`
  gate in `config.py`/`routes_followup.py` + deepening-question generation in `services/followup.py`
  + a new test; keep the 156-test suite green).

## Session 18 — 2026-07-09 — "Context Fixed Problem 2.0" spec captured + planned; STRUCT-1 done
- Did: (1) Oriented from the session files. (2) The human delivered a NEW work spec —
  `agent_docs/context fixed problem 2.0.md` (UI/UX redesign + functional fixes across all three
  portals, real OTP, and a doctor-side AI drug-info chatbot) plus 3 healthcare reference
  screenshots and a stated priority order. (3) Explored the codebase (frontend portals, backend
  pipeline, OTP/auth) and turned the spec into a priority-sequenced, checkable plan (saved to the
  Claude plan file; the priority checklist is now mirrored in `current_task.md`). Plan APPROVED.
  (3b) Converted `agent_docs/context fixed problem 2.0.md` into a living, checkable **BUILD TRACKER**
  (plan IDs + status + the files each item touches, original requirements kept verbatim below it) so
  any future session sees exactly what's done/left — STRUCT-1 ✅, STRUCT-2 👉 next.
  (4) Implemented **STRUCT-1**: renamed the 4 user-facing "Patient Kiosk" strings → "Patient Portal"
  (EN + Bangla "রোগী পোর্টাল") in `frontend/index.html:41` + `frontend/kiosk.html:6,81,200`;
  file names/URLs (`/kiosk.html`, `/kiosk.js`) kept so routes don't break. No backend touched.
- Decided: **ADR-0042** — approach for the 2.0 build: (a) UI = *evolve the theme* (shift shared
  `:root` tokens toward the teal/modern reference look + polish; KEEP all existing layouts &
  wired features — no 1:1 screenshot copy, no layout rebuild); (b) Confirm & Submit = *assess in
  background* (M10/M11/M10C move to a FastAPI BackgroundTasks job so submit returns instantly);
  (c) execute priority-by-priority, functional fixes before polish, ONE item per "go". The faculty
  "Future Features" (quantized Moshi / quantized STT-TTS) are OUT of scope for this spec.
- Broke / problem: none (STRUCT-1 was a string-only change; not a code path, so no tests run).
- Deferred: everything from STRUCT-2 onward — logout buttons, theme tokens, and all of P1–P4.
  Two items still need a human choice at build time: the exact **OTP delivery channel** (P4 —
  free reliable OTP-to-any-phone is not feasible; recommend persisted-OTP seam + `000000` bypass +
  one free reference channel) and a **look at the teal palette** before it's applied broadly.
- Next: **STRUCT-2** — add a Logout button to the medic + doctor headers that returns to the
  Portal Directory (`/`), plus an optional shared `logout()` in `frontend_shared/shared.js`.

## Session 17 — 2026-07-07 — Quota audit + quota-aware free-provider switching (ADR-0041)
- Did: (1) **API quota audit**: counted all LLM usage from `module_events` (33 lifetime events;
  visit 7 = the clean 13-call Session-8c run; visit 8 on 07-06 = M4 failing) + one read-only
  OpenRouter `GET /api/v1/key` (free tier confirmed, $0 usage). Found the "voice transcribes but
  formatting fails" bug: **Gemini Flash 429s were invisible** (only the LAST provider in the chain
  was logged) and the only fallback was OpenRouter `:free`, which itself 429'd **10× in ~9s** with
  no backoff — while Groq (1,000 free req/day) was never tried. (2) **Fix built (ADR-0041)**:
  `llm_client.py` now logs EVERY attempt to `module_events` (error rows incl. provider + message),
  puts a provider on **cooldown after a 429/quota error** (60s RPM / 15min daily, fail-open when
  all cool down), and `llm_providers.py` gained a universal `FALLBACK_ORDER` = assigned → Groq →
  Cerebras → Mistral → OpenRouter (blank-key buckets auto-skipped; Gemini buckets deliberately not
  cross-fallbacks). New optional free buckets in `config.py`/`.env.example`: **Cerebras**
  (~1M tok/day) and **Mistral Experiment** (trains on inputs — rule #4 warning, off by default).
  New `tests/conftest.py` (autouse cooldown reset) + `test_llm_client.py` (6 tests). **156 pass.**
- Decided: ADR-0041 (quota-aware cooldown + extended free fallback chain). Web research logged:
  Gemini Flash free ≈ 10 RPM / 1,500 RPD (resets midnight PT), Groq ≈ 1,000 RPD, OpenRouter
  `:free` ≈ 50 RPD, Cerebras ≈ 1M tok/day, Mistral ≈ 1B tok/month but 2 RPM + trains on data.
- Broke / problem: none; `test_intake.py::test_fallback_is_used_and_logged` updated for the new
  per-attempt error rows. Root cause of WHY Gemini Flash 429'd on 07-06 still unconfirmed (the
  old code didn't log it) — the new logging will show it on the next live run.
- Deferred: optional Cerebras key signup (human); $10 OpenRouter top-up (optional); everything
  from S16 (live real-mic run, Windows Bangla voice, key rotation, bug/feature list).
- Next: unchanged from S16 — human's bug list + faculty features → numbered spec → plan step 1.

## Session 16 — 2026-07-07 — Arch Linux TTS: installed + VERIFIED working (🔊 + mic confirmed by human)
- Did: finished the Session-15 Arch TTS fix. The human ran `sudo pacman -S speech-dispatcher
  espeak-ng`; I then verified the whole chain. System layer PASS: `espeak-ng --voices` lists `bn`
  (Bengali, `inc/bn`), rendered `আমার মাথা ব্যথা করছে` → valid **81,202-byte WAV** (RIFF PCM 16-bit
  mono 22050 Hz), `spd-say` exit 0. Then debugged why Chromium's `speechSynthesis.getVoices()` was
  **empty `[]`** despite the working synth: (a) the running Chromium (PID 10193) had started
  **before** the packages existed and caches the voice list at process start; (b) the speech-
  dispatcher daemon wasn't up and Chromium's sandbox can't spawn it. Fix: started the daemon and
  **`systemctl --user start speech-dispatcher.socket`** (it was `enabled` but not active) so Chromium
  triggers the daemon via socket activation; then the human **fully quit Chromium** (`pkill chromium`,
  not just a reload — Wayland keeps the process alive) and relaunched with `chromium
  --enable-speech-dispatcher`. Result: **getVoices() non-empty, 🔊 speaks, and the mic works** on
  Arch → **TC-V2 audio PASS on Arch** (human-confirmed). No application code changed.
- Decided: **ADR-0040** — Linux TTS/STT dev setup: `speech-dispatcher` + `espeak-ng`, stay on
  Chromium (do NOT require Google Chrome), rely on the enabled `speech-dispatcher.socket` +
  `--enable-speech-dispatcher`, and a FULL Chromium restart after install.
- Broke / problem: none now. (Prior blocker — empty `getVoices()` — was a stale pre-install
  Chromium process + no running daemon; both resolved.) Voice is espeak-ng-robotic (expected).
- Deferred: the full human **live real-mic run** (TC-V1 WER/latency, TC-V3 voice-only loop, TC-F2,
  TC-R1, TC-A1) + Windows Bangla voice + key rotation — all still pending. **The human also flagged
  (a) some bugs to fix next and (b) possible new features per faculty requirements** — NOT yet
  enumerated; next session must collect that list first and plan it one step per "go".
- Next: get the human's bug list + faculty requirements, turn them into a numbered spec (like
  `context_fixed_problem.md`), and plan step 1.

## Session 15 — 2026-07-07 — Arch Linux TTS fix: diagnosed + documented (PART 1B)
- Did: chased down why the kiosk 🔊 button is **silent on the Arch laptop**. Read-only
  diagnostics confirmed it is **system-level, not a code bug**: `speech-dispatcher` and
  `espeak-ng` are **not installed** and the speechd service is inactive, so Linux Chromium's
  `speechSynthesis.getVoices()` is empty and `frontend_shared/tts.js` correctly degrades to
  text-only (ADR-0028). The existing `human_live_run_guide.md` only covered the **Windows**
  Bangla-voice install. Added a new **"🐧 PART 1B — Enable a Bangla voice on Arch Linux"**
  section right after the Windows PART 1: `sudo pacman -S speech-dispatcher espeak-ng`,
  `espeak-ng --voices | grep bn` + `spd-say` verification, "fully restart Chromium", the same
  `getVoices().filter(bn)` console check + "hint banner gone = ✅" success test, and a note that
  the espeak-ng Bengali voice is robotic (expected; text stays primary) and STT is unaffected.
  **No application code changed** — `_pickBanglaVoice()`/`banglaVoiceAvailable()` already match
  any `bn*` voice, so they start working once the packages exist.
- Decided: nothing at ADR level — this is a docs/system-setup step, not an architecture choice.
  Confirmed scope with the human: **TTS only** (their mic/STT works), and **stay on Chromium**
  (do NOT switch to Google Chrome).
- Broke / problem: the `pacman` install needs `sudo` and could not be run from the non-interactive
  agent shell, so the fix is **documented but NOT yet installed/verified** on the Arch box.
- Deferred: the human runs the one `pacman` line, then verify (espeak-ng bn voice + `spd-say`
  audible → Chromium `getVoices` non-empty → kiosk `#voice-hint` gone + 🔊 speaks = TC-V2 on Arch).
  Everything from S14 still pending too (the full live real-mic run + Windows Bangla voice + key rotation).
- Next: human installs `speech-dispatcher`+`espeak-ng`, then I verify the three checks above.

## Session 14 — 2026-07-07 — Step 20 of 20 (FINAL): test gate + status flips + doc sweep — BUILD COMPLETE
- Did: closed the 20-step fix/feature build. Re-ran the gate — `pytest backend/tests/` = **150
  passed**. Flipped all stale markers in `context_fixed_problem.md` to ✅ (its "Last updated" was
  2026-07-05, predating S11/S13): **KIOSK-4/5/6/7** (S11 steps 8–11; KIOSK-7 = ADR-0034),
  **MEDIC-1/2/5** (S11 step 12) + **MEDIC-3** (S11 step 13, ADR-0035), **DOCTOR-3** (S13 step 17),
  **DOCTOR-4/5** (S13 step 18, ADR-0038), **DOCTOR-6** (S13 step 19, ADR-0039), and **DOCTOR-7**
  🟨→✅ (S13 steps 17–19) — each with a one-line "Done" note; added a "BUILD COMPLETE" banner +
  refreshed the header date/ADR list. Every numbered spec item is now ✅ (no ⬜/🟨 left except the
  legend). Marked the 20-step build complete in `milestone_log.md` while **deliberately keeping the
  15-module status table 🟨** (those gate on the human live-voice run, not build completion).
  `test_log.md` got a one-line S14 gate entry. Also (same session): wrote a plain-language
  **`agent_docs/human_live_run_guide.md`** for the human — start-the-app, install a Bangla TTS
  voice on Windows, the live-test walkthrough (each step mapped to TC-V1/V2/V3/F2/R1), and
  key rotation (which key → which `.env` line → where to get a fresh one). Refreshed the stale
  **`CLAUDE.md`** status line (was "Session 8 / Alembic 0009 / 104 tests" → now Session 14 /
  Alembic 0010 / 150 tests / build complete, pointing at the new guide).
- Decided: nothing new — step 20 is a sweep, no ADR (ADR-0031–0039 already cover the build).
- Broke / problem: none. Docs-only; no application code, DB, or patient data touched.
- Deferred: NOT build work — the **human live real-mic run** (TC-V2/V3/F2/R1/A1, real keys already
  in `.env`) and installing a Bangla TTS voice on the Windows box (kiosk audio). Any polish the
  live run surfaces.
- Next: hand off to the human live run; there is no further coded step in the 20-step plan.

## Session 13 — 2026-07-06 — Steps 17–19 of 20: DOCTOR-3 patient-details · DOCTOR-4/5 prescription form · DOCTOR-6 prescription .docx + save
- Did (step 19, DOCTOR-6, ADR-0039): the prescription **Submit** now saves + downloads.
  New `render_prescription(payload)` in `services/documents/visit_docx.py` (LOCAL .docx:
  letterhead · patient · symptoms · **Diagnosis verbatim from payload** · medicines table ·
  advice/tests/follow-up · signature) and `generate_prescription_document()` in
  `services/documents/__init__.py` (render → store → `create_document(kind="prescription")` →
  persist a `prescriptions` row linked by `document_id`). New endpoint
  `POST /api/visits/{uuid}/prescription` (body `{doctor_id, payload}`; 404 visit/doctor, 400
  non-doctor; audit `prescription.created`; returns `{prescription_id, document}`). A **new**
  prescription + docx per Submit (append). Frontend: `submitPrescription()` POSTs, auto-downloads
  the .docx (anchor-click, like the medic), and shows a "✅ Saved & Downloaded" confirmation with a
  re-download link (the step-18 preview fn removed). The .docx writer reads ONLY the payload, so
  the Diagnosis is structurally un-AI-fillable (rule #2) — regression-tested. New
  `test_prescription_docx.py` (5). **150 tests pass** (145 + 5). Verified live: real POST created a
  prescription row + linked document, downloaded the .docx and confirmed it contains the diagnosis,
  medicine, clinic, patient; frontend Submit wiring checked with a stubbed POST (body/auto-download/
  confirmation), no console errors.
- Did (step 18, DOCTOR-4/5, ADR-0038): a **Prescription form** in the doctor portal.
  Backend (small, read-only): `GET /api/visits/{uuid}/prescription/context?doctor_id=`
  (new `routes_prescription.py` + `schemas/prescription.py`) returns **letterhead only**
  (clinic + doctor); 404 unknown visit/doctor, 400 non-doctor. Patient + the 10 symptoms
  are assembled client-side from the already-loaded case (no re-send). An idempotent
  `seed_demo_letterhead()` (new `backend/app/db/seed.py`, run in `lifespan`) fills the NULL
  letterhead columns on the demo clinic + doctors with sample values (never clobbers a real
  value). New `test_prescription_context.py` (6). **No prescription is persisted in step 18**
  — the DB row + .docx are created together at Submit in step 19 (DOCTOR-6). Frontend
  (`frontend_doctor/index.html`): "📝 Write Prescription" in the review bar opens a full-screen
  `#prescription-screen` form — letterhead (editable, prefilled) · Date · Patient
  (auto-filled) · Symptoms (auto-filled from `summary_fields`) · **Diagnosis EMPTY, doctor-
  authored, never AI-filled (rule #2)** · Medicines table with **add/remove rows** · Advice ·
  Tests · Follow-up · signature line. `rxDraft` state survives the EN↔বাংলা toggle;
  `collectPrescriptionPayload()` assembles the payload (empty medicine rows filtered);
  Submit shows an inline preview (the .docx/download replaces it in step 19). **145 tests
  pass** (139 + 6). Browser-verified (stubbed context): full autofill, empty Diagnosis,
  add/remove + language-toggle persistence, ≥1-row guard, payload correct, no console errors,
  screenshot of the rendered form.
- Did (step 17, DOCTOR-3, frontend-only, `frontend_doctor/index.html`): the doctor case
  view now shows — right after the safety panel — a **Patient Details card** (Name · Phone ·
  Age-from-`birth_year` · Gender · Weight · Blood Pressure) reading the patient embedded in
  `GET /visits/{uuid}` (`VisitDetailWithPatientOut`), with **inline weight + BP editing** that
  reuses `PATCH /patients/{id}/vitals` (already permits role=doctor — **zero backend change**);
  a mounted **`#condition-card`** so the shared `renderConditionCard()` surfaces the C1 AI
  suggestion + reasoning + "not a diagnosis" disclaimer (identical to the medic — closes part of
  DOCTOR-7); and the **C2 display band** (`tierBand()`) beside the risk tier badge in
  `renderSafety()`. New page functions: `onDoctorCaseLoaded()` (renders patient details then
  loads risk — replaces `loadRisk` as the `PORTAL.onCaseLoaded` hook), `renderPatientDetails()`,
  `saveVitals()` (weight range + ≥1-field validation), `genderLabel()`; `onLanguageChange()`
  re-renders the patient card. Bilingual throughout; raw verbatim + patient name are never
  translated (rule #1). **139 tests still pass** (no backend touched). Browser-verified with
  stubbed network: all 6 fields correct, band renders "HIGH 51–75%", condition card + disclaimer,
  EN↔বাংলা toggle, edit fires `PATCH /api/patients/42/vitals` body `{editor_id, weight_kg, bp}`
  and updates the card, empty/invalid-weight guards block the call, no console errors, screenshot
  confirms the layout order (safety → patient → condition).
- Decided: **ADR-0038** (step 18, form + read-only letterhead prefill; save deferred) +
  **ADR-0039** (step 19, dedicated `POST …/prescription` saves row + renders .docx; new
  prescription per Submit; Diagnosis structurally un-AI-fillable). Step 17 needed no ADR
  (reuses C1/ADR-0036, C2 band, ADR-0037).
- Broke / problem: none. The preview server stopped between edits twice (restarted cleanly);
  `preview_screenshot` worked this session. Note: the startup letterhead seed only runs on
  server (re)start.
- Deferred: Step 20 (final): full `pytest` sweep + doc sweep + flip the `context_fixed_problem`
  DOCTOR-3/4/5/6/7 (+ any still-open KIOSK/MEDIC/STRUCT) statuses to done; sanity-eyeball all
  three portals. The whole 20-step build then closes.
- Next: Step 20 — final test + doc sweep + `context_fixed_problem` status flips. See `current_task.md`.

## Session 12 — 2026-07-06 — Steps 14–16 of 20: C1 suggested condition (MEDIC-4) + post-referral summary & docx (MEDIC-6/7) + doctor toggle/polish (DOCTOR-1/2/7)
- Did: **Step 14 (MEDIC-4/C1, ADR-0036):** new module **M10C** (Flash bucket, deliberately a
  SEPARATE call from M10 so the risk prompt's no-disease-names rule is never contaminated)
  generates a bilingual "Possible Condition (AI Suggestion – Not a Diagnosis)" + reasoning at
  kiosk submit, best-effort (LLM down → no suggestion, submit never blocked). Stored at
  `case_profiles.entities["suggested_condition"]` (no migration) with 10-field-style provenance
  AND the "not a diagnosis" disclaimers embedded IN the object — every payload carrying the
  suggestion carries them. `PATCH /visits/{uuid}/profile/condition` staff edit (403 non-staff,
  all language slots untranslated, disclaimer re-attached server-side, audit `profile.condition_edit`).
  Shared `renderConditionCard()` in staff.js; medic mounts `#condition-card`; kiosk has no mount.
  New `test_suggested_condition.py` (5). **Step 15 (MEDIC-6/7):** "Submit & Forward" now lands on
  a bilingual post-referral summary (snapshot-as-referred): patient card (name/phone/age-from-
  birth-year/**weight inline-edit**/BP), risk tier + C2 band + flags + XAI, the disclaimered
  condition, all 10 Q&A rows, ⬇ Download Report (.docx) + Back to Queue. New
  `PATCH /patients/{id}/vitals` (staff-only, 0–500 kg validated, audit `patient.vitals_edit`);
  `GET /visits/{uuid}` now embeds the patient with vitals (`VisitDetailWithPatientOut`, defined in
  patient.py to avoid a schema import cycle). M12 report sections gain vitals +
  `suggested_condition`; the summary_report docx renders the C1 block with both disclaimers; and
  the docx is assembled from a **FRESH report at download time** — staleness after staff
  edits/overrides was the hidden "download doesn't really work" failure. New
  `test_medic_summary.py` (5, incl. the staleness regression). **Step 16 (DOCTOR-1/2/7):** doctor
  portal fully bilingual (EN/বাংলা toggle, data-en/bn on all chrome, safety panel re-renders from
  state via `renderSafety()`, placeholders switch); **↻ Queue removed** (auto-refresh + post-review
  reload already cover it; the medic's Refresh-Queue stays — it clears the phone filter);
  `@media print` block (case content prints, chrome doesn't); responsive flex-wrap.
  **139 tests pass** (129 + 5 + 5). All frontend steps browser-verified with stubbed network.
- Decided: ADR-0036 (C1 = separate M10C call; embedded disclaimer; staff-only; never the doctor's
  Diagnosis field); ADR-0037 (post-referral summary = snapshot + fresh-report-on-download +
  patient embedded in visit detail + patient-scoped vitals PATCH).
- Broke / problem: `preview_screenshot` worked early in the session then timed out again
  (S11 flakiness) — post-referral screen + doctor toggle proven via eval + a11y snapshot;
  worth a human eyeball of `/medic/` after a forward and `/doctor/` in বাংলা (Ctrl+F5 first).
- Deferred: Steps 17–20 (one per "go"): DOCTOR-3 patient-details card (17, mounts the shared
  condition card + vitals from the now-embedded patient) · prescription form (18, Diagnosis
  defaults EMPTY — rule #2, per ADR-0036) · prescription docx + save (19) · final sweep (20).
  DOCTOR-7 stays 🟨 until 17–19 land its remaining identification targets.
- Next: Step 17 — DOCTOR-3: patient-details card in the doctor portal. See `current_task.md`.

## Session 11 — 2026-07-06 — Steps 8–13 of 20: kiosk summary complete (KIOSK-4/5/6/7) + medic bilingual/polish/refresh (MEDIC-1/2/5) + risk override (MEDIC-3)
- Did: **Step 8 (KIOSK-4):** bilingual "Download Raw Transcript (.docx)" button on the kiosk
  summary screen (before Confirm & Submit), wired to the existing step-3 endpoint via a
  temporary-anchor click (kiosk page never navigates away); no backend change.
  **Step 9 (KIOSK-5):** summary redesigned — each of the 10 fields is its own card (18px
  radius, backdrop blur, soft shadow, icon chip 🩺⏱️📋🤒📖💊⚠️🔄🩹💬, bold primary-blue
  titles); clinically key fields (main problem, duration, symptom details, medicines,
  allergies) get a left accent border + value badge; empty = muted-italic "Not mentioned /
  উল্লেখ করা হয়নি"; clinical-blue tokens only. **Step 10 (KIOSK-6):** summary follows the
  language toggle end-to-end — `renderSummary()` reads via `fieldValue()`, profile kept as
  `state.lastProfile`, `onLanguageChange()` re-renders; legacy `{value}` rows display as-is.
  **Step 11 (KIOSK-7, ADR-0034):** resume loop live — `?scope=fields` on `followup/next`
  + `followup/answer` (no 0.7-threshold gate; missing = empty summary-field keys via new
  `missing_summary_fields()`; `target_gap` forced to a real field key so "নেই/জানি না"
  is never re-asked; SHARED per-visit question cap). Kiosk: progress chip ("৮/১০ তথ্য
  সম্পন্ন"), resume voice dock on the summary screen (one recognition engine serves both
  docks via `activeDock()`), Confirm & Submit hidden while a question is open, summary
  regenerates after every answer, FAIL-OPEN (cap/API-error → submit returns; never trap
  the patient). New `test_resume_loop.py` (5 tests). **Step 12 (MEDIC-1/2/5):** staff.js
  fully bilingual (labels+icons, badges, verbatim chrome via t(); values via fieldValue();
  new `staffLanguageRefresh()`), medic portal gets the EN/বাংলা toggle + data-en/bn on all
  static text; "↻ Queue" → "↻ Refresh Queue / তালিকা রিফ্রেশ" (clears the phone filter +
  reloads — its one clear job); field-card icon chips + queue hover in shared.css; doctor
  portal (shares staff.js) regression-checked. **Step 13 (MEDIC-3, ADR-0035):**
  `POST /api/visits/{uuid}/risk/override` — appends a `model_provider='human'`
  risk_assessments row (AI rows never edited), carries red_flags + rule_overrode forward,
  stores a reason (constitution), audit_logs from/to/reason; **red-flag Critical cannot be
  downgraded by staff (409)** — only the doctor decides at review. Medic risk panel: tier
  badge + C2 display band + AI/Human badge + red flags + XAI + override select (labels
  from TIER_LABELS, band per tier) + reason box. New `test_risk_override.py` (3 tests).
  **129 tests pass** (121 + 5 + 3). All frontend steps browser-verified with stubbed
  network (no live LLM spend).
- Decided: ADR-0034 (resume loop = `?scope=fields` on the existing endpoints; shared
  question cap; asked-once = answered); ADR-0035 (risk override = appended human row, no
  migration; red-flag-Critical downgrade blocked for staff).
- Broke / problem: `preview_screenshot` tool times out this session (page itself healthy —
  all assertions via eval/a11y snapshot); the step-9 visual is worth a human eyeball at
  /kiosk.html (Ctrl+F5 first).
- Deferred: Steps 14–20 (one per "go"): C1 suggested condition (14) · post-referral
  summary + docx (15) · doctor toggle+polish (16) · patient-details card (17) ·
  prescription form (18) · prescription docx + save (19) · final sweep (20). Real-M7
  resume-loop questions over Groq untested by design — covered by the next live-mic run.
- Next: Step 14 — MEDIC-4 / C1: "Possible Condition (AI Suggestion – Not a Diagnosis)"
  section (clearly labeled, disclaimer, editable; doctor's Diagnosis never AI-filled —
  needs its own ADR per the locked C1 note). See `current_task.md`.

## Session 10 — 2026-07-06 — Fix/feature build continues: steps 6–7 (KIOSK-1 OTP + KIOSK-2/3 TTS UX)
- Did: **Step 6 DONE (KIOSK-1):** `frontend/kiosk.js` gains `initOtpInputs()` — typing a
  digit auto-focuses the next `.otp-input` (repeated digits like 000000 flow smoothly),
  non-digits are stripped, Backspace on an empty box clears + focuses the previous one,
  and pasting fills the boxes from box 1 (junk stripped, e.g. "code: 04-73-92" → 047392;
  short pastes focus the next empty box). `kiosk.html` boxes gain `inputmode="numeric"`
  + `autocomplete="one-time-code"`. All 5 behaviors asserted live in Chrome + screenshot.
  **Step 7 DONE (KIOSK-2/3):** (a) ROOT CAUSE of "Repeat Question does nothing" found and
  CONFIRMED live: the button always fired — **this Windows machine has NO Bangla TTS voice**
  (`banglaVoiceAvailable() === false`), so speech was silently absent (TC-V2, recorded in
  test_log.md). Fix = make the state visible: a bilingual `#voice-hint` banner shows on the
  voice screen whenever no bn voice exists (chained onto tts.js's `onvoiceschanged`, not
  replacing it); on-screen text stays the fallback (ADR-0028). (b) `addBubble()` now puts a
  🔊 icon on EVERY chat bubble — assistant icon replays that question; patient icon reads
  back EXACTLY the words captured at bubble creation (rule #1, never re-fetched/rewritten).
  The Repeat-Question button is KEPT alongside the icons (KIOSK-2 and KIOSK-3 are separate
  spec items; the button is also the accessibility-friendly big target). Browser-verified
  via a `speak()` spy: both icons + the repeat button speak the exact right text; hint
  toggles correctly both ways. **121 tests pass** (frontend-only; no backend change).
- Decided: nothing new (no ADR — bug fix + spec'd UI; the keep-the-repeat-button call is
  recorded here).
- Broke / problem: Browser CACHE bit twice — a stale kiosk.js made the first verification
  round of step 6 report false failures. Rule for preview checks: `fetch(url,
  {cache:'reload'})` + reload BEFORE asserting. The human should Ctrl+F5 the kiosk once.
- Deferred: Steps 8–20 (one per "go"). Installing a Bangla TTS voice on the Windows box
  (Settings → Time & Language → Speech → Add voices → Bengali) so TC-V2 can PASS with
  audio — human action, worth doing before the re-run.
- Next: Step 8 — kiosk "Download Raw Transcript (.docx)" button wired to the step-3
  endpoint `POST /api/visits/{uuid}/documents/transcript` (KIOSK-4). See `current_task.md`.

## Session 9 — 2026-07-05 — Fix/feature build from the human's Part-2 test: steps 1–5 of 20
- Did: The human's real-mic Part-2 run surfaced bugs + feature gaps, written up as
  `agent_docs/context_fixed_problem.md` (stable IDs: STRUCT/KIOSK/MEDIC/DOCTOR). A 20-step
  sequenced plan was approved with all open decisions resolved: C1 = "Possible Condition
  (AI Suggestion – Not a Diagnosis)" allowed with disclaimer + editable, doctor's Diagnosis
  never AI-filled; C2 = display-only tier→band mapping, NO stored numeric risk scores;
  legacy → `/legacy/` + `/` landing page; prescriptions/reports DB-backed (documents.visit_id
  + kinds + prescriptions table, Alembic 0010); bilingual summary values generated once and
  stored (`value_bn`/`value_en`, back-compat with `{value}`); clinic/doctor letterhead in DB;
  KIOSK-7 = resume loop asking only missing fields, cap respected, "নেই/জানি না" accepted.
  **Step 1 DONE (STRUCT-1/2, ADR-0031):** legacy demo `git mv`-ed to `frontend_legacy/`
  (asset refs made relative), mounted at `/legacy/`; new clinical-blue landing page at `/`
  linking all four entry points; `ENTRY_POINTS` list logged at startup; new
  `test_routes_static.py` (5 tests). **Step 2 DONE (ADR-0032):** Alembic rev
  `0010_prescriptions_letterhead` written AND applied to the real DB (backup
  `prescreener.db.pre-0010.bak`): `documents.utterance_id` now nullable (visit-grain
  exports), `patients.weight_kg`+`bp`, users/clinics letterhead columns, new
  `prescriptions` table (payload JSON, document_id link). Discovery that shrank the step:
  `documents.visit_id` already existed since 0003 and `patients` already had
  `birth_year`/`sex` — no duplicates added. Models updated (+`Prescription`); new
  `test_migration_0010.py` (4 tests incl. rule-#1 raw-preservation across the rebuild).
  architecture.md gained §8 (rev-0010 deltas). **Step 3 DONE:** visit-grain docx seam —
  new `services/documents/visit_docx.py` (full-visit RAW transcript writer, verbatim
  role-labeled turns; staff summary-report writer rendering the stored M12 sections with
  bilingual field labels + red flags + disclaimer), `generate_visit_document()` orchestrator
  (documents row: `visit_id` set, `utterance_id` NULL), `create_document` repo + DocumentOut
  schema extended (both grains), new route `POST /api/visits/{uuid}/documents/{kind}`
  (`routes_visit_documents.py`; download reuses `/api/documents/{id}/download`). New
  `test_visit_documents.py` (3 tests: byte-exact raw turns, field labels/values/disclaimer,
  route guards). **Step 4 DONE:** `shared.js` gains `fieldValue(field)` (bilingual summary
  values: picks `value_bn`/`value_en` by the active language, falls back cross-language,
  then to the legacy `{value}` shape, then ''; display-only, never writes back) and the C2
  `TIER_BANDS` map + `tierBand(tier)` (fixed display-only percentage band per tier — no
  numeric score generated/stored/wired). Verified live in the browser preview (all shapes +
  fallbacks + bands correct, zero console errors). **Step 5 DONE (ADR-0033):** M3/M8 now
  emit BOTH `value_en` + `value_bn` per field in ONE extraction call ({"en","bn"} reply
  shape; plain-string replies salvaged as English); stored shape `{value, value_en,
  value_bn, source, ...}` with `value` mirroring `value_en` so every legacy consumer/row
  works; M9 `field_has_text()` counts any slot; staff PATCH edits write the typed text to
  ALL slots untranslated (authoritative, no quota); `visit_docx._field_value()` falls back
  across slots. Test fakes updated + new `test_bilingual_fields.py` (5 back-compat tests)
  + a staff-PATCH slot assertion. **121 tests pass** (104 + 5 + 4 + 3 + 5).
- Decided: ADR-0031 (legacy isolation + landing page + startup URL log); ADR-0032 (rev 0010:
  one documents table with two grains, DB letterhead, prescriptions payload as JSON,
  human-only Diagnosis per C1, no stored risk scores per C2); ADR-0033 (bilingual values:
  one extraction call fills en+bn, `value` mirrors value_en, staff edits fill all slots
  untranslated).
- Broke / problem: Nothing. Note: legacy `index.html` used absolute `/styles.css`+`/app.js` —
  would have 404'd under `/legacy/`; caught before shipping, made relative.
- Deferred: Steps 6–20 (kiosk fixes KIOSK-1..7, medic MEDIC-1..7, doctor DOCTOR-1..7,
  final doc sweep) — one approved step at a time. Note: values stored by OLD intake runs
  stay English-only until re-extracted; new runs are bilingual.
- Next: Step 6 — kiosk OTP auto-advance + Backspace + paste (KIOSK-1). See
  `current_task.md`.

## Session 8c — 2026-07-03 — Live-run Part 1 PASSED: full pipeline live with real keys, all three buckets verified
- Did: (A) Added the human-provided **GROQ_API_KEY + OPENROUTER_API_KEY** to `backend/.env`
  (Gemini untouched) — the Session-8b key gap is CLOSED. (B) Ran **live-run Part 1** end-to-end
  with SYNTHETIC typed Banglish (no mic): phone lookup → stub OTP → visit → 2 utterances →
  `/intake` → follow-up loop (2 real Bangla questions from Groq, loop exited at completeness
  0.7) → `/assess` (tier=medium, no red flags — correct for headache+mild fever) → `/report`.
  (C) Verified `module_events`: **13 rows, all status=ok, ZERO fallbacks** — M3/M8=
  gemini_flash_lite, M4/M10/M11=gemini_flash, M6/M7=groq, M12=local — exactly the ADR-0026
  bucket map, live. Latencies 484–8577 ms. (D) `pytest backend/tests/` still **104 passing**.
  Numbers in test_log.md.
- Decided: nothing new (this executes the existing plan; no ADR).
- Broke / problem: Only a cosmetic Windows console issue: printing Bangla from a driver script
  needs `PYTHONIOENCODING=utf-8` (cp1252 UnicodeEncodeError) — not a code bug, backend unaffected.
  Note: the keys were pasted in chat; `.env` is gitignored so the repo is safe, but rotate the
  keys before any public demo.
- Deferred: **Part 2 — the human real-mic kiosk run** (TC-V1/V2/V3/F2/R1 + a live TC-A1
  pull-a-key test) — inherently the human's job. Then `.docx` per-visit report export, optional
  PDF, Phase-1 faster-whisper. Still: ~50 samples + WER, real SMS OTP/auth, encryption at rest.
- Next: Human does Part 2 in Chrome (`/kiosk.html` → speak → follow-ups → submit → `/medic/` →
  forward → `/doctor/` → review) and records TC-V2/V3/F2/R1/A1 in test_log.md. See
  `current_task.md`.

## Session 8b — 2026-07-03 — ADR-0029 doc rewrite executed + FIRST live Gemini verification
- Did: (A) Executed the deferred **ADR-0029 design-system switch in the docs**: CLAUDE.md's
  frontend section now points at the clinical-blue system (`frontend_shared/shared.css`) as the
  source of truth (with the TIER_LABELS rule + Noto Sans Bengali + the read-only-raw rule) and its
  status/stack lines updated; `DESIGN-mintlify.md` got a **SUPERSEDED banner** at the top (ADR-0029)
  with a compact clinical-blue token summary, keeping the old Mintlify analysis only as historical
  reference. (B) Ran the **first-ever LIVE LLM call** in the project: one real Gemini correction on
  synthetic Banglish — see test_log.md.
- Decided: nothing new (ADR-0029/0030 already stand; this executes them).
- Broke / problem: **Live-run gap surfaced, not a code bug:** only `GEMINI_API_KEY` is set;
  `GROQ_API_KEY` and `OPENROUTER_API_KEY` are EMPTY. Since M6 (gaps) + M7 (follow-up) are assigned
  to the Groq bucket with OpenRouter as the only fallback, a FULL live intake/loop cannot complete
  until a Groq OR OpenRouter key is added. All of it passes offline (LLM faked) — purely a missing
  key, not a code issue.
- Deferred: The full live pipeline (blocked on a Groq/OpenRouter key) and the human mic test
  (I cannot operate a real microphone — the voice portion is inherently the human's part).
- Next: Add a Groq (or OpenRouter) key to `backend/.env`, then run a full live pipeline with
  synthetic typed text; separately, the human does the real-voice kiosk run in Chrome. Record
  TC-V2/V3/F2/R1/A1. See `current_task.md`.

## Session 8 — 2026-07-03 — Mockup reconciliation + FULL-STACK BUILD: DB 0003–0009, backend M3–M12 pipeline, three portals
- Did: The biggest build session so far. (A) **Reconciliation:** reconciled `mockups-redesign.html`
  against architecture.md → new `agent_docs/reconciliation.md` + architecture.md §7. Human decided:
  'medic' is a real role; OTP is a stub; the mockup's clinical-blue design system replaces Mintlify
  (ADR-0029). (B) **Database:** Alembic revs **0003–0009 all written AND applied** to the real DB
  (backup .bak per rev): clinics/users/patients/visits (+'medic' role, 'awaiting_doctor' status,
  `assigned_doctor_id` — ADR-0030), case_profiles, module_events, followup_questions,
  risk_assessments, xai_explanations, reports, doctor_reviews, feedback, audit_log. Legacy
  utterances backfilled onto synthetic closed visits; seeds: 1 clinic, 1 medic, 2 doctors, 1 admin.
  (C) **Backend:** visits API + phone lookup + stub OTP (`DEV_OTP`); LLM provider registry +
  fallback + module_events logging (ADR-0026 as data); intake M3→M4→M6 writing the enforced
  10-field `summary_fields` JSON; follow-up loop M7 (Groq, no repeats, question stored + spoken)
  → M8 (merge; human edits never overwritten) → M9 (LOCAL completeness, threshold/max-turn exit);
  **M10 risk with the LOCAL red-flag rule list (5 categories, Bangla/Banglish/English) that forces
  Critical and survives total LLM outage** + M11 XAI (deterministic fallback reason); local M12
  report (Red Flags section + no-diagnosis disclaimer); staff endpoints (submit→auto-assess,
  dashboard queues, field-edit PATCH, assign); doctor review (accept/override→'reviewed') +
  feedback; audit rows on every state change. (D) **Frontend:** `frontend_shared/` (clinical-blue
  CSS, TIER_LABELS, EN/BN helper, tts.js `speak()` — Step A1 shipped), patient kiosk at
  `/kiosk.html` (phone→OTP→voice chat with STT bn-BD + TTS→10-field summary→submit→auto-logout),
  medic portal `/medic/`, doctor portal `/doctor/`. Old Module-1 app at `/` untouched.
- Decided: ADR-0029 (mockup clinical-blue design system supersedes Mintlify) and ADR-0030
  (medic role, `assigned_doctor_id`, 'awaiting_doctor', stub OTP, 10-field JSON shape, tier
  display labels, OTP-typing clarification) — both written to decisions.md mid-session.
  Implementation choices: M12 report assembly is LOCAL (no quota); model failure in M10 degrades
  to 'medium', never 'low' (rule #3); each legacy utterance = its own closed visit.
- Broke / problem: (1) Found + FIXED a pre-existing crash: this Windows machine's DB was a
  MIXED-state legacy DB (had `stt_provider`, lacked `documents.kind`) — the old blind
  stamp-at-0001 died with 'duplicate column'; `database.py` now picks the stamp revision from the
  ACTUAL columns (regression-tested). (2) alembic wasn't installed in the Windows venv (S6 ran on
  Arch) — installed from requirements.txt. (3) Batch-mode FKs need explicit names (0003 fixed).
- Deferred: Real SMS OTP, real auth (still stubbed), PDF export, per-visit report .docx export,
  Postgres (G7 = config), Phase 1 faster-whisper. CLAUDE.md + DESIGN doc rewrite per ADR-0029
  (awaiting explicit go). LIVE end-to-end run with real Gemini/Groq calls — the human's manual
  check (quota). Still from S4–S6: live mic test + ~50 samples + WER/latency.
- Next: Human live test in Chrome (`/kiosk.html` → speak → follow-ups → submit → `/medic/` →
  forward → `/doctor/` → review), with real keys in backend/.env; record TC-V2/V3/F2/R1/A1
  results + Bangla-voice availability per OS in test_log.md. Then the ADR-0029 doc rewrite.
  See `current_task.md`.

## Session 7 — 2026-06-25 — Architect planning lock: flowchart + final stack + per-module API strategy + voice model
- Did: A planning-only session (NO code). Locked the FINAL project plan ahead of vibe-coding.
  (A) **Flowchart:** removed the standalone Emergency module from the Patient Journey diagram —
  deleted node `D1` ("Emergency Detected?"), node `AX` (escalation alert), the `M4→D1`, `D1→No→M6`,
  `D1→Yes→AX` and the dashed `AX→` continuation arrows; added a direct `M4→M6` arrow; dropped the
  now-unused `DECA`, `ALTB`, `RA` styles and the "Emergency" legend entry. Reconstructed the whole
  TikZ source into `update_system_flowchart.md` (the original file was NOT in the uploaded set —
  marked as a reconstruction to diff against the real one). (B) **Safety preserved:** folded a
  lightweight **rule-based red-flag check into Module 10 (Risk Assessment)** that forces the
  **Critical** tier for clearly life-threatening symptoms, with a **Red Flags** section in the M12
  report; revised constitution rule #3 from "emergency detection runs first" to "surface red flags;
  never reassure falsely". (C) **Stack:** CONFIRMED the existing stack (no rewrite) and **added
  browser TTS** for M7 + a deploy path. (D) **API strategy:** assigned each LLM module across three
  independent free quota buckets (Gemini Flash / Gemini Flash-Lite / Groq) with OpenRouter `:free`
  as universal fallback. (E) **Voice:** patient input is **voice-only**; M7 questions show as **text
  AND play as audio (TTS) simultaneously**; manual text box demoted to a mic-failure fallback.
  (F) Rewrote the tracking docs (CLAUDE.md, constitution.md, Context, decisions.md, changelog.md,
  current_task.md, milestone_log.md, test_log.md, codebase_map.md; session_protocol.md unchanged).
- Decided: ADR-0024 (retire Emergency module, fold red-flag check into M10, keep numbering with an
  M5 gap), ADR-0025 (confirm stack + add browser TTS + deploy path), ADR-0026 (per-module free-API
  assignment, refines ADR-0003), ADR-0027 (voice model: STT `bn-BD` + `SpeechSynthesis` TTS,
  voice-only patient replies, manual text = fallback), ADR-0028 (follow-up = on-screen text AND
  spoken audio simultaneously).
- Broke / problem: Nothing built, so nothing broke. **Open conflict flagged, not silently resolved:**
  removing the Emergency module contradicts the *original* non-negotiable rule #3 and the Module
  10/12 dependency columns — this is a SAFETY-relevant change for a medical tool, so it is recorded
  as Open Flag 1 (recommended default: keep the rule-based red-flag check in M10, which is how the
  files are now written). `update_system_flowchart.md` is a reconstruction — node positions / exact
  fill colours are best-effort and must be diffed against the real file before committing.
- Deferred: Building any of the new modules (M2–M15) — still Phase 0. The actual M7 TTS code, the
  per-module provider config wiring, and the OpenRouter $10 top-up decision. Still deferred from
  S4/S5/S6: the human live mic test + ~50 samples + WER/latency on real speech.
- Next: First coding task = **Phase A / Step A1** of the build plan — add browser **TTS** to the
  existing frontend (speak a test Bangla string via `speechSynthesis`, on-screen text stays as
  fallback), planned-then-approved per CLAUDE.md before any code. See `current_task.md`.

## Session 6 — 2026-06-21 — Two separate raw/corrected .docx + Alembic migration (fix stt_provider bug)
- Did: (A) FIXED the live `sqlite3.OperationalError: table utterances has no column named
  stt_provider` by adopting **Alembic**. New `backend/alembic.ini` + `backend/migrations/`
  (env.py reads the URL from app settings, `render_as_batch=True` for SQLite) with two
  revisions: `0001_baseline` (original schema) and `0002` (adds `utterances.stt_provider` +
  `documents.kind`). `init_db()` now runs `run_migrations()` — stamps the baseline on a
  legacy DB, then `upgrade head`; fresh DBs build from scratch; re-runs no-op. Verified on
  the REAL db (2 rows preserved) + a fresh db; backed up the pre-migration db to
  `backend/data/prescreener.db.pre-alembic.bak`. (B) Split document export into TWO separate,
  independently downloadable files: added `documents.kind` ("raw"|"corrected"; legacy
  "combined"); `DocumentWriter.render(utterance, *, kind)` → DocxWriter renders raw-only
  ("Transcript") or corrected-only ("Corrected Transcript"); `generate_session_document(kind=…)`;
  repo `create_document(kind=…)` + `get_latest_document`. New routes (kept `/api/*`):
  `GET /api/transcripts/{id}` (TranscriptDetailOut: raw+corrected text + both doc links),
  `POST /api/transcripts/{id}/documents/raw`, `…/documents/corrected`; `/api/correct` now
  best-effort generates the CORRECTED doc and returns the detail. (C) Frontend: raw is now
  saved + a raw .docx generated when recording STOPS (not only on Correct); added per-panel
  "Download Raw/Corrected .docx" buttons (enabled when each file exists), loading states
  (Saving…/Generating document…/Correcting text…), and the exact spec error strings.
  (D) Config: added `STT_PROVIDER` + `DOCUMENT_OUTPUT_PATH` (alias of DOCUMENTS_DIR) +
  documented `DATABASE_URL`; updated `.env.example` and `.env`. Added a `backend-linux`
  launch.json config (the existing one is Windows-only `.venv/Scripts/python.exe`).
- Decided: Alembic + auto-migrate-at-startup with legacy baseline-stamp (ADR-0022); raw and
  corrected exported as SEPARATE docs via a `documents.kind` column, dedicated documents
  table kept over flat path columns, `/api/*` prefix kept (ADR-0023, decided with the human).
- Broke / problem: One real issue surfaced at END of session — `preview_start` failed with
  `spawn .venv/Scripts/python.exe ENOENT`: the DEFAULT `.claude/launch.json` config uses the
  WINDOWS venv path, which doesn't exist on Arch. Workaround: launch the new `backend-linux`
  config (`.venv/bin/python`) explicitly — that starts cleanly (earlier this session the
  server ran fine that way). NOT yet OS-robust (no single launch.json default works on both
  machines; the preview panel picks the first config). Test gotchas fixed during dev:
  TestClient runs sync endpoints in a threadpool, so the route test needed `StaticPool` to
  share the in-memory SQLite across threads; the preview screenshot tool timed out (renderer),
  but functional verification via preview_eval was conclusive. A synthetic session #3 raw doc
  was created in the dev DB during verification (harmless; gitignored, like S5's session #5).
- Deferred: LIVE Gemini correction in-browser + opening both .docx in Word/LibreOffice to
  confirm Bangla renders (human's manual check — not auto-run to save free quota). PDF /
  Markdown writers (format seam ready), version-history UI, auth, cloud storage, Patient/Visit
  tables. Still deferred from S4/S5: the human live mic test + ~50 samples + WER/latency.
- Next: Human live test in Chrome — record → Stop (raw .docx auto-saves + downloads) →
  Correct (corrected .docx) → open both, confirm Bangla renders + RAW unchanged; collect
  samples. See `current_task.md`.

## Session 5 — 2026-06-21 — Auto-generate & store .docx per session + Saved Documents UI
- Did: Added automatic Word-document export for completed sessions (additive, nothing
  existing broken). New `Document` SQLAlchemy model (UUID PK, FK → Utterance, format,
  filename, rel_path, created_at) + repo `create_document`/`get_document`/
  `list_documents`. New `services/documents/` layer: `DocumentWriter` ABC, `DocxWriter`
  (python-docx; renders Raw verbatim + Corrected + metadata; Bengali font set on Latin
  AND complex-script slots), `storage.py` filesystem abstraction (S3-swappable), and a
  `build_writer()` seam + `generate_session_document()` orchestrator. New routes
  `GET /api/documents` (list) and `GET /api/documents/{id}/download` (FileResponse, Word
  media type). `/api/correct` now best-effort generates the .docx after a successful
  correction (a docx failure logs but never fails the correction). Added `documents_dir`
  config (env-overridable, default `backend/data/documents`, no hardcoded paths) and
  `python-docx==1.1.2` to requirements.txt. Frontend: "Saved documents (.docx)" panel
  (Mintlify-styled) listing docs with download links, auto-refreshed after correction.
- Decided: A `.docx` is a DERIVED export artifact; the DB stays the source of truth
  (regenerable, preserves rule #1, avoids Bangla round-trip loss). python-docx (pure
  Python, cross-platform). Filesystem storage now, behind a swappable interface.
  Document grain = one Utterance/session; NO Patient/Visit tables yet. DOCX now, PDF
  later (clean `format` seam). (ADR-0021.)
- Broke / problem: Nothing broke. Note: passing a multi-line python `-c` with Bangla
  string literals through PowerShell mangled the quotes — used a temp script file
  instead (deleted after). Port-8000 orphaned-socket workaround (port 8001) still stands.
- Deferred: PDF generation + in-browser preview; Patient/Visit data model; auth on the
  document routes; cloud (S3/MinIO) storage. All have seams left in place. Still
  deferred from S4: the human live mic test + ~50 samples + WER/latency.
- Next: Human live test — record/correct in Chrome, confirm a .docx auto-saves and
  downloads + opens correctly (Bangla renders), alongside the mic/sample collection.

## Session 4 — 2026-06-20 — Simplify to browser-only STT + Mintlify UI + scrollable panels
- Did: (A) REMOVED the multi-provider STT architecture per the human's new plan —
  deleted `backend/app/services/stt/`, `api/routes_stt.py`, `test_stt_registry.py`,
  the three `requirements-*.txt`, all STT config + the `.env` STT block,
  `python-multipart`, and the startup health log. Recreated the venv from
  requirements.txt (clean core: fastapi 0.115.6, starlette 0.41.3; torch/
  transformers/qwen gone). Module 1 STT is now ONLY the browser Web Speech API.
  Rewrote the frontend for continuous recording: no cap, append-only verbatim
  transcript, brief pauses keep going (restart on `onend`), auto-stop after ~10s
  of silence. (B) Restyled the whole frontend to `DESIGN-mintlify.md` (Inter font,
  black pill buttons, mint-green accent for Start + active, 12px cards, hairline
  borders) and made the 3 transcript panels (Raw/Corrected/Manual) fixed-height,
  scrollable, with stick-to-bottom auto-scroll. Added the Frontend/Transcript-UI
  rules to CLAUDE.md.
- Decided: Browser Web Speech API is the only Module 1 STT (others return later);
  keep a clean seam (the `stt_provider` column stays). Drop the banglaspeech2text
  package permanently. Frontend follows DESIGN-mintlify.md. (ADR-0019, ADR-0020.)
- Broke / problem: A previous session left an ORPHANED socket holding port 8000
  (process dead, leaked handle keeps it LISTENING; clears on reboot). Worked around
  by switching `.claude/launch.json` to **port 8001**.
- Deferred: Live mic test of the continuous-recording + 10s-silence behavior (the
  human's manual check in Chrome). Collecting ~50 samples + WER/latency. Switching
  launch.json back to 8000 after a reboot. Regenerating the (now-removed) Groq key
  is moot since Groq STT was removed.
- Next: Human does the live mic test (speak, pause briefly, then go silent ~10s to
  confirm auto-stop) and collects samples. See `current_task.md`.

## Session 3 — 2026-06-19 — Multi-provider STT (5 providers) + provider health + installs
- Did: Re-planned Phase 0 to support 5 swappable STT providers with frontend
  switching. Built `backend/app/services/stt/` (STTProvider ABC + ProviderInfo
  health + registry + audio.py decode + 5 providers: browser_webspeech,
  groq_whisper, local_whisper, banglaspeech2text, qwen_asr). Added endpoints
  `GET /api/stt/providers`, `POST /api/transcribe`, `POST /api/transcripts`;
  refactored `/api/correct` to correct by utterance_id; added `Utterance.stt_provider`.
  Rewrote the frontend (provider dropdown + status badges, Start/Stop, MM:SS timer
  with 5-min auto-stop, raw/corrected copy+clear, manual fallback, error banner).
  Added a startup STT health log. Then FIXED 5 issues the human reported: documented
  QWEN_ASR_MODEL_DIR (optional, auto-download); rich provider health
  (available/missing_api_key/missing_package/missing_model/unsupported_platform/error)
  shown in the UI; resolved the huggingface-hub dependency conflict; split installs
  into per-provider requirements files; wrote INSTALL.md. INSTALLED all engines and
  verified the local transcribe paths.
- Decided: Drop the unmaintained `banglaspeech2text` pip package (pins
  huggingface-hub==0.11.1) and run shhossain/whisper-*-bn via `transformers`
  instead. Per-provider optional requirements files. Server STT = record→upload→
  transcribe; browser stays live. (ADR-0015 to ADR-0018.)
- Broke / problem: `requirements-local.txt` had a real conflict (fixed by the split).
  `torch==2.5.1` pin had no Python-3.14 wheel → unpinned (got torch 2.12.1).
  `qwen-asr` is INVASIVE: it bumped fastapi 0.115→0.137, starlette→1.3, transformers
  5→4.57, huggingface_hub→0.36 and pulled gradio/flask. App still works (13 tests
  pass, server boots) but Qwen may warrant its own venv.
- Deferred: Live Groq STT test (would spend the human's free quota). Qwen live run
  (3.4 GB download + very slow on CPU) — installed/ready but unverified. WER/latency
  on real Bangla speech. Regenerating the exposed Groq key (human action).
- Next: Human runs the live mic test for each provider in Chrome, collects ~50
  samples, and records real latency/WER. See `current_task.md`.

## Session 2 — 2026-06-19 — Phase 0 Steps 3–5: correction service + API + frontend
- Did: Built the correction service (Step 3): `services/correction/base.py`
  (`Corrector` ABC) + `openai_compatible.py` (`OpenAICompatibleCorrector` +
  `build_corrector()` + strict prompt + manual `__main__` live check) and
  `test_corrector.py` (4 offline guards). Built the API (Step 4):
  `schemas/transcript.py`, `api/routes_transcripts.py` (`POST /api/correct`,
  `GET /api/transcripts`), and `main.py` (lifespan `init_db`, `/health`, serves
  frontend or a placeholder). Built the frontend (Step 5): `frontend/index.html`,
  `app.js` (Web Speech API bn-BD, interim grey / final verbatim), `styles.css`.
  Fixed `.claude/launch.json` to use the venv Python. Ran the server via the
  preview tool and verified the page renders with no console errors.
- Decided: `POST /api/correct` persists RAW *before* calling the LLM, so raw
  survives a correction failure (502 with raw kept); misconfig fails fast (500).
  Recorded as ADR-0013.
- Broke / problem: `launch.json` first used system `python` (no uvicorn) → fixed to
  `.venv/Scripts/python.exe` (Windows-specific; Arch needs `.venv/bin/python`).
- Deferred: Live Gemini call NOT auto-run (spends free-tier quota) — left as a
  manual check for the human. No automated test for `/api/correct` (would hit the
  network). Groq/OpenRouter still interface-only. Frontend = plain HTML/JS (React later).
- Next: Step 6 — human runs the end-to-end live mic test in Chrome on both
  machines and collects ~50 sample utterances. See `current_task.md`.

## Session 1 — 2026-06-19 — Phase 0 scaffolding + backend skeleton (Steps 1–2)
- Did: Approved the Phase 0 plan, then built the foundation (not a throwaway
  demo folder): `requirements.txt`, `.gitignore`, `backend/.env` + `.env.example`,
  and the backend skeleton — `backend/app/core/config.py` (pydantic-settings),
  `backend/app/db/` (database.py, models.py `Utterance`, repository.py), and
  `backend/tests/test_raw_immutable.py`. Installed deps in `.venv` and ran tests.
- Decided: Build the real `backend/` + `frontend/` structure now (foundation for
  the full app); SQLite via a repository layer; one FastAPI server serving the
  frontend; mic + manual-text fallback; correction via the OpenAI-compatible
  client pointed at Gemini (swappable). Recorded as ADR-0009 to ADR-0011.
- Broke / problem: Pinned `SQLAlchemy==2.0.36` crashed on Python 3.14.4
  (typing-union `__getitem__` bug). Fixed by upgrading to `2.0.51` and re-pinning.
- Deferred: Gemini code + the actual network call, API routes, frontend
  (Steps 3–5). Groq/OpenRouter fallback (interface only). The human still needs to
  REGENERATE the pasted Gemini key and put it in `backend/.env`.
- Next: Step 3 — correction service (`Corrector` ABC + `OpenAICompatibleCorrector`
  with the strict correct-only prompt). See `current_task.md`.

## Session 0 — 2026-06-18 — Project setup & memory system
- Did: Created the project memory system: `CLAUDE.md` plus `agent_docs/`
  (constitution, milestone_log, current_task, changelog, test_log, decisions,
  codebase_map, session_protocol). No code yet.
- Decided: Locked in the starting stack and key choices — recorded as
  ADR-0001 to ADR-0008 in `decisions.md`.
- Broke / problem: None (nothing built yet).
- Deferred: All actual coding. AMD-GPU acceleration deferred (CPU-only first).
  Real Bangla-fine-tuned model deferred to Phase 2.
- Next: Build the Phase 0 demo (browser Web Speech API live Bangla transcription
  + free-LLM correction). Plan it with the human before coding.
  See `current_task.md`.
