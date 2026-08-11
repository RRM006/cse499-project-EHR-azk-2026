# current_task.md — What We Are Doing RIGHT NOW

> This is a small, throwaway snapshot. It gets **overwritten** every session.
> It is NOT a history log (that is `changelog.md`). It answers only:
> "If I open a brand-new Claude Code session, what do I need to know to continue?"

---

**Date:** 2026-08-11 (end of Session 33)
**Phase:** **Faculty-demo feature cycle — ALL IN-SCOPE DEVELOPMENT IS COMPLETE.**
F1–F6 done, **F5 done** (voice phone + voice OTP), **P1 robotic doctor done**, **P2 elderly/3D UI
done**, **P3 age validation done (deterministic tiers only)**. Test suite: **480 passed, 2 skipped,
0 failures**. Alembic head: **0012 — no schema change, do not create a migration.**
New ADRs this session: **0053** (F5) and **0054** (P1/P2/P3).

**What is left is NOT coding. It is a human at a real microphone.**

---

## 🚦 THE NEXT STEP — **REAL MICROPHONE VALIDATION OF F5**

Everything in F5 was built and exercised WITHOUT a microphone: the Browser pane blocks audio
capture, so every voice claim so far rests on feeding the recognizer's buffer directly with text.
**What Chrome's `bn-BD` recogniser actually returns for spoken digits is still UNPROVEN**, and it
is the one thing that can still invalidate the digit vocabulary.

### Setup
- Run: `.venv\\Scripts\\python.exe -m uvicorn backend.app.main:app --reload --port 8001`
- Open **http://localhost:8001/kiosk.html** in **Chrome** (and repeat in **Edge** if possible —
  nobody has ever run STT in Edge).
- ⚠ Use `localhost` or `127.0.0.1`. A LAN IP (`http://192.168.x.x`) **blocks the mic and Web
  Speech entirely** — it is not a secure context.
- Allow the microphone when prompted. The FIRST tap on the phone screen's mic is deliberately
  what raises that prompt (F5b tap-to-start).

### The exact flow to test
1. **Phone screen** → tap 🎤 → **speak your mobile number** → the number appears in the field and
   a large read-back panel shows it (e.g. `01715-984632`) and speaks it back digit by digit.
2. **Confirm** → tap **"✔ Yes — send the code"**. Nothing is sent before this tap — verify that.
3. **OTP screen** → the prompt is spoken and **the mic opens by itself** → **speak the 6 digits** →
   the boxes fill and verification runs with no button press.
4. **Verified** → the interview opens and asks **area → name → age → problem**.

### What to say (cover all four, both screens)
- **Bangla digits spoken as words:** শূন্য এক সাত এক পাঁচ নয় আট চার ছয় তিন দুই
- **English digits spoken as words:** zero one seven one five nine eight four six three two
- **Digits read naturally/grouped** ("০১৭ ১৫৯ ৮৪৬৩২") — grouping and pauses must not break it
- **A number with filler around it** ("আমার নম্বর হলো ০১৭…") — filler must be ignored

### Failure / re-ask behaviour to exercise deliberately
- **Say too few digits** on the phone screen → expect: partial digits kept in the field, an error
  naming how many were heard, the prompt re-spoken, and the mic reopened. **Nothing sent.**
- **Say a wrong OTP** → expect: all six boxes cleared, the server's own reason shown, the prompt
  re-spoken, the mic reopened.
- **Say too few/too many OTP digits** → expect: boxes cleared, "I heard N digits — the code has 6".
- **Tap "✖ No — say it again"** → expect: field cleared and the mic reopens in the same gesture.
- **Switch to ⌨ Type on either screen** → typing must still work fully, and the re-ask must NOT
  speak at you or reopen the mic (typing patients are left alone by design).

### Also worth watching while you are there
- **The robotic doctor (P1)** — does it correctly show *speaking* while it talks, *listening* while
  the mic is open, *please wait* while it thinks? It is derived from real state, so a wrong face
  means a real bug. The antenna lamp: grey idle, teal speaking, green listening, amber processing.
- **TTS-1 / TTS-2** — nobody has ever HEARD these. Is one question spoken in ONE language, and does
  the Bangla voice sound natural (edge-tts) rather than robotic (espeak)?
- **Elderly readability (P2)** — is the text large enough, are the buttons easy to hit, is anything
  important below the fold on your actual screen?

