# current_task.md — What We Are Doing RIGHT NOW

> This is a small, throwaway snapshot. It gets **overwritten** every session.
> It is NOT a history log (that is `changelog.md`). It answers only:
> "If I open a brand-new Claude Code session, what do I need to know to continue?"

---

**Date:** 2026-07-09 (Session 18 end)
**Phase:** Executing a NEW work spec — **"Context Fixed Problem 2.0"** (`agent_docs/context fixed
problem 2.0.md`): UI/UX redesign + functional fixes across all three portals + real OTP + a
doctor-side AI drug-info chatbot. The plan is **approved**; we execute **one item per "go"**,
functional fixes before polish. **STRUCT-1 is DONE.**

## Where we are right now
- The 20-step build from S9–S17 is closed (156 tests pass, Alembic head **0010**). This is a
  fresh feature/fix cycle on top of it.
- **STRUCT-1 DONE (S18):** renamed user-facing "Patient Kiosk" → "Patient Portal" (EN + Bangla
  "রোগী পোর্টাল") in `frontend/index.html:41` + `frontend/kiosk.html:6,81,200`. File names/URLs
  (`/kiosk.html`, `/kiosk.js`) unchanged on purpose. No backend touched, no tests run.

## The one thing we are doing next
👉 **STEP: STRUCT-2 — Logout on every page → returns to the Portal Directory (`/`).**
   Add a small **Logout** button to the medic and doctor portal headers
   (`frontend_medic/index.html` + `frontend_doctor/index.html`, the `.portal-header`) that
   navigates to `/`. Optionally add a shared `logout()` helper in `frontend_shared/shared.js`.
   The kiosk already auto-logs-out, so it likely needs nothing. Small, reviewable, wait for "go".

## The approved plan — priority order (checkable; ONE item per "go")
> Full detail in the Claude plan file `~/.claude/plans/…agile-forest.md` (not auto-loaded next
> session). The durable copies are THIS list **and** `agent_docs/context fixed problem 2.0.md`,
> which is now a checkable **BUILD TRACKER** (plan IDs + status, requirements below it) — keep both
> in sync as items land. Do functional fixes first, theme polish after.

**Cross-cutting (STRUCT):** [x] STRUCT-1 rename · [ ] STRUCT-2 logout→`/` · [ ] STRUCT-3 theme
tokens in `frontend_shared/shared.css` (evolve toward teal/modern; keep layouts).

**P1 Patient Portal (highest):**
- [ ] P1-1 "Summary" auto-stops recording + processes now (`kiosk.js` `finishConversation`:287 —
  if `listening`, stop + flush `finalBuffer` as a turn before intake/profile).
- [ ] P1-2 Language toggle translates ALL UI (assistant/opening bubbles carry `data-en/bn` +
  re-apply in `onLanguageChange`; **patient raw words NEVER translated — rule #1**).
- [ ] P1-3 Force 4–5 history-based follow-ups (add `followup_min_questions=4` in `config.py`;
  don't report `complete` before min in `routes_followup.py`; broaden `_QUESTION_SYSTEM` in
  `services/followup.py` so it asks useful deepening Qs when the 10 gaps are filled). Add a test.
- [ ] P1-4 Highlight MISSING required fields on the summary (`renderSummary` + `.summary-item.missing` CSS).
- [ ] P1-5 Submit fast = background assessment (move `assess_visit`+`suggest_condition` in
  `routes_dashboard.submit_visit`:92 into FastAPI `BackgroundTasks`; keep status+audit synchronous).
- [ ] P1-6 Patient Portal UI polish.

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

## Locked decisions this cycle (ADR-0042) — do NOT re-open
- **UI = evolve the theme** (teal/modern tokens + polish; KEEP layouts & wired features; no rebuild).
- **Submit = assess in background** (BackgroundTasks; risk fills in on the medic's 15s refresh).
- Faculty "Future Features" (quantized Moshi / quantized STT-TTS) = OUT of scope for this spec.
- Plus the pre-existing locks from the S9–S17 build (C1/C2, DB-backed prescriptions, bilingual
  values, quota-aware switching) — see `decisions.md`.

## Important environment notes
- Server: port 8001. Entry points: `/` · `/kiosk.html` · `/medic/` · `/doctor/` · `/legacy/`.
  `.env`/migration changes need a restart. **DEV_OTP=000000**. Alembic head `0010` (P3-1 bumps to
  `0011`); NEVER delete the DB. Windows Bangla console needs `PYTHONIOENCODING=utf-8`.
- Three API keys in `backend/.env` (Gemini/Groq/OpenRouter) — rotate before public demo; never
  auto-run live LLM calls (rule #4, synthetic data only). Browser-cache gotcha: `{cache:'reload'}`
  + reload before asserting in preview.

## Reminders (the four non-negotiables)
- **Rule #1:** raw words are never edited/translated — this constrains P1-2 (patient bubbles stay verbatim).
- **Rule #2:** the system never diagnoses — the chatbot is informational + disclaimered; the doctor decides.
- **Rule #3:** red flags are ADD-only; staff can't hide a red-flag Critical.
- **Rule #4:** no auto-run of live LLM calls; synthetic/offline data only in dev.
- Run (Windows): `.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --port 8001`
- Run (Arch):    `.venv/bin/python -m uvicorn backend.app.main:app --reload --port 8001`
- Tests: `pytest backend/tests/` (**156 passing** as of S17).
