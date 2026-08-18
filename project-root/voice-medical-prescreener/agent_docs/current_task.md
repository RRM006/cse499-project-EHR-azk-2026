# current_task.md — What We Are Doing RIGHT NOW

> This is a small, throwaway snapshot. It gets **overwritten** every session.
> It is NOT a history log (that is `changelog.md`). It answers only:
> "If I open a brand-new Claude Code session, what do I need to know to continue?"

---

**Date:** 2026-08-19 (end of Session 42) — **DEMO-HARDENING SESSION, demo is TOMORROW**
**Phase:** The reported Patient-Portal **502** is fixed at its root, the provider chain no longer has
a single point of failure, and a total AI outage now fails safely and **recoverably** instead of
showing the patient an upstream provider's error.
Test suite: **1087 passed, 2 skipped, 0 failures** (was 1056).
Alembic head: **0014 — unchanged. 18 tables. No new dependency. No schema or migration change.**
New ADR: **0067**. ⚠ **No STT/TTS logic was touched** — the speech pipeline is exactly as S41 left it.
**No module changed status. M15 stays 🟨.**

**⚠ Step S5 is STILL NOT implemented.** S42 added a `visibilitychange` handler that is deliberately
NOT S5 — see the bottom of this file.

---

## 🚦 BEFORE THE DEMO — do these in order

### 1. ⚠ Gemini's free daily quota is SPENT right now (measured 2026-08-19)

Not a bug and not a key problem. The key authenticates; the free tier allows **20 requests/day** on
`gemini-3.7-flash` and it is used up. **It resets at midnight Pacific Time.**

This is now survivable — Groq picks the work up in under a second and intake completes in ~7 s — but
it means **the demo is currently running on ONE healthy provider bucket**, which is the exact shape
of the problem this session just fixed. Please close that:

### 2. ⚠ RECOMMENDED — add a Cerebras key (5 minutes, free, no card)

This is the single highest-value thing you can do before tomorrow.

1. Sign up at **https://cloud.cerebras.ai** and create an API key.
2. Add ONE line to `backend/.env` (gitignored — never paste a key into chat or a commit):
   ```
   CEREBRAS_API_KEY=<your key>
   ```
3. Restart uvicorn (keys are read at startup), then verify:
   ```
   .venv\\Scripts\\python.exe -m backend.scripts.check_api_keys
   ```

