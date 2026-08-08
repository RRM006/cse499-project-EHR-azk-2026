# current_task.md — What We Are Doing RIGHT NOW

> This is a small, throwaway snapshot. It gets **overwritten** every session.
> It is NOT a history log (that is `changelog.md`). It answers only:
> "If I open a brand-new Claude Code session, what do I need to know to continue?"

---

**Date:** 2026-08-08 (Session 28 end)
**Phase:** ✅ Build complete + live-voice gate cleared (S25) — **and a NEW build cycle is UNDERWAY:
faculty Requirement 3 + 3b, the VOICE-FIRST Patient Portal with typing as the always-available
fallback. Steps S1, S2, S3 of 7 are DONE. S4–S7 are NOT built.**
Test suite: **234 pass** (was 192; +19 S1, +11 S2, +12 S3). Alembic head: **0012** (unchanged —
this cycle needs no schema change).

## 🎯 The priority that governs every remaining step (the human, S28)
**Voice is the main goal and primary UX, not an optional feature.** The Patient Portal must guide
patients toward speaking, automating the voice interaction wherever possible. **Typing exists so a
patient is never blocked** by recognition failure, mic/environment problems, or preference.
**UX priority: minimize clicks, waiting and complexity** for elderly/non-technical patients.
**Ideal flow: AI speaks → mic opens automatically → patient speaks → 3-second visible countdown →
submit → AI speaks the next question → repeat.**

## What is already built (do NOT rebuild or re-derive)
- **S1 — backend seam, zero UX change.** `voice_loop` (`auto`|`manual`, default `auto`) +
  `voice_countdown_ms=3000`, `voice_tts_guard_ms=400`, `voice_no_speech_ms=10000`,
  `voice_max_answer_ms=120000` in `core/config.py`, with a `resolved_voice_loop` property (a `.env`
  typo falls back to `auto`, never a startup crash). New **public `GET /api/config`**
  (`api/routes_config.py` + `schemas/kiosk_config.py`) — no DB, no auth, built field-by-field so a
  future secret in `Settings` cannot leak. `AnswerRequest.raw_text` gained `min_length=1` + a
  non-blank validator that **returns the value UNCHANGED** (`.strip()` tests emptiness only — rule #1).
- **S2 — kiosk UI, turn-taking unchanged.** Bilingual `[🎤 Speak] [⌨ Type]` switch in **both** docks
  (conversation + KIOSK-7 resume), one **shared** mode, mic hidden in Type mode, **Enter sends**, and
  mic failure / unsupported browser now switches the patient **to** typing. The old "Microphone
  issue? Type instead" link is **gone**. Voice→Type **discards** the un-submitted STT buffer (never
  pre-fills: a typed edit over STT text would store false `source`/`stt_provider` provenance).
- **S3 — auto-listen.** `askAloud()` at the **3** question sites (`assistantSays`, `setResumeMode`,
  `repeatQuestion`); the per-bubble 🔊 replay deliberately stays plain `speak()`.
  `openMicWhenQuiet()` = the **echo guard** (poll until `speechSynthesis.speaking` clears, then wait
  `tts_guard_ms`, then call the SAME `toggleListening()` a tap calls). **Generation token in
  `tts.js`** so a CANCELLED question's `onend` can never open the mic during the next one.
  `max(3 s, len×80 ms)` safety net for machines where `onend` never fires. `cancelPendingMic()` on
  every deliberate action (tap, mode switch, Done, logout reset). `/api/config` is now consumed.
  **The patient still taps ONCE to finish** — that is S4's job.

## 🚦 The one thing to do next — **Step S4, on the human's "go"**
**S4 = silence detection + the VISIBLE 3-2-1 confirmation countdown + barge-in cancel.** This is the
heart of the requirement and **the step where rule #1 is genuinely at risk** (a clipped answer is a
correctness defect, not a UX nit).

Plan to review before the go:
- Replace `r.onend = () => { if (listening) r.start(); }` in `initRecognition()` — today's
  "brief pauses keep going" line — with an endpointer that arbitrates between "Chrome stopped the
  engine" and "the patient stopped".
- **Every `onresult` tick (interim OR final) restarts the countdown.** The 3 s window is a
  CONFIRMATION window, never a hard cutoff — a cough or "উম্…" cancels it, erring toward not cutting
  the patient off.
- Visible countdown in **both** docks: large 3 → 2 → 1 + a bilingual "submitting" line, driven by
  `voiceConfig.countdown_ms`. Reaching zero calls the existing `stopListening(true)`, which already
  submits and already refuses to send empty text.
- Active only when `autoVoiceMode()`; `voice_loop=manual` keeps tap-to-finish untouched.
- ⚠ **Unlike S3, a spy CANNOT verify S4's core behaviour** — it needs real speech. Expect
  static-source assertions plus, at best, a fake-`onresult` harness for the timer state machine.
  Whether 3 seconds suits an elderly Bangla speaker is answerable **only** by the live run.

### Remaining steps after S4
| Step | What | Risk |
|---|---|---|
| **S5** | No-speech re-prompt (repeat once, then offer typing), empty-submit guard, 120 s cap, mic-permission + `visibilitychange` recovery, **and the deferred repeat-while-listening echo gap** | medium |
| **S6** | KIOSK-7 resume dock + re-verify the `scope=fields` loop | low |
| **S7** | Docs + the human's **12-point live Chrome run** (`faculty_future_features.md` §K) | — |

