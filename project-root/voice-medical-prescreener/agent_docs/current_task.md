# current_task.md — What We Are Doing RIGHT NOW

> This is a small, throwaway snapshot. It gets **overwritten** every session.
> It is NOT a history log (that is `changelog.md`). It answers only:
> "If I open a brand-new Claude Code session, what do I need to know to continue?"

---

**Date:** 2026-08-14 (end of Session 40)
**Phase:** **The S40 brief is COMPLETE.** The reported Medic-portal outage was root-caused and fixed,
the kiosk got its clarity redesign (1A–1F), and the test gap that let the outage ship is closed.
Test suite: **1031 passed, 2 skipped, 0 failures** (was 1005).
Alembic head: **0014** — unchanged. **18 tables. No new dependency. NO BACKEND FILE WAS TOUCHED.**
New ADR: **0065**. **No module changed status. M15 stays 🟨.**

**⚠ Step S5 is STILL NOT implemented and must not be assumed. See the bottom of this file.**

---

## 🚦 THE NEXT STEP — **a HUMAN pass over all three portals, and this time it is about how they LOOK**

Everything below was verified by **measuring the DOM in a real browser** — positions, sizes, computed
styles, state attributes, a real end-to-end kiosk session. That is precise about *where things are*
and *what state they are in*, and **completely silent about whether it looks good**. No screenshot
could be taken this session: the Browser pane was not displayed, so it composites no frames.

So the open question is the one only a person can answer, and for the kiosk it is specific:
**does it now read as SIMPLE to someone who has never used a computer?**

### Setup
- Your server on **8000** is fine — the app is port-agnostic (every front-end path is relative).
  S40 used 8001 (`.claude/launch.json`) and never touched the 8000 process.
  `.venv\\Scripts\\python.exe -m uvicorn backend.app.main:app --reload --port 8001`
- Hard-reload once (Ctrl-F5). The medic fix is in a served HTML file and 304s are exactly what
  the last session's confusion was made of.

### What is NEW in S40 and needs eyes
1. **MEDIC → the login button.** It works now. Click `ড্যাশবোর্ডে প্রবেশ করুন`, confirm the dashboard
   opens and the **clock in the header is running** (top right, 12-hour, Bangla digits in বাংলা).
   Both were dead before — one cause, see below.
2. **KIOSK → the conversation screen.** It is now **two columns**: the assistant (robot, status, the
   conversation) on the LEFT, and everything of yours on the RIGHT — your live words in a large
   box, a 3-step strip (1 I ask · 2 You speak · 3 You check), a 92px microphone, then Repeat and
   Done. Judge: is it obvious *without reading* where you speak and what to press next?
3. **KIOSK → answer a question by VOICE and let the read-back appear.** This is the one thing a
   microphone must verify: while your answer waits to be confirmed, everything except the read-back
   should visibly **step back** (dimmed, not disabled — the buttons still work), the "tap the mic"
   hint should disappear, and step **3** should light up. Is the current action now unmistakable?
4. **KIOSK → the review screen.** Your answers are column 1; the assistant, the "still needed"
   notice and the three buttons are a **sticky rail** in column 2, with **✔ Confirm & Submit** first
   and full width. It used to be a bar at the very bottom that you had to scroll past every card to
   reach. Judge whether the rail is the right width and whether the answers still read comfortably.
5. **KIOSK → narrow the window** below ~1000px. It should return to exactly the single column it had
   before S40 — nothing about the small-screen experience was traded away for the wide one.
6. **Both staff portals + kiosk, বাংলা toggle**, on every screen above.

### ⚠ One piece of housekeeping
Driving the kiosk end to end left **one synthetic in-progress visit** in the dev DB (phone
`1999000111`, synthetic Bangla answers, never submitted). It sits in the medic queue as a waiting
case. Delete it or ignore it — it is test data, not a patient.

### The rule for next session
**Only change code if the walkthrough reveals a REAL issue.** The brief is complete and test-pinned.

---

## Also open (the human's choice, not a queue)

