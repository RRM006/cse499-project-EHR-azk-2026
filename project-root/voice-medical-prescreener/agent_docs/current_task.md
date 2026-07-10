# current_task.md — What We Are Doing RIGHT NOW

> This is a small, throwaway snapshot. It gets **overwritten** every session.
> It is NOT a history log (that is `changelog.md`). It answers only:
> "If I open a brand-new Claude Code session, what do I need to know to continue?"

---

**Date:** 2026-07-10 (Session 23 end)
**Phase:** Executing **"Context Fixed Problem 2.0"** (`agent_docs/context fixed problem 2.0.md`,
the checkable BUILD TRACKER). **One item per "go"**, functional fixes before polish.
**STRUCT ✅ · P1 CLOSED · P2 CLOSED · P3 CLOSED. Only P4-1 (real OTP) is left — and it is
BLOCKED on a human decision (the OTP channel).** Test suite: **177 pass**. Alembic head: **0011**.

## Where we are right now
- **P2 closed in S23:** P2-3 found the medic portal already token-clean; the real fixes were in
  `shared.css` — `.card` radius → `var(--radius)` and verbatim speaker labels on their own line.
- **P3 fully closed in S23:**
  - P3-1: `Visit.submitted_at` (Alembic **0011**, applied), stamped in `set_visit_status()` on
    `awaiting_review`; queues render `dhakaTime(submitted_at || started_at)`; doctor details card
    has a "Submitted / জমার সময়" row (`dhakaDateTime()`).
  - P3-2: verified (code trace + end-to-end test) that the doctor always sees the latest medic
    edits — every doctor-side read is fresh; `test_doctor_sees_medic_edits.py`.
  - P3-3 (**ADR-0044**): M16 drug-info assistant — `services/assistant.py` (ddgs search → one
    Flash-bucket `call_module`), `POST /api/visits/{uuid}/assistant/drug-info`, disclaimer
    attached SERVER-side always (rule #2), doctor slide-in panel (textContent-only rendering).
    Dep: `ddgs==9.14.4` in requirements.txt (**run `pip install -r requirements.txt` on the Arch
    laptop before next run there**).
  - P3-4: `.safety-panel` radius → token; prescription form verified hex-free, Diagnosis empty.

## The one thing we are doing next
👉 **STEP: P4-1 — Real OTP. FIRST ask the human to pick the sender channel** (do NOT build the
   sender before that answer — this was explicitly reserved for the human):
   - ⚠ Free reliable OTP-to-any-phone is NOT feasible (SMS/WhatsApp cost money/approval; a
     Telegram bot cannot cold-message a phone number).
   - **Recommend:** dev/log sender (code printed to the server log) + `000000` universal bypass
     behind a **pluggable sender seam** — plus optionally ONE free reference channel
     (email-OTP or Telegram-for-opted-in-users).
   Then build: `OtpCode` table (new Alembic **0012**), persisted expiring code (hash it),
   verify-otp checks DB code OR the `000000` bypass, sender seam class + dev/log impl, tests
   (expiry, wrong code, bypass, single-use), kiosk unchanged UX-wise.

## The approved plan — priority order (checkable; ONE item per "go")
> Durable copies: THIS list **and** `agent_docs/context fixed problem 2.0.md`. Keep both in sync.

**Cross-cutting (STRUCT):** [x] STRUCT-1 · [x] STRUCT-2 · [x] STRUCT-3 (ADR-0043).
**P1 Patient Portal:** [x] P1-1 … P1-6 — **CLOSED** (S19–S22).
**P2 Medic Portal:** [x] P2-1 Dhaka time · [x] P2-2 demographics · [x] P2-3 polish — **CLOSED** (S22–S23).
**P3 Doctor Portal:** [x] P3-1 submitted-at (0011) · [x] P3-2 latest-details verification ·
[x] P3-3 M16 drug-info assistant (ADR-0044) · [x] P3-4 polish — **CLOSED** (S23).
**P4 OTP (last):**
- [ ] P4-1 Real OTP: `OtpCode` table + Alembic 0012, expiring persisted code, `000000` universal
  bypass, pluggable sender seam. **Channel choice = the human's call (see above).**

## Locked decisions this cycle — do NOT re-open
- **ADR-0042:** UI = evolve the theme (KEEP layouts); background-assessed submit; 4–5 follow-up
  floor; browser-side Dhaka time; OTP seam + `000000`; disclaimered chatbot; faculty "Future
  Features" OUT of scope.
- **ADR-0043:** "Teal Medical" palette; radius 10px via `--radius` (S23 removed the last two
  hardcoded 12px radii); semantic risk colors kept.
- **ADR-0044 (S23):** M16 assistant = visit-scoped endpoint, Flash bucket, server-attached
  mandatory disclaimer, ddgs-only dep, best-effort search (fail → sourceless answer).
- Pre-existing S9–S17 locks (C1/C2, DB-backed prescriptions, bilingual values, quota-aware
  switching) — see `decisions.md`.

## Important environment notes
- Server: port 8001. Entry points: `/` · `/kiosk.html` · `/medic/` · `/doctor/` · `/legacy/`.
  `.env`/migration changes need a RESTART (uvicorn reload does NOT re-run startup migrations —
  seen again in S23; restart via the preview tool applied 0011). **DEV_OTP=000000**. Alembic head
  **0011**; NEVER delete the DB. Windows console: `PYTHONIOENCODING=utf-8` for pytest.
- **New dep S23:** `ddgs==9.14.4` — installed in the Windows venv; **Arch laptop needs
  `pip install -r requirements.txt`** before running there.
- **Preview gotchas:** fresh-fetch changed assets (`await fetch(url,{cache:'reload'})`) then
  navigate; stub `window.api` for UI verification (rule #4 — no live LLM); stub paths must match
  query strings too (e.g. `/prescription/context?doctor_id=`); `preview_eval` can mis-read a
  just-toggled class — re-check before chasing "bugs"; el.click() via eval beats preview_click.
- Three API keys in `backend/.env` (Gemini/Groq/OpenRouter) — rotate before public demo. M16
  spends Flash quota per doctor question (fine; doctor-triggered only).

## Reminders (the four non-negotiables)
- **Rule #1:** raw words are never edited/translated — verbatim panels stay untouched.
- **Rule #2:** the system never diagnoses — M16 answers carry the server-attached "verify before
  prescribing" disclaimer; prescription Diagnosis stays doctor-authored/empty.
- **Rule #3:** red flags are ADD-only — the local rule still forces Critical from the background
  submit job even with every LLM down.
- **Rule #4:** no auto-run of live LLM calls; synthetic/offline data only in dev; the M16 search
  gets only the doctor's typed question, never patient data.
- Run (Windows): `.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --port 8001`
- Run (Arch):    `.venv/bin/python -m uvicorn backend.app.main:app --reload --port 8001`
- Tests: `pytest backend/tests/` (**177 passing** as of S23).