Why Cerebras specifically: free ~1M tokens/day, OpenAI-compatible, very fast, **already wired into
the chain** (`FALLBACK_ORDER`), and it sits **ahead of** OpenRouter's shared free pool. With it set
the chain becomes `Gemini → Groq → Cerebras → OpenRouter(x3)`. Nothing else needs changing.
⚠ **Do NOT set `MISTRAL_API_KEY`** — that tier trains on inputs (rule #4).

**Optional (not required):** rotating the 3 existing keys, pending since S25. All three
authenticate today, so this is hygiene before a *public* demo, not a fix.

### 3. Hard-reload every portal before the demo

`Ctrl-F5` on `/kiosk.html`, `/medic/` and `/doctor/`. These are static files and S42 changed
`kiosk.js`, `kiosk.html`, `shared.js` and `shared.css`.

### 4. What only YOU can verify — a real-microphone pass

**No microphone run happened this session.** The browser here reports `microphone: denied`.
Everything was verified through the **typed** path, which is the SAME pipeline (`source: manual` vs
`mic`, one endpoint, ADR-0048) — so the backend, the AI chain and the whole flow are proven, but the
speech capture itself is not re-proven by S42 (and S42 changed no STT code).

Please check, speaking normally:
- normal Bangla, then Banglish; one short answer and one long one
- the words stay inside the box and the newest line is visible (S41)
- the red **"🎤 এখন কথা বলুন — বলা শেষ হলে থেমে যান"** banner appears while the mic is open and
  disappears the moment it closes
- **NEW (S42):** while the mic is open, switch to another browser tab and come back. The kiosk must
  stop listening and say *"পেজটি ছেড়ে যাওয়ায় রেকর্ডিং থেমে গেছে…"* — it must NOT sit there still
  showing the red "speak now" banner.

---

## ✅ What Session 42 shipped (settled — do not redo or re-derive)

**The root cause was three faults, not one**
- Groq's `llama-3.3-70b-versatile` is **decommissioned** — no Llama chat model remains in Groq's live
  list, the call answers `404 model_not_found`. Groq is `FALLBACK_ORDER[0]`, so the first fallback
  bucket was dead.
- OpenRouter's `google/gemma-4-31b-it:free` answered **429 from a SHARED upstream pool**. That is
  ADR-0026's universal fallback.
- Which left **Gemini alone**, so its routine daily 429 took everything down. The reported error named
  only the *last* provider to fail, which is why it read as an OpenRouter problem.

**A bucket now names SEVERAL models**
- `OPENROUTER_MODEL` is comma-separated; each entry is its own attempt with its **own cooldown**
  (keyed on `bucket|model`, because the provider's 429 names a model, not a bucket).
- ⚠ Measured: the configured id and one sibling were 429 while **three other siblings served the
  identical request correctly in the same minute**. A `:free` id is a queue you share, not a quota you
  own — so pinning the universal fallback to one id is a single point of failure by construction.

**Live-verified model choices**
- Groq → `openai/gpt-oss-120b`. ⚠ **Rejected on measurement:** `qwen/qwen3.6-27b` emits a `<think>`
  block that breaks `_parse_json`; `groq/compound*` carry **built-in web search** — patient speech
  must never reach a search tool (rule #4).

**Retry and time bounds**
- One retry pass for **transient** failures only (429/5xx/timeout). A 404 or 401 is never retried.
- `CALL_DEADLINE_S = 90` bounds the **whole** call. Unbounded it was 5 attempts x 45 s x 2 passes =
  **7.5 minutes** of spinner. 90 s is ~6x the slowest measured degraded success (14.1 s).

**The patient never sees provider text again**
- ⚠ Six routes answered `detail=str(exc)`, which ends in the raw upstream body — measured as
  containing the model id, `'provider_name': 'Google AI Studio'` and a signup URL.
- All six now go through ONE helper, `backend/app/api/_llm_errors.py`. A test walks `routes_*.py` and
  fails if any file handling `LLMCallError` skips it.
- The kiosk shows its **own** bilingual panel and never echoes server text for these calls, so a
  future server regression cannot reach a patient.

**A total outage is a WAIT, not a dead end**
- Amber panel + hourglass, **not red** — an upstream queue clearing in a moment is a wait, and
  danger-red tells an unwell patient something is wrong with *them*.
- It does not auto-hide (the 8 s banner is right for a typo, wrong for this) and it offers **Try again**.
- ⚠ **The retry resumes from the FAILED step and never re-posts the utterance.** Re-posting would
  write the patient's sentence into their verbatim record twice (rule #1). Verified live: 4 utterances
  before, 4 after, zero duplicates.

**`check_api_keys` was accusing a valid key**
- Groq's 404 body contains `'type': 'invalid_request_error'` and the classifier tested `"invalid"`
  **before** `404` — so it said "REJECTED — the key is wrong" about a perfectly good credential and
  would have sent you to rotate it. Order fixed; it now probes **every** model of every bucket.

## ⚠ Open gaps / honest caveats (carry these forward)

- **No real-microphone run this session** — `microphone: denied` here. Verified via the typed path,
  which is the same pipeline. S42 changed no STT/TTS code.
- **Appearance IS claimed this time, for the new panel only.** The Browser pane composites frames now,
  so the AI-retry panel was screenshotted in English and Bangla. Nothing else was re-screenshotted.
- **I created 3 synthetic test visits in the dev DB** while verifying (phones `+8801955000321/322/323`,
  synthetic Bangla symptoms, rule #4 respected). One of them — সাবিনা — **will appear at the top of
  the medic queue at the demo**. Deleting it is your call, not mine; S41's careful deletion procedure
  is the precedent. Say the word and I will do it the same way.
- **The six committed `.db.bak` files are still tracked** (unchanged since S41). Repo-content decision.
- **Still not done:** Step S5, the mid-turn word-loss rule #1 decision, formal WER, the Edge run.

## Locked decisions — do NOT re-open

- **ADR-0067 (S42):** a bucket may name several models and each is its own attempt with its own
  cooldown; cooldowns key on `bucket|model`; only transient failures are retried, exactly once; the
  whole call is time-bounded; `str(exc)` never answers a patient and all LLM routes go through
  `_llm_errors.llm_unavailable()`; the kiosk shows its own bilingual panel rather than server text;
  the retry never re-posts an utterance; `check_api_keys` decides the MODEL verdict before the
  CREDENTIAL verdict; the `visibilitychange` handler is **not** S5 and takes no position on
  `finalBuffer`.
- **ADR-0066 (S41), ADR-0065 (S40), ADR-0064 (S39), ADR-0060–0063 (S38), ADR-0058/0059 (S37)** and
  earlier — see `decisions.md`. All still stand; S42 re-verified S41's containment and Edit-scroll fixes.
- **S31's terminal/transient STT split** — `no-speech`, `aborted`, `bad-grammar` stay OUT of
  `TERMINAL_STT_ERRORS` or Chrome's continuous listening regresses. `r.onend` stays untouched.
- **⚠ No apostrophes in comments inside the `CONFIRM_*` literals** in `kiosk.js`.
- **⚠ Write project files as LF.** S42 wasted a cycle: Python's `write_text` on Windows converts LF to
  CRLF, which silently broke two tests that split on a bare newline. Pass `newline="\\n"`.

## ⛔ Step S5 is NOT implemented — and S42's visibility handler is NOT it

S5 (`faculty_future_features.md` §J) is: **no-speech re-prompt, empty-submit guard, 120 s answer cap,
and permission/visibility recovery.** `no_speech_ms` and `max_answer_ms` are still served by
`/api/config` and **read by nothing** — pinned by a test that now counts their references.

S42 added `handleVisibilityChange()`, which does ONE thing: when the tab is hidden while the mic is
open, it calls the **existing** `stopListening(false)` so `r.onend` cannot spin a recogniser that
cannot hear while the screen still shows the red "speak now" banner. It uses the identical call
`setInputMode('type')` and `finishConversation()` already make, so it introduces **no new rule** about
the patient's captured words. Tests forbid it from referencing `finalBuffer`, any submit path, or any
S5 timing.
⚠ **The mid-turn word-loss rule #1 decision is still YOURS and still blocks the second half of S5.**
⚠ The `visibilitychange` listener in **`frontend_shared/staff.js`** is the S38 staff queue
auto-refresh and is unrelated.

## Reminders (the four non-negotiables)

- **Rule #1:** raw words are never edited. S42 touched no transcript storage, and the retry path was
  built specifically so a retry cannot duplicate an utterance. Verified live through a real outage.
- **Rule #2:** never diagnoses. S42 added no clinical content of any kind.
- **Rule #3:** red flags ADD-only. Untouched.
- **Rule #4:** synthetic/consented data only. All S42 test data is synthetic. Two candidate models
  were **rejected** for carrying built-in web search.
- Run (Windows): `.venv\\Scripts\\python.exe -m uvicorn backend.app.main:app --reload --port 8001`
- Tests: `pytest backend/tests/` (**1087 passing, 2 skipped**). Windows: `PYTHONIOENCODING=utf-8`.
- Keys: `.venv\\Scripts\\python.exe -m backend.scripts.check_api_keys` (never prints a key).
