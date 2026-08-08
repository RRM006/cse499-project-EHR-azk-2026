# current_task.md — What We Are Doing RIGHT NOW

> This is a small, throwaway snapshot. It gets **overwritten** every session.
> It is NOT a history log (that is `changelog.md`). It answers only:
> "If I open a brand-new Claude Code session, what do I need to know to continue?"

---

**Date:** 2026-08-08 (Session 30 end)
**Phase:** 3.0 fix cycle — **TTS-1 (ADR-0051) and TTS-2 (ADR-0050) are both IMPLEMENTED.** The session
ended with an **Edge browser-compatibility verification**, which found **one real defect that is NOT yet
fixed**. Test suite: **318 pass, 1 skipped** (the skip is the opt-in `TTS_LIVE=1` network test, which
passes when run). Alembic head: **0012** — no schema change; do not create a migration.

## ⛔ STATE OF THE TREE — read this first
**NOTHING HAS BEEN CHANGED SINCE THE EDGE VERIFICATION.** The Edge work was **inspection only**: no
production code, no tests, and no behaviour were modified after TTS-2 shipped. The uncommitted working
tree is exactly the TTS-1 + TTS-2 work plus this session's documentation. The proposed Edge fix below is
**NOT IMPLEMENTED** — it is a proposal awaiting the human's "go".

---

## 🚦 THE NEXT STEP (recommended) — the Edge STT **terminal-error** fix. NOT IMPLEMENTED.

### The defect (real, confirmed by reading the code — not speculation)
`frontend/kiosk.js:499` handles only **2 of the 8** Web Speech API error codes:

```js
r.onerror = (e) => {
  if (e.error === 'not-allowed' || e.error === 'audio-capture') { … stopListening(false); setInputMode('type'); }
};
```

Unhandled: **`language-not-supported`** (exactly what Edge emits if its speech backend rejects
`bn-BD`), **`network`**, **`service-not-allowed`**, `bad-grammar`. For any of these `listening` stays
`true`, and `kiosk.js:491` then runs:

```js
r.onend = () => { … if (listening) try { r.start(); } catch (_) {} };
```

→ **`start → error → end → start` forever.** The patient sees a mic that looks live but gets **no error
message, no switch to typing, and no countdown** (S4 arms only after real words are captured). **S5,
which would catch the silence, is NOT built.** So on Edge a `bn-BD` rejection is a *silent dead end*
that also spins CPU and hammers the speech service.

### The proposed minimal fix (~6 lines, ONE handler, one file)
```js
const TERMINAL_STT_ERRORS = ['not-allowed', 'audio-capture', 'network',
                             'service-not-allowed', 'language-not-supported'];

r.onerror = (e) => {
  if (!TERMINAL_STT_ERRORS.includes(e.error)) return;   // no-speech / aborted: keep going
  showError(t('Microphone unavailable — you can type instead.',
              'মাইক্রোফোন পাওয়া যায়নি — টাইপ করতে পারেন।'));
  stopListening(false);
  setInputMode('type');
};
```

⚠ **THE SUBTLETY THAT MAKES THIS NON-TRIVIAL — do not "simplify" it away.** `no-speech` and `aborted`
**must keep restarting**: that restart IS what keeps continuous listening alive in Chrome and is part of
the S29 live-run PASS. A blanket "stop on any error" would **regress Chrome**. Terminal vs transient is
the whole point of the fix. `stopListening(false)` sets `listening = false`, which is what breaks the
loop.

**Scope:** `frontend/kiosk.js` only + ~4 static-source tests. **No change** to S1–S4 behaviour, the echo
guard, the countdown, TTS-1, TTS-2, storage, or schema.

---

## 🔎 EDGE VERIFICATION FINDINGS (S30 — real Edge, not assumed)

**Method:** Claude's browser tools drive Electron/Chromium 148, **not** Edge — so real
**Microsoft Edge 151.0.4129.72** was launched at a local read-only probe page that reported back. The
probe deliberately did **not** call `recognition.start()` or `getUserMedia()` (either would pop a
permission dialog unprompted), so it covers everything **except audio**.

### ✅ Verified TRUE in real Edge
- **The STT is the browser's native Web Speech API** — `kiosk.js:464`
  `window.SpeechRecognition || window.webkitSpeechRecognition`. No library, no server STT.
