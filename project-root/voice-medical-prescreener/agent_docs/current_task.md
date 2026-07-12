# current_task.md — What We Are Doing RIGHT NOW

> This is a small, throwaway snapshot. It gets **overwritten** every session.
> It is NOT a history log (that is `changelog.md`). It answers only:
> "If I open a brand-new Claude Code session, what do I need to know to continue?"

---

**Date:** 2026-07-12 (Session 26 end)
**Phase:** ✅ **Build complete AND the human live-voice gate is CLEARED.** Both build cycles (the
20-step build + "Context Fixed Problem 2.0") are done, the human live real-mic run PASSED (S25),
and Modules 1–14 are ✅ (ADR-0046). Test suite: **192 pass**. Alembic head: **0012** (17 tables).
**There is no forced next step — what we work on next is the HUMAN's choice** (see the menu below).

## Where we are right now
- The system is **demo-ready** except for API-key rotation. Nothing is broken; no open build tracker.
- **The 3.0 tracker (`context fixed problem 3.0.md`) is intentionally EMPTY.** In S25 the human
  reported **0 bugs** from the live run and said "leave it empty for now" — so the 📥 inbox reads
  "(nothing yet)" by design. The moment the human pastes findings there, we triage into a numbered
  cycle (one item per "go", functional before polish).
- ⚠ Standing honesty caveat: the S25 live run was **qualitative** (no by-hand WER/precision-recall)
  and **Windows-only**. Formal metrics are a recommended thesis-evidence follow-up, not a blocker.

## The one thing we are doing next — 👉 HUMAN'S CHOICE from this menu (do NOT assume one)
> At the START of every session, surface this menu and wait for the human to pick — picking among
> these (or something else entirely) is the human's call. This is a standing request (S26).

1. **Rotate the 3 API keys** — `GEMINI_API_KEY` / `GROQ_API_KEY` / `OPENROUTER_API_KEY` in
   `backend/.env`. *Recommended before any public demo* (the keys were typed into chat during dev, so
   treat them as burned). Steps: `agent_docs/human_live_run_guide.md` **PART 3** (new key on each
   provider → revoke the old → paste into `backend/.env` → **restart the server**; `.env` is read
   only at startup). **HUMAN step — I must never enter/handle the keys.**
2. **Report manual-testing bugs/UX findings** → paste raw notes into
   `agent_docs/context fixed problem 3.0.md` (📥 inbox). I triage → numbered tracker → your approval
   → one item per "go".
3. **Faculty future features** (research track, needs its own plan) — the two faculty requirements in
   `agent_docs/faculty_future_features.md`: a **quantized Moshi** medical-summary model + **quantized
   on-device STT/TTS** replacing the browser APIs. Suggested order there: summary → STT → TTS.
4. **Record formal WER / precision-recall** on ~50 samples for thesis evidence
   (`test_log.md` "Metrics we care about"), and/or the **TextBee real-SMS OTP demo**
   (install TextBee on an Android+BD-SIM phone, set `OTP_CHANNEL=textbee` + creds, restart).
5. **Anything else the human wants.**

## Locked decisions — do NOT re-open
- **ADR-0046 (S25):** on the passed live-voice gate, the module board (1–14) moved to ✅ (M5 ⛔,
  M15 🟨), with the caveat that formal WER/precision-recall is still owed (qualitative Windows-only
  run). The human picked this over the more conservative "flip M1 & M7 only" / "change nothing".
- **ADR-0045 (S24):** OTP = hashed/expiring/single-use codes in `otp_codes` + pluggable sender seam;
  `dev` log sender default; `000000` bypass only when `otp_channel=="dev"` AND `OTP_DEV_BYPASS`
  (structurally impossible elsewhere); TextBee = free real-SMS demo channel; BTRC aggregator = future
  production sender (new subclass, no core change).
- **ADR-0042/0043/0044** (2.0 approach / Teal Medical / M16 assistant) and the pre-existing S9–S17
  locks — see `decisions.md`.

## Important environment notes
- Server: port 8001. Entry points: `/` · `/kiosk.html` · `/medic/` · `/doctor/` · `/legacy/`.
  `.env`/migration changes need a RESTART (uvicorn reload does NOT re-run startup migrations).
  Alembic head **0012**; NEVER delete the DB. Windows console: `PYTHONIOENCODING=utf-8` for pytest.
- OTP env (backend/.env, see .env.example): `OTP_CHANNEL=dev|textbee`, `OTP_DEV_BYPASS`,
  `DEV_OTP=000000`, `OTP_TTL_SECONDS=300`, `OTP_MAX_ATTEMPTS=5`, `OTP_RESEND_COOLDOWN_SECONDS=60`,
  `TEXTBEE_API_KEY/TEXTBEE_DEVICE_ID/TEXTBEE_BASE_URL`.
- `httpx==0.28.1` is a DIRECT dep — **Arch laptop: re-run `pip install -r requirements.txt`** (also
  needed for S23's `ddgs`).
- Three API keys in `backend/.env` (Gemini/Groq/OpenRouter) — **still NOT rotated** (option 1 above).
  Some synthetic patients (0175–0179 9-digit fakes) linger in the dev DB — harmless demo data.

## Reminders (the four non-negotiables)
- **Rule #1:** raw words are never edited/translated — verbatim panels stay untouched.
- **Rule #2:** the system never diagnoses — M16 disclaimer server-attached; Diagnosis doctor-only.
- **Rule #3:** red flags are ADD-only — the local rule still forces Critical with every LLM down.
- **Rule #4:** no auto-run of live LLM calls; synthetic/consented data only in dev; OTP codes are
  never persisted or logged in plaintext (the dev-channel server log is the ONE sanctioned spot).
- Run (Windows): `.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --port 8001`
- Run (Arch):    `.venv/bin/python -m uvicorn backend.app.main:app --reload --port 8001`
- Tests: `pytest backend/tests/` (**192 passing** as of S24/S25).
