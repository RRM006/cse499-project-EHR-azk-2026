# current_task.md — What We Are Doing RIGHT NOW

> This is a small, throwaway snapshot. It gets **overwritten** every session.
> It is NOT a history log (that is `changelog.md`). It answers only:
> "If I open a brand-new Claude Code session, what do I need to know to continue?"

---

**Date:** 2026-08-15 (end of Session 41)
**Phase:** **The S41 brief is COMPLETE.** The four defects the human's **real-microphone** run
surfaced are fixed, the synthetic test visit is deleted, and the API keys are now *checkable* (the
rotation itself is still yours — see below).
Test suite: **1056 passed, 2 skipped, 0 failures** (was 1031).
Alembic head: **0014 — unchanged. 18 tables. No new dependency.**
New ADR: **0066**. ⚠ **No schema, migration, route, service, FHIR, PDF, OTP or auth change** — the
only backend edit is one configuration default. ⚠ **No voice/STT/TTS logic changed.**
**No module changed status. M15 stays 🟨.**

**⚠ Step S5 is STILL NOT implemented and must not be assumed. See the bottom of this file.**

---

## 🚦 THE NEXT STEP — **one thing only you can do, and one you may want to**

### 1. Rotate the 3 API keys (HUMAN-ONLY — everything around it is now ready)

Pending since S25. It needs provider logins, so it cannot be automated — but the verification half
is built. **Never paste a key into chat, a commit, or any `agent_docs/` file.**

For each of the three, in this order: revoke the old key, create a new one, paste it into
`backend/.env` (that file is gitignored and has never been committed — verified this session).

| Variable in `backend/.env` | Provider console |
|---|---|
| `GEMINI_API_KEY` | https://aistudio.google.com/apikey |
| `GROQ_API_KEY` | https://console.groq.com/keys |
| `OPENROUTER_API_KEY` | https://openrouter.ai/settings/keys |

Then restart uvicorn (the keys are read at startup) and verify:

```
.venv\\Scripts\\python.exe -m backend.scripts.check_api_keys
```

It prints PASS/FAIL per provider and **never prints a key**. Exit code 0 = all good.
⚠ A `429` verdict still reads PASS — that means the key is valid and the free daily quota is spent.
⚠ If OpenRouter reports "model not found", its `:free` model ids get retired regularly: pick a
current one from https://openrouter.ai/models and set `OPENROUTER_MODEL` in `backend/.env`.

### 2. A human pass over the kiosk with a real microphone

S41 changed what you see while speaking, and only a person can judge whether it now reads as *simple*
to someone who has never used a computer. Specifically:

- **The open-microphone banner.** While the mic is open you should get a filled red banner reading
  **"🎤 এখন কথা বলুন — বলা শেষ হলে থেমে যান"**, on every screen that listens (phone, OTP,
  conversation, follow-up). Is it unmistakable? Does it disappear the moment listening stops?
- **Your own words.** Speak a long sentence. The text must stay inside the box, wrap, and scroll
  inside itself with the newest line visible — never spill out, never push the mic off screen.
- **The assistant's question.** A long Bangla question must be fully readable, never cut.
- **Medic → open a case → ✏️ Edit.** The form should now scroll itself into view with its **Save**
  button visible. That was the whole "Edit does nothing" bug.

⚠ Hard-reload (Ctrl-F5) first — these are served static files.

---

## Also open (your choice, not a queue)

1. **The six committed `.bak` databases.** ⚠ Two `.gitignore` rules never worked (an inline `#` is
   part of the pattern, not a comment), so `backend/prescreener.db.pre-0003..0010.bak` are **tracked
   in git**. The patterns are fixed and new backups are ignored, but `.gitignore` cannot untrack what
   is already tracked. Removing them is a repo-content decision: `git rm --cached <files>` stops
   tracking them going forward but does not erase them from history. They hold synthetic data, so
   this is hygiene, not an incident.
2. **Formal WER / precision-recall** on a labelled set — the thesis-evidence gap.
3. **The mid-turn word-loss rule #1 decision** — what happens to a half-captured answer in
   `finalBuffer` when the tab is backgrounded or mic permission is revoked mid-answer. **Yours to
   decide, and it BLOCKS the second half of Step S5.**
4. **The Edge run** — every live run so far has been Chrome only.
5. **Faculty future requirements** (`faculty_future_features.md`): quantized summary model,
   quantized STT/TTS, the fully voice-driven follow-up loop (S6–S7 each need their own "go").

---

## ✅ What Session 41 shipped (settled — do not redo or re-derive)

**The patient's words stay in their box**
- `overflow-wrap: anywhere` + `word-break` + `min-width: 0` on the **base** `.dock-transcript`, so all
  four docks are covered by one rule. `min-width: 0` is load-bearing: the box is a flex item and a
  flex item defaults to `min-width: auto`, refusing to shrink below its content.
- Bounded (`max-height: 30vh; overflow-y: auto`) with `flex: none` so it is not squeezed back to its
  minimum, and it scrolls its own newest line into view via `scrollTranscriptToEnd()`.