- Edge 151 exposes **BOTH** `SpeechRecognition` and `webkitSpeechRecognition` as functions.
- A recognizer **constructed successfully** and **accepted** `lang='bn-BD'`, `continuous=true`,
  `interimResults=true`.
- **Microphone permission:** `navigator.permissions.query({name:'microphone'})` → **`"prompt"`**. Not
  blocked; Edge will ask. `isSecureContext: true` on localhost.
- **Edge can play the TTS-2 output:** `canPlayType('audio/mpeg')` → **`"probably"`**.
- **No Chrome-only APIs anywhere in the STT path.**

### ⚠️ THE CRITICAL DISTINCTION — do not blur these
> **API surface verified ≠ actual Bangla STT service verified.**
> Edge *accepting* the string `'bn-BD'` proves only that the property setter took it. Whether Edge's
> speech **backend actually transcribes Bangla** is **UNPROVEN** and cannot be proven without a human
> speaking into a real mic in Edge. **Do not claim Edge STT works end-to-end.**

### 🔑 Edge has NO Bengali browser TTS voice — and this is good news
Edge 151 exposes **26 voices across 21 languages; `bnVoices: []`.** This **disproves ADR-0050's
option 3** ("Edge as the kiosk browser — Microsoft online `bn-BD`, zero code — *unverified*"). Now
verified: **FALSE.** Microsoft's *Edge browser* ships no Bengali voice, even though Microsoft's
*edge-tts service* has `bn-BD-NabanitaNeural`. Same vendor, different surface.

**Consequence:** in Edge, `_pickVoice('bn')` returns null → the chain falls to provider 2 → **the
server-side TTS-2 `edge-tts` path remains the Bangla TTS route in Edge, exactly as designed.** There is
**no** Chrome-vs-Edge divergence for Bangla audio.

### 🟡 UNVERIFIED — a suspicion, NOT a confirmed bug
**`FLUSH_GRACE_MS = 600`** (`kiosk.js:372`) is Chrome-calibrated — its own comment says *"how long to
let **Chrome** flush its last final chunk"*. If Edge finalises more slowly, the tail of a long answer
could be dropped, which would be a **rule #1 defect**. **This has NOT been observed and MUST NOT be
recorded as a bug.** It cannot be measured without real audio in Edge. **Do not change the constant
blindly** — have the live run check whether the last few words of a long Bangla answer survive. If they
do not, raising it is a one-constant change.

### ⚠️ Demo warning (secure-context rule)
The Web Speech API and the microphone require a **secure context**. `http://localhost:8001` qualifies.
Demoing from another machine over LAN (`http://192.168.x.x:8001`) **blocks both**. Use localhost on the
demo machine, or HTTPS.

---

## ❗ THE HUMAN END-TO-END TEST HAS NOT HAPPENED YET
**Nobody has heard TTS-1 or TTS-2, and nobody has run STT in Edge.** Everything shipped in S30 is
proven only by tests plus non-audio browser probes. The pending run must cover **Chrome AND Edge**.
The full procedure was handed over at the end of S30; the short version:

1. Restart the server (config changes need it):
   `.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --port 8001`
2. Chrome → `http://localhost:8001/kiosk.html` → **Ctrl+Shift+R** (a stale `tts.js` invalidates the test).
3. Bangla session, then an English session. Judge: **(a)** one question = one language, no English tail;
   **(b)** the Bangla voice sounds human, not robotic; **(c)** the screen still shows BOTH languages;
   **(d)** mic timing / countdown / transcript unchanged from the S29 PASS.
4. **Then repeat in Edge** — and watch specifically for: does Bangla STT produce any text at all, and do
   the **last words of a long answer survive** (the `FLUSH_GRACE_MS` question)?
5. If the voice is wrong, it is a `.env` swap, not code: `TTS_EDGE_VOICE_BN=bn-BD-PradeepNeural` (male),
   or `TTS_PROVIDER=espeak` to go back offline. **Restart after either.**

---

## ✅ What S30 shipped (settled — do not redo or re-derive)
### TTS-1 — one question, one language (ADR-0051, Accepted)
Human's choice: **option (a), speak only the half matching the active UI language.**
- `frontend_shared/tts.js` — `BILINGUAL_QUESTION` regex + `spokenHalf(text, short)`, applied **once**
  inside `speak()`: `const speech = verbatim ? text : spokenHalf(text, short);`
