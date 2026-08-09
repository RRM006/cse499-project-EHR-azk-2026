# current_task.md — What We Are Doing RIGHT NOW

> This is a small, throwaway snapshot. It gets **overwritten** every session.
> It is NOT a history log (that is `changelog.md`). It answers only:
> "If I open a brand-new Claude Code session, what do I need to know to continue?"

---

**Date:** 2026-08-09 (Session 31 end)
**Phase:** 3.0 fix cycle — **the Edge STT terminal-error defect is FIXED and CLOSED.** The tree is now
**entering a faculty-demo feature cycle**: the human has opened a feature-planning workflow but has
**not yet given the features**. Test suite: **324 pass, 1 skipped** (the skip is the opt-in `TTS_LIVE=1`
network test, which passes when run). Alembic head: **0012** — no schema change; do not create a migration.

---

## 🚦 THE NEXT STEP — **wait for the human's faculty-demo feature list. Do NOT assume a single feature.**

The human ended S31 by pasting a **feature-planning workflow** (STEP 1 read context → STEP 2 collect and
classify requests → STEP 3 prioritised plan → STEP 4 wait for "GO" → STEP 5 implement → STEP 6 docs →
STEP 7 demo-readiness report). **The message contained the workflow but no features.** The S31 context
summary (STEP 1) was delivered. **STEP 2 has no content yet.**

**So the next session's job is:** receive the feature requests (they may arrive in messy Bangla or
English), and for EACH one classify it as **NEW FEATURE · CHANGE EXISTING · REMOVE · UI/UX · BUG FIX ·
FACULTY-DEMO REQUIREMENT · FUTURE/OUT OF SCOPE**, then state: what it currently does · what they want
changed · which files/modules are affected · risks and dependencies · whether it is needed before the
demo. Then a **P0 / P1 / P2** plan. **Then STOP and wait for "GO".**

The human's standing rules for this cycle, in their words: *do not assume desired features · do not
implement before approval · no unrelated improvements · do not rewrite working code for style · preserve
the voice/STT behaviour that already passed live testing · treat this as a working system being extended,
not rebuilt.* **If a request conflicts with an existing ADR, STOP and explain the conflict before
changing architecture.**

---

## ✅ What S31 shipped (settled — do not redo or re-derive)

### The Edge STT terminal-error fix — `frontend/kiosk.js` ONLY
`r.onerror` now looks up a **`TERMINAL_STT_ERRORS`** map instead of testing two codes by hand:

```js
r.onerror = (e) => {
  const message = TERMINAL_STT_ERRORS[e.error];
  if (!message) return;   // transient (no-speech / aborted): onend restarts, as before
  showError(t(message.en, message.bn));
  stopListening(false);   // sets listening = false — this is what breaks the restart loop
  setInputMode('type');
};
```

**Terminal:** `not-allowed`, `audio-capture`, `network`, `service-not-allowed`, `language-not-supported`.
**Transient (absent from the map, and they MUST stay absent):** `no-speech`, `aborted`, `bad-grammar`.

⚠ **THE SUBTLETY THAT MUST SURVIVE EVERY FUTURE EDIT.** `no-speech` fires constantly during a normal
pause and `aborted` fires on our OWN `stop()` at the end of every turn. Their restart via `onend` **IS**
what keeps continuous listening alive in Chrome and is part of the passed S29 live run. **A blanket "stop
on any error" would regress Chrome and clip patients mid-answer (a rule #1 defect).** `r.onend` was
deliberately left untouched — the fix works by flipping `listening`, not by teaching the restart about
error codes, and `test_the_onend_restart_itself_is_unchanged` pins exactly that.

**Three messages, not one** (a deliberate deviation from the S30 proposal, flagged to the human —
**they have not responded, so it stands**): `MIC_UNAVAILABLE` (mic/permission), `STT_SERVICE_UNAVAILABLE`
(`network` / `service-not-allowed`), `STT_LANGUAGE_UNSUPPORTED` (Bangla rejected). A dead speech SERVICE
is not a dead MIC, and at a demo those need different responses. Reverting to one generic message is a
3-line change if the human prefers it.

**Tests:** new `backend/tests/test_kiosk_stt_errors.py` (6) → suite **318 → 324**. It **extracts the
shipped map's keys out of the served `kiosk.js`** (the S30 precedent) rather than substring-matching a
comment. **No existing test was touched, weakened or deleted.**

**Live-verified in a real browser engine, no mic and no permission prompt needed** (build a recognizer,
call `onerror` directly): `no-speech`/`aborted`/`bad-grammar` → `listening` stays **true** ✅;
`network`/`service-not-allowed`/`not-allowed`/`audio-capture` → **false**, loop broken ✅; `inputMode`
flipped to `'type'`; the banner showed the right bilingual message.

