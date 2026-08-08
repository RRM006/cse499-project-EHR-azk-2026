# current_task.md — What We Are Doing RIGHT NOW

> This is a small, throwaway snapshot. It gets **overwritten** every session.
> It is NOT a history log (that is `changelog.md`). It answers only:
> "If I open a brand-new Claude Code session, what do I need to know to continue?"

---

**Date:** 2026-08-08 (Session 29 end)
**Phase:** Requirement 3 (voice-first Patient Portal) **Steps S1–S4 of 7 are DONE and live-tested
PASS.** Bangla TTS is **audible but rejected on quality**. A **new 3.0 fix cycle is now OPEN** with 2
items. Test suite: **277 pass, 0 skipped.** Alembic head: **0012** (no schema change needed).

## ✅ What the human's live run CONFIRMED (settled — do not re-test or re-open)
From the S29 real-audio run in Chrome:
- **Mic timing: PASS** — the echo guard holds against real server audio; the mic waits.
- **Countdown: PASS** — S4's 3-2-1 confirmation window, barge-in and flush all work.
- **Transcript clean: YES** — **zero AI words in the patient's verbatim record. Rule #1 holds
  end-to-end even with a server-side TTS provider.** This was the biggest risk of the whole cycle.
- **English TTS: PASS.**
- ❌ **Bangla voice: "Too robotic"** → that is TTS-2 below.

## 🚦 THE NEXT STEP — **TTS-1**, and it needs ONE decision from the human before any code
**TTS-1 = "no gap when tts Bangla and English hear … sometimes 2 question hear at a same time".**

**Root cause is already found — do not re-investigate.** `backend/app/services/followup.py:45` forces
the M7 prompt to emit `"question": "<Bangla question> (<English question>)"`. **Every question is ONE
string containing both languages**, so TTS reads Bangla and then immediately English in one breath.
It is **not** an overlap bug, and **not** caused by ADR-0049 — it has been there since S25 and was only
exposed because espeak `-v bn` also applies Bengali phonetics to the English half.

**⚠ ASK THE HUMAN FIRST (do not assume):** should the patient hear
**(a) only the half matching their UI language** — recommended: fewer seconds, less confusion, matches
the "minimize waiting" priority — or **(b) both halves with a real pause** between them (~1 s longer
per question)?

**Whichever is chosen, the fix is TTS-ONLY:**
- Split the trailing `(...)` for **speech only**, in `frontend_shared/tts.js` / `askAloud()`.
- ⚠ **The stored `system` utterance and the on-screen text MUST keep the FULL bilingual string
  unchanged** — `followup.py:145` stores `question_text` verbatim, and ADR-0028 makes the on-screen
  text the fallback. This changes what is SPOKEN, never what is stored or displayed.
- Do **not** change `followup.py:45` unless the human wants the server to return two separate fields —
  that is a bigger change touching the M7 contract and what medic/doctor display.

## Then TTS-2 — make the Bangla voice human, not robotic
**ADR-0050 (Proposed).** The ADR-0049 **seam is validated and stays**; only the provider is rejected.
espeak-ng is a **formant synthesizer**, so "too robotic" is **inherent, not tunable** — `TTS_SPEED_WPM`
and voice variants change speed/pitch, never naturalness. Swapping it is **one new `TtsProvider`
subclass** in `backend/app/services/tts/` + a `TTS_PROVIDERS` entry: no route, frontend, or schema
change. espeak-ng stays as the offline fallback (and the Arch path, ADR-0040).

**The provider is NOT chosen. Do not assume one.** Options researched in S29:
| Option | Bangla quality | Cost |
|---|---|---|
| **edge-tts** (`bn-BD-NabanitaNeural` / `PradeepNeural`) | genuinely neural, natural Dhaka accent | binary `aiohttp` dep; needs internet; **sends question text to Microsoft** |
| **`facebook/mms-tts-ben`** | neural VITS, fully local | torch+transformers (heavy, CPU-only box); **CC-BY-NC-4.0** = non-commercial |
| **Edge as the kiosk browser** | Microsoft online `bn-BD`, zero code | per-machine setup; helps neither Chrome nor a reproducible demo; **unverified** |

⚠ **Rule #4 decision the human must make explicitly:** M7 questions are **derived from what the patient
said**, so a cloud TTS exports patient-derived text to a third party — exactly why ADR-0049 chose a
local engine. Trading locality for naturalness is legitimate for a prototype on synthetic data, but it
is the human's call, must be recorded in ADR-0050, and changes what the thesis may claim about privacy.
⚠ This also **overlaps faculty Requirement 2** (quantized on-device Bangla STT/TTS) — decide whether
TTS-2 is a 3.0 quick win or folds into Req 2.

## The full tracker
**`agent_docs/context fixed problem 3.0.md` is now 🟢 OPEN** (empty since S24) with **TTS-1** and
**TTS-2**, the human's verbatim wording, priorities, and the files each touches. That file — not this
one — is the living checklist for this cycle. The human also said they want to **add features** in the
upcoming session; those findings go in its RAW FINDINGS INBOX.

