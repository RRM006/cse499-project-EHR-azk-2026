# test_log.md — What Was Tested + Results

> For an ML/NLP project, "it runs" is NOT success. This file records **numbers**:
> what we tested, how, and the result — including failed runs. This makes progress
> verifiable and gives the thesis real evidence.
>
> Template for each entry:
> ```
> ## YYYY-MM-DD — Module N — <what was tested>
> - Setup: <model/library/version, machine: Windows or Linux, sample data used>
> - Metric(s): <e.g. WER, precision, recall, accuracy, latency>
> - Result: <the numbers>
> - Notes: <what helped / hurt, errors, next idea>
> ```

---

## Metrics we care about (per module)

- **Module 1 (STT):** Word Error Rate (WER, lower is better), latency (seconds
  from speech to text), and whether it ran on CPU on both OSes.
- **Module 2 (Normalization):** % of fields correctly normalized; raw left intact.
- **Module 3 (Extraction):** precision & recall for each entity type (symptom,
  duration, severity, medication, etc.).
- **Module 7 (Follow-up + TTS):** question is shown as text AND spoken; whether a
  Bangla (`bn-BD`) voice exists per OS; patient voice reply round-trips to text.
- **Module 10 (Risk + red-flag):** **red-flag recall** on a fixed list of
  life-threatening phrases (we want to almost never miss one → it must force Critical),
  plus overall Low/Med/High/Critical accuracy / confusion matrix on labeled cases.

## How to measure WER (quick note for later)
WER = (substitutions + insertions + deletions) / number of words in the reference.
Use the `jiwer` Python package against a small set of audio clips that we have
transcribed by hand (the "ground truth"). Record the model + machine each time.

---

## Planned test cases (added Session 7 — to run as each step is built)

> These are **not yet executed** — they define what "done" looks like for the new
> voice + flow + API work so a future session can fill in real numbers.

- **TC-V1 — STT voice input (Module 1, existing):** speak 10 Bangla + 10 Banglish
  sentences in Chrome; confirm each appends live & verbatim to RAW, raw is stored
  unchanged, and record rough latency + by-hand WER per sentence. (Still the human's
  pending live test from S4–S6.)
- **TC-V2 — TTS playback (Module 7 / Phase A Step A1):** call `speak('আপনার কতদিন
  ধরে জ্বর হচ্ছে?')`; PASS = audio plays AND the same text is visible on screen.
  Record per OS (Windows / Arch) whether a `bn-BD` voice was available in
  `speechSynthesis.getVoices()`; if none, PASS still requires the on-screen text
  fallback to show (Open Flag 4).
- **TC-V3 — Voice-only reply loop (Module 7→8):** after a TTS question, speak an
  answer; PASS = the answer is transcribed to text and accepted with NO keyboard
  input; the manual text box is used only when the mic is unavailable.
- **TC-A1 — API fallback chain (ADR-0026):** force the primary provider to fail
  (bad key / simulated 429); PASS = the request transparently falls back to
  OpenRouter `:free` and still returns a corrected/structured result; the provider
  actually used is logged.
- **TC-F1 — Flow M4→M6 direct (ADR-0024):** with the Emergency module removed,
  PASS = a case flows M4 → M6 with no emergency branch, and there is no `D1`/`AX`
  node or "Emergency Detected?" step anywhere in the pipeline or UI.
- **TC-F2 — Follow-up loop (Module 9→7):** an incomplete profile loops back to M7
  and asks only for still-missing items (no repeats of answered questions); PASS =
  loop exits when the completeness threshold or max turns is reached.
- **TC-R1 — Red-flag check (Module 10, ADR-0024):** feed a fixed list of clearly
  life-threatening phrases (e.g. "বুকে প্রচণ্ড ব্যথা", severe breathing difficulty,
  stroke signs, loss of consciousness); PASS = every one is forced to **Critical**
  and surfaced in the M12 **Red Flags** section. Record red-flag recall (target:
  no misses on the list).

---

## Test entries (newest first)

## 2026-08-12 — Session 35 — voice yes/no, header clock, question context, TTS pacing — suite **547 → 622**
- Setup: Windows 11, Python 3.13.3 (venv), FastAPI TestClient + pytest; uvicorn on port 8001;
  browser validation in the in-app Chromium engine. SQLite, Alembic head **0012** (verified from the
  DB: `alembic_version = 0012_otp_codes`, 12 migration files, 17 data tables + `alembic_version`).
- Metric(s): automated test pass/fail (not an ML metric); the shipped parsers executed against real
  utterances in a browser engine; measured page geometry at three viewports.
  **No microphone, no audio, no WER, and no acoustic judgement of any kind.**
- **Baseline, re-measured before any change: 547 passed, 2 skipped, 0 failures** (~34 s).
- **Final: 622 passed, 2 skipped, 0 failures** (~33 s). The 2 skips are unchanged and opt-in by
  design (`TTS_LIVE=1` network test, `M7_LIVE=1` model probe).
- Targeted counts: **4 new test files, +75 tests** — `test_question_context.py` (12),
  `test_tts_prosody.py` (29), `test_kiosk_voice_confirmation.py` (17), `test_kiosk_phone_timer.py` (17).
- **6 existing tests updated, none weakened**, each for a contract this session deliberately changed:
  `test_kiosk_config.py` + `test_tts_provider.py` (both assert the COMPLETE `/api/config` key set, so
  a new knob must be declared in both — that is the guard working, not failing);
  `test_kiosk_answer_confirm.py::test_the_panel_is_retracted_by_every_action_that_ends_its_turn`
  (now pins the REMOVAL of S34's retraction-on-listen and explains why it was a defect once the
  read-back is answered by speech); two tokenizer assertions in `test_voice_digits.py` retargeted
  from `digitsFromSpeech` to the extracted `speechTokens()` the two vocabularies now share (the rule
  is unchanged and now covers strictly more); and four clock assertions in
  `test_kiosk_review_timer.py` retargeted from the review-scoped element to the header one.

### Live browser verification (no microphone — the recogniser's own buffer, S33's method)

**The yes/no vocabulary — the shipped `parseConfirmation()`, executed:**

| said | verdict | | said | verdict |
|---|---|---|---|---|
| হ্যাঁ · জি · ঠিক আছে · ঠিক | `yes` | | না · ঠিক নাই · ঠিক না · ঠিক নেই | `no` |
| হ্যাঁ ঠিক আছে · ঠিক আছে ঠিক | `yes` | | ভুল · আবার বলি · না, আবার বলি | `no` |
| yes · okay · ok | `yes` | | no | `no` |

Ambiguous / unrelated, all `null` (ask again, decide nothing): `আমার পেটে ব্যথা` ·
**`আমার নাম রহিম না মানে রহিমা`** (contains না, is not a rejection) · `হ্যাঁ আমার পেটে ব্যথা` ·
`তিন দিন ধরে` · `ব্যথা আছে` · `doctor` · `"   "` · `"..."`. **9/9 yes, 8/8 no, 8/8 ambiguous.**

**Phone read-back window (Finding 1):** clock ran 10s → 8s → 7s in the header, `urgent` from the
start (≤10 s); re-showing the panel returned the SAME ticker handle (no stacking); **a triple
`confirmPhone()` racing the clock produced exactly ONE `/patients/lookup`**; reject produced **zero**;
letting it run to zero produced exactly one and advanced to the OTP screen with the clock hidden.

**Answer confirmation (Finding 2):** a captured answer showed the panel with **0 turns stored**; an
ambiguous reply decided nothing and left it pending with the banner shown; `না ঠিক নাই` stored
nothing and re-asked the SAME question; `হ্যাঁ ঠিক আছে` stored the answer and advanced — and the
verdict itself **never appeared in the transcript**.

**Review confirmation (Finding 7):** armed together with the submit button (clock 59s "left", float
visible); an ambiguous reply → **0 submits**, still waiting; `না ঠিক নাই` → the resume dock re-opened
with *"What would you like to correct?"*, clock stopped, **0 submits**, patient still on the review;
after the correction and the loop closing, `হ্যাঁ ঠিক আছে` **racing a manual `confirmSubmit()`
produced exactly 1 submit**, avatar `done`, logout modal shown.

**Layout (Findings 5 + 8), measured at three viewports:**

| viewport | page overflow-X | layout overflow-X | header overflow-X | clock overlaps title / avatar | clock visible w/o scroll |
|---|---|---|---|---|---|
| 1280x720 | no | no | no | no / no | yes |
| 1024x600 | no | no | no | no / no | yes |
| 375x812 | no | no | no | no / no | yes (and still visible after scrolling the review to the bottom) |

Heading and subtitle inside their container at all three. **First render: 0 px of shift** — with the
clock hidden vs shown, `.summary-head` top, title left, title width and grid top were identical
(93/178/909/168 both times). At 375px the clock measured x 264–348 against a 348px content edge
after the `order: 1` fix (it had been x 28–112, i.e. the left of the wrapped row).

**Listening cues (Finding 3):** while listening, `body[data-kiosk-state]="listening"`, the dock hint
went **13.12px → 16.8px**, `rgb(239,68,68)`, weight 700, and the mic ran `mic-listening`; idle
reverted all three. Avatar and body state agreed at every point.

**Regression sweep, all unchanged:** Bangla digit words, English digit words, the S34 Bangla
transliterations and a mixed/filler number all → `1715984632`; `তিনি বলেছেন` → `""`; Unicode OTP
digits fold; `countdown_ms` 3000 and the S4 endpointer intact; all five `TERMINAL_STT_ERRORS` keys
present; six avatar states; shared tokenizer live. **Zero JS errors**; the only console 404s are the
pre-existing `/favicon.ico` and `/api/visits/null/...` from the synthetic no-visit test scenario.
- Notes: **nothing here is a microphone result, and nothing here is an acoustic result.**
  `test_tts_prosody.py` proves the text handed to the engine is punctuated for speech and that no
  WORD can change — it says nothing about how it sounds. Whether a real `bn-BD` recogniser returns
  a recognisable "হ্যাঁ" is now the most load-bearing unproven claim in the build, because every
  answer and the final submit pass through it.

## 2026-08-12 — Session 34 — S34 manual-testing cycle: read-back gate, digit vocabulary, review clock — suite **480 → 547**
- Setup: Windows 11, Python 3.13.3 (venv), FastAPI TestClient + pytest; uvicorn on port 8001;
  browser validation in the in-app Chromium engine. SQLite, Alembic head **0012** (verified from the
  DB: `alembic_version = 0012_otp_codes`, 12 migration files, 17 data tables + `alembic_version`).
- Metric(s): automated test pass/fail (not an ML metric); live function-level execution in a real
  browser engine; measured page geometry at two viewports. **No microphone, no audio, no WER.**
- Result: **547 passed, 2 skipped, 0 failures.** Runtime ~32 s. Baseline before any change this
  session was re-measured at **480 passed, 2 skipped** (~90 s cold). The **2 skips are unchanged and
  opt-in by design** (`TTS_LIVE=1` network test, `M7_LIVE=1` model probe).
- Targeted counts: **3 new test files, +59 tests** — `test_kiosk_answer_confirm.py` (23),
  `test_kiosk_review_timer.py` (17), `test_kiosk_review_screen.py` (19). **2 files extended, +8** —
  `test_voice_digits.py` 20 → 26, `test_kiosk_config.py` 6 → 8.
- **3 existing tests updated, none weakened:** `test_kiosk_config.py` and `test_tts_provider.py`
  each assert the COMPLETE `/api/config` key set (deliberately, so a new secret cannot leak through
  an unauthenticated route), so the two new behavioural knobs had to be declared in both;
  `test_kiosk_avatar.py::test_both_conversation_and_resume_docks_carry_the_avatar` pinned the exact
  literal `const AVATAR_IDS = ['doctor-avatar', 'resume-avatar'];` and was rewritten to PARSE the
  list and additionally require every mount to exist in the markup — strictly stronger than the
  string it replaced, and renamed to match what it now checks.

### Live browser verification (no microphone — S33's method: feed the recogniser's own buffer)
Executed against the running server at `http://localhost:8001/kiosk.html`.

**Digit vocabulary (Phase 1) — pure functions, executed:**

| input (as a `bn-BD` recogniser would return it) | `digitsFromSpeech` | `phoneFromSpeech` |
|---|---|---|
| `one two three four five six seven eight nine zero` | `1234567890` | `1234567890` |
| `এক দুই তিন চার পাঁচ ছয় সাত আট নয় শূন্য` | `1234567890` | — |
| `জিরো ওয়ান সেভেন ওয়ান ফাইভ নাইন এইট ফোর সিক্স থ্রি টু` (English digits, spoken) | `01715984632` | `1715984632` |
| `zero one seven one five nine eight four six three two` | — | `1715984632` |
| `আমার নম্বর হলো শূন্য এক ৭ ওয়ান five নয় আট চার ছয় তিন দুই` (mixed + filler) | — | `1715984632` |
| `তিনি বলেছেন` (pronoun containing "তিন") | `''` | — |
| `for the number` (English homophone trap) | `''` | — |

