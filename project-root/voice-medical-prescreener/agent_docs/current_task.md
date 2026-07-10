# current_task.md — What We Are Doing RIGHT NOW

> This is a small, throwaway snapshot. It gets **overwritten** every session.
> It is NOT a history log (that is `changelog.md`). It answers only:
> "If I open a brand-new Claude Code session, what do I need to know to continue?"

---

**Date:** 2026-07-10 (Session 22 end)
**Phase:** Executing **"Context Fixed Problem 2.0"** (`agent_docs/context fixed problem 2.0.md`,
the checkable BUILD TRACKER): UI/UX evolve-the-theme redesign + functional fixes on all three
portals + real OTP + a doctor drug-info chatbot. **One item per "go"**, functional fixes before
polish. **STRUCT ✅ · P1 CLOSED · P2-1/P2-2 ✅. Next = P2-3 (closes P2).** Test suite: **166 pass**.

## Where we are right now
- **P1 (Patient Portal) is fully CLOSED** — P1-1 through P1-6 all ✅ (auto-stop mic, full EN↔BN
  toggle, 4–5 follow-up floor, missing-field highlight, background-assessed submit, teal polish).
- **P2 in progress:** P2-1 done (Dhaka time — root cause was offset-less UTC strings parsed as
  local; fixed via shared `parseUtc()`/`dhakaTime()`/`dhakaDateTime()` in `shared.js`, used by
  `staff.js` — both medic AND doctor queues benefit). P2-2 done (Gender + auto-fill Name/Age/Gender
  from the conversation via extended M3/M8 extraction + `apply_demographics()` fill-only-when-empty
  writer; extended vitals PATCH; medic identity editor). Only **P2-3** left in P2.
- Alembic head still **0010** (P3-1 will bump to 0011). Test suite: **166 pass** (was 156 at cycle
  start: +3 P1-3, +3 P1-5, +4 P2-2).

## The one thing we are doing next
👉 **STEP: P2-3 — Medic Portal UI polish (closes P2).**
   Frontend-only, on top of the shared teal base (ADR-0043), same pattern as P1-6: sweep
   `frontend_medic/index.html` for leftover clinical-blue hardcodes (inline styles/hex tints) and
   retint to the Teal Medical equivalents (`#E6F7F3`/`#B8E5DC`/`#ECF5F3`/`#F4FAF8`); light spacing/
   visual polish per the reference screenshots. KEEP the layout and all wired hooks (queue,
   field-cards, risk card, post-referral card, identity/weight editors). Verify in preview
   (fresh-fetch assets; computed-style checks + screenshot). Small, reviewable, wait for "go".

## The approved plan — priority order (checkable; ONE item per "go")
> Durable copies: THIS list **and** `agent_docs/context fixed problem 2.0.md` (the BUILD TRACKER,
> with per-item file pointers). Keep both in sync. Functional fixes first, theme polish after.

**Cross-cutting (STRUCT):** [x] STRUCT-1 rename · [x] STRUCT-2 logout→`/` · [x] STRUCT-3 theme =
"Teal Medical" (ADR-0043).

**P1 Patient Portal (highest):**
- [x] P1-1 "Summary" auto-stops recording (`kiosk.js` `submitFinalTurn()` + `finishConversation()`).
- [x] P1-2 Language toggle translates ALL UI (bilingual bubbles + `setBilingualText()`;
  patient raw words verbatim — rule #1).
- [x] P1-3 4–5 follow-up floor + deepening (S20: `followup_min_questions=4`, `_loop_state()` gate,
  M7 deepening mode; resume loop unaffected; cap 5 wins. `test_followup_min_questions.py` — 159 pass).
- [x] P1-4 Missing REQUIRED fields highlighted (S20: `.summary-item.missing` + bilingual chip).
- [x] P1-5 Submit fast = background assessment (S21: `_post_submit_assessment()` BackgroundTasks
  job, own session via `db.get_bind()`; red-flag rule verified effective in background — rule #3.
  New `test_submit_background.py` — **162 pass**).
- [x] P1-6 Patient Portal UI polish (S22: 6 blue tints in kiosk.html → teal; amber/green semantic
  colors kept; verified via computed styles + screenshot). **P1 CLOSED.**

**P2 Medic Portal:**
- [x] P2-1 Correct **Dhaka** date/time in the queue (S22: root cause = offset-less UTC strings
  parsed as local; new shared `parseUtc()`+`dhakaTime()`/`dhakaDateTime()` in `shared.js`,
  `staff.js` uses `dhakaTime()`; verified with known instants; both staff portals inherit).
- [x] P2-2 Gender + auto-fill Name/Age/Gender + editable (S22: `patient_demographics` in the
  M3/M8 extraction + `apply_demographics()` fill-only-when-empty writer; vitals PATCH extended;
  medic identity editor. `test_patient_demographics.py` — **166 pass**).
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
- **ADR-0042:** UI = evolve the theme (KEEP layouts); Submit = assess in background; 4–5 follow-up
  floor; browser-side Dhaka time; OTP seam + `000000`; disclaimered chatbot; faculty quantized
  "Future Features" OUT of scope.
- **ADR-0043:** shared palette = "Teal Medical" (primary `#0F766E`, secondary `#0D9488`,
  bg `#F0FBF8`, radius 10px); semantic risk colors kept.
- Pre-existing S9–S17 locks (C1/C2, DB-backed prescriptions, bilingual values, quota-aware
  switching) — see `decisions.md`.

## Important environment notes
- Server: port 8001. Entry points: `/` · `/kiosk.html` · `/medic/` · `/doctor/` · `/legacy/`.
  `.env`/migration changes need a restart. **DEV_OTP=000000**. Alembic head `0010`; NEVER delete
  the DB. Windows console: `PYTHONIOENCODING=utf-8` (used it for pytest this session).
- **Preview gotchas:** browser caches `kiosk.js`/`shared.js`/`shared.css` — `await fetch(url,
  {cache:'reload'})` per changed asset THEN `location.reload()` before asserting. The screenshot
  tool can wedge; a11y `snapshot` is the fallback proof. Stub `window.api` for UI verification
  (rule #4 — no live LLM calls). `preview_click` can silently no-op; prefer `el.click()` via eval.
- Three API keys in `backend/.env` (Gemini/Groq/OpenRouter) — rotate before public demo.
  P1-3 note: each visit now uses ~3 more Groq M7 calls + M8 merges (fine vs ~1,000/day).

## Reminders (the four non-negotiables)
- **Rule #1:** raw words are never edited/translated — patient bubbles/transcript stay verbatim.
- **Rule #2:** the system never diagnoses — the chatbot (P3-3) is informational + disclaimered.
- **Rule #3:** red flags are ADD-only — P1-5 must keep the local red-flag rule effective in the
  background job (it forces Critical even when every LLM is down).
- **Rule #4:** no auto-run of live LLM calls; synthetic/offline data only in dev.
- Run (Windows): `.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --port 8001`
- Run (Arch):    `.venv/bin/python -m uvicorn backend.app.main:app --reload --port 8001`
- Tests: `pytest backend/tests/` (**166 passing** as of S22).