- ⚠ **`display: block`, never flex-centred.** A flex container with `align-items: center` and
  overflowing content pushes the TOP of that content above the scroll origin, **where it cannot be
  scrolled back to** — the patient would silently lose the start of their own answer (rule #1).

**The microphone says it is open, in words**
- `LISTENING_HINT` now reads **"🎤 You can speak now …" / "🎤 এখন কথা বলুন …"** — changed in the ONE
  constant every dock reads through `listeningHint()`. One edit, four docks.
- A filled banner, not colour alone; SPEAKING/PROCESSING look deliberately different.
- ⚠ `stopListening()` retracts the claim in the same call that clears the listening class — pinned.

**"Clicking Edit does not work" (medic) was a scroll**
- The form opened at y=461 with its **Save button at y=727 in a 720px viewport**. `openIntakeEditor()`
  now calls `bringIntoView(editor)` after showing it.
- ⚠ **Smooth scrolling silently no-ops on that container** (`perspective: 1400px` from the S37 depth
  layer). `bringIntoView()` attempts smooth, then checks `isFullyInView()` and finishes instantly.
- **`bringIntoView()` MOVED to `frontend_shared/shared.js`** — one definition front-end-wide, pinned.

**Data + config**
- Synthetic visit (patient 13 / visit 22, `+8801999000111`) deleted — 21 rows, 8 tables — after every
  reference was enumerated and a backup written. `documents`/`prescriptions` unchanged.
- `OPENROUTER_MODEL` → `google/gemma-4-31b-it:free`; the previous id was **retired** by OpenRouter,
  so ADR-0026's universal fallback was silently dead.
- `.gitignore`: two never-working patterns repaired.

## ⚠ Open gaps / honest caveats (carry these forward)

- **Real-mic: the successful run is YOURS, not this session's.** It is corroborated by the dev DB
  (`source='mic'` Bengali utterances on visit 23, 2026-08-14 18:08–18:11, a visit that reached
  `reviewed`). **This environment cannot do a real-mic run** — the browser reports
  `microphone: denied` with no readable audio-input labels. Nothing is claimed as agent-verified
  microphone testing.
- **Appearance is still UNCLAIMED.** No screenshot is possible here (the Browser pane composites no
  frames). Everything is measured DOM geometry and computed style at 1280/768/375 px.
- **One transient test anomaly, recorded not explained:** a single full run showed 10
  `FileNotFoundError` errors in the documents tests. They did not reproduce across three subsequent
  full runs and pass in isolation. If they return, that is a real lead, not noise.
- **Four pinned test literals were UPDATED, not weakened** — the auto-mode hint wording, the banner's
  size/weight, and two references to the helper that moved. The auto-mode test now asserts the
  property directly ("must not ask for a tap") rather than one exact sentence, which is stronger.
- **Still not done from earlier cycles:** the 3 API keys, formal WER, the Edge run, Step S5.

## Locked decisions — do NOT re-open

- **ADR-0066 (S41):** the transcript box is bounded and scrolls **internally**, never flex-centred;
  wrapping lives on the BASE dock rule so all four docks share it; the open-microphone wording lives
  in **one constant** and is **retracted** when listening stops; `bringIntoView()` has exactly **one**
  definition (shared.js) and **verifies** that its smooth scroll landed; the S37 perspective is NOT
  removed to make smooth scrolling work; synthetic data is deleted only after every reference is
  enumerated and a backup written; API keys are **never** printed, fabricated or auto-rotated.
- **ADR-0065 (S40):** a developer note goes in a `/* */` comment, **never** an HTML comment inside
  generated markup; the two kiosk columns are built by grid **placement**, never wrappers; the review
  rail is placed by **`order`**, never `grid-column`; a control that steps back is **dimmed, never
  disabled**; `data-kiosk-stage` is the read-back gate reporting itself; the step strip stays
  **CSS-only**; node is a **skippable** test helper, never a dependency.
- **ADR-0064 (S39):** name provenance derived from `audit_log`, never a column; `unknown` is never
  guessed; glucose is **value + context or neither**; **no band or interpretation** anywhere; HbA1c is
  not recordable; the PDF **renders the bundle and never reads the DB**; the renderer **refuses**
  rather than mis-shaping Bangla.
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
Phase 2 required; S35–S40 built nothing from S5, and **S41 changed no turn-taking logic** — it added
a scroll helper and changed one hint constant. Pinned by `test_step_s5_is_still_not_implemented`:
`no_speech_ms` and `max_answer_ms` are still marked `S5 (not used yet)` and read by nothing, and
there is no `visibilitychange` handler and no permission-recovery path anywhere in the kiosk.
⚠ **The permission/visibility half is BLOCKED, not merely pending** — see open item 3 above.
⚠ The `visibilitychange` listener in **`frontend_shared/staff.js`** is the STAFF queue auto-refresh
(S38) and has nothing to do with S5, which is about the kiosk.

## Reminders (the four non-negotiables)

- **Rule #1:** raw words are never edited. S41 touched no transcript STORAGE — only how it is shown.
  The live box is still mirrored into **both** language slots, so a language toggle mid-answer cannot
  replace the patient's words with a placeholder (re-verified and pinned).
- **Rule #2:** never diagnoses. Untouched by S41.
- **Rule #3:** red flags ADD-only. Untouched by S41.
- **Rule #4:** synthetic/consented data only. The synthetic visit was removed; the dev DB otherwise
  holds only synthetic/dev records.
- Run (Windows): `.venv\\Scripts\\python.exe -m uvicorn backend.app.main:app --reload --port 8001`
- Tests: `pytest backend/tests/` (**1056 passing, 2 skipped**). Windows: `PYTHONIOENCODING=utf-8`.
- Keys: `.venv\\Scripts\\python.exe -m backend.scripts.check_api_keys` (never prints a key).