---

## ⚠ Open gaps / honest caveats (carry these forward)

- **🔴 A RULE #1 DECISION IS WAITING FOR THE HUMAN — mid-turn word loss.** `stopListening(false)`
  (`kiosk.js:576`) discards `finalBuffer`, so a terminal error landing **mid-turn** — a wifi blip giving
  `network` after the patient has already spoken — **throws their captured words away instead of
  submitting them.** Pre-existing (already true for `not-allowed`/`audio-capture`), but S31 widened the
  set of codes that reach it. Left alone on purpose: the fate of a half-spoken answer is a **rule #1
  call, not a drive-by change** (same family as the deferred repeat-while-listening item). Cheap fix if
  wanted: when `endingTurn` is true, submit what we have instead of dropping it.
- **❗ THE HUMAN END-TO-END TEST STILL HAS NOT HAPPENED.** **Nobody has HEARD TTS-1 or TTS-2, and nobody
  has run STT in Edge.** Everything since S29 is proven by tests plus non-audio browser probes only.
  The pending run must cover **Chrome AND Edge**. Short version:
  1. Restart the server (config changes need it):
     `.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --port 8001`
  2. Chrome → `http://localhost:8001/kiosk.html` → **Ctrl+Shift+R** (a stale `tts.js` invalidates the test).
  3. Bangla session, then an English session. Judge: **(a)** one question = one language, no English
     tail; **(b)** the Bangla voice sounds human, not robotic; **(c)** the screen still shows BOTH
     languages; **(d)** mic timing / countdown / transcript unchanged from the S29 PASS.
  4. **Then repeat in Edge** — watch for: does Bangla STT produce any text at all, and do the **last
     words of a long answer survive** (the `FLUSH_GRACE_MS` question)?
  5. If the voice is wrong it is a `.env` swap, not code: `TTS_EDGE_VOICE_BN=bn-BD-PradeepNeural` (male),
     or `TTS_PROVIDER=espeak` to go back offline. **Restart after either.**
- **Edge Bangla STT service support is still UNPROVEN** (API surface only). S31 makes a rejection
  **visible and recoverable**; it does **not** prove which failure occurs, or that Bangla works.
- **`FLUSH_GRACE_MS = 600`** (`kiosk.js:372`) is Chrome-calibrated by its own comment. **UNVERIFIED on
  Edge — a suspicion, NOT a bug.** Do not change it blindly; the live run answers it.
- **⚠ Demo warning (secure-context rule).** The Web Speech API and the mic require a **secure context**.
  `http://localhost:8001` qualifies; demoing over LAN (`http://192.168.x.x:8001`) **blocks both**. Use
  localhost on the demo machine, or HTTPS.
- **Naturalness is NOT proven** for TTS-2, and TTS-1 has not been heard. Measured: bytes, MIME, ~0.8 s
  latency, playback complete at 3013 ms. Not measured: how any of it sounds.
- **⚠ Rule #4 / thesis:** M7 questions are derived from patient speech and **now go to Microsoft**
  (ADR-0050). Accepted deliberately (the Web Speech API already sends the patient's *actual audio* to
  Google), but **it limits what the thesis may claim about privacy.** `TTS_PROVIDER=espeak` reverts it.
- **The kiosk needs internet for the good voice.** Without it the fallback speaks robotically — by
  design, not a bug.
- **Steps S5–S7 of Requirement 3 are NOT built.** S5 = no-speech re-prompt (10 s → repeat once → 10 s →
  offer typing), the 120 s answer cap, mic-permission + `visibilitychange` recovery, **and the deferred
  repeat-while-listening echo gap**. S6 = KIOSK-7 resume dock re-verify. S7 = docs + the 12-point live
  run. (S31 removed the *silent* half of the Edge dead end; S5 would add the re-prompt half.)
- **Deferred since S25:** tapping "Repeat question" while the mic is ALREADY open plays TTS into a live
  recognizer. Closing it means deciding the fate of the half-spoken buffer — a **rule #1 decision**.
- `askAloud`'s safety-net timeout is still sized from the **full** bilingual text, so it over-waits
  slightly. **Deliberate and test-pinned:** over-waiting is harmless, opening the mic early is a rule #1
  defect.
- The Web Speech API opens its **own** audio stream, so `echoCancellation` **cannot** be passed. Echo
  protection is structural gating only — the ceiling until Requirement 2.
- **`ttsSpeaking()` — not `speechSynthesis.speaking` — must remain the echo-guard predicate** (ADR-0049).
  A network provider adds ~0.8 s of in-flight time that `<audio>` alone cannot report. Reverting it
  reopens a rule #1 echo hole.
