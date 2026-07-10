# current_task.md — What We Are Doing RIGHT NOW

> This is a small, throwaway snapshot. It gets **overwritten** every session.
> It is NOT a history log (that is `changelog.md`). It answers only:
> "If I open a brand-new Claude Code session, what do I need to know to continue?"

---

**Date:** 2026-07-10 (Session 19 end)
**Phase:** Executing **"Context Fixed Problem 2.0"** (`agent_docs/context fixed problem 2.0.md`,
now a checkable BUILD TRACKER): UI/UX evolve-the-theme redesign + functional fixes on all three
portals + real OTP + a doctor drug-info chatbot. **One item per "go"**, functional fixes before
polish. **All STRUCT done; P1-1 + P1-2 done. Next = P1-3.**

## Where we are right now
- The S9–S17 build is closed (156 tests pass, Alembic head **0010**). This is a fresh fix/feature
  cycle on top of it.
- **Done this cycle:** STRUCT-1 (rename), STRUCT-2 (logout→`/`), STRUCT-3 (Teal Medical theme,
  ADR-0043), P1-1 (Summary auto-stops mic), P1-2 (full EN↔BN toggle). All frontend/CSS; all
  preview-verified with a stubbed `api` (no LLM calls). **No pytest changes yet this cycle.**

## The one thing we are doing next
👉 **STEP: P1-3 — Always ask 4–5 intelligent, history-based follow-up questions.**
   This is the **largest** P1 item and the first BACKEND change of the cycle. Plan:
   1. `backend/app/core/config.py`: add `followup_min_questions: int = 4` (cap stays
      `followup_max_questions: int = 5`).
   2. `backend/app/api/routes_followup.py`: in the non-`fields` loop (`next_question` +
      `answer_question`), do NOT report `complete` via the 0.7 threshold until **≥ min** questions
      have been asked; still stop at the cap. Count asked questions from the `FollowupQuestion`
      rows for the visit. Leave the `scope=fields` resume loop (KIOSK-7) behavior unchanged.
   3. `backend/app/services/followup.py`: broaden `_QUESTION_SYSTEM` + `generate_next_question`
      so that when the 10 field-gaps are all filled it asks clinically useful **deepening**
      questions grounded in the conversation (instead of returning `None`). Keep the no-repeat
      `asked_gaps` guard so it never repeats a target.
   4. **Add a test** in `backend/tests/` (min-count enforced; cap respected; no infinite loop).
   5. Run `pytest backend/tests/` — **all 156 must stay green** (+ the new test).
   Wait for "go". Show the plan/prompt-wording before finalizing the M7 prompt change.

## The approved plan — priority order (checkable; ONE item per "go")
> Durable copies: THIS list **and** `agent_docs/context fixed problem 2.0.md` (the BUILD TRACKER,
> with per-item file pointers). Keep both in sync. Do functional fixes first, theme polish after.

**Cross-cutting (STRUCT):** [x] STRUCT-1 rename · [x] STRUCT-2 logout→`/` · [x] STRUCT-3 theme =
"Teal Medical" (ADR-0043).

**P1 Patient Portal (highest):**
- [x] P1-1 "Summary" auto-stops recording + processes now (`kiosk.js` `submitFinalTurn()` +
  reworked `finishConversation()`).