1. **Rotate the 3 API keys** — HUMAN-only, pending since S25, recommended before any public demo.
2. **Formal WER / precision-recall** on a labelled set — the thesis-evidence gap.
3. **The mid-turn word-loss rule #1 decision** — what happens to a half-captured answer in
   `finalBuffer` when the tab is backgrounded or mic permission is revoked mid-answer. **Yours to
   decide, and it is what BLOCKS the second half of Step S5.**
4. **The Edge run** — every live run so far has been Chrome only.
5. **Faculty future requirements** (`faculty_future_features.md`): quantized summary model,
   quantized STT/TTS, the fully voice-driven follow-up loop (S6–S7 each need their own "go").

---

## ✅ What Session 40 shipped (settled — do not redo or re-derive)

**The Medic-portal outage — one root cause, BOTH reported symptoms, and it was never the backend**
- S39 put a developer note inside `renderPostReferral()`'s **template literal**, as an HTML comment,
  and the note named the `patients` table **in backticks**. A backtick inside a template literal ends
  it, so the browser read the next word as code: `SyntaxError: Unexpected identifier 'patients'`.
- A syntax error is not partial. **The whole `<script>` block is discarded before one line runs**, so
  every function it declared was undefined: `login()` never existed (the button did nothing) and
  `tickClock()` never ran (the clock sat on its `—` placeholder). **"No time is shown" was not a
  second bug.** The `304 Not Modified` lines were a red herring.
- Fixed by moving the paragraph into the existing `/* S39 */` comment above the function — **where
  the note lives, not how it is escaped**. Escaping the backticks would have left the trap armed.
- ⚠ **Why 1005 tests could not see it:** every frontend test here is a static-source assertion (S28 —
  no vitest, no jsdom), and the file still *contained* every asserted string. Only its
  **executability** was gone. That is the gap S39 wrote down about itself.
- `backend/tests/test_portal_inline_script_parses.py` (NEW) closes it in two layers: a
  dependency-free ban on the exact construct, and `node --check` over every inline block and shared
  script, **skipped with a reason when node is absent** (one requirements.txt, Windows + Arch).
  **Both layers were proved non-vacuous against the pre-fix HEAD blob.**

**The kiosk redesign (ADR-0065 e–l)**
- **Two columns, split by whose side of the conversation it is** — machine left, patient right. Built
  with grid **placement and no wrapper elements**, so the DOM, every id, every `aria-live`
  relationship and the screen-reader order are unchanged, and one media query restores the original
  single column below 1000px.
- **The patient's own words are the loudest thing on screen** (1.3rem, upright, red-edged while
  listening) via a **more specific** selector — never a second equal-specificity rule.
- **One emphasised thing at a time:** `data-kiosk-stage="confirming"` is set in the one function that
  opens the read-back gate and cleared in the one that closes it. ⚠ **Dimmed, never disabled** — no
  `pointer-events: none`, no `display: none`, asserted per CSS rule by a test.
- **The 3-step strip has NO JavaScript.** It is lit purely by `data-kiosk-state` and
  `data-kiosk-stage`, so it can never claim the mic is open when it is not.
- **`bringIntoView()` uses `block: 'nearest'`** — an element already on screen does not move at all.
  Four call sites, and ⚠ **never per recognition result**.
- **Review page:** answers column 1, sticky review rail column 2. ⚠ Placed with **`order`, not
  `grid-column`** — an explicit column would create an implicit second track under any single-column
  rule, which is exactly the S36 bug on this grid.

## ⚠ Open gaps / honest caveats (carry these forward)

- **Appearance is UNCLAIMED.** No screenshot exists. Everything is measured geometry and computed
  style. It is verified to be *positioned and stated* correctly, not verified to look good.
- **No microphone ran this session**, and S40 changed no voice logic. The S37 wording for S33–S36
  stands exactly: that run was carried out, **no per-claim results were supplied**, no defects came
  back. Do not upgrade those claims. S25's itemised evidence stands.
- **The 1D confirmation emphasis was verified by setting the state attribute directly** and by a test
  that the gate sets it — not by a spoken answer, because there is no microphone in this environment.
