# current_task.md — What We Are Doing RIGHT NOW

> This is a small, throwaway snapshot. It gets **overwritten** every session.
> It is NOT a history log (that is `changelog.md`). It answers only:
> "If I open a brand-new Claude Code session, what do I need to know to continue?"

---

**Date:** 2026-08-13 (end of Session 36)
**Phase:** **The post-S35 hardening cycle is CLOSED.** All seven items were implemented and
verified in one pass: the review-grid alignment defect, a real patient-session boundary, the
MCP evaluation (**rejected, with reasons**), the phone-number early stop, "ঠিক আছে" finishing the
review, the automatic raw-transcript download, and two usability gaps.
Test suite: **723 passed, 2 skipped, 0 failures** (was 622).
Alembic head: **0012 — no schema change, do not create a migration.** No new dependency.
New ADR this session: **0057.** **No module changed status** — refinements inside M1 / M7 / M12 /
M13 / M14, all already ✅. **M15 🟨.**

**⚠ Step S5 was NOT implemented and must not be assumed. See the bottom of this file.**

---

## 🚦 THE NEXT STEP — **REAL MICROPHONE VALIDATION of the S36 voice changes**

⚠ **A correction to how S33–S35 phrased this, because it matters and it was wrong.** Those files say
"NO MICROPHONE HAS EVER BEEN USED, in any session". That is not true and contradicts our own record:
**S25's human live real-mic run PASSED on Windows 11 + Chrome + a real mic** (TC-V1/V2/V3/F2/R1 all
✅, STT "very accurate", ~2 s latency) — see `milestone_log.md` and `human_live_run_guide.md`. The
accurate, narrower statement is the one to carry forward:

> **Real-microphone STT/TTS is PROVEN for the S25-era flow. What no microphone has exercised is the
> voice behaviour added SINCE — S33/S34/S35/S36.** Those results all come from driving the shipped
> handlers with scripted recogniser results in a browser engine, which validates the wiring and the
> vocabulary but not what a real `bn-BD` recogniser actually returns.

Three NEW claims from S36 that a real recogniser can disprove, in priority order:

1. **The completion vocabulary** (`CONFIRM_YES` in `frontend/kiosk.js`). S36 added `alright`,
   `all`, `সব`, `সবকিছু` and the filler `s`. Bring back what the recogniser actually returns for:
   ঠিক আছে · সব ঠিক আছে · সবকিছু ঠিক আছে · সব ঠিক · all right · alright · okay · that's all.
   A miss is **one map entry**, not an architecture change.
2. **The phone early stop.** Does `maybeCompletePhone()` fire on the eleventh digit of real
   speech, or does the recogniser deliver digits in chunks that make it fire early/late? Watch the
   live digit preview and whether the mic closes the moment the last digit lands.
3. **Is the spoken completion audible?** It is a single `speak()` over a waiting room. Also: does
   it finish before the 5-second auto-logout cuts it off?

### Setup
- Run: `.venv\\Scripts\\python.exe -m uvicorn backend.app.main:app --reload --port 8001`
- Open **http://127.0.0.1:8001/kiosk.html** in **Chrome** (and **Edge** if possible — still never run).
- ⚠ Use `localhost` or `127.0.0.1`. A LAN IP **blocks the mic and Web Speech entirely**.

### The exact flow to test
1. **Phone** → speak the 11 digits and **keep talking** ("এটাই আমার নম্বর"). The mic must close on
   the eleventh digit and the trailing words must NOT appear in the number. Then try repeating a
   digit — that used to break a correct number and should now be impossible.
2. **OTP** → unchanged; confirm the mic still opens itself.
3. **Interview** → confirm `Question 1 of 4 … 4 of 4` appears during the scripted opening and
   **disappears** once the M7 loop starts (that is deliberate, not a bug).
4. **Review** → say **না** to open the correction question, then say **ঠিক আছে**. It must submit
   once, close the dock, and NOT read "ঠিক আছে" back as a symptom. Then repeat with **all right**.
5. **Completion** → the assistant should SAY that the information went to the doctor, and a
   `raw-transcript-visit-….docx` should download by itself, exactly once.
6. **Next patient** → after the 5-second logout, confirm the screen is the phone screen and nothing
   from the previous patient is visible anywhere.

### ⚠ The rule for next session
**Only change code if live testing reveals a REAL issue.** Everything through S36 is complete and
test-pinned.

---

## ✅ What Session 36 shipped (settled — do not redo or re-derive)

- **The session boundary:** `sessionEpoch`, `sessionToken()`, `endSession()`, `startNewSession()`.
  Eight async paths check `mine()` before writing. `startNewSession()` is COMPLETE — teardown,
  fresh state, avatar clear, voice mode, phone screen. `confirmSubmit()` calls only that.
- **Layout:** `.summary-body.no-float` (the grid track dies with the float) + `.resume-q-body`
  (`min-width: 0`, `overflow-wrap: anywhere`).
- **Phone:** `maybeCompletePhone()` inside `onresult`, checked before `restartSilenceWindow()`;
  `otpSending` guard on `sendOtp()`.
- **Review completion:** `reviewCorrectionOpen()`, `maybeFinishReview()`, routed before
  `holdForConfirmation()`; `updateSubmitVisibility()` now also respects `submitting`.
- **Transcript:** `downloadRawTranscript({auto:true})` from `confirmSubmit()`,
  `autoTranscriptDownloaded` guard; server filename `raw-transcript-visit-<8>-<date>.docx`.