- [x] P1-2 Language toggle translates ALL UI (bilingual bubbles + `setBilingualText()`;
  patient raw words verbatim — rule #1).
- [ ] P1-3 Force 4–5 history-based follow-ups (config gate + `routes_followup.py` + broaden
  `_QUESTION_SYSTEM` in `services/followup.py`). **Add a test.**
- [ ] P1-4 Highlight MISSING required fields on the summary (`renderSummary` + `.summary-item.missing` CSS).
- [ ] P1-5 Submit fast = background assessment (move `assess_visit`+`suggest_condition` in
  `routes_dashboard.submit_visit`:92 into FastAPI `BackgroundTasks`; keep status+audit synchronous).
- [ ] P1-6 Patient Portal UI polish (on top of the shared teal base).

**P2 Medic Portal:**
- [ ] P2-1 Correct **Dhaka** date/time in the queue (shared `dhakaDateTime()` in `shared.js` using
  `toLocaleString(..., {timeZone:'Asia/Dhaka'})` — browser-side, no backend tzdata; fix `staff.js:51`).
- [ ] P2-2 Patient details: add **Gender**, auto-fill Name/Age/Gender from the conversation
  (`Patient.sex`/`birth_year` exist but are never written — extend M3/M8 extraction + a writer),
  make name/age/gender editable (extend the vitals PATCH or add a patient PATCH).
- [ ] P2-3 Medic Portal UI polish.

**P3 Doctor Portal:**
- [ ] P3-1 Correct patient **submission** Dhaka date/time (add `Visit.submitted_at`, Alembic **0011**,
  set in submit, expose in dashboard/detail, render with `dhakaDateTime()`).
- [ ] P3-2 Show latest patient details incl. medic edits (mostly verification).
- [ ] P3-3 AI drug-info chatbot: slide-in side panel; new `routes_assistant.py` → web search
  (add a free no-key dep e.g. `ddgs`/DuckDuckGo + `httpx`) → `call_module()` (new code e.g. M16) →
  structured answer + MANDATORY disclaimer "AI-generated information. Please verify before
  prescribing." (rule #2 — informational only).
- [ ] P3-4 Doctor Portal UI polish.

**P4 OTP (last):**
- [ ] P4-1 Real OTP: persisted, expiring code (new `OtpCode` table + migration) + `000000` universal
  bypass + a **pluggable sender seam**. ⚠ Free reliable OTP-to-any-phone is NOT feasible (WhatsApp/SMS
  cost money/approval; a Telegram bot can't cold-message a phone). **Confirm the channel with the
  human before building the sender** (recommend: dev/log sender + `000000` for demos, plus ONE free
  reference channel — email-OTP or Telegram-for-opted-in).

## Locked decisions this cycle — do NOT re-open
- **ADR-0042:** UI = evolve the theme (KEEP layouts & wired features; no rebuild); Submit = assess
  in background; faculty "Future Features" (quantized Moshi / STT-TTS) = OUT of scope.
- **ADR-0043:** shared palette = "Teal Medical" (primary `#0F766E`, secondary `#0D9488`, bg
  `#F0FBF8`, radius 10px); ADR-0029 structure + semantic risk colors kept.
- Pre-existing S9–S17 locks (C1/C2, DB-backed prescriptions, bilingual values, quota-aware
  switching) — see `decisions.md`.

## Important environment notes
- Server: port 8001. Entry points: `/` · `/kiosk.html` · `/medic/` · `/doctor/` · `/legacy/`.
  `.env`/migration changes need a restart. **DEV_OTP=000000**. Alembic head `0010` (P3-1 bumps to
  `0011`); NEVER delete the DB. Windows Bangla console needs `PYTHONIOENCODING=utf-8`.
- **Preview gotcha (hit this cycle):** the browser caches `kiosk.js`/`shared.js`/`shared.css` — do
  `await fetch(url, {cache:'reload'})` for each changed asset THEN `location.reload()` before
  asserting, or you'll test stale code. The screenshot tool can also wedge; the a11y `snapshot` is a
  reliable fallback proof.
- Three API keys in `backend/.env` (Gemini/Groq/OpenRouter) — rotate before public demo; never
  auto-run live LLM calls (rule #4). For UI verification, stub `window.api` in the preview.

## Reminders (the four non-negotiables)
- **Rule #1:** raw words are never edited/translated — patient bubbles/transcript stay verbatim.
- **Rule #2:** the system never diagnoses — the chatbot (P3-3) is informational + disclaimered.
- **Rule #3:** red flags are ADD-only; staff can't hide a red-flag Critical.
- **Rule #4:** no auto-run of live LLM calls; synthetic/offline data only in dev.
- Run (Windows): `.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --port 8001`
- Run (Arch):    `.venv/bin/python -m uvicorn backend.app.main:app --reload --port 8001`
- Tests: `pytest backend/tests/` (**156 passing** as of S17; P1-3 adds one).