**Identification flow:** live preview showed `0 1 7 1 5` while the transcript showed the words →
read-back `01715-984632` with **nothing sent** (still on the phone screen) → confirm → OTP screen →
spoken Bangla-word code → boxes `000000` → verified → interview opened on the scripted area question.

**Read-back gate (Phase 2):** a captured answer showed the panel with the words verbatim and
**0 turns stored**; ✔ stored it and advanced to the next scripted question; ✖ stored nothing, left
the turn count unchanged and re-asked the SAME question; an empty capture and a punctuation-only
capture both produced *"Sorry, I did not catch that — let me ask again"* with **0 turns stored** and
the same question still pending. With `inputMode = 'type'` the re-ask correctly stayed silent.

**Review clock (Phases 6-7):** 60 → 57 → 53 → 52 s; `startReviewTimer()` called three more times
returned the SAME ticker handle (no stacking); Speak Again froze it at 25 s and hid it; returning
restarted it at 60 s; it went `urgent` at ≤10 s. **The timeout firing while TWO manual
`confirmSubmit()` calls raced it produced exactly 1 POST to `/submit`** (counted by wrapping
`window.fetch`), the avatar went `done`, the logout modal ran, and the reset returned the kiosk to
the phone screen with `submitting` released, the thread empty, and voice mode restored.
**Ticker in isolation:** `startTicker(3000)` yielded `3,3,3,3,2,2,2,2,1,1,1,1,0` with `onEnd` fired
**once**; cancelled at 400 ms it fired **zero** times, and a double `cancel()` was safe.

**Layout, measured (not eyeballed):**
- 730x694: review title occupies x 28-568, clock x 582-687 → **no overlap** (as an absolute overlay
  it had covered the centred title — that is why it became a flex sibling).
- 375x812: `summary-layout` scrollWidth 375 = clientWidth 375 → **no horizontal overflow**. Before
  the fix it was **497px of content in a 375px viewport** (pre-existing, caused by an inline
  `grid-column: span 2` creating an implicit second column in the one-column narrow grid).
- Conversation at 730x694 with 12 bubbles + the read-back panel open: `documentElement.scrollHeight
  == clientHeight` (**the page no longer grows**; before the fix it was **1538px in a 694px
  viewport**), the thread scrolls internally, and the mic, the panel and its ✔ button are all fully
  inside the viewport (panel at y 361-519).
- Auto-scroll: thread forced to `scrollTop = 0`, a new bubble appended → 476px at 150 ms (moving,
  not jumping) → landed at the end with the last bubble fully visible.
- Bilingual: preview `০ ১ ৭ ১ ৫`, clock `৬০ সেকেন্ড বাকি` / `60s left`, panel
  `আমি শুনেছি আপনি বলেছেন:` / `✔ হ্যাঁ — এটাই ঠিক`; toggling EN↔BN mid-state left the patient's own
  captured words **byte-identical** (they carry no `data-en`/`data-bn`, by design).
- Console: clean apart from the pre-existing `/favicon.ico` 404. No JS errors at load or during any
  of the above.
- Notes: **nothing here is a microphone result.** What Chrome's `bn-BD` recogniser actually returns
  for spoken English digits is REASONED (transliteration), not observed, and remains the single most
  disprovable claim in the build. Formal WER and extraction precision/recall are still not measured.

## 2026-08-11 — Session 33 — F5 voice identification + P1 avatar + P2 elderly UI + P3 age validation
- Setup: Windows 11, Python 3.13.3 (venv), FastAPI TestClient + pytest; uvicorn on port 8001;
  browser validation in the in-app Chromium engine (Electron/Chromium). SQLite, Alembic head 0012.
- Metric(s): automated test pass/fail (not an ML metric); UI geometry measured in a live browser;
  ONE live M7 (LLM) observation.
- Result: **480 passed, 2 skipped, 0 failures** (was 392 at the end of S32; 438 mid-session after
  F5). Runtime ~40 s. The **2 skips are both opt-in network tests** and are skipped by design:
  `TTS_LIVE=1` (edge-tts) and the new `M7_LIVE=1` (live M7 age probe).
  Per new file: `test_voice_digits.py` **20**, `test_kiosk_voice_identification.py` **26**,
  `test_kiosk_avatar.py` **25**, `test_age_appropriate_questions.py` **17 + 1 skipped**.
  One existing test updated (`test_kiosk_otp_entry.py`) and NOT weakened — it pinned the literal
  `if (!res) return;` which F5b extended; it now asserts the guard returns before both the screen
  change and the visit assignment.
- **Browser validation performed (NO MICROPHONE — see the note below).** Driven by writing the
  recogniser's own `finalBuffer` and calling the real `stopListening(true)`, i.e. the production
  routing path:
  * digit vocabulary, 23 + 11 cases, all passing — Bangla words, Bangla digits, ASCII, English
    words, "oh", variant spellings, grouped/punctuated, mixed-script, filler-wrapped; both
    encodings of `ছয়`/`নয়`; ZWJ/ZWNJ mid-word; and the traps stay empty (`তিনি বলেছেন` -> "",
    `for the number, too` -> "").
  * full flow: spoken Bangla-word phone -> read-back `01715-984632` with **nothing sent** ->
    confirm -> OTP screen -> spoken Bangla-word code -> verified -> interview.
  * avatar: all 6 states across both avatar elements, the precedence cases (speaking beats busy,
    listening beats all), autonomous 200 ms polling, error expiry, and the EN/BN toggle.
  * geometry at **1280x900, 1280x720, 1024x600 and 375x812**: no horizontal overflow on any of the
    four screens, primary action visible without scrolling, and **zero controls below the 44px
    touch minimum** after fixing the 🔊 replay button (measured 30x20 before the fix).
- **ONE live M7 call** (synthetic patient, rule #4 respected): a 78-year-old with a stomach
  complaint. Spoken Bangla age word "আমার বয়স আটাত্তর বছর" was extracted to `birth_year 1948`
  (= age 78), name and sex captured, and M7 returned *"ব্যথার তীব্রতা কত? (How severe is the
  pain?)"* — bilingual, on-topic, non-diagnostic. Summary rendered **10 cards**, F3's gate hid
  Submit and named the outstanding items, and all **12 turns stayed byte-identical and in order**.
- ⚠ **NO MICROPHONE TESTING OCCURRED IN THIS SESSION.** The Browser pane blocks audio capture. No
  claim here is evidence about real speech recognition: what Chrome's `bn-BD` recogniser returns
  for spoken digits remains UNPROVEN and is next session's task. Screenshots were also unavailable
  (the pane stopped compositing), so the UI results are measured geometry, not visual inspection.
