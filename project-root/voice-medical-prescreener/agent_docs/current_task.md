# current_task.md — What We Are Doing RIGHT NOW

> This is a small, throwaway snapshot. It gets **overwritten** every session.
> It is NOT a history log (that is `changelog.md`). It answers only:
> "If I open a brand-new Claude Code session, what do I need to know to continue?"

---

**Date:** 2026-08-12 (end of Session 34)
**Phase:** **The S34 manual-testing cycle is COMPLETE.** All twelve phases the human gave were
implemented in one pass: the spoken-digit vocabulary fix + live digit preview, the spoken-answer
read-back, the review read-aloud, the floating review assistant, auto-scroll, the 60-second review
clock, and one reusable ticker. Test suite: **547 passed, 2 skipped, 0 failures** (was 480).
Alembic head: **0012 — no schema change, do not create a migration.**
New ADR this session: **0055**. **No module changed status** — these are refinements inside
M1 / M7 / M13 / M14, all already ✅. **M15 stays 🟨.**

**⚠ Step S5 was NOT implemented and must not be assumed.** See the bottom of this file.

**What is left is still NOT coding. It is a human at a real microphone.**

---

## 🚦 THE NEXT STEP — **REAL MICROPHONE VALIDATION** (now with two more things to disprove)

This was S33's next step and it is still the next step, because nothing since has involved a real
microphone. S34 added two things a real recogniser can still invalidate, so they go at the top of
the list:

1. **The English digit words in Bangla script.** The kiosk listens at `lang='bn-BD'`, so a patient
   saying "one two three" should produce `ওয়ান টু থ্রি`, and S34 mapped those ten spellings. **That
   this is what Chrome actually returns is REASONED, NOT OBSERVED.** If the real spellings differ,
   the fix is one entry each in `SPOKEN_DIGITS` in `frontend/kiosk.js` — not an architecture change.
2. **The spoken-answer read-back.** Whether an elderly patient understands ✔/✖ after hearing their
   own words, and whether the extra tap per turn is acceptable, cannot be settled from here. If it
   is too slow, `VOICE_ANSWER_CONFIRM=false` in `backend/.env` restores the S25-era flow exactly —
   that is what the switch is for. Do NOT delete the feature to make it faster.

### Setup
- Run: `.venv\\Scripts\\python.exe -m uvicorn backend.app.main:app --reload --port 8001`
- Open **http://localhost:8001/kiosk.html** in **Chrome** (and repeat in **Edge** if possible —
  nobody has ever run STT in Edge).
- ⚠ Use `localhost` or `127.0.0.1`. A LAN IP (`http://192.168.x.x`) **blocks the mic and Web
  Speech entirely** — it is not a secure context.
- Allow the microphone when prompted. The FIRST tap on the phone screen's mic is deliberately
  what raises that prompt (F5b tap-to-start).

### The exact flow to test
1. **Phone screen** → tap 🎤 → **speak your mobile number**. Watch the new **digit preview** under
   the transcript: it should read `0 1 7 1 5 …` while you speak, even though the transcript above
   shows the words. Then the read-back panel appears — nothing is sent before you tap **"✔ Yes"**.
2. **OTP screen** → the prompt is spoken and the mic opens by itself → **speak the 6 digits** →
   the boxes fill and verification runs with no button press.
3. **Interview** → area → name → age → problem. After each spoken answer: **"I heard you say:"**
   with your words, spoken back — then ✔ or ✖.
4. **Review** → the 60-second clock top-right, per-card 🔊, "Hear my answers", the floating doctor
   on the left. Leave it alone and it should submit itself exactly once.

### What to say (cover all four, on the phone AND the OTP screen)
- **Bangla digits spoken as words:** শূন্য এক সাত এক পাঁচ নয় আট চার ছয় তিন দুই
- **English digits spoken as words:** zero one seven one five nine eight four six three two
  ← **this is the case S34 fixed and the one most worth watching**
