# current_task.md — What We Are Doing RIGHT NOW

> This is a small, throwaway snapshot. It gets **overwritten** every session.
> It is NOT a history log (that is `changelog.md`). It answers only:
> "If I open a brand-new Claude Code session, what do I need to know to continue?"

---

**Date:** 2026-08-11 (Session 32)
**Phase:** **Faculty-demo feature cycle — the human's 8-part list, approved plan F1→F2→F3→F4→F5→F6.**
**F1, F2, F3, F4 and F6 are DONE. F5 is NOT STARTED.** Test suite: **392 pass, 1 skipped** (the skip is
still the opt-in `TTS_LIVE=1` network test). Alembic head: **0012 — no schema change, do not create a
migration.** New ADR: **0052**.

---

## 🚦 THE NEXT STEP — **F5 — implement and validate voice phone-number entry + voice OTP.**

That one line is the whole of next session's job. It is the human's requirement **1 and 2**, so until
it lands the demo flow they specified (*speak the phone number → speak the OTP → interview*) is
**not achievable**. **F1/F2/F3/F4/F6 are complete. F5, P1 and P2 remain.**

### The human's required order of work before writing any F5 code
1. **Re-read the relevant project documentation** (this file, `changelog.md` S32, ADR-0052, ADR-0048).
2. **Re-inspect the existing STT / listening state machine** — `initRecognition()`,
   `toggleListening()`, `stopListening()`, `r.onresult/onend/onerror`, `TERMINAL_STT_ERRORS`.
3. **Verify the existing Speak/Type architecture** — `DOCKS`, `activeDock()`, `setInputMode()`,
   `state.inputMode`.
4. **Design the safest way to add identification/number voice input WITHOUT creating a second STT
   pipeline.** A third "identification" dock entry in the `DOCKS` map is the intended shape.
   ⚠ **Do NOT build a second recognizer** — the human's explicit regression rule.
5. **Implement Bangla/English digit normalization carefully**: Bangla digits `০১২৩৪৫৬৭৮৯`, ASCII
   digits, **Bangla number words**, **English number words**, arbitrary spacing/grouping.
6. **NEVER silently submit an uncertain phone number.** Show the normalized number back and require
   confirmation. Manual typing stays fully available on both screens.
7. **Then implement voice OTP** — recognized digits fill the six boxes and the EXISTING
   `maybeAutoVerify()` (F1) takes over: correct → continue, wrong → clear + re-ask. **Do not
   duplicate that logic.**
8. **Test manually and with automated tests.**
9. **Perform real browser / live-microphone validation where possible.**
10. **Only after F5 is stable, continue to P1/P2.**

⚠ **`normalize_phone` rejects Bangla digits today — verified, not assumed.**
`re.sub(r"\D", "", ...)` in `db/repository_visits.py:17` **keeps** `০১৭…` (they are Unicode digits),
then the ASCII `startswith("1")` check fails → `ValueError` → 400. Meanwhile **JS** `/\D/g` in
`kiosk.js` is ASCII-only, so a Bangla digit in an OTP box is silently **deleted**. The two languages
disagree; the normalizer must resolve it explicitly.

---

## ✅ What Session 32 shipped (settled — do not redo or re-derive)

- **F1 `frontend/kiosk.js`** — `OTP_LENGTH`, `otpDigits()`, `clearOtpInputs()`, `maybeAutoVerify()`
  (wired into the typed AND pasted paths), Enter on the OTP boxes **and** the phone field, and a
  rewritten `verifyOtp()`: length gate, `otpVerifying` re-entry guard, clear-and-re-ask keeping the
  server's reason, `if (!res) return;`.
- **F2 `services/followup.py`** — the resume scope's SERVER-named field + `FIELD_PROMPTS`. The old
  `target_gap = remaining[0]` repair is GONE. **The main loop is deliberately unchanged.**