- **Stale docs, still not fixed (needs a "go"):** `human_live_run_guide.md:19` ("use Chrome, not Edge")
  and `:72` (the now-disproven "Edge may expose `bn-BD` voices"). **`CLAUDE.md`** in three places — its
  status paragraph still describes S28/234 tests, *"TTS for M7 audio: browser Web Speech API — no
  server, no key"* is two ADRs out of date, and it says Python 3.14 while the venv is **3.13.3**.
- **Rotating the 3 API keys is STILL NOT DONE** (`GEMINI_API_KEY` / `GROQ_API_KEY` /
  `OPENROUTER_API_KEY`) — recommended before any public demo. **HUMAN step — I must never handle keys.**
- **A uvicorn was left running on port 8001** at the end of S31 (started via the preview tooling), with
  `kiosk.html` loaded. A second one may still exist on **8000** from S30. **Alembic stays at 0012.**

## The standing menu (still the human's call)
1. **Give the faculty-demo feature list** ← **THIS IS WHAT THE HUMAN SAID THEY WOULD DO NEXT.**
2. **The combined Chrome + Edge live listen / STT run** — closes the 3.0 cycle and is the only thing that
   can validate the voice stack before faculty see it.
3. **Decide the mid-turn word-loss question** above (rule #1).
4. **Step S5** of Requirement 3.
5. **Rotate the 3 API keys** — human-only step.
6. **Fix the stale docs** — `human_live_run_guide.md` and `CLAUDE.md`.
7. **Faculty Reqs 1 & 2** (quantized summary model; quantized on-device STT/TTS — `facebook/mms-tts-ben`
   drops into the ADR-0049 seam as one subclass). Or formal WER / the TextBee real-SMS demo.

## Locked decisions — do NOT re-open
- **S31 (no ADR, deliberately):** the terminal/transient split **implements ADR-0048**'s existing
  requirement that a patient is never blocked by a failed mic; it decides nothing new, so it got no ADR.
  Do not "tidy" it into stopping on every error — see the subtlety above.
- **ADR-0051 (S30, Accepted):** TTS speaks only the UI-language half; stored and displayed text keep the
  FULL bilingual string. The split lives at the single entry point (`speak()`), covers BOTH providers,
  and must never migrate into the recording or display path.
- **ADR-0050 (S30, Accepted):** `edge-tts` is the default provider; espeak-ng is demoted, not deleted,
  and is the automatic fallback. The rule #4 privacy cost was accepted explicitly. **edge-tts is
  LGPL-3.0**; **`facebook/mms-tts-ben` is CC-BY-NC-4.0** (non-commercial only). Its **option 3 is
  disproven** — Edge exposes no Bengali browser voice. Do not re-litigate on the old "binary aiohttp dep".
- **ADR-0049 (S29, Accepted):** the server-side TTS provider seam; **supersedes ADR-0040's rejection of
  server-side TTS**. Browser voice still WINS when present. Failure is loud (503 / `speak()` returns
  false), never silent.
- **ADR-0048 (S28):** voice-first + typing always available; supersedes ADR-0027's voice-only rule. The
  3 s countdown **is** the silence window and is a **confirmation window, never a hard cutoff**; ONE
  answer pipeline (`source: mic|manual`); frontend tests = **static-source assertions only** (S30/S31
  keep that, with one narrow exception: a shipped literal may be extracted and executed).
- **ADR-0047 / 0046 / 0045 / 0042–0044 / 0040** — see `decisions.md`.

## Reminders (the four non-negotiables)
- **Rule #1:** raw words are never edited/translated. **Live-verified clean in S29** and preserved
  through S30's two TTS fixes and S31's error fix — none of them changed what is stored or displayed.
  ⚠ The one open rule #1 question is the mid-turn buffer discard above.
- **Rule #2:** the system never diagnoses — M16 disclaimer server-attached; Diagnosis doctor-only.
- **Rule #3:** red flags are ADD-only — the local rule still forces Critical with every LLM down.
- **Rule #4:** synthetic/consented data only in dev. **M7 question text now leaves the machine** for
  Microsoft (ADR-0050) — a deliberate, recorded trade-off, reversible with `TTS_PROVIDER=espeak`.
- Run (Windows): `.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --port 8001`
- Run (Arch):    `.venv/bin/python -m uvicorn backend.app.main:app --reload --port 8001`
  **`.env` changes need a RESTART** (this includes every `TTS_*` knob). NEVER delete the DB.
- Tests: `pytest backend/tests/` (**324 passing, 1 skipped** as of S31). Windows: `PYTHONIOENCODING=utf-8`.
  Add `TTS_LIVE=1` to also run the real-network TTS test.
