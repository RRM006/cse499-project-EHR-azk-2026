# current_task.md — What We Are Doing RIGHT NOW

> This is a small, throwaway snapshot. It gets **overwritten** every session.
> It is NOT a history log (that is `changelog.md`). It answers only:
> "If I open a brand-new Claude Code session, what do I need to know to continue?"

---

**Date:** 2026-08-12 (end of Session 35)
**Phase:** **The second manual-testing cycle is CLOSED.** All 8 findings were implemented and
verified in one pass: the phone-confirm countdown, voice yes/no confirmation, guided/elderly cues,
context-aware questions, the review first-render fix, TTS pacing, review voice confirmation, and an
always-visible clock. Test suite: **622 passed, 2 skipped, 0 failures** (was 547).
Alembic head: **0012 — no schema change, do not create a migration.**
New ADR this session: **0056** (it supersedes ADR-0055's "Rejected (1)" and amends ADR-0053).
**No module changed status** — refinements inside M1 / M7 / M13 / M14, all already ✅. **M15 🟨.**

**⚠ Step S5 was NOT implemented and must not be assumed.** See the bottom of this file.

**What is left is STILL not coding. It is a human at a real microphone — and the stakes went up.**

---

## 🚦 THE NEXT STEP — **REAL MICROPHONE VALIDATION** (now blocking, not just pending)

This has been the next step since S33, and S35 made it more urgent rather than less: **the whole
flow now depends on a spoken "হ্যাঁ" being recognised.** Every answer and the final submit pass
through a spoken yes/no. If a real `bn-BD` recogniser returns something the vocabulary does not
know, the patient is stuck in a confirmation loop (recoverable — the buttons still work and the
banner says so — but it would ruin a demo).

Three claims a real microphone can still disprove, in priority order:

1. **The yes/no vocabulary.** `CONFIRM_YES` / `CONFIRM_NO` in `frontend/kiosk.js`. If a real
   recogniser returns a spelling the map misses, the fix is **one entry** — not an architecture
   change. Bring a list of what it actually returns for: হ্যাঁ · জি · ঠিক আছে · ঠিক · না · ঠিক নাই ·
   আবার বলি · ভুল · yes · okay · no.
2. **The English digit words in Bangla script** (S34, still unproven): `জিরো ওয়ান টু থ্রি …`.
3. **Whether the paced TTS actually sounds better.** S35 added sentence terminators and real pauses;
   whether that is audibly more natural is a human listening judgement, not a test.

### Setup
- Run: `.venv\\Scripts\\python.exe -m uvicorn backend.app.main:app --reload --port 8001`
- Open **http://localhost:8001/kiosk.html** in **Chrome** (and repeat in **Edge** if possible —
  nobody has ever run STT in Edge).
- ⚠ Use `localhost` or `127.0.0.1`. A LAN IP **blocks the mic and Web Speech entirely**.
- Allow the microphone when prompted. The FIRST tap on the phone screen's mic raises that prompt.

### The exact flow to test
1. **Phone** → tap 🎤 → speak the number → watch the live digit preview (`0 1 7 1 5 …`) and the
   **10-second clock in the header**. Do nothing: it should send by itself, exactly once.
   Then repeat and tap ✔ early — the clock must stop and it must still send exactly once.
2. **OTP** → the mic opens itself → speak the 6 digits → verified with no button press.
3. **Interview** → after each spoken answer: *"আমি শুনেছি আপনি বলেছেন: …"*, then
   *"এটা কি ঠিক আছে? হ্যাঁ বলুন অথবা না বলুন।"* — and the mic opens by itself for the verdict.
   Say **হ্যাঁ** (stores and advances), say **না** (stores nothing, same question again), and say
   **something unrelated** (nothing decided, asked again).
4. **Review** → the 60-second clock in the header, the floating doctor on the left, per-card 🔊.
   The assistant asks *"সবকিছু কি ঠিক আছে?"* — say **না** (the correction question opens, nothing
   submitted) and later **হ্যাঁ** (submits, exactly once).

### Also worth watching
- **The clock**, at whatever size the demo screen is. It must never need scrolling to find.
- **The listening cues (Finding 3)** — mic pulsing, the hint going large and red. Is that enough for
  someone who has never used a computer, without any instruction?
- **The paced TTS.** Does the question end properly instead of stopping mid-breath?

### ⚠ The rule for next session
**Only change code if live testing reveals a REAL issue.** Everything through S35 is complete and
test-pinned. If the confirmation is too slow in practice, `VOICE_ANSWER_CONFIRM=false` and
`VOICE_PHONE_CONFIRM_MS=0` are the switches — do not delete the features to make it faster.

---

## ✅ What Session 35 shipped (settled — do not redo or re-derive)

- **Voice yes/no:** `speechTokens()` (the ONE tokenizer, extracted so digits and confirmations
  share it), `CONFIRM_YES`/`CONFIRM_NO`/`CONFIRM_FILLER`, `parseConfirmation()`,
  `applySpokenConfirmation()`, `askConfirmationAloud()`, `CONFIRM_NOT_UNDERSTOOD`.
- **Review voice approval:** `state.reviewConfirm`, `startReviewConfirmation()` /
  `stopReviewConfirmation()` / `applyReviewConfirmation()` / `rejectReview()`,
  `REVIEW_CONFIRM_PROMPT`, `REVIEW_CORRECTION` (reuses the KIOSK-7 resume dock).