- **Both providers receive `speech`** (`SpeechSynthesisUtterance(speech)` and `encodeURIComponent(speech)`).
- `frontend/kiosk.js` — the per-bubble 🔊 passes `verbatim: role === 'patient'`.
- **Unchanged and test-pinned:** the stored `system` utterance, the on-screen bilingual bubble
  (ADR-0028 fallback), and `followup.py`'s M7 prompt.

### TTS-2 — natural neural Bangla (ADR-0050, Accepted)
Human's two calls: **provider = `edge-tts`** (now the DEFAULT) and **fall back to espeak-ng on failure
rather than go silent.**
- **NEW** `backend/app/services/tts/edge.py` — `EdgeTtsProvider`, `media_type = "audio/mpeg"` (MP3).
- `service.py` — `PROVIDER_FACTORIES` registry + `get_fallback_provider()` + the chain in
  `synthesize()`: primary → espeak-ng → raise. Both failing → the error **names both**, route returns
  **503, never a silent 200**, fallback logs at **WARNING**.
- `base.py` — `MAX_TEXT_CHARS` moved here from `espeak.py` (it is the endpoint's contract, not one
  engine's) and `TtsProvider.available()` (default True; **never** touches the network).
- `config.py` — `TTS_PROVIDERS += "edge"`, `tts_provider` default `espeak` → **`edge`**, plus
  `tts_edge_voice_bn/_en`, `tts_edge_rate`, `tts_edge_timeout_s`, `tts_local_fallback`.
- `requirements.txt` += **`edge-tts==7.2.8`**. `.env.example` documents all three providers.
- **No route, frontend, schema or Alembic change — the ADR-0049 seam held.**

## ⚠ Open gaps / honest caveats (carry these forward)
- **The Edge STT terminal-error fix is NOT implemented** (the next step, above).
- **Naturalness is NOT proven** for TTS-2, and **TTS-1 has not been heard.** Measured: bytes, MIME,
  ~0.8 s latency, playback complete at 3013 ms, `ttsSpeaking()` true throughout, `<audio>` requesting
  only the Bangla half. Not measured: how any of it sounds.
- **Edge Bangla STT service support is UNPROVEN** (API surface only).
- **`FLUSH_GRACE_MS` on Edge is UNVERIFIED** — a suspicion, not a bug.
- **⚠ Rule #4 / thesis:** M7 questions are derived from patient speech and **now go to Microsoft**.
  Accepted deliberately (the Web Speech API already sends the patient's *actual audio* to Google), but
  **it limits what the thesis may claim about privacy.** `TTS_PROVIDER=espeak` reverts it in one line.
- **The kiosk now needs internet for the good voice.** Without it the fallback speaks robotically — by
  design, not a bug.
- **`agent_docs/human_live_run_guide.md` is now WRONG in two places** and was deliberately NOT edited
  this session: line 19 says *"Open Google Chrome (not Edge/Firefox — the mic + voice work best in
  Chrome)"*, and line 72 repeats the **now-disproven** "Edge may expose Microsoft's online `bn-BD`
  neural voices" claim. Needs a human "go".
- **Steps S5–S7 of Requirement 3 are NOT built.** S5 = no-speech re-prompt (10 s → repeat once → 10 s →
  offer typing), the 120 s answer cap, mic-permission + `visibilitychange` recovery, **and the deferred
  repeat-while-listening echo gap**. S5 also directly mitigates the Edge dead-end above. S6 = KIOSK-7
  resume dock re-verify. S7 = docs + the 12-point live run.
- **Deferred since S25:** tapping "Repeat question" while the mic is ALREADY open plays TTS into a live
  recognizer. Closing it means deciding the fate of the half-spoken answer in the buffer — discarding a
  patient's words is a **rule #1 decision**, not a drive-by change.
- `askAloud`'s safety-net timeout is still sized from the **full** bilingual text, so it over-waits
  slightly. **Deliberate and test-pinned:** over-waiting is harmless, opening the mic early is a rule #1
  defect.
- The Web Speech API opens its **own** audio stream, so `echoCancellation` **cannot** be passed. Echo
  protection is structural gating only — the ceiling until Requirement 2.
- **`ttsSpeaking()` — not `speechSynthesis.speaking` — must remain the echo-guard predicate** (ADR-0049).
  This matters MORE now: a network provider adds ~0.8 s of in-flight time that `<audio>` alone cannot
  report. Reverting it reopens a rule #1 echo hole.
- **`CLAUDE.md` is stale in two places** (needs a human "go"): its status paragraph still describes
  S28/234 tests, and *"TTS for M7 audio: browser Web Speech API — no server, no key"* is now two ADRs
  out of date. It also says Python 3.14 while the venv is **3.13.3**.
- **A second uvicorn may still be running on port 8000**; S30 left one on **8001**. An **Edge window may
  still be open** on the throwaway probe page (`http://127.0.0.1:8799/`, server already exited).
- **Alembic stays at 0012.**

## The standing menu (still the human's call)
1. **The Edge STT terminal-error fix** ← **RECOMMENDED next step** (small, and it removes a silent
   dead end before the demo).
2. **The combined Chrome + Edge live listen / STT run** — closes the 3.0 cycle. Can be done before or
   after (1); doing (1) first means one run instead of two.
3. **Step S5** of Requirement 3 (also mitigates the Edge dead end from the other direction).
4. **Rotate the 3 API keys** (`GEMINI_API_KEY` / `GROQ_API_KEY` / `OPENROUTER_API_KEY`) —
   *recommended before any public demo*. **HUMAN step — I must never handle the keys.** Still NOT done.
5. **Fix the stale docs** — `human_live_run_guide.md` (Chrome/Edge claims) and `CLAUDE.md`.
6. **More 3.0 findings / new features** → the inbox in `context fixed problem 3.0.md`.
7. **Faculty Reqs 1 & 2** (quantized summary model; quantized on-device STT/TTS — `facebook/mms-tts-ben`
   is its natural candidate and now drops into the same seam as one subclass). Or formal WER / the
   TextBee real-SMS demo.

## Locked decisions — do NOT re-open
- **ADR-0050 (S30, ACCEPTED):** `edge-tts` is the default provider; espeak-ng is demoted, not deleted,
  and is the automatic fallback. The rule #4 privacy cost was accepted explicitly. Verified facts that
  settled it: **edge-tts is LGPL-3.0** (no copyleft on our code, no NC clause);
  **`facebook/mms-tts-ben` is CC-BY-NC-4.0** (non-commercial only). Its **option 3 is now disproven** —
  Edge exposes no Bengali voice. Do not re-litigate on the old "binary aiohttp dep" framing.
- **ADR-0051 (S30, Accepted):** TTS speaks only the UI-language half; stored and displayed text keep the
  FULL bilingual string. The split lives at the single entry point (`speak()`), covers BOTH providers,
  and must never migrate into the recording or display path.
- **ADR-0049 (S29, Accepted):** the server-side TTS provider seam; **supersedes ADR-0040's rejection of
  server-side TTS**. Browser voice still WINS when present. Failure is loud (503 / `speak()` returns
  false), never silent.
- **ADR-0048 (S28):** voice-first + typing always available; supersedes ADR-0027's voice-only rule. The
  3 s countdown **is** the silence window and is a **confirmation window, never a hard cutoff**; ONE
  answer pipeline (`source: mic|manual`); frontend tests = **static-source assertions only** (S30 kept
  that, with one narrow exception: the shipped regex literal is extracted and executed).
- **ADR-0047 / 0046 / 0045 / 0042–0044 / 0040** — see `decisions.md`.

## Reminders (the four non-negotiables)
- **Rule #1:** raw words are never edited/translated. **Live-verified clean in S29** and preserved
  through both S30 fixes — TTS changed only what is SPOKEN, never what is stored or displayed.
- **Rule #2:** the system never diagnoses — M16 disclaimer server-attached; Diagnosis doctor-only.
- **Rule #3:** red flags are ADD-only — the local rule still forces Critical with every LLM down.
- **Rule #4:** synthetic/consented data only in dev. **M7 question text now leaves the machine** for
  Microsoft (ADR-0050) — a deliberate, recorded trade-off, reversible with `TTS_PROVIDER=espeak`.
- Run (Windows): `.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --port 8001`
- Run (Arch):    `.venv/bin/python -m uvicorn backend.app.main:app --reload --port 8001`
  **`.env` changes need a RESTART** (this includes every `TTS_*` knob). NEVER delete the DB.
- Tests: `pytest backend/tests/` (**318 passing, 1 skipped** as of S30). Windows: `PYTHONIOENCODING=utf-8`.
  Add `TTS_LIVE=1` to also run the real-network TTS test.