## ⚠ Open gaps / honest caveats (carry these forward)
- **Deferred to S5, documented in `repeatQuestion()`:** tapping "Repeat question" while the mic is
  ALREADY open plays TTS into a live recognizer. Closing it means deciding the fate of the
  half-spoken answer already in the buffer — discarding a patient's words is a **rule #1 decision**,
  not a drive-by change. Pre-existing since S25.
- **No microphone was opened in S28.** `toggleListening` was replaced by a spy for the browser
  checks, so echo is disproven only at the **scheduling** level, never against a real room.
- **This dev machine has NO Bangla voice installed** (`banglaVoiceAvailable() === false`) — the
  Bangla TTS path is still unexercised; the KIOSK-2 banner correctly shows.
- The Web Speech API opens its **own** audio stream, so `echoCancellation` constraints **cannot** be
  passed. Echo protection is structural gating only — that is the ceiling until Requirement 2.
- **Alembic stays at 0012** for this whole cycle. No migration is needed; do not create one.

## The standing menu (still the human's call — S26)
1. **Continue this cycle: Step S4** ← the natural next move.
2. **Rotate the 3 API keys** (`GEMINI_API_KEY` / `GROQ_API_KEY` / `OPENROUTER_API_KEY` in
   `backend/.env`) — *recommended before any public demo*; `human_live_run_guide.md` **PART 3**.
   **HUMAN step — I must never enter/handle the keys.** Still NOT done.
3. **Manual-testing bugs/UX findings** → `agent_docs/context fixed problem 3.0.md` (📥 still empty by
   design).
4. **Faculty Reqs 1 & 2** (quantized Moshi summary model; quantized on-device STT/TTS) — independent
   of Req 3.
5. **Formal WER / precision-recall** on ~50 samples, and/or the **TextBee real-SMS OTP demo**.

## Locked decisions — do NOT re-open
- **ADR-0048 (S28, Accepted):** voice-first + typing always available; **supersedes ADR-0027's
  clinical-input voice-only rule** (ADR-0028 "text AND audio" untouched); the 3 s countdown **is**
  the silence window and is a **confirmation window, never a hard cutoff**; ONE answer pipeline
  (`source: mic|manual`); timings from `.env` via `GET /api/config`; `raw_text` non-blank
  server-side; frontend tests = **static-source assertions only** (no vitest/jsdom). Rejected: silent
  reinterpretation of ADR-0027; a separate typing flow; pre-filling the text box from the STT buffer
  on a Voice→Type switch; passing `echoCancellation` (impossible with Web Speech).
- **ADR-0047 (S27):** Req 3 = research track, client-side turn-taking, independent of Reqs 1 & 2,
  behind a `voice_loop = manual | auto` switch (ADR-0045 pattern, old path never deleted).
  **Scope EXTENDED by ADR-0048.**
- **ADR-0046 (S25):** module board 1–14 → ✅ on the passed live-voice gate (M5 ⛔, M15 🟨); formal
  WER/precision-recall still owed as evidence.
- **ADR-0045 (S24):** OTP = hashed/expiring/single-use codes + pluggable sender seam; `000000` bypass
  only when `otp_channel=="dev"` AND `OTP_DEV_BYPASS`.
- **ADR-0042/0043/0044** (2.0 approach / Teal Medical / M16 assistant) + the S9–S17 locks — see
  `decisions.md`.

## Important environment notes
- Server: port 8001. Entry points: `/` · `/kiosk.html` · `/medic/` · `/doctor/` · `/legacy/`.
  **`.env` changes need a RESTART** (uvicorn reload does NOT re-run startup migrations) — this now
  matters for the five `VOICE_*` knobs too. NEVER delete the DB.
  Windows console: `PYTHONIOENCODING=utf-8` for pytest.
- Files this cycle touches: `backend/app/core/config.py`, `backend/app/api/routes_config.py`,
  `backend/app/schemas/{kiosk_config,followup}.py`, `frontend/kiosk.{html,js}`,
  `frontend_shared/tts.js`, and `backend/tests/test_kiosk_{config,input_modes,auto_listen}.py` +
  `test_answer_raw_text_guard.py`.
- Follow-up loop knobs (`core/config.py`): `followup_min_questions = 4`,
  `followup_max_questions = 5`, `completeness_threshold = 0.7` — these bound the loop server-side and
  are what make hands-free safe (**the cap ends the conversation, not the patient's finger**).
- `httpx==0.28.1` is a DIRECT dep — **Arch laptop: re-run `pip install -r requirements.txt`**.
- Three API keys in `backend/.env` — **still NOT rotated** (menu item 2).

## Reminders (the four non-negotiables)
- **Rule #1:** raw words are never edited/translated. **In this cycle it is the top risk** — an
  endpointer that clips an answer (S4) or TTS echo transcribed into a `patient` utterance corrupts
  the verbatim record. Typed answers are stored verbatim too.
- **Rule #2:** the system never diagnoses — M16 disclaimer server-attached; Diagnosis doctor-only.
- **Rule #3:** red flags are ADD-only — the local rule still forces Critical with every LLM down.
- **Rule #4:** synthetic/consented data only in dev. **For this cycle:** an always-open mic on a
  shared kiosk can capture **bystanders** into a medical record — the mic must be open ONLY during an
  active turn.
- Run (Windows): `.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --port 8001`
- Run (Arch):    `.venv/bin/python -m uvicorn backend.app.main:app --reload --port 8001`
- Tests: `pytest backend/tests/` (**234 passing** as of S28).