- **Three pinned test literals were UPDATED, not weakened** (two review `grid-template-columns`
  values, and the reflow-before-scroll assertion now made inside the shared helper). Every intent is
  preserved and re-stated in place. Nothing was deleted or loosened.
- **Still not done from earlier cycles:** the 3 API keys, formal WER, the Edge run, Step S5.

## Locked decisions — do NOT re-open

- **ADR-0065 (S40):** a developer note goes in a `/* */` comment, **never** an HTML comment inside
  generated markup; the two kiosk columns are built by grid **placement**, never by wrapper
  elements; the review rail is placed by **`order`**, never `grid-column`; a control that steps back
  is **dimmed, never disabled**; `data-kiosk-stage` is the read-back gate reporting itself and is
  **not** a second state machine; the step strip stays **CSS-only**; automatic movement is
  **`block: 'nearest'`** and is never called per recognition result; node is a **skippable** test
  helper, never a dependency.
- **ADR-0064 (S39):** name provenance derived from `audit_log`, never a column; `unknown` is never
  guessed; glucose is **value + context or neither**; **no band or interpretation** is ever stored or
  computed; HbA1c is not recordable; the PDF **renders the bundle and never reads the DB**; the
  renderer **refuses** rather than mis-shaping Bangla.
- **ADR-0060/0061/0062/0063 (S38)** — BMI derived not stored; dates policed by category with a fixed
  **UTC+06:00** offset (do NOT switch to `ZoneInfo`); the FHIR export excludes the AI suggested
  condition; M16's web search receives the question and nothing else, by signature.
- **ADR-0058 / 0059 (S37)** and **0057 / 0056 / 0055 / 0054 / 0053 / 0052 / 0051 / 0050 / 0049 /
  0048 / 0045 / 0040** — see `decisions.md`.
- **S31's terminal/transient STT split:** `no-speech`, `aborted`, `bad-grammar` must stay OUT of
  `TERMINAL_STT_ERRORS` or Chrome's continuous listening regresses. `r.onend` stays untouched.
- **⚠ No apostrophes in comments inside the `CONFIRM_*` literals** in `kiosk.js` — the vocabulary
  tests parse quoted tokens straight out of the served file. This actually happened in S36.

## ⛔ Step S5 is NOT implemented — do not assume it is

S5 (`faculty_future_features.md` §J) is: **no-speech re-prompt, empty-submit guard, 120 s answer
cap, and permission/visibility recovery.** S34 built only the narrow empty-capture re-ask its
Phase 2 required; S35–S39 built nothing from S5, and **S40 changed no voice logic** — it added one
scroll helper and four call sites, none of which touch turn-taking. Pinned by
`test_step_s5_is_still_not_implemented`: `no_speech_ms` and `max_answer_ms` are still marked
`S5 (not used yet)` and read by nothing, and there is no `visibilitychange` handler and no
permission-recovery path anywhere in the kiosk.
⚠ **The permission/visibility half is BLOCKED, not merely pending** — see open item 3 above.
⚠ The `visibilitychange` listener in **`frontend_shared/staff.js`** is the STAFF queue auto-refresh
(S38) and has nothing to do with S5, which is about the kiosk.

## Reminders (the four non-negotiables)

- **Rule #1:** raw words are never edited. S40 touched no transcript code. The live transcript box is
  still mirrored into **both** language slots, so a language toggle mid-answer cannot replace the
  patient's words with a placeholder — re-verified in source and now pinned by a test.
- **Rule #2:** never diagnoses. Untouched by S40.
- **Rule #3:** red flags ADD-only. Untouched by S40.
- **Rule #4:** synthetic/consented data only. The S40 kiosk run used a synthetic phone and synthetic
  Bangla answers; the one visit it created is noted above.
- Run (Windows): `.venv\\Scripts\\python.exe -m uvicorn backend.app.main:app --reload --port 8001`
- Tests: `pytest backend/tests/` (**1031 passing, 2 skipped**). Windows: `PYTHONIOENCODING=utf-8`.
