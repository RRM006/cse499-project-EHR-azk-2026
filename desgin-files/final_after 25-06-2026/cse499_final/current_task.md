# current_task.md — What We Are Doing RIGHT NOW

> This is a small, throwaway snapshot. It gets **overwritten** every session.
> It is NOT a history log (that is `changelog.md`). It answers only:
> "If I open a brand-new Claude Code session, what do I need to know to continue?"

---

**Date:** 2026-06-25
**Phase:** Phase 0 → starting **Phase A** of the locked build plan (Setup & first voice add-on)
**Module:** Module 1 (Speech-to-Text, working) + **Module 7 groundwork (TTS)**

## Where we are right now
The Session 7 architect lock is DONE (planning only — no code was written). The plan is now
final: the Emergency module is removed from the flow and replaced by a **rule-based red-flag
check inside Module 10**; the stack is CONFIRMED (plain HTML/JS + FastAPI + SQLite/Alembic +
python-docx) with **browser TTS added** for M7; each LLM module is assigned a free-tier API
(Gemini Flash / Gemini Flash-Lite / Groq, OpenRouter `:free` as fallback); the patient
interaction is **voice-only** and follow-up questions display as **text AND audio at the same
time**. All tracking docs were rewritten this session (see `changelog.md` Session 7 and
`decisions.md` ADR-0024…0028).

The actual running code is unchanged from Session 6:
- Pipeline: **mic → Chrome Web Speech API → RAW (immutable, stored) → raw .docx on Stop →
  Gemini correct → corrected .docx**, two separate downloadable Word files.
- DB schema is owned by **Alembic** (auto-migrates at startup; never delete the DB).
- `pytest backend/tests/` = **19 passing**. Server runs on **port 8001**.

## The one thing we are doing next
**Phase A / Step A1 — Add browser Text-to-Speech (TTS) to the existing frontend.**
This is the smallest first step toward Module 7's "audio + text" requirement and adds no new
dependency (uses the browser's built-in `window.speechSynthesis`).

Goal for the step:
1. Add a tiny TTS helper in `frontend/app.js`: `speak(text)` →
   `const u = new SpeechSynthesisUtterance(text); u.lang = 'bn-BD';
   speechSynthesis.speak(u);` (pick an installed Bangla voice from
   `speechSynthesis.getVoices()` if one exists, else fall back to the default voice).
2. Add a temporary "🔊 Test speak" button to `frontend/index.html` (Mintlify-styled pill) that
   speaks a hard-coded Bangla sentence, e.g. `আপনার কতদিন ধরে জ্বর হচ্ছে?`
3. Confirm the on-screen text of that sentence is shown at the same time (text is the
   always-present fallback if no Bangla voice is installed / audio is muted).
4. Verify in Chrome on both machines; note in `test_log.md` whether a Bangla voice was
   available on each OS (this is the one real risk — see Open Flag 4).

**Do NOT** wire this to any backend or LLM yet, and do NOT touch the raw/corrected/export code.
Keep it to the two frontend files. Plan it with the human and get "go" before writing code.

## Important environment notes
- **Server runs on port 8001.** `.claude/launch.json` has TWO configs: Windows
  (`backend (FastAPI + uvicorn)`, `.venv/Scripts/python.exe`) and Linux
  (`backend-linux (FastAPI + uvicorn)`, `.venv/bin/python`). Pick the one for your OS.
  - ⚠ **Preview gotcha (Arch):** the preview panel DEFAULTS to the first (Windows) config and
    fails with `spawn .venv/Scripts/python.exe ENOENT`. On Linux start the **`backend-linux`**
    config by name, or run uvicorn directly (Arch command below).
- `.env` changes need a server RESTART (uvicorn --reload only watches `.py`).
- Schema changes are applied by Alembic automatically at startup — **never delete the DB.**
- Synthetic/consented data only — the free APIs may log input (rule #4).

## Reminders
- Raw words are never edited (rule #1). Correction AND both .docx files are derived/separate.
- The system never diagnoses (rule #2). Rule #3 is now "**surface red flags; never reassure
  falsely**" — the red-flag check lives in **Module 10**, not a separate Emergency module.
- Schema = Alembic; do not delete the DB; add new columns via a new migration (ADR-0022).
- Plan first, one small step at a time. Do not assume. (CLAUDE.md)
- Frontend follows DESIGN-mintlify.md; the transcript panels share the fixed-height + scroll +
  stick-to-bottom behavior (see CLAUDE.md).
- Run (Windows): `.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --port 8001`
- Run (Arch):    `.venv/bin/python -m uvicorn backend.app.main:app --reload --port 8001`
- Tests: `pytest backend/tests/`  ·  Python 3.14 needs SQLAlchemy>=2.0.51.