- ⚠ **Age-appropriateness is NOT validated at the model level.** Tier 1 (age computed, reaching M7
  verbatim, confined to PATIENT CONTEXT, implausible ages rejected, nothing else age-coupled) and
  Tier 2 (the prompt's instructions are directional) are proven. Tier 3 — that the model's questions
  actually differ appropriately by age — rests on the single live observation above.
- Notes: six defects were found by EXECUTING code rather than by any assertion, which is the
  reusable lesson — a Bangla tokeniser that shredded words at their own vowel marks (returned
  "118" for an eleven-digit sentence), two identical-looking Unicode encodings, a temporal-dead-zone
  ReferenceError, a stale-layout `scrollIntoView` no-op, equal-specificity duplicate CSS that read
  as applied but was dead, and a 30x20 touch target. All fixed and regression-pinned.


## 2026-08-11 — Session 32 — Faculty-demo cycle F1–F4 + F6: suite **324 → 392**, plus two no-microphone browser verifications

- Setup: Windows 11, `.venv` Python **3.13.3**, `PYTHONIOENCODING=utf-8`,
  `pytest backend/tests/`. Browser checks ran against the project's own dev server on
  **port 8001** (`.claude/launch.json`) in the in-app Chromium pane. No API keys were
  exercised — every LLM call in the new tests is stubbed.
- Metric: suite size + pass/fail, and pass/fail per browser scenario.

### A. AUTOMATED (pytest) — the only thing these prove is what the code does offline

- **Result: 392 passed, 1 skipped** (was 324 passed, 1 skipped at the end of S31).
  The skip is unchanged: the opt-in `TTS_LIVE=1` real-network TTS test.
- **+68 tests across 5 new files:**
  - `test_kiosk_otp_entry.py` (12) — F1. Enter wiring on both screens, auto-verify from
    the typed AND pasted paths, the incomplete-code gate, clear-and-re-ask, the
    single-use re-entry guard, and that manual entry survives in full.
  - `test_followup_target_gap.py` (13) — F2. Parameterised over 6 things M7 might echo
    back (different case, near miss, display label, phrase, empty, **and a different
    real key** — the dangerous one); all must record the field actually asked about.
    Includes the JSON-salvage path and two tests proving the MAIN loop is untouched.
  - `test_required_info.py` (21) — F3/F4. The two-kinds requirement split, the resume
    budget, `GET /readiness`, the 409 gate, that the DEFAULT submit contract is
    unchanged, and the anti-trap invariant (every identity requirement has a question
    the kiosk can ask).
  - `test_intake_context.py` (16) — F4. `problem_area` extraction, the merge that stops
    `entities` being wiped, the age/area context reaching M7, and script ordering.
  - `test_conversation_preserved.py` (6) — F6. Both speakers in order; summary/report
    ADD rows and delete none; raw byte-exact **in the database** (including a
    deliberately awkward trailing space); the .docx renders the whole conversation.
- **Two pre-existing tests were updated, neither weakened, none deleted:**
  `test_resume_loop.py` — its fake `Settings` had to gain `followup_resume_max_questions`
  (a stub must model the real object); renamed, both caps zeroed, **same assertion**.
  `test_kiosk_auto_listen.py` — `setResumeMode()` now speaks a local `text` covering both
  an M7 row and a re-asked scripted requirement, so the literal
  `askAloud(question.question_text)` no longer exists; the assertion was retargeted to the
  function body and **strengthened** (it now also proves that function never falls back to
  plain `speak()`).

### B. REAL BROWSER (no microphone required) — behaviour, not source assertions

> ⚠ These are the only two things this session verified in a running browser. Both were
> chosen precisely because they need **no audio**. Everything voice-related is untested.

- **F1 — OTP entry cycle: PASS.** Typed `01712345678`, pressed **Enter** → advanced to the
  OTP screen (`state.phone` set, `otp-sub` filled). Entered a **wrong** 6-digit code → it
  auto-submitted with no button press, the server returned 401, **all six boxes cleared**,
  focus returned to box 1, and the banner read *"Invalid verification code. Please enter the
  code again."* (`display:block` confirmed immediately after `showError`). Entered `000000`
  (dev bypass, `OTP_CHANNEL=dev`) → auto-submitted and advanced to the voice screen with a
  visit created.
  - *Artifact worth recording, not a defect:* the automation's synthetic typing drops
    characters when our KIOSK-1 auto-advance moves focus mid-string, so the six digits were
    driven box-by-box through the same `input` event a keyboard fires. Real human typing is
    unaffected — that auto-advance passed the S25 live run.
  - *Second false alarm, same as S31:* a later read showed the banner as `display:none`.
    That is `showError`'s own 8-second auto-hide (`shared.js:134`), not a missing message.
- **F4 — scripted opening sequence: PASS.** After OTP, the first question was the **area**
  question. Answering advanced `scriptIndex` 0 → 1 → 2 → 3 with the questions appearing in
  the intended order: area → *"What is your name?"* → *"How old are you?"* → the free
  description. `GET /api/visits/{uuid}` then showed **every system question and every
  patient answer stored in order** (live confirmation of the F6 property), and
  `GET /readiness` correctly listed all 8 outstanding requirements.
  - *Investigated and dismissed:* a stray leading opening-question turn was leftover state
    from the earlier F1 probe — `verify-otp` deliberately resumes an open `in_progress`
    visit. Re-checked with an unused phone number: a fresh visit has **0 turns**. Not a bug.
- Console across both runs: **only** the expected 401 from the deliberately wrong OTP.

### C. NOT TESTED — do not read anything above as covering these

- ❌ **Bangla voice digits were NOT validated.** No spoken phone number, no spoken OTP, no
  digit normalization exists yet (F5 is not started). Nothing here says Bangla voice digits
  work.
- ❌ **No microphone path was exercised at all** — the Browser pane blocks mic capture.
  STT, TTS, auto-listen, the countdown and barge-in remain provable only by the human's
  live run.
- ❌ **The F4 prompt changes are unproven against a real model.** The tests prove the age +
  area context *reaches* M7 and that the system prompt demands age-appropriate questions;
  no live LLM call was made, so whether the model *obeys* is unmeasured. Worth one real
  conversation before the demo.
- ❌ Still outstanding from earlier cycles: the combined **Chrome + Edge live listen / STT
  run**, and formal **WER / extraction precision-recall** on a labeled set.

## 2026-08-09 — Session 31 — Module 1/7 — **Web Speech terminal-error fix**: suite 318 → 324, plus a real-engine error-injection matrix
- Setup: Windows 11, `.venv` Python 3.13.3, `pytest backend/tests/` with `PYTHONIOENCODING=utf-8`.
  Live checks against the dev server on **port 8001** (`uvicorn backend.app.main:app --reload`), page
  `http://localhost:8001/kiosk.html`, in Claude's in-app Chromium. **No microphone and no permission
  prompt were involved** — the recognizer's `onerror` was invoked directly, which is the whole point:
  this defect is reachable without audio, so it is testable without audio.
- Metric(s): pass/fail count; and for each of the 8 Web Speech API error codes, the value of `listening`
  after the handler runs (the true predicate — `listening === true` is what makes `onend` restart).
- Result — **offline suite: 324 passed, 1 skipped** (was 318 + 1). The skip is the unchanged opt-in
  `TTS_LIVE=1` network test. New file `backend/tests/test_kiosk_stt_errors.py` = **6 tests**, run in
  1.87 s. **No pre-existing test was modified, weakened or deleted** (contrast S30, which had to update
  two static assertions). Full-suite wall time 37.09 s.
- Result — **real-engine error-injection matrix** (each row: fresh recognizer, `listening = true`, fire
  the code, read `listening`):

  | error fired | `listening` after | required behaviour |
  |---|---|---|
  | `no-speech` | **true** | transient — `onend` must restart ✅ |
  | `aborted` | **true** | transient — fires on our OWN `stop()` every turn ✅ |
  | `bad-grammar` | **true** | transient ✅ |
  | `network` | **false** | terminal — loop broken ✅ |
  | `service-not-allowed` | **false** | terminal ✅ |
  | `not-allowed` | **false** | terminal (unchanged from before) ✅ |
  | `audio-capture` | **false** | terminal (unchanged from before) ✅ |
  | `language-not-supported` | **false** | terminal — **the Edge case** ✅ |

  After a terminal error: `state.inputMode === 'type'` and `#error-banner` carried the matching bilingual
  message with `display=block` (e.g. *"Speech recognition is unavailable — you can type instead."*).
  `Object.keys(TERMINAL_STT_ERRORS)` in the live page returned exactly the 5 terminal codes, proving the
  map is **valid JS** — the Python tests only parse it as text. Zero console errors on page load.
- Notes: **the two tests that matter most are the negative ones.** `no-speech` fires constantly during a
  normal pause and `aborted` fires on our own `stop()` at the end of every turn; if either were ever
  added to the terminal map, Chrome would stop mid-answer and clip patients — a **rule #1 defect**, and
  a much worse bug than the one being fixed. They are pinned from both directions (absent from the
  extracted key set, and the early `return` must precede every side effect).
  One **false alarm** chased and dismissed: a probe read `#error-banner` as `display:none`, which looked
  like the message never rendering. It was `showError`'s **8-second auto-hide** (`shared.js:134`) — the
  check had run two tool round-trips late. Re-run immediately, `display=block`. Not a defect.
  ⚠ **What this does NOT measure, stated plainly:** whether **Edge actually emits
  `language-not-supported` for `bn-BD`**, and whether Edge transcribes Bangla at all. Injecting an error
  proves the *handler*; it cannot prove which error a real browser produces. That still needs a human at
  a real mic in Edge, and it is still the pending end-to-end run — **nobody has heard TTS-1 or TTS-2
  either.**

## 2026-08-08 — Session 30 — Module 1/7 — **Microsoft Edge 151 compatibility probe (non-audio)**
- Setup: **real Microsoft Edge 151.0.4129.72** on Windows 11, launched at a throwaway local probe page
  (`http://127.0.0.1:8799/`, read-only, server exited afterwards). Claude's own browser tools drive
  Electron/**Chromium 148**, not Edge, which is why a separate probe was needed. The probe deliberately
  did **NOT** call `recognition.start()` or `getUserMedia()` — either pops a permission dialog on the
  human's desktop unprompted — so it measures **API surface + capability only, never audio**.
- Metric(s): presence/type of the Web Speech constructors; whether the recognizer accepts this
  project's exact config; `speechSynthesis` voice inventory; microphone permission state; media
  `canPlayType`; secure-context status.
- Result:
  * `SpeechRecognition` = **function**, `webkitSpeechRecognition` = **function** (both present).
  * Recognizer **constructed**; accepted `lang='bn-BD'`, `continuous=true`, `interimResults=true`.
  * `speechSynthesis`: **26 voices across 21 languages**, **`bnVoices: []` — NO Bengali voice.**
    Languages present: de, en(AU/CA/GB/IN/US), es(ES/MX), fr(CA/FR), it, ja, ko, nl, pl, pt-BR, ru, tr,
    zh(CN/HK/TW).
  * `navigator.permissions.query({name:'microphone'})` → **`"prompt"`** (not blocked/denied).
  * `canPlayType('audio/mpeg')` → **`"probably"`**; `audio/wav` → `"maybe"` (normal without a codecs
    parameter).
  * `isSecureContext` → **true** on `127.0.0.1`.
  * For contrast, the Chromium 148 browser on the same machine: **3 voices, all `en-US`, no `bn`** —
    consistent with ADR-0049's finding that Windows registers no Bengali TTS voice (registry check:
    only David/Zira/Mark, all en-US, in both the classic and `Speech_OneCore` hives).
- Notes / interpretation — **read this before quoting the result:**
  * ⚠ **API surface verified ≠ Bangla STT service verified.** Edge accepting the string `'bn-BD'`
    proves the property setter took it, nothing more. Whether Edge's speech **backend transcribes
    Bangla** is **UNPROVEN** and requires a human speaking into a real microphone. **This entry does
    NOT establish that Edge STT works end-to-end.**
  * The empty Bengali voice list **disproves ADR-0050's option 3** and confirms the TTS-2 design: in
    Edge the browser path cannot speak Bangla, so the chain falls to the **server-side `edge-tts`
    provider** — the same route as Chrome.
  * This probe also surfaced a **real code defect by inspection** (not by measurement): `kiosk.js:499`
    handles only 2 of 8 Web Speech error codes, so `language-not-supported` / `network` /
    `service-not-allowed` leave `listening === true` and `kiosk.js:491` restarts forever. **Not fixed —
    proposed only.** See `current_task.md`.
  * **`FLUSH_GRACE_MS = 600` on Edge is UNVERIFIED**, recorded as a suspicion and **not** as a bug: it
    is Chrome-calibrated, and whether Edge's finalisation is slower cannot be measured without audio.
  * **No test suite run was required for this entry** — nothing executable changed; the 318/1 baseline
    from the TTS-2 entry below still stands.

## 2026-08-08 — Session 30 — Module 7 (TTS-2, ADR-0050 edge-tts): suite 297 → 318, live latency measured
- Setup: Python 3.13.3 on Windows; `pytest backend/tests/` with `PYTHONIOENCODING=utf-8`. New dep
  `edge-tts==7.2.8` (LGPL-3.0). Live checks against a real uvicorn on port 8001 in the in-app Chrome.
  No DB writes, no schema change (**Alembic stays 0012**).
- Metric(s): test pass/fail; audio bytes + MIME type + wall-clock latency per language; whether the S3
  echo guard still holds while a NETWORK provider is in flight (rule #1); which text reaches the wire.
- Result:
  * **318 passed, 1 skipped** (was 297). New `test_tts_edge_provider.py` = **21 tests**, offline by
    default; the 1 skip is the opt-in network test.
  * **Opt-in live test** (`TTS_LIVE=1`) **passed** — real MP3 frame header, > 5 KB.
  * **Direct provider latency:** `bn` **1.48 s / 20,016 bytes**, `en` **0.85 s / 17,424 bytes**, both
    `audio/mpeg`. Bengali voices available from Microsoft: `bn-BD-NabanitaNeural`,
    `bn-BD-PradeepNeural`, `bn-IN-BashkarNeural`, `bn-IN-TanishaaNeural` (bn-BD is the configured default).
  * **Through the HTTP stack** (cache bypassed): `bn` **899 ms / 766 ms**, `en` **720 ms**, all
    `audio/mpeg` → i.e. the neural provider, not the fallback.
  * **Echo guard (rule #1) still holds:** `speak()` → `onend` at **3013 ms**, and `ttsSpeaking()` was
    **true at 200 / 600 / 1200 / 2000 ms** — the mic cannot open during the ~0.8 s network wait or the
    playback. This was the main regression risk of introducing a network provider.
  * **TTS-1 + TTS-2 compose:** the `<audio>` element requested
    `/api/tts?lang=bn&text=আপনার জ্বর কত দিন ধরে?` — **the Bangla half only**, no English in the URL.
  * **Fallback chain** (unit-tested, monkeypatched): edge failure → espeak WAV; both failing → error
    naming **both** providers → **503**, never a silent 200; `TTS_LOCAL_FALLBACK=false` → bare 503.
  * **Non-regression:** full suite green, including all S1–S4 (auto-listen, countdown, input modes,
    raw_text guard) and the TTS-1 split tests.
- Notes: a 124 ms WAV response during live checking looked like an unwanted espeak fallback but was the
  **browser cache** (`private, max-age=300`) from the earlier TTS-1 verification — re-fetched with
  `cache: 'no-store'` it was `audio/mpeg`. Three espeak-specific tests were updated to pin
  `TTS_PROVIDER=espeak`; they had relied on espeak being the default and would otherwise have asserted
  `RIFF` against MP3. ⚠ **None of this measures NATURALNESS.** Bytes, MIME, latency and completed
  playback are proven; whether the Bangla sounds human — the entire point of TTS-2 — is answerable only
  by the human's live listen, still pending, and must not be described as validated until then.

## 2026-08-08 — Session 30 — Module 7 (TTS-1 bilingual split): suite 277 → 297, plus a real-JS-engine cross-check
- Setup: Python 3.13.3 on Windows; `pytest backend/tests/` with `PYTHONIOENCODING=utf-8`. No DB writes,
  no network, no LLM — the change is frontend-only. Browser checks in the in-app Chrome against a real
  uvicorn on port 8001.
- Metric(s): test pass/fail; which exact string reaches each TTS provider; rule #1 / ADR-0028
  preservation (stored + displayed text unchanged).
- Result:
  * **297 passed, 0 skipped** (was 277). New `test_tts_bilingual_split.py` = **20 tests**.
  * **Split rule, exercised not asserted:** the tests extract the shipped `BILINGUAL_QUESTION` regex
    literal out of the served `/shared/tts.js` and run it. `"আপনার জ্বর কত দিন ধরে? (How many days have
    you had the fever?)"` → **bn half only** / **en half only**, with the other language absent.
  * **Fail-safe cases all spoken WHOLE** (4/4): a monolingual English parenthetical, a `(...)` not at
    the end, a Bangla parenthetical, and nested parentheses.
  * **Real JS engine cross-check** (the pytest tests use Python's `re`): Chrome's own `spokenHalf`
    agreed with all **8** cases, case-for-case.
  * **End-to-end on the server path:** with `serverTts` on and the UI in Bangla, `/api/tts` was called
    with `lang=bn` and `text=আপনার জ্বর কত দিন ধরে?` — English half absent. **0 console errors.**
  * **Non-regression:** all **85** tests across the S1–S4 + TTS-seam files pass
    (`test_kiosk_config` / `test_kiosk_input_modes` / `test_kiosk_auto_listen` / `test_kiosk_countdown` /
    `test_answer_raw_text_guard` / `test_tts_provider` / `test_kiosk_tts_fallback`).
- Notes: two pre-existing static-source assertions failed on the first full run because they pinned the
  exact strings the fix changed (`encodeURIComponent(text)`, the replay-button one-liner); both were
  updated to the new wiring with their original intent still asserted. ⚠ **This is not an audio-quality
  measurement.** It proves which string reaches each provider — not that a patient hears one coherent
  question, and not that the voice sounds acceptable (that is TTS-2, untouched). The human's live listen
  is still pending.

## 2026-07-12 — Session 25 — HUMAN LIVE REAL-MIC RUN: TC-V1/V2/V3/F2/R1 all PASS (Windows 11)
- Setup: **Human-driven live run** (the one thing that can't be automated). Windows 11, Google
  Chrome, real microphone, real dev server on port 8001 (real SQLite DB, Alembic head 0012).
  **Synthetic/pretend patient data only** (rule #4). OTP via the `000000` dev bypass
  (`OTP_CHANNEL=dev`). Followed `agent_docs/human_live_run_guide.md` PART 2 end to end.
- Metric(s): per-test-case PASS/FAIL from the guide (TC-V1 raw transcript · TC-V2 spoken+text ·
  TC-V3 voice-only reply · TC-F2 smart follow-up loop · TC-R1 red-flag→Critical); qualitative
  STT accuracy, rough latency, TTS audibility, follow-up quality.
- Result: **ALL FIVE PASS.**
  * **TC-V1 (STT raw)** ✅ — live mic words appeared on screen and stayed verbatim (rule #1 held).
  * **TC-V2 (TTS)** ✅ — follow-up questions were BOTH shown as text AND spoken aloud; a Bangla
    voice was available on this Windows box (the "no bn voice" hint did not block — PART 1 done).
  * **TC-V3 (voice-only)** ✅ — answers were given by voice and transcribed; no keyboard needed.
  * **TC-F2 (follow-up loop)** ✅ — questions were relevant, one at a time, no repeats of answered
    items ("Follow-up questions: Good").
  * **TC-R1 (red-flag)** ✅ — the severe-symptom phrase forced **Critical** with a Red Flag surfaced.
  * Qualitative observations (human's words): **STT "very accurate"**, **latency ≈ 2 s** speech→text,
    **TTS worked correctly**, **follow-up questions "good"**. No bugs or UX issues found this run.
- Notes: This clears the long-standing HUMAN live-voice gate the module board waited on → the human
  chose to move **Modules 1–14 to ✅** (M5 retired ⛔, M15 stays 🟨 = future retrain pipeline). ⚠
  This run is **qualitative** — no by-hand WER, precision/recall, or a labeled test set was recorded,
  and it was **Windows-only** this pass (Arch browser-level TTS+mic was S16). Formal WER/precision-
  recall on ~50 samples remains the recommended thesis-evidence follow-up. No app code changed.
  Still pending (not build): **rotate the 3 API keys** (guide PART 3) before any public demo.

## 2026-08-08 — Session 28 — Requirement 3 step S1 (voice-loop config seam): suite 192 → 211, all offline
- Setup: Python 3.14 on Windows; `pytest backend/tests/` with `PYTHONIOENCODING=utf-8`. No DB, no
  network, no LLM — S1 is pure config + schema. Settings swapped per-test with the established
  `monkeypatch.setattr("<module>.get_settings", lambda: fake)` pattern from `test_otp.py`.
- Metric(s): test pass/fail; endpoint contract; rule #1 verbatim preservation.
- Result:
  * `pytest backend/tests/` → **211 passed** (was 192; +19, zero regressions, 15.8 s).
  * **`test_kiosk_config.py` (8)** — voice-first defaults (`voice_loop="auto"`, countdown 3000 ms,
    guard 400 ms, no-speech 10000 ms, cap 120000 ms) · `.env` override reaches the kiosk (a clinic
    lengthens the countdown for elderly patients without touching JS) · `manual` still selectable
    (ADR-0045 pattern) · 4 normalization cases (`AUTO`, padded, typo, blank → safe `auto`, never a
    startup crash) · **a secret-leak guard**: the payload's key set must be exactly the 5 behavioural
    knobs, and no value may contain `key/token/secret/url/password/sqlite/otp`.
  * **`test_answer_raw_text_guard.py` (11)** — 6 blank forms (`""`, spaces, `\t`, `\n`, mixed)
    rejected · **padding preserved byte-for-byte** (`"  আমার মাথা ব্যথা করছে  "` survives the
    validator untouched — rule #1: `.strip()` tests emptiness only, it never rewrites) · a 1-char
    answer (`"না"`) is accepted (the guard rejects EMPTY, not SHORT) · voice and typing share one
    contract · unknown `source` rejected · `mic` is the default (voice-first).
- Caveat (honest): S1 is backend-only and **proves nothing about the voice UX** — no mic, TTS,
  countdown or barge-in behaviour exists yet, and per the human's decision (2) those will be covered
  only by static-source assertions plus the **12-point live Chrome checklist**
  (`faculty_future_features.md` §K). Nothing reads `/api/config` yet; kiosk behaviour is unchanged.

## 2026-08-08 — Session 29 — ADR-0049 Bangla TTS seam: suite 247 → 274 (3 skipped), plus real-browser provider checks
- Setup: `pytest backend/tests/` on Windows 11, **Python 3.13.3** (note: `CLAUDE.md` still claims 3.14).
  New: `test_tts_provider.py` (backend seam) and `test_kiosk_tts_fallback.py` (static-source, frontend).
  Real-browser checks via the in-app Chrome preview with **no microphone**: the current `tts.js` source
  was fetched past the cache and evaluated, then each provider path was exercised directly.
- Metric(s): suite size / pass count; provider-selection correctness; failure latency; echo-guard
  truthfulness while a request is in flight.
- Result (SECOND PASS, after espeak-ng 1.52.0 was installed via winget): **277 passed, 0 skipped,
  0 failed** (247 → 277, +30). Engine carries a **Bengali voice** (`bn`, `inc\bn`). Measured:
  · Engine direct: Bangla → exit 0, **158,098 bytes**, RIFF/WAVE, **22,050 Hz, 3.58 s**.
  · `GET /api/tts?lang=bn` → **200, audio/wav, 157,438 bytes, 3.57 s**, `private, max-age=300`.
  · `/api/config` → **`"server_tts": true`**; KIOSK-2 banner **hidden** while
    `banglaVoiceAvailable()` is still **false** — so the FALLBACK is what speaks, not a browser voice.
  · **Playback completes:** `onend` at **3877 ms** (≈ the 3.57 s clip) vs the **22 ms** error path —
    the difference is what distinguishes real playback from silent failure.
  · **Rule #1 integration proof:** `toggleListening` spied → mic opened **exactly once at 4110 ms**;
    `ttsSpeaking()` true at 509 / 1525 / 2553 / 3583 ms with the mic **shut** throughout. Without the
    ttsSpeaking() swap it would have opened at ~400 ms, mid-question.
  · **HUMAN LIVE LISTEN (end of S29, Chrome, real audio) — the seam PASSED, the voice FAILED:**
    **Mic timing PASS** · **Countdown PASS** · **Transcript clean = YES (zero AI words in the patient's
    verbatim record — rule #1 holds end-to-end WITH a server TTS provider; this was the cycle's biggest
    risk)** · **English PASS** · **Bangla voice: "Too robotic" → REJECTED on quality (ADR-0050).**
    Two defects reported → filed as TTS-1 / TTS-2 in `context fixed problem 3.0.md`.
  ⚠ **Quality is therefore measured and NEGATIVE, not unmeasured.** espeak-ng is a formant synthesizer,
  so this is inherent, not tunable — no `TTS_SPEED_WPM` or voice-variant change fixes it.

## 2026-08-08 — Session 29 — HUMAN LIVE LISTEN of ADR-0049 Bangla TTS: 4 PASS, 1 FAIL (voice quality), 1 new defect root-caused
- Setup: the human, real Chrome on Windows 11, real speakers and a real microphone, espeak-ng 1.52.0 as
  the server provider (`server_tts: true`), `voice_loop=auto`. Qualitative by design — this is the only
  gate that can judge audio.
- Metric(s): the 10-point checklist agreed for this feature (audible Bangla · mic timing · countdown ·
  barge-in · transcript purity · English regression · manual-mode regression).
- Result: **Bangla is now genuinely AUDIBLE on Windows** (it was structurally impossible before —
  Bengali is absent from Microsoft's entire Windows TTS voice list).
  · **Mic timing: PASS** — the echo guard holds against real server audio.
  · **Countdown: PASS** — S4's confirmation window survived the TTS change untouched.
  · **Transcript clean: YES** — **zero AI words captured into a patient utterance. Rule #1 verified
    end-to-end with a server-side audio provider.**
  · **English: PASS.**
  · **Bangla voice quality: FAIL — "Too robotic."** Requirement stated as *"i want make it like human
    not too robotic"*.
  · **NEW DEFECT (TTS-1):** *"there are no gap when tts Bangla and English hear . some time 2 question
    hear at a same time this is confusing."* **Root-caused by inspection to
    `backend/app/services/followup.py:45`**, which forces the M7 prompt to emit
    `"question": "<Bangla question> (<English question>)"` — every question is ONE bilingual string, so
    TTS speaks both halves in a single breath. **Not an overlap bug; pre-existing since S25**, merely
    exposed because espeak `-v bn` also applies Bengali phonetics to the English half.
- Notes: 4 of 5 structural checks passed, so **ADR-0049's architecture is validated and retained** — only
  its first provider is rejected (**ADR-0050, Proposed**), which is a one-subclass swap by design. No code
  was written after the verdict, at the human's explicit request. **Next measurement owed:** after TTS-1,
  re-listen and confirm one question = one spoken question; after TTS-2, a human judgement of naturalness
  against `bn-BD-NabanitaNeural` or `mms-tts-ben`.
- Result (FIRST PASS, engine absent): **274 passed, 3 skipped, 0 failed** (247 → 274, +27). The 3 skips
  were the real-audio tests, self-skipping because espeak-ng was not installed. Browser-measured:
  · English → `speak()` returns **true**, `ttsSpeaking()` true during playback, **`onend` fired**.
  · Bangla, no bn voice, no engine → `speak()` returns **false** (no fake success) and the KIOSK-2
    banner shows; `banglaAudioAvailable() === false`.
  · With `serverTts` advertised → Bangla takes the server path and **`ttsSpeaking()` is already true
    while the HTTP request is still in flight** — this is the echo-guard hole that `<audio>` would
    otherwise open (rule #1).
  · Engine missing → **`GET /api/tts` = 503** (not 500, not a silent 200) and the caller is released in
    **22 ms**, so the auto-listen loop cannot hang.
  · `/api/config` → `"server_tts": false`, correctly reporting that the engine is not installed.
- Notes: ⚠ **NO Bangla audio has been heard — audibility and intelligibility are unproven.** Three bugs
  were found by measurement, not by tests: (1) the `<audio>` echo-guard hole above; (2) **English TTS
  broken** by making the browser path require a matching voice while Chrome's `getVoices()` is still
  loading — only Bangla now demands one; (3) **a stale cached `shared.js`** silently routing every
  question down the wrong language path, which hid bug (2) for two rounds → static assets are now
  served `no-cache, must-revalidate` and `tts.js` reads the language from localStorage instead of a
  shared.js helper. **Next measurement owed:** after `winget install eSpeak-NG.eSpeak-NG`, the 3 skipped
  tests must pass (valid RIFF/WAVE, duration > 0.3 s) and the human must confirm audible, intelligible
  Bangla in Chrome.

## 2026-08-08 — Session 29 — Requirement 3 step S4 (silence + 3-2-1 countdown + barge-in): suite 234 → 247, live run PASSED
- Setup: `pytest backend/tests/` plus a **fake-`onresult` harness** in the in-app Chrome —
  `webkitSpeechRecognition` was replaced with a stub engine so the endpointer state machine could be
  driven with synthetic interim/final results, **with no microphone and no permission prompt**.
  Followed by the **human's live real-mic run**.
- Metric(s): countdown visibility and tick accuracy; barge-in cancellation; submit-exactly-once;
  whether the trailing final chunk survives the auto-submit (rule #1).
- Result: **247 passed, 0 failed** (234 → 247, +13). Harness-measured:
  · Countdown appears on first speech and ticks **3 → 2 → 1** (**৩ → ২** with the Bangla UI).
  · **Barge-in at 2115 ms reset the digit to 3**; at 3418 ms — past the original deadline — still
    listening with **0 submits**. The answer was not clipped.
  · A blank/noise-only tick **cancels** a running window but can never **arm** one.
  · Zero → `stopListening(true)` **exactly once**, with `engine.stopped === 1` (flushed first).
  · **Flush proof:** the buffer at submit was `"আমার জ্বর — এবং গলা ব্যথাও আছে"`, i.e. it **included the
    tail the engine only released on `stop()`** — without the flush that tail is silently lost.
  · Window length is genuinely server-driven: `countdown_ms: 30000` → the digit showed **৩০**.
  · `voice_loop=manual` → no countdown, nothing submitted, old "tap again" hint (S25 behaviour intact);
    Type mode → no countdown, mic hidden.
- Notes: **The human's live real-mic run PASSED.** Synthetic events prove the state machine, not real
  Bangla endpointing — but the live run covered that. Zero console errors, zero server errors.

## 2026-08-08 — Session 28 — Requirement 3 step S3 (auto-listen): suite 222 → 234, plus a real-browser timing check
- Setup: `pytest backend/tests/` (static-source assertions over `/kiosk.js` and `/shared/tts.js`)
  **plus** an instrumented Chrome check via the in-app preview: `toggleListening` was replaced with a
  spy so the arming logic could be timed **without touching a microphone**. Default (non-Bangla)
  system voice; `banglaVoiceAvailable() === false`, 3 voices installed.
- Metric(s): number of mic-opens per question; delay from question start → mic open; whether TTS was
  still audible at that instant (`speechSynthesis.speaking`).
- Result:
  * `pytest backend/tests/` → **234 passed** (was 222; +12 in `test_kiosk_auto_listen.py`, zero
    regressions, 13.4 s).
  * **`/api/config` is really consumed:** the kiosk loaded
    `{voice_loop: auto, countdown_ms: 3000, tts_guard_ms: 400, no_speech_ms: 10000,
    max_answer_ms: 120000}` from the server at page load.
  * **Normal question:** exactly **1** mic-open, at **926 ms**, with `speaking === false` — TTS ended
    (~526 ms) and the 400 ms guard elapsed. The length-based safety net (which would have fired at
    3680 ms) correctly did **not** double-fire: the token was already consumed.
  * **🔴 The echo case — the one that matters for rule #1.** Two questions 200 ms apart (the second
    cancels the first): **exactly 1** mic-open, at **1057 ms**, i.e. after the SECOND question
    finished. The cancelled utterance's `onend` — which Chrome does fire on `cancel()` — did **not**
    open the mic during question 2. Without the generation token in `tts.js` this is precisely how
    the AI's own voice would have been transcribed into a `patient` utterance.
  * **Mode switch cancels a pending arm:** `setInputMode('type')` 150 ms after a question → **0**
    mic-opens.
  * **`voice_loop=manual` is untouched behaviour:** **0** mic-opens, hint stays "Tap the mic when you
    are ready to speak" — identical to the passed S25 run.
  * **No TTS at all** (`window.speechSynthesis` deleted → `speak()` returns false): mic opened at
    **416 ms**. The kiosk cannot freeze when speech synthesis is missing or silently degraded.
  * **Zero browser-console errors and zero server errors** across the whole session.
- Caveat (honest): the microphone itself was **never opened** — `toggleListening` was a spy, so this
  measures *when the kiosk decides to listen*, not that recognition starts, that Bangla is recognized,
  or that no echo is captured by a real microphone in a real room. Echo was disproven only at the
  *scheduling* level. Live-run items 1, 7 and 8 (§K) remain the real gate, and the machine used here
  has **no Bangla voice installed**, so the Bangla TTS path is still unexercised.

## 2026-08-08 — Session 28 — Requirement 3 step S2 (voice/typing mode switch): suite 211 → 222, plus a browser check
- Setup: `pytest backend/tests/` (static-source assertions over the served `kiosk.html` / `kiosk.js`,
  the `test_routes_static.py` pattern) **plus** a real Chrome render check via the in-app preview
  against a local uvicorn on port 8001. **No microphone was used and none was needed** — S2 changes
  which input the patient may choose, not the turn-taking.
- Metric(s): test pass/fail; rendered state of both docks; console/server errors.
- Result:
  * `pytest backend/tests/` → **222 passed** (was 211; +11 in `test_kiosk_input_modes.py`, zero
    regressions, 13.7 s). Asserted: both docks carry the two controls · `aria-pressed` on each ·
    bilingual `data-en`/`data-bn` labels · the old "Microphone issue? Type instead" link is **gone** ·
    both typed inputs + send handlers survive · voice is the default at load and after logout ·
    Voice→Type **discards** the un-submitted buffer · a dead mic switches the patient to typing ·
    one switch updates both docks · voice and typing still share one pipeline (`mic`/`manual`).
  * **Browser check (Chrome, 1280×720):** voice default → "🎤 Speak" filled teal, mic button shown,
    typed row hidden, hint "Tap the mic when you are ready to speak". Clicking "⌨ Type" →
    `inputMode='type'`, mic `display:none`, typed row `flex`, **input auto-focused**
    (`activeElement=fallback-input`), hint "Type your answer, then press Send", **and the resume dock
    switched with it** (`resume-mic-btn` hidden, `resume-fallback-row` flex). Switching back restored
    voice. EN→BN toggle re-rendered both labels ("🎤 বলুন" / "⌨ টাইপ করুন") and the hint.
    **Zero browser-console errors and zero server errors.**
- Caveat (honest): this is a **rendering + wiring** check, not a clinical-flow check — no visit was
  created, no answer submitted, no LLM called, and the mode switch was exercised on a screen forced
  open with `showScreen()`. The end-to-end typed-answer path (Type → Send → M8 merge → next question)
  is still only covered by the pre-existing backend tests, and the real mic/TTS behaviour remains
  entirely unproven until the 12-point live run (§K).

## 2026-07-11 — Session 24 — P4-1 real OTP: suite 177 → 192, all offline; live end-to-end verified on the dev server
- Setup: Python 3.14 on Windows; in-memory SQLite via dependency override; the OTP sender replaced
  by a recording fake (no SMS, no network); TextBee HTTP layer mocked (`httpx.post` monkeypatched).
  Live check: real uvicorn dev server on port 8001 (real SQLite DB, DevLogSender).
- Metric(s): test pass/fail; HTTP statuses; hash-only storage; bypass containment.
- Result:
  * `pytest backend/tests/` → **192 passed** (was 177). New: `test_otp.py` (13) +
    `test_migration_0012.py` (2). Zero regressions — the default config (dev channel + bypass on)
    reproduces the old stub behavior, so no existing test needed changes.
  * Security properties each locked by a test: hash≠plaintext in `otp_codes` + audit row carries
    no code · expiry (backdated → 401) · wrong code 401 + attempts increment · single-use
    (2nd verify of a consumed code → 401) · bypass matrix (dev+flag → 200; dev+flag-off → 401;
    **textbee+flag-ON → 401**, the production-impossibility proof) · lockout (5th wrong → 429,
    then 429 even for the CORRECT code; fresh code unlocks) · resend throttle (2nd lookup in 60 s:
    sender called once, `otp_sent=false`, `retry_after` 1–60; after cooldown the old code is void) ·
    send-failure → 502 + code voided · `get_sender` selection (dev/textbee/missing-creds/unknown) ·
    TextBee request contract (URL/`x-api-key`/recipients/message) + HTTP-500/network → OtpSendError.
  * Migration gates: fresh DB → head has `otp_codes` (no plaintext column); 0011 DB with a visit
    upgrades in place (row survives, empty otp_codes appears).
  * LIVE (dev server): startup log shows `0011 → 0012` applied; `POST /patients/lookup` printed
    `[OTP] verification code for +8801766666666: 130303`; wrong code → **401**; real code → **200**
    + `in_progress` visit; `000000` → **200** (dev channel). Throttled re-lookup returned
    `otp_sent=false` earlier in the same sequence.
- Notes: The live check first FAILED to show the OTP log line — root cause was a pre-existing bug:
  `migrations/env.py` `fileConfig(alembic.ini)` with default `disable_existing_loggers=True`
  silenced every `uvicorn.*` logger at startup (the entry-point banner and access logs had been
  invisible after migrations too). Fixed with `disable_existing_loggers=False`; DevLogSender logs
  via the `uvicorn.error` logger (same channel as main.py's banner). No LLM calls anywhere in the
  OTP path (rule #4-safe).

## 2026-07-10 — Session 23 — P3-1/P3-2/P3-3: suite 166 → 177, all offline; P2-3/P3-4 preview-verified
- Setup: Windows desktop; `pytest backend/tests/` with `PYTHONIOENCODING=utf-8`; LLM + ddgs
  boundaries faked (rule #4 — zero live API spend); migration gates on throwaway SQLite files;
  UI checks in the browser preview with a stubbed `window.api`.
- Metric(s): pass/fail; migration data preservation; the P3 behavioral guarantees.
- Result: **177 passed, 0 failed, ~8 s** (was 166). New suites:
  * `test_submitted_at.py` (3, P3-1): submit stamps `submitted_at` exactly once and returns it —
    a second submit 409s and the stamp cannot move; the medic queue row AND the visit detail
    carry the identical timestamp; assign→doctor-queue + review transitions never clobber it.
  * `test_migration_0011.py` (2, house-style DB gates): fresh DB → head has nullable
    `visits.submitted_at`; a 0010 DB with an existing visit upgrades in place (row survives,
    `submitted_at` NULL — the frontend falls back to `started_at` for such rows). Real dev DB
    migrated 0010→**0011** at server restart, data untouched. (Note re-confirmed: uvicorn
    `--reload` does NOT re-run startup migrations — a real restart is needed.)
  * `test_doctor_sees_medic_edits.py` (1, P3-2): end-to-end — medic field edit + C1 replacement +
    risk override + POST-forward identity/vitals PATCH are ALL visible to the doctor (queue row:
    human tier + new name/problem; detail: new vitals/identity; profile: `source=human` with the
    C1 disclaimer surviving the edit; /risk: `model_provider=human`).
  * `test_assistant.py` (5, P3-3/M16): happy path returns answer + sources + BOTH disclaimers and
    logs an `ok` M16 `module_events` row; dead search degrades to a sourceless answer (prompt
    says "search unavailable"); `_search` swallows ddgs exceptions → `[]`; a non-JSON model reply
    is salvaged as the answer with the disclaimer still attached; dead provider chain → 502,
    unknown visit → 404 (guard fires BEFORE any LLM call), short question → 422.
- Notes: browser-preview verification (frontend items, no pytest surface): P2-3 medic full flow
  (queue Dhaka time 04:30Z→10:30, verbatim speaker-label spacing fix, `.card` radius 10px);
  P3-1 doctor "Submitted" row renders `10 Jul 2026, 20:00` for a 14:00Z instant ("১০ জুল, ২০২৬"
  in Bangla) and a null-`submitted_at` queue row falls back to `started_at`; P3-3 panel (pending
  state, Q/A bubbles, source links, disclaimers in bar + under every answer, EN↔BN); P3-4
  safety-panel 10px + prescription form hex-free with Diagnosis empty. No console errors anywhere.

## 2026-07-10 — Session 22 — P2-2 patient demographics: suite 162 → 166, all offline
- Setup: Windows desktop; `pytest backend/tests/` with `PYTHONIOENCODING=utf-8`; LLM boundary
  faked via the standard `_attempt` monkeypatch (rule #4 — zero live API spend).
- Metric(s): pass/fail; the four P2-2 behavioral guarantees.
- Result: **166 passed, 0 failed, 6.86 s** (was 162). New `test_patient_demographics.py` (4
  tests): (1) `patient_demographics` in the M3 extraction ("আমার নাম রহিম উদ্দিন, বয়স ৪৫") writes
  `display_name="রহিম উদ্দিন"`, `sex="male"`, `birth_year=current_year-45` on intake; (2) a LATER
  extraction claiming different demographics does NOT overwrite the already-set values
  (fill-only-when-empty); (3) an absent `patient_demographics` key OR malformed values (age 500,
  sex "banana") are silently ignored — no crash, no garbage written; (4) a staff PATCH
  (`display_name`/`sex`/`age_years`) sets the identity AND is final — a subsequent AI extraction
  with different demographics cannot override it; PATCH validation confirmed (`sex` outside
  male|female|other → 422; an edit with no fields → 400). One pre-existing test needed updating:
  `test_medic_summary.py::test_vitals_patch_updates_and_audits` asserted strict equality on the
  audit `detail` dict, which now also carries the 3 new (mostly-`None`) identity keys — fixed by
  auditing only the fields actually sent, which also fixed the assertion.
- Notes: P2-1 (Dhaka time fix) and P1-6 (kiosk teal retint) were verified live in the browser
  preview the same session — frontend/formatting-only, no pytest surface. P2-1 unit-checked with
  known UTC instants directly in the console: offset-less `2026-07-10T06:30:00` → **12:30** (the
  exact bug reproduced and fixed — Dhaka is UTC+6), `18:00Z` → `00:00`, `+00:00` → `06:00`, Bangla
  digits "১২:৩০ PM", invalid string → "—".

## 2026-07-10 — Session 21 — P1-5 background-assessed submit: suite 159 → 162, all offline
- Setup: Windows desktop; `pytest backend/tests/` with `PYTHONIOENCODING=utf-8`; LLM boundary
  faked via the standard `_attempt` monkeypatch (rule #4 — zero live API spend).
- Metric(s): pass/fail; the three P1-5 behavioral guarantees.
- Result: **162 passed, 0 failed, 6.08 s** (was 159). New `test_submit_background.py` (3 tests):
  (1) after `POST /submit` returns, the background job has stored the RiskAssessment (tier high) +
  XaiExplanation + C1 `suggested_condition`, and the medic queue shows the tier; (2) with
  `assess_visit` monkeypatched to raise, submit still returns **200 / awaiting_review**, the visit
  is queued (tier None → "—"), and nothing is rolled back — a background crash can never block or
  undo a submission; (3) with a red-flag phrase ("বুকে ব্যথা") and the M10 model call RAISING, the
  background job still stores **tier=critical, rule_overrode=True** with a stored deterministic
  reason — rule #3 survives the move off the request thread. All pre-existing submit-dependent
  suites (staff routes, risk, report/review, suggested condition, risk override) passed UNCHANGED —
  the job binds to the request's engine (`db.get_bind()`), so the tests' in-memory DB exercises the
  identical path.
- Notes: TestClient executes BackgroundTasks synchronously before returning, so offline tests can't
  measure the wall-clock win — the human live run will see submit drop from ~seconds (3 LLM calls)
  to instant.

## 2026-07-10 — Session 20 — P1-3 follow-up floor + deepening: suite 156 → 159, all offline
- Setup: Windows desktop; `pytest backend/tests/` with `PYTHONIOENCODING=utf-8`; all LLM calls
  faked via the standard `_attempt` monkeypatch (rule #4 — zero live API spend).
- Metric(s): pass/fail; loop-termination counts (the floor/cap invariants).
- Result: **159 passed, 0 failed, 6.57 s** (was 156). New `test_followup_min_questions.py` (3
  tests): (1) threshold met after answer 1 but the loop ends at **exactly 4** questions, Q2–Q4 via
  DEEPENING (incl. the non-JSON salvage path with empty gap list → `target_gap="deepening detail"`,
  and the M7 user msg for deepening calls carries an EMPTY missing list); (2) floor 10 > cap 5 →
  terminates at **exactly 5** (no infinite loop); (3) `scope=fields` resume loop unaffected —
  completes at **2** questions when both empty fields were asked. Two existing tests updated to the
  new spec: `test_followup_loop.py` (drives to the floor, asserts 4) and `test_resume_loop.py`
  (main loop no longer complete at 0 asked; re-serves the open question, no duplicate M7 spend).
- Notes: P1-4 (missing-field highlight) verified in the browser preview the same session (classes,
  bilingual chip EN↔BN, screenshot, no console errors) — frontend-only, no pytest surface. The
  live-run implication of P1-3: every visit now asks 4–5 M7 questions (≈3 extra Groq calls/visit).

## 2026-07-07 — Session 17 — LLM quota audit + quota-aware switching (ADR-0041) test gate
- Setup: Windows desktop; read-only SQL on `backend/prescreener.db` `module_events`; one read-only
  `GET https://openrouter.ai/api/v1/key`; then the new switching code + pytest.
- Metric(s): usage counts; provider error evidence; test pass/fail.
- Result: lifetime API usage = **33 events / 2 visits** (gemini_flash 4 ok · flash-lite 14 ok ·
  groq 4 ok · openrouter **10 error, 0 ok** · local 1). Visit 7 = the clean Session-8c run
  (13/13 ok — matches the S8c log ✅). Visit 8 (2026-07-06 15:18 UTC) = **M4 429-failed 10× in
  ~9 s on OpenRouter** (`meta-llama/llama-3.3-70b-instruct:free` RPM limit) with the Gemini Flash
  attempt unlogged — the "transcribes but doesn't format" bug. OpenRouter key check: free tier,
  $0 usage, no custom limit. After the ADR-0041 fix: `pytest backend/tests/` = **156 passed**
  (150 prior + 6 new in `test_llm_client.py`: per-attempt logging, 429 cooldown + skip,
  no-cooldown on non-quota errors, fail-open, all-failed logging, chain order/key gating).
- Notes: free limits researched (2026): Gemini Flash ≈10 RPM/1,500 RPD (reset midnight PT),
  Flash-Lite higher RPM, Groq ≈1,000 RPD (midnight UTC), OpenRouter `:free` ≈50 RPD,
  Cerebras ≈1M tok/day, Mistral ≈1B tok/month (2 RPM, trains on inputs). One full visit ≈13 API
  calls (~5 flash / ~5 flash-lite / ~4 groq) → ≈250–300 free visits/day. Root cause of the
  visit-8 Gemini 429 will be visible on the next live run thanks to per-attempt logging.

## 2026-07-07 — Session 16 — Module 7 (TTS) — Arch Linux 🔊 + mic: browser-level PASS (TC-V2 audio)
- Setup: **Arch Linux laptop**, Chromium 149.0.7827.200 (Wayland), `speech-dispatcher 0.12.1` +
  `espeak-ng 1.52.0` installed. Started the daemon + `systemctl --user start
  speech-dispatcher.socket` (was enabled, not active); full Chromium restart (`pkill chromium`)
  relaunched with `--enable-speech-dispatcher`.
- Metric(s): `speechSynthesis.getVoices()` non-empty in Chromium · kiosk 🔊 speaks · mic works.
- Result: **PASS (human-confirmed).** Before restart `getVoices()` was `[]` (0 voices) — Chromium
  had cached an empty list from a pre-install process start + no running daemon. After the socket
  activation + full restart, `getVoices()` returns voices (incl. `bn`), 🔊 audio plays, and the mic
  works → **TC-V2 audio PASS on Arch**.
- Notes: root cause of the empty list = (1) stale Chromium process predating the package install
  (voices read only at process start), (2) daemon not running + Chromium sandbox can't spawn it →
  fixed by the enabled `speech-dispatcher.socket` (see ADR-0040). Still pending (HUMAN, full live
  run, not this test): TC-V1 (WER/latency), TC-V3 (voice-only loop), TC-F2, TC-R1, TC-A1. No app
  code changed.

## 2026-07-07 — Session 15 — Module 7 (TTS) — Arch Linux Bangla voice: system-level PASS
- Setup: **Arch Linux laptop**, Chromium (no Google Chrome). Installed `speech-dispatcher 0.12.1-3`
  + `espeak-ng 1.52.0-1` via `sudo pacman` (the human ran the install; the rest run headless).
- Metric(s): Bangla (`bn`) voice present in the synth · Bengali text renders real audio · the
  speech-dispatcher daemon (what Chromium reads voices from) is reachable.
- Result: **system layer PASS.** `espeak-ng --voices` lists `bn` (Bengali, `inc/bn`); `espeak-ng`
  is a registered speech-dispatcher output module; rendering `আমার মাথা ব্যথা করছে` produced a
  valid **81,202-byte WAV** (RIFF PCM, 16-bit mono, 22050 Hz); `spd-say` exits 0 (daemon reachable).
- Notes: this is the root-cause fix for the silent kiosk 🔊 on Arch (packages were simply missing;
  `tts.js` was degrading correctly per ADR-0028). **Browser layer still human-pending** (needs a
  full Chromium *restart* + real audio hardware I can't drive from the shell): confirm
  `speechSynthesis.getVoices().filter(v=>v.lang.startsWith('bn'))` is non-empty, the kiosk
  `#voice-hint` banner disappears, and 🔊 speaks aloud → that completes **TC-V2 on Arch**. Voice is
  espeak-ng-robotic (expected; on-screen text stays primary). No application code changed.

## 2026-07-07 — Session 14 — Step 20 (final): 150-test gate re-confirmed; docs-only sweep
- Setup: Windows dev box, venv Python 3.14, `pytest backend/tests/`. No code changed this session
  — step 20 flips stale ✅ markers in `context_fixed_problem.md` + doc sweep only.
- Metric(s): pytest pass count (regression gate).
- Result: **150/150 pass** (~7.7 s), unchanged from S13 — confirms the closing sweep touched no
  application code. No new tests (the S13 entry details the current suites).
- Notes: the 20-step build is complete. Still pending (HUMAN, not build): the live real-mic run
  (TC-V1/V2/V3/F2/R1/A1) + installing a Bangla TTS voice on Windows. The 15-module status board
  stays 🟨 until those live numbers are recorded.

## 2026-07-06 — Session 13 — Steps 17–19: suite 139 → 150, all offline; doctor patient-card + prescription form/.docx browser- and live-verified
- Setup: Windows dev box, venv Python 3.14, `pytest backend/tests/` after each step. In-memory
  SQLite (StaticPool) + tmp-dir document storage; zero live LLM calls (rule #4). Browser checks
  on the running uvicorn (port 8001) with `window.api`/`fetch` stubbed for mutating calls; plus
  ONE real end-to-end prescription POST/curl (the .docx is LOCAL — no LLM — so it was safe to run).
- Metric(s): pytest pass count; behavioral assertions per endpoint/screen; live docx content.
- Result: **150/150 pass** (139 → +6 `test_prescription_context.py` → 145 → +5
  `test_prescription_docx.py` → 150). Step 17 (DOCTOR-3) was frontend-only (no test delta).
  `test_prescription_context` (6): context returns seeded letterhead (clinic + doctor); contract
  holds with NULL letterhead; 404 unknown visit, 404 unknown doctor, **400 non-doctor role**;
  `seed_demo_letterhead()` idempotent + non-clobbering (a custom qualification survives, a NULL
  slot is filled once). `test_prescription_docx` (5): POST persists a `prescriptions` row + a
  linked `documents` row (kind `prescription`, `visit_id` set, `utterance_id` NULL); the .docx
  contains clinic/patient/**typed diagnosis "Viral fever"**/medicine "Napa 500mg"/tests "CBC";
  **rule-#2 regression** — POST with EMPTY diagnosis while a `suggested_condition` (GERD) is stored
  → the docx contains neither "GERD" nor "Acid Reflux" (the writer reads only the payload, so the
  AI condition is structurally incapable of leaking into Diagnosis); 400 non-doctor, 404 bad visit.
- Live end-to-end (real server + real dev DB, no LLM): `POST /api/visits/{uuid}/prescription`
  (doctor 2) → `{prescription_id:1, document:{kind:"prescription", download_url}}`; downloaded the
  .docx and confirmed it contains Viral fever + Napa + 500mg + Demo Clinic + Kamal Hossain + CBC +
  Signature. `GET .../prescription/context` returned the seeded letterhead live; unknown-doctor and
  bad-visit both 404.
- Browser (eval + a11y + working screenshots): DOCTOR-3 patient card shows Name/Phone/Age 41
  (from birth_year 1985)/Gender/Weight/BP, the C2 band "HIGH 51–75%" beside the tier, the C1
  condition card + disclaimer; vitals edit fires `PATCH /patients/42/vitals` `{editor_id,weight_kg,
  bp}` and updates, empty/invalid-weight guards block the call. Prescription form: letterhead +
  patient + symptoms autofill, **Diagnosis empty on load**, medicine add/remove + language-toggle
  keep typed values, ≥1-row guard, payload correct; Submit POSTs `{doctor_id, payload}`,
  auto-downloads (anchor href `/api/documents/…/download`, filename), shows "✅ Saved & Downloaded".
  EN↔বাংলা switches all chrome; raw verbatim + patient name never translated (rule #1). Zero
  console errors throughout.
- Notes: preview server stopped between edits twice (restarted cleanly; the startup letterhead
  seed only runs on (re)start). Human eyeball still wanted: the full `/doctor/` prescription flow
  through the real UI against an assigned case, in EN + বাংলা (Ctrl+F5 first). The live curl left
  one demo `prescription_id=1` row in the dev DB (harmless). Prescription rendering / real-mic
  run (TC-V2/V3/F2/R1/A1) remain the human's live tasks.

## 2026-07-06 — Session 12 — Steps 14–16: suite 129 → 139, all offline; medic condition/post-referral + doctor toggle browser-verified with stubbed network
- Setup: Arch Linux laptop, venv Python 3.14, in-memory SQLite (StaticPool) + tmp-dir document
  storage, `llm_client._attempt` monkeypatched (zero live LLM calls — rule #4). Browser checks
  on the running uvicorn (port 8001) with `window.fetch` stubbed for all mutating calls.
- Metric(s): pytest pass count; behavioral assertions per new endpoint/screen.
- Result: **139/139 pass** (~6.3 s). New `test_suggested_condition.py` (5): bilingual M10C
  suggestion stored at submit with `source:'ai'` + BOTH disclaimers + its own `module_events`
  row (provider gemini_flash); LLM failure → submit still 200 and no suggestion key; no
  profile → still submits; staff edit fills all language slots untranslated, `source:'human'`,
  audit `profile.condition_edit`, disclaimer re-attached; guards 403 (desk/unknown editor),
  404, 422 (empty condition), 400 (no profile). New `test_medic_summary.py` (5): patient
  (with vitals) embedded in GET /visits/{uuid}; vitals PATCH updates + audits
  (`patient.vitals_edit`, detail weight/bp); guards 403/404/422 (weight −3 and 700)/400
  (nothing to update); summary_report .docx contains the C1 label + condition (EN+BN) +
  reasoning + C1 disclaimer + "72.5 kg" + "130/85" + M12 disclaimer; **staleness regression**:
  field edited AFTER a first download → second download shows the new value (fresh report,
  ADR-0037).
- Browser (eval + a11y snapshot; screenshot tool worked early, then timed out again):
  medic condition card renders EN↔BN with badge/reasoning/disclaimer, empty state, edit
  round-trip (PATCH url+body captured, re-renders Human Edited, empty-value blocked);
  post-referral screen shows doctor name, age 41 computed from birth_year 1985, weight edit
  (invalid −5 blocked client-side; 72.5 saved via PATCH), download anchor gets the right
  `download_url`/filename, Back-to-Queue resets state; doctor portal: ↻ Queue gone,
  15 data-bn nodes, BN subtitle/buttons/placeholders/red-flag line/tier badge (ঝুঁকিপূর্ণ),
  `@media print` rule present, not-assessed state renders. Zero console errors.
- Notes: rule #1 untouched (no utterance writes anywhere in these paths); rule #2 boundary
  carried: the C1 disclaimer is asserted as a PAYLOAD property, and step 18 must default the
  prescription Diagnosis to EMPTY. Human eyeball still wanted: `/medic/` after a real forward
  and `/doctor/` in বাংলা (Ctrl+F5 first).

## 2026-07-06 — Session 11 — Steps 8–13: suite 121 → 129, all offline; kiosk + medic flows browser-verified with stubbed network
- Setup: Windows dev box; `pytest backend/tests/` after every step; live Chrome preview
  against the real server (port 8001) with `window.fetch` REPLACED by spies for every
  flow test — zero live LLM calls, synthetic data only (rule #4). Cache rule applied
  throughout (`fetch(url,{cache:'reload'})` + reload before asserting).
- Metric(s): pytest counts; scripted DOM assertions pass/fail.
- Result: **129/129 pass** (was 121; +5 `test_resume_loop.py`, +3 `test_risk_override.py`;
  both new suites green on first run). Key offline assertions now enforced:
  (a) resume scope ignores the 0.7 threshold (8/10-filled visit still gets a question);
  (b) `target_gap` forced to a real field key; a field answered "নেই" is NOT re-asked and
  "জানি না" on the last empty field ends the loop complete at score 0.8, both raw answers
  stored verbatim (rule #1); (c) cap=0 → complete immediately (never trap); (d) 10/10
  filled → complete with ZERO M7 calls; (e) `?scope=bogus` → 422; (f) risk override
  appends a `model_provider='human'` row (AI row untouched, 2 rows total), audit_log
  detail == {from: 'medium', to: 'high', reason}, GET /risk AND the dashboard queue serve
  the human tier; (g) red-flag Critical downgrade → 409, re-affirming critical carries
  red_flags + rule_overrode forward, and the carried flags keep blocking later downgrades;
  (h) bad tier code → 422 (C2: codes only). Browser: kiosk resume walk-through
  (8/10 chip → Q1 spoken+shown → 9/10 → Q2 → 10/10 green chip, dock gone, submit back;
  Bangla chip "৮/১০ তথ্য সম্পন্ন"; fail-open on network error), KIOSK-4 download POST +
  anchor click, KIOSK-5 computed styles (18px radius, blur(8px), accent border
  rgb(42,117,211)), KIOSK-6 EN↔BN value swap with legacy-row fallback, medic full EN↔BN
  round-trip with the RAW Banglish utterance byte-identical both ways, MEDIC-3 panel
  (Moderate·26–50%·AI-Assessed → override POST → High·51–75%·Human Set). Zero console
  errors everywhere.
- Notes: `preview_screenshot` timed out all session (tool issue; page healthy — evidence
  via preview_eval + a11y snapshot). Human should eyeball /kiosk.html + /medic/ once.
  Real-M7 resume questions over Groq intentionally untested — belongs to the live re-run.

## 2026-07-06 — Session 10 — Steps 6–7: kiosk OTP + TTS UX; TC-V2 PARTIAL result (Windows: no bn voice)
- Setup: Windows dev box; live Chrome preview against the real server (port 8001); scripted
  DOM events via preview_eval (no DB writes — screens driven directly); `speak()` spy for
  TTS wiring so no audio was needed. `pytest backend/tests/` after each step (both frontend-
  only). ⚠ Verification gotcha: a CACHED kiosk.js produced false failures — always
  `fetch(url, {cache:'reload'})` + reload before asserting.
- Metric(s): behavior pass/fail per scripted assertion; TC-V2 voice availability per OS.
- Result: **121/121 tests still passing** (no backend change). Step 6 (KIOSK-1 OTP): 5/5
  scripted checks PASS — typing 000000 fills all six with focus advancing each keystroke;
  non-digit rejected; Backspace on empty box clears+focuses previous; paste "code: 04-73-92"
  → 047392 focus last; paste "123" → fills 3, focus box 4. Step 7 (KIOSK-2/3): 6/6 PASS —
  🔊 icon on every bubble (2/2 rendered); assistant icon spoke the exact question; patient
  icon spoke the EXACT captured raw words (rule #1); Repeat button spoke the last question;
  hint banner shows when `banglaVoiceAvailable()` is false and hides when true.
- **TC-V2 (partial, Windows):** `banglaVoiceAvailable()` = **false** on this machine — NO
  bn/bn-BD voice in `speechSynthesis.getVoices()`. This is the CONFIRMED root cause of the
  human-reported "Repeat Question does nothing": the code always fired; the OS had no voice
  to speak with. Per Open Flag 4 / ADR-0028 the on-screen text fallback + the new visible
  hint banner = graceful degradation (verified). TC-V2 with real AUDIO still needs: install
  a Bengali voice (Settings → Time & Language → Speech → Add voices), then re-check that
  the banner disappears and audio plays. Arch laptop still unmeasured.
- Notes: TC-V3/F2/R1/A1 (real-mic run) remain pending — re-run after steps 8–11 land.

## 2026-07-05 — Session 9 — Fix/feature build steps 1–5: suite 104 → 121, all offline (no live LLM)
- Setup: Python 3.14 on Windows (`.venv`); `pytest backend/tests/` after every step; all new
  tests offline per rule #4 (LLM boundary faked; temp-dir document storage; throwaway SQLite
  files for migration gates). Browser checks via the preview panel on the real server (port 8001).
- Metric(s): test count / pass rate per step; migration data-preservation; docx content checks.
- Result: **121/121 passing** (was 104). Step-by-step: +5 `test_routes_static` (all 5 entry
  points 200; legacy isolated at /legacy/; landing links all four; kiosk untouched) → 109.
  +4 `test_migration_0010` (legacy-DB upgrade keeps raw text byte-identical + document link;
  fresh DB has prescriptions table + all new columns; visit-grain document inserts with
  utterance_id NULL; prescription JSON payload round-trips) → 113. +3 `test_visit_documents`
  (transcript .docx contains all 4 Bangla raw turns BYTE-EXACT in order; summary report has
  10 bilingual labels + stored values + vitals + no-diagnosis disclaimer; route guards
  400/404) → 116. +5 `test_bilingual_fields` (en+bn fill, plain-string salvage→English,
  legacy `{value}` rows validate + score 0.6, any-slot counting, bn-only counts) → 121.
  Rev 0010 applied to the REAL dev DB: upgrade 0009→0010 clean, head confirmed, backup
  `prescreener.db.pre-0010.bak` taken first.
- Browser verification (step 4, real Chrome preview, zero console errors): `fieldValue()`
  legacy `{value}` ✓ · en pick "Headache" ✓ · bn pick "মাথা ব্যথা" ✓ · cross-language
  fallback ✓ · whitespace/null → '' ✓ · `tierBand()` low '0–25%', critical '76–100%',
  unknown '—' ✓.
- Notes: two would-be bugs caught before shipping: legacy index.html's absolute
  `/styles.css`/`/app.js` refs (would 404 under /legacy/) and `documents.utterance_id`
  NOT NULL (would block every visit-grain export). Existing English-only stored rows stay
  as-is until re-extracted — readers fall back across slots (ADR-0033). TC-V2/V3/F2/R1/A1
  (human real-mic run) remain pending — re-run AFTER the kiosk fixes land (steps 6–11).

## 2026-07-03 — Session 8c — Live-run Part 1: FULL pipeline live (M3→M12), all three API buckets
- Setup: Python 3.14 on Windows; server via uvicorn port 8001. **All three keys real** in
  `backend/.env` (Gemini + Groq + OpenRouter — Groq/OpenRouter added this session). Driven by a
  scratch script over the REST API with SYNTHETIC typed Banglish (no mic; rule #4):
  lookup(01712345678) → OTP 000000 → visit → 2 utterances ("amar 3 din dhore matha betha ar
  halka jor ache", "raate ghum hocche na, matha ta dan dike beshi betha kore") → /intake →
  followup next/answer ×2 → /assess → /report.
- Metric(s): end-to-end success; per-module provider + latency + fallback from `module_events`;
  loop exit; risk tier sanity; test-suite regression.
- Result: **PASS end to end.** `module_events` = 13 rows, **13/13 status=ok, 0 fallbacks**:
  M3=gemini_flash_lite (1658/1899 ms), M4=gemini_flash (8577/3714 ms), M6=groq (859/850 ms),
  M7=groq (671/484 ms), M8=gemini_flash_lite (1426/2516 ms), M10=gemini_flash (4093 ms),
  M11=gemini_flash (3437 ms), M12=local. Providers match the ADR-0026 bucket map exactly.
  Follow-up loop: 2 real Bangla questions ("আপনার জ্বর কত দিন ধরে আছে?", "আপনার শরীরের তাপমাত্রা
  কত ছিল?"), no repeats, exited complete=True at completeness 0.7. Risk: tier=**medium**,
  red_flags=[] (correct: 3-day headache + mild fever is not a red-flag case), M11 gave a
  plain-language reason. Report generated. `pytest backend/tests/`: **104 passed** (3.88 s).
- Notes: This effectively covers TC-F1 (M4→M6 direct, live) and the no-repeat/exit half of
  TC-F2 in a typed run; TC-V2/V3 (voice), TC-R1 (red-flag → Critical, live) and TC-A1
  (forced-fallback) still need the human Part-2 run. Windows console needs
  `PYTHONIOENCODING=utf-8` to print Bangla from scripts (cp1252 crash — cosmetic only).
  Keys were pasted in chat → rotate before any public demo.

## 2026-07-03 — Session 8b — FIRST live LLM call (Gemini M2 correction) + ADR-0029 doc rewrite
- Setup: Python 3.14 on Windows; `.venv`. Real `GEMINI_API_KEY` in `backend/.env` (Groq +
  OpenRouter keys EMPTY). One live call via
  `python -m backend.app.services.correction.openai_compatible "<synthetic Banglish>"`
  (model `gemini-flash-latest`). Synthetic data only (rule #4).
- Metric(s): does a real Gemini call succeed? does it obey the correction-only prompt (no
  translation / no diagnosis / same script)?
- Result: **PASS — the live Gemini path works** (first live verification in 8 sessions).
  * RAW:       `ami 3 din dhore onek jor ar mathabetha te vugchi, sathe kashi o ache`
  * CORRECTED: `ami 3 din dhore onek jor ar mathabethate bhugchi, sathe kashi o ache`
  * Behavior correct: fixed spelling only (`vugchi`→`bhugchi`, `mathabetha te`→`mathabethate`),
    kept Banglish/Roman script (NO conversion to Bangla), no translation, no diagnosis, no added
    symptoms (rules #1/#2 upheld). ~1 request spent.
- Notes: **Full live intake/loop is BLOCKED on keys, not code** — M6/M7 are Groq-bucket and both
  Groq + OpenRouter are empty, so `provider_chain_for_module` returns [] → LLMCallError for those
  modules. Add a Groq OR OpenRouter key to run the full pipeline live. The real-voice kiosk run
  (mic) remains the human's task. TC-V2/V3/F2/R1(live)/A1(live) still pending.

## 2026-07-03 — Session 8 — Full-stack build: DB 0003–0009 + M3–M12 backend + 3 portals
- Setup: Python 3.14 on **Windows**; `.venv` (had to `pip install -r requirements.txt` — alembic
  was missing, S6 ran on Arch). Server on port 8001 via the preview tool. Unit/route tests on
  in-memory SQLite (StaticPool) with the **LLM layer faked** (no network, no quota); migration
  tests on throwaway SQLite files; real-DB migrations verified on a COPY then applied to the real DB
  (backups `prescreener.db.pre-000{3,4,5,6,7}.bak`). Browser checks via preview_eval/snapshot.
- Metric(s): test pass/fail; migration data-preservation; red-flag recall; API status; UI render.
- Result:
  * `pytest backend/tests/` → **104 passed** (was 19). New suites: `test_migration_0003` (4:
    legacy backfill keeps raw byte-identical, fresh schema + seeds, CHECK accepts medic/
    awaiting_doctor + rejects bogus, mixed-state-legacy regression), `test_routes_visits` (4),
    `test_intake` (3), `test_followup_loop` (4), `test_risk` (**~70** — every red-flag phrase is a
    parametrized case), `test_staff_routes` (2), `test_report_review` (2). The 19 baseline never
    regressed.
  * **TC-R1 (red-flag recall) — offline PASS with zero misses:** every phrase in
    `RED_FLAG_RULES` (5 categories, Bangla/Banglish/English) forces tier `critical`; verified it
    still forces `critical` when BOTH the M10 and M11 LLM calls fail (simulated outage), and when
    the phrase appears only in RAW (uncorrected) text. Benign text triggers nothing. Model failure
    WITHOUT a flag degrades to `medium`, never silently `low` (rule #3).
  * **Migration data preservation:** real Windows DB (mixed-state legacy: had `stt_provider`,
    lacked `documents.kind`) migrated `→ 0009`; **5 utterances preserved, raw byte-identical, 5
    synthetic closed visits backfilled, 0 orphans**; re-run is a no-op (idempotent). Also fixed a
    latent crash: blind stamp-at-0001 died with `duplicate column name: stt_provider`;
    `_legacy_stamp_revision()` now stamps by actual columns (regression-tested).
  * **Fallback logging (TC-A1, offline):** forcing the primary provider to fail makes intake fall
    to OpenRouter and logs `module_events.status='fallback'` with the provider — verified per module.
  * **Browser smoke (no quota spent):** `/kiosk.html` → phone `1715984632` → OTP `000000` →
    conversation screen with the Bangla opening question rendered AND queued for TTS; 0 console
    errors, 0 failed network requests, Bangla renders correctly (Noto Sans Bengali). `/medic/`
    login → seeded "Medic Rahman", doctors dropdown populated, empty queue (correct — nothing
    submitted). `/doctor/` login → "Dr. M. Rahman", assigned queue renders.
- Notes: NOT yet run — the LIVE end-to-end with real Gemini/Groq keys (intake/followup/assess/xai
  actually calling the models). That's the human's next step (spends quota; rule #4 synthetic data
  only). Still open: TC-V2 (bn-BD TTS voice availability per OS), TC-V3 (voice-only reply loop),
  TC-F2 on real speech, real-data accuracy for M3/M10, WER/latency, and the S4–S6 mic test + ~50
  samples.

## 2026-06-25 — Session 7 — Architect planning lock (no code run)
- Setup: Planning/documentation session only. No server started, no `pytest` run, no
  models executed. Working code is unchanged from Session 6 (still 19 tests on disk).
- Metric(s): none (nothing executed).
- Result: N/A — see the "Planned test cases" block above for the test contract added this
  session (TC-V1…TC-R1). The 19-passing-tests figure from 2026-06-21 still stands because no
  code changed.
- Notes: The Emergency module was retired and replaced by a rule-based red-flag check in
  Module 10 (ADR-0024); TC-R1 makes red-flag recall a first-class, measured metric so the
  safety change is verifiable. Next executable test will be TC-V2 (browser TTS) once Phase A
  Step A1 is built.

## 2026-06-21 — Module 1 (+ doc export) — Two separate raw/corrected .docx + Alembic migration
- Setup: Python 3.14.3 on **Arch Linux**; `.venv`. Added `alembic==1.14.0`. Server run on
  port 8001 via the preview tool (`backend-linux` launch config). Unit tests on in-memory
  SQLite (StaticPool for the route test) + temp-dir storage + a fake corrector; migration
  tests on throwaway SQLite FILES; end-to-end checks via preview_eval against the real DB/FS.
- Metric(s): test pass/fail; migration correctness + data preservation; file validity
  (bytes, Word content-type); HTTP status/headers.
- Result:
  * `pytest backend/tests/` → **19 passed in ~1.2s** (raw_immutable 3 + corrector 4 +
    docx_writer 5 + documents_repo 4 + migration 2 + routes_documents 2). The docx_writer
    tests assert raw doc holds RAW verbatim and NOT the correction, and vice-versa (rule #1).
  * **DB bug FIXED & verified.** Before: live `utterances` had columns up to `corrected_at`
    but NO `stt_provider`. After `run_migrations()` on the real DB: `stt_provider` +
    `documents.kind` present, `alembic_version = 0002_add_stt_provider_and_doc_kind`, and
    **both original utterance rows preserved (count = 2)**. Fresh-DB path (0001→0002) builds
    the full schema from scratch; a second `upgrade head` is a no-op. Migration unit tests
    (legacy-DB-keeps-rows + fresh-DB-full-schema) pass. Pre-migration DB backed up to
    `backend/data/prescreener.db.pre-alembic.bak`.
  * End-to-end in the browser (manual-text path; no Gemini): typing a Banglish utterance +
    "Use this text as RAW" → raw saved, **raw .docx generated**, "Download Raw .docx" button
    enabled, `GET /api/documents` lists kind=`raw` filename `raw-session-3-20260621.docx`,
    and downloading it → HTTP 200, Content-Type
    `application/vnd.openxmlformats-officedocument.wordprocessingml.document`, **36,913 bytes**.
    Both download buttons start disabled (is-disabled, no href). Startup logs: 0 errors.
  * Route integration test (TestClient, fake corrector): save → raw .docx → GET detail →
    400 on corrected-before-correction → correct (RAW unchanged, corrected stored) →
    corrected .docx → both files download as Word docs; unknown ids → 404.
- Notes: The LIVE Gemini correction in-browser + opening both .docx in Word/LibreOffice to
  confirm real Bangla rendering is still the human's manual check (not auto-run — saves free
  quota). The preview screenshot tool timed out (renderer); preview_eval gave conclusive
  functional proof. On Arch, launch the preview via the **`backend-linux`** config — the
  default Windows config fails with `spawn .venv/Scripts/python.exe ENOENT`. No WER/latency
  on real speech yet — still the human's next step.

## 2026-06-21 — Module 1 (+ doc export) — Auto .docx generation + list/download
- Setup: Python 3.14.4 on Windows; `.venv`. Added `python-docx==1.1.2`. Server run on
  port 8001 via the preview tool. Unit tests on in-memory SQLite + temp-dir storage;
  end-to-end checks via preview_eval (browser fetch) against the real DB/filesystem.
- Metric(s): test pass/fail; file validity (size, zip magic); HTTP status/headers.
- Result:
  * `pytest backend/tests/` → **13 passed in 1.78s** (3 raw_immutable + 4 corrector +
    4 docx_writer + 2 documents_repo). The 6 new tests include a rule-#1 guard at the
    export layer (RAW text appears verbatim in the rendered .docx).
  * End-to-end (no Gemini; correction inserted directly): generated a real **35,799-byte**
    `.docx`; file written under `documents_dir` named by UUID; `EXISTS=True`.
  * `GET /api/documents` → 200, lists the doc (id, utterance_id, format, filename,
    created_at). `GET /api/documents/{id}/download` → 200, Content-Type
    `application/vnd.openxmlformats-officedocument.wordprocessingml.document`,
    Content-Disposition `attachment; filename="session-5-20260621.docx"`, body 35,799
    bytes, first 2 bytes = `PK` (valid .docx/zip magic).
  * Frontend "Saved documents (.docx)" panel renders the row + mint-green download
    pill link (`/api/documents/{id}/download`); empty-state message shown when none.
    Server booted with 0 errors in logs.
- Notes: The LIVE Gemini correction + the .docx opened in Word/LibreOffice with real
  Bangla rendering is still the human's manual check (Bengali font set on Latin AND
  complex-script slots; needs a Bengali-capable font installed to render). No WER/
  latency on real speech yet — still the human's next step.

## 2026-06-20 — Module 1 — Browser-only simplification + Mintlify UI + scroll behavior
- Setup: Python 3.14.4 on Windows; venv RECREATED from requirements.txt (clean core:
  fastapi 0.115.6, starlette 0.41.3 — torch/transformers/qwen removed). Server run on
  port 8001 via the preview tool (port 8000 had an orphaned socket). Browser checks
  via preview_eval / console logs.
- Metric(s): test pass/fail; endpoint presence; CSS/JS behavior (fonts, scroll).
- Result:
  * `pytest backend/tests/` → **7 passed** (test_raw_immutable + test_corrector;
    test_stt_registry removed). 0 console errors on the page.
  * Routes now exactly: `/api/correct`, `/api/transcripts`, `/health` (+ static).
    `/api/stt/providers` → 404, `/api/transcribe` → gone. STT endpoints removed.
  * UI: Inter font loaded; Start button mint-green pill (rgb(0,212,164), radius
    9999px); transcript panels fixed-height 280px (220px mobile), overflow-y auto,
    scrollable.
  * Auto-scroll: sticks to bottom on append; scroll-up sets stick=false and append
    does NOT yank down; returning to bottom sets stick=true and append follows.
    Verified all four conditions true.
  * Mobile (375px): single-column grid, 220px panels, no horizontal overflow
    (bodyScrollWidth == viewport).
  * One live store→correct round-trip succeeded earlier this day (raw immutable,
    corrected separate).
- Notes: Live mic continuous-recording + ~10s-silence auto-stop is the human's
  manual Chrome check (can't automate the mic). No WER/latency on real speech yet.

## 2026-06-19 — Module 1 (infra) — Multi-provider STT: installs, health, transcribe paths
- Setup: Python 3.14.4 on Windows; `.venv`. Installed faster-whisper 1.1.0
  (requirements-whisper.txt), transformers 5.12.1→4.57.6 + torch 2.12.1 (banglaspeech),
  qwen-asr 0.0.6 (qwen). Synthetic 2-second 16 kHz WAV used to exercise the code path.
- Metric(s): test pass/fail; dependency resolution; transcribe-path success; provider health.
- Result:
  * `pytest backend/tests/` → **13 passed** (immutability + corrector + STT registry).
  * Dependency conflict RESOLVED: requirements-whisper.txt installed cleanly with
    huggingface-hub 1.20.1 (the old banglaspeech2text==0.0.7 / hub==0.11.1 pin is gone).
  * `torch==2.5.1` had NO Python-3.14 wheel; unpinned → torch 2.12.1 installed.
  * After all installs, `GET /api/stt/providers` → all 5 status=available, ready=True;
    app boots under fastapi 0.137.2 / starlette 1.3.1 (only a TestClient deprecation warning).
  * Transcribe code path validated on the synthetic clip (no crash, returns a str;
    empty text expected for a pure tone): local_whisper (faster-whisper base, int8)
    and banglaspeech2text (shhossain/whisper-base-bn via transformers).
- Notes: `qwen-asr` install was invasive (bumped fastapi/starlette/transformers/
  huggingface_hub, pulled gradio/flask) — app still works. NOT yet tested live:
  Groq STT (would spend free quota) and Qwen (3.4 GB download + very slow on CPU).
  No WER/latency on real Bangla speech yet — that is the human's next step. Rough
  latency ESTIMATES (10 s clip, CPU): Browser ~live; Groq ~1–3 s; local_whisper base
  ~2–5 s; banglaspeech base-bn ~10–25 s; Qwen ~30 s–minutes. Gemini correction +1–3 s.

## 2026-06-19 — Module 1 (infra) — Correction guards + API/frontend smoke test
- Setup: Python 3.14.4 on Windows; `.venv`. Backend served via the preview tool
  (uvicorn on port 8000). Browser checks via preview_eval / console logs.
- Metric(s): test pass/fail; HTTP status of endpoints; JS console errors.
- Result:
  * `pytest backend/tests/` → **7 passed** (3 immutability + 4 corrector guards).
  * Endpoints: `/`, `/app.js`, `/styles.css` → 200; `/api/transcripts` → 200 `[]`;
    `/health` → 200; routes = `/`, `/api/correct`, `/api/transcripts`, `/health`.
  * Frontend: page renders, all elements present, Web Speech API detected,
    **0 console errors**, recent-list fetch returned 200.
- Notes: Corrector guards are OFFLINE (no network) — empty input short-circuits,
  provider selection, missing-key → RuntimeError, unknown-provider → ValueError.
  The LIVE Gemini call (`POST /api/correct` / the module `__main__`) was NOT run
  this session (spends free-tier quota) — that is the human's Step-6 live test.
  No WER/latency numbers yet; those come from the live test on real utterances.

## 2026-06-19 — Module 1 (infra) — Raw-immutability guard + clean install
- Setup: Python 3.14.4 on Windows; `.venv`; deps from `requirements.txt`
  (fastapi 0.115.6, uvicorn 0.34.0, pydantic-settings 2.7.1, SQLAlchemy 2.0.51,
  openai 1.59.6, pytest 8.3.4). DB = in-memory SQLite for the test.
- Metric(s): test pass/fail (not an ML metric — this is an infra guard).
- Result: `pytest backend/tests/` → **3 passed in 0.43s**. Confirms: raw text is
  stored verbatim (spaces preserved), `set_correction` never alters `raw_text`,
  and the repository exposes no raw-mutating function.
- Notes: `pip install -r requirements.txt` succeeded with wheels only (no compiler)
  on Python 3.14. SQLAlchemy 2.0.36 crashed on 3.14 (typing-union bug) → upgraded
  to 2.0.51 (see ADR-0012). `git check-ignore` confirms `backend/.env` is ignored
  and `backend/.env.example` is tracked.

## 2026-06-18 — Setup
- No tests yet. Nothing built.
- First ML test will be: Phase 0 demo — can it transcribe ~10 spoken Bangla/Banglish
  sentences live, and is the raw text stored unchanged? (latency + a rough
  by-hand WER on those 10 sentences).