- **The header clock:** `#kiosk-clock` in the portal header, `renderClock()` / `hideClock()` /
  `CLOCK_LABELS`; `startPhoneTimer()` / `cancelPhoneTimer()` / `phoneConfirmMs()`; the
  `#review-timer` element is GONE (not duplicated).
- **Guidance cues:** `body[data-kiosk-state]` written by `applyAvatarState()` + the mic pulse and
  the loud dock hint.
- **Backend:** `collected_context()` + two `_QUESTION_SYSTEM` clauses in `services/followup.py`;
  NEW `services/tts/prosody.py` (`speech_text()`) applied once in `tts/service.py`;
  `tts_edge_pitch`/`tts_edge_volume`; `voice_phone_confirm_ms` → `/api/config.phone_confirm_ms`.

## ⚠ Open gaps / honest caveats (carry these forward)

- **🔴 NO MICROPHONE HAS EVER BEEN USED, in any session.** Every voice result on record comes from
  feeding the recogniser's own buffer in a browser engine.
- **The confirmation vocabulary is now on the critical path** — see the top of this file.
- **Acoustic quality is not tested and is not claimed.** `speech_text()` proves the text is
  punctuated for speech and that no word is changed; whether it SOUNDS better is a human judgement.
  Do not let the green suite become "the TTS is natural now".
- **Whether the model OBEYS the new "do not re-ask" instruction is NOT proven** — Tier 1/Tier 2 only,
  the ADR-0054 (f) rule. `M7_LIVE=1` runs the opt-in probe.
- **The confirmation costs a turn.** An ambiguous reply loops back to the same question; the buttons
  and ⌨ Type are the escapes, and the banner says what to say.
- **A pending read-back discarded by "Done"** remains part of the open **mid-turn word-loss** rule #1
  decision (`stopListening(false)` drops `finalBuffer`) — **do not decide it unilaterally.**
- **Still not done from earlier cycles:** rotating the **3 API keys** (HUMAN-only), the Chrome + Edge
  live run, formal **WER**, and the stale `human_live_run_guide.md:19,72` + `CLAUDE.md`'s status
  paragraph (still says S28/234 tests).

## Locked decisions — do NOT re-open
- **ADR-0056 (S35):** one yes/no vocabulary for every confirmation; an unknown word makes an
  utterance ambiguous and NO beats YES; a verdict is routed before the clinical branches and never
  stored; review-NO reuses the resume dock; the phone window is a window, not a bypass, and 0
  restores the tap; ONE clock, in the header, never `position: fixed`; `collected_context()` informs
  the question and never selects it; TTS pacing may never change a word.
  ⚠ It **supersedes ADR-0055's Rejected (1)** and **amends ADR-0053**.
- **ADR-0055 (S34):** the read-back gate at ONE routing point, typed answers never gated, unclear
  captures re-asked (not switchable), ONE shared ticker with the **S4 endpointer excluded**.
- **ADR-0054 / 0053 / 0052 / 0051 / 0050 / 0049 / 0048 / 0045 / 0040** — see `decisions.md`.
- **S31's terminal/transient STT split:** `no-speech`, `aborted`, `bad-grammar` must stay OUT of
  `TERMINAL_STT_ERRORS` or Chrome's continuous listening regresses. `r.onend` stays untouched.

## ⛔ Step S5 is NOT implemented — do not assume it is

S5 of faculty Requirement 3 (`faculty_future_features.md` §J) is: **no-speech re-prompt, empty-submit
guard, 120 s answer cap, and permission/visibility recovery.** S34 built only the narrow
empty-capture re-ask its Phase 2 required; S35 built nothing from S5 at all. **Untouched and still
deferred:** the `no_speech_ms` watchdog (a mic open with no speech), the `max_answer_ms` cap on a
runaway turn, and recovery when microphone permission is revoked or the tab is backgrounded
mid-answer. Both timings are already served by `/api/config` and are still marked `S5 (not used yet)`
in `kiosk.js`. ADR-0055 (e) records the one overlap in full.
⚠ Note ADR-0056 corrects a claim ADR-0055 made in passing: a spoken yes/no is **not** S5 content.
S5 is timers and browser-lifecycle recovery; a verdict needs neither.

## Reminders (the four non-negotiables)
- **Rule #1:** raw words never edited. A verdict is never stored; a rejected capture was never
  stored; the read-back stays verbatim and untranslated; `speech_text()` cannot touch a word.
- **Rule #2:** never diagnoses. "Ambiguous" and "unclear" are presence-of-token tests, not
  judgements about content; `collected_context()` adds no clinical reasoning.
- **Rule #3:** red flags ADD-only; the local rule still forces Critical with every LLM down.
- **Rule #4:** synthetic/consented data only. Web Speech sends audio to Google; edge-tts sends the
  assistant's question text to Microsoft (ADR-0050) — state both in the thesis privacy section.
- Run (Windows): `.venv\\Scripts\\python.exe -m uvicorn backend.app.main:app --reload --port 8001`
- Tests: `pytest backend/tests/` (**622 passing, 2 skipped**). Windows: `PYTHONIOENCODING=utf-8`.