- **Digits read naturally/grouped** ("০১৭ ১৫৯ ৮৪৬৩২") — grouping and pauses must not break it
- **A number with filler around it** ("আমার নম্বর হলো ০১৭…") — filler must be ignored

### Failure / re-ask behaviour to exercise deliberately
- **Say too few digits** → partial digits kept, an error naming how many were heard, the prompt
  re-spoken, the mic reopened. **Nothing sent.**
- **Say a wrong OTP** → all six boxes cleared, the server's own reason shown, prompt re-spoken.
- **Answer a question, then tap ✖ "No — say it again"** → nothing stored, the SAME question asked
  again, the mic reopened in the same gesture.
- **Stay silent for a whole turn, then tap the mic to stop** → "Sorry, I did not catch that — let
  me ask again", nothing stored, same question.
- **Switch to ⌨ Type at any point** → typing works fully, a pending read-back is dropped, and the
  re-ask must NOT speak at you or reopen the mic (typing patients are left alone by design).
- **On the review screen:** press Confirm & Submit before 60 s → the clock must stop and there must
  be exactly ONE submission. Then press Speak Again from a later review → the clock must stop.

### Also worth watching while you are there
- **TTS-1 / TTS-2** — nobody has ever HEARD these. Is one question spoken in ONE language, and does
  the Bangla voice sound natural (edge-tts) rather than robotic (espeak)? The read-back is now a
  second, much more frequent consumer of TTS, so bad audio hurts twice as much.
- **The robotic doctor (P1)** — *speaking* while it talks, *listening* while the mic is open,
  *please wait* while it thinks. It is derived from real state, so a wrong face means a real bug.
- **Elderly readability (P2)** — text size, button reach, and whether anything important is below
  the fold on your actual screen. S34 fixed the page so the chat thread scrolls instead of the
  document; check that the mic and Done stay visible however long the conversation gets.

### ⚠ The rule for next session
**Only change code if live testing reveals a REAL issue.** F1–F6, F5, P1–P3 and everything S34
shipped are complete and test-pinned; do not redesign, "improve" or refactor them speculatively.

---

## ✅ What Session 34 shipped (settled — do not redo or re-derive)

- **Digits:** ten Bangla transliterations of the English digit words in `SPOKEN_DIGITS`;
  `spacedDigits()`; `renderDigitPreview()` / `clearDigitPreview()`; `digitPreview` on `DOCKS.phone`
  and `DOCKS.otp` + `#phone-digit-preview` / `#otp-digit-preview`.
