# current_task.md — What We Are Doing RIGHT NOW

> This is a small, throwaway snapshot. It gets **overwritten** every session.
> It is NOT a history log (that is `changelog.md`). It answers only:
> "If I open a brand-new Claude Code session, what do I need to know to continue?"

---

**Date:** 2026-07-11 (Session 24 end; 24b docs addendum: CLAUDE.md refreshed, 2.0 tracker closed,
`context fixed problem 3.0.md` scaffold + `faculty_future_features.md` created)
**Phase:** ✅ **"Context Fixed Problem 2.0" is COMPLETE** — STRUCT, P1, P2, P3 and P4-1 (real OTP,
ADR-0045) are ALL done. Test suite: **192 pass**. Alembic head: **0012** (applied to the dev DB).
There is no open build tracker. What remains is HUMAN work, not build work.

## Where we are right now
- **P4-1 landed in S24:** real OTP behind a pluggable sender seam (`backend/app/services/otp/`).
  - `OTP_CHANNEL=dev` (default): the code is printed to the SERVER LOG (`[OTP] verification code
    for +8801… : NNNNNN`) and `000000` still works (`OTP_DEV_BYPASS=true`). Kiosk UX unchanged.
  - `OTP_CHANNEL=textbee`: real SMS via a TextBee.dev Android-SIM gateway; the `000000` bypass is
    structurally dead on this channel (tested). Needs `TEXTBEE_API_KEY` + `TEXTBEE_DEVICE_ID`.
  - Security: hashed (salted SHA-256) single-use codes, 5-min expiry, constant-time compare,
    5-attempt lockout (429), 60 s resend throttle. `otp_codes` table = Alembic **0012**.
  - Bonus fix: `migrations/env.py` now passes `disable_existing_loggers=False` — previously EVERY
    startup silenced all uvicorn logs (banner/access/OTP line) the moment migrations ran.
- Research evidence (S24): free SMS-OTP to any BD number does not exist (Twilio BD ~$0.60/SMS,
  WhatsApp ~$0.0113 auth msg, Firebase = Blaze-only, Telegram Gateway $0.01/code Telegram-only);
  production path later = a BTRC-approved BD aggregator (~৳0.30–0.40/OTP) as one new sender class.

## The one thing we are doing next
👉 **STEP: the HUMAN live real-mic run** — follow `agent_docs/human_live_run_guide.md` end to end
   (TC-V1/V2/V3/F2/R1 + jot numbers for `test_log.md`). Note for the guide: with the dev channel
   the kiosk OTP can now be EITHER `000000` OR the real code from the server log. Also rotate the
   three API keys before any public demo (guide PART 3). Optional demo upgrade: install TextBee on
   an Android phone (BD SIM), set `OTP_CHANNEL=textbee` + creds in `backend/.env`, restart, and
   show a real SMS OTP. **Bugs/UX findings from the manual testing go into
   `agent_docs/context fixed problem 3.0.md`** (S24 scaffold: human pastes raw notes in its inbox
   → we triage into a numbered tracker like 2.0 → one item per "go"). The faculty quantized-model
   work is filed in `agent_docs/faculty_future_features.md` (research track — needs its own plan).

## Locked decisions this cycle — do NOT re-open
- **ADR-0045 (S24):** OTP = hashed/expiring/single-use codes in `otp_codes` + pluggable sender
  seam; `dev` log sender default; `000000` bypass only when `otp_channel=="dev"` AND
  `OTP_DEV_BYPASS` (structurally impossible elsewhere); TextBee = free real-SMS demo channel;
  BTRC aggregator = future production sender (new subclass, no core change).
- **ADR-0042/0043/0044** (2.0 approach / Teal Medical / M16 assistant) and the pre-existing
  S9–S17 locks — see `decisions.md`.

## Important environment notes
- Server: port 8001. Entry points: `/` · `/kiosk.html` · `/medic/` · `/doctor/` · `/legacy/`.
  `.env`/migration changes need a RESTART (uvicorn reload does NOT re-run startup migrations).
  Alembic head **0012**; NEVER delete the DB. Windows console: `PYTHONIOENCODING=utf-8` for pytest.
- OTP env (backend/.env, see .env.example): `OTP_CHANNEL=dev|textbee`, `OTP_DEV_BYPASS`,
  `DEV_OTP=000000`, `OTP_TTL_SECONDS=300`, `OTP_MAX_ATTEMPTS=5`, `OTP_RESEND_COOLDOWN_SECONDS=60`,
  `TEXTBEE_API_KEY/TEXTBEE_DEVICE_ID/TEXTBEE_BASE_URL`.
- `httpx==0.28.1` is now a DIRECT dep (was transitive) — **Arch laptop: re-run
  `pip install -r requirements.txt`** (also still needs it for S23's `ddgs`).
- Three API keys in `backend/.env` (Gemini/Groq/OpenRouter) — rotate before public demo.
- S24 left a few synthetic patients in the dev DB (0175/0176/0177/0178/0179 9-digit fakes) from
  live verification — harmless demo data.

## Reminders (the four non-negotiables)
- **Rule #1:** raw words are never edited/translated — verbatim panels stay untouched.
- **Rule #2:** the system never diagnoses — M16 disclaimer server-attached; Diagnosis doctor-only.
- **Rule #3:** red flags are ADD-only — the local rule still forces Critical with every LLM down.
- **Rule #4:** no auto-run of live LLM calls; synthetic/consented data only in dev; OTP codes are
  never persisted or logged in plaintext (the dev-channel server log is the ONE sanctioned spot).
- Run (Windows): `.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --port 8001`
- Run (Arch):    `.venv/bin/python -m uvicorn backend.app.main:app --reload --port 8001`
- Tests: `pytest backend/tests/` (**192 passing** as of S24).