## What is already built (do NOT rebuild or re-derive)
- **S1** — `voice_loop` + 4 timings in `.env`, public `GET /api/config`, non-blank `raw_text` guard.
- **S2** — bilingual `[🎤 Speak] [⌨ Type]` switch in both docks, one shared mode, Enter-to-send.
- **S3** — auto-listen: mic opens itself after TTS, echo guard + TTS generation token.
- **S4** — silence detection, the visible 3-2-1 countdown in both docks (Bangla numerals via the reused
  `bnDigits()`), barge-in cancel on **every** `onresult` tick, arm-only-after-real-words, and
  **flush-before-submit** (`recognition.stop()` → submit from `onend` or a 600 ms grace, exactly once)
  so the tail Chrome had not yet finalized is not dropped. **Live-tested PASS.**
- **ADR-0049 TTS seam** — `backend/app/services/tts/` (`base.py` ABC + `espeak.py` + `service.py`,
  mirroring the ADR-0045 OTP seam) + public `GET /api/tts?text=&lang=` → `audio/wav`. `tts.js` walks
  **browser voice → server → `false`**. `/api/config` carries `server_tts: bool`. Missing engine = **503,
  never silent audio**. espeak-ng **1.52.0 is installed** on the Windows box.
- **Static assets now serve `no-cache, must-revalidate`** (`RevalidatedStaticFiles` in `main.py`) — a
  stale cached `shared.js` had silently broken TTS language selection. If frontend edits ever seem not to
  apply, that is fixed now, but **Ctrl+Shift+R** is still the reliable reload.

## ⚠ Open gaps / honest caveats (carry these forward)
- **Steps S5–S7 of Requirement 3 are NOT built.** S5 = no-speech re-prompt (10 s → repeat once → 10 s →
  offer typing), the 120 s answer cap, mic-permission + `visibilitychange` recovery, **and the deferred
  repeat-while-listening echo gap**. S6 = KIOSK-7 resume dock re-verify. S7 = docs + the 12-point live run.
- **Deferred since S25:** tapping "Repeat question" while the mic is ALREADY open plays TTS into a live
  recognizer. Closing it means deciding the fate of the half-spoken answer in the buffer — discarding a
  patient's words is a **rule #1 decision**, not a drive-by change.
- The Web Speech API opens its **own** audio stream, so `echoCancellation` **cannot** be passed. Echo
  protection is structural gating only — the ceiling until Requirement 2.
- **`ttsSpeaking()` — not `speechSynthesis.speaking` — must remain the echo-guard predicate** (ADR-0049).
  `<audio>` is invisible to the latter; reverting it reopens a rule #1 echo hole.
- **`CLAUDE.md` says Python 3.14; the venv is actually 3.13.3.** Not corrected.
- **A second uvicorn may still be running on port 8000** from an older session.
- **Alembic stays at 0012.** No migration is needed; do not create one.

## The standing menu (still the human's call)
1. **TTS-1** ← the natural next move (functional before polish), after the (a)/(b) decision.
2. **TTS-2** — the natural-voice provider choice + the rule #4 privacy decision.
3. **Step S5** of Requirement 3.
4. **Rotate the 3 API keys** (`GEMINI_API_KEY` / `GROQ_API_KEY` / `OPENROUTER_API_KEY`) —
   *recommended before any public demo*. **HUMAN step — I must never handle the keys.** Still NOT done.
5. **More 3.0 findings / new features** → the inbox in `context fixed problem 3.0.md`.
6. **Faculty Reqs 1 & 2** (quantized summary model; quantized on-device STT/TTS — Req 2 now has a seam
   waiting for it). Or formal WER / the TextBee real-SMS demo.

## Locked decisions — do NOT re-open
- **ADR-0050 (S29, Proposed):** keep the ADR-0049 seam, replace espeak-ng as the default provider;
  provider and the privacy trade-off **undecided**.
- **ADR-0049 (S29, Accepted):** server-side TTS provider seam + espeak-ng; **supersedes ADR-0040's
  rejection of server-side TTS** (its premise — that Windows can add a Bengali voice — is false;
  **Bengali is absent from Microsoft's entire Windows TTS voice list**). Browser voice still WINS when
  present. Failure is loud (503 / `speak()` returns false), never silent.
- **ADR-0048 (S28):** voice-first + typing always available; supersedes ADR-0027's voice-only rule. The
  3 s countdown **is** the silence window and is a **confirmation window, never a hard cutoff**; ONE
  answer pipeline (`source: mic|manual`); frontend tests = **static-source assertions only**.
- **ADR-0047 / 0046 / 0045 / 0042–0044 / 0040** — see `decisions.md`.

## Reminders (the four non-negotiables)
- **Rule #1:** raw words are never edited/translated. **Live-verified clean in S29** — keep it that way:
  the TTS-1 fix must change only what is SPOKEN, never the stored or displayed text.
- **Rule #2:** the system never diagnoses — M16 disclaimer server-attached; Diagnosis doctor-only.
- **Rule #3:** red flags are ADD-only — the local rule still forces Critical with every LLM down.
- **Rule #4:** synthetic/consented data only in dev. M7 question text is **derived from patient
  speech** — central to the TTS-2 provider decision.
- Run (Windows): `.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --port 8001`
- Run (Arch):    `.venv/bin/python -m uvicorn backend.app.main:app --reload --port 8001`
  **`.env` changes need a RESTART** (this includes the four `TTS_*` knobs). NEVER delete the DB.
- Tests: `pytest backend/tests/` (**277 passing** as of S29). Windows: `PYTHONIOENCODING=utf-8`.