- **Read-back:** `holdForConfirmation()` (the ONE gate, in `stopListening()`'s spoken branch),
  `isUnclearAnswer()`, `currentQuestionText()`, `reAskUnclearAnswer()`, `offerSpokenAnswer()`,
  `showAnswerConfirm()` / `hideAnswerConfirm()`, `speakAnswerBack()`, `acceptAnswer()` /
  `rejectAnswer()`, `state.pendingAnswer`, `applyCountdownCaption()`, and the two panels.
- **Review:** per-card 🔊 in `renderSummary()`, `speakSummaryField()`, `toggleSummaryReadAloud()` +
  `readAloudQueue` + `setReadAloudLabel()`; `summary-avatar` as a third `AVATAR_IDS` mount with
  `AVATAR_STATUS_IDS` / `AVATAR_SUBSTATUS_IDS`; `.doctor-float`.
- **Timer:** `startTicker()` (shared with the auto-logout), `startReviewTimer()` /
  `cancelReviewTimer()` / `renderReviewClock()` / `hideReviewClock()` / `reviewTimeoutMs()` /
  `reviewSpeakAgain()`, and `submitting` in `confirmSubmit()`.
- **Scroll:** `scrollThreadToEnd()`; `html, body { height: 100% }` + `.screen { min-height: 0;
  overflow-y: auto }` in `kiosk.html`.
- **Config:** `voice_answer_confirm` + `voice_review_timeout_ms` → `/api/config` as
  `answer_confirm` + `review_timeout_ms`.

## ⚠ Open gaps / honest caveats (carry these forward)

- **🔴 NO MICROPHONE HAS EVER BEEN USED, in any session.** Every voice result on record comes from
  feeding the recogniser's own buffer in a browser engine. That is the whole of the next session.
- **The Bangla transliterations of English digit words are REASONED, not observed** — see above.
- **The read-back costs one tap per spoken turn.** That is a deliberate trade (ADR-0055 c) and a
  real regression against the zero-touch goal. `VOICE_ANSWER_CONFIRM=false` is the escape hatch.
- **A pending read-back discarded by "Done"** joins the existing **mid-turn word-loss** rule #1
  decision (`stopListening(false)` drops `finalBuffer`). Same open question, now with a second
  instance — **do not decide it unilaterally.**
- **Age-appropriateness Tier 3 is still NOT proven** (S33). `M7_LIVE=1` runs the opt-in probe.
- **Edge is still unproven** for `bn-BD` STT, and has no Bengali browser TTS voice.
- **Still not done from earlier cycles:** rotating the **3 API keys** (HUMAN-only — I must never
  handle keys), the combined Chrome + Edge live run, formal **WER**, and the stale
  `human_live_run_guide.md:19,72` + `CLAUDE.md`'s status paragraph (still says S28/234 tests).

## Locked decisions — do NOT re-open
- **ADR-0055 (S34):** the read-back gate lives at ONE routing point and typed answers are never
  gated; an unclear capture is re-asked and that is NOT switchable; the review clock runs only while
  the submit button is genuinely pressable; ONE shared ticker, with the **S4 endpointer deliberately
  excluded** because its deadline restart is the rule #1 anti-clipping guarantee.
- **ADR-0054 (S33):** avatar state is DERIVED, never pushed (listening > speaking > processing);
  only `done`/`error` may be pushed and `error` expires; elderly sizing scoped to the kiosk.
- **ADR-0053 (S33):** a Unicode decimal digit is a digit; ONE recognizer; phone confirmed but OTP
  not; tap-to-start on the phone screen only.
- **ADR-0052 / 0051 / 0050 / 0049 / 0048 / 0047 / 0045 / 0042–0044 / 0040** — see `decisions.md`.
- **S31's terminal/transient STT split:** `no-speech`, `aborted`, `bad-grammar` must stay OUT of
  `TERMINAL_STT_ERRORS` or Chrome's continuous listening regresses. `r.onend` stays untouched.

## ⛔ Step S5 is NOT implemented — do not assume it is

S5 of faculty Requirement 3 (`faculty_future_features.md` §J) is: **no-speech re-prompt, empty-submit
guard, 120 s answer cap, and permission/visibility recovery.** S34 built ONLY the narrow empty-capture
re-ask that the human's Phase 2 explicitly required. **Untouched and still deferred:** the
`no_speech_ms` watchdog (a mic open with no speech at all), the `max_answer_ms` hard cap on a runaway
turn, and recovery when microphone permission is revoked or the tab is backgrounded mid-answer. Both
`no_speech_ms` and `max_answer_ms` are already served by `/api/config` and are still marked
`S5 (not used yet)` in `kiosk.js`. ADR-0055 (e) records the overlap in full.

## Reminders (the four non-negotiables)
- **Rule #1:** raw words never edited. The read-back shows and speaks them verbatim, carries no
  `data-en`/`data-bn` so a language toggle cannot overwrite them, and a REJECTED capture was never
  stored — so rejecting it edits nothing.
- **Rule #2:** never diagnoses. "Unclear" is a presence-of-characters test, not a judgement.
- **Rule #3:** red flags ADD-only; the local rule still forces Critical with every LLM down.
- **Rule #4:** synthetic/consented data only. Web Speech sends audio to Google; F5 added phone
  numbers and OTP codes to that (ADR-0053) — state this in the thesis privacy section.
- Run (Windows): `.venv\\Scripts\\python.exe -m uvicorn backend.app.main:app --reload --port 8001`
- Tests: `pytest backend/tests/` (**547 passing, 2 skipped**). Windows: `PYTHONIOENCODING=utf-8`.