- **F3** — NEW `services/requirements.py`; `GET /api/visits/{uuid}/readiness`;
  `submit?require_complete=true`; `followup_resume_max_questions = 8`; kiosk
  `updateSubmitVisibility()` + `#required-notice`.
- **F4** — `INTAKE_SCRIPT` (area → name → age → description) as ordinary recorded turns;
  `problem_area` in M3/M8 + **merged** entities; `patient_context()` → M7; AGE-APPROPRIATE prompt rule;
  identity re-askable through the resume dock.
- **F6** — `test_conversation_preserved.py`, tests only, no production code.

## ⚠ Open gaps / honest caveats (carry these forward)

- **🔴 F5 IS NOT BUILT.** See above.
- **NO VOICE PATH WAS VERIFIED THIS SESSION.** The Browser pane blocks microphone capture, so every
  voice claim still rests on the human's live run. What WAS live-verified (no mic needed): the OTP
  keyboard/auto-submit/clear cycle and the scripted-opening sequence.
- **The F4 prompt changes are UNPROVEN.** `AGE-APPROPRIATE` questioning and area-context are
  instructions to M7 — no live LLM call was made against them. Tests prove the context *reaches* the
  model, not that the model *obeys* it. Worth one real conversation before the demo.
- **`require_complete` is opt-in** (ADR-0052 d) — a client omitting the flag skips the gate. Deliberate:
  staff/walk-in paths legitimately submit partial cases. Flip the default if the human prefers, but it
  means updating three fixtures that intentionally model sparse cases.
- **A resumed `in_progress` visit re-asks the script** and appends to the earlier conversation
  (pre-existing `verify-otp` behaviour, now more visible because the opening is 4 turns).
- **Still not done from earlier cycles:** the combined **Chrome + Edge live listen / STT run** (nobody
  has HEARD TTS-1/TTS-2 or run STT in Edge); the **mid-turn word-loss** rule #1 decision
  (`kiosk.js` `stopListening(false)` discards `finalBuffer`); **Step S5** of Requirement 3;
  **rotating the 3 API keys** (HUMAN-only — I must never handle keys); the stale
  `human_live_run_guide.md:19,72`; `CLAUDE.md`'s status paragraph (S28/234 tests), its
  *"TTS … no server, no key"* line (two ADRs out of date) and Python 3.14 vs the venv's **3.13.3**.
- **A uvicorn is running on port 8001** (started via the preview tooling) with `kiosk.html` loaded.
  Demo on **8001**, not 8000. `localhost` and `127.0.0.1` are both secure contexts, so the mic works
  on either; a LAN IP (`http://192.168.x.x`) **blocks mic and Web Speech**.

## Locked decisions — do NOT re-open
- **ADR-0052 (S32):** identity (name/age/area) stays OUTSIDE the 10 fields; two kinds of requirement
  (value vs asked); server-side readiness gate; `require_complete` opt-in; resume loop's own budget;
  the server names the resume field.
- **ADR-0051 / 0050 / 0049 / 0048 / 0047 / 0045 / 0042–0044 / 0040** — see `decisions.md`.
- **S31's terminal/transient STT split:** `no-speech`, `aborted`, `bad-grammar` must stay OUT of
  `TERMINAL_STT_ERRORS` or Chrome's continuous listening regresses. `r.onend` stays untouched.

## Reminders (the four non-negotiables)
- **Rule #1:** raw words never edited. F4's scripted turns go through the SAME insert-only endpoint;
  F6 now pins byte-exactness in the DB and the .docx.
- **Rule #2:** never diagnoses — the new `problem_area` prompt says *"this is a location, not a
  diagnosis"*.
- **Rule #3:** red flags ADD-only; the local rule still forces Critical with every LLM down.
- **Rule #4:** synthetic/consented data only. M7 question text goes to Microsoft (ADR-0050).
- Run (Windows): `.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --port 8001`
- Tests: `pytest backend/tests/` (**392 passing, 1 skipped**). Windows: `PYTHONIOENCODING=utf-8`.