### ⚠ The rule for next session
**Only change code if live testing reveals a REAL issue.** F1–F6, F5, P1, P2 and P3 are complete
and test-pinned; do not redesign, "improve" or refactor them speculatively. If the recogniser turns
out to return a Bangla spelling the map misses, the fix is usually **one entry in `SPOKEN_DIGITS`
in `frontend/kiosk.js`** — not an architecture change.

---

## ✅ What Session 33 shipped (settled — do not redo or re-derive)

- **F5a** — `to_ascii_digits()` in `db/repository_visits.py`; `unicodeDigit()` / `asciiDigits()` /
  `digitsFromSpeech()` / `phoneFromSpeech()` + `SPOKEN_DIGITS` in `frontend/kiosk.js`; both OTP box
  handlers fold Unicode digits instead of deleting them.
- **F5b** — `DOCKS.phone` / `DOCKS.otp`, `state.identifyStep`, two branches in `stopListening()`,
  the read-back/confirm panel, voice OTP on F1's `maybeAutoVerify()`, re-ask on failure.
- **P1** — the robotic doctor: `currentAvatarState()` / `refreshAvatar()` / `setAvatarOverride()`,
  `AVATAR_STATES`, a 200 ms poll, and CSS-only 3D in `kiosk.html`.
- **P2** — elderly sizing + focus rings + two responsive axes, scoped to `kiosk.html`.
- **P3** — `test_age_appropriate_questions.py`, tiered honestly (see below).

## ⚠ Open gaps / honest caveats (carry these forward)

- **🔴 NO MICROPHONE HAS EVER BEEN USED.** That is the whole of the next session.
- **Age-appropriateness Tier 3 is NOT proven.** The tests prove the age is computed, reaches M7
  verbatim, is confined to PATIENT CONTEXT and changes nothing else; the prompt's instructions are
  directional. Whether the MODEL obeys is one live observation (a 78-year-old got *"How severe is
  the pain?"* — on-topic and non-diagnostic), not a validation across ages. `M7_LIVE=1` runs the
  opt-in probe.
- **P2 rests on measured geometry, not on looking at it** — the Browser pane stopped compositing,
  so no screenshots exist. Verified at 1280x900, 1280x720, 1024x600 and 375x812: no horizontal
  overflow, primary action visible, all touch targets ≥44px.
- **Edge is still unproven** for `bn-BD` STT, and Edge has **no Bengali browser TTS voice** (so it
  falls to the server edge-tts path, same as Chrome).
- **Still not done from earlier cycles:** rotating the **3 API keys** (HUMAN-only — I must never
  handle keys), the combined **Chrome + Edge live listen/STT run**, the **mid-turn word-loss**
  rule #1 decision (`kiosk.js` `stopListening(false)` discards `finalBuffer`), **Step S5** of
  Requirement 3, formal **WER**, and the stale `human_live_run_guide.md:19,72` +
  `CLAUDE.md`'s status paragraph (still says S28/234 tests) and its *"TTS … no server, no key"* line.

## Locked decisions — do NOT re-open
- **ADR-0054 (S33):** avatar state is DERIVED, never pushed (listening > speaking > processing);
  only `done`/`error` may be pushed and `error` expires; elderly sizing scoped to the kiosk, not
  `shared.css`; validation reported in three explicit tiers.
- **ADR-0053 (S33):** a Unicode decimal digit is a digit; ONE recognizer; phone confirmed but OTP
  not; tap-to-start on the phone screen only.
- **ADR-0052 / 0051 / 0050 / 0049 / 0048 / 0047 / 0045 / 0042–0044 / 0040** — see `decisions.md`.
- **S31's terminal/transient STT split:** `no-speech`, `aborted`, `bad-grammar` must stay OUT of
  `TERMINAL_STT_ERRORS` or Chrome's continuous listening regresses. `r.onend` stays untouched.

## Reminders (the four non-negotiables)
- **Rule #1:** raw words never edited. Identification digits are NOT clinical utterances and are
  never stored as raw text; the 12-turn preservation check passed byte-exact.
- **Rule #2:** never diagnoses — asserted unconditionally across both age tiers.
- **Rule #3:** red flags ADD-only; the local rule still forces Critical with every LLM down.
- **Rule #4:** synthetic/consented data only. Web Speech sends audio to Google and F5 now adds
  phone numbers + OTP codes to what it hears (ADR-0053) — state this in the thesis privacy section.
- Run (Windows): `.venv\\Scripts\\python.exe -m uvicorn backend.app.main:app --reload --port 8001`
- Tests: `pytest backend/tests/` (**480 passing, 2 skipped**). Windows: `PYTHONIOENCODING=utf-8`.