- **UX:** `SUBMITTED_ALOUD` + `renderConvoProgress()` / `hideConvoProgress()` and `#convo-progress`.
- **Backend:** NEW `services/question_tools.py` (`get_patient_context`, `get_question_context`,
  `unsafe_question_reason`, `safe_fallback_question`, `MAX_CONTEXT_TURNS = 24`);
  `followup.py` now renders from those tools and guards M7's OUTPUT.

## ⚠ Open gaps / honest caveats (carry these forward)

- **🟡 Real-mic STT/TTS is PROVEN (S25) — for the S25-era flow only.** The voice behaviour added in
  S33–S36 (spoken yes/no, Bangla-script English digit words, the answer read-back, the phone early
  stop, the completion phrases, the spoken completion line) has **never been exercised by a
  microphone**. ⚠ Do not repeat S33–S35's "no microphone has ever been used" — it is false; and do
  not swing the other way and call the new behaviour validated either.
- **The S36 guard on M7's output is HIGH-PRECISION, LOW-RECALL and is not a medical-safety
  classifier.** It catches dosage amounts and explicit prescribing/diagnosing phrases. It
  deliberately does NOT ban "ওষুধ"/"medicine"/"diagnosis" — asking ABOUT those is M7's job. Rule #2
  rests on the whole design, not on that function. Do not let the green suite become "the AI cannot
  diagnose now".
- **Whether the model OBEYS the bounded context is NOT proven** — Tier 1/Tier 2 only (ADR-0054 f).
- **Acoustic quality is still not tested and not claimed** (S35 caveat, unchanged).
- **A pending read-back discarded by "Done"** remains part of the open **mid-turn word-loss rule #1
  decision** (`stopListening(false)` drops `finalBuffer`) — **do not decide it unilaterally.** This
  is now also what BLOCKS S5's permission/visibility recovery.
- **Still not done from earlier cycles:** rotating the **3 API keys** (HUMAN-only), the Chrome +
  Edge live run, and formal **WER**.

## Locked decisions — do NOT re-open
- **ADR-0057 (S36):** the session is an epoch-guarded boundary and `endSession()` is its one place;
  `startNewSession()` is complete, and is never called from `resetState()` (module-load TDZ);
  **MCP is rejected** — no tool-calling loop, the round-trips are the scarce resource, a second
  context path rebuilds a disagreement S35 removed, and session scoping is structural; a complete
  phone number ends its own turn but does NOT skip the read-back; only YES finishes the correction
  question; the auto-download is dropped rather than handed to the next patient; the grid track dies
  with the float; progress is claimed only where the length is a fact.
- **ADR-0056 (S35):** one yes/no vocabulary for every confirmation; an unknown word makes an
  utterance ambiguous and NO beats YES; a verdict is routed before the clinical branches and never
  stored; ONE clock, in the header; `collected_context()` informs the question and never selects it.
- **ADR-0055 / 0054 / 0053 / 0052 / 0051 / 0050 / 0049 / 0048 / 0045 / 0040** — see `decisions.md`.
- **S31's terminal/transient STT split:** `no-speech`, `aborted`, `bad-grammar` must stay OUT of
  `TERMINAL_STT_ERRORS` or Chrome's continuous listening regresses. `r.onend` stays untouched.
- **⚠ No apostrophes in comments inside the `CONFIRM_*` literals.** The vocabulary tests parse
  quoted tokens straight out of the served file, so prose with an apostrophe is read AS VOCABULARY.
  This actually happened in S36 and was caught by `test_the_two_vocabularies_do_not_overlap`.

## ⛔ Step S5 is NOT implemented — do not assume it is

S5 (`faculty_future_features.md` §J) is: **no-speech re-prompt, empty-submit guard, 120 s answer
cap, and permission/visibility recovery.** S34 built only the narrow empty-capture re-ask its
Phase 2 required; S35 and **S36 built nothing from S5 at all**. Verified by inspection at the end of
S36 and now pinned by `test_step_s5_is_still_not_implemented`: `no_speech_ms` and `max_answer_ms`
are still marked `S5 (not used yet)` and read by nothing, and there is no `visibilitychange`
handler and no permission-recovery path anywhere in the kiosk.
⚠ **The permission/visibility half is BLOCKED, not merely pending.** It cannot be built without
deciding what happens to the half-captured answer in `finalBuffer` when the tab is backgrounded or
permission is revoked mid-answer — and discarding a patient's words is the open rule #1 decision
above. **That decision is the human's.**

## Reminders (the four non-negotiables)
- **Rule #1:** raw words never edited. A verdict is never stored; a rejected capture was never
  stored; the auto-downloaded transcript is `u.raw_text` and says so on its first line; the M7
  output guard replaces a *generated question*, never a patient's words.
- **Rule #2:** never diagnoses. `question_tools` restates and bounds; it ranks nothing and names no
  condition, and a test asserts no disease name lives in the guard's vocabulary.
- **Rule #3:** red flags ADD-only; the local rule still forces Critical with every LLM down.
- **Rule #4:** synthetic/consented data only. Web Speech sends audio to Google; edge-tts sends the
  assistant's question text to Microsoft (ADR-0050) — state both in the thesis privacy section.
  The auto-download filename deliberately carries no name and no phone number.
- Run (Windows): `.venv\\Scripts\\python.exe -m uvicorn backend.app.main:app --reload --port 8001`
- Tests: `pytest backend/tests/` (**723 passing, 2 skipped**). Windows: `PYTHONIOENCODING=utf-8`.
